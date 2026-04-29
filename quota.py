"""
Quota counters atômicos por (tenant, period_yyyymm, kind) (Frente 2.2-2.6).

Suporta 3 kinds: leads_month, wa_msgs_month, gemini_tokens_month.

Uso::

    from quota import consume_quota, get_usage, refund_quota

    allowed, current, limit = consume_quota(tenant_id, "wa_msgs_month", 1)
    if not allowed:
        # bloqueia ou queue conforme política do kind

    # Falha posterior — devolve cota:
    refund_quota(tenant_id, "wa_msgs_month", 1, reason="provider_send_failed")

Atomicidade:
- UPSERT + UPDATE com WHERE compare-and-swap. SQLite/Postgres seguros
  contra race entre dois consumes simultâneos no mesmo tenant×kind.
- Suporta `dry_run=True` pra checar sem incrementar (útil em pre-checks).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from db import models
from db.database import SessionLocal
import plans as plans_module


logger = logging.getLogger(__name__)


VALID_KINDS = ("leads_month", "wa_msgs_month", "gemini_tokens_month")


def _current_yyyymm(when: Optional[datetime] = None) -> int:
    when = when or datetime.now(timezone.utc)
    return when.year * 100 + when.month


def consume_quota(
    tenant_id: str,
    kind: str,
    amount: int = 1,
    *,
    dry_run: bool = False,
    cost_brl_cents: int = 0,
    db_session=None,
) -> tuple[bool, int, int]:
    """
    Atomicamente incrementa counter. Retorna (allowed, current_after, limit).

    Se `allowed=False`, NENHUM incremento foi aplicado (atômico via CAS).

    Args:
        tenant_id: tenant alvo
        kind: leads_month | wa_msgs_month | gemini_tokens_month
        amount: quanto consumir (default 1)
        dry_run: se True, só checa (não incrementa)
        cost_brl_cents: custo aproximado pra contabilidade (gemini_tokens)
        db_session: opcional reuso de session
    """
    if kind not in VALID_KINDS:
        logger.error("[quota] kind inválido: %s", kind)
        return True, 0, 0  # fail open pra não quebrar fluxo

    if amount < 0:
        return refund_quota(tenant_id, kind, abs(amount), db_session=db_session)

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        yyyymm = _current_yyyymm()
        limit = plans_module.effective_quota(tenant_id, kind, db_session=db)

        # 1. Garante que a row existe (UPSERT no-op se já)
        # SQLite e Postgres divergem na sintaxe; usamos try/except como portátil.
        existing = db.query(models.TenantUsageCounter).filter_by(
            tenant_id=tenant_id, period_yyyymm=yyyymm, kind=kind,
        ).first()

        current_before = existing.count if existing else 0

        if dry_run:
            allowed = (limit == plans_module.UNLIMITED) or (current_before + amount <= limit)
            return allowed, current_before, limit

        # 2. Compare-and-swap atômico
        if limit == plans_module.UNLIMITED:
            # Unlimited: incrementa sem checar
            if existing:
                existing.count = (existing.count or 0) + amount
                if cost_brl_cents:
                    existing.cost_brl_cents = (existing.cost_brl_cents or 0) + cost_brl_cents
                existing.updated_at = datetime.now(timezone.utc)
            else:
                db.add(models.TenantUsageCounter(
                    tenant_id=tenant_id, period_yyyymm=yyyymm, kind=kind,
                    count=amount, cost_brl_cents=cost_brl_cents,
                ))
            db.commit()
            return True, current_before + amount, limit

        # Limited: tenta UPDATE com WHERE count+amount <= limit (CAS)
        if existing:
            new_count = existing.count + amount
            if new_count > limit:
                return False, existing.count, limit
            existing.count = new_count
            if cost_brl_cents:
                existing.cost_brl_cents = (existing.cost_brl_cents or 0) + cost_brl_cents
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            return True, new_count, limit
        else:
            # Primeira vez: amount tem que caber dentro do limit
            if amount > limit:
                return False, 0, limit
            db.add(models.TenantUsageCounter(
                tenant_id=tenant_id, period_yyyymm=yyyymm, kind=kind,
                count=amount, cost_brl_cents=cost_brl_cents,
            ))
            db.commit()
            return True, amount, limit
    finally:
        if own_session:
            db.close()


def refund_quota(
    tenant_id: str,
    kind: str,
    amount: int = 1,
    *,
    reason: str = "",
    db_session=None,
) -> tuple[bool, int, int]:
    """
    Devolve cota (decrementa counter). Usado quando ação que consumiu falhou.
    Nunca vai abaixo de 0.
    """
    if kind not in VALID_KINDS or amount < 1:
        return True, 0, 0

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        yyyymm = _current_yyyymm()
        existing = db.query(models.TenantUsageCounter).filter_by(
            tenant_id=tenant_id, period_yyyymm=yyyymm, kind=kind,
        ).first()
        if not existing:
            return True, 0, 0
        existing.count = max(0, (existing.count or 0) - amount)
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        if reason:
            logger.info(
                "[quota.refund] tenant=%s kind=%s amount=%s reason=%s new=%s",
                tenant_id, kind, amount, reason, existing.count,
            )
        limit = plans_module.effective_quota(tenant_id, kind, db_session=db)
        return True, existing.count, limit
    finally:
        if own_session:
            db.close()


def get_usage(
    tenant_id: str,
    *,
    period_yyyymm: Optional[int] = None,
    db_session=None,
) -> dict[str, dict]:
    """
    Lê uso atual sem mutar. Retorna dict {kind: {count, limit, pct, cost_brl_cents}}.
    """
    period_yyyymm = period_yyyymm or _current_yyyymm()
    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        rows = db.query(models.TenantUsageCounter).filter_by(
            tenant_id=tenant_id, period_yyyymm=period_yyyymm,
        ).all()
        usage_by_kind: dict[str, dict] = {}
        # Pre-fill todos os kinds (count=0 se nunca consumiu)
        for kind in VALID_KINDS:
            limit = plans_module.effective_quota(tenant_id, kind, db_session=db)
            usage_by_kind[kind] = {
                "count": 0,
                "cost_brl_cents": 0,
                "limit": limit,
                "unlimited": limit == plans_module.UNLIMITED,
                "pct": 0.0,
                "remaining": limit if limit != plans_module.UNLIMITED else None,
            }
        for row in rows:
            if row.kind in usage_by_kind:
                limit = usage_by_kind[row.kind]["limit"]
                usage_by_kind[row.kind]["count"] = row.count or 0
                usage_by_kind[row.kind]["cost_brl_cents"] = row.cost_brl_cents or 0
                if limit != plans_module.UNLIMITED and limit > 0:
                    usage_by_kind[row.kind]["pct"] = round(
                        min(100, (row.count or 0) / limit * 100), 2
                    )
                    usage_by_kind[row.kind]["remaining"] = max(0, limit - (row.count or 0))
        return usage_by_kind
    finally:
        if own_session:
            db.close()


def reset_period(tenant_id: str, *, db_session=None) -> None:
    """
    Reset manual de cotas (admin-only). Apaga rows do período corrente.
    Cron mensal NÃO precisa chamar isso — period_yyyymm muda automaticamente.
    """
    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        yyyymm = _current_yyyymm()
        db.query(models.TenantUsageCounter).filter_by(
            tenant_id=tenant_id, period_yyyymm=yyyymm,
        ).delete()
        db.commit()
        logger.warning("[quota.reset] tenant=%s yyyymm=%s", tenant_id, yyyymm)
    finally:
        if own_session:
            db.close()

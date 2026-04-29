"""
Schema canônico de planos da Acássia (Frente 2.1).

Source-of-truth dos limites e features de cada plano. Define base estática
em código + permite override por campo via `plan_global_overrides` no DB
(admin pode aumentar limite de Pro de 5k pra 7k sem deploy).

Helpers:
    - effective_plan(tenant_id) → plan_key efetivo (override > stripe > trial > free)
    - get_plan_config(plan_key) → dict completo com overrides aplicados
    - has_quota(plan, kind, current) → bool
    - has_feature(plan, feature) → bool
    - effective_quota(tenant_id, kind) → int (base + grants ativos)
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

UNLIMITED = -1  # sentinel pra limites ilimitados


# ─── Definição base ──────────────────────────────────────────────────


PLANS: dict[str, dict] = {
    "free": {
        "label": "Grátis",
        "price_brl": 0,
        "stripe_price_id": None,
        "stripe_price_id_annual": None,
        "limits": {
            "leads_month": 50,
            "wa_msgs_month": 200,
            "gemini_tokens_month": 10_000,
            "flows": 1,
            "agents": 1,
            "wa_connections": 1,
            "team_seats": 1,
        },
        "features": {
            "branding_removed": False,
            "ab_test": False,
            "api_access": False,
            "webhooks": False,
            "custom_domain": False,
            "priority_support": False,
            "voice_cloning": False,
            "marketplace_sell": False,
        },
    },
    "starter": {
        "label": "Starter",
        "price_brl": 97,
        "stripe_price_id": "price_starter_monthly_brl",
        "stripe_price_id_annual": "price_starter_annual_brl",
        "limits": {
            "leads_month": 500,
            "wa_msgs_month": 5_000,
            "gemini_tokens_month": 100_000,
            "flows": 1,
            "agents": 1,
            "wa_connections": 1,
            "team_seats": 1,
        },
        "features": {
            "branding_removed": False,
            "ab_test": False,
            "api_access": False,
            "webhooks": False,
            "custom_domain": False,
            "priority_support": False,
            "voice_cloning": False,
            "marketplace_sell": False,
        },
    },
    "pro": {
        "label": "Pro",
        "price_brl": 197,
        "price_brl_annual": 1_894,  # 20% off vs 12*197 = 2364
        "stripe_price_id": "price_pro_monthly_brl",
        "stripe_price_id_annual": "price_pro_annual_brl",
        "limits": {
            "leads_month": 5_000,
            "wa_msgs_month": 50_000,
            "gemini_tokens_month": 1_000_000,
            "flows": 5,
            "agents": 3,
            "wa_connections": 3,
            "team_seats": 3,
        },
        "features": {
            "branding_removed": True,
            "ab_test": True,
            "api_access": False,
            "webhooks": False,
            "custom_domain": False,
            "priority_support": True,
            "voice_cloning": True,
            "marketplace_sell": True,
        },
    },
    "enterprise": {
        "label": "Enterprise",
        "price_brl": 497,
        "price_brl_annual": 4_771,
        "stripe_price_id": "price_enterprise_monthly_brl",
        "stripe_price_id_annual": "price_enterprise_annual_brl",
        "limits": {
            "leads_month": UNLIMITED,
            "wa_msgs_month": UNLIMITED,
            "gemini_tokens_month": 10_000_000,  # cap mesmo "unlimited" pra controlar custo
            "flows": UNLIMITED,
            "agents": UNLIMITED,
            "wa_connections": 10,
            "team_seats": UNLIMITED,
        },
        "features": {
            "branding_removed": True,
            "ab_test": True,
            "api_access": True,
            "webhooks": True,
            "custom_domain": True,
            "priority_support": True,
            "voice_cloning": True,
            "marketplace_sell": True,
        },
    },
}


# Ordem de "rank" pra comparar planos (e.g., is plan >= pro?)
PLAN_RANK: dict[str, int] = {"free": 0, "starter": 1, "pro": 2, "enterprise": 3}


# ─── Cache simples de overrides DB ───────────────────────────────────


_override_cache: dict[str, Any] = {"data": None, "loaded_at": None}
_CACHE_TTL_S = 60  # 1 min


def _load_db_overrides() -> dict[str, dict]:
    """
    Carrega overrides ativos do DB e organiza por plan_key. Cacheado 60s
    pra evitar query em todo lookup. Falha silenciosa → sem overrides.
    """
    now = datetime.now(timezone.utc)
    if _override_cache["data"] is not None and _override_cache["loaded_at"] is not None:
        age = (now - _override_cache["loaded_at"]).total_seconds()
        if age < _CACHE_TTL_S:
            return _override_cache["data"]

    out: dict[str, dict] = {}
    try:
        from db import models
        from db.database import SessionLocal

        db = SessionLocal()
        try:
            rows = db.query(models.PlanGlobalOverride).filter_by(active=True).all()
            for r in rows:
                plan_overrides = out.setdefault(r.plan_key, {})
                # field_path tipo "limits.leads_month" → nested
                _set_nested(plan_overrides, r.field_path.split("."), r.field_value)
        finally:
            db.close()
    except Exception as exc:  # nunca quebra fluxo principal
        logger.debug("[plans] falha carregando overrides: %s", exc)
        return _override_cache["data"] or {}

    _override_cache["data"] = out
    _override_cache["loaded_at"] = now
    return out


def _set_nested(d: dict, path: list[str], value: Any) -> None:
    cur = d
    for key in path[:-1]:
        cur = cur.setdefault(key, {})
    cur[path[-1]] = value


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def invalidate_overrides_cache() -> None:
    """Forçar reload do cache. Chamar após admin editar override."""
    _override_cache["data"] = None
    _override_cache["loaded_at"] = None


# ─── API pública ─────────────────────────────────────────────────────


def get_plan_config(plan_key: str) -> dict:
    """
    Retorna config do plano com overrides do DB aplicados. Plan inválido
    cai pra free com warning.
    """
    if plan_key not in PLANS:
        logger.warning("[plans] plan_key desconhecido '%s' — fallback free", plan_key)
        plan_key = "free"
    base = PLANS[plan_key]
    overrides = _load_db_overrides().get(plan_key, {})
    if not overrides:
        return copy.deepcopy(base)
    return _deep_merge(base, overrides)


def all_public_plans() -> list[dict]:
    """Retorna lista pública (pra frontend pricing) — exclui 'free'."""
    return [
        {**get_plan_config(k), "key": k}
        for k in ("starter", "pro", "enterprise")
    ]


def has_quota(plan_key: str, kind: str, current: int) -> bool:
    """True se ainda tem quota disponível (current < limit), ou unlimited."""
    cfg = get_plan_config(plan_key)
    limit = cfg["limits"].get(kind)
    if limit is None:
        logger.warning("[plans] kind desconhecido '%s' em plan '%s'", kind, plan_key)
        return True  # fail open pra não bloquear
    if limit == UNLIMITED:
        return True
    return current < limit


def has_feature(plan_key: str, feature: str) -> bool:
    """True se o plano tem a feature ligada."""
    cfg = get_plan_config(plan_key)
    return bool(cfg["features"].get(feature, False))


def plan_rank(plan_key: str) -> int:
    """Ordem numérica (free=0, enterprise=3) pra comparações."""
    return PLAN_RANK.get(plan_key, -1)


def is_plan_at_least(plan_key: str, min_plan: str) -> bool:
    """is_plan_at_least(user_plan, 'pro') → True se user tem Pro ou Enterprise."""
    return plan_rank(plan_key) >= plan_rank(min_plan)


# ─── Effective plan (override > stripe > trial > free) ───────────────


def effective_plan(tenant_id: str, *, db_session=None) -> tuple[str, str]:
    """
    Retorna (plan_key, source) onde source ∈ {override, stripe, trial, free}.

    Ordem de precedência (Frente 1.5 + 2.19):
        1. Override admin ativo (TenantPlanOverride não-revoked, não-expirado)
        2. Stripe subscription ativa (lookup placeholder — implementar quando
           subscription tracking estiver hooked)
        3. Trial não expirado (users.trial_ends_at > now)
        4. Free
    """
    from db import models
    from db.database import SessionLocal

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # 1. Override
        override = (
            db.query(models.TenantPlanOverride)
            .filter(
                models.TenantPlanOverride.tenant_id == tenant_id,
                models.TenantPlanOverride.revoked_at.is_(None),
            )
            .order_by(models.TenantPlanOverride.created_at.desc())
            .first()
        )
        if override and (override.expires_at is None or override.expires_at > now):
            return override.plan, "override"

        # 2. Stripe (placeholder — TODO: tabela tenant_billing quando 2.16 estiver pronto)

        # 3. Trial
        user = db.query(models.User).filter_by(tenant_id=tenant_id, is_active=True).first()
        if user and user.trial_ends_at and user.trial_ends_at > now:
            return "pro", "trial"

        # 4. Free
        return "free", "free"
    finally:
        if own_session:
            db.close()


def effective_quota(tenant_id: str, kind: str, *, db_session=None) -> int:
    """
    Quota efetiva = base do plano + grants ativos (TenantQuotaGrant não-expirado).
    Retorna -1 (UNLIMITED) se plano é unlimited pra esse kind.
    """
    from db import models
    from db.database import SessionLocal

    plan_key, _ = effective_plan(tenant_id, db_session=db_session)
    base = get_plan_config(plan_key)["limits"].get(kind, 0)
    if base == UNLIMITED:
        return UNLIMITED

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        grants_total = (
            db.query(models.TenantQuotaGrant)
            .filter(
                models.TenantQuotaGrant.tenant_id == tenant_id,
                models.TenantQuotaGrant.kind == kind,
            )
            .filter(
                (models.TenantQuotaGrant.expires_at.is_(None))
                | (models.TenantQuotaGrant.expires_at > now)
            )
            .all()
        )
        extra = sum(g.amount for g in grants_total)
        return base + extra
    finally:
        if own_session:
            db.close()

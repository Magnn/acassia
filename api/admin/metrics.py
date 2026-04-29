"""
Métricas de negócio (Frente 1.14): MRR, churn, LTV, ARPU, cohort retention.

Endpoints:
    GET /api/admin/metrics/summary        — cards top (MRR, tenants ativos, churn, ARPU, LTV)
    GET /api/admin/metrics/mrr-history    — série temporal de MRR (mensal)
    GET /api/admin/metrics/cohort         — heatmap retenção por cohort de signup
    GET /api/admin/metrics/funnel         — signup → activation → 1st_msg → 1st_sale → renew_30d
    GET /api/admin/metrics/top-tenants    — top N por MRR / por uso de tokens

NOTA: Esta primeira versão usa cálculos heurísticos baseados nos dados
disponíveis (users + leads + mensagens + plan overrides). Quando Stripe
estiver totalmente integrado (Frente 2.16), a fonte primária de MRR vai
mudar pra subscriptions reais.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import func, or_

from api.admin.guard import require_admin
from db import models
from db.database import SessionLocal
import plans as plans_module


logger = logging.getLogger(__name__)
metrics_bp = Blueprint("admin_metrics_v2", __name__, url_prefix="/api/admin/metrics")


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _compute_tenant_mrr(user: models.User, db) -> tuple[int, str]:
    """
    Retorna (mrr_brl_cents, source) pra um tenant.
    Override "comp" (pauses_stripe=True) → MRR=0 (shadow MRR).
    Caso contrário, usa preço do plano efetivo.
    """
    plan_key, source = plans_module.effective_plan(user.tenant_id, db_session=db)
    if source == "override":
        # Comp gratuito (pausa Stripe) NÃO conta como MRR
        ovr = (
            db.query(models.TenantPlanOverride)
            .filter(
                models.TenantPlanOverride.tenant_id == user.tenant_id,
                models.TenantPlanOverride.revoked_at.is_(None),
            )
            .order_by(models.TenantPlanOverride.created_at.desc())
            .first()
        )
        if ovr and ovr.pauses_stripe:
            return 0, "override_comp"
    if source in ("trial", "free"):
        return 0, source
    cfg = plans_module.get_plan_config(plan_key)
    return int(cfg.get("price_brl", 0)) * 100, source  # cents


@metrics_bp.route("/summary", methods=["GET"])
@login_required
@require_admin
def metrics_summary():
    """Cards top: MRR atual + Δ vs mês passado, ARPU, churn, total tenants."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_period_start = (period_start - timedelta(days=1)).replace(day=1)

        # Tenants ativos = users.is_active=true, deleted_at=null
        active_users = db.query(models.User).filter(
            models.User.is_active == True,  # noqa: E712
            models.User.deleted_at.is_(None),
        ).all()

        # Soma MRR por user
        mrr_total_cents = 0
        plans_distribution: dict[str, int] = {}
        for u in active_users:
            mrr_cents, _ = _compute_tenant_mrr(u, db)
            mrr_total_cents += mrr_cents
            plan_key, _ = plans_module.effective_plan(u.tenant_id, db_session=db)
            plans_distribution[plan_key] = plans_distribution.get(plan_key, 0) + 1

        # Active tenants count (com plano pago — não trial nem free)
        paying_count = sum(1 for u in active_users if _compute_tenant_mrr(u, db)[0] > 0)

        # Tenants signup recentes
        new_30d = sum(1 for u in active_users if _aware(u.criado_em) and _aware(u.criado_em) > month_ago)

        # Churn aproximado: deleted_at OR suspended_at nos últimos 30d
        churned_30d = db.query(func.count(models.User.id)).filter(
            or_(
                models.User.deleted_at >= month_ago,
                models.User.suspended_at >= month_ago,
            )
        ).scalar() or 0

        # ARPU = MRR / paying_count
        arpu_brl_cents = (mrr_total_cents / paying_count) if paying_count > 0 else 0

        # Churn rate aproximado: churned / (active_30d_ago)
        # Como aproximação: active_users + churned como base
        denom = paying_count + churned_30d
        churn_rate_pct = (churned_30d / denom * 100) if denom > 0 else 0

        # LTV estimado (simplificado): ARPU / churn_rate_mensal
        # Se churn=0, retorna 'unbounded'
        if churn_rate_pct > 0:
            ltv_brl_cents = arpu_brl_cents / (churn_rate_pct / 100)
        else:
            ltv_brl_cents = None  # unbounded com dados atuais

        # Trial expirando próximos 7 dias
        trial_expiring_7d = db.query(func.count(models.User.id)).filter(
            models.User.trial_ends_at.isnot(None),
            models.User.trial_ends_at > now,
            models.User.trial_ends_at <= now + timedelta(days=7),
            models.User.is_active == True,  # noqa: E712
            models.User.deleted_at.is_(None),
        ).scalar() or 0

        # Dunning ativos
        dunning_count = db.query(func.count(models.User.id)).filter(
            models.User.dunning_status.isnot(None),
            models.User.dunning_status != "",
        ).scalar() or 0

        return jsonify({
            "mrr_brl_cents": mrr_total_cents,
            "mrr_brl": mrr_total_cents / 100,
            "active_tenants": len(active_users),
            "paying_tenants": paying_count,
            "new_signups_30d": new_30d,
            "churned_30d": churned_30d,
            "churn_rate_30d_pct": round(churn_rate_pct, 2),
            "arpu_brl_cents": int(arpu_brl_cents),
            "arpu_brl": round(arpu_brl_cents / 100, 2),
            "ltv_brl_cents": int(ltv_brl_cents) if ltv_brl_cents is not None else None,
            "ltv_brl": round(ltv_brl_cents / 100, 2) if ltv_brl_cents is not None else None,
            "ltv_unbounded": ltv_brl_cents is None,
            "trial_expiring_7d": trial_expiring_7d,
            "dunning_count": dunning_count,
            "plans_distribution": plans_distribution,
            "computed_at": now.isoformat(),
        })
    finally:
        db.close()


@metrics_bp.route("/mrr-history", methods=["GET"])
@login_required
@require_admin
def mrr_history():
    """
    Série mensal de MRR pelos últimos N meses.
    Cada ponto: snapshot do MRR no fim do mês (aproximação heurística).

    Limitação V1: como não temos histórico diário de subscriptions,
    o "MRR" passado é aproximado: MRR_M = sum(plan_price) pra users
    que estavam ativos naquele mês.
    """
    months = min(int(request.args.get("months") or 12), 24)
    db = SessionLocal()
    try:
        users = db.query(models.User).filter(models.User.deleted_at.is_(None)).all()
        history = []
        now = datetime.now(timezone.utc)
        for i in range(months - 1, -1, -1):
            # Fim do mês i atrás
            month_end = (now.replace(day=1) - timedelta(days=i * 30))
            label = month_end.strftime("%Y-%m")

            mrr_cents = 0
            count_active = 0
            for u in users:
                criado = _aware(u.criado_em)
                deleted = _aware(u.deleted_at)
                # Estava ativo naquele mês?
                if criado and criado > month_end:
                    continue
                if deleted and deleted < month_end:
                    continue
                # Snapshot heurístico: assume plano atual pra meses passados
                # (ideal: histórico subscriptions; TODO Frente 2.16)
                cents, src = _compute_tenant_mrr(u, db)
                mrr_cents += cents
                if cents > 0:
                    count_active += 1

            history.append({
                "month": label,
                "mrr_brl_cents": mrr_cents,
                "mrr_brl": mrr_cents / 100,
                "paying_tenants": count_active,
            })
        return jsonify({"history": history, "months": months})
    finally:
        db.close()


@metrics_bp.route("/cohort", methods=["GET"])
@login_required
@require_admin
def cohort_retention():
    """
    Heatmap retention: tenants signup mês M → % retidos M+1, M+2, ...

    "Retido" = ainda não-deleted no fim do mês N.
    """
    months = min(int(request.args.get("months") or 12), 12)
    db = SessionLocal()
    try:
        users = db.query(models.User).order_by(models.User.criado_em.asc()).all()

        # Agrupa por cohort (mês de signup)
        cohorts: dict[str, list[models.User]] = {}
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=months * 31)

        for u in users:
            criado = _aware(u.criado_em)
            if criado is None or criado < cutoff:
                continue
            label = criado.strftime("%Y-%m")
            cohorts.setdefault(label, []).append(u)

        # Calcula retenção pra cada cohort × N meses
        out = []
        for cohort_label in sorted(cohorts.keys()):
            cohort_users = cohorts[cohort_label]
            cohort_size = len(cohort_users)
            cohort_start = datetime.strptime(cohort_label + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)

            row = {
                "cohort": cohort_label,
                "size": cohort_size,
                "retention": [],
                "low_confidence": cohort_size < 10,
            }
            for n in range(months):
                check_date = cohort_start + timedelta(days=(n + 1) * 30)
                if check_date > now:
                    row["retention"].append(None)  # mês ainda não chegou
                    continue
                retained = 0
                for u in cohort_users:
                    deleted = _aware(u.deleted_at)
                    suspended = _aware(u.suspended_at)
                    if deleted and deleted < check_date:
                        continue
                    if suspended and suspended < check_date:
                        continue
                    retained += 1
                row["retention"].append({
                    "month_offset": n,
                    "retained": retained,
                    "pct": round(retained / cohort_size * 100, 1) if cohort_size > 0 else 0,
                })
            out.append(row)

        return jsonify({"cohorts": out, "months_tracked": months})
    finally:
        db.close()


@metrics_bp.route("/funnel", methods=["GET"])
@login_required
@require_admin
def activation_funnel():
    """
    Funnel principal:
        signup → trial_started → wa_connected → first_msg_sent → first_lead → first_sale → renew_30d

    Definições V1 (heurísticas):
        - signup: user criado
        - trial_started: tem trial_started_at
        - first_msg_sent: tem >=1 mensagem outbound (remetente='bot')
        - first_lead: tem >=1 lead
        - first_sale: tem >=1 PaymentEventReceipt
        - renew_30d: still active 30d depois do signup

    Filtro temporal: últimos 90d de signups.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=90)

        users = db.query(models.User).filter(
            models.User.criado_em >= since,
        ).all()

        signup_count = len(users)
        trial_count = sum(1 for u in users if u.trial_started_at is not None)

        # First msg sent: tenant tem mensagem de bot
        tenant_ids_with_msg = set(
            row[0] for row in db.query(models.Lead.tenant_id).join(
                models.Mensagem, models.Mensagem.lead_id == models.Lead.id,
            ).filter(
                models.Lead.tenant_id.in_([u.tenant_id for u in users]),
                models.Mensagem.remetente == "bot",
            ).distinct().all()
        )
        first_msg_count = sum(1 for u in users if u.tenant_id in tenant_ids_with_msg)

        # First lead
        tenant_ids_with_lead = set(
            row[0] for row in db.query(models.Lead.tenant_id).filter(
                models.Lead.tenant_id.in_([u.tenant_id for u in users]),
            ).distinct().all()
        )
        first_lead_count = sum(1 for u in users if u.tenant_id in tenant_ids_with_lead)

        # First sale
        tenant_ids_with_sale = set(
            row[0] for row in db.query(models.PaymentEventReceipt.tenant_id).filter(
                models.PaymentEventReceipt.tenant_id.in_([u.tenant_id for u in users]),
            ).distinct().all()
        )
        first_sale_count = sum(1 for u in users if u.tenant_id in tenant_ids_with_sale)

        # Renew 30d: ativo + signup > 30d
        renew_count = sum(
            1 for u in users
            if u.is_active and u.deleted_at is None
            and _aware(u.criado_em) and _aware(u.criado_em) < now - timedelta(days=30)
        )

        steps = [
            {"key": "signup", "label": "Signup", "count": signup_count, "pct_total": 100.0},
            {"key": "trial_started", "label": "Trial iniciado", "count": trial_count},
            {"key": "first_msg", "label": "1ª msg enviada", "count": first_msg_count},
            {"key": "first_lead", "label": "1º lead capturado", "count": first_lead_count},
            {"key": "first_sale", "label": "1ª venda", "count": first_sale_count},
            {"key": "renew_30d", "label": "Renovou 30d+", "count": renew_count},
        ]
        # Computa pct_total + drop_pct
        for i, s in enumerate(steps):
            s["pct_total"] = round(s["count"] / signup_count * 100, 1) if signup_count > 0 else 0
            if i > 0:
                prev = steps[i - 1]["count"]
                s["drop_pct"] = round((prev - s["count"]) / prev * 100, 1) if prev > 0 else 0

        return jsonify({
            "steps": steps,
            "period_days": 90,
            "computed_at": now.isoformat(),
        })
    finally:
        db.close()


@metrics_bp.route("/top-tenants", methods=["GET"])
@login_required
@require_admin
def top_tenants():
    """
    Top tenants por:
        - mrr (mais valor)
        - msgs_30d (mais uso WhatsApp)
        - leads_30d (mais leads)
    """
    by = request.args.get("by") or "mrr"
    limit = min(int(request.args.get("limit") or 10), 50)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        since_30d = now - timedelta(days=30)

        users = db.query(models.User).filter(
            models.User.is_active == True,  # noqa: E712
            models.User.deleted_at.is_(None),
        ).all()

        rows = []
        for u in users:
            mrr_cents, _ = _compute_tenant_mrr(u, db)
            leads_30d = db.query(func.count(models.Lead.id)).filter(
                models.Lead.tenant_id == u.tenant_id,
                models.Lead.criado_em > since_30d,
            ).scalar() or 0
            msgs_30d = db.query(func.count(models.Mensagem.id)).join(
                models.Lead, models.Mensagem.lead_id == models.Lead.id,
            ).filter(
                models.Lead.tenant_id == u.tenant_id,
                models.Mensagem.timestamp > since_30d,
            ).scalar() or 0
            rows.append({
                "tenant_id": u.tenant_id,
                "user_id": u.id,
                "email": u.email,
                "name": u.name,
                "mrr_brl": mrr_cents / 100,
                "leads_30d": leads_30d,
                "msgs_30d": msgs_30d,
            })

        if by == "mrr":
            rows.sort(key=lambda r: r["mrr_brl"], reverse=True)
        elif by == "msgs_30d":
            rows.sort(key=lambda r: r["msgs_30d"], reverse=True)
        elif by == "leads_30d":
            rows.sort(key=lambda r: r["leads_30d"], reverse=True)

        return jsonify({"tenants": rows[:limit], "ordered_by": by})
    finally:
        db.close()

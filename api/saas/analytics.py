"""
Analytics endpoints user-facing (Frente 3.26-3.34).
Privado por tenant via current_user.tenant_id.

Endpoints:
    GET /saas/analytics/funnel?flow_id=&flow_slug=&period_days=30&score_band=hot
    GET /saas/analytics/flows                        — lista fluxos com visitas
    GET /saas/analytics/leads/by-score              — distribuição hot/warm/cold
    GET /saas/analytics/recovery-suggestions        — leads inativos elegíveis
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
analytics_bp = Blueprint("saas_analytics", __name__, url_prefix="/saas/analytics")


@analytics_bp.route("/funnel", methods=["GET"])
@login_required
def funnel():
    import funnel_analytics
    flow_id_arg = request.args.get("flow_id")
    flow_slug = request.args.get("flow_slug") or None
    period_days = min(int(request.args.get("period_days") or 30), 365)
    score_band = request.args.get("score_band") or None

    flow_id = None
    if flow_id_arg and flow_id_arg.isdigit():
        flow_id = int(flow_id_arg)

    if not flow_id and not flow_slug:
        return jsonify({"error": "flow_id_or_slug_required"}), 422

    return jsonify(funnel_analytics.funnel_for_flow(
        tenant_id=current_user.tenant_id,
        flow_id=flow_id,
        flow_slug=flow_slug,
        period_days=period_days,
        score_band=score_band,
    ))


@analytics_bp.route("/flows", methods=["GET"])
@login_required
def list_flows():
    import funnel_analytics
    period_days = min(int(request.args.get("period_days") or 30), 365)
    return jsonify({
        "flows": funnel_analytics.list_flows_with_visits(
            current_user.tenant_id, period_days=period_days,
        ),
        "period_days": period_days,
    })


@analytics_bp.route("/leads/by-score", methods=["GET"])
@login_required
def leads_by_score():
    """Distribuição hot/warm/cold pra dashboard pie chart."""
    db = SessionLocal()
    try:
        rows = db.query(
            models.Lead.score_band,
            func.count(models.Lead.id),
        ).filter(
            models.Lead.tenant_id == current_user.tenant_id,
        ).group_by(models.Lead.score_band).all()

        distribution = {"hot": 0, "warm": 0, "cold": 0}
        for band, count in rows:
            if band in distribution:
                distribution[band] = count

        return jsonify({
            "distribution": distribution,
            "total": sum(distribution.values()),
        })
    finally:
        db.close()


@analytics_bp.route("/recovery-suggestions", methods=["GET"])
@login_required
def recovery_suggestions():
    """
    Lista leads inativos potencialmente recuperáveis (Frente 3.32).
    Critério: última msg > 3 dias E < 30 dias E não-convertido E não opt-out.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        cutoff_lower = now - timedelta(days=30)
        cutoff_upper = now - timedelta(days=3)

        # Subquery: timestamp da última msg por lead
        subq = (
            db.query(
                models.Mensagem.lead_id,
                func.max(models.Mensagem.timestamp).label("last_ts"),
            )
            .group_by(models.Mensagem.lead_id)
            .subquery()
        )

        leads = (
            db.query(models.Lead, subq.c.last_ts)
            .join(subq, subq.c.lead_id == models.Lead.id)
            .filter(
                models.Lead.tenant_id == current_user.tenant_id,
                models.Lead.convertido == False,  # noqa: E712
                models.Lead.opt_out == False,  # noqa: E712
                subq.c.last_ts >= cutoff_lower,
                subq.c.last_ts <= cutoff_upper,
            )
            .order_by(models.Lead.score_value.desc())
            .limit(50)
            .all()
        )

        items = []
        for lead, last_ts in leads:
            items.append({
                "id": lead.id,
                "telefone": lead.telefone,
                "nome": lead.nome,
                "score_value": lead.score_value,
                "score_band": lead.score_band,
                "node_atual": lead.node_atual,
                "last_msg_at": last_ts.isoformat() if last_ts else None,
                "days_inactive": (now - last_ts.replace(tzinfo=timezone.utc) if last_ts.tzinfo is None else now - last_ts).days if last_ts else 0,
            })

        return jsonify({
            "items": items,
            "total": len(items),
            "criteria": {
                "min_days_inactive": 3,
                "max_days_inactive": 30,
            },
        })
    finally:
        db.close()

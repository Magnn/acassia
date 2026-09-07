"""
Métricas SaaS — KPIs por tenant + dados pra gráfico (Chart.js).

Endpoints:
    GET  /saas/metrics            — dashboard com KPIs

Computa em queries SQLAlchemy diretas — sem agregação pesada por enquanto.
Ver SAAS_ROADMAP Fase 6 pra cohort/LTV/funnel mais profundos.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

metrics_bp = Blueprint("saas_metrics", __name__, url_prefix="/saas/metrics")


def compute_kpis(tenant_id: str) -> dict:
    """KPIs base do tenant. Computa em queries diretas."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        total_leads = db.query(models.Lead).filter_by(tenant_id=tenant_id).count()
        leads_7d = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.criado_em >= seven_days_ago,
        ).count()
        leads_30d = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.criado_em >= thirty_days_ago,
        ).count()
        convertidos = db.query(models.Lead).filter_by(
            tenant_id=tenant_id, convertido=True,
        ).count()
        ativas = db.query(models.Lead).filter_by(
            tenant_id=tenant_id, opt_out=False, convertido=False,
        ).count()
        pausadas = db.query(models.Lead).filter_by(
            tenant_id=tenant_id, bot_pausado=True,
        ).count()
        opt_out = db.query(models.Lead).filter_by(
            tenant_id=tenant_id, opt_out=True,
        ).count()

        conversion_rate = round(convertidos / total_leads * 100, 1) if total_leads else 0.0

        # Distribuição por node_atual (top 5)
        from sqlalchemy import func
        node_counts_raw = (
            db.query(models.Lead.node_atual, func.count(models.Lead.id))
            .filter_by(tenant_id=tenant_id)
            .group_by(models.Lead.node_atual)
            .order_by(func.count(models.Lead.id).desc())
            .limit(5)
            .all()
        )
        node_distribution = [
            {"node": (n or "—")[:40], "count": c}
            for (n, c) in node_counts_raw
        ]

        return {
            "total_leads": total_leads,
            "leads_7d": leads_7d,
            "leads_30d": leads_30d,
            "convertidos": convertidos,
            "ativas": ativas,
            "pausadas": pausadas,
            "opt_out": opt_out,
            "conversion_rate": conversion_rate,
            "node_distribution": node_distribution,
        }
    finally:
        db.close()


@metrics_bp.route("/", methods=["GET"])
@login_required
def dashboard():
    tenant_id = current_user.tenant_id
    kpis = compute_kpis(tenant_id)
    return render_template("metrics/dashboard.html", kpis=kpis)


@metrics_bp.route("/data", methods=["GET"])
@login_required
def dashboard_data():
    """Endpoint REST para consumo do novo React Dashboard."""
    from flask import jsonify
    tenant_id = current_user.tenant_id
    kpis = compute_kpis(tenant_id)
    return jsonify(kpis)

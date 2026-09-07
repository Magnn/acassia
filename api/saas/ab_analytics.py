"""
api/saas/ab_analytics.py — A/B Test Analytics & Reporting
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints:
    GET  /saas/ab/<blueprint_id>/analytics   — Report por flow (todos os nós AB)
    GET  /saas/ab/<blueprint_id>/node/<node_id>/analytics  — Report por nó específico
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, case

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

ab_bp = Blueprint("ab_analytics", __name__, url_prefix="/saas/ab")


@ab_bp.route("/<int:blueprint_id>/analytics", methods=["GET"])
@login_required
def flow_ab_analytics(blueprint_id: int):
    """
    Retorna analytics de todos os nós A/B de um flow.

    Response:
    {
        "blueprint_id": 42,
        "nodes": {
            "node_xyz": {
                "node_id": "node_xyz",
                "variants": {
                    "A": {"impressions": 500, "conversions": 12, "rate": 2.4, "revenue": 1800.0},
                    "B": {"impressions": 500, "conversions": 45, "rate": 9.0, "revenue": 6750.0}
                },
                "winner": "B",
                "confidence": "high",
                "total_impressions": 1000,
                "total_revenue": 8550.0
            }
        }
    }
    """
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        # Verify blueprint belongs to tenant
        bp = db.query(models.FlowBlueprint).filter_by(
            id=blueprint_id, tenant_id=tenant_id,
        ).first()
        if not bp:
            return jsonify({"error": "blueprint_not_found"}), 404

        # Aggregate by node_id + variant
        rows = db.query(
            models.ABTestExposure.node_id,
            models.ABTestExposure.variant,
            func.count(models.ABTestExposure.id).label("impressions"),
            func.sum(
                case((models.ABTestExposure.converted == True, 1), else_=0)  # noqa: E712
            ).label("conversions"),
            func.sum(
                case(
                    (models.ABTestExposure.converted == True, models.ABTestExposure.conversion_value),  # noqa: E712
                    else_=0,
                )
            ).label("revenue"),
        ).filter(
            models.ABTestExposure.tenant_id == tenant_id,
            models.ABTestExposure.blueprint_id == blueprint_id,
        ).group_by(
            models.ABTestExposure.node_id,
            models.ABTestExposure.variant,
        ).all()

        # Build response grouped by node
        nodes: dict = {}
        for row in rows:
            nid = row.node_id
            if nid not in nodes:
                nodes[nid] = {
                    "node_id": nid,
                    "variants": {},
                    "total_impressions": 0,
                    "total_revenue": 0.0,
                }
            impr = int(row.impressions or 0)
            conv = int(row.conversions or 0)
            rev = float(row.revenue or 0)
            rate = round((conv / impr * 100) if impr > 0 else 0, 2)
            nodes[nid]["variants"][row.variant] = {
                "impressions": impr,
                "conversions": conv,
                "rate": rate,
                "revenue": round(rev, 2),
            }
            nodes[nid]["total_impressions"] += impr
            nodes[nid]["total_revenue"] += rev

        # Determine winner for each node
        for nid, data in nodes.items():
            va = data["variants"].get("A", {})
            vb = data["variants"].get("B", {})
            rate_a = va.get("rate", 0)
            rate_b = vb.get("rate", 0)
            imp_a = va.get("impressions", 0)
            imp_b = vb.get("impressions", 0)

            if rate_a > rate_b and rate_a > 0:
                data["winner"] = "A"
            elif rate_b > rate_a and rate_b > 0:
                data["winner"] = "B"
            else:
                data["winner"] = None

            # Simple confidence heuristic (not Z-test, but good enough for SaaS)
            total = imp_a + imp_b
            if total >= 200 and abs(rate_a - rate_b) > 2.0:
                data["confidence"] = "high"
            elif total >= 50 and abs(rate_a - rate_b) > 1.0:
                data["confidence"] = "medium"
            else:
                data["confidence"] = "low"

            data["total_revenue"] = round(data["total_revenue"], 2)

        return jsonify({
            "blueprint_id": blueprint_id,
            "nodes": nodes,
        })
    finally:
        db.close()


@ab_bp.route("/<int:blueprint_id>/node/<node_id>/analytics", methods=["GET"])
@login_required
def node_ab_analytics(blueprint_id: int, node_id: str):
    """Detailed analytics for a specific A/B node including recent exposures."""
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        # Aggregate stats
        rows = db.query(
            models.ABTestExposure.variant,
            func.count(models.ABTestExposure.id).label("impressions"),
            func.sum(
                case((models.ABTestExposure.converted == True, 1), else_=0)  # noqa: E712
            ).label("conversions"),
            func.sum(
                case(
                    (models.ABTestExposure.converted == True, models.ABTestExposure.conversion_value),  # noqa: E712
                    else_=0,
                )
            ).label("revenue"),
        ).filter(
            models.ABTestExposure.tenant_id == tenant_id,
            models.ABTestExposure.blueprint_id == blueprint_id,
            models.ABTestExposure.node_id == node_id,
        ).group_by(models.ABTestExposure.variant).all()

        variants = {}
        for row in rows:
            impr = int(row.impressions or 0)
            conv = int(row.conversions or 0)
            rev = float(row.revenue or 0)
            variants[row.variant] = {
                "impressions": impr,
                "conversions": conv,
                "rate": round((conv / impr * 100) if impr > 0 else 0, 2),
                "revenue": round(rev, 2),
            }

        # Recent exposures (last 20)
        recent = db.query(models.ABTestExposure).filter(
            models.ABTestExposure.tenant_id == tenant_id,
            models.ABTestExposure.blueprint_id == blueprint_id,
            models.ABTestExposure.node_id == node_id,
        ).order_by(models.ABTestExposure.exposed_at.desc()).limit(20).all()

        return jsonify({
            "node_id": node_id,
            "blueprint_id": blueprint_id,
            "variants": variants,
            "recent": [{
                "lead_id": e.lead_id,
                "variant": e.variant,
                "converted": e.converted,
                "conversion_value": e.conversion_value,
                "exposed_at": e.exposed_at.isoformat() if e.exposed_at else None,
                "converted_at": e.converted_at.isoformat() if e.converted_at else None,
            } for e in recent],
        })
    finally:
        db.close()

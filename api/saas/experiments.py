"""
A/B testing API (Frente 3.28-3.29).

Endpoints:
    GET    /saas/experiments               — lista do tenant (com stats live)
    POST   /saas/experiments               — cria
    GET    /saas/experiments/<id>          — detail + evaluate live
    PATCH  /saas/experiments/<id>          — pausa, ajusta split, promove manual
    POST   /saas/experiments/<id>/promote  — promove vencedora pro fluxo
    DELETE /saas/experiments/<id>          — encerra (status=stopped_manual)
    POST   /saas/experiments/<id>/conversion — registra conversao manual

Limit: max 3 experimentos `running` por flow_id (enforcement no POST).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
import flow_experiments as fx


logger = logging.getLogger(__name__)
exp_bp = Blueprint("saas_experiments", __name__, url_prefix="/saas/experiments")


VALID_WINNING_EVENTS = {"responded", "clicked", "paid", "custom"}
MAX_RUNNING_PER_FLOW = 3


def _serialize(exp: models.FlowNodeExperiment, *, with_stats: bool = False, db=None) -> dict:
    out = {
        "id": exp.id,
        "tenant_id": exp.tenant_id,
        "flow_id": exp.flow_id,
        "flow_slug": exp.flow_slug,
        "node_id": exp.node_id,
        "name": exp.name,
        "variant_a_text": exp.variant_a_text,
        "variant_b_text": exp.variant_b_text,
        "split_pct": exp.split_pct,
        "winning_event": exp.winning_event,
        "min_sample_size": exp.min_sample_size,
        "confidence_threshold": exp.confidence_threshold,
        "status": exp.status,
        "winner": exp.winner,
        "p_value": exp.p_value,
        "lift_pct": exp.lift_pct,
        "started_at": exp.started_at.isoformat() if exp.started_at else None,
        "winner_picked_at": exp.winner_picked_at.isoformat() if exp.winner_picked_at else None,
        "created_at": exp.created_at.isoformat(),
    }
    if with_stats and db is not None:
        out["stats"] = fx.evaluate_experiment(exp, db)
    return out


@exp_bp.route("", methods=["GET"])
@login_required
def list_experiments():
    flow_id = request.args.get("flow_id")
    status = (request.args.get("status") or "").strip().lower() or None

    db = SessionLocal()
    try:
        q = db.query(models.FlowNodeExperiment).filter_by(
            tenant_id=current_user.tenant_id,
        )
        if flow_id and str(flow_id).isdigit():
            q = q.filter_by(flow_id=int(flow_id))
        if status:
            q = q.filter_by(status=status)
        items = q.order_by(models.FlowNodeExperiment.created_at.desc()).all()
        return jsonify({
            "items": [_serialize(e, with_stats=True, db=db) for e in items],
            "total": len(items),
        })
    finally:
        db.close()


@exp_bp.route("", methods=["POST"])
@login_required
def create_experiment():
    body = request.get_json(silent=True) or {}
    flow_id = body.get("flow_id")
    flow_slug = (body.get("flow_slug") or "").strip() or None
    node_id = (body.get("node_id") or "").strip()
    name = (body.get("name") or "").strip() or None
    variant_a = (body.get("variant_a_text") or "").strip()
    variant_b = (body.get("variant_b_text") or "").strip()
    split_pct = body.get("split_pct", 50)
    winning_event = (body.get("winning_event") or "responded").strip().lower()
    min_sample = body.get("min_sample_size", 50)

    if not node_id:
        return jsonify({"error": "node_id_required"}), 422
    if not variant_a or not variant_b:
        return jsonify({"error": "both_variants_required"}), 422
    if winning_event not in VALID_WINNING_EVENTS:
        return jsonify({"error": "winning_event_invalid"}), 422
    try:
        split_pct = int(split_pct)
        if not 5 <= split_pct <= 95:
            return jsonify({"error": "split_pct_out_of_range"}), 422
    except (TypeError, ValueError):
        return jsonify({"error": "split_pct_invalid"}), 422
    try:
        min_sample = max(20, min(int(min_sample), 1000))
    except (TypeError, ValueError):
        min_sample = 50

    db = SessionLocal()
    try:
        # Limit MAX_RUNNING_PER_FLOW
        if flow_id:
            running_count = db.query(models.FlowNodeExperiment).filter_by(
                tenant_id=current_user.tenant_id,
                flow_id=int(flow_id),
                status="running",
            ).count()
            if running_count >= MAX_RUNNING_PER_FLOW:
                return jsonify({
                    "error": "max_running_per_flow_exceeded",
                    "max": MAX_RUNNING_PER_FLOW,
                }), 409

        exp = models.FlowNodeExperiment(
            tenant_id=current_user.tenant_id,
            flow_id=int(flow_id) if flow_id else None,
            flow_slug=flow_slug,
            node_id=node_id[:120],
            name=name[:200] if name else None,
            variant_a_text=variant_a[:4000],
            variant_b_text=variant_b[:4000],
            split_pct=split_pct,
            winning_event=winning_event,
            min_sample_size=min_sample,
            created_by=current_user.id,
            status="running",
        )
        db.add(exp)
        db.commit()
        db.refresh(exp)

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="ab_test.created",
                target_type="flow_node_experiment",
                target_id=str(exp.id),
                payload={
                    "node_id": exp.node_id,
                    "flow_id": exp.flow_id,
                    "split_pct": exp.split_pct,
                },
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({"ok": True, "experiment": _serialize(exp)}), 201
    finally:
        db.close()


@exp_bp.route("/<int:exp_id>", methods=["GET"])
@login_required
def get_experiment(exp_id: int):
    db = SessionLocal()
    try:
        exp = db.query(models.FlowNodeExperiment).filter_by(
            id=exp_id, tenant_id=current_user.tenant_id,
        ).first()
        if not exp:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_serialize(exp, with_stats=True, db=db))
    finally:
        db.close()


@exp_bp.route("/<int:exp_id>", methods=["PATCH"])
@login_required
def update_experiment(exp_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        exp = db.query(models.FlowNodeExperiment).filter_by(
            id=exp_id, tenant_id=current_user.tenant_id,
        ).first()
        if not exp:
            return jsonify({"error": "not_found"}), 404

        if "split_pct" in body and exp.status == "running":
            try:
                sp = int(body["split_pct"])
                if 5 <= sp <= 95:
                    exp.split_pct = sp
            except (TypeError, ValueError):
                pass
        if "name" in body:
            n = (body["name"] or "").strip()
            exp.name = n[:200] if n else None
        if "variant_a_text" in body and exp.status == "running":
            t = (body["variant_a_text"] or "").strip()
            if t:
                exp.variant_a_text = t[:4000]
        if "variant_b_text" in body and exp.status == "running":
            t = (body["variant_b_text"] or "").strip()
            if t:
                exp.variant_b_text = t[:4000]

        db.commit()
        return jsonify({"ok": True, "experiment": _serialize(exp, with_stats=True, db=db)})
    finally:
        db.close()


@exp_bp.route("/<int:exp_id>", methods=["DELETE"])
@login_required
def stop_experiment(exp_id: int):
    db = SessionLocal()
    try:
        exp = db.query(models.FlowNodeExperiment).filter_by(
            id=exp_id, tenant_id=current_user.tenant_id,
        ).first()
        if not exp:
            return jsonify({"error": "not_found"}), 404
        if exp.status != "running":
            return jsonify({"error": "already_finalized", "status": exp.status}), 422
        exp.status = "stopped_manual"
        exp.winner_picked_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "status": exp.status})
    finally:
        db.close()


@exp_bp.route("/<int:exp_id>/promote", methods=["POST"])
@login_required
def promote_winner(exp_id: int):
    """
    Forca promocao manual de uma variante. Body: {variant: 'A'|'B'}.
    Util quando admin quer encerrar antes do auto-pick.
    """
    body = request.get_json(silent=True) or {}
    variant = (body.get("variant") or "").upper()
    if variant not in ("A", "B"):
        return jsonify({"error": "variant_invalid"}), 422

    db = SessionLocal()
    try:
        exp = db.query(models.FlowNodeExperiment).filter_by(
            id=exp_id, tenant_id=current_user.tenant_id,
        ).first()
        if not exp:
            return jsonify({"error": "not_found"}), 404

        exp.winner = variant
        exp.winner_picked_at = datetime.now(timezone.utc)
        exp.status = f"completed_winner_{variant.lower()}"

        # Calcula stats finais
        try:
            stats = fx.evaluate_experiment(exp, db)
            exp.p_value = stats.get("p_value")
            exp.lift_pct = stats.get("lift_pct")
        except Exception:
            pass

        db.commit()

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="ab_test.promoted_manual",
                target_type="flow_node_experiment",
                target_id=str(exp.id),
                payload={"variant": variant},
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({"ok": True, "experiment": _serialize(exp, with_stats=True, db=db)})
    finally:
        db.close()


@exp_bp.route("/<int:exp_id>/conversion", methods=["POST"])
@login_required
def record_manual_conversion(exp_id: int):
    """Registra conversao manual (para winning_event=custom)."""
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422

    db = SessionLocal()
    try:
        exp = db.query(models.FlowNodeExperiment).filter_by(
            id=exp_id, tenant_id=current_user.tenant_id,
        ).first()
        if not exp:
            return jsonify({"error": "not_found"}), 404

        ok = fx.record_conversion(exp_id, int(lead_id), db_session=db)
        return jsonify({"ok": ok, "experiment_id": exp_id, "lead_id": int(lead_id)})
    finally:
        db.close()

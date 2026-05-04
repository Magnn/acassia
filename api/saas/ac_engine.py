"""
api/saas/ac_engine.py — ActiveCampaign Engine (Tier 1-3 Features)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tasks, Notes, Goals, Attribution, Widget, Win Probability,
Engagement Tagging, Predictive Sending, Subscription Prefs.
"""
from __future__ import annotations
import logging, secrets
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
ac_bp = Blueprint("ac_engine", __name__, url_prefix="/saas/ac")


# ════════════════════════ TASKS ════════════════════════

@ac_bp.route("/tasks", methods=["GET"])
@login_required
def list_tasks():
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        show = request.args.get("show", "pending")  # pending, completed, all
        lead_id = request.args.get("lead_id", type=int)
        q = db.query(models.LeadTask).filter_by(tenant_id=tid)
        if lead_id:
            q = q.filter_by(lead_id=lead_id)
        if show == "pending":
            q = q.filter_by(completed=False)
        elif show == "completed":
            q = q.filter_by(completed=True)
        q = q.order_by(models.LeadTask.due_at.asc().nullslast())
        tasks = q.limit(200).all()
        overdue = 0
        now = datetime.now(timezone.utc)
        result = []
        for t in tasks:
            is_overdue = bool(t.due_at and t.due_at < now and not t.completed)
            if is_overdue:
                overdue += 1
            lead = db.query(models.Lead).filter_by(id=t.lead_id).first()
            result.append({
                "id": t.id, "lead_id": t.lead_id,
                "lead_name": lead.nome or lead.telefone if lead else "?",
                "title": t.title, "description": t.description,
                "task_type": t.task_type, "due_at": t.due_at.isoformat() if t.due_at else None,
                "completed": t.completed, "priority": t.priority,
                "is_overdue": is_overdue,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return jsonify({"tasks": result, "total": len(result), "overdue": overdue})
    finally:
        db.close()


@ac_bp.route("/tasks", methods=["POST"])
@login_required
def create_task():
    db = SessionLocal()
    try:
        data = request.json or {}
        t = models.LeadTask(
            tenant_id=current_user.tenant_id,
            lead_id=data["lead_id"],
            title=data["title"],
            description=data.get("description"),
            task_type=data.get("task_type", "follow_up"),
            due_at=datetime.fromisoformat(data["due_at"]) if data.get("due_at") else None,
            priority=data.get("priority", "medium"),
        )
        db.add(t)
        db.commit()
        return jsonify({"ok": True, "task_id": t.id}), 201
    finally:
        db.close()


@ac_bp.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    db = SessionLocal()
    try:
        t = db.query(models.LeadTask).filter_by(id=task_id, tenant_id=current_user.tenant_id).first()
        if not t:
            return jsonify({"error": "not found"}), 404
        t.completed = not t.completed
        t.completed_at = datetime.now(timezone.utc) if t.completed else None
        db.commit()
        return jsonify({"ok": True, "completed": t.completed})
    finally:
        db.close()


@ac_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    db = SessionLocal()
    try:
        t = db.query(models.LeadTask).filter_by(id=task_id, tenant_id=current_user.tenant_id).first()
        if not t:
            return jsonify({"error": "not found"}), 404
        db.delete(t)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ════════════════════════ NOTES ════════════════════════

@ac_bp.route("/notes", methods=["GET"])
@login_required
def list_notes():
    db = SessionLocal()
    try:
        lead_id = request.args.get("lead_id", type=int)
        if not lead_id:
            return jsonify({"error": "lead_id required"}), 400
        notes = (
            db.query(models.LeadNote)
            .filter_by(tenant_id=current_user.tenant_id, lead_id=lead_id)
            .order_by(models.LeadNote.created_at.desc())
            .limit(100).all()
        )
        return jsonify({"notes": [{
            "id": n.id, "content": n.content, "author_user_id": n.author_user_id,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        } for n in notes]})
    finally:
        db.close()


@ac_bp.route("/notes", methods=["POST"])
@login_required
def create_note():
    db = SessionLocal()
    try:
        data = request.json or {}
        n = models.LeadNote(
            tenant_id=current_user.tenant_id,
            lead_id=data["lead_id"],
            content=data["content"],
            author_user_id=current_user.id,
        )
        db.add(n)
        db.commit()
        return jsonify({"ok": True, "note_id": n.id}), 201
    finally:
        db.close()


@ac_bp.route("/notes/<int:note_id>", methods=["DELETE"])
@login_required
def delete_note(note_id):
    db = SessionLocal()
    try:
        n = db.query(models.LeadNote).filter_by(id=note_id, tenant_id=current_user.tenant_id).first()
        if not n:
            return jsonify({"error": "not found"}), 404
        db.delete(n)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ════════════════════════ FLOW GOALS ════════════════════════

@ac_bp.route("/goals", methods=["GET"])
@login_required
def list_goals():
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        goals = db.query(models.FlowGoal).filter_by(tenant_id=tid).all()
        result = []
        for g in goals:
            hits = db.query(func.count(models.FlowGoalHit.id)).filter_by(goal_id=g.id).scalar() or 0
            total_runs = (
                db.query(func.count(models.FlowRun.id))
                .filter_by(blueprint_id=g.blueprint_id, tenant_id=tid)
                .scalar() or 0
            )
            bp = db.query(models.FlowBlueprint).filter_by(id=g.blueprint_id).first()
            result.append({
                "id": g.id, "goal_key": g.goal_key, "goal_type": g.goal_type,
                "description": g.description, "blueprint_id": g.blueprint_id,
                "blueprint_name": bp.title if bp else "?",
                "hits": hits, "total_runs": total_runs,
                "conversion_rate": round(hits / max(total_runs, 1) * 100, 1),
            })
        return jsonify({"goals": result})
    finally:
        db.close()


@ac_bp.route("/goals", methods=["POST"])
@login_required
def create_goal():
    db = SessionLocal()
    try:
        data = request.json or {}
        g = models.FlowGoal(
            tenant_id=current_user.tenant_id,
            blueprint_id=data["blueprint_id"],
            goal_key=data["goal_key"],
            goal_type=data.get("goal_type", "converted"),
            goal_condition=data.get("goal_condition", {}),
            description=data.get("description"),
        )
        db.add(g)
        db.commit()
        return jsonify({"ok": True, "goal_id": g.id}), 201
    finally:
        db.close()


# ════════════════════════ CONVERSION ATTRIBUTION ════════════════════════

@ac_bp.route("/conversions", methods=["GET"])
@login_required
def list_conversions():
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        days = request.args.get("days", 30, type=int)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        evts = (
            db.query(models.ConversionEvent)
            .filter(
                models.ConversionEvent.tenant_id == tid,
                models.ConversionEvent.converted_at >= since,
            )
            .order_by(models.ConversionEvent.converted_at.desc())
            .limit(500).all()
        )
        # Aggregate by source
        by_source = {}
        total_value = 0.0
        for e in evts:
            key = e.source_name or e.source_type
            if key not in by_source:
                by_source[key] = {"source": key, "type": e.source_type, "count": 0, "value": 0.0}
            by_source[key]["count"] += 1
            by_source[key]["value"] += e.value or 0
            total_value += e.value or 0

        return jsonify({
            "events": [{
                "id": e.id, "lead_id": e.lead_id,
                "source_type": e.source_type, "source_name": e.source_name,
                "value": e.value, "converted_at": e.converted_at.isoformat() if e.converted_at else None,
            } for e in evts[:50]],
            "by_source": sorted(by_source.values(), key=lambda x: x["value"], reverse=True),
            "total_conversions": len(evts),
            "total_value": round(total_value, 2),
            "period_days": days,
        })
    finally:
        db.close()


@ac_bp.route("/conversions", methods=["POST"])
@login_required
def register_conversion():
    db = SessionLocal()
    try:
        data = request.json or {}
        lead = db.query(models.Lead).filter_by(
            id=data["lead_id"], tenant_id=current_user.tenant_id
        ).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        evt = models.ConversionEvent(
            tenant_id=current_user.tenant_id,
            lead_id=data["lead_id"],
            source_type=data.get("source_type", "manual"),
            source_id=data.get("source_id"),
            source_name=data.get("source_name", "Manual"),
            value=data.get("value", 0),
            notes=data.get("notes"),
        )
        db.add(evt)

        # Update lead
        lead.convertido = True
        lead.pipeline_stage = "convertido"
        lead.conversion_source = data.get("source_name", "Manual")
        lead.conversion_at = datetime.now(timezone.utc)
        lead.deal_value = data.get("value", lead.deal_value)
        db.commit()
        return jsonify({"ok": True, "event_id": evt.id}), 201
    finally:
        db.close()


# ════════════════════════ DEAL VALUE ════════════════════════

@ac_bp.route("/deal-value", methods=["POST"])
@login_required
def set_deal_value():
    db = SessionLocal()
    try:
        data = request.json or {}
        lead = db.query(models.Lead).filter_by(
            id=data["lead_id"], tenant_id=current_user.tenant_id
        ).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        lead.deal_value = data.get("value", 0)
        db.commit()
        return jsonify({"ok": True, "deal_value": lead.deal_value})
    finally:
        db.close()


@ac_bp.route("/forecast", methods=["GET"])
@login_required
def forecast():
    """Revenue forecast based on pipeline + win probability."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        leads = db.query(models.Lead).filter(
            models.Lead.tenant_id == tid,
            models.Lead.opt_out == False,
            models.Lead.pipeline_stage != "perdido",
        ).all()

        stages = {}
        total_weighted = 0.0
        total_raw = 0.0
        for lead in leads:
            s = lead.pipeline_stage or "novo"
            if s not in stages:
                stages[s] = {"count": 0, "raw_value": 0.0, "weighted_value": 0.0}
            stages[s]["count"] += 1
            v = lead.deal_value or 0
            stages[s]["raw_value"] += v
            wp = (lead.win_probability or 0) / 100.0
            stages[s]["weighted_value"] += v * wp
            total_raw += v
            total_weighted += v * wp

        return jsonify({
            "by_stage": stages,
            "total_pipeline_value": round(total_raw, 2),
            "weighted_forecast": round(total_weighted, 2),
            "total_leads": len(leads),
        })
    finally:
        db.close()


# ════════════════════════ WIN PROBABILITY ════════════════════════

@ac_bp.route("/win-probability/recalc", methods=["POST"])
@login_required
def recalc_win_probability():
    """Recalculate win probability for all leads."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        leads = db.query(models.Lead).filter_by(tenant_id=tid, opt_out=False).all()
        updated = 0
        for lead in leads:
            prob = _calc_win_probability(lead, db)
            if lead.win_probability != prob:
                lead.win_probability = prob
                updated += 1
        db.commit()
        return jsonify({"ok": True, "updated": updated, "total": len(leads)})
    finally:
        db.close()


STAGE_WEIGHTS = {
    "novo": 5, "em_conversa": 15, "interessado": 35,
    "proposta": 55, "agendado": 75, "convertido": 100, "perdido": 0,
}


def _calc_win_probability(lead, db) -> int:
    score = 0
    # Stage weight (0-40 pts)
    stage = lead.pipeline_stage or "novo"
    score += STAGE_WEIGHTS.get(stage, 5) * 0.4
    # Engagement score (0-20 pts)
    score += min((lead.score_value or 0) / 5, 20)
    # Tags intent (0-15 pts)
    tags = lead.tags or []
    if any(t.startswith("intent:") for t in tags):
        score += 15
    # Response speed (0-15 pts)
    if lead.avg_response_time_min is not None:
        if lead.avg_response_time_min < 5:
            score += 15
        elif lead.avg_response_time_min < 30:
            score += 10
        elif lead.avg_response_time_min < 120:
            score += 5
    # Message volume (0-10 pts)
    msg_count = db.query(func.count(models.Mensagem.id)).filter_by(lead_id=lead.id).scalar() or 0
    score += min(msg_count / 2, 10)
    return min(int(score), 100)


# ════════════════════════ ENGAGEMENT TAGGING ════════════════════════

@ac_bp.route("/engagement/recalc", methods=["POST"])
@login_required
def recalc_engagement():
    """Recalculate engagement level + preferred hour + avg response time."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        leads = db.query(models.Lead).filter_by(tenant_id=tid, opt_out=False).all()
        updated = 0
        now = datetime.now(timezone.utc)

        for lead in leads:
            msgs = (
                db.query(models.Mensagem)
                .filter_by(lead_id=lead.id, origem="lead")
                .order_by(models.Mensagem.timestamp.desc())
                .limit(50).all()
            )
            if not msgs:
                lead.engagement_level = "inactive"
                continue

            # Last response
            lead.last_response_at = msgs[0].timestamp

            # Engagement level based on recency
            days_since = (now - msgs[0].timestamp).days if msgs[0].timestamp else 999
            if days_since <= 1:
                lead.engagement_level = "superfan" if len(msgs) >= 10 else "engaged"
            elif days_since <= 7:
                lead.engagement_level = "engaged"
            elif days_since <= 30:
                lead.engagement_level = "idle"
            else:
                lead.engagement_level = "inactive"

            # Preferred hour (most common hour of responses)
            hours = [m.timestamp.hour for m in msgs if m.timestamp]
            if hours:
                lead.preferred_hour = max(set(hours), key=hours.count)

            # Avg response time (time between bot message and lead reply)
            response_times = []
            all_msgs = (
                db.query(models.Mensagem)
                .filter_by(lead_id=lead.id)
                .order_by(models.Mensagem.timestamp.asc())
                .limit(100).all()
            )
            for i in range(1, len(all_msgs)):
                if all_msgs[i].origem == "lead" and all_msgs[i-1].origem != "lead":
                    if all_msgs[i].timestamp and all_msgs[i-1].timestamp:
                        delta = (all_msgs[i].timestamp - all_msgs[i-1].timestamp).total_seconds() / 60
                        if 0 < delta < 1440:  # max 24h
                            response_times.append(delta)
            if response_times:
                lead.avg_response_time_min = round(sum(response_times) / len(response_times), 1)

            updated += 1

        db.commit()
        return jsonify({"ok": True, "updated": updated})
    finally:
        db.close()


# ════════════════════════ CAPTURE WIDGET ════════════════════════

@ac_bp.route("/widgets", methods=["GET"])
@login_required
def list_widgets():
    db = SessionLocal()
    try:
        widgets = (
            db.query(models.CaptureWidget)
            .filter_by(tenant_id=current_user.tenant_id)
            .order_by(models.CaptureWidget.created_at.desc()).all()
        )
        return jsonify({"widgets": [{
            "id": w.id, "name": w.name, "widget_type": w.widget_type,
            "config": w.config, "active": w.active,
            "leads_captured": w.leads_captured,
            "embed_token": w.embed_token,
            "embed_url": f"/api/widget/{w.embed_token}/embed.js",
        } for w in widgets]})
    finally:
        db.close()


@ac_bp.route("/widgets", methods=["POST"])
@login_required
def create_widget():
    db = SessionLocal()
    try:
        data = request.json or {}
        w = models.CaptureWidget(
            tenant_id=current_user.tenant_id,
            name=data.get("name", "Widget de Captura"),
            widget_type=data.get("widget_type", "popup"),
            config=data.get("config", {
                "title": "Receba uma tiragem grátis! 🔮",
                "subtitle": "Deixe seu WhatsApp e receba uma leitura especial",
                "cta_text": "Quero minha tiragem!",
                "color": "#8b5cf6",
                "position": "bottom-right",
                "delay_seconds": 5,
            }),
            welcome_flow_id=data.get("welcome_flow_id"),
            embed_token=secrets.token_urlsafe(32),
        )
        db.add(w)
        db.commit()
        return jsonify({"ok": True, "widget_id": w.id, "embed_token": w.embed_token}), 201
    finally:
        db.close()


# ════════════════════════ SUBSCRIPTION PREFERENCES ════════════════════════

@ac_bp.route("/preferences/<int:lead_id>", methods=["GET"])
@login_required
def get_preferences(lead_id):
    db = SessionLocal()
    try:
        pref = (
            db.query(models.SubscriptionPreference)
            .filter_by(tenant_id=current_user.tenant_id, lead_id=lead_id)
            .first()
        )
        if not pref:
            return jsonify({"preferences": {
                "daily_tarot": True, "promotions": True, "lunar_alerts": True,
                "rituals": True, "horoscope": True, "events": True,
            }})
        return jsonify({"preferences": {
            "daily_tarot": pref.daily_tarot, "promotions": pref.promotions,
            "lunar_alerts": pref.lunar_alerts, "rituals": pref.rituals,
            "horoscope": pref.horoscope, "events": pref.events,
        }})
    finally:
        db.close()


@ac_bp.route("/preferences/<int:lead_id>", methods=["POST"])
@login_required
def update_preferences(lead_id):
    db = SessionLocal()
    try:
        data = request.json or {}
        pref = (
            db.query(models.SubscriptionPreference)
            .filter_by(tenant_id=current_user.tenant_id, lead_id=lead_id)
            .first()
        )
        if not pref:
            pref = models.SubscriptionPreference(
                tenant_id=current_user.tenant_id, lead_id=lead_id
            )
            db.add(pref)
        for k in ("daily_tarot", "promotions", "lunar_alerts", "rituals", "horoscope", "events"):
            if k in data:
                setattr(pref, k, bool(data[k]))
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ════════════════════════ GLOBAL STATS ════════════════════════

@ac_bp.route("/dashboard", methods=["GET"])
@login_required
def ac_dashboard():
    """Unified AC dashboard with all metrics."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        now = datetime.now(timezone.utc)
        thirty_days = now - timedelta(days=30)

        # Tasks
        tasks_pending = db.query(func.count(models.LeadTask.id)).filter(
            models.LeadTask.tenant_id == tid, models.LeadTask.completed == False
        ).scalar() or 0
        tasks_overdue = db.query(func.count(models.LeadTask.id)).filter(
            models.LeadTask.tenant_id == tid, models.LeadTask.completed == False,
            models.LeadTask.due_at < now,
        ).scalar() or 0

        # Conversions
        conv_30d = db.query(func.count(models.ConversionEvent.id)).filter(
            models.ConversionEvent.tenant_id == tid,
            models.ConversionEvent.converted_at >= thirty_days,
        ).scalar() or 0
        revenue_30d = db.query(func.sum(models.ConversionEvent.value)).filter(
            models.ConversionEvent.tenant_id == tid,
            models.ConversionEvent.converted_at >= thirty_days,
        ).scalar() or 0

        # Pipeline value
        pipeline_value = db.query(func.sum(models.Lead.deal_value)).filter(
            models.Lead.tenant_id == tid,
            models.Lead.pipeline_stage.notin_(["convertido", "perdido"]),
        ).scalar() or 0

        # Engagement distribution
        eng_dist = dict(
            db.query(models.Lead.engagement_level, func.count(models.Lead.id))
            .filter_by(tenant_id=tid, opt_out=False)
            .group_by(models.Lead.engagement_level).all()
        )

        # Widgets
        widgets_captured = db.query(func.sum(models.CaptureWidget.leads_captured)).filter_by(
            tenant_id=tid
        ).scalar() or 0

        return jsonify({
            "tasks_pending": tasks_pending,
            "tasks_overdue": tasks_overdue,
            "conversions_30d": conv_30d,
            "revenue_30d": round(float(revenue_30d), 2),
            "pipeline_value": round(float(pipeline_value), 2),
            "engagement": eng_dist,
            "widgets_captured": widgets_captured,
        })
    finally:
        db.close()

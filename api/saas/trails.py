"""
api/saas/trails.py — Trilhas de Aprendizado + Gamificação
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: jornadas de 7/21/40 dias, cursos estruturados, gamificação.

Endpoints ADMIN (terapeuta cria trilhas):
  GET    /saas/trails/                     — lista trilhas
  POST   /saas/trails/                     — cria trilha
  GET    /saas/trails/<id>                 — detalhe + passos
  PUT    /saas/trails/<id>                 — edita trilha
  POST   /saas/trails/<id>/publish         — publica
  POST   /saas/trails/<id>/steps           — adiciona passo
  PUT    /saas/trails/<id>/steps/<sid>     — edita passo
  DELETE /saas/trails/<id>/steps/<sid>     — remove passo

Endpoints CONSUMIDOR (lead participa):
  GET    /saas/trails/catalog              — trilhas publicadas
  POST   /saas/trails/<id>/enroll          — matricula
  GET    /saas/trails/my                   — minhas trilhas
  GET    /saas/trails/<id>/progress        — progresso na trilha
  POST   /saas/trails/<id>/complete-step   — completa passo (ganha XP)
  GET    /saas/trails/leaderboard          — ranking XP
  GET    /saas/trails/badges               — minhas conquistas
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
trails_bp = Blueprint("saas_trails", __name__, url_prefix="/saas/trails")


# ═══════════════════════════════════════════════════════════════════════
# ADMIN — Criação e gestão de trilhas
# ═══════════════════════════════════════════════════════════════════════

@trails_bp.route("/", methods=["GET"])
@login_required
def list_trails():
    db = SessionLocal()
    try:
        trails = db.query(models.LearningTrail).filter(
            (models.LearningTrail.tenant_id == current_user.tenant_id)
            | (models.LearningTrail.tenant_id.is_(None))
        ).order_by(models.LearningTrail.created_at.desc()).limit(50).all()

        return jsonify({
            "trails": [_trail_to_dict(t) for t in trails]
        })
    finally:
        db.close()


@trails_bp.route("/", methods=["POST"])
@login_required
def create_trail():
    """
    Body: {title, description?, cover_image_url?, category?, difficulty?,
           duration_days?, xp_reward?, badge_name?, badge_icon?}
    """
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title or len(title) < 3:
        return jsonify({"error": "title_required"}), 422

    db = SessionLocal()
    try:
        trail = models.LearningTrail(
            tenant_id=current_user.tenant_id,
            created_by_user_id=current_user.id,
            title=title[:200],
            description=(body.get("description") or "").strip() or None,
            cover_image_url=body.get("cover_image_url"),
            category=body.get("category", "spiritual"),
            difficulty=body.get("difficulty", "beginner"),
            duration_days=int(body.get("duration_days", 7)),
            xp_reward=int(body.get("xp_reward", 100)),
            badge_name=body.get("badge_name"),
            badge_icon=body.get("badge_icon"),
        )
        db.add(trail)
        db.commit()
        db.refresh(trail)
        return jsonify({"ok": True, "id": trail.id}), 201
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>", methods=["GET"])
@login_required
def get_trail(trail_id: int):
    db = SessionLocal()
    try:
        t = db.query(models.LearningTrail).filter_by(id=trail_id).first()
        if not t:
            return jsonify({"error": "not_found"}), 404

        steps = db.query(models.TrailStep).filter_by(
            trail_id=trail_id,
        ).order_by(models.TrailStep.day_number.asc()).all()

        result = _trail_to_dict(t)
        result["steps"] = [
            {
                "id": s.id, "day_number": s.day_number, "title": s.title,
                "content": s.content, "content_type": s.content_type,
                "media_url": s.media_url, "media_type": s.media_type,
                "action_type": s.action_type, "action_config": s.action_config,
                "xp_reward": s.xp_reward,
            } for s in steps
        ]
        return jsonify(result)
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>", methods=["PUT"])
@login_required
def update_trail(trail_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        t = db.query(models.LearningTrail).filter_by(
            id=trail_id, tenant_id=current_user.tenant_id,
        ).first()
        if not t:
            return jsonify({"error": "not_found"}), 404

        for f in ["title", "description", "cover_image_url", "category",
                   "difficulty", "duration_days", "xp_reward", "badge_name", "badge_icon"]:
            if f in body:
                setattr(t, f, body[f])

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>/publish", methods=["POST"])
@login_required
def publish_trail(trail_id: int):
    db = SessionLocal()
    try:
        t = db.query(models.LearningTrail).filter_by(
            id=trail_id, tenant_id=current_user.tenant_id,
        ).first()
        if not t:
            return jsonify({"error": "not_found"}), 404

        steps = db.query(models.TrailStep).filter_by(trail_id=trail_id).count()
        if steps == 0:
            return jsonify({"error": "add_at_least_one_step"}), 422

        t.is_published = True
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>/steps", methods=["POST"])
@login_required
def add_step(trail_id: int):
    """
    Body: {day_number, title, content?, content_type?, media_url?, media_type?,
           action_type?, action_config?, xp_reward?}
    """
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title_required"}), 422

    db = SessionLocal()
    try:
        t = db.query(models.LearningTrail).filter_by(
            id=trail_id, tenant_id=current_user.tenant_id,
        ).first()
        if not t:
            return jsonify({"error": "trail_not_found"}), 404

        step = models.TrailStep(
            trail_id=trail_id,
            day_number=int(body.get("day_number", 1)),
            title=title[:200],
            content=body.get("content"),
            content_type=body.get("content_type", "text"),
            media_url=body.get("media_url"),
            media_type=body.get("media_type"),
            action_type=body.get("action_type"),
            action_config=body.get("action_config") or {},
            xp_reward=int(body.get("xp_reward", 10)),
        )
        db.add(step)
        db.commit()
        db.refresh(step)
        return jsonify({"ok": True, "id": step.id}), 201
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>/steps/<int:step_id>", methods=["PUT"])
@login_required
def update_step(trail_id: int, step_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        step = db.query(models.TrailStep).filter_by(
            id=step_id, trail_id=trail_id,
        ).first()
        if not step:
            return jsonify({"error": "not_found"}), 404

        for f in ["title", "content", "content_type", "media_url", "media_type",
                   "action_type", "action_config", "xp_reward", "day_number"]:
            if f in body:
                setattr(step, f, body[f])

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>/steps/<int:step_id>", methods=["DELETE"])
@login_required
def delete_step(trail_id: int, step_id: int):
    db = SessionLocal()
    try:
        step = db.query(models.TrailStep).filter_by(
            id=step_id, trail_id=trail_id,
        ).first()
        if not step:
            return jsonify({"error": "not_found"}), 404
        db.delete(step)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# CONSUMIDOR — Participação em trilhas
# ═══════════════════════════════════════════════════════════════════════

@trails_bp.route("/catalog", methods=["GET"])
@login_required
def catalog():
    """Trilhas publicadas disponíveis."""
    category = request.args.get("category")
    db = SessionLocal()
    try:
        q = db.query(models.LearningTrail).filter_by(is_published=True)
        if category:
            q = q.filter_by(category=category)

        trails = q.order_by(models.LearningTrail.total_enrollments.desc()).limit(50).all()
        return jsonify({
            "trails": [_trail_to_dict(t) for t in trails]
        })
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>/enroll", methods=["POST"])
@login_required
def enroll(trail_id: int):
    """Matricula na trilha."""
    db = SessionLocal()
    try:
        trail = db.query(models.LearningTrail).filter_by(
            id=trail_id, is_published=True,
        ).first()
        if not trail:
            return jsonify({"error": "trail_not_found"}), 404

        # Já matriculado?
        existing = db.query(models.TrailEnrollment).filter_by(
            trail_id=trail_id, tenant_id=current_user.tenant_id,
            status="active",
        ).first()
        if existing:
            return jsonify({"error": "already_enrolled", "enrollment_id": existing.id}), 409

        enrollment = models.TrailEnrollment(
            trail_id=trail_id,
            tenant_id=current_user.tenant_id,
            current_day=1,
        )
        db.add(enrollment)
        trail.total_enrollments += 1
        db.commit()
        db.refresh(enrollment)

        return jsonify({"ok": True, "enrollment_id": enrollment.id}), 201
    finally:
        db.close()


@trails_bp.route("/my", methods=["GET"])
@login_required
def my_trails():
    """Minhas trilhas ativas."""
    db = SessionLocal()
    try:
        enrollments = db.query(models.TrailEnrollment).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.TrailEnrollment.last_activity_at.desc()).all()

        results = []
        for e in enrollments:
            trail = db.query(models.LearningTrail).filter_by(id=e.trail_id).first()
            if trail:
                total_steps = db.query(models.TrailStep).filter_by(trail_id=trail.id).count()
                completed = len(e.completed_steps or [])
                results.append({
                    "enrollment_id": e.id,
                    "trail": _trail_to_dict(trail),
                    "current_day": e.current_day,
                    "completed_steps": completed,
                    "total_steps": total_steps,
                    "progress_pct": round(completed / total_steps * 100) if total_steps else 0,
                    "total_xp": e.total_xp,
                    "streak": e.streak_count,
                    "status": e.status,
                })

        return jsonify({"enrollments": results})
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>/progress", methods=["GET"])
@login_required
def trail_progress(trail_id: int):
    """Progresso detalhado na trilha."""
    db = SessionLocal()
    try:
        enrollment = db.query(models.TrailEnrollment).filter_by(
            trail_id=trail_id, tenant_id=current_user.tenant_id,
        ).first()
        if not enrollment:
            return jsonify({"error": "not_enrolled"}), 404

        trail = db.query(models.LearningTrail).filter_by(id=trail_id).first()
        steps = db.query(models.TrailStep).filter_by(
            trail_id=trail_id,
        ).order_by(models.TrailStep.day_number.asc()).all()

        completed_ids = set(enrollment.completed_steps or [])

        return jsonify({
            "trail": _trail_to_dict(trail),
            "enrollment": {
                "current_day": enrollment.current_day,
                "total_xp": enrollment.total_xp,
                "streak": enrollment.streak_count,
                "best_streak": enrollment.best_streak,
                "status": enrollment.status,
                "started_at": enrollment.started_at.isoformat(),
            },
            "steps": [
                {
                    "id": s.id, "day_number": s.day_number, "title": s.title,
                    "content": s.content if s.id in completed_ids or s.day_number <= enrollment.current_day else None,
                    "content_type": s.content_type,
                    "action_type": s.action_type,
                    "xp_reward": s.xp_reward,
                    "is_completed": s.id in completed_ids,
                    "is_locked": s.day_number > enrollment.current_day,
                } for s in steps
            ],
            "progress_pct": round(len(completed_ids) / len(steps) * 100) if steps else 0,
        })
    finally:
        db.close()


@trails_bp.route("/<int:trail_id>/complete-step", methods=["POST"])
@login_required
def complete_step(trail_id: int):
    """
    Completa um passo da trilha. Ganha XP e pode desbloquear badge.
    Body: {step_id, response?}
    """
    body = request.get_json(silent=True) or {}
    step_id = body.get("step_id")
    if not step_id:
        return jsonify({"error": "step_id_required"}), 422

    db = SessionLocal()
    try:
        enrollment = db.query(models.TrailEnrollment).filter_by(
            trail_id=trail_id, tenant_id=current_user.tenant_id,
            status="active",
        ).first()
        if not enrollment:
            return jsonify({"error": "not_enrolled"}), 404

        step = db.query(models.TrailStep).filter_by(
            id=int(step_id), trail_id=trail_id,
        ).first()
        if not step:
            return jsonify({"error": "step_not_found"}), 404

        # Verificar se pode acessar
        if step.day_number > enrollment.current_day:
            return jsonify({"error": "step_locked"}), 403

        completed = list(enrollment.completed_steps or [])
        if step.id in completed:
            return jsonify({"error": "already_completed"}), 409

        # Completar
        completed.append(step.id)
        enrollment.completed_steps = completed
        enrollment.total_xp += step.xp_reward
        enrollment.last_activity_at = datetime.now(timezone.utc)

        # Streak
        enrollment.streak_count += 1
        if enrollment.streak_count > enrollment.best_streak:
            enrollment.best_streak = enrollment.streak_count

        # Avançar dia se todos os steps do dia atual completados
        all_day_steps = db.query(models.TrailStep).filter_by(
            trail_id=trail_id, day_number=enrollment.current_day,
        ).all()
        all_day_ids = {s.id for s in all_day_steps}
        if all_day_ids.issubset(set(completed)):
            enrollment.current_day += 1

        # Trilha completa?
        total_steps = db.query(models.TrailStep).filter_by(trail_id=trail_id).count()
        badges_earned = []

        if len(completed) >= total_steps:
            enrollment.status = "completed"
            enrollment.completed_at = datetime.now(timezone.utc)

            trail = db.query(models.LearningTrail).filter_by(id=trail_id).first()
            if trail:
                trail.total_completions += 1
                enrollment.total_xp += trail.xp_reward

                # Badge de conclusão
                if trail.badge_name:
                    badge = models.UserBadge(
                        tenant_id=current_user.tenant_id,
                        badge_name=trail.badge_name,
                        badge_icon=trail.badge_icon or "🏆",
                        badge_type="trail_completion",
                        description=f"Completou a trilha: {trail.title}",
                        xp_earned=trail.xp_reward,
                        trail_id=trail.id,
                    )
                    db.add(badge)
                    badges_earned.append({
                        "name": badge.badge_name,
                        "icon": badge.badge_icon,
                        "xp": badge.xp_earned,
                    })

        db.commit()

        result = {
            "ok": True,
            "xp_earned": step.xp_reward,
            "total_xp": enrollment.total_xp,
            "streak": enrollment.streak_count,
            "current_day": enrollment.current_day,
            "progress_pct": round(len(completed) / total_steps * 100) if total_steps else 100,
            "trail_completed": enrollment.status == "completed",
        }
        if badges_earned:
            result["badges_earned"] = badges_earned

        return jsonify(result)
    finally:
        db.close()


@trails_bp.route("/leaderboard", methods=["GET"])
@login_required
def leaderboard():
    """Ranking de XP."""
    db = SessionLocal()
    try:
        enrollments = db.query(models.TrailEnrollment).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.TrailEnrollment.total_xp.desc()).limit(20).all()

        return jsonify({
            "leaderboard": [
                {
                    "rank": i + 1,
                    "total_xp": e.total_xp,
                    "streak": e.streak_count,
                    "trails_completed": 1 if e.status == "completed" else 0,
                } for i, e in enumerate(enrollments)
            ]
        })
    finally:
        db.close()


@trails_bp.route("/badges", methods=["GET"])
@login_required
def my_badges():
    """Minhas conquistas."""
    db = SessionLocal()
    try:
        badges = db.query(models.UserBadge).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.UserBadge.earned_at.desc()).all()

        return jsonify({
            "badges": [
                {
                    "id": b.id, "name": b.badge_name, "icon": b.badge_icon,
                    "type": b.badge_type, "description": b.description,
                    "xp": b.xp_earned,
                    "earned_at": b.earned_at.isoformat(),
                } for b in badges
            ],
            "total_xp": sum(b.xp_earned for b in badges),
        })
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _trail_to_dict(t: models.LearningTrail) -> dict:
    return {
        "id": t.id, "title": t.title, "description": t.description,
        "cover_image_url": t.cover_image_url,
        "category": t.category,
        "difficulty": t.difficulty,
        "duration_days": t.duration_days,
        "xp_reward": t.xp_reward,
        "badge_name": t.badge_name,
        "badge_icon": t.badge_icon,
        "is_published": t.is_published,
        "total_enrollments": t.total_enrollments,
        "total_completions": t.total_completions,
        "created_at": t.created_at.isoformat(),
    }

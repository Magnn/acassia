"""
api/saas/client_progress.py — Relatório de Progresso Espiritual do Cliente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O terapeuta vê a jornada completa do cliente:
  - Leituras de tarot recebidas
  - Humor ao longo do tempo (journal)
  - Rituais completados + streaks
  - Sonhos interpretados
  - Manifestações no vision board
  - Trilhas em andamento
  - Relatório IA de evolução

Endpoints:
  GET /saas/client-progress/<lead_id>/report    — Relatório completo
  GET /saas/client-progress/<lead_id>/timeline  — Timeline de atividades
  POST /saas/client-progress/<lead_id>/note     — Nota do terapeuta
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, date, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from sqlalchemy import func

logger = logging.getLogger(__name__)
progress_bp = Blueprint("saas_client_progress", __name__, url_prefix="/saas/client-progress")


@progress_bp.route("/<int:lead_id>/report", methods=["GET"])
@login_required
def client_report(lead_id: int):
    """
    Relatório de progresso espiritual completo do lead/cliente.
    Cruza dados de todos os módulos.
    """
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        tid = current_user.tenant_id
        now = datetime.now(timezone.utc)
        d30 = now - timedelta(days=30)

        # Tarot readings
        readings_total = db.query(func.count(models.TarotReading.id)).filter_by(tenant_id=tid).scalar() or 0

        # Journal stats
        journal_total = db.query(func.count(models.JournalEntry.id)).filter_by(tenant_id=tid).scalar() or 0
        journal_recent = db.query(models.JournalEntry).filter(
            models.JournalEntry.tenant_id == tid,
            models.JournalEntry.created_at >= d30,
        ).all()
        mood_distribution = {}
        for j in journal_recent:
            if j.mood:
                mood_distribution[j.mood] = mood_distribution.get(j.mood, 0) + 1

        # Rituals
        rituals_total = db.query(func.count(models.RitualLog.id)).filter_by(tenant_id=tid).scalar() or 0
        ritual_streak = 0
        last_ritual = db.query(models.RitualLog).filter_by(
            tenant_id=tid,
        ).order_by(models.RitualLog.created_at.desc()).first()
        if last_ritual:
            ritual_streak = last_ritual.streak_days or 0

        # Dreams
        dreams_total = db.query(func.count(models.DreamEntry.id)).filter_by(tenant_id=tid).scalar() or 0
        recurring = db.query(models.DreamEntry.archetype, func.count()).filter(
            models.DreamEntry.tenant_id == tid,
            models.DreamEntry.archetype.isnot(None),
        ).group_by(models.DreamEntry.archetype).all()
        archetypes = {r[0]: r[1] for r in recurring}

        # Vision Board
        vb_total = db.query(func.count(models.VisionBoardItem.id)).filter_by(tenant_id=tid).scalar() or 0
        vb_manifested = db.query(func.count(models.VisionBoardItem.id)).filter_by(
            tenant_id=tid, is_manifested=True,
        ).scalar() or 0

        # Trails
        enrollments = db.query(models.TrailEnrollment).filter_by(tenant_id=tid).all()
        trails_active = sum(1 for e in enrollments if not e.completed_at)
        trails_completed = sum(1 for e in enrollments if e.completed_at)

        # Appointments
        appointments = db.query(func.count(models.Appointment.id)).filter_by(tenant_id=tid).scalar() or 0

        # Badges
        badges = db.query(models.UserBadge).filter_by(tenant_id=tid).all()
        total_xp = sum(b.xp_earned or 0 for b in badges)

        # Generate IA evolution analysis
        evolution = _generate_evolution_insight(
            readings_total, journal_total, rituals_total, dreams_total,
            vb_manifested, vb_total, mood_distribution, ritual_streak, total_xp,
        )

        return jsonify({
            "lead": {
                "id": lead.id,
                "name": lead.nome,
                "sign": lead.signo,
                "phone": lead.telefone,
            },
            "summary": {
                "readings": readings_total,
                "journal_entries": journal_total,
                "rituals": rituals_total,
                "ritual_streak": ritual_streak,
                "dreams": dreams_total,
                "vision_board_items": vb_total,
                "manifested": vb_manifested,
                "manifestation_rate": round((vb_manifested / vb_total * 100) if vb_total > 0 else 0, 1),
                "trails_active": trails_active,
                "trails_completed": trails_completed,
                "appointments": appointments,
                "total_xp": total_xp,
                "badges_count": len(badges),
            },
            "mood_30d": mood_distribution,
            "archetypes": archetypes,
            "badges": [
                {"name": b.badge_name, "icon": b.badge_icon, "earned_at": b.earned_at.isoformat() if b.earned_at else None}
                for b in badges[:10]
            ],
            "evolution_insight": evolution,
        })
    finally:
        db.close()


@progress_bp.route("/<int:lead_id>/timeline", methods=["GET"])
@login_required
def client_timeline(lead_id: int):
    """Timeline das últimas 30 atividades do cliente."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        limit = min(30, int(request.args.get("limit") or 20))

        activities = []

        # Journal
        journals = db.query(models.JournalEntry).filter_by(tenant_id=tid).order_by(
            models.JournalEntry.created_at.desc()
        ).limit(limit).all()
        for j in journals:
            activities.append({
                "type": "journal",
                "icon": "📔",
                "title": f"Diário: {j.entry_type}",
                "detail": j.content[:80] if j.content else "",
                "mood": j.mood,
                "at": j.created_at.isoformat() if j.created_at else "",
            })

        # Rituals
        rituals = db.query(models.RitualLog).filter_by(tenant_id=tid).order_by(
            models.RitualLog.created_at.desc()
        ).limit(limit).all()
        for r in rituals:
            activities.append({
                "type": "ritual",
                "icon": "🔥",
                "title": f"Ritual: {r.ritual_type}",
                "detail": f"Humor: {r.mood_before} → {r.mood_after}" if r.mood_before else "",
                "at": r.created_at.isoformat() if r.created_at else "",
            })

        # Dreams
        dreams = db.query(models.DreamEntry).filter_by(tenant_id=tid).order_by(
            models.DreamEntry.created_at.desc()
        ).limit(limit).all()
        for d in dreams:
            activities.append({
                "type": "dream",
                "icon": "🌙",
                "title": f"Sonho: {d.title or 'sem título'}",
                "detail": d.archetype or "",
                "at": d.created_at.isoformat() if d.created_at else "",
            })

        # Sort all by date
        activities.sort(key=lambda x: x["at"], reverse=True)

        return jsonify({"timeline": activities[:limit]})
    finally:
        db.close()


@progress_bp.route("/<int:lead_id>/note", methods=["POST"])
@login_required
def add_therapist_note(lead_id: int):
    """Terapeuta adiciona nota sobre progresso."""
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content obrigatório"}), 422

    db = SessionLocal()
    try:
        note = models.LeadNote(
            lead_id=lead_id,
            tenant_id=current_user.tenant_id,
            content=content,
            note_type=body.get("note_type", "progress"),
        )
        db.add(note)
        db.commit()
        return jsonify({"ok": True, "id": note.id}), 201
    finally:
        db.close()


def _generate_evolution_insight(readings, journal, rituals, dreams,
                                 manifested, vb_total, moods, streak, xp) -> str:
    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return _fallback_insight(readings, journal, rituals)

        prompt = f"""Analise o progresso espiritual deste cliente e gere um insight curto para o terapeuta:

Dados:
- Leituras de tarot: {readings}
- Entradas no diário: {journal}
- Rituais completados: {rituals} (streak atual: {streak} dias)
- Sonhos interpretados: {dreams}
- Vision board: {manifested}/{vb_total} manifestados
- XP total: {xp}
- Humores últimos 30 dias: {moods}

Escreva 2-3 frases sobre:
1. Padrão emocional detectado
2. Áreas de progresso
3. Sugestão de foco para as próximas sessões

pt-BR. Tom profissional para o terapeuta ler."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 300, "temperature": 0.7},
        )
        return (resp.text or "").strip() or _fallback_insight(readings, journal, rituals)
    except Exception:
        return _fallback_insight(readings, journal, rituals)


def _fallback_insight(readings, journal, rituals) -> str:
    if readings + journal + rituals == 0:
        return "Cliente ainda não iniciou sua jornada espiritual na plataforma. Recomende que comece pelo diário ou rituais diários."
    level = "iniciante" if (readings + journal + rituals) < 10 else "engajado" if (readings + journal + rituals) < 50 else "avançado"
    return f"Cliente em nível {level} de engajamento. {'Foco em estabelecer consistência.' if level == 'iniciante' else 'Boa evolução — aprofundar práticas.' if level == 'engajado' else 'Alta maturidade espiritual — explorar práticas avançadas.'}"

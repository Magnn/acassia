"""
api/saas/ritual.py — Motor de Rituais Diários Personalizados
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vertical 5: Curador de Rituais — "5 minutos de espiritualidade personalizada"

Combina:
  - Fase da lua (lunar.py)
  - Signo solar do usuário (astrology_lite.py)
  - Humor atual (input do usuário)
  - Tempo disponível
  - Calendário espiritual (spiritual_dates_seed.py)
  - IA (Gemini) para gerar ritual único

Endpoints:
  POST /saas/ritual/generate    — Gera ritual personalizado
  POST /saas/ritual/complete    — Marca ritual como completado (streak tracking)
  GET  /saas/ritual/streak      — Streak do lead/consumer
  GET  /saas/ritual/history     — Histórico de rituais
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
ritual_bp = Blueprint("saas_ritual", __name__, url_prefix="/saas/ritual")

MOODS = ["ansioso", "triste", "grato", "motivado", "cansado", "confuso", "em_paz", "irritado"]
RITUAL_TYPES = ["breathing", "mantra", "meditation", "intention", "gratitude", "visualization"]


@ritual_bp.route("/generate", methods=["POST"])
@login_required
def generate_ritual():
    """
    Gera ritual personalizado com base no humor + lua + signo + tempo.

    Body:
        {
            "mood": "ansioso",
            "minutes_available": 5,
            "sign": "leao",          // opcional (usa do lead se tiver)
            "lead_id": 123           // opcional
        }

    Returns: ritual completo com passos, mantra, cor, incenso, áudio sugerido
    """
    body = request.get_json(silent=True) or {}
    mood = (body.get("mood") or "").strip().lower()
    minutes = int(body.get("minutes_available") or 5)
    sign = (body.get("sign") or "").strip().lower()
    lead_id = body.get("lead_id")

    if mood and mood not in MOODS:
        return jsonify({"error": "invalid_mood", "valid": MOODS}), 422
    if minutes < 1:
        minutes = 5

    # Pegar fase da lua
    from lunar import phase_for_date
    moon = phase_for_date()
    moon_name = moon.get("phase_name", "crescente")

    # Pegar signo do lead se disponível
    if not sign and lead_id:
        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter_by(
                id=int(lead_id), tenant_id=current_user.tenant_id,
            ).first()
            if lead and lead.signo:
                sign = lead.signo.lower()
        finally:
            db.close()

    # Verificar se há data espiritual hoje
    spiritual_date = None
    try:
        db = SessionLocal()
        try:
            today = datetime.now(timezone.utc).date()
            sd = db.query(models.SpiritualDate).filter(
                models.SpiritualDate.date_start <= today,
                models.SpiritualDate.date_end >= today,
            ).first()
            if sd:
                spiritual_date = {"name": sd.name, "description": sd.description}
        finally:
            db.close()
    except Exception:
        pass

    # Gerar ritual via IA
    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return jsonify(_fallback_ritual(mood, moon_name, minutes, sign))

        prompt = f"""Você é um mestre espiritual criando um ritual personalizado de {minutes} minutos.

Contexto:
- Humor do praticante: {mood or "não informado"}
- Fase da lua: {moon_name} ({moon.get("illumination_pct", "?")}% iluminada)
- Signo solar: {sign or "não informado"}
- Tempo disponível: {minutes} minutos
{f"- Data espiritual de hoje: {spiritual_date['name']} — {spiritual_date['description']}" if spiritual_date else ""}

Retorne JSON estrito (sem markdown):
{{
  "title": "nome poético do ritual em 3-5 palavras",
  "intention": "frase de intenção para o ritual (1 linha)",
  "steps": [
    {{"order": 1, "type": "breathing|mantra|meditation|visualization|gratitude", "duration_seconds": 60, "instruction": "instrução clara e acolhedora", "details": "detalhes extras opcionais"}},
    ...
  ],
  "mantra": "um mantra ou afirmação poderosa para repetir",
  "recommended_color": "cor da vela ou roupa recomendada",
  "recommended_incense": "tipo de incenso ideal",
  "recommended_crystal": "cristal ideal para esse ritual",
  "closing_message": "mensagem de encerramento acolhedora (2 frases)"
}}

Crie de 2 a {max(2, minutes)} passos. Cada passo deve ter instrução prática e detalhada.
Tom: acolhedor, místico, prático. pt-BR."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 1500, "temperature": 0.85},
        )
        text = (resp.text or "").strip()

        # Parse JSON
        import re
        import json
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        ritual = json.loads(cleaned)

        # Enriquecer com dados do contexto
        ritual["moon_phase"] = moon
        ritual["mood"] = mood
        ritual["sign"] = sign
        ritual["minutes"] = minutes
        if spiritual_date:
            ritual["spiritual_date"] = spiritual_date

        return jsonify({"ok": True, "ritual": ritual})

    except Exception as exc:
        logger.warning("[ritual.generate] falhou: %s", exc)
        return jsonify(_fallback_ritual(mood, moon_name, minutes, sign))


@ritual_bp.route("/complete", methods=["POST"])
@login_required
def complete_ritual():
    """
    Marca ritual como completado.

    Body:
        {
            "ritual_type": "breathing",
            "duration_seconds": 300,
            "mood_before": "ansioso",
            "mood_after": "em_paz",
            "lead_id": 123,
            "ritual_data": {...}        // dados do ritual gerado
        }
    """
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        from lunar import phase_for_date
        moon = phase_for_date()

        log = models.RitualLog(
            tenant_id=current_user.tenant_id,
            lead_id=body.get("lead_id"),
            ritual_type=body.get("ritual_type", "general"),
            duration_seconds=body.get("duration_seconds"),
            mood_before=body.get("mood_before"),
            mood_after=body.get("mood_after"),
            moon_phase=moon.get("phase_name"),
            sign=body.get("sign"),
            ritual_data=body.get("ritual_data", {}),
        )
        db.add(log)
        db.commit()

        # Calcular streak
        streak = _calc_streak(db, current_user.tenant_id, body.get("lead_id"))

        return jsonify({
            "ok": True,
            "streak_days": streak,
            "mood_shift": f"{body.get('mood_before', '?')} → {body.get('mood_after', '?')}",
        })
    finally:
        db.close()


@ritual_bp.route("/streak", methods=["GET"])
@login_required
def get_streak():
    """Retorna streak atual e stats do lead/tenant."""
    lead_id = request.args.get("lead_id")
    db = SessionLocal()
    try:
        streak = _calc_streak(db, current_user.tenant_id, int(lead_id) if lead_id else None)

        # Total de rituais este mês
        from sqlalchemy import func, extract
        now = datetime.now(timezone.utc)
        q = db.query(func.count(models.RitualLog.id)).filter_by(
            tenant_id=current_user.tenant_id,
        )
        if lead_id:
            q = q.filter_by(lead_id=int(lead_id))
        q = q.filter(
            extract("year", models.RitualLog.completed_at) == now.year,
            extract("month", models.RitualLog.completed_at) == now.month,
        )
        monthly = q.scalar() or 0

        return jsonify({
            "streak_days": streak,
            "monthly_rituals": monthly,
        })
    finally:
        db.close()


@ritual_bp.route("/history", methods=["GET"])
@login_required
def ritual_history():
    lead_id = request.args.get("lead_id")
    limit = min(int(request.args.get("limit") or 30), 100)

    db = SessionLocal()
    try:
        q = db.query(models.RitualLog).filter_by(
            tenant_id=current_user.tenant_id,
        )
        if lead_id:
            q = q.filter_by(lead_id=int(lead_id))
        logs = q.order_by(models.RitualLog.completed_at.desc()).limit(limit).all()

        return jsonify({
            "history": [
                {
                    "id": l.id,
                    "ritual_type": l.ritual_type,
                    "duration_seconds": l.duration_seconds,
                    "mood_before": l.mood_before,
                    "mood_after": l.mood_after,
                    "moon_phase": l.moon_phase,
                    "completed_at": l.completed_at.isoformat(),
                } for l in logs
            ]
        })
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────

def _calc_streak(db, tenant_id: str, lead_id: int | None = None) -> int:
    """Calcula streak de dias consecutivos com ritual."""
    from sqlalchemy import func
    q = db.query(
        func.date(models.RitualLog.completed_at).label("d"),
    ).filter_by(tenant_id=tenant_id)
    if lead_id:
        q = q.filter_by(lead_id=lead_id)
    q = q.group_by("d").order_by(func.date(models.RitualLog.completed_at).desc())
    dates = [row.d for row in q.limit(365).all()]

    if not dates:
        return 0

    streak = 1
    for i in range(1, len(dates)):
        if (dates[i - 1] - dates[i]).days == 1:
            streak += 1
        else:
            break
    return streak


def _fallback_ritual(mood: str, moon_name: str, minutes: int, sign: str) -> dict:
    """Ritual estático quando IA não está disponível."""
    return {
        "ok": True,
        "ritual": {
            "title": f"Ritual de {moon_name.capitalize()}",
            "intention": "Conectar-me com minha essência neste momento",
            "steps": [
                {
                    "order": 1, "type": "breathing",
                    "duration_seconds": min(minutes * 60 // 2, 180),
                    "instruction": "Feche os olhos. Inspire profundamente por 4 segundos, segure por 4, expire por 6.",
                    "details": "Repita 5 vezes, sentindo cada respiração.",
                },
                {
                    "order": 2, "type": "mantra",
                    "duration_seconds": min(minutes * 60 // 2, 180),
                    "instruction": "Repita em silêncio: 'Eu sou luz, eu sou paz, eu sou força'",
                    "details": "Coloque a mão no coração enquanto repete.",
                },
            ],
            "mantra": "Eu sou luz, eu sou paz, eu sou força",
            "recommended_color": "branco" if not mood else {"ansioso": "azul", "triste": "amarelo", "irritado": "verde"}.get(mood, "branco"),
            "recommended_incense": "lavanda" if mood == "ansioso" else "sândalo",
            "recommended_crystal": "ametista" if mood == "ansioso" else "quartzo rosa",
            "closing_message": f"Que a energia da lua {moon_name} ilumine seu caminho. Namastê. 🙏",
            "moon_phase": {"phase_name": moon_name},
            "mood": mood,
            "sign": sign,
            "minutes": minutes,
        },
    }

"""
api/saas/journal.py — Diário Espiritual com IA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: journaling guiado, tracking de humor, reflexões com IA, streaks.

Endpoints:
  GET    /saas/journal/                    — lista entradas (paginado)
  POST   /saas/journal/                    — cria entrada
  GET    /saas/journal/<id>                — detalhe + insight IA
  PUT    /saas/journal/<id>                — edita
  DELETE /saas/journal/<id>                — apaga
  GET    /saas/journal/stats               — streaks, humor, contagem
  POST   /saas/journal/prompt              — gera prompt guiado por IA
  GET    /saas/journal/moods               — timeline de humor
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
journal_bp = Blueprint("saas_journal", __name__, url_prefix="/saas/journal")

ENTRY_TYPES = {
    "free", "gratitude", "intention", "reflection",
    "dream", "affirmation", "moon_ritual", "shadow_work",
}

MOOD_MAP = {
    "ansioso": "😰", "grato": "🙏", "motivado": "🔥", "triste": "😢",
    "esperancoso": "🌟", "calmo": "😌", "confuso": "🤔", "energizado": "⚡",
    "introspectivo": "🔮", "amoroso": "💜", "neutro": "😐",
}


@journal_bp.route("/", methods=["GET"])
@login_required
def list_entries():
    """Filtros: ?type=gratitude&mood=grato&from=2026-01-01&limit=20&page=1"""
    entry_type = request.args.get("type")
    mood = request.args.get("mood")
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    limit = min(50, int(request.args.get("limit", 20)))
    page = max(1, int(request.args.get("page", 1)))

    db = SessionLocal()
    try:
        q = db.query(models.JournalEntry).filter_by(
            tenant_id=current_user.tenant_id,
        )
        if entry_type:
            q = q.filter_by(entry_type=entry_type)
        if mood:
            q = q.filter_by(mood=mood)
        if from_str:
            try:
                q = q.filter(models.JournalEntry.entry_date >= date.fromisoformat(from_str))
            except Exception:
                pass
        if to_str:
            try:
                q = q.filter(models.JournalEntry.entry_date <= date.fromisoformat(to_str))
            except Exception:
                pass

        total = q.count()
        entries = q.order_by(
            models.JournalEntry.entry_date.desc(),
            models.JournalEntry.created_at.desc(),
        ).offset((page - 1) * limit).limit(limit).all()

        return jsonify({
            "entries": [_entry_to_dict(e) for e in entries],
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit,
        })
    finally:
        db.close()


@journal_bp.route("/", methods=["POST"])
@login_required
def create_entry():
    """
    Body: {content, entry_type?, title?, mood?, energy_level?,
           moon_phase?, tarot_card?, sign?, tags?, generate_insight?}
    """
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content or len(content) < 10:
        return jsonify({"error": "content_min_10_chars"}), 422

    entry_type = body.get("entry_type", "free")
    if entry_type not in ENTRY_TYPES:
        entry_type = "free"

    today = date.today()

    db = SessionLocal()
    try:
        # Calcular streak
        streak = 1
        yesterday = today - timedelta(days=1)
        prev = db.query(models.JournalEntry).filter(
            models.JournalEntry.tenant_id == current_user.tenant_id,
            models.JournalEntry.entry_date == yesterday,
        ).first()
        if prev:
            streak = prev.streak_day + 1

        entry = models.JournalEntry(
            tenant_id=current_user.tenant_id,
            entry_type=entry_type,
            title=(body.get("title") or "").strip()[:200] or None,
            content=content,
            mood=body.get("mood"),
            energy_level=body.get("energy_level"),
            moon_phase=body.get("moon_phase"),
            tarot_card=body.get("tarot_card"),
            sign=body.get("sign"),
            tags=body.get("tags") or [],
            streak_day=streak,
            entry_date=today,
        )

        # Gerar insight com IA se solicitado
        if body.get("generate_insight", False):
            insight = _generate_ai_insight(content, entry_type, body.get("mood"))
            if insight:
                entry.ai_insight = insight

        db.add(entry)

        # Verificar badges de streak
        badges_earned = []
        if streak in (7, 21, 40):
            badge = models.UserBadge(
                tenant_id=current_user.tenant_id,
                badge_name=f"Streak de {streak} dias",
                badge_icon="🔥" if streak == 7 else "⭐" if streak == 21 else "👑",
                badge_type=f"streak_{streak}",
                description=f"Escreveu no diário por {streak} dias consecutivos!",
                xp_earned=streak * 5,
            )
            db.add(badge)
            badges_earned.append({
                "name": badge.badge_name,
                "icon": badge.badge_icon,
                "xp": badge.xp_earned,
            })

        db.commit()
        db.refresh(entry)

        result = {"ok": True, "id": entry.id, "streak": streak}
        if badges_earned:
            result["badges_earned"] = badges_earned
        return jsonify(result), 201
    finally:
        db.close()


@journal_bp.route("/<int:entry_id>", methods=["GET"])
@login_required
def get_entry(entry_id: int):
    db = SessionLocal()
    try:
        e = db.query(models.JournalEntry).filter_by(
            id=entry_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_entry_to_dict(e))
    finally:
        db.close()


@journal_bp.route("/<int:entry_id>", methods=["PUT"])
@login_required
def update_entry(entry_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        e = db.query(models.JournalEntry).filter_by(
            id=entry_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404

        for f in ["content", "title", "mood", "energy_level", "tags", "entry_type"]:
            if f in body:
                setattr(e, f, body[f])

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@journal_bp.route("/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_entry(entry_id: int):
    db = SessionLocal()
    try:
        e = db.query(models.JournalEntry).filter_by(
            id=entry_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404
        db.delete(e)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@journal_bp.route("/stats", methods=["GET"])
@login_required
def journal_stats():
    """Estatísticas do diário: streak, contagem, distribuição de humor."""
    db = SessionLocal()
    try:
        entries = db.query(models.JournalEntry).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.JournalEntry.entry_date.desc()).all()

        total = len(entries)
        if total == 0:
            return jsonify({
                "total_entries": 0, "current_streak": 0,
                "best_streak": 0, "mood_distribution": {},
            })

        # Current streak
        current_streak = 0
        check_date = date.today()
        dates_set = {e.entry_date for e in entries}
        while check_date in dates_set:
            current_streak += 1
            check_date -= timedelta(days=1)

        # Best streak
        best = entries[0].streak_day if entries else 0
        for e in entries:
            if e.streak_day > best:
                best = e.streak_day

        # Mood distribution
        moods = {}
        for e in entries:
            if e.mood:
                moods[e.mood] = moods.get(e.mood, 0) + 1

        # Tipos
        types = {}
        for e in entries:
            types[e.entry_type] = types.get(e.entry_type, 0) + 1

        # Energy avg last 7 days
        week_ago = date.today() - timedelta(days=7)
        recent = [e for e in entries if e.entry_date >= week_ago and e.energy_level]
        avg_energy = sum(e.energy_level for e in recent) / len(recent) if recent else None

        # Badges
        badges = db.query(models.UserBadge).filter_by(
            tenant_id=current_user.tenant_id,
        ).all()

        return jsonify({
            "total_entries": total,
            "current_streak": current_streak,
            "best_streak": best,
            "mood_distribution": moods,
            "type_distribution": types,
            "avg_energy_7d": round(avg_energy, 1) if avg_energy else None,
            "first_entry": entries[-1].entry_date.isoformat() if entries else None,
            "badges": [
                {"name": b.badge_name, "icon": b.badge_icon, "earned_at": b.earned_at.isoformat()}
                for b in badges
            ],
        })
    finally:
        db.close()


@journal_bp.route("/prompt", methods=["POST"])
@login_required
def generate_prompt():
    """
    Gera prompt de journaling guiado por IA.
    Body: {entry_type?, mood?, context?}
    """
    body = request.get_json(silent=True) or {}
    entry_type = body.get("entry_type", "reflection")
    mood = body.get("mood")

    prompts = {
        "gratitude": [
            "Cite 3 coisas pelas quais você é grato(a) hoje. Para cada uma, escreva por que ela é importante.",
            "Pense em alguém que impactou positivamente sua vida recentemente. O que essa pessoa fez?",
            "Qual momento do seu dia trouxe mais alegria? Descreva em detalhes.",
        ],
        "intention": [
            "Qual é a sua intenção mais importante para hoje? Como pretende manifestá-la?",
            "Se pudesse mudar uma coisa na sua vida agora, o que seria? Qual é o primeiro passo?",
            "Que energia você deseja atrair para sua semana? Visualize e descreva.",
        ],
        "reflection": [
            "O que você aprendeu sobre si mesmo(a) nos últimos 7 dias?",
            "Existe algo que está te incomodando mas você ainda não teve coragem de enfrentar?",
            "Como você descreveria seu estado emocional agora? De onde vem esse sentimento?",
        ],
        "dream": [
            "Descreva o sonho mais vívido que teve recentemente. Que símbolos apareceram?",
            "Se seu sonho fosse uma mensagem do seu subconsciente, o que ele estaria tentando dizer?",
            "Há algum sonho recorrente na sua vida? O que você acha que ele significa?",
        ],
        "affirmation": [
            "Escreva 5 afirmações poderosas sobre quem você está se tornando.",
            "Complete: 'Eu sou digno(a) de _____ porque _____.'",
            "Que crença limitante você quer substituir hoje? Escreva a crença antiga e a nova.",
        ],
        "moon_ritual": [
            "A Lua está pedindo que você libere algo. O que é? Escreva e solte.",
            "Que intenção você planta nesta fase lunar? Seja específico(a).",
            "Qual aspecto da sua vida precisa de renovação? A Lua ilumina o caminho.",
        ],
        "free": [
            "Escreva livremente por 5 minutos sem parar. Deixe as palavras fluírem.",
            "Se pudesse enviar uma carta para si mesmo(a) de 5 anos atrás, o que diria?",
            "Descreva o dia ideal da sua vida daqui a 1 ano. Onde está? O que faz? Com quem?",
        ],
        "shadow_work": [
            "Qual emoção você tem evitado sentir? Dê espaço a ela agora, sem julgamento.",
            "Pense em algo que te irrita profundamente nos outros. O que isso revela sobre uma parte de você que você nega?",
            "Qual crença sobre si mesmo(a) você carrega desde a infância que já não serve mais?",
            "Complete: 'Tenho medo de ser visto(a) como _____ porque isso significaria _____.'",
            "Se pudesse ter uma conversa honesta com sua versão de 10 anos, o que essa criança diria que precisa?",
            "Qual máscara você usa com mais frequência? Por que sente necessidade de usá-la?",
            "Escreva uma carta para a parte de você que sente mais vergonha. O que ela precisa ouvir?",
            "Que padrão autodestrutivo você percebe se repetindo? De onde ele veio?",
        ],
    }

    type_prompts = prompts.get(entry_type, prompts["free"])
    import random
    prompt = random.choice(type_prompts)

    # Personalizar com mood se fornecido
    if mood:
        emoji = MOOD_MAP.get(mood, "")
        prompt = f"{emoji} Você está se sentindo {mood}. {prompt}"

    return jsonify({
        "prompt": prompt,
        "entry_type": entry_type,
        "mood": mood,
    })


@journal_bp.route("/moods", methods=["GET"])
@login_required
def mood_timeline():
    """Timeline de humor dos últimos 30 dias."""
    days = min(90, int(request.args.get("days", 30)))
    from_date = date.today() - timedelta(days=days)

    db = SessionLocal()
    try:
        entries = db.query(models.JournalEntry).filter(
            models.JournalEntry.tenant_id == current_user.tenant_id,
            models.JournalEntry.entry_date >= from_date,
            models.JournalEntry.mood.isnot(None),
        ).order_by(models.JournalEntry.entry_date.asc()).all()

        return jsonify({
            "moods": [
                {
                    "date": e.entry_date.isoformat(),
                    "mood": e.mood,
                    "emoji": MOOD_MAP.get(e.mood, ""),
                    "energy": e.energy_level,
                } for e in entries
            ],
            "total": len(entries),
        })
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _entry_to_dict(e: models.JournalEntry) -> dict:
    return {
        "id": e.id, "entry_type": e.entry_type,
        "title": e.title, "content": e.content,
        "mood": e.mood,
        "mood_emoji": MOOD_MAP.get(e.mood, ""),
        "energy_level": e.energy_level,
        "moon_phase": e.moon_phase,
        "tarot_card": e.tarot_card,
        "sign": e.sign,
        "tags": e.tags or [],
        "ai_insight": e.ai_insight,
        "streak_day": e.streak_day,
        "entry_date": e.entry_date.isoformat(),
        "created_at": e.created_at.isoformat(),
    }


def _generate_ai_insight(content: str, entry_type: str, mood: str = None) -> str | None:
    """Gera reflexão da IA sobre a entrada do diário."""
    try:
        from google import genai
        client = genai.Client()
        prompt = (
            f"Você é uma guia espiritual compassiva. O usuário escreveu em seu diário "
            f"espiritual (tipo: {entry_type}"
            + (f", humor: {mood}" if mood else "")
            + f"):\n\n\"{content[:500]}\"\n\n"
            f"Escreva uma reflexão curta (2-3 frases) que seja acolhedora, "
            f"profunda e que ajude no autoconhecimento. Use linguagem poética e "
            f"referências a simbolismos espirituais quando apropriado."
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return resp.text.strip() if resp.text else None
    except Exception as exc:
        logger.warning("[journal.ai_insight] falhou: %s", exc)
        return None

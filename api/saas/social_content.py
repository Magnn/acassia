"""
api/saas/social_content.py — Gerador de Conteúdo Social com IA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: terapeuta não sabe criar conteúdo para redes sociais.
IA gera posts, scripts de reels, stories e newsletters.

Endpoints:
  POST /saas/social/generate-post      — Gera post para feed
  POST /saas/social/generate-reel      — Gera roteiro de reel/TikTok
  POST /saas/social/generate-story     — Gera sequência de stories
  POST /saas/social/generate-newsletter — Gera newsletter semanal
  GET  /saas/social/history            — Histórico de conteúdos gerados
  GET  /saas/social/calendar           — Sugestão de calendário editorial
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
social_bp = Blueprint("saas_social", __name__, url_prefix="/saas/social")

CONTENT_TYPES = ["post", "reel", "story", "newsletter", "caption"]
NICHES = ["tarot", "astrologia", "terapia_holistica", "meditacao", "cristais", "numerologia", "yoga", "reiki"]


@social_bp.route("/generate-post", methods=["POST"])
@login_required
def generate_post():
    """
    Body: {topic?, niche?, tone?, target_audience?, include_hashtags?: bool}
    """
    body = request.get_json(silent=True) or {}
    return _generate_content("post", body)


@social_bp.route("/generate-reel", methods=["POST"])
@login_required
def generate_reel():
    """
    Body: {topic?, niche?, duration_seconds?: 30|60|90, hook_style?: "question"|"shock"|"story"}
    """
    body = request.get_json(silent=True) or {}
    return _generate_content("reel", body)


@social_bp.route("/generate-story", methods=["POST"])
@login_required
def generate_story():
    """
    Body: {topic?, niche?, num_slides?: 3-7, include_poll?: bool}
    """
    body = request.get_json(silent=True) or {}
    return _generate_content("story", body)


@social_bp.route("/generate-newsletter", methods=["POST"])
@login_required
def generate_newsletter():
    """
    Body: {topic?, niche?, subscriber_name?: string, include_reading?: bool}
    """
    body = request.get_json(silent=True) or {}
    return _generate_content("newsletter", body)


@social_bp.route("/history", methods=["GET"])
@login_required
def content_history():
    """Lista conteúdos gerados recentemente."""
    db = SessionLocal()
    try:
        # Reuse content_assets to store generated social content
        entries = db.query(models.ContentAsset).filter(
            models.ContentAsset.tenant_id == current_user.tenant_id,
            models.ContentAsset.asset_type == "social_content",
        ).order_by(models.ContentAsset.created_at.desc()).limit(30).all()

        return jsonify({
            "history": [
                {
                    "id": e.id,
                    "title": e.name,
                    "content_type": e.description,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in entries
            ],
        })
    finally:
        db.close()


@social_bp.route("/calendar", methods=["GET"])
@login_required
def editorial_calendar():
    """Gera sugestão de calendário editorial para a semana."""
    niche = request.args.get("niche", "tarot")

    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return jsonify({"calendar": _fallback_calendar()})

        # Get moon phase
        moon_phase = ""
        try:
            from lunar import phase_for_date
            moon = phase_for_date()
            moon_phase = moon.get("phase_name", "")
        except Exception:
            pass

        prompt = f"""Crie um calendário editorial para 7 dias para um(a) profissional de {niche}.
Fase lunar atual: {moon_phase}
Data início: {date.today().isoformat()}

Para cada dia, sugira:
- Tipo de conteúdo (post, reel, story, live)
- Tema específico
- Hook/gancho de abertura
- Melhor horário para postar

Retorne JSON:
{{
  "week_theme": "tema da semana",
  "days": [
    {{"day": "segunda", "date": "2026-05-05", "type": "reel", "topic": "...", "hook": "...", "best_time": "19h", "caption_idea": "..."}}
  ],
  "tips": "dica extra para a semana"
}}

pt-BR. Foque em conteúdo viral e engajamento."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 1000, "temperature": 0.85},
        )
        import re
        m = re.search(r'\{[\s\S]*\}', (resp.text or "").strip())
        if m:
            try:
                return jsonify({"calendar": json.loads(m.group())})
            except Exception:
                pass
        return jsonify({"calendar": _fallback_calendar()})
    except Exception as exc:
        logger.warning("[social.calendar] IA falhou: %s", exc)
        return jsonify({"calendar": _fallback_calendar()})


# ── Generator Core ───────────────────────────────────────────────────

def _generate_content(content_type: str, body: dict):
    topic = (body.get("topic") or "").strip()
    niche = body.get("niche", "tarot")
    tone = body.get("tone", "inspirador e autêntico")

    prompts = {
        "post": f"""Crie um post de Instagram para um(a) profissional de {niche}.
Tema: {topic or 'conteúdo do dia baseado na energia atual'}
Tom: {tone}

Retorne JSON:
{{
  "title": "título interno (não publicar)",
  "caption": "texto completo do post (2-4 parágrafos, emojis moderados)",
  "hook": "primeira frase que prende atenção",
  "cta": "call to action final",
  "hashtags": ["hashtag1", "hashtag2", "...até 15"],
  "image_suggestion": "descrição da imagem ideal para acompanhar",
  "best_time": "melhor horário para postar"
}}

pt-BR. Foque em engajamento e autenticidade. Não use clichês.""",

        "reel": f"""Crie um roteiro de Reel/TikTok para um(a) profissional de {niche}.
Tema: {topic or 'conteúdo viral do momento'}
Duração: {body.get('duration_seconds', 60)} segundos
Hook: {body.get('hook_style', 'question')}

Retorne JSON:
{{
  "title": "título do reel",
  "hook": "frase de abertura (primeiros 3 segundos — CRUCIAL)",
  "script": [
    {{"timestamp": "0-3s", "text": "...", "visual": "descrição do visual"}},
    {{"timestamp": "3-15s", "text": "...", "visual": "..."}},
    {{"timestamp": "15-30s", "text": "...", "visual": "..."}}
  ],
  "cta": "call to action final",
  "audio_suggestion": "sugestão de áudio/música trending",
  "caption": "legenda para o reel",
  "hashtags": ["hashtag1", "..."]
}}

pt-BR. Foque em reter nos primeiros 3 segundos. Tom casual e magnético.""",

        "story": f"""Crie uma sequência de Stories para um(a) profissional de {niche}.
Tema: {topic or 'conexão com a audiência'}
Slides: {body.get('num_slides', 5)}

Retorne JSON:
{{
  "title": "tema da sequência",
  "slides": [
    {{"type": "text|poll|question|quiz", "content": "...", "background": "cor sugerida", "sticker": "sugestão de sticker"}}
  ],
  "objective": "objetivo da sequência"
}}

pt-BR. Crie curiosidade progressiva. Inclua enquete ou caixinha em pelo menos 1 slide.""",

        "newsletter": f"""Crie uma newsletter semanal para um(a) profissional de {niche}.
Tema: {topic or 'energia da semana'}

Retorne JSON:
{{
  "subject_line": "assunto do email (curto, intrigante)",
  "preview_text": "texto de preview",
  "greeting": "saudação personalizada",
  "sections": [
    {{"title": "título da seção", "content": "conteúdo (1-2 parágrafos)", "emoji": "emoji da seção"}}
  ],
  "cta": {{"text": "texto do botão", "message": "mensagem de contexto"}},
  "closing": "despedida calorosa",
  "ps": "P.S. (mensagem bônus)"
}}

pt-BR. Tom íntimo e acolhedor. Máximo 600 palavras.""",
    }

    prompt = prompts.get(content_type, prompts["post"])

    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return jsonify({"ok": True, "content": _fallback_content(content_type), "type": content_type})

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 1200, "temperature": 0.85},
        )

        text = (resp.text or "").strip()
        import re
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                content = json.loads(m.group())
                # Persist
                _save_content(content_type, content.get("title", topic), content)
                return jsonify({"ok": True, "content": content, "type": content_type})
            except Exception:
                pass

        return jsonify({"ok": True, "content": {"raw": text}, "type": content_type})
    except Exception as exc:
        logger.warning("[social.generate] IA falhou: %s", exc)
        return jsonify({"ok": True, "content": _fallback_content(content_type), "type": content_type})


def _save_content(content_type: str, title: str, content: dict):
    try:
        db = SessionLocal()
        try:
            from flask_login import current_user as cu
            asset = models.ContentAsset(
                tenant_id=cu.tenant_id,
                name=title[:200] or f"Conteúdo {content_type}",
                asset_type="social_content",
                description=content_type,
                metadata_json=content,
            )
            db.add(asset)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("[social.save] Falhou: %s", exc)


def _fallback_content(content_type: str) -> dict:
    return {
        "title": "Conteúdo Gerado",
        "caption": "✨ O universo conspira a seu favor. Hoje é dia de confiar no processo e abrir espaço para o novo.\n\nQual área da sua vida precisa de renovação?",
        "hook": "Você sabia que a lua de hoje favorece novos começos?",
        "cta": "Me conta nos comentários!",
        "hashtags": ["#espiritualidade", "#tarot", "#autoconhecimento", "#astrologia"],
    }


def _fallback_calendar() -> dict:
    return {
        "week_theme": "Semana de Renovação",
        "days": [
            {"day": "segunda", "type": "post", "topic": "Energia da semana", "hook": "O que os astros reservam?", "best_time": "19h"},
            {"day": "terça", "type": "reel", "topic": "Dica rápida", "hook": "Você faz isso antes de dormir?", "best_time": "20h"},
            {"day": "quarta", "type": "story", "topic": "Bastidores", "hook": "Meu ritual matinal", "best_time": "10h"},
            {"day": "quinta", "type": "post", "topic": "Carta da semana", "hook": "A carta que saiu para você", "best_time": "19h"},
            {"day": "sexta", "type": "reel", "topic": "Lua do fim de semana", "hook": "Atenção com esse trânsito!", "best_time": "18h"},
        ],
        "tips": "Poste nos horários de pico e interaja nos primeiros 30 minutos.",
    }

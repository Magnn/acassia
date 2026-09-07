"""
api/saas/unified_reading.py — Leitura Integrada Multi-Modal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Combina TUDO em uma leitura:
  - Tarot (3 cartas)
  - Trânsitos astrológicos
  - Numerologia pessoal
  - Fase lunar atual
  - Análise de foto (palma/aura) via Gemini Vision

Endpoints:
  POST /saas/reading/unified      — Leitura integrada completa
  POST /saas/reading/palm          — Análise de palma por foto
  GET  /saas/reading/daily         — Leitura diária personalizada (1 grátis/dia)
  GET  /saas/reading/history       — Histórico de leituras
"""

from __future__ import annotations

import json
import logging
import base64
from datetime import datetime, date, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from api.saas.platform_health import rate_limit

logger = logging.getLogger(__name__)
reading_bp = Blueprint("saas_reading", __name__, url_prefix="/saas/reading")

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


@reading_bp.route("/unified", methods=["POST"])
@login_required
@rate_limit("ai_reading")
def unified_reading():
    """
    Leitura unificada: Tarot + Astro + Numerologia + Lua.
    Body: {
        question?: string,
        birth_date?: "1990-05-15",
        birth_time?: "14:30",
        birth_city?: "São Paulo",
        name?: string,
        include_tarot?: bool (default true),
        include_astro?: bool (default true),
        include_numerology?: bool (default true),
    }
    """
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()

    # Gather context
    context = _build_context(body)

    # Generate integrated reading
    reading = _generate_unified(question, context)
    if not reading:
        return jsonify({"error": "ai_failed"}), 500

    # Persist
    db = SessionLocal()
    try:
        entry = models.TarotReading(
            tenant_id=current_user.tenant_id,
            pergunta=question or "Leitura integrada multi-modal",
            resposta=json.dumps(reading, ensure_ascii=False),
            num_cartas=3,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        reading["id"] = entry.id
    finally:
        db.close()

    return jsonify({"ok": True, "reading": reading})


@reading_bp.route("/palm", methods=["POST"])
@login_required
@rate_limit("ai_palm")
def palm_reading():
    """
    Análise de palma/mão por foto via Gemini Vision.
    Body: {image_base64: string, question?: string}
    """
    body = request.get_json(silent=True) or {}
    image_b64 = body.get("image_base64")
    if not image_b64:
        return jsonify({"error": "image_base64 é obrigatório"}), 422

    question = (body.get("question") or "Analise minha mão").strip()

    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return jsonify({"error": "ai_unavailable"}), 503

        # Clean base64
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_b64)

        # Image size validation
        if len(image_bytes) > MAX_IMAGE_SIZE:
            return jsonify({"error": f"Imagem muito grande. Máximo: {MAX_IMAGE_SIZE // (1024*1024)}MB"}), 413

        prompt = f"""Você é um quiromante (palmista) espiritual experiente com 30 anos de prática.

Analise a imagem da mão enviada e forneça uma leitura completa de quiromancia.

Pergunta do consulente: "{question}"

Analise as seguintes linhas e monte:
- Linha da Vida (comprimento, profundidade, curvatura)
- Linha do Coração (posição, ramificações)
- Linha da Cabeça (traçado, interseções)
- Linha do Destino (se visível)
- Monte de Vênus, Júpiter, Saturno

Retorne em JSON estrito:
{{
  "title": "Leitura da sua Mão",
  "life_line": {{"description": "...", "interpretation": "..."}},
  "heart_line": {{"description": "...", "interpretation": "..."}},
  "head_line": {{"description": "...", "interpretation": "..."}},
  "destiny_line": {{"description": "...", "interpretation": "..."}},
  "mounts": {{"venus": "...", "jupiter": "...", "saturn": "..."}},
  "overall_message": "mensagem geral integradora",
  "advice": "conselho prático para o momento",
  "dominant_element": "fogo|terra|ar|agua"
}}

pt-BR. Seja profunda e específica."""

        from google.genai import types
        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=[
                types.Content(parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                ])
            ],
            config={"max_output_tokens": 1200, "temperature": 0.8},
        )

        text = (resp.text or "").strip()
        # Parse JSON
        reading = _extract_json(text)
        if not reading:
            reading = {"title": "Leitura da Palma", "overall_message": text, "advice": ""}

        return jsonify({"ok": True, "palm_reading": reading})
    except Exception as exc:
        logger.error("[reading.palm] Erro: %s", exc)
        return jsonify({"error": str(exc)}), 500


@reading_bp.route("/daily", methods=["GET"])
@login_required
def daily_reading():
    """
    Leitura diária personalizada — 1 grátis/dia.
    Combina: 1 carta tarot + fase lunar + vibração do dia.
    """
    db = SessionLocal()
    try:
        today = date.today()

        # Check if already read today
        existing = db.query(models.TarotReading).filter(
            models.TarotReading.tenant_id == current_user.tenant_id,
            models.TarotReading.created_at >= datetime.combine(today, datetime.min.time()),
            models.TarotReading.pergunta.like("%diária%"),
        ).first()

        if existing:
            try:
                cached = json.loads(existing.resposta)
                cached["id"] = existing.id
                cached["cached"] = True
                return jsonify({"ok": True, "reading": cached})
            except Exception:
                pass

        # Generate new
        reading = _generate_daily()

        entry = models.TarotReading(
            tenant_id=current_user.tenant_id,
            pergunta="Leitura diária personalizada",
            resposta=json.dumps(reading, ensure_ascii=False),
            num_cartas=1,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        reading["id"] = entry.id

        return jsonify({"ok": True, "reading": reading})
    finally:
        db.close()


@reading_bp.route("/history", methods=["GET"])
@login_required
def reading_history():
    """Histórico de leituras (paginado)."""
    limit = min(50, int(request.args.get("limit") or 20))
    page = max(1, int(request.args.get("page") or 1))

    db = SessionLocal()
    try:
        q = db.query(models.TarotReading).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.TarotReading.created_at.desc())

        total = q.count()
        readings = q.offset((page - 1) * limit).limit(limit).all()

        return jsonify({
            "readings": [
                {
                    "id": r.id,
                    "question": r.pergunta,
                    "cards": r.num_cartas,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "summary": _reading_summary(r.resposta),
                }
                for r in readings
            ],
            "total": total,
            "page": page,
        })
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────

def _build_context(body: dict) -> dict:
    ctx = {}

    # Moon phase
    try:
        from lunar import phase_for_date
        moon = phase_for_date()
        ctx["moon_phase"] = moon.get("phase_name", "")
        ctx["moon_emoji"] = moon.get("emoji", "")
    except Exception:
        ctx["moon_phase"] = ""

    # Birth data
    if body.get("birth_date"):
        ctx["birth_date"] = body["birth_date"]
        ctx["birth_time"] = body.get("birth_time", "12:00")
        ctx["birth_city"] = body.get("birth_city", "")

        # Numerology
        try:
            from astrology_lite import calculate_life_path
            ctx["life_path"] = calculate_life_path(body["birth_date"])
        except Exception:
            pass

        # Sun sign
        try:
            from astrology_lite import sun_sign_from_date
            ctx["sun_sign"] = sun_sign_from_date(body["birth_date"])
        except Exception:
            pass

    ctx["name"] = body.get("name", "")
    return ctx


def _generate_unified(question: str, ctx: dict) -> dict | None:
    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return _fallback_unified(question, ctx)

        prompt = f"""Você é um Oráculo Multi-Modal que integra Tarot, Astrologia, Numerologia e sabedoria lunar.

Contexto do consulente:
- Nome: {ctx.get('name', 'Consulente')}
- Signo Solar: {ctx.get('sun_sign', 'desconhecido')}
- Caminho de Vida: {ctx.get('life_path', 'desconhecido')}
- Fase Lunar Atual: {ctx.get('moon_phase', 'desconhecida')} {ctx.get('moon_emoji', '')}
- Data Nascimento: {ctx.get('birth_date', 'desconhecida')}

Pergunta: "{question or 'O que o universo quer me dizer hoje?'}"

Faça uma leitura INTEGRADA que combine:

1. TAROT: Selecione 3 cartas (passado/presente/futuro) e interprete
2. ASTROLOGIA: Analise trânsitos relevantes para o signo
3. NUMEROLOGIA: Use o número do caminho de vida na interpretação
4. LUNAR: Contextualize com a fase lunar atual

Retorne JSON estrito:
{{
  "title": "título da leitura",
  "tarot": {{
    "cards": [
      {{"name": "...", "position": "passado|presente|futuro", "meaning": "...", "reversed": false}}
    ],
    "synthesis": "síntese do tarot"
  }},
  "astrology": {{
    "sun_sign": "...",
    "current_transit": "trânsito principal do momento",
    "advice": "conselho astrológico"
  }},
  "numerology": {{
    "life_path": "número",
    "vibration_today": "número do dia",
    "meaning": "significado"
  }},
  "lunar": {{
    "phase": "...",
    "influence": "como a lua afeta esta leitura",
    "ritual_suggestion": "ritual sugerido"
  }},
  "integrated_message": "mensagem final que integra TUDO em 3-4 parágrafos",
  "affirmation": "afirmação poderosa para o dia",
  "lucky": {{
    "color": "...",
    "crystal": "...",
    "number": 0,
    "element": "fogo|terra|ar|agua"
  }}
}}

pt-BR. Seja profunda, mística e personalizada."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 1500, "temperature": 0.85},
        )

        text = (resp.text or "").strip()
        result = _extract_json(text)
        if result:
            return result
        return {"title": "Leitura Integrada", "integrated_message": text, "tarot": {}, "astrology": {}, "numerology": {}, "lunar": {}}
    except Exception as exc:
        logger.warning("[reading.unified] IA falhou: %s", exc)
        return _fallback_unified(question, ctx)


def _generate_daily() -> dict:
    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return _fallback_daily()

        moon_phase = ""
        try:
            from lunar import phase_for_date
            moon = phase_for_date()
            moon_phase = moon.get("phase_name", "")
        except Exception:
            pass

        prompt = f"""Gere uma leitura diária espiritual curta e impactante para hoje.
Fase lunar: {moon_phase}
Data: {date.today().isoformat()}

Retorne JSON:
{{
  "title": "título inspirador",
  "card": {{"name": "nome carta tarot", "meaning": "significado breve"}},
  "message": "mensagem do dia (2-3 frases)",
  "affirmation": "afirmação poderosa",
  "energy": "energia do dia (1 palavra)",
  "color": "cor do dia",
  "crystal": "cristal do dia",
  "moon_phase": "{moon_phase}",
  "lucky_number": 0
}}

pt-BR. Conciso e poderoso."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 500, "temperature": 0.9},
        )
        result = _extract_json((resp.text or "").strip())
        return result or _fallback_daily()
    except Exception:
        return _fallback_daily()


def _fallback_unified(question: str, ctx: dict) -> dict:
    return {
        "title": "Leitura Integrada",
        "integrated_message": "O universo se comunica através de múltiplas linguagens — estrelas, cartas e números convergem para uma mensagem: confie no processo.",
        "tarot": {"cards": [{"name": "A Estrela", "position": "presente", "meaning": "Esperança e renovação"}], "synthesis": "Momento de fé."},
        "astrology": {"sun_sign": ctx.get("sun_sign", ""), "advice": "Os astros favorecem a introspecção."},
        "numerology": {"life_path": ctx.get("life_path", ""), "meaning": "Seu número vibra em harmonia hoje."},
        "lunar": {"phase": ctx.get("moon_phase", ""), "ritual_suggestion": "Medite por 5 minutos."},
        "affirmation": "Eu confio na sabedoria do universo que me guia.",
        "lucky": {"color": "violeta", "crystal": "ametista", "number": 7, "element": "agua"},
    }


def _fallback_daily() -> dict:
    return {
        "title": "Mensagem do Dia",
        "card": {"name": "O Sol", "meaning": "Alegria e vitalidade"},
        "message": "Hoje é um dia de luz. Permita-se brilhar.",
        "affirmation": "Eu irradio luz e recebo abundância.",
        "energy": "expansão",
        "color": "dourado",
        "crystal": "citrino",
        "lucky_number": 3,
    }


def _extract_json(text: str) -> dict | None:
    import re
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return None


def _reading_summary(resposta: str) -> str:
    try:
        data = json.loads(resposta)
        return data.get("title", data.get("message", ""))[:100]
    except Exception:
        return resposta[:100] if resposta else ""

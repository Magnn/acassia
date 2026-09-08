"""
api/public/v1/astrology.py — API Pública de Astrologia do Meu Mistério
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints públicos autenticados por API Key para devs e empresas externas.
Vende a infraestrutura de astrologia como serviço (AaaS).

Pricing tiers:
  - Free:  100 requests/dia, sem interpretação IA
  - Pro:   10.000 requests/dia, com interpretação IA
  - Scale: ilimitado, SLA, webhook, whitelabel

Endpoints:
  POST /api/v1/astrology/natal-chart     — Mapa natal completo
  POST /api/v1/astrology/horoscope       — Horóscopo diário/semanal/mensal
  POST /api/v1/astrology/synastry        — Compatibilidade de casais
  POST /api/v1/astrology/transit         — Trânsitos do momento
  GET  /api/v1/astrology/moon            — Fase lunar atual
  GET  /api/v1/astrology/moon/calendar   — Calendário lunar
  POST /api/v1/numerology/full           — Mapa numerológico completo
"""

from __future__ import annotations

import functools
import logging
import os
import time
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

public_astro_bp = Blueprint("public_astrology", __name__)


# ═══════════════════════════════════════════════════════════════════════
# API Key Authentication + Rate Limiting
# ═══════════════════════════════════════════════════════════════════════

def require_api_key(f):
    """Decorator: valida API key no header X-API-Key ou query ?api_key=."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not key:
            return jsonify({
                "error": "api_key_required",
                "message": "Inclua sua API key no header X-API-Key.",
                "docs": "https://meumisterio.com/docs/api",
            }), 401

        # Lookup key
        from db.database import SessionLocal
        from db import models
        db = SessionLocal()
        try:
            api_key_obj = db.query(models.PublicApiKey).filter_by(
                key_hash=_hash_key(key),
                is_active=True,
            ).first()

            if not api_key_obj:
                return jsonify({"error": "invalid_api_key"}), 401

            # Rate limiting by tier
            tier = api_key_obj.tier or "free"
            limits = {"free": 100, "pro": 10_000, "scale": 1_000_000}
            daily_limit = limits.get(tier, 100)

            # Check daily usage (stored in api_key metadata)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            usage = api_key_obj.daily_usage or {}
            today_count = usage.get(today, 0)

            if today_count >= daily_limit:
                return jsonify({
                    "error": "rate_limit_exceeded",
                    "limit": daily_limit,
                    "used": today_count,
                    "tier": tier,
                    "upgrade": "https://meumisterio.com/api/pricing",
                }), 429

            # Increment
            usage[today] = today_count + 1
            # Cleanup old dates
            for k in list(usage.keys()):
                if k < today:
                    del usage[k]
            api_key_obj.daily_usage = usage
            api_key_obj.last_used_at = datetime.now(timezone.utc)
            api_key_obj.total_requests = (api_key_obj.total_requests or 0) + 1
            db.commit()

            # Store in request context
            g.api_key = api_key_obj
            g.api_tier = tier
            g.api_tenant_id = api_key_obj.tenant_id

        finally:
            db.close()

        return f(*args, **kwargs)
    return decorated


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash da API key para storage seguro."""
    import hashlib
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════
# ASTROLOGY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@public_astro_bp.route("/api/v1/astrology/natal-chart", methods=["POST"])
@require_api_key
def natal_chart():
    """
    Gera mapa natal completo.

    Body:
        {
            "birth_date": "1990-05-15",
            "birth_time": "14:30",        // opcional
            "latitude": -23.55,           // opcional (para ascendente)
            "longitude": -46.63,          // opcional
            "interpret": true             // IA interpretation (Pro+ tier)
        }

    Returns: mapa natal com sol, lua, ascendente, elementos, interpretação
    """
    body = request.get_json(silent=True) or {}
    birth_date_str = body.get("birth_date")

    if not birth_date_str:
        return jsonify({"error": "birth_date_required", "format": "YYYY-MM-DD"}), 422

    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid_date_format", "expected": "YYYY-MM-DD"}), 422

    birth_time = body.get("birth_time")
    lat = body.get("latitude")
    lon = body.get("longitude")
    want_interpretation = bool(body.get("interpret", False))

    # Mapa natal via motor existente
    from astrology_lite import natal_chart_lite, chart_summary_text

    kwargs = {"birth_date": birth_date}
    if birth_time:
        try:
            h, m = map(int, birth_time.split(":"))
            kwargs["birth_time_utc"] = birth_date.replace(hour=h, minute=m)
        except Exception:
            pass
    if lat is not None and lon is not None:
        kwargs["lat_deg"] = float(lat)
        kwargs["lon_deg"] = float(lon)

    chart = natal_chart_lite(**kwargs)
    summary = chart_summary_text(chart)

    result = {
        "chart": chart,
        "summary_text": summary,
        "interpretation": None,
    }

    # Interpretação IA (Pro+ tier)
    if want_interpretation and g.api_tier in ("pro", "scale"):
        try:
            from personalizer import Personalizer
            p = Personalizer()
            if p.client:
                prompt = (
                    f"Interprete este mapa natal de forma acolhedora em pt-BR, "
                    f"max 200 palavras:\n\n{summary}"
                )
                resp = p.client.models.generate_content(
                    model=p.model_name, contents=prompt,
                )
                result["interpretation"] = (resp.text or "").strip() or None
        except Exception:
            pass
    elif want_interpretation and g.api_tier == "free":
        result["interpretation_note"] = "Interpretação IA requer plano Pro. Upgrade: https://meumisterio.com/api/pricing"

    return jsonify(result)


@public_astro_bp.route("/api/v1/astrology/horoscope", methods=["POST"])
@require_api_key
def horoscope_api():
    """
    Gera horóscopo personalizado.

    Body:
        {
            "sign": "leao",
            "period": "daily" | "weekly" | "monthly",
            "date": "2027-01-15"          // opcional, default=hoje
        }
    """
    body = request.get_json(silent=True) or {}
    sign = (body.get("sign") or "").strip().lower()
    period = body.get("period", "daily").strip().lower()
    target_date_str = body.get("date")

    valid_signs = [
        "aries", "touro", "gemeos", "cancer", "leao", "virgem",
        "libra", "escorpiao", "sagitario", "capricornio", "aquario", "peixes",
    ]
    if sign not in valid_signs:
        return jsonify({"error": "invalid_sign", "valid": valid_signs}), 422
    if period not in ("daily", "weekly", "monthly"):
        return jsonify({"error": "invalid_period", "valid": ["daily", "weekly", "monthly"]}), 422

    target_date = datetime.now(timezone.utc)
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            pass

    # Gerar via Gemini (motor existente)
    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return jsonify({"error": "ai_unavailable"}), 503

        period_map = {"daily": "diário", "weekly": "semanal", "monthly": "mensal"}
        prompt = (
            f"Escreva o horóscopo {period_map[period]} para {sign.capitalize()} "
            f"no dia {target_date.strftime('%d/%m/%Y')}. "
            f"Tom: místico e acolhedor, pt-BR. Max 150 palavras. "
            f"Inclua: energia do dia, conselho prático, cor e número da sorte."
        )
        resp = p.client.models.generate_content(
            model=p.model_name, contents=prompt,
            config={"max_output_tokens": 400, "temperature": 0.9},
        )
        text = (resp.text or "").strip()

        # Fase da lua
        from lunar import phase_for_date
        moon = phase_for_date(target_date)

        return jsonify({
            "sign": sign,
            "period": period,
            "date": target_date.strftime("%Y-%m-%d"),
            "horoscope": text,
            "moon_phase": moon,
        })
    except Exception as exc:
        logger.warning("[public.horoscope] erro: %s", exc)
        return jsonify({"error": "generation_failed"}), 500


@public_astro_bp.route("/api/v1/astrology/moon", methods=["GET"])
@require_api_key
def moon_phase():
    """Fase lunar atual + detalhes."""
    from lunar import phase_for_date
    date_str = request.args.get("date")
    target = None
    if date_str:
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
    phase = phase_for_date(target)
    return jsonify(phase)


@public_astro_bp.route("/api/v1/astrology/moon/calendar", methods=["GET"])
@require_api_key
def moon_calendar():
    """Calendário lunar para período."""
    from lunar import calendar_range
    from_str = request.args.get("from", "")
    to_str = request.args.get("to", "")

    now = datetime.now(timezone.utc)
    try:
        from_date = datetime.strptime(from_str, "%Y-%m-%d") if from_str else now
    except ValueError:
        from_date = now
    try:
        to_date = datetime.strptime(to_str, "%Y-%m-%d") if to_str else now.replace(
            month=now.month + 1 if now.month < 12 else 1,
            year=now.year if now.month < 12 else now.year + 1,
        )
    except ValueError:
        to_date = now

    events = calendar_range(from_date=from_date, to_date=to_date)
    return jsonify({"from": from_date.strftime("%Y-%m-%d"), "to": to_date.strftime("%Y-%m-%d"), "events": events})


@public_astro_bp.route("/api/v1/astrology/synastry", methods=["POST"])
@require_api_key
def synastry():
    """
    Compatibilidade entre dois mapas natais.

    Body:
        {
            "person_a": {"birth_date": "1990-05-15", "name": "Ana"},
            "person_b": {"birth_date": "1988-11-22", "name": "Bruno"},
            "interpret": true
        }
    """
    body = request.get_json(silent=True) or {}
    a = body.get("person_a") or {}
    b = body.get("person_b") or {}

    if not a.get("birth_date") or not b.get("birth_date"):
        return jsonify({"error": "both_birth_dates_required"}), 422

    from astrology_lite import natal_chart_lite, chart_summary_text

    try:
        chart_a = natal_chart_lite(birth_date=datetime.strptime(a["birth_date"], "%Y-%m-%d"))
        chart_b = natal_chart_lite(birth_date=datetime.strptime(b["birth_date"], "%Y-%m-%d"))
    except ValueError:
        return jsonify({"error": "invalid_date_format"}), 422

    # Element compatibility
    element_compat = _element_compatibility(chart_a.get("sun_element", ""), chart_b.get("sun_element", ""))

    result = {
        "person_a": {"name": a.get("name", "A"), "chart": chart_a},
        "person_b": {"name": b.get("name", "B"), "chart": chart_b},
        "compatibility": {
            "element_match": element_compat,
            "sun_signs": f"{chart_a.get('sun_sign', '?')} + {chart_b.get('sun_sign', '?')}",
        },
        "interpretation": None,
    }

    if body.get("interpret") and g.api_tier in ("pro", "scale"):
        try:
            from personalizer import Personalizer
            p = Personalizer()
            if p.client:
                prompt = (
                    f"Analise a sinastria astrológica entre:\n"
                    f"A ({a.get('name', 'A')}): {chart_summary_text(chart_a)}\n"
                    f"B ({b.get('name', 'B')}): {chart_summary_text(chart_b)}\n\n"
                    f"Tom acolhedor, pt-BR, max 200 palavras. "
                    f"Fale sobre pontos de harmonia e tensão."
                )
                resp = p.client.models.generate_content(model=p.model_name, contents=prompt)
                result["interpretation"] = (resp.text or "").strip() or None
        except Exception:
            pass

    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════
# NUMEROLOGY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@public_astro_bp.route("/api/v1/numerology/full", methods=["POST"])
@require_api_key
def numerology_full():
    """
    Mapa numerológico completo.

    Body:
        {
            "name": "Maria da Silva",       // opcional
            "birth_date": "1990-05-15",     // opcional
            "interpret": true
        }
    """
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    birth_str = body.get("birth_date")

    if not name and not birth_str:
        return jsonify({"error": "name_or_birth_date_required"}), 422

    birth_date = None
    if birth_str:
        try:
            birth_date = datetime.strptime(birth_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "invalid_date_format"}), 422

    from numerology import compute_full
    result = compute_full(name=name, birth_date=birth_date)

    if body.get("interpret") and g.api_tier in ("pro", "scale"):
        try:
            from personalizer import Personalizer
            p = Personalizer()
            if p.client:
                prompt = (
                    f"Interprete este mapa numerológico em pt-BR, max 150 palavras, "
                    f"tom acolhedor:\n{result}"
                )
                resp = p.client.models.generate_content(model=p.model_name, contents=prompt)
                result["interpretation"] = (resp.text or "").strip() or None
        except Exception:
            pass

    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════
# TAROT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@public_astro_bp.route("/api/v1/tarot/draw", methods=["POST"])
@require_api_key
def tarot_draw():
    """
    Sorteia cartas de tarot com interpretação IA opcional.

    Body:
        {
            "spread": "3card",              // 1card, 3card, cross5, celtic10
            "question": "Sobre amor",       // opcional
            "interpret": true
        }
    """
    body = request.get_json(silent=True) or {}
    spread = body.get("spread", "3card")
    question = body.get("question", "")

    # Reutiliza lógica do saas/tarot.py
    from api.saas.tarot import SPREAD_TYPES

    if spread not in SPREAD_TYPES:
        return jsonify({"error": "invalid_spread", "valid": list(SPREAD_TYPES.keys())}), 422

    import random
    from db.database import SessionLocal
    from db import models

    db = SessionLocal()
    try:
        cards = db.query(models.TarotCard).filter_by(deck_id="marselha").all()
        if not cards:
            return jsonify({"error": "no_deck_available"}), 500

        spread_info = SPREAD_TYPES[spread]
        n = len(spread_info["positions"])
        chosen = random.sample(cards, min(n, len(cards)))

        result_cards = []
        for i, c in enumerate(chosen):
            reversed_ = random.random() < 0.3
            result_cards.append({
                "position": spread_info["positions"][i],
                "name": c.name,
                "arcana": c.arcana,
                "reversed": reversed_,
                "meaning": c.meaning_reversed if reversed_ else c.meaning_upright,
                "keywords": c.keywords,
                "image_url": c.image_url,
            })

        result = {
            "spread": spread,
            "spread_name": spread_info["name"],
            "cards": result_cards,
            "interpretation": None,
        }

        if body.get("interpret") and g.api_tier in ("pro", "scale"):
            from api.saas.tarot import _generate_interpretation
            result["interpretation"] = _generate_interpretation(result_cards, question, spread)

        return jsonify(result)
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

_COMPAT = {
    ("fogo", "fogo"): 85, ("fogo", "ar"): 90, ("fogo", "terra"): 50, ("fogo", "agua"): 40,
    ("ar", "ar"): 80, ("ar", "terra"): 45, ("ar", "agua"): 60,
    ("terra", "terra"): 85, ("terra", "agua"): 90,
    ("agua", "agua"): 80,
}

def _element_compatibility(el_a: str, el_b: str) -> dict:
    a, b = el_a.lower(), el_b.lower()
    score = _COMPAT.get((a, b)) or _COMPAT.get((b, a)) or 50
    if score >= 80:
        label = "alta"
    elif score >= 60:
        label = "moderada"
    else:
        label = "baixa"
    return {"elements": [a, b], "score": score, "label": label}

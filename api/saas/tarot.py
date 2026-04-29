"""
Tarot virtual endpoints (Frente 4.7-4.10).

GET  /saas/tarot/decks                       — lista decks disponíveis
GET  /saas/tarot/decks/<id>/cards            — lista cartas do deck
POST /saas/tarot/draw                        — sorteia tiragem
POST /saas/tarot/readings                    — salva tiragem + interpreta com IA
GET  /saas/tarot/readings?lead_id=&limit=    — histórico
GET  /saas/tarot/readings/<id>               — leitura específica
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
tarot_bp = Blueprint("saas_tarot", __name__, url_prefix="/saas/tarot")


SPREAD_TYPES = {
    "1card": {"name": "Carta do dia", "positions": ["mensagem"]},
    "3card": {"name": "Passado/Presente/Futuro", "positions": ["passado", "presente", "futuro"]},
    "cross5": {"name": "Cruz simples", "positions": ["situação", "obstáculo", "passado", "presente", "futuro"]},
    "celtic10": {
        "name": "Cruz Celta",
        "positions": [
            "presente", "obstáculo", "consciente", "subconsciente",
            "passado", "futuro", "você", "ambiente", "esperanças", "resultado",
        ],
    },
}


@tarot_bp.route("/decks", methods=["GET"])
@login_required
def list_decks():
    db = SessionLocal()
    try:
        # Globais (tenant_id=null) + do tenant
        from sqlalchemy import or_
        decks = db.query(models.TarotDeck).filter(
            or_(
                models.TarotDeck.tenant_id.is_(None),
                models.TarotDeck.tenant_id == current_user.tenant_id,
            )
        ).all()
        return jsonify({
            "decks": [
                {
                    "id": d.id, "name": d.name,
                    "is_default": d.is_default,
                    "tenant_id": d.tenant_id,
                    "card_count": db.query(models.TarotCard).filter_by(deck_id=d.id).count(),
                } for d in decks
            ],
            "spreads": [
                {"key": k, **v} for k, v in SPREAD_TYPES.items()
            ],
        })
    finally:
        db.close()


@tarot_bp.route("/decks/<deck_id>/cards", methods=["GET"])
@login_required
def list_cards(deck_id: str):
    db = SessionLocal()
    try:
        cards = db.query(models.TarotCard).filter_by(deck_id=deck_id).all()
        return jsonify({
            "cards": [
                {
                    "id": c.id, "name": c.name,
                    "arcana": c.arcana, "suit": c.suit, "number": c.number,
                    "meaning_upright": c.meaning_upright,
                    "meaning_reversed": c.meaning_reversed,
                    "keywords": c.keywords,
                    "image_url": c.image_url,
                } for c in cards
            ]
        })
    finally:
        db.close()


@tarot_bp.route("/draw", methods=["POST"])
@login_required
def draw_cards():
    """
    Sorteia tiragem de cartas (sem persistir).
    Body: {spread_type, deck_id?, seed?, reversal_chance?}.

    `seed` opcional pra reprodutibilidade (lead_id+timestamp).
    `reversal_chance` 0-1, default 0.3 (30% chance reverso).
    """
    body = request.get_json(silent=True) or {}
    spread_type = body.get("spread_type") or "3card"
    deck_id = body.get("deck_id") or "marselha"
    seed_str = body.get("seed")
    reversal_chance = float(body.get("reversal_chance", 0.3))

    if spread_type not in SPREAD_TYPES:
        return jsonify({"error": "spread_type_invalid", "valid": list(SPREAD_TYPES.keys())}), 422

    spread = SPREAD_TYPES[spread_type]
    n_cards = len(spread["positions"])

    # RNG determinístico se seed fornecido (lead_id + timestamp)
    if seed_str:
        seed_int = int(hashlib.sha256(str(seed_str).encode()).hexdigest()[:16], 16)
        rng = random.Random(seed_int)
    else:
        rng = random.Random()

    db = SessionLocal()
    try:
        cards = db.query(models.TarotCard).filter_by(deck_id=deck_id).all()
        if len(cards) < n_cards:
            return jsonify({"error": "deck_too_small"}), 400

        chosen = rng.sample(cards, n_cards)
        result = []
        for i, card in enumerate(chosen):
            reversed_ = rng.random() < reversal_chance
            result.append({
                "position": spread["positions"][i],
                "card_id": card.id,
                "name": card.name,
                "arcana": card.arcana,
                "reversed": reversed_,
                "meaning": card.meaning_reversed if reversed_ else card.meaning_upright,
                "keywords": card.keywords,
                "image_url": card.image_url,
            })
        return jsonify({
            "spread_type": spread_type,
            "spread_name": spread["name"],
            "deck_id": deck_id,
            "cards": result,
        })
    finally:
        db.close()


@tarot_bp.route("/readings", methods=["POST"])
@login_required
def save_reading():
    """
    Salva tiragem + (opcional) gera interpretação via IA.
    Body: {spread_type, deck_id, cards: [...], lead_id?, question?, generate_interpretation?}.
    """
    body = request.get_json(silent=True) or {}
    spread_type = body.get("spread_type")
    deck_id = body.get("deck_id") or "marselha"
    cards = body.get("cards") or []
    lead_id = body.get("lead_id")
    question = (body.get("question") or "").strip()
    gen_interp = bool(body.get("generate_interpretation", True))

    if spread_type not in SPREAD_TYPES:
        return jsonify({"error": "spread_type_invalid"}), 422
    if not cards or not isinstance(cards, list):
        return jsonify({"error": "cards_required"}), 422

    tenant_id = current_user.tenant_id

    # Quota Gemini check (Frente 2.6) — se vai gerar interpretação
    interpretation = None
    if gen_interp:
        try:
            import quota
            allowed, _, _ = quota.consume_quota(tenant_id, "gemini_tokens_month", 2000)  # estimativa
            if not allowed:
                gen_interp = False
                logger.warning("[tarot.reading] gemini quota exceeded — skipping interpretation")
        except Exception:
            pass

    if gen_interp:
        interpretation = _generate_interpretation(cards, question, spread_type)

    db = SessionLocal()
    try:
        reading = models.TarotReading(
            tenant_id=tenant_id,
            lead_id=int(lead_id) if lead_id else None,
            attended_by_user_id=current_user.id,
            spread_type=spread_type,
            deck_id=deck_id,
            cards=cards,
            question=question or None,
            interpretation=interpretation,
        )
        db.add(reading)
        db.commit()
        db.refresh(reading)
        return jsonify({
            "ok": True,
            "id": reading.id,
            "interpretation": interpretation,
            "created_at": reading.created_at.isoformat(),
        }), 201
    finally:
        db.close()


@tarot_bp.route("/readings", methods=["GET"])
@login_required
def list_readings():
    lead_id = request.args.get("lead_id")
    limit = min(int(request.args.get("limit") or 20), 100)

    db = SessionLocal()
    try:
        q = db.query(models.TarotReading).filter_by(tenant_id=current_user.tenant_id)
        if lead_id and lead_id.isdigit():
            q = q.filter_by(lead_id=int(lead_id))
        readings = q.order_by(models.TarotReading.created_at.desc()).limit(limit).all()
        return jsonify({
            "readings": [
                {
                    "id": r.id,
                    "lead_id": r.lead_id,
                    "spread_type": r.spread_type,
                    "deck_id": r.deck_id,
                    "cards": r.cards,
                    "question": r.question,
                    "interpretation": r.interpretation,
                    "sent_to_lead": r.sent_to_lead,
                    "created_at": r.created_at.isoformat(),
                } for r in readings
            ]
        })
    finally:
        db.close()


@tarot_bp.route("/readings/<int:reading_id>/send", methods=["POST"])
@login_required
def send_reading_to_lead(reading_id: int):
    """Envia interpretacao da tiragem para o lead via WhatsApp."""
    db = SessionLocal()
    try:
        r = db.query(models.TarotReading).filter_by(
            id=reading_id, tenant_id=current_user.tenant_id,
        ).first()
        if not r:
            return jsonify({"error": "not_found"}), 404
        if not r.lead_id:
            return jsonify({"error": "reading_not_linked_to_lead"}), 422

        lead = db.query(models.Lead).filter_by(
            id=r.lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        cards_block = "\n".join([
            f"• {c['position'].capitalize()}: {c['name']}"
            f"{' (invertida)' if c.get('reversed') else ''}"
            for c in (r.cards or [])
        ])
        spread_name = SPREAD_TYPES.get(r.spread_type, {}).get("name", r.spread_type)
        intro = f"✦ Tiragem: {spread_name}"
        if r.question:
            intro += f"\nPergunta: {r.question}"
        body = f"{intro}\n\n{cards_block}"
        if r.interpretation:
            body += f"\n\n{r.interpretation}"

        try:
            import horoscope
            client = horoscope._get_whatsapp_client(current_user.tenant_id)
            if client is None:
                return jsonify({"error": "whatsapp_unavailable"}), 502
            ok = client.enviar_mensagem(lead.telefone, body, formato="texto")
            if not ok:
                return jsonify({"error": "send_returned_false"}), 502
        except Exception as exc:
            logger.exception("[tarot.send] falha: %s", exc)
            return jsonify({"error": "send_failed", "message": str(exc)[:200]}), 502

        from datetime import datetime, timezone as _tz
        r.sent_to_lead = True
        r.sent_at = datetime.now(_tz.utc) if hasattr(r, "sent_at") else None
        db.commit()

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="tarot.reading.sent",
                target_type="tarot_reading",
                target_id=str(r.id),
                payload={"lead_id": r.lead_id, "spread": r.spread_type},
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({"ok": True, "preview": body[:500]})
    finally:
        db.close()


@tarot_bp.route("/readings/<int:reading_id>/regenerate", methods=["POST"])
@login_required
def regenerate_interpretation(reading_id: int):
    """Regenera a interpretacao IA de uma leitura existente."""
    db = SessionLocal()
    try:
        r = db.query(models.TarotReading).filter_by(
            id=reading_id, tenant_id=current_user.tenant_id,
        ).first()
        if not r:
            return jsonify({"error": "not_found"}), 404
        if not r.cards:
            return jsonify({"error": "no_cards"}), 422

        try:
            import quota
            allowed, _, _ = quota.consume_quota(
                current_user.tenant_id, "gemini_tokens_month", 2000,
            )
            if not allowed:
                return jsonify({"error": "quota_exceeded"}), 402
        except Exception:
            pass

        new_text = _generate_interpretation(
            r.cards, r.question or "", r.spread_type,
        )
        r.interpretation = new_text
        db.commit()
        return jsonify({"ok": True, "interpretation": new_text})
    finally:
        db.close()


@tarot_bp.route("/readings/<int:reading_id>", methods=["DELETE"])
@login_required
def delete_reading(reading_id: int):
    db = SessionLocal()
    try:
        r = db.query(models.TarotReading).filter_by(
            id=reading_id, tenant_id=current_user.tenant_id,
        ).first()
        if not r:
            return jsonify({"error": "not_found"}), 404
        db.delete(r)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@tarot_bp.route("/readings/<int:reading_id>", methods=["GET"])
@login_required
def get_reading(reading_id: int):
    db = SessionLocal()
    try:
        r = db.query(models.TarotReading).filter_by(
            id=reading_id, tenant_id=current_user.tenant_id,
        ).first()
        if not r:
            return jsonify({"error": "not_found"}), 404
        return jsonify({
            "id": r.id, "lead_id": r.lead_id,
            "spread_type": r.spread_type, "deck_id": r.deck_id,
            "cards": r.cards, "question": r.question,
            "interpretation": r.interpretation,
            "sent_to_lead": r.sent_to_lead,
            "created_at": r.created_at.isoformat(),
        })
    finally:
        db.close()


# ─── IA interpretation helper ─────────────────────────────────────────


def _generate_interpretation(cards: list, question: str, spread_type: str) -> Optional[str]:
    """
    Gera interpretação via Gemini. Falha silenciosa retorna fallback estático.
    """
    try:
        from personalizer import Personalizer
        pers = Personalizer()
        if not pers.client:
            return _fallback_interpretation(cards, spread_type)

        spread_name = SPREAD_TYPES[spread_type]["name"]
        cards_block = "\n".join([
            f"{c['position'].upper()}: {c['name']} ({'invertida' if c.get('reversed') else 'em pé'}) — {c.get('meaning', '')}"
            for c in cards
        ])
        prompt = f"""Você é uma tarot reader empática e poética, falando português do Brasil.
Faça uma interpretação conectada e fluida das cartas tiradas.
Tom: acolhedor, místico, prático. Máximo 250 palavras.
Termine com 1 conselho prático.

Tipo de tiragem: {spread_name}
{f'Pergunta do consultante: "{question}"' if question else ''}

Cartas:
{cards_block}

Faça a leitura agora:"""
        response = pers.client.models.generate_content(
            model=pers.model_name,
            contents=prompt,
        )
        text = (response.text or "").strip()
        return text or _fallback_interpretation(cards, spread_type)
    except Exception as exc:
        logger.warning("[tarot.interpretation] gemini falhou: %s", exc)
        return _fallback_interpretation(cards, spread_type)


def _fallback_interpretation(cards: list, spread_type: str) -> str:
    """Concat dos significados se Gemini falhou."""
    parts = []
    for c in cards:
        parts.append(f"**{c['position'].capitalize()}** — {c['name']}: {c.get('meaning', '')}")
    return "\n\n".join(parts)

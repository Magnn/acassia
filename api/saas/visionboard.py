"""
api/saas/visionboard.py — Quadro de Visão / Manifestação com IA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vertical: Manifestation Tracker — "Visualize, afirme, manifeste"

Endpoints:
  GET  /saas/visionboard/                   — Lista itens
  POST /saas/visionboard/                   — Cria item
  PUT  /saas/visionboard/<id>               — Atualiza item
  PUT  /saas/visionboard/<id>/manifest      — Marca como manifestado
  DELETE /saas/visionboard/<id>             — Remove
  GET  /saas/visionboard/stats              — Estatísticas
  POST /saas/visionboard/generate-affirmation — Gera afirmação IA
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
visionboard_bp = Blueprint("saas_visionboard", __name__, url_prefix="/saas/visionboard")

CATEGORIES = ["amor", "prosperidade", "saude", "carreira", "espiritual", "familia", "criatividade", "viagem"]


@visionboard_bp.route("/", methods=["GET"])
@login_required
def list_items():
    category = request.args.get("category")
    db = SessionLocal()
    try:
        q = db.query(models.VisionBoardItem).filter_by(tenant_id=current_user.tenant_id)
        if category:
            q = q.filter_by(category=category)
        items = q.order_by(models.VisionBoardItem.sort_order, models.VisionBoardItem.created_at.desc()).all()
        return jsonify({
            "items": [_serialize(i) for i in items],
            "categories": CATEGORIES,
        })
    finally:
        db.close()


@visionboard_bp.route("/", methods=["POST"])
@login_required
def create_item():
    body = request.get_json(silent=True) or {}
    affirmation = (body.get("affirmation") or "").strip()
    category = (body.get("category") or "espiritual").strip().lower()
    if not affirmation:
        return jsonify({"error": "Afirmação é obrigatória"}), 422
    if category not in CATEGORIES:
        return jsonify({"error": "invalid_category", "valid": CATEGORIES}), 422

    db = SessionLocal()
    try:
        item = models.VisionBoardItem(
            tenant_id=current_user.tenant_id,
            category=category,
            affirmation=affirmation,
            description=body.get("description"),
            image_url=body.get("image_url"),
            target_date=body.get("target_date"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify({"ok": True, "id": item.id, "item": _serialize(item)}), 201
    finally:
        db.close()


@visionboard_bp.route("/<int:item_id>", methods=["PUT"])
@login_required
def update_item(item_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        item = db.query(models.VisionBoardItem).filter_by(
            id=item_id, tenant_id=current_user.tenant_id,
        ).first()
        if not item:
            return jsonify({"error": "not_found"}), 404

        for k in ("affirmation", "description", "image_url", "category", "target_date", "sort_order"):
            if k in body:
                setattr(item, k, body[k])
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@visionboard_bp.route("/<int:item_id>/manifest", methods=["PUT"])
@login_required
def manifest_item(item_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        item = db.query(models.VisionBoardItem).filter_by(
            id=item_id, tenant_id=current_user.tenant_id,
        ).first()
        if not item:
            return jsonify({"error": "not_found"}), 404

        item.is_manifested = True
        item.manifested_at = datetime.now(timezone.utc)
        item.manifestation_notes = body.get("notes", "")
        db.commit()
        return jsonify({"ok": True, "manifested_at": item.manifested_at.isoformat()})
    finally:
        db.close()


@visionboard_bp.route("/<int:item_id>", methods=["DELETE"])
@login_required
def delete_item(item_id: int):
    db = SessionLocal()
    try:
        item = db.query(models.VisionBoardItem).filter_by(
            id=item_id, tenant_id=current_user.tenant_id,
        ).first()
        if not item:
            return jsonify({"error": "not_found"}), 404
        db.delete(item)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@visionboard_bp.route("/stats", methods=["GET"])
@login_required
def board_stats():
    db = SessionLocal()
    try:
        items = db.query(models.VisionBoardItem).filter_by(
            tenant_id=current_user.tenant_id,
        ).all()

        total = len(items)
        manifested = sum(1 for i in items if i.is_manifested)
        by_category: dict[str, int] = {}
        for i in items:
            by_category[i.category] = by_category.get(i.category, 0) + 1

        return jsonify({
            "total": total,
            "manifested": manifested,
            "pending": total - manifested,
            "manifestation_rate": round(manifested / total * 100, 1) if total else 0,
            "by_category": by_category,
        })
    finally:
        db.close()


@visionboard_bp.route("/generate-affirmation", methods=["POST"])
@login_required
def generate_affirmation():
    """Gera afirmação personalizada via IA."""
    body = request.get_json(silent=True) or {}
    category = body.get("category", "espiritual")
    intention = body.get("intention", "")

    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return jsonify({"affirmation": _fallback_affirmation(category)})

        prompt = f"""Gere UMA afirmação poderosa de manifestação para a categoria "{category}".
{f'Intenção do usuário: "{intention}"' if intention else ''}

Retorne JSON estrito: {{"affirmation": "frase no presente, positiva, empoderada, 1 linha", "visualization": "descrição visual de 1-2 frases para o quadro de visão"}}

Tom: empoderado, presente, positivo. Nunca use negações. pt-BR."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 300, "temperature": 0.9},
        )
        text = (resp.text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        return jsonify(data)
    except Exception:
        return jsonify({"affirmation": _fallback_affirmation(category)})


def _fallback_affirmation(category: str) -> str:
    return {
        "amor": "Eu sou digna de amor profundo e recebo com o coração aberto",
        "prosperidade": "A abundância flui naturalmente para mim em todas as formas",
        "saude": "Meu corpo é um templo sagrado e vibra com saúde plena",
        "carreira": "Meu trabalho é minha missão e me realiza profundamente",
        "espiritual": "Eu estou conectada com a fonte infinita de sabedoria",
        "familia": "Minha família é um pilar de amor incondicional",
        "criatividade": "Minha criatividade flui livremente e transforma o mundo",
        "viagem": "O mundo é meu lar e cada jornada expande minha alma",
    }.get(category, "Eu sou luz, eu sou poder, eu sou manifestação")


def _serialize(i: models.VisionBoardItem) -> dict:
    return {
        "id": i.id,
        "category": i.category,
        "affirmation": i.affirmation,
        "description": i.description,
        "image_url": i.image_url,
        "target_date": i.target_date.isoformat() if i.target_date else None,
        "is_manifested": i.is_manifested,
        "manifested_at": i.manifested_at.isoformat() if i.manifested_at else None,
        "manifestation_notes": i.manifestation_notes,
        "sort_order": i.sort_order,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }

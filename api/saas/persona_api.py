"""
Persona presets + Glossario espiritual API (Frente 4.20 + 4.21).

Endpoints:
    GET    /saas/personas                       — lista presets
    GET    /saas/personas/<id>                  — preset completo
    GET    /saas/personas/<id>/system-prompt    — preview do system prompt

    GET    /saas/glossary                       — lista termos (global+tenant)
    POST   /saas/glossary                       — adiciona termo custom (tenant)
    PATCH  /saas/glossary/<id>                  — atualiza termo do tenant
    DELETE /saas/glossary/<id>                  — remove termo do tenant
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
persona_bp = Blueprint("saas_persona", __name__, url_prefix="/saas")


VALID_GLOSSARY_CATEGORIES = {
    "afro", "tarot", "astrologia", "espirita", "meumisterio",
    "holistica", "numerologia", "geral",
}


# ─── Personas ────────────────────────────────────────────────────────


@persona_bp.route("/personas", methods=["GET"])
@login_required
def list_personas():
    import persona_presets
    return jsonify({"personas": persona_presets.list_personas()})


@persona_bp.route("/personas/<persona_id>", methods=["GET"])
@login_required
def get_persona(persona_id: str):
    import persona_presets
    p = persona_presets.get_persona(persona_id)
    if not p:
        return jsonify({"error": "not_found"}), 404
    return jsonify(p)


@persona_bp.route("/personas/<persona_id>/system-prompt", methods=["GET"])
@login_required
def preview_system_prompt(persona_id: str):
    """
    Preview do system prompt completo (persona + glossario do tenant).
    Util pra UI mostrar 'isso e o que vai pro Gemini'.
    """
    import persona_presets
    include_glossary = request.args.get("include_glossary", "1") in ("1", "true")

    p = persona_presets.get_persona(persona_id)
    if not p:
        return jsonify({"error": "not_found"}), 404

    glossary_terms = []
    if include_glossary:
        db = SessionLocal()
        try:
            rows = db.query(models.SpiritualGlossaryTerm).filter(
                or_(
                    models.SpiritualGlossaryTerm.tenant_id.is_(None),
                    models.SpiritualGlossaryTerm.tenant_id == current_user.tenant_id,
                ),
            ).order_by(
                models.SpiritualGlossaryTerm.importance.desc(),
            ).limit(50).all()
            glossary_terms = [
                {"term": r.term, "definition": r.definition, "category": r.category}
                for r in rows
            ]
        finally:
            db.close()

    prompt = persona_presets.build_system_prompt(persona_id, glossary_terms=glossary_terms)
    return jsonify({
        "persona_id": persona_id,
        "label": p["label"],
        "system_prompt": prompt,
        "glossary_terms_count": len(glossary_terms),
        "chars": len(prompt),
    })


# ─── Glossary ────────────────────────────────────────────────────────


def _serialize_term(t: models.SpiritualGlossaryTerm) -> dict:
    return {
        "id": t.id,
        "term": t.term,
        "definition": t.definition,
        "category": t.category,
        "importance": t.importance,
        "is_global": t.tenant_id is None,
        "usage_examples": t.usage_examples,
        "created_at": t.created_at.isoformat(),
    }


@persona_bp.route("/glossary", methods=["GET"])
@login_required
def list_glossary():
    category = (request.args.get("category") or "").strip().lower() or None
    search = (request.args.get("search") or "").strip().lower()
    only_custom = request.args.get("only_custom") in ("1", "true")

    db = SessionLocal()
    try:
        if only_custom:
            q = db.query(models.SpiritualGlossaryTerm).filter(
                models.SpiritualGlossaryTerm.tenant_id == current_user.tenant_id,
            )
        else:
            q = db.query(models.SpiritualGlossaryTerm).filter(
                or_(
                    models.SpiritualGlossaryTerm.tenant_id.is_(None),
                    models.SpiritualGlossaryTerm.tenant_id == current_user.tenant_id,
                ),
            )
        if category:
            q = q.filter_by(category=category)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    models.SpiritualGlossaryTerm.term.ilike(like),
                    models.SpiritualGlossaryTerm.definition.ilike(like),
                ),
            )
        items = q.order_by(
            models.SpiritualGlossaryTerm.importance.desc(),
            models.SpiritualGlossaryTerm.term.asc(),
        ).all()
        return jsonify({
            "items": [_serialize_term(t) for t in items],
            "total": len(items),
        })
    finally:
        db.close()


@persona_bp.route("/glossary", methods=["POST"])
@login_required
def create_term():
    body = request.get_json(silent=True) or {}
    term = (body.get("term") or "").strip()
    definition = (body.get("definition") or "").strip()
    category = (body.get("category") or "geral").strip().lower()
    importance = body.get("importance", 5)

    if not term or len(term) < 2:
        return jsonify({"error": "term_too_short"}), 422
    if not definition or len(definition) < 10:
        return jsonify({"error": "definition_too_short"}), 422
    if category not in VALID_GLOSSARY_CATEGORIES:
        return jsonify({
            "error": "category_invalid",
            "valid": sorted(VALID_GLOSSARY_CATEGORIES),
        }), 422
    try:
        importance = int(importance)
        if not 1 <= importance <= 10:
            importance = 5
    except (TypeError, ValueError):
        importance = 5

    db = SessionLocal()
    try:
        # Evita duplicar termo do tenant
        dup = db.query(models.SpiritualGlossaryTerm).filter_by(
            tenant_id=current_user.tenant_id,
            term=term,
        ).first()
        if dup:
            return jsonify({"error": "term_already_exists", "id": dup.id}), 409

        t = models.SpiritualGlossaryTerm(
            tenant_id=current_user.tenant_id,
            term=term[:100],
            definition=definition[:2000],
            category=category,
            importance=importance,
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return jsonify({"ok": True, "term": _serialize_term(t)}), 201
    finally:
        db.close()


@persona_bp.route("/glossary/<int:term_id>", methods=["PATCH"])
@login_required
def update_term(term_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        t = db.query(models.SpiritualGlossaryTerm).filter_by(
            id=term_id, tenant_id=current_user.tenant_id,
        ).first()
        if not t:
            return jsonify({"error": "not_found_or_global"}), 404

        if "term" in body:
            v = (body["term"] or "").strip()
            if len(v) >= 2:
                t.term = v[:100]
        if "definition" in body:
            v = (body["definition"] or "").strip()
            if len(v) >= 10:
                t.definition = v[:2000]
        if "category" in body:
            c = (body["category"] or "").strip().lower()
            if c in VALID_GLOSSARY_CATEGORIES:
                t.category = c
        if "importance" in body:
            try:
                imp = int(body["importance"])
                if 1 <= imp <= 10:
                    t.importance = imp
            except (TypeError, ValueError):
                pass

        db.commit()
        return jsonify({"ok": True, "term": _serialize_term(t)})
    finally:
        db.close()


@persona_bp.route("/glossary/<int:term_id>", methods=["DELETE"])
@login_required
def delete_term(term_id: int):
    db = SessionLocal()
    try:
        t = db.query(models.SpiritualGlossaryTerm).filter_by(
            id=term_id, tenant_id=current_user.tenant_id,
        ).first()
        if not t:
            return jsonify({"error": "not_found_or_global"}), 404
        db.delete(t)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

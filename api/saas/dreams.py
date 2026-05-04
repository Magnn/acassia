"""
api/saas/dreams.py — Interpretador de Sonhos com IA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vertical: Dream Interpreter — "Decodifique o que sua mente tenta dizer"

Combina:
  - Simbologia junguiana
  - Contexto espiritual (fase da lua, signo)
  - Tarô (carta que representa o sonho)
  - Padrões recorrentes entre sonhos do usuário

Endpoints:
  GET  /saas/dreams/           — Lista sonhos
  POST /saas/dreams/           — Registra + interpreta sonho
  GET  /saas/dreams/<id>       — Detalhes
  GET  /saas/dreams/patterns   — Padrões recorrentes
  DELETE /saas/dreams/<id>     — Remove
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone, date

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
dreams_bp = Blueprint("saas_dreams", __name__, url_prefix="/saas/dreams")


@dreams_bp.route("/", methods=["GET"])
@login_required
def list_dreams():
    limit = min(int(request.args.get("limit") or 20), 100)
    page = max(int(request.args.get("page") or 1), 1)
    db = SessionLocal()
    try:
        q = db.query(models.DreamEntry).filter_by(tenant_id=current_user.tenant_id)
        total = q.count()
        entries = q.order_by(models.DreamEntry.created_at.desc()) \
            .offset((page - 1) * limit).limit(limit).all()
        return jsonify({
            "entries": [_serialize(e) for e in entries],
            "total": total,
            "page": page,
            "pages": max(1, (total + limit - 1) // limit),
        })
    finally:
        db.close()


@dreams_bp.route("/", methods=["POST"])
@login_required
def create_dream():
    """
    Registra sonho e gera interpretação IA.

    Body:
        {
            "content": "Eu estava voando sobre um oceano...",
            "dream_date": "2026-05-04",
            "lucidity_level": 3
        }
    """
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content or len(content) < 10:
        return jsonify({"error": "Relato do sonho muito curto (mín. 10 caracteres)"}), 422

    db = SessionLocal()
    try:
        # Fase da lua
        moon_phase = None
        try:
            from lunar import phase_for_date
            moon = phase_for_date()
            moon_phase = moon.get("phase_name")
        except Exception:
            pass

        # Signo do tenant owner
        sign = None
        lead = db.query(models.Lead).filter_by(tenant_id=current_user.tenant_id).first()
        if lead and lead.signo:
            sign = lead.signo

        # Buscar sonhos anteriores para padrões
        prev_dreams = db.query(models.DreamEntry).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.DreamEntry.created_at.desc()).limit(5).all()
        prev_symbols = []
        for d in prev_dreams:
            if d.symbols:
                prev_symbols.extend(d.symbols if isinstance(d.symbols, list) else [])

        # Gerar interpretação IA
        interpretation_data = _interpret_dream(content, moon_phase, sign, prev_symbols)

        dream_date = None
        if body.get("dream_date"):
            try:
                dream_date = date.fromisoformat(body["dream_date"])
            except Exception:
                dream_date = date.today()

        entry = models.DreamEntry(
            tenant_id=current_user.tenant_id,
            content=content,
            title=interpretation_data.get("title", "Sonho sem título"),
            dream_date=dream_date or date.today(),
            symbols=interpretation_data.get("symbols", []),
            interpretation=interpretation_data.get("interpretation"),
            emotional_tone=interpretation_data.get("emotional_tone"),
            archetype=interpretation_data.get("archetype"),
            recurring_themes=interpretation_data.get("recurring_themes", []),
            lucidity_level=body.get("lucidity_level"),
            moon_phase=moon_phase,
            sign=sign,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        return jsonify({"ok": True, "id": entry.id, "dream": _serialize(entry)}), 201
    finally:
        db.close()


@dreams_bp.route("/<int:dream_id>", methods=["GET"])
@login_required
def get_dream(dream_id: int):
    db = SessionLocal()
    try:
        entry = db.query(models.DreamEntry).filter_by(
            id=dream_id, tenant_id=current_user.tenant_id,
        ).first()
        if not entry:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_serialize(entry))
    finally:
        db.close()


@dreams_bp.route("/<int:dream_id>", methods=["DELETE"])
@login_required
def delete_dream(dream_id: int):
    db = SessionLocal()
    try:
        entry = db.query(models.DreamEntry).filter_by(
            id=dream_id, tenant_id=current_user.tenant_id,
        ).first()
        if not entry:
            return jsonify({"error": "not_found"}), 404
        db.delete(entry)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@dreams_bp.route("/patterns", methods=["GET"])
@login_required
def dream_patterns():
    """Retorna padrões recorrentes nos sonhos do usuário."""
    db = SessionLocal()
    try:
        entries = db.query(models.DreamEntry).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.DreamEntry.created_at.desc()).limit(50).all()

        # Agregar símbolos
        symbol_count: dict[str, int] = {}
        archetype_count: dict[str, int] = {}
        tone_count: dict[str, int] = {}

        for e in entries:
            if e.symbols and isinstance(e.symbols, list):
                for s in e.symbols:
                    symbol_count[s] = symbol_count.get(s, 0) + 1
            if e.archetype:
                archetype_count[e.archetype] = archetype_count.get(e.archetype, 0) + 1
            if e.emotional_tone:
                tone_count[e.emotional_tone] = tone_count.get(e.emotional_tone, 0) + 1

        return jsonify({
            "total_dreams": len(entries),
            "top_symbols": sorted(symbol_count.items(), key=lambda x: -x[1])[:15],
            "top_archetypes": sorted(archetype_count.items(), key=lambda x: -x[1])[:5],
            "emotional_tones": sorted(tone_count.items(), key=lambda x: -x[1])[:8],
        })
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────

def _interpret_dream(content: str, moon_phase: str | None, sign: str | None, prev_symbols: list) -> dict:
    """Interpreta sonho usando IA."""
    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return _fallback_interpretation(content)

        prev_context = ""
        if prev_symbols:
            unique = list(set(prev_symbols))[:10]
            prev_context = f"\nSímbolos de sonhos anteriores do usuário (busque padrões): {', '.join(unique)}"

        prompt = f"""Você é um analista de sonhos especialista em simbologia junguiana e espiritual.

Sonho relatado:
"{content}"

Contexto:
- Fase da lua: {moon_phase or "desconhecida"}
- Signo solar: {sign or "desconhecido"}{prev_context}

Retorne JSON estrito (sem markdown):
{{
  "title": "título poético/evocativo do sonho em 3-5 palavras",
  "symbols": ["símbolo1", "símbolo2", "símbolo3"],
  "interpretation": "interpretação profunda de 3-5 frases combinando simbologia junguiana + espiritual + contexto lunar/astrológico",
  "emotional_tone": "uma palavra: medo, alegria, confusao, nostalgia, libertacao, transformacao, poder, vulnerabilidade",
  "archetype": "sombra, anima, animus, self, trickster, grande_mae, velho_sabio, heroi, crianca_divina",
  "recurring_themes": ["tema1", "tema2"],
  "tarot_suggestion": "nome da carta de tarô que mais se conecta com este sonho",
  "action_suggestion": "uma ação prática que o sonhador pode fazer hoje baseada neste sonho (1 frase)"
}}

Tom: profundo, acolhedor, não julgador. Valide a experiência onírica. pt-BR."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 1200, "temperature": 0.8},
        )
        text = (resp.text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(cleaned)

    except Exception as exc:
        logger.warning("[dreams.interpret] IA falhou: %s", exc)
        return _fallback_interpretation(content)


def _fallback_interpretation(content: str) -> dict:
    words = content.lower().split()
    symbols = []
    symbol_map = {
        "água": ["água", "mar", "oceano", "rio", "chuva", "lago"],
        "voar": ["voar", "voando", "voo"],
        "queda": ["cair", "caindo", "queda"],
        "casa": ["casa", "quarto", "porta"],
        "animal": ["cobra", "gato", "cachorro", "pássaro", "lobo"],
        "luz": ["luz", "sol", "brilho", "estrela"],
        "escuridão": ["escuro", "noite", "sombra", "trevas"],
    }
    for sym, keys in symbol_map.items():
        if any(k in words for k in keys):
            symbols.append(sym)
    if not symbols:
        symbols = ["inconsciente", "jornada"]

    return {
        "title": "Mensagem do Inconsciente",
        "symbols": symbols[:5],
        "interpretation": "Seu sonho carrega símbolos profundos do inconsciente. Os elementos que apareceram representam aspectos da sua psique buscando integração. Preste atenção nas emoções que sentiu — elas são a chave para compreender a mensagem.",
        "emotional_tone": "reflexao",
        "archetype": "self",
        "recurring_themes": ["autoconhecimento"],
    }


def _serialize(e: models.DreamEntry) -> dict:
    return {
        "id": e.id,
        "content": e.content,
        "title": e.title,
        "dream_date": e.dream_date.isoformat() if e.dream_date else None,
        "symbols": e.symbols or [],
        "interpretation": e.interpretation,
        "emotional_tone": e.emotional_tone,
        "archetype": e.archetype,
        "recurring_themes": e.recurring_themes or [],
        "lucidity_level": e.lucidity_level,
        "moon_phase": e.moon_phase,
        "sign": e.sign,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }

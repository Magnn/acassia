"""
Compose box features: quick replies + AI suggestions (Frente 3.11-3.13).

Quick replies CRUD:
    GET    /saas/quick-replies                         — lista
    POST   /saas/quick-replies                         — cria
    PATCH  /saas/quick-replies/<id>                    — atualiza
    DELETE /saas/quick-replies/<id>                    — remove
    POST   /saas/quick-replies/<id>/render             — substitui placeholders pra um lead

AI suggestions (3.13):
    POST   /saas/inbox/<lead_id>/ai-suggestions        — gera 3 sugestoes baseadas
                                                          no historico recente.
                                                          Cache 5min em memoria local
                                                          + quota gemini check.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
compose_bp = Blueprint("saas_compose", __name__, url_prefix="/saas")


PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
VALID_CATEGORIES = {"saudacao", "oferta", "fechamento", "recuperacao", "outro"}
SUGGESTION_CACHE: dict[tuple[str, int], tuple[float, list[dict]]] = {}
SUGGESTION_TTL_SEC = 300  # 5 minutos


def _serialize_quick_reply(q: models.QuickReply) -> dict:
    return {
        "id": q.id,
        "title": q.title,
        "body": q.body,
        "category": q.category,
        "shortcut_number": q.shortcut_number,
        "usage_count": q.usage_count,
        "created_at": q.created_at.isoformat(),
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
    }


def _render_template(body: str, lead: models.Lead | None) -> str:
    """Substitui {{nome}}, {{signo}} etc com dados do lead."""
    if lead is None:
        return body
    placeholders = {
        "nome": lead.nome or "",
        "telefone": lead.telefone or "",
        "signo": lead.signo or "",
        "primeiro_nome": (lead.nome or "").split(" ")[0] if lead.nome else "",
    }
    return PLACEHOLDER_RE.sub(
        lambda m: placeholders.get(m.group(1).lower(), m.group(0)),
        body,
    )


# ─── Quick replies CRUD ──────────────────────────────────────────────


@compose_bp.route("/quick-replies", methods=["GET"])
@login_required
def list_quick_replies():
    db = SessionLocal()
    try:
        items = db.query(models.QuickReply).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(
            models.QuickReply.shortcut_number.is_(None),
            models.QuickReply.shortcut_number.asc(),
            models.QuickReply.usage_count.desc(),
        ).all()
        return jsonify({"quick_replies": [_serialize_quick_reply(q) for q in items]})
    finally:
        db.close()


@compose_bp.route("/quick-replies", methods=["POST"])
@login_required
def create_quick_reply():
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    text = (body.get("body") or "").strip()
    category = (body.get("category") or "outro").strip().lower()
    shortcut = body.get("shortcut_number")

    if not title or len(title) < 3:
        return jsonify({"error": "title_too_short"}), 422
    if not text:
        return jsonify({"error": "body_required"}), 422
    if category not in VALID_CATEGORIES:
        return jsonify({"error": "category_invalid", "valid": sorted(VALID_CATEGORIES)}), 422
    if shortcut is not None:
        try:
            shortcut = int(shortcut)
            if not 1 <= shortcut <= 9:
                return jsonify({"error": "shortcut_out_of_range"}), 422
        except (TypeError, ValueError):
            return jsonify({"error": "shortcut_invalid"}), 422

    db = SessionLocal()
    try:
        # Se shortcut definido, libera de outro template (1 atalho por tenant)
        if shortcut is not None:
            current = db.query(models.QuickReply).filter_by(
                tenant_id=current_user.tenant_id,
                shortcut_number=shortcut,
            ).first()
            if current:
                current.shortcut_number = None
                db.commit()

        q = models.QuickReply(
            tenant_id=current_user.tenant_id,
            title=title[:120],
            body=text,
            category=category,
            shortcut_number=shortcut,
            created_by=current_user.id,
        )
        db.add(q)
        db.commit()
        db.refresh(q)
        return jsonify({"ok": True, "quick_reply": _serialize_quick_reply(q)}), 201
    finally:
        db.close()


@compose_bp.route("/quick-replies/<int:qr_id>", methods=["PATCH"])
@login_required
def update_quick_reply(qr_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        q = db.query(models.QuickReply).filter_by(
            id=qr_id, tenant_id=current_user.tenant_id,
        ).first()
        if not q:
            return jsonify({"error": "not_found"}), 404

        if "title" in body:
            t = (body["title"] or "").strip()
            if len(t) >= 3:
                q.title = t[:120]
        if "body" in body:
            b = (body["body"] or "").strip()
            if b:
                q.body = b
        if "category" in body:
            c = (body["category"] or "").strip().lower()
            if c in VALID_CATEGORIES:
                q.category = c
        if "shortcut_number" in body:
            sc = body["shortcut_number"]
            if sc is None:
                q.shortcut_number = None
            else:
                try:
                    sc = int(sc)
                    if not 1 <= sc <= 9:
                        return jsonify({"error": "shortcut_out_of_range"}), 422
                except (TypeError, ValueError):
                    return jsonify({"error": "shortcut_invalid"}), 422
                # libera shortcut do outro template
                other = db.query(models.QuickReply).filter(
                    models.QuickReply.tenant_id == current_user.tenant_id,
                    models.QuickReply.shortcut_number == sc,
                    models.QuickReply.id != q.id,
                ).first()
                if other:
                    other.shortcut_number = None
                q.shortcut_number = sc

        q.updated_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "quick_reply": _serialize_quick_reply(q)})
    finally:
        db.close()


@compose_bp.route("/quick-replies/<int:qr_id>", methods=["DELETE"])
@login_required
def delete_quick_reply(qr_id: int):
    db = SessionLocal()
    try:
        q = db.query(models.QuickReply).filter_by(
            id=qr_id, tenant_id=current_user.tenant_id,
        ).first()
        if not q:
            return jsonify({"error": "not_found"}), 404
        db.delete(q)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@compose_bp.route("/quick-replies/<int:qr_id>/render", methods=["POST"])
@login_required
def render_quick_reply(qr_id: int):
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")

    db = SessionLocal()
    try:
        q = db.query(models.QuickReply).filter_by(
            id=qr_id, tenant_id=current_user.tenant_id,
        ).first()
        if not q:
            return jsonify({"error": "not_found"}), 404

        lead = None
        if lead_id:
            lead = db.query(models.Lead).filter_by(
                id=int(lead_id), tenant_id=current_user.tenant_id,
            ).first()

        text = _render_template(q.body, lead)
        # Increment usage
        q.usage_count = (q.usage_count or 0) + 1
        db.commit()
        return jsonify({"ok": True, "text": text})
    finally:
        db.close()


# ─── AI suggestions ──────────────────────────────────────────────────


@compose_bp.route("/inbox/<int:lead_id>/ai-suggestions", methods=["POST"])
@login_required
def ai_suggestions(lead_id: int):
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force"))

    cache_key = (current_user.tenant_id, lead_id)
    if not force:
        cached = SUGGESTION_CACHE.get(cache_key)
        if cached and (time.time() - cached[0]) < SUGGESTION_TTL_SEC:
            return jsonify({"ok": True, "suggestions": cached[1], "cached": True})

    # Quota check
    try:
        import quota
        allowed, _, _ = quota.consume_quota(
            current_user.tenant_id, "gemini_tokens_month", 1500,
        )
        if not allowed:
            return jsonify({
                "error": "quota_exceeded",
                "message": "Limite Gemini do periodo atingido",
            }), 402
    except Exception:
        pass

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        # Ultimas 10 mensagens
        msgs = db.query(models.Mensagem).filter_by(
            lead_id=lead_id,
        ).order_by(models.Mensagem.timestamp.desc()).limit(10).all()
        msgs = list(reversed(msgs))

        suggestions = _generate_suggestions(lead, msgs)
        SUGGESTION_CACHE[cache_key] = (time.time(), suggestions)
        return jsonify({"ok": True, "suggestions": suggestions, "cached": False})
    finally:
        db.close()


def _generate_suggestions(lead: models.Lead, msgs: list[models.Mensagem]) -> list[dict]:
    """
    Gera 3 sugestoes via Gemini. Fallback: 3 templates genericos.
    """
    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            raise RuntimeError("personalizer_unavailable")

        history = "\n".join([
            f"{'Lead' if m.remetente == 'lead' else 'Bot'}: {(m.texto or '')[:200]}"
            for m in msgs
        ]) or "(sem historico)"

        contexto = []
        if lead.nome:
            contexto.append(f"nome: {lead.nome}")
        if lead.signo:
            contexto.append(f"signo: {lead.signo}")
        if lead.score_band:
            contexto.append(f"interesse: {lead.score_band}")
        if lead.ultima_intencao:
            contexto.append(f"intencao recente: {lead.ultima_intencao}")
        ctx_line = "; ".join(contexto) or "(sem contexto)"

        prompt = (
            "Voce e atendente humana de uma cigana/taroteira no WhatsApp. "
            "Sua tarefa: sugerir 3 respostas curtas (max 200 chars cada) que continuem "
            "naturalmente a conversa. Use tom acolhedor, mistico, em portugues do Brasil. "
            "Cada sugestao deve ter um angulo diferente (uma pratica, uma emocional, uma com cta sutil).\n\n"
            f"Lead: {ctx_line}\n\nHistorico recente:\n{history}\n\n"
            "Responda em JSON: {\"suggestions\": [\"...\", \"...\", \"...\"]}. "
            "Apenas o JSON, sem texto extra."
        )
        resp = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 500, "temperature": 0.95,
                    "response_mime_type": "application/json"},
        )
        text = (resp.text or "").strip()
        import json
        parsed = json.loads(text)
        items = parsed.get("suggestions") if isinstance(parsed, dict) else None
        if not items or not isinstance(items, list):
            raise ValueError("invalid_format")
        return [
            {"text": (s or "").strip()[:280], "tone": _detect_tone(s or "")}
            for s in items[:3] if s
        ]
    except Exception as exc:
        logger.warning("[compose.suggestions] fallback: %s", exc)
        return _fallback_suggestions(lead)


def _detect_tone(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ("clique", "garante", "ultima", "vagas", "agora")):
        return "cta"
    if "?" in t:
        return "pergunta"
    if any(w in t for w in ("entendo", "sinto", "compreendo", "te abraco")):
        return "empatico"
    return "conexao"


def _fallback_suggestions(lead: models.Lead) -> list[dict]:
    primeiro = (lead.nome or "querida").split(" ")[0]
    return [
        {"text": f"{primeiro}, sinto que voce esta pronta pra dar o proximo passo. Posso te guiar?", "tone": "empatico"},
        {"text": "Quer que eu faca uma tiragem rapida agora pra te orientar?", "tone": "pergunta"},
        {"text": "O universo conspira a seu favor — me conta mais sobre o que esta sentindo.", "tone": "conexao"},
    ]

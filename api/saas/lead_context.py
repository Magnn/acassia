"""
Lead context extras (Frente 3.18 / 3.21 / 3.23):

PATCH  /saas/inbox/<lead_id>/profile          — atualiza campos editaveis
GET    /saas/inbox/<lead_id>/notes            — lista notas
POST   /saas/inbox/<lead_id>/notes            — cria nota
PATCH  /saas/inbox/<lead_id>/notes/<id>       — edita nota
DELETE /saas/inbox/<lead_id>/notes/<id>       — remove nota
POST   /saas/inbox/<lead_id>/next-action      — IA sugere proxima acao (cache 10min)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
lead_context_bp = Blueprint("saas_lead_context", __name__, url_prefix="/saas/inbox")

NEXT_ACTION_CACHE: dict[tuple[str, int], tuple[float, dict]] = {}
NEXT_ACTION_TTL_SEC = 600  # 10 minutos

EDITABLE_FIELDS = {"nome", "signo", "idade", "cidade", "email", "tags", "custom_fields"}


def _serialize_note(n: models.LeadNote) -> dict:
    return {
        "id": n.id,
        "content": n.content,
        "author_user_id": n.author_user_id,
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


def _get_lead_or_404(db, lead_id: int):
    return db.query(models.Lead).filter_by(
        id=lead_id, tenant_id=current_user.tenant_id,
    ).first()


# ─── Profile edit ─────────────────────────────────────────────────────


@lead_context_bp.route("/<int:lead_id>/profile", methods=["PATCH"])
@login_required
def patch_profile(lead_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        changes: dict = {}
        if "nome" in body:
            v = (body.get("nome") or "").strip() or None
            if v != lead.nome:
                lead.nome = v[:200] if v else None
                changes["nome"] = v
        if "signo" in body:
            v = (body.get("signo") or "").strip() or None
            if v != lead.signo:
                lead.signo = v[:20] if v else None
                changes["signo"] = v
        if "idade" in body:
            raw = body.get("idade")
            try:
                v = int(raw) if raw not in (None, "") else None
                if v is not None and not (0 <= v <= 150):
                    return jsonify({"error": "idade_invalid"}), 422
                if v != lead.idade:
                    lead.idade = v
                    changes["idade"] = v
            except (TypeError, ValueError):
                return jsonify({"error": "idade_invalid"}), 422
        if "cidade" in body:
            v = (body.get("cidade") or "").strip() or None
            if v != lead.cidade:
                lead.cidade = v[:120] if v else None
                changes["cidade"] = v
        if "email" in body:
            v = (body.get("email") or "").strip() or None
            if v != lead.email:
                lead.email = v[:200] if v else None
                changes["email"] = v
        if "tags" in body:
            tags = body.get("tags")
            if isinstance(tags, list):
                clean = [
                    str(t).strip().lower()[:40]
                    for t in tags
                    if isinstance(t, str) and str(t).strip()
                ][:30]
                lead.tags = clean
                changes["tags"] = clean
        if "custom_fields" in body:
            cf = body.get("custom_fields")
            if isinstance(cf, dict):
                # Sanitiza: max 30 chaves, valores str/num/bool
                clean: dict = {}
                for k, v in list(cf.items())[:30]:
                    key = str(k).strip()[:40]
                    if not key:
                        continue
                    if isinstance(v, (str, int, float, bool)):
                        clean[key] = v if not isinstance(v, str) else v[:500]
                lead.custom_fields = clean
                changes["custom_fields"] = clean

        if not changes:
            return jsonify({"ok": True, "no_changes": True})

        lead.atualizado_em = datetime.now(timezone.utc)
        db.commit()

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="lead.profile.updated",
                target_type="lead",
                target_id=str(lead.id),
                payload={"fields": list(changes.keys())},
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({"ok": True, "changes": changes})
    finally:
        db.close()


# ─── Notes CRUD ───────────────────────────────────────────────────────


@lead_context_bp.route("/<int:lead_id>/notes", methods=["GET"])
@login_required
def list_notes(lead_id: int):
    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404
        items = db.query(models.LeadNote).filter_by(
            lead_id=lead_id, tenant_id=current_user.tenant_id,
        ).order_by(models.LeadNote.updated_at.desc()).all()
        return jsonify({"notes": [_serialize_note(n) for n in items]})
    finally:
        db.close()


@lead_context_bp.route("/<int:lead_id>/notes", methods=["POST"])
@login_required
def create_note(lead_id: int):
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content_required"}), 422

    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404
        n = models.LeadNote(
            lead_id=lead_id,
            tenant_id=current_user.tenant_id,
            author_user_id=current_user.id,
            content=content[:8000],
        )
        db.add(n)
        db.commit()
        db.refresh(n)
        return jsonify({"ok": True, "note": _serialize_note(n)}), 201
    finally:
        db.close()


@lead_context_bp.route("/<int:lead_id>/notes/<int:note_id>", methods=["PATCH"])
@login_required
def update_note(lead_id: int, note_id: int):
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content_required"}), 422

    db = SessionLocal()
    try:
        n = db.query(models.LeadNote).filter_by(
            id=note_id, lead_id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not n:
            return jsonify({"error": "not_found"}), 404
        n.content = content[:8000]
        n.updated_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "note": _serialize_note(n)})
    finally:
        db.close()


@lead_context_bp.route("/<int:lead_id>/notes/<int:note_id>", methods=["DELETE"])
@login_required
def delete_note(lead_id: int, note_id: int):
    db = SessionLocal()
    try:
        n = db.query(models.LeadNote).filter_by(
            id=note_id, lead_id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not n:
            return jsonify({"error": "not_found"}), 404
        db.delete(n)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ─── Next-action suggestion ───────────────────────────────────────────


@lead_context_bp.route("/<int:lead_id>/next-action", methods=["POST"])
@login_required
def next_action(lead_id: int):
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force"))

    cache_key = (current_user.tenant_id, lead_id)
    if not force:
        cached = NEXT_ACTION_CACHE.get(cache_key)
        if cached and (time.time() - cached[0]) < NEXT_ACTION_TTL_SEC:
            return jsonify({"ok": True, "suggestion": cached[1], "cached": True})

    try:
        import quota
        allowed, _, _ = quota.consume_quota(
            current_user.tenant_id, "gemini_tokens_month", 2000,
        )
        if not allowed:
            return jsonify({"error": "quota_exceeded"}), 402
    except Exception:
        pass

    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        msgs = db.query(models.Mensagem).filter_by(
            lead_id=lead_id,
        ).order_by(models.Mensagem.timestamp.desc()).limit(15).all()
        msgs = list(reversed(msgs))

        suggestion = _generate_next_action(lead, msgs)
        NEXT_ACTION_CACHE[cache_key] = (time.time(), suggestion)
        return jsonify({"ok": True, "suggestion": suggestion, "cached": False})
    finally:
        db.close()


def _generate_next_action(lead: models.Lead, msgs: list[models.Mensagem]) -> dict:
    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            raise RuntimeError("personalizer_unavailable")

        history = "\n".join([
            f"{'Lead' if m.remetente == 'lead' else 'Bot'}: {(m.texto or '')[:200]}"
            for m in msgs
        ]) or "(sem historico)"

        ctx_bits = []
        if lead.nome: ctx_bits.append(f"nome: {lead.nome}")
        if lead.signo: ctx_bits.append(f"signo: {lead.signo}")
        if lead.score_band: ctx_bits.append(f"interesse: {lead.score_band}")
        if lead.node_atual: ctx_bits.append(f"no atual: {lead.node_atual}")
        if lead.ultima_intencao: ctx_bits.append(f"intencao: {lead.ultima_intencao}")
        if lead.tempo_sofrimento: ctx_bits.append(f"tempo dor: {lead.tempo_sofrimento}")

        prompt = (
            "Voce e supervisor de atendimento de cigana/taroteira. "
            "Analise o lead e sugira a PROXIMA ACAO concreta. "
            "Contexto:\n"
            f"{'; '.join(ctx_bits) if ctx_bits else '(pouco contexto)'}\n\n"
            f"Historico recente:\n{history}\n\n"
            "Responda em JSON com {\"summary\": \"...\", \"action\": \"...\", "
            "\"message\": \"...\"} onde:\n"
            "- summary: 1 frase curta sobre estado do lead\n"
            "- action: 1 acao concreta (ex.: 'tirar 3 cartas focadas em amor', "
            "'enviar audio de acolhimento', 'fechar venda 130')\n"
            "- message: mensagem pronta pra enviar (max 250 chars), pt-BR, "
            "tom acolhedor mistico.\n"
            "Apenas o JSON, sem texto extra."
        )
        resp = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 600, "temperature": 0.85,
                    "response_mime_type": "application/json"},
        )
        text = (resp.text or "").strip()
        import json
        parsed = json.loads(text)
        return {
            "summary": (parsed.get("summary") or "").strip()[:300],
            "action": (parsed.get("action") or "").strip()[:200],
            "message": (parsed.get("message") or "").strip()[:280],
        }
    except Exception as exc:
        logger.warning("[lead_context.next_action] fallback: %s", exc)
        return _fallback_next_action(lead)


def _fallback_next_action(lead: models.Lead) -> dict:
    band = (lead.score_band or "cold").lower()
    if band == "hot":
        return {
            "summary": "Lead engajado e pronto pra conversao",
            "action": "Enviar oferta principal com CTA direto",
            "message": "Sinto que voce ja esta pronta. Me confirma que quer dar esse passo agora?",
        }
    if band == "warm":
        return {
            "summary": "Lead morno; precisa de empurrao emocional",
            "action": "Tiragem rapida + mensagem de conexao",
            "message": "Tirei tres cartas pra voce. O universo me trouxe um sinal forte sobre o que voce ta vivendo.",
        }
    return {
        "summary": "Lead frio; aquecer com curiosidade",
        "action": "Pergunta aberta sobre o que ela busca",
        "message": "Posso te ajudar com algo especifico hoje? Me conta o que te trouxe ate aqui.",
    }

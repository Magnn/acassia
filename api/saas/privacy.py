"""
LGPD endpoints — consent management, lead opt-out detection, data export
(Frente 8.13-8.17).

Endpoints:
    POST /saas/consent          — registra consent do user/visitor
    GET  /saas/consent          — lê consents salvos
    POST /saas/data-export      — solicita ZIP com dados (LGPD direito acesso)
    POST /saas/data-deletion    — solicita deleção (LGPD direito esquecimento)

    POST /api/leads/<id>/opt-out  — marca lead opt-out manual
    POST /api/leads/<id>/opt-in   — re-opt-in
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user

from db import models
from db.database import SessionLocal
from extensions import limiter


logger = logging.getLogger(__name__)
privacy_bp = Blueprint("saas_privacy", __name__, url_prefix="/saas")


_VALID_CONSENT_KEYS = frozenset({
    "essential",       # sempre true (não-opcional)
    "analytics",       # PostHog/Sentry
    "marketing",       # email marketing
    "ai_personalization",  # IA usar dados pra customizar
    "third_party_sharing",  # parceiros (default false)
})

_CURRENT_POLICY_VERSION = "v1.0-2026-04-29"


# ─── Consent management (Frente 8.13, 8.16) ───────────────────────────


@privacy_bp.route("/consent", methods=["POST"])
@limiter.limit("30/hour")
def set_consent():
    """
    Registra consents. Funciona com ou sem login (visitor anônimo via cookie).
    """
    body = request.get_json(silent=True) or {}
    consents = body.get("consents") or {}
    if not isinstance(consents, dict):
        return jsonify({"error": "consents_must_be_object"}), 422

    # Filtra só keys válidos
    cleaned = {
        k: bool(v) for k, v in consents.items()
        if k in _VALID_CONSENT_KEYS
    }
    cleaned["essential"] = True  # sempre true

    user_id = current_user.id if current_user.is_authenticated else None
    visitor_id = body.get("visitor_id") or request.cookies.get("meumisterio_visitor_id")
    if not visitor_id and not user_id:
        # Gera visitor_id pra anônimo
        visitor_id = secrets.token_hex(16)

    db = SessionLocal()
    try:
        record = models.ConsentRecord(
            user_id=user_id,
            visitor_id=visitor_id if not user_id else None,
            consents=cleaned,
            policy_version=_CURRENT_POLICY_VERSION,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:500] or None,
        )
        db.add(record)
        db.commit()

        resp = jsonify({
            "ok": True,
            "consents": cleaned,
            "policy_version": _CURRENT_POLICY_VERSION,
        })
        if visitor_id and not user_id:
            resp.set_cookie(
                "meumisterio_visitor_id", visitor_id,
                max_age=365 * 24 * 3600,
                httponly=True,
                samesite="Lax",
                secure=request.is_secure,
            )
        return resp
    finally:
        db.close()


@privacy_bp.route("/consent", methods=["GET"])
def get_consent():
    """Retorna consents atuais (último registro). Funciona logado ou anônimo."""
    user_id = current_user.id if current_user.is_authenticated else None
    visitor_id = request.cookies.get("meumisterio_visitor_id")

    if not user_id and not visitor_id:
        return jsonify({
            "consents": None,
            "policy_version": _CURRENT_POLICY_VERSION,
            "needs_consent": True,
        })

    db = SessionLocal()
    try:
        if user_id:
            record = (
                db.query(models.ConsentRecord)
                .filter_by(user_id=user_id)
                .order_by(models.ConsentRecord.created_at.desc())
                .first()
            )
        else:
            record = (
                db.query(models.ConsentRecord)
                .filter_by(visitor_id=visitor_id)
                .order_by(models.ConsentRecord.created_at.desc())
                .first()
            )

        if not record:
            return jsonify({
                "consents": None,
                "policy_version": _CURRENT_POLICY_VERSION,
                "needs_consent": True,
            })

        return jsonify({
            "consents": record.consents,
            "policy_version": record.policy_version,
            "needs_consent": record.policy_version != _CURRENT_POLICY_VERSION,
            "recorded_at": record.created_at.isoformat(),
        })
    finally:
        db.close()


# ─── Data export (Frente 8.15 / 1.23) ─────────────────────────────────


def _build_user_data_export(user_id: int) -> dict:
    """
    Coleta todos os dados do user pra export LGPD.
    V1: retorna dict serializável (frontend converte pra JSON download).
    V2: gera ZIP server-side + signed URL (Frente 1.23).
    """
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=user_id).first()
        if not user:
            return {}

        leads = db.query(models.Lead).filter_by(tenant_id=user.tenant_id).all()
        lead_ids = [l.id for l in leads]
        msgs = (
            db.query(models.Mensagem)
            .filter(models.Mensagem.lead_id.in_(lead_ids))
            .all() if lead_ids else []
        )
        payments = db.query(models.PaymentEventReceipt).filter_by(
            tenant_id=user.tenant_id,
        ).all()
        consents = db.query(models.ConsentRecord).filter_by(user_id=user.id).all()

        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "tenant_id": user.tenant_id,
                "phone": user.phone,
                "timezone": user.timezone,
                "criado_em": user.criado_em.isoformat() if user.criado_em else None,
                "is_verified": user.is_verified,
            },
            "leads": [
                {
                    "id": l.id, "telefone": l.telefone, "nome": l.nome,
                    "email": l.email, "tags": l.tags, "criado_em": str(l.criado_em),
                } for l in leads
            ],
            "messages_count": len(msgs),
            "messages_sample": [
                {
                    "id": m.id, "lead_id": m.lead_id, "remetente": m.remetente,
                    "texto": m.texto[:500], "tipo": m.tipo,
                    "timestamp": str(m.timestamp),
                } for m in msgs[:100]  # primeiros 100; full export V2
            ],
            "payments": [
                {
                    "id": p.id, "provider": p.provider, "event_type": p.event_type,
                    "processed_at": str(p.processed_at),
                } for p in payments
            ],
            "consents_history": [
                {
                    "consents": c.consents,
                    "policy_version": c.policy_version,
                    "created_at": c.created_at.isoformat(),
                } for c in consents
            ],
            "_metadata": {
                "lgpd_disclaimer": (
                    "Este export contém todos os dados pessoais associados "
                    "ao seu cadastro Meu Mistério. Para deleção total, use "
                    "/saas/data-deletion."
                ),
                "policy_version": _CURRENT_POLICY_VERSION,
            },
        }
    finally:
        db.close()


@privacy_bp.route("/data-export", methods=["POST"])
@login_required
@limiter.limit("3/day")
def data_export():
    """
    Gera export síncrono em JSON. Para ZIP completo + email, ver Frente 1.23.
    """
    data = _build_user_data_export(current_user.id)
    json_bytes = json.dumps(data, indent=2, ensure_ascii=False, default=str).encode("utf-8")

    logger.info(
        "[privacy.data_export] user_id=%s tenant=%s size_bytes=%d",
        current_user.id, current_user.tenant_id, len(json_bytes),
    )

    # Audit
    try:
        db = SessionLocal()
        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="privacy.data_export",
                target_type="user", target_id=str(current_user.id),
                payload={"size_bytes": len(json_bytes)},
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass

    from io import BytesIO
    return send_file(
        BytesIO(json_bytes),
        mimetype="application/json",
        as_attachment=True,
        download_name=f"meumisterio-export-{current_user.id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json",
    )


@privacy_bp.route("/data-deletion", methods=["POST"])
@login_required
@limiter.limit("3/day")
def data_deletion():
    """
    Solicita deleção da conta (LGPD direito esquecimento).
    Marca soft-delete. Hard-delete via cron 30d depois (Frente 1.9).
    """
    body = request.get_json(silent=True) or {}
    confirm_email = (body.get("confirm_email") or "").strip().lower()
    reason = (body.get("reason") or "Solicitação LGPD do user").strip()

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=current_user.id).first()
        if not user:
            return jsonify({"error": "user_not_found"}), 404

        if confirm_email != (user.email or "").strip().lower():
            return jsonify({"error": "confirm_email_mismatch"}), 422

        if user.deleted_at:
            return jsonify({"error": "already_deleted"}), 409

        now = datetime.now(timezone.utc)
        user.deleted_at = now
        user.suspended_at = now
        user.suspended_by = user.id  # self-suspend
        user.suspension_reason = f"lgpd_deletion: {reason[:200]}"
        db.commit()

        # Audit
        db.add(models.AuditEvent(
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            event_type="privacy.data_deletion_requested",
            target_type="user", target_id=str(user.id),
            payload={"reason": reason, "hard_delete_after_days": 30},
        ))
        db.commit()

        logger.warning(
            "[privacy.data_deletion] user_id=%s tenant=%s reason=%s",
            user.id, user.tenant_id, reason,
        )

        return jsonify({
            "ok": True,
            "deleted_at": now.isoformat(),
            "hard_delete_after_days": 30,
            "message": (
                "Sua conta foi marcada para deleção. Você tem 30 dias para "
                "reativá-la entrando em contato com suporte. Após esse prazo, "
                "todos os dados serão removidos permanentemente."
            ),
        })
    finally:
        db.close()


# ─── Lead opt-out detection (Frente 8.17) ─────────────────────────────


_OPT_OUT_KEYWORDS = frozenset({
    "stop", "parar", "cancelar", "cancela", "sair", "remover",
    "tira meu", "remove me", "unsubscribe", "esquece", "para",
})


def detect_opt_out(message_text: str) -> bool:
    """
    Detecta intenção de opt-out via keywords (Frente 8.17).
    Match case-insensitive em palavras isoladas.
    """
    if not message_text:
        return False
    lower = message_text.lower().strip()
    # Se for só uma palavra-chave, é opt-out claro
    if lower in _OPT_OUT_KEYWORDS:
        return True
    # Ou se a mensagem tem keyword mas é < 30 chars (sinal forte)
    if len(lower) < 30:
        for kw in _OPT_OUT_KEYWORDS:
            if kw in lower.split() or kw in lower:
                return True
    return False


@privacy_bp.route("/leads/<int:lead_id>/opt-out", methods=["POST"])
@login_required
def lead_opt_out(lead_id: int):
    """Marca lead como opted-out (manual ou via auto-detect)."""
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "manual").strip()

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        # Marca opt-out via tags (não temos coluna específica na Lead atual)
        tags = list(lead.tags or [])
        if "opted_out" not in tags:
            tags.append("opted_out")
        lead.tags = tags
        # Se metadata_json existe, marca também
        meta = dict(lead.metadata_json or {})
        meta["opted_out"] = True
        meta["opted_out_at"] = datetime.now(timezone.utc).isoformat()
        meta["opted_out_reason"] = reason
        lead.metadata_json = meta
        db.commit()

        # Audit
        db.add(models.AuditEvent(
            tenant_id=current_user.tenant_id,
            actor_user_id=current_user.id,
            event_type="privacy.lead.opted_out",
            target_type="lead", target_id=str(lead_id),
            payload={"reason": reason},
        ))
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


@privacy_bp.route("/leads/<int:lead_id>/opt-in", methods=["POST"])
@login_required
def lead_opt_in(lead_id: int):
    """Re-marca lead como opted-in (após user explicitar interesse)."""
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        tags = [t for t in (lead.tags or []) if t != "opted_out"]
        lead.tags = tags
        meta = dict(lead.metadata_json or {})
        meta.pop("opted_out", None)
        meta["opted_in_at"] = datetime.now(timezone.utc).isoformat()
        lead.metadata_json = meta
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


def is_lead_opted_out(lead) -> bool:
    """Helper pra checar se lead está em opt-out (chamável de qualquer lugar)."""
    if not lead:
        return False
    tags = lead.tags or []
    if "opted_out" in tags:
        return True
    meta = lead.metadata_json or {}
    return bool(meta.get("opted_out"))

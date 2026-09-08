"""
api/public/webchat.py — Webchat Widget API (Omnichannel ManyChat / ChatbotX style)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Permite incorporar um widget de chat em qualquer site/landing page de clientes SaaS:
- Cria/recupera sessão do visitante via session_id persistido no browser.
- Conecta diretamente ao motor conversacional (engine) ou suporte humano.
- Notifica o Inbox da plataforma em tempo real via SSE.
- CORS habilitado para carregamento em qualquer domínio.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, make_response
from flask_login import current_user, login_required
from db import models
from db.database import SessionLocal
from extensions import limiter

logger = logging.getLogger(__name__)
webchat_bp = Blueprint("public_webchat", __name__, url_prefix="/api/public/webchat")


_SESSION_TTL_SECONDS = 60 * 60 * 24 * 30


def _signing_key() -> bytes:
    value = (os.getenv("WEBCHAT_SIGNING_KEY") or "").strip()
    if not value:
        raise RuntimeError("WEBCHAT_SIGNING_KEY ausente")
    return value.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _signed_token(payload: dict) -> str:
    encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(_signing_key(), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64encode(signature)}"


def _verify_token(token: str, expected_kind: str) -> dict | None:
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = _b64encode(
            hmac.new(_signing_key(), encoded.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        payload = json.loads(_b64decode(encoded))
        if payload.get("kind") != expected_kind:
            return None
        expires_at = payload.get("exp")
        if expires_at is not None and int(expires_at) < int(time.time()):
            return None
        return payload
    except (TypeError, ValueError, KeyError, json.JSONDecodeError, RuntimeError):
        return None


def _allowed_origins(db, tenant_id: str) -> list[str]:
    row = db.query(models.TenantFlowVariable).filter_by(
        tenant_id=tenant_id, key="webchat.allowed_origins"
    ).first()
    raw = row.value_json if row and isinstance(row.value_json, list) else []
    return [str(value).rstrip("/") for value in raw if str(value).strip()]


def _origin_allowed(db, tenant_id: str) -> bool:
    origin = (request.headers.get("Origin") or "").rstrip("/")
    allowed = _allowed_origins(db, tenant_id)
    return bool(origin and origin in allowed)


def _tenant_exists(db, tenant_id: str) -> bool:
    return db.query(models.User.id).filter_by(tenant_id=tenant_id, is_active=True).first() is not None


def _cors_response(data, status=200, origin: str | None = None):
    resp = make_response(jsonify(data), status)
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Webchat-Session"
    return resp


def _session_from_request(body: dict | None = None) -> dict | None:
    body = body or {}
    token = (
        request.headers.get("X-Webchat-Session")
        or body.get("session_token")
        or request.args.get("session_token")
        or ""
    )
    return _verify_token(token, "webchat_session")


@webchat_bp.route("/config", methods=["GET", "PUT"])
@login_required
def webchat_config():
    """Configura origens permitidas e entrega a chave pública do widget."""
    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id
        if not _tenant_exists(db, tenant_id):
            return jsonify({"error": "tenant_not_found"}), 404
        if request.method == "PUT":
            body = request.get_json(silent=True) or {}
            origins = body.get("allowed_origins")
            if not isinstance(origins, list):
                return jsonify({"error": "allowed_origins_must_be_a_list"}), 422
            normalized = []
            for value in origins:
                origin = str(value).strip().rstrip("/")
                if not origin.startswith(("https://", "http://localhost", "http://127.0.0.1")):
                    return jsonify({"error": "invalid_origin", "origin": origin}), 422
                if origin not in normalized:
                    normalized.append(origin)
            row = db.query(models.TenantFlowVariable).filter_by(
                tenant_id=tenant_id, key="webchat.allowed_origins"
            ).first()
            if row:
                row.value_json = normalized
            else:
                db.add(models.TenantFlowVariable(
                    tenant_id=tenant_id,
                    key="webchat.allowed_origins",
                    value_json=normalized,
                ))
            db.commit()
        site_key = _signed_token({"kind": "webchat_site", "tenant_id": tenant_id})
        return jsonify({"site_key": site_key, "allowed_origins": _allowed_origins(db, tenant_id)})
    except RuntimeError as exc:
        return jsonify({"error": "webchat_not_configured", "message": str(exc)}), 503
    finally:
        db.close()


@webchat_bp.route("/<path:subpath>", methods=["OPTIONS"])
@webchat_bp.route("/", methods=["OPTIONS"])
def handle_options(subpath=None):
    origin = (request.headers.get("Origin") or "").rstrip("/")
    site_payload = _verify_token(request.args.get("site_key") or "", "webchat_site")
    session_payload = _session_from_request()
    identity = site_payload or session_payload
    if not identity:
        return _cors_response({"error": "invalid_webchat_identity"}, 403)
    db = SessionLocal()
    try:
        tenant_id = str(identity.get("tenant_id") or "")
        if not _tenant_exists(db, tenant_id) or not _origin_allowed(db, tenant_id):
            return _cors_response({"error": "origin_not_allowed"}, 403)
        return _cors_response({}, 204, origin)
    finally:
        db.close()


@webchat_bp.route("/init", methods=["POST"])
@limiter.limit("30/minute")
def init_session():
    """
    Inicializa ou recupera a sessão do visitante no widget.
    Gera session_id único se não fornecido e sincroniza histórico recente.
    """
    body = request.get_json(silent=True) or {}
    site_payload = _verify_token(body.get("site_key") or "", "webchat_site")
    if not site_payload:
        return _cors_response({"error": "invalid_site_key"}, 401)
    tenant_id = str(site_payload.get("tenant_id") or "")
    origin = (request.headers.get("Origin") or "").rstrip("/")
    resumed = _session_from_request(body)
    session_id = (
        str(resumed.get("session_id"))
        if resumed and resumed.get("tenant_id") == tenant_id
        else f"web_{uuid.uuid4().hex}"
    )

    visitor_name = (body.get("name") or "").strip() or None
    visitor_phone = (body.get("phone") or "").strip() or None

    db = SessionLocal()
    try:
        if not _tenant_exists(db, tenant_id) or not _origin_allowed(db, tenant_id):
            return _cors_response({"error": "origin_not_allowed"}, 403)
        lead = db.query(models.Lead).filter_by(
            tenant_id=tenant_id, telefone=session_id
        ).first()

        if not lead:
            tags = ["webchat"]
            custom_fields = {"channel": "webchat", "session_id": session_id}
            lead = models.Lead(
                tenant_id=tenant_id,
                telefone=session_id,
                nome=visitor_name or "Visitante Web",
                tags=tags,
                custom_fields=custom_fields,
                metadata_json={"origem": "webchat", "session_id": session_id, "visitor_phone": visitor_phone},
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
        else:
            tags = list(lead.tags) if isinstance(lead.tags, list) else []
            if "webchat" not in tags:
                tags.append("webchat")
                lead.tags = tags
                db.commit()

        # Carregar mensagens existentes
        msgs = db.query(models.Mensagem).filter_by(lead_id=lead.id).order_by(
            models.Mensagem.timestamp.asc()
        ).limit(50).all()

        messages_data = [{
            "id": m.id,
            "text": m.texto,
            "sender": "user" if m.remetente == "user" else "assistant",
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        } for m in msgs]

        session_token = _signed_token({
            "kind": "webchat_session",
            "tenant_id": tenant_id,
            "session_id": session_id,
            "exp": int(time.time()) + _SESSION_TTL_SECONDS,
        })
        return _cors_response({
            "ok": True,
            "session_id": session_id,
            "session_token": session_token,
            "lead_id": lead.id,
            "bot_pausado": bool(lead.bot_pausado),
            "messages": messages_data,
        }, origin=origin)
    except Exception as exc:
        logger.exception("[webchat] Erro em /init: %s", exc)
        return _cors_response({"error": "init_failed"}, 500, origin)
    finally:
        db.close()


@webchat_bp.route("/message", methods=["POST"])
@limiter.limit("60/minute")
def send_message():
    """
    Recebe mensagem do visitante na web.
    - Se bot_pausado == False: processa pelo motor e devolve resposta.
    - Se bot_pausado == True: armazena e aguarda operador responder pelo Inbox.
    """
    body = request.get_json(silent=True) or {}
    identity = _session_from_request(body)
    if not identity:
        return _cors_response({"error": "invalid_session"}, 401)
    tenant_id = str(identity.get("tenant_id") or "")
    session_id = str(identity.get("session_id") or "")
    origin = (request.headers.get("Origin") or "").rstrip("/")
    text = (body.get("text") or "").strip()

    if not session_id or not text:
        return _cors_response({"error": "missing_params", "message": "text é obrigatório"}, 400, origin)

    db = SessionLocal()
    try:
        if not _tenant_exists(db, tenant_id) or not _origin_allowed(db, tenant_id):
            return _cors_response({"error": "origin_not_allowed"}, 403)
        # Busca lead pelo session_id ou telefone
        lead = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.telefone == session_id,
        ).first()

        if not lead:
            lead = models.Lead(
                tenant_id=tenant_id,
                telefone=session_id,
                nome="Visitante Web",
                tags=["webchat"],
                custom_fields={"channel": "webchat", "session_id": session_id},
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)

        now = datetime.now(timezone.utc)

        # 1. Salvar mensagem do visitante
        user_msg = models.Mensagem(
            lead_id=lead.id,
            remetente="user",
            texto=text,
            tipo="texto",
            timestamp=now,
        )
        db.add(user_msg)
        lead.atualizado_em = now
        db.commit()
        db.refresh(user_msg)

        # Notificar Inbox via SSE
        try:
            from api.saas.realtime_hooks import notify_message_created
            notify_message_created(tenant_id, lead.id, {
                "id": user_msg.id,
                "texto": text,
                "remetente": "user",
                "timestamp": now.isoformat(),
            }, origin=origin)
        except Exception:
            pass

        # 2. Se o bot estiver pausado pelo operador (atendimento humano)
        if lead.bot_pausado:
            return _cors_response({
                "ok": True,
                "bot_pausado": True,
                "replies": [],
                "user_message_id": user_msg.id,
            }, origin=origin)

        # 3. Processar mensagem via motor
        replies = []
        try:
            from flask import current_app
            motor = current_app.extensions.get("flow_engine")
            if motor:
                with SessionLocal() as engine_db:
                    result = motor.processar_mensagem(
                        telefone=lead.telefone,
                        texto_recebido=text,
                        db=engine_db,
                    )
                    # Aguarda a thread da fila persistir os balões
                    import time
                    time.sleep(0.35)

                    # Busca mensagens geradas pelo motor e salvas no banco
                    new_bot_msgs = engine_db.query(models.Mensagem).filter(
                        models.Mensagem.lead_id == lead.id,
                        models.Mensagem.id > user_msg.id,
                        models.Mensagem.remetente != "user",
                    ).order_by(models.Mensagem.timestamp.asc()).all()

                    for bm in new_bot_msgs:
                        if bm.texto and bm.texto.strip():
                            replies.append(bm.texto.strip())

                    if not replies and isinstance(result, dict):
                        reply_text = result.get("mensagem") or result.get("texto") or result.get("resposta")
                        if reply_text:
                            replies.append(reply_text)
            else:
                replies.append("Olá! Recebemos sua mensagem e entraremos em contato em breve.")
        except Exception as exc:
            logger.exception("[webchat] Erro ao processar mensagem no motor: %s", exc)
            replies.append("Olá! Recebemos sua mensagem e já estamos processando. Como posso ajudar mais?")

        # Retorna respostas para exibição imediata no widget
        return _cors_response({
            "ok": True,
            "bot_pausado": False,
            "replies": replies,
            "user_message_id": user_msg.id,
        }, origin=origin)
    except Exception as exc:
        logger.exception("[webchat] Erro em /message: %s", exc)
        return _cors_response({"error": "message_failed"}, 500, origin)
    finally:
        db.close()


@webchat_bp.route("/poll", methods=["GET"])
@limiter.limit("120/minute")
def poll_messages():
    """
    Retorna mensagens novas (útil para quando o operador responde pelo Inbox).
    Query: ?tenant_id=...&session_id=...&after_id=123
    """
    identity = _session_from_request()
    if not identity:
        return _cors_response({"error": "invalid_session"}, 401)
    tenant_id = str(identity.get("tenant_id") or "")
    session_id = str(identity.get("session_id") or "")
    origin = (request.headers.get("Origin") or "").rstrip("/")
    after_id = int(request.args.get("after_id") or 0)

    if not session_id:
        return _cors_response({"error": "missing_session_id"}, 400, origin)

    db = SessionLocal()
    try:
        if not _tenant_exists(db, tenant_id) or not _origin_allowed(db, tenant_id):
            return _cors_response({"error": "origin_not_allowed"}, 403)
        lead = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.telefone == session_id,
        ).first()

        if not lead:
            return _cors_response({"messages": []}, origin=origin)

        q = db.query(models.Mensagem).filter_by(lead_id=lead.id)
        if after_id > 0:
            q = q.filter(models.Mensagem.id > after_id)

        msgs = q.order_by(models.Mensagem.timestamp.asc()).limit(30).all()

        return _cors_response({
            "messages": [{
                "id": m.id,
                "text": m.texto,
                "sender": "user" if m.remetente == "user" else "assistant",
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            } for m in msgs]
        }, origin=origin)
    finally:
        db.close()

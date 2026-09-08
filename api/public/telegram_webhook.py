"""
api/public/telegram_webhook.py — Canal Telegram Bot (Omnichannel ChatbotX style)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Permite conectar bots do Telegram ao motor e ao Inbox da Acássia:
- Cada tenant pode usar seu próprio TELEGRAM_BOT_TOKEN ou o token global.
- Recebe atualizações de mensagens do Telegram e processa no motor.
- Envia respostas de volta usando a Telegram Bot API oficial.
- Permite atendimento humano (pausar bot no Inbox).
"""

from __future__ import annotations

import logging
import os
import hmac
import secrets
import requests
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from db import models
from db.database import SessionLocal
from api.utils.tenant_secrets import decrypt_tenant_secret, encrypt_tenant_secret

logger = logging.getLogger(__name__)
telegram_bp = Blueprint("public_telegram", __name__, url_prefix="/api/webhooks/telegram")


def _get_telegram_token(tenant_id: str) -> str:
    db = SessionLocal()
    try:
        row = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key="telegram.bot_token"
        ).first()
        if row:
            return decrypt_tenant_secret(row.value_cipher, allow_plaintext_legacy=True)
    finally:
        db.close()
    token = os.getenv(f"TELEGRAM_BOT_TOKEN_{tenant_id.upper()}", "").strip()
    if not token:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return token


def _get_telegram_webhook_secret(tenant_id: str) -> str:
    db = SessionLocal()
    try:
        row = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key="telegram.webhook_secret"
        ).first()
        return decrypt_tenant_secret(row.value_cipher) if row else ""
    finally:
        db.close()


def _put_secret(db, tenant_id: str, key: str, value: str) -> None:
    row = db.query(models.TenantFlowSecret).filter_by(tenant_id=tenant_id, key=key).first()
    cipher = encrypt_tenant_secret(value)
    if row:
        row.value_cipher = cipher
    else:
        db.add(models.TenantFlowSecret(tenant_id=tenant_id, key=key, value_cipher=cipher))


@telegram_bp.route("/<tenant_id>", methods=["POST"])
def handle_telegram_update(tenant_id: str):
    """Webhook receptor de mensagens do Telegram."""
    expected_secret = _get_telegram_webhook_secret(tenant_id)
    supplied_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
    if not expected_secret or not hmac.compare_digest(supplied_secret, expected_secret):
        return jsonify({"error": "invalid_webhook_secret"}), 403
    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message")

    if not message or "text" not in message:
        return jsonify({"ok": True, "ignored": "no_text"})

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    from_user = message.get("from", {})
    first_name = from_user.get("first_name", "Usuário Telegram")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return jsonify({"ok": True, "ignored": "empty_chat_or_text"})

    tel_id = f"tg_{chat_id}"
    token = _get_telegram_token(tenant_id)

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            tenant_id=tenant_id, telefone=tel_id
        ).first()

        now = datetime.now(timezone.utc)

        if not lead:
            lead = models.Lead(
                tenant_id=tenant_id,
                telefone=tel_id,
                nome=first_name,
                tags=["telegram"],
                custom_fields={"channel": "telegram", "telegram_chat_id": chat_id},
                metadata_json={"origem": "telegram", "chat_id": chat_id},
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
        else:
            tags = list(lead.tags) if isinstance(lead.tags, list) else []
            if "telegram" not in tags:
                tags.append("telegram")
                lead.tags = tags
                db.commit()

        # Salvar mensagem do usuário
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
            })
        except Exception:
            pass

        # Se bot pausado para atendimento humano, não responde automaticamente
        if lead.bot_pausado:
            return jsonify({"ok": True, "bot_pausado": True})

        # Processar com o motor
        if token:
            try:
                from flask import current_app
                motor = current_app.extensions.get("flow_engine")
                if motor:
                    with SessionLocal() as engine_db:
                        motor.processar_mensagem(
                            telefone=lead.telefone,
                            texto_recebido=text,
                            db=engine_db,
                        )

                        # Aguardar thread de persistência
                        import time
                        time.sleep(0.35)

                        bot_msgs = engine_db.query(models.Mensagem).filter(
                            models.Mensagem.lead_id == lead.id,
                            models.Mensagem.id > user_msg.id,
                            models.Mensagem.remetente != "user",
                        ).order_by(models.Mensagem.timestamp.asc()).all()

                        for bm in bot_msgs:
                            if bm.texto and bm.texto.strip():
                                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                requests.post(
                                    send_url,
                                    json={"chat_id": chat_id, "text": bm.texto.strip()},
                                    timeout=10,
                                )
            except Exception as exc:
                logger.exception("[telegram] Erro ao processar mensagem do Telegram: %s", exc)

        return jsonify({"ok": True})
    finally:
        db.close()


@telegram_bp.route("/setup", methods=["POST"])
@login_required
def setup_telegram_webhook():
    """
    Registra a URL deste servidor como webhook oficial no Telegram:
    Payload: { "bot_token": "...", "tenant_id": "default", "server_url": "https://..." }
    """
    body = request.get_json(silent=True) or {}
    token = body.get("bot_token", "").strip()
    tenant_id = current_user.tenant_id
    server_url = (os.getenv("PUBLIC_URL") or request.host_url).strip().rstrip("/")

    if not token:
        return jsonify({"error": "missing_params", "message": "bot_token é obrigatório"}), 400

    webhook_url = f"{server_url}/api/webhooks/telegram/{tenant_id}"
    webhook_secret = secrets.token_urlsafe(32)
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"

    try:
        res = requests.post(api_url, json={
            "url": webhook_url,
            "secret_token": webhook_secret,
            "allowed_updates": ["message", "edited_message"],
        }, timeout=10)
        data = res.json()
        if res.status_code != 200 or not data.get("ok"):
            return jsonify({"ok": False, "telegram_response": data}), 422
        db = SessionLocal()
        try:
            _put_secret(db, tenant_id, "telegram.bot_token", token)
            _put_secret(db, tenant_id, "telegram.webhook_secret", webhook_secret)
            db.commit()
        finally:
            db.close()
        return jsonify({"ok": True, "telegram_response": data, "webhook_url": webhook_url})
    except Exception as exc:
        return jsonify({"error": "telegram_request_failed", "message": str(exc)}), 500

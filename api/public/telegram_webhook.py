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
import requests
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
telegram_bp = Blueprint("public_telegram", __name__, url_prefix="/api/webhooks/telegram")


def _get_telegram_token(tenant_id: str) -> str:
    # 1. Variável de ambiente específica do tenant ou global
    token = os.getenv(f"TELEGRAM_BOT_TOKEN_{tenant_id.upper()}", "").strip()
    if not token:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return token


@telegram_bp.route("/<tenant_id>", methods=["POST"])
def handle_telegram_update(tenant_id: str):
    """Webhook receptor de mensagens do Telegram."""
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
def setup_telegram_webhook():
    """
    Registra a URL deste servidor como webhook oficial no Telegram:
    Payload: { "bot_token": "...", "tenant_id": "default", "server_url": "https://..." }
    """
    body = request.get_json(silent=True) or {}
    token = body.get("bot_token", "").strip()
    tenant_id = (body.get("tenant_id") or "default").strip()
    server_url = (body.get("server_url") or "").strip()

    if not token or not server_url:
        return jsonify({"error": "missing_params", "message": "bot_token e server_url são obrigatórios"}), 400

    webhook_url = f"{server_url.rstrip('/')}/api/webhooks/telegram/{tenant_id}"
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"

    try:
        res = requests.get(api_url, timeout=10)
        data = res.json()
        return jsonify({"ok": res.status_code == 200, "telegram_response": data, "webhook_url": webhook_url})
    except Exception as exc:
        return jsonify({"error": "telegram_request_failed", "message": str(exc)}), 500

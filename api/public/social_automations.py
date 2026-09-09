"""
api/public/social_automations.py — Conectores para Instagram, Facebook, TikTok e YouTube
Permite:
  1. Auto-resposta de comentarios no Instagram e Facebook ("comente EU QUERO")
  2. Webhook receptor de mensagens e leads do TikTok Business
  3. Integracao YouTube (publicacao de shorts, notificacao de novos videos / comunidade)
"""

import hashlib
import hmac
import json
import logging
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from api.utils.tenant_secrets import decrypt_tenant_secret, encrypt_tenant_secret
from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
social_bp = Blueprint("social_automations", __name__)


def _get_variable(db, tenant_id: str, key: str, default):
    row = db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id, key=key).first()
    return row.value_json if row else default


def _put_variable(db, tenant_id: str, key: str, value) -> None:
    row = db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id, key=key).first()
    if row:
        row.value_json = value
    else:
        db.add(models.TenantFlowVariable(tenant_id=tenant_id, key=key, value_json=value))


def _get_secret(db, tenant_id: str, key: str) -> str:
    row = db.query(models.TenantFlowSecret).filter_by(tenant_id=tenant_id, key=key).first()
    if not row:
        return ""
    try:
        return decrypt_tenant_secret(row.value_cipher, allow_plaintext_legacy=False)
    except Exception:
        logger.exception("[SOCIAL_SECRET] Falha ao descriptografar tenant=%s key=%s", tenant_id, key)
        return ""


def _put_secret(db, tenant_id: str, key: str, value: str) -> None:
    row = db.query(models.TenantFlowSecret).filter_by(tenant_id=tenant_id, key=key).first()
    if not value:
        if row:
            db.delete(row)
        return
    cipher = encrypt_tenant_secret(value)
    if row:
        row.value_cipher = cipher
    else:
        db.add(models.TenantFlowSecret(tenant_id=tenant_id, key=key, value_cipher=cipher))


def _require_tenant() -> str | None:
    tenant_id = (request.args.get("tenant_id") or "").strip()
    return tenant_id or None


def _valid_meta_signature(app_secret: str) -> bool:
    supplied = request.headers.get("X-Hub-Signature-256") or ""
    expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), request.get_data(), hashlib.sha256).hexdigest()
    return bool(app_secret and hmac.compare_digest(supplied, expected))


def reply_to_instagram_comment(comment_id: str, message: str, access_token: str) -> bool:
    """Responde publicamente ao comentário via Graph API."""
    if not comment_id or not message or not access_token:
        return False
    try:
        import requests
        url = f"https://graph.facebook.com/v21.0/{comment_id}/replies"
        res = requests.post(url, json={"message": message}, params={"access_token": access_token}, timeout=10)
        return res.status_code == 200
    except Exception as exc:
        logger.warning("[COMMENT_REPLY] Falha ao responder comentário %s: %s", comment_id, exc)
        return False


def send_instagram_private_reply(comment_id: str, message: str, access_token: str) -> bool:
    """Envia DM privada ao usuário que comentou via Instagram Private Replies API."""
    if not comment_id or not message or not access_token:
        return False
    try:
        import requests
        url = "https://graph.facebook.com/v21.0/me/messages"
        payload = {
            "recipient": {"comment_id": comment_id},
            "message": {"text": message},
        }
        res = requests.post(url, json=payload, params={"access_token": access_token}, timeout=10)
        return res.status_code == 200
    except Exception as exc:
        logger.warning("[PRIVATE_REPLY] Falha ao enviar DM para comment %s: %s", comment_id, exc)
        return False


def send_instagram_direct_message(recipient_id: str, message: str, access_token: str) -> bool:
    """Envia mensagem para um usuário que já iniciou uma interação no Instagram."""
    if not recipient_id or not message or not access_token:
        return False
    try:
        import requests
        response = requests.post(
            "https://graph.facebook.com/v21.0/me/messages",
            json={"recipient": {"id": recipient_id}, "message": {"text": message}},
            params={"access_token": access_token},
            timeout=10,
        )
        return response.status_code == 200
    except Exception as exc:
        logger.warning("[INSTAGRAM_DM] Falha ao enviar DM para recipient=%s: %s", recipient_id, exc)
        return False


def process_social_comment(tenant_id: str, comment_data: dict, db) -> int:
    """
    Compara comentário recebido com as regras ativas de Comment-to-DM do tenant.
    Se bater com a palavra-chave:
      1. Responde o comentário no feed/post (se configurado)
      2. Envia DM exclusiva (Private Reply)
      3. Cria ou atualiza Lead com tag ['comment_to_dm', 'instagram']
      4. Dispara realtime SSE para o Inbox
    """
    from datetime import datetime, timezone
    text = (comment_data.get("text") or comment_data.get("message") or "").strip()
    comment_id = comment_data.get("id") or comment_data.get("comment_id") or ""
    sender = comment_data.get("from") or {}
    sender_id = sender.get("id") or ""
    sender_username = sender.get("username") or ""

    if not text or not comment_id:
        return 0

    # Meta retries webhook deliveries. Claim event or check existing status
    event_key = f"comment:{comment_id}"
    receipt = db.query(models.SocialWebhookReceipt).filter_by(
        tenant_id=tenant_id, provider="meta", event_key=event_key
    ).first()
    if receipt and receipt.status == "sent":
        return 0
    if not receipt:
        try:
            receipt = models.SocialWebhookReceipt(
                tenant_id=tenant_id, provider="meta", event_key=event_key, status="processing"
            )
            db.add(receipt)
            db.commit()
        except IntegrityError:
            db.rollback()
            receipt = db.query(models.SocialWebhookReceipt).filter_by(
                tenant_id=tenant_id, provider="meta", event_key=event_key
            ).first()
            if receipt and receipt.status == "sent":
                return 0
    else:
        receipt.status = "processing"
        db.commit()

    rules = _get_variable(db, tenant_id, "social.comment_rules", [])
    access_token = _get_secret(db, tenant_id, "meta_social.access_token")

    matched_count = 0
    text_upper = text.upper()
    for rule in rules:
        if not rule.get("active", True):
            continue
        kw = (rule.get("keyword") or "").strip().upper()
        if not kw or kw in text_upper:
            # Match!
            reply_comment = rule.get("reply_comment")
            send_dm = rule.get("send_dm")

            public_ok = not bool(reply_comment)
            private_ok = not bool(send_dm)

            if reply_comment and receipt and receipt.public_reply_sent:
                public_ok = True
            elif reply_comment and access_token:
                ok = reply_to_instagram_comment(comment_id, reply_comment, access_token)
                public_ok = bool(ok)
                if ok and receipt:
                    receipt.public_reply_sent = True
                    db.commit()

            if send_dm and receipt and receipt.private_reply_sent:
                private_ok = True
            elif send_dm and access_token:
                ok = send_instagram_private_reply(comment_id, send_dm, access_token)
                private_ok = bool(ok)
                if ok and receipt:
                    receipt.private_reply_sent = True
                    db.commit()

            # Criar ou enriquecer lead
            lead_ident = sender_id or (f"ig_{sender_username}" if sender_username else f"comment_{comment_id}")
            lead = db.query(models.Lead).filter_by(tenant_id=tenant_id, telefone=lead_ident).first()
            now = datetime.now(timezone.utc)
            if not lead:
                tags = ["instagram", "comment_to_dm"]
                lead = models.Lead(
                    tenant_id=tenant_id,
                    telefone=lead_ident,
                    nome=sender_username or "Usuário Instagram",
                    tags=tags,
                    custom_fields={"channel": "instagram", "ig_username": sender_username},
                    metadata_json={"origem": "comment_to_dm", "comment_id": comment_id, "text": text},
                )
                db.add(lead)
                db.commit()
                db.refresh(lead)
            else:
                current_tags = list(lead.tags or [])
                if "comment_to_dm" not in current_tags:
                    current_tags.append("comment_to_dm")
                    lead.tags = current_tags
                    db.commit()

            # Notificar realtime SSE
            try:
                from api.saas.realtime_hooks import notify_lead_updated
                notify_lead_updated(tenant_id, lead.id, {"tags": lead.tags})
            except Exception:
                pass

            matched_count += 1
            if receipt:
                receipt.status = "sent" if (public_ok and private_ok) else "failed"
                receipt.last_error = None if receipt.status == "sent" else "one_or_more_social_effects_failed"
                db.commit()
            break  # Executa primeira regra correspondente

    if receipt and receipt.status == "processing":
        receipt.status = "sent"
        db.commit()

    return matched_count


# ── 1. INSTAGRAM & FACEBOOK COMMENT AUTO-REPLY ────────────────────────

@social_bp.route("/api/public/webhooks/meta-social", methods=["GET", "POST"])
def meta_social_webhook():
    """
    Webhook da Meta para feed, comments e mentions do Facebook / Instagram.
    Valida token no GET (hub.challenge) e processa comentarios no POST.
    """
    tenant_id = _require_tenant()
    if not tenant_id:
        return jsonify({"error": "tenant_id_required"}), 400
    db = SessionLocal()
    try:
        if request.method == "GET":
            mode = request.args.get("hub.mode")
            token = request.args.get("hub.verify_token") or ""
            challenge = request.args.get("hub.challenge") or ""
            expected_token = _get_secret(db, tenant_id, "meta_social.verify_token")
            if mode == "subscribe" and expected_token and hmac.compare_digest(token, expected_token):
                return challenge, 200
            return jsonify({"error": "invalid_verify_token"}), 403

        app_secret = _get_secret(db, tenant_id, "meta_social.app_secret")
        if not _valid_meta_signature(app_secret):
            return jsonify({"error": "invalid_signature"}), 403
    finally:
        db.close()

    payload = request.get_json(silent=True) or {}
    logger.info("[META_SOCIAL_WEBHOOK] Evento autenticado tenant=%s", tenant_id)

    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            field = change.get("field")
            val = change.get("value", {})

            if field in ["comments", "feed", "live_comments", "mentions"]:
                post_id = val.get("post_id") or val.get("media", {}).get("id")
                logger.info("[COMMENT_DETECTED] tenant=%s post=%s field=%s", tenant_id, post_id, field)
                db_proc = SessionLocal()
                try:
                    process_social_comment(tenant_id, val, db_proc)
                except Exception as exc:
                    logger.warning("[COMMENT_PROC_ERROR] tenant=%s: %s", tenant_id, exc)
                finally:
                    db_proc.close()

        # Respostas e reações a Stories chegam via entry.messaging
        messaging_events = entry.get("messaging", [])
        for msg_ev in messaging_events:
            sender = msg_ev.get("sender", {}).get("id")
            recipient = msg_ev.get("recipient", {}).get("id")
            message = msg_ev.get("message", {})
            story_ref = message.get("reply_to", {}).get("story") or message.get("story")
            if sender and story_ref:
                logger.info("[STORY_REPLY_DETECTED] tenant=%s sender=%s", tenant_id, sender)
                db_proc = SessionLocal()
                try:
                    message_id = message.get("mid") or msg_ev.get("timestamp") or hashlib.sha256(
                        json.dumps(msg_ev, sort_keys=True).encode("utf-8")
                    ).hexdigest()
                    event_key = f"story:{sender}:{message_id}"
                    receipt = db_proc.query(models.SocialWebhookReceipt).filter_by(
                        tenant_id=tenant_id, provider="meta", event_key=event_key
                    ).first()
                    if receipt and receipt.status == "sent":
                        continue
                    if not receipt:
                        try:
                            receipt = models.SocialWebhookReceipt(
                                tenant_id=tenant_id, provider="meta", event_key=event_key, status="processing",
                            )
                            db_proc.add(receipt)
                            db_proc.commit()
                        except IntegrityError:
                            db_proc.rollback()
                            receipt = db_proc.query(models.SocialWebhookReceipt).filter_by(
                                tenant_id=tenant_id, provider="meta", event_key=event_key
                            ).first()
                            if receipt and receipt.status == "sent":
                                continue
                    else:
                        receipt.status = "processing"
                        db_proc.commit()

                    story_cfg = _get_variable(db_proc, tenant_id, "social.story_reply_config", {
                        "active": True,
                        "reply_text": "Obrigada por interagir com o nosso Story! 🔮 Como posso te ajudar hoje?",
                    })
                    sent_ok = False
                    if story_cfg.get("active", True):
                        access_token = _get_secret(db_proc, tenant_id, "meta_social.access_token")
                        sent_ok = send_instagram_direct_message(
                            sender,
                            story_cfg.get("reply_text", "Obrigada por responder nosso Story! ✨"),
                            access_token,
                        )
                    if receipt:
                        receipt.status = "sent" if sent_ok else "failed"
                        db_proc.commit()
                except Exception as exc:
                    logger.warning("[STORY_REPLY_ERROR] tenant=%s: %s", tenant_id, exc)
                finally:
                    db_proc.close()

    return jsonify({"status": "received"}), 200


@social_bp.route("/saas/social/rules", methods=["GET", "POST"])
@login_required
def comment_rules():
    """Gerencia regras de resposta automatica para posts do Instagram/Facebook."""
    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id
        rules = _get_variable(db, tenant_id, "social.comment_rules", [
            {
                "id": "rule_1",
                "platform": "instagram",
                "keyword": "EU QUERO",
                "reply_comment": "Enviamos o link exclusivo no seu direct! 🔮✨",
                "send_dm": "Olá! Vi que você comentou no nosso post. Aqui está o link que prometemos: {link}",
                "active": True
            }
        ])

        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            new_rules = data.get("rules", [])
            if not isinstance(new_rules, list):
                return jsonify({"error": "rules_must_be_a_list"}), 422
            _put_variable(db, tenant_id, "social.comment_rules", new_rules)
            credentials = data.get("credentials") or {}
            if "verify_token" in credentials:
                _put_secret(db, tenant_id, "meta_social.verify_token", str(credentials["verify_token"]).strip())
            if "app_secret" in credentials:
                _put_secret(db, tenant_id, "meta_social.app_secret", str(credentials["app_secret"]).strip())
            if "access_token" in credentials:
                _put_secret(db, tenant_id, "meta_social.access_token", str(credentials["access_token"]).strip())
            db.commit()
            return jsonify({"ok": True, "rules": new_rules})

        return jsonify({
            "ok": True,
            "rules": rules,
            "credentials_configured": {
                "verify_token": bool(_get_secret(db, tenant_id, "meta_social.verify_token")),
                "app_secret": bool(_get_secret(db, tenant_id, "meta_social.app_secret")),
                "access_token": bool(_get_secret(db, tenant_id, "meta_social.access_token")),
            },
        })
    finally:
        db.close()


@social_bp.route("/saas/social/story-reply", methods=["GET", "POST"])
@login_required
def story_reply_config():
    """Gerencia configurações da automação de resposta a Stories do Instagram."""
    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id
        default_cfg = {
            "active": True,
            "reply_text": "Obrigada por interagir com o nosso Story! 🔮 Como posso te ajudar hoje?",
        }
        cfg = _get_variable(db, tenant_id, "social.story_reply_config", default_cfg)

        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            cfg = {
                "active": bool(data.get("active", True)),
                "reply_text": (data.get("reply_text") or default_cfg["reply_text"]).strip(),
            }
            _put_variable(db, tenant_id, "social.story_reply_config", cfg)
            db.commit()
            return jsonify({"ok": True, "config": cfg})

        return jsonify({"ok": True, "config": cfg})
    finally:
        db.close()


# ── 2. TIKTOK BUSINESS WEBHOOK & MESSAGING ────────────────────────────

@social_bp.route("/api/public/webhooks/tiktok", methods=["GET", "POST"])
def tiktok_webhook():
    """Webhook receptor de eventos de mensagens e leads do TikTok Business."""
    tenant_id = _require_tenant()
    if not tenant_id:
        return jsonify({"error": "tenant_id_required"}), 400
    db = SessionLocal()
    try:
        expected = _get_secret(db, tenant_id, "tiktok.webhook_secret")
    finally:
        db.close()
    supplied = request.headers.get("X-TikTok-Webhook-Secret") or ""
    if not expected or not hmac.compare_digest(supplied, expected):
        return jsonify({"error": "invalid_webhook_secret"}), 403
    if request.method == "GET":
        return request.args.get("challenge", ""), 200

    logger.info("[TIKTOK_WEBHOOK] Evento autenticado tenant=%s", tenant_id)
    return jsonify({"status": "received"}), 200


@social_bp.route("/saas/tiktok/config", methods=["GET", "POST"])
@login_required
def tiktok_config():
    """Configura credenciais do TikTok Business (App ID, Secret, Access Token)."""
    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id
        tiktok_data = _get_variable(db, tenant_id, "tiktok.business", {})

        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            tiktok_data = {
                "business_id": payload.get("business_id", "").strip(),
                "app_id": payload.get("app_id", "").strip(),
                "active": bool(payload.get("active", False)),
            }
            _put_variable(db, tenant_id, "tiktok.business", tiktok_data)
            if "access_token" in payload:
                _put_secret(db, tenant_id, "tiktok.access_token", str(payload["access_token"]).strip())
            if "webhook_secret" in payload:
                _put_secret(db, tenant_id, "tiktok.webhook_secret", str(payload["webhook_secret"]).strip())
            db.commit()
            return jsonify({"ok": True, "config": tiktok_data, "has_token": bool(_get_secret(db, tenant_id, "tiktok.access_token"))})

        return jsonify({
            "ok": True,
            "business_id": tiktok_data.get("business_id", ""),
            "has_token": bool(_get_secret(db, tenant_id, "tiktok.access_token")),
            "has_webhook_secret": bool(_get_secret(db, tenant_id, "tiktok.webhook_secret")),
            "app_id": tiktok_data.get("app_id", ""),
            "active": tiktok_data.get("active", False),
        })
    finally:
        db.close()


# ── 3. YOUTUBE CHANNEL & COMMUNITY INTEGRATION ────────────────────────

@social_bp.route("/saas/youtube/config", methods=["GET", "POST"])
@login_required
def youtube_config():
    """Configura canal do YouTube (Channel ID, API Key, Notificacoes de novos videos/shorts)."""
    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id
        yt_data = _get_variable(db, tenant_id, "youtube.integration", {})

        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            yt_data = {
                "channel_id": payload.get("channel_id", "").strip(),
                "auto_broadcast_new_videos": bool(payload.get("auto_broadcast_new_videos", False)),
                "active": bool(payload.get("active", False)),
            }
            _put_variable(db, tenant_id, "youtube.integration", yt_data)
            if "api_key" in payload:
                _put_secret(db, tenant_id, "youtube.api_key", str(payload["api_key"]).strip())
            db.commit()
            return jsonify({"ok": True, "config": yt_data, "has_api_key": bool(_get_secret(db, tenant_id, "youtube.api_key"))})

        return jsonify({
            "ok": True,
            "channel_id": yt_data.get("channel_id", ""),
            "has_api_key": bool(_get_secret(db, tenant_id, "youtube.api_key")),
            "auto_broadcast_new_videos": yt_data.get("auto_broadcast_new_videos", False),
            "active": yt_data.get("active", False),
        })
    finally:
        db.close()

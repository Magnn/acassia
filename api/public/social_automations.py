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

            if field in ["comments", "feed", "live_comments"]:
                post_id = val.get("post_id") or val.get("media", {}).get("id")
                logger.info("[COMMENT_DETECTED] tenant=%s post=%s", tenant_id, post_id)

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
            db.commit()
            return jsonify({"ok": True, "rules": new_rules})

        return jsonify({
            "ok": True,
            "rules": rules,
            "credentials_configured": {
                "verify_token": bool(_get_secret(db, tenant_id, "meta_social.verify_token")),
                "app_secret": bool(_get_secret(db, tenant_id, "meta_social.app_secret")),
            },
        })
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

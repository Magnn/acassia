"""
api/saas/wa_embedded_signup.py — WhatsApp Embedded Signup (Meta Cloud API)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Implementa o fluxo de Embedded Signup oficial da Meta (padrão ManyChat / ChatbotX):
1. Frontend abre o popup do Facebook Login / Embedded Signup.
2. Meta retorna o `code` de autorização e os IDs (waba_id, phone_number_id).
3. Backend troca o `code` por um access token permanente da Meta Graph API.
4. Registra automaticamente o WADevice no tenant e subscreve webhook da WABA.
"""

from __future__ import annotations

import logging
import os
import requests
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
wa_embedded_bp = Blueprint("wa_embedded_signup", __name__, url_prefix="/saas/wa/embedded-signup")

GRAPH_API_VERSION = "v20.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def _get_meta_app_credentials():
    app_id = (os.getenv("META_APP_ID") or os.getenv("APP_ID") or "").strip()
    app_secret = (os.getenv("META_APP_SECRET") or os.getenv("APP_SECRET") or "").strip()
    config_id = os.getenv("META_CONFIG_ID", "").strip()
    return app_id, app_secret, config_id


@wa_embedded_bp.route("/config", methods=["GET"])
@login_required
def get_config():
    """Retorna se o Embedded Signup está configurado e as credenciais públicas."""
    app_id, app_secret, config_id = _get_meta_app_credentials()
    return jsonify({
        "configured": bool(app_id and app_secret and config_id),
        "exchange_configured": bool(app_id and app_secret),
        "app_id": app_id or None,
        "config_id": config_id or None,
        "graph_version": GRAPH_API_VERSION,
        "missing": [
            key for key, value in (
                ("META_APP_ID", app_id),
                ("META_APP_SECRET", app_secret),
                ("META_CONFIG_ID", config_id),
            ) if not value
        ],
    })


@wa_embedded_bp.route("/exchange", methods=["POST"])
@login_required
def exchange_code():
    """
    Troca o authorization code pelo access token permanente da Meta,
    obtém informações do número e cria o WADevice no tenant.
    """
    app_id, app_secret, _ = _get_meta_app_credentials()
    if not app_id or not app_secret:
        return jsonify({
            "error": "meta_app_not_configured",
            "message": "META_APP_ID e META_APP_SECRET não estão configurados no servidor.",
        }), 400

    data = request.get_json(silent=True) or {}
    code = data.get("code")
    phone_number_id = data.get("phone_number_id")
    waba_id = data.get("waba_id")
    nickname = (data.get("nickname") or "").strip() or "WhatsApp Oficial"

    if not code:
        return jsonify({"error": "missing_code", "message": "Authorization code obrigatório."}), 400

    tenant_id = current_user.tenant_id

    # 1. Trocar code por access token
    token_url = f"{GRAPH_URL}/oauth/access_token"
    token_params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "code": code,
    }

    try:
        resp = requests.get(token_url, params=token_params, timeout=15)
        token_data = resp.json()
        if resp.status_code != 200 or "access_token" not in token_data:
            logger.error("[wa_embedded] Erro ao trocar code Meta: %s", token_data)
            return jsonify({
                "error": "token_exchange_failed",
                "details": token_data.get("error", {}).get("message", "Falha na troca de token."),
            }), 400

        access_token = token_data["access_token"]
    except Exception as exc:
        logger.exception("[wa_embedded] Falha HTTP na troca de token: %s", exc)
        return jsonify({"error": "http_error", "message": str(exc)}), 500

    # 2. Se phone_number_id foi fornecido, buscar display_phone_number e status
    phone_display = None
    if phone_number_id:
        try:
            phone_url = f"{GRAPH_URL}/{phone_number_id}"
            p_resp = requests.get(
                phone_url,
                params={"fields": "display_phone_number,verified_name,quality_rating"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if p_resp.status_code == 200:
                p_data = p_resp.json()
                phone_display = p_data.get("display_phone_number")
        except Exception as exc:
            logger.warning("[wa_embedded] Não foi possível obter display_phone_number: %s", exc)

    # 3. Se waba_id foi fornecido, subscrever webhook
    if waba_id:
        try:
            sub_url = f"{GRAPH_URL}/{waba_id}/subscribed_apps"
            s_resp = requests.post(
                sub_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            logger.info("[wa_embedded] Subscribed apps status=%s: %s", s_resp.status_code, s_resp.text)
        except Exception as exc:
            logger.warning("[wa_embedded] Falha ao assinar webhook da WABA: %s", exc)

    # 4. Criar ou atualizar WADevice
    db = SessionLocal()
    try:
        # Verificar se já existe device com esse phone_number_id no tenant
        device = None
        if phone_number_id:
            device = db.query(models.WADevice).filter_by(
                tenant_id=tenant_id,
                meta_phone_number_id=phone_number_id,
                active=True,
            ).first()

        has_any = db.query(models.WADevice).filter_by(
            tenant_id=tenant_id, active=True,
        ).count()

        if not device:
            device = models.WADevice(
                tenant_id=tenant_id,
                nickname=nickname,
                provider="meta_cloud",
                phone_display=phone_display or phone_number_id or "WhatsApp",
                meta_phone_number_id=phone_number_id,
                meta_waba_id=waba_id,
                meta_access_token=access_token,
                connected=True,
                connection_state="connected",
                is_primary=(has_any == 0),
                created_at=datetime.now(timezone.utc),
            )
            db.add(device)
        else:
            device.meta_access_token = access_token
            if phone_display:
                device.phone_display = phone_display
            if waba_id:
                device.meta_waba_id = waba_id
            device.connected = True
            device.connection_state = "connected"

        db.commit()
        db.refresh(device)

        logger.info(
            "[wa_embedded] Conexão WhatsApp bem sucedida! device_id=%d tenant=%s phone=%s",
            device.id, tenant_id, device.phone_display,
        )

        return jsonify({
            "ok": True,
            "device": {
                "id": device.id,
                "nickname": device.nickname,
                "phone_display": device.phone_display,
                "connected": device.connected,
                "is_primary": device.is_primary,
            },
        }), 200
    except Exception as exc:
        db.rollback()
        logger.exception("[wa_embedded] Erro ao salvar device: %s", exc)
        return jsonify({"error": "db_error", "message": str(exc)}), 500
    finally:
        db.close()

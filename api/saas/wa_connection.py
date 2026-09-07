"""
api/saas/wa_connection.py — Conexão WhatsApp (QR Code + Status)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Expõe endpoints para:
  - GET  /saas/wa/status      — estado da conexão
  - GET  /saas/wa/qr-code     — gera QR code para parear
  - POST /saas/wa/disconnect  — desconecta instância
  - GET  /saas/wa/groups      — lista grupos do WhatsApp conectado
"""
from __future__ import annotations
import logging
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
wa_conn_bp = Blueprint("wa_connection", __name__, url_prefix="/saas/wa")


def _get_provider(tenant_id):
    """Get the WA provider for this tenant."""
    from api.whatsapp_providers.factory import get_provider_for_tenant
    try:
        return get_provider_for_tenant(tenant_id)
    except Exception as e:
        logger.warning("[wa_conn] provider error: %s", e)
        return None


@wa_conn_bp.route("/status", methods=["GET"])
@login_required
def connection_status():
    """Check WhatsApp connection status."""
    provider = _get_provider(current_user.tenant_id)
    if not provider:
        return jsonify({
            "ok": False, "connected": False,
            "mode": "none", "configured": False,
            "hint": "Nenhum provedor WhatsApp configurado. Vá em Configuração > Variáveis & Segredos.",
        })

    status = provider.status()
    return jsonify({
        "ok": status.get("ok", False),
        "connected": status.get("ok", False),
        "mode": status.get("mode", "unknown"),
        "configured": status.get("configured", False),
        "connection_state": status.get("connection_state"),
        "hint": status.get("hint"),
    })


@wa_conn_bp.route("/qr-code", methods=["GET"])
@login_required
def get_qr_code():
    """Get QR code for Evolution API pairing."""
    provider = _get_provider(current_user.tenant_id)
    if not provider:
        return jsonify({"ok": False, "error": "provider_not_configured"}), 422

    # Only Evolution supports QR codes
    if not hasattr(provider, "get_qr_code"):
        return jsonify({
            "ok": False, "mode": provider.mode.value,
            "error": "qr_not_supported",
            "message": "Meta Cloud API não usa QR Code. Configure access_token e phone_number_id em Variáveis & Segredos.",
        }), 422

    result = provider.get_qr_code()
    if result.ok:
        return jsonify({
            "ok": True,
            "qr_base64": result.raw.get("base64") if result.raw else None,
            "qr_code": result.raw.get("code") if result.raw else None,
        })
    return jsonify({"ok": False, "error": result.error}), 500


@wa_conn_bp.route("/disconnect", methods=["POST"])
@login_required
def disconnect():
    """Disconnect WhatsApp instance (Evolution only)."""
    provider = _get_provider(current_user.tenant_id)
    if not provider:
        return jsonify({"ok": False}), 422

    if hasattr(provider, "server_url") and hasattr(provider, "instance"):
        import requests
        try:
            resp = requests.delete(
                f"{provider.server_url}/instance/logout/{provider.instance}",
                headers=provider._headers(),
                timeout=10,
            )
            return jsonify({"ok": resp.status_code in (200, 201)})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)[:200]}), 500

    return jsonify({"ok": False, "error": "disconnect_not_supported"}), 422


@wa_conn_bp.route("/groups", methods=["GET"])
@login_required
def list_wa_groups():
    """List groups from connected WhatsApp (Evolution API)."""
    provider = _get_provider(current_user.tenant_id)
    if not provider:
        return jsonify({"ok": False, "groups": []}), 422

    # Evolution API: GET /group/fetchAllGroups/{instance}
    if hasattr(provider, "server_url") and hasattr(provider, "instance"):
        import requests
        try:
            resp = requests.get(
                f"{provider.server_url}/group/fetchAllGroups/{provider.instance}",
                headers=provider._headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                groups = []
                for g in (data if isinstance(data, list) else []):
                    groups.append({
                        "name": g.get("subject", g.get("name", "?")),
                        "jid": g.get("id", ""),
                        "members_count": len(g.get("participants", [])),
                        "creation": g.get("creation"),
                    })
                return jsonify({"ok": True, "groups": groups, "total": len(groups)})
        except Exception as e:
            logger.warning("[wa_conn] fetch groups failed: %s", e)

    # Meta Cloud: groups not directly listable via API
    return jsonify({
        "ok": True, "groups": [],
        "message": "Meta Cloud API não lista grupos automaticamente. Use o botão Importar para adicionar manualmente.",
    })

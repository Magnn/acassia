"""
api/saas/wa_devices.py — CRUD de Dispositivos WhatsApp (Multi-Número)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Suporta N dispositivos por tenant. Cada dispositivo tem provider + credenciais.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
devices_bp = Blueprint("wa_devices", __name__, url_prefix="/saas/devices")


@devices_bp.route("/", methods=["GET"])
@login_required
def list_devices():
    db = SessionLocal()
    try:
        devs = (
            db.query(models.WADevice)
            .filter_by(tenant_id=current_user.tenant_id, active=True)
            .order_by(models.WADevice.is_primary.desc(), models.WADevice.created_at.desc())
            .all()
        )
        return jsonify({"devices": [{
            "id": d.id,
            "nickname": d.nickname,
            "provider": d.provider,
            "phone_display": d.phone_display,
            "connected": d.connected,
            "connection_state": d.connection_state,
            "is_primary": d.is_primary,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            "groups_count": db.query(models.WAGroup).filter_by(device_id=d.id).count(),
        } for d in devs], "total": len(devs)})
    finally:
        db.close()


@devices_bp.route("/", methods=["POST"])
@login_required
def create_device():
    db = SessionLocal()
    try:
        data = request.json or {}
        nickname = (data.get("nickname") or "").strip()
        if not nickname:
            return jsonify({"error": "nickname_required"}), 422

        # Check duplicates
        existing = db.query(models.WADevice).filter_by(
            tenant_id=current_user.tenant_id, nickname=nickname, active=True
        ).first()
        if existing:
            return jsonify({"error": "nickname_duplicate"}), 409

        provider = data.get("provider", "evolution")

        # Auto-set primary if first device
        has_any = db.query(models.WADevice).filter_by(
            tenant_id=current_user.tenant_id, active=True
        ).count()

        d = models.WADevice(
            tenant_id=current_user.tenant_id,
            nickname=nickname,
            provider=provider,
            phone_display=data.get("phone_display"),
            is_primary=(has_any == 0),  # First device is primary
            # Evolution
            evolution_server_url=data.get("evolution_server_url"),
            evolution_instance=data.get("evolution_instance"),
            evolution_api_key=data.get("evolution_api_key"),
            # Meta Cloud
            meta_phone_number_id=data.get("meta_phone_number_id"),
            meta_waba_id=data.get("meta_waba_id"),
            meta_access_token=data.get("meta_access_token"),
        )
        db.add(d)
        db.commit()
        return jsonify({"ok": True, "device_id": d.id, "is_primary": d.is_primary}), 201
    finally:
        db.close()


@devices_bp.route("/<int:device_id>", methods=["PUT"])
@login_required
def update_device(device_id):
    db = SessionLocal()
    try:
        d = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404

        data = request.json or {}
        for k in ("nickname", "phone_display", "provider",
                   "evolution_server_url", "evolution_instance", "evolution_api_key",
                   "meta_phone_number_id", "meta_waba_id", "meta_access_token"):
            if k in data:
                setattr(d, k, data[k])
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@devices_bp.route("/<int:device_id>", methods=["DELETE"])
@login_required
def delete_device(device_id):
    db = SessionLocal()
    try:
        d = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404
        d.active = False
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@devices_bp.route("/<int:device_id>/set-primary", methods=["POST"])
@login_required
def set_primary(device_id):
    db = SessionLocal()
    try:
        # Unset all primaries for this tenant
        db.query(models.WADevice).filter_by(
            tenant_id=current_user.tenant_id
        ).update({"is_primary": False})
        # Set the new primary
        d = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404
        d.is_primary = True
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@devices_bp.route("/<int:device_id>/status", methods=["GET"])
@login_required
def device_status(device_id):
    """Check connection status for a specific device."""
    db = SessionLocal()
    try:
        d = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404

        provider = _get_provider_for_device(d)
        if not provider:
            return jsonify({"ok": False, "connected": False, "hint": "Provider não configurado"})

        status = provider.status()
        # Update device state
        d.connected = status.get("ok", False)
        d.connection_state = status.get("connection_state")
        if d.connected:
            d.last_seen_at = datetime.now(timezone.utc)
        db.commit()

        return jsonify({
            "ok": status.get("ok", False),
            "connected": status.get("ok", False),
            "connection_state": status.get("connection_state"),
            "hint": status.get("hint"),
        })
    finally:
        db.close()


@devices_bp.route("/<int:device_id>/qr-code", methods=["GET"])
@login_required
def device_qr_code(device_id):
    """Get QR code for a specific Evolution device."""
    db = SessionLocal()
    try:
        d = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404
        if d.provider != "evolution":
            return jsonify({"error": "qr_only_evolution"}), 422

        provider = _get_provider_for_device(d)
        if not provider or not hasattr(provider, "get_qr_code"):
            return jsonify({"error": "provider_not_ready"}), 422

        result = provider.get_qr_code()
        if result.ok:
            return jsonify({
                "ok": True,
                "qr_base64": result.raw.get("base64") if result.raw else None,
                "qr_code": result.raw.get("code") if result.raw else None,
            })
        return jsonify({"ok": False, "error": result.error}), 500
    finally:
        db.close()


def _get_provider_for_device(device: models.WADevice):
    """Instantiate a WhatsApp provider from device credentials."""
    try:
        if device.provider == "evolution":
            from api.whatsapp_providers.evolution import EvolutionProvider
            return EvolutionProvider(
                tenant_id=device.tenant_id,
                config={
                    "evolution_server_url": device.evolution_server_url or "",
                    "evolution_instance": device.evolution_instance or "",
                    "evolution_api_key": device.evolution_api_key or "",
                },
            )
        elif device.provider in ("meta_cloud", "coex"):
            from api.whatsapp_providers.meta_cloud import MetaCloudProvider
            return MetaCloudProvider(
                tenant_id=device.tenant_id,
                config={
                    "access_token": device.meta_access_token or "",
                    "phone_number_id": device.meta_phone_number_id or "",
                },
            )
    except Exception as e:
        logger.warning("[devices] Provider error: %s", e)
    return None

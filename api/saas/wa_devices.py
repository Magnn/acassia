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
from api.utils.tenant_secrets import decrypt_tenant_secret, encrypt_tenant_secret

logger = logging.getLogger(__name__)
devices_bp = Blueprint("wa_devices", __name__, url_prefix="/saas/devices")


def _device_secret_key(device_id: int, field: str) -> str:
    return f"whatsapp.device.{device_id}.{field}"


def _set_device_secret(db, device: models.WADevice, field: str, value: str | None) -> None:
    key = _device_secret_key(device.id, field)
    row = db.query(models.TenantFlowSecret).filter_by(tenant_id=device.tenant_id, key=key).first()
    clean = str(value or "").strip()
    if not clean:
        if row:
            db.delete(row)
        return
    cipher = encrypt_tenant_secret(clean)
    if row:
        row.value_cipher = cipher
    else:
        db.add(models.TenantFlowSecret(tenant_id=device.tenant_id, key=key, value_cipher=cipher))


def _get_device_secret(db, device: models.WADevice, field: str, legacy_value: str | None) -> str:
    row = db.query(models.TenantFlowSecret).filter_by(
        tenant_id=device.tenant_id, key=_device_secret_key(device.id, field)
    ).first()
    if row:
        return decrypt_tenant_secret(row.value_cipher, allow_plaintext_legacy=True)
    return str(legacy_value or "")


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
            "flow_mode": getattr(d, "flow_mode", "static_funnel") or "static_funnel",
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
            evolution_api_key=None,
            # OpenWA
            openwa_server_url=data.get("openwa_server_url"),
            openwa_session_id=data.get("openwa_session_id"),
            openwa_api_key=None,
            # Meta Cloud
            meta_phone_number_id=data.get("meta_phone_number_id"),
            meta_waba_id=data.get("meta_waba_id"),
            meta_access_token=None,
        )
        db.add(d)
        db.flush()
        _set_device_secret(db, d, "evolution_api_key", data.get("evolution_api_key"))
        _set_device_secret(db, d, "openwa_api_key", data.get("openwa_api_key"))
        _set_device_secret(db, d, "meta_access_token", data.get("meta_access_token"))
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
                   "evolution_server_url", "evolution_instance",
                   "openwa_server_url", "openwa_session_id",
                   "meta_phone_number_id", "meta_waba_id"):
            if k in data:
                setattr(d, k, data[k])
        if "evolution_api_key" in data:
            _set_device_secret(db, d, "evolution_api_key", data.get("evolution_api_key"))
            d.evolution_api_key = None
        if "openwa_api_key" in data:
            _set_device_secret(db, d, "openwa_api_key", data.get("openwa_api_key"))
            d.openwa_api_key = None
        if "meta_access_token" in data:
            _set_device_secret(db, d, "meta_access_token", data.get("meta_access_token"))
            d.meta_access_token = None
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
        for field in ("evolution_api_key", "openwa_api_key", "meta_access_token"):
            row = db.query(models.TenantFlowSecret).filter_by(
                tenant_id=d.tenant_id, key=_device_secret_key(d.id, field)
            ).first()
            if row:
                db.delete(row)
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
    """Check connection status for a specific device, detecting CONFLICT explicitly."""
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
        conn_state = status.get("connection_state")
        is_conflict = (str(conn_state).upper() == "CONFLICT")

        # Update device state
        d.connected = False if is_conflict else status.get("ok", False)
        d.connection_state = "CONFLICT" if is_conflict else conn_state
        if d.connected:
            d.last_seen_at = datetime.now(timezone.utc)
        db.commit()

        hint = status.get("hint")
        if is_conflict and not hint:
            hint = "Conflito de Sessão: o WhatsApp Web foi aberto em outro dispositivo. Desconecte lá e reinicie a sessão aqui."

        return jsonify({
            "ok": d.connected,
            "connected": d.connected,
            "connection_state": d.connection_state,
            "is_conflict": is_conflict,
            "hint": hint,
        })
    finally:
        db.close()


@devices_bp.route("/<int:device_id>/qr-code", methods=["GET"])
@login_required
def device_qr_code(device_id):
    """Get QR code for Evolution or OpenWA devices."""
    db = SessionLocal()
    try:
        d = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404
        if d.provider not in ("evolution", "openwa"):
            return jsonify({"error": "qr_only_qr_providers"}), 422

        provider = _get_provider_for_device(d)
        if not provider or not hasattr(provider, "get_qr_code"):
            return jsonify({"error": "provider_not_ready"}), 422

        result = provider.get_qr_code()
        if result.ok:
            return jsonify({
                "ok": True,
                "qr_base64": result.raw.get("base64") if result.raw else None,
                "qr_code": result.raw.get("code") or result.raw.get("qr") if result.raw else None,
            })
        return jsonify({"ok": False, "error": result.error}), 500
    finally:
        db.close()


@devices_bp.route("/<int:device_id>/restart", methods=["POST"])
@login_required
def restart_device(device_id):
    """Reinicia a sessão do dispositivo (útil para recuperar de CONFLICT ou desconexão)."""
    db = SessionLocal()
    try:
        d = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404

        provider = _get_provider_for_device(d)
        if not provider:
            return jsonify({"error": "provider_not_configured"}), 422

        if hasattr(provider, "restart_session"):
            ok = provider.restart_session()
            if ok:
                d.connection_state = "connecting"
                db.commit()
            return jsonify({
                "ok": ok,
                "message": "Sessão reiniciada com sucesso" if ok else "Falha ao reiniciar sessão",
            })
        return jsonify({"ok": False, "error": "not_supported_by_provider"}), 400
    finally:
        db.close()


@devices_bp.route("/<int:device_id>/flow-mode", methods=["POST"])
@login_required
def set_device_flow_mode(device_id: int):
    """Alterna o modo de automação do dispositivo: static_funnel, ai_agent ou flow_builder."""
    db = SessionLocal()
    try:
        data = request.json or {}
        new_mode = (data.get("flow_mode") or "").strip().lower()
        if new_mode not in ("static_funnel", "ai_agent", "flow_builder"):
            return jsonify({
                "error": "invalid_mode",
                "allowed": ["static_funnel", "ai_agent", "flow_builder"],
            }), 400

        dev = db.query(models.WADevice).filter_by(
            id=device_id, tenant_id=current_user.tenant_id, active=True
        ).first()
        if not dev:
            return jsonify({"error": "device_not_found"}), 404

        dev.flow_mode = new_mode

        is_static = (new_mode == "static_funnel")
        ini_node = "static_meumisterio_b1" if is_static else "1_apresentacao"

        def _set_tv(k: str, val):
            row = db.query(models.TenantFlowVariable).filter_by(
                tenant_id=current_user.tenant_id, key=k
            ).first()
            if row:
                row.value_json = val
            else:
                db.add(models.TenantFlowVariable(tenant_id=current_user.tenant_id, key=k, value_json=val))

        _set_tv("funnel_mode", new_mode)
        _set_tv("funil_estatico_meu_misterio_ativo", is_static)
        _set_tv("funil_entrada_inicial", ini_node)

        db.commit()

        # Invalida o cache de tenant_config
        try:
            from api.tenant_config import clear_cache
            clear_cache(current_user.tenant_id)
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "device_id": dev.id,
            "flow_mode": dev.flow_mode,
            "funil_entrada_inicial": ini_node,
        })
    finally:
        db.close()


def _get_provider_for_device(device: models.WADevice):
    """Instantiate a WhatsApp provider from device credentials."""
    try:
        db = SessionLocal()
        try:
            evolution_key = _get_device_secret(db, device, "evolution_api_key", device.evolution_api_key)
            openwa_key = _get_device_secret(db, device, "openwa_api_key", getattr(device, "openwa_api_key", None))
            meta_token = _get_device_secret(db, device, "meta_access_token", device.meta_access_token)
        finally:
            db.close()
        if device.provider == "evolution":
            from api.whatsapp_providers.evolution import EvolutionProvider
            return EvolutionProvider(
                tenant_id=device.tenant_id,
                config={
                    "evolution_server_url": device.evolution_server_url or "",
                    "evolution_instance": device.evolution_instance or "",
                    "evolution_api_key": evolution_key,
                },
            )
        elif device.provider == "openwa":
            from api.whatsapp_providers.openwa import OpenWAProvider
            return OpenWAProvider(
                tenant_id=device.tenant_id,
                config={
                    "openwa_server_url": getattr(device, "openwa_server_url", "") or "",
                    "openwa_session_id": getattr(device, "openwa_session_id", "") or "",
                    "openwa_api_key": openwa_key,
                },
            )
        elif device.provider in ("meta_cloud", "coex"):
            from api.whatsapp_providers.meta_cloud import MetaCloudProvider
            return MetaCloudProvider(
                tenant_id=device.tenant_id,
                config={
                    "access_token": meta_token,
                    "phone_number_id": device.meta_phone_number_id or "",
                },
            )
    except Exception as e:
        logger.warning("[devices] Provider error: %s", e)
    return None

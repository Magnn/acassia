"""
api/public/meta_capi_bp.py — Gerenciamento e Disparo de Meta Conversions API (CAPI)
"""

import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from utils.meta_capi import send_meta_capi_event
from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
meta_capi_bp = Blueprint("meta_capi_bp", __name__, url_prefix="/saas/capi")


@meta_capi_bp.route("/config", methods=["GET"])
@login_required
def get_capi_config():
    """Retorna configuracao do Meta Pixel / CAPI para o tenant logado."""
    db = SessionLocal()
    try:
        tenant = db.query(models.Tenant).filter_by(id=current_user.tenant_id).first()
        meta = (tenant.metadata_json if tenant else {}) or {}
        capi = meta.get("meta_capi", {})
        return jsonify({
            "ok": True,
            "pixel_id": capi.get("pixel_id", ""),
            "has_token": bool(capi.get("access_token")),
            "test_event_code": capi.get("test_event_code", ""),
            "auto_purchase": capi.get("auto_purchase", True),
            "auto_lead": capi.get("auto_lead", True),
        })
    finally:
        db.close()


@meta_capi_bp.route("/config", methods=["POST"])
@login_required
def save_capi_config():
    """Salva configuracao do Meta Pixel / CAPI."""
    payload = request.get_json(silent=True) or {}
    pixel_id = str(payload.get("pixel_id", "")).strip()
    access_token = str(payload.get("access_token", "")).strip()
    test_event_code = str(payload.get("test_event_code", "")).strip()
    auto_purchase = bool(payload.get("auto_purchase", True))
    auto_lead = bool(payload.get("auto_lead", True))

    db = SessionLocal()
    try:
        tenant = db.query(models.Tenant).filter_by(id=current_user.tenant_id).first()
        if not tenant:
            return jsonify({"ok": False, "error": "tenant_not_found"}), 404

        meta = dict(tenant.metadata_json or {})
        curr_capi = meta.get("meta_capi", {})
        # Se nao passou novo token, mantem o existente
        if not access_token and curr_capi.get("access_token"):
            access_token = curr_capi["access_token"]

        meta["meta_capi"] = {
            "pixel_id": pixel_id,
            "access_token": access_token,
            "test_event_code": test_event_code,
            "auto_purchase": auto_purchase,
            "auto_lead": auto_lead,
        }
        tenant.metadata_json = meta
        db.commit()
        return jsonify({"ok": True, "message": "Configuracao CAPI salva com sucesso!"})
    finally:
        db.close()


@meta_capi_bp.route("/test-event", methods=["POST"])
@login_required
def test_capi_event():
    """Envia evento de teste para o Meta Pixel."""
    payload = request.get_json(silent=True) or {}
    event_name = payload.get("event_name", "Lead")
    phone = payload.get("phone", "5511999999999")
    email = payload.get("email", "teste@meumisterio.com")
    val = payload.get("value", 97.0)

    db = SessionLocal()
    try:
        tenant = db.query(models.Tenant).filter_by(id=current_user.tenant_id).first()
        meta = (tenant.metadata_json if tenant else {}) or {}
        capi = meta.get("meta_capi", {})
        pixel_id = capi.get("pixel_id")
        token = capi.get("access_token")
        test_code = capi.get("test_event_code") or payload.get("test_event_code")

        if not pixel_id or not token:
            return jsonify({"ok": False, "error": "Pixel ID e Access Token sao obrigatorios."}), 400

        res = send_meta_capi_event(
            pixel_id=pixel_id,
            access_token=token,
            event_name=event_name,
            phone=phone,
            email=email,
            value=val,
            test_event_code=test_code,
        )
        return jsonify(res)
    finally:
        db.close()

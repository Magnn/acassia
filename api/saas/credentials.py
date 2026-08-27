from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from db.database import SessionLocal
from db import models
from api.utils.crypto import encrypt_credential
import logging

logger = logging.getLogger(__name__)

credentials_bp = Blueprint("credentials", __name__, url_prefix="/saas/credentials")

_ALLOWED_SERVICES = frozenset({"google_sheets", "activecampaign", "cakto", "webhook"})

@credentials_bp.route("/", methods=["GET"])
@login_required
def list_credentials():
    """List all integration credentials for the current tenant. Excludes raw secrets."""
    db = SessionLocal()
    try:
        creds = db.query(models.TenantIntegrationCredential).filter_by(tenant_id=current_user.tenant_id).all()
        return jsonify({
            "credentials": [
                {
                    "id": c.id,
                    "service": c.service,
                    "name": c.name,
                    "updated_at": c.atualizado_em.isoformat() if c.atualizado_em else None
                } for c in creds
            ]
        })
    finally:
        db.close()

@credentials_bp.route("/", methods=["POST"])
@login_required
def create_credential():
    """Create a new encrypted credential."""
    data = request.json or {}
    service = str(data.get("service") or "").strip()
    name = str(data.get("name") or "").strip()[:128]
    secret_data = data.get("secret_data")

    if not service or not name or not secret_data:
        return jsonify({"error": "service, name, and secret_data are required"}), 400
    if service not in _ALLOWED_SERVICES:
        return jsonify({"error": f"service inválido; valores aceitos: {sorted(_ALLOWED_SERVICES)}"}), 400
    if not isinstance(secret_data, dict):
        return jsonify({"error": "secret_data deve ser um objeto JSON"}), 400

    db = SessionLocal()
    try:
        encrypted = encrypt_credential(secret_data)
        
        cred = models.TenantIntegrationCredential(
            tenant_id=current_user.tenant_id,
            service=service,
            name=name,
            encrypted_data=encrypted
        )
        db.add(cred)
        db.commit()
        db.refresh(cred)
        
        return jsonify({
            "success": True,
            "credential": {
                "id": cred.id,
                "service": cred.service,
                "name": cred.name
            }
        }), 201
    except Exception as e:
        db.rollback()
        logger.exception("Error saving credential")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@credentials_bp.route("/<int:credential_id>", methods=["PUT"])
@login_required
def update_credential(credential_id: int):
    """Rotate or update an existing credential in-place (id stays stable for the flow canvas)."""
    data = request.json or {}
    name = str(data.get("name") or "").strip()[:128] or None
    secret_data = data.get("secret_data")

    if secret_data is not None and not isinstance(secret_data, dict):
        return jsonify({"error": "secret_data deve ser um objeto JSON"}), 400

    db = SessionLocal()
    try:
        cred = db.query(models.TenantIntegrationCredential).filter_by(
            id=credential_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not cred:
            return jsonify({"error": "not_found"}), 404

        if name:
            cred.name = name
        if secret_data is not None:
            cred.encrypted_data = encrypt_credential(secret_data)
        db.commit()
        return jsonify({"success": True, "id": cred.id})
    except Exception as e:
        db.rollback()
        logger.exception("Error updating credential %s", credential_id)
        return jsonify({"error": "internal_error"}), 500
    finally:
        db.close()


@credentials_bp.route("/<int:credential_id>", methods=["DELETE"])
@login_required
def delete_credential(credential_id: int):
    """Delete an existing credential."""
    db = SessionLocal()
    try:
        cred = db.query(models.TenantIntegrationCredential).filter_by(
            id=credential_id,
            tenant_id=current_user.tenant_id,
        ).first()

        if not cred:
            return jsonify({"error": "not_found"}), 404

        db.delete(cred)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()

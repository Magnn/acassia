"""
api/saas/api_keys.py — Gestão de API Keys do painel do profissional
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O profissional cria API keys no dashboard para:
  - Vender horóscopo no próprio app dele
  - Integrar mapa natal no site dele
  - Dar API access pra clientes dev

Endpoints:
  GET    /saas/api-keys          — lista as keys do tenant
  POST   /saas/api-keys          — cria nova key
  DELETE /saas/api-keys/<id>     — revoga key
"""

from __future__ import annotations

import hashlib
import logging
import secrets

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
api_keys_bp = Blueprint("saas_api_keys", __name__, url_prefix="/saas/api-keys")
ALLOWED_SCOPES = {"contacts:read", "contacts:write", "messages:write", "sequences:write"}


def _generate_key() -> tuple[str, str, str]:
    """Gera API key (raw, hash, prefix)."""
    raw = f"mm_pk_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:12]
    return raw, key_hash, prefix


@api_keys_bp.route("/", methods=["GET"])
@login_required
def list_keys():
    db = SessionLocal()
    try:
        keys = db.query(models.PublicApiKey).filter_by(
            tenant_id=current_user.tenant_id
        ).order_by(models.PublicApiKey.created_at.desc()).all()

        return jsonify({
            "keys": [
                {
                    "id": k.id,
                    "label": k.label,
                    "prefix": k.key_prefix,
                    "tier": k.tier,
                    "scopes": k.scopes or [],
                    "is_active": k.is_active,
                    "total_requests": k.total_requests or 0,
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                    "created_at": k.created_at.isoformat(),
                } for k in keys
            ]
        })
    finally:
        db.close()


@api_keys_bp.route("/", methods=["POST"])
@login_required
def create_key():
    body = request.get_json(silent=True) or {}
    label = (body.get("label") or "").strip()
    if not label:
        return jsonify({"error": "label_required"}), 422
    scopes = body.get("scopes") or sorted(ALLOWED_SCOPES)
    if not isinstance(scopes, list) or not set(scopes).issubset(ALLOWED_SCOPES):
        return jsonify({"error": "invalid_scopes", "allowed": sorted(ALLOWED_SCOPES)}), 422

    # Limite: max 5 keys por tenant (free)
    db = SessionLocal()
    try:
        count = db.query(models.PublicApiKey).filter_by(
            tenant_id=current_user.tenant_id, is_active=True,
        ).count()
        if count >= 10:
            return jsonify({"error": "max_keys_reached", "limit": 10}), 422

        raw, key_hash, prefix = _generate_key()
        key_obj = models.PublicApiKey(
            tenant_id=current_user.tenant_id,
            label=label,
            key_hash=key_hash,
            key_prefix=prefix,
            tier="free",
            scopes=scopes,
        )
        db.add(key_obj)
        db.commit()
        db.refresh(key_obj)

        return jsonify({
            "ok": True,
            "key": raw,  # MOSTRADO APENAS UMA VEZ
            "prefix": prefix,
            "id": key_obj.id,
            "scopes": scopes,
            "warning": "Guarde esta chave — ela não será exibida novamente.",
        }), 201
    finally:
        db.close()


@api_keys_bp.route("/<int:key_id>", methods=["DELETE"])
@login_required
def revoke_key(key_id: int):
    db = SessionLocal()
    try:
        key_obj = db.query(models.PublicApiKey).filter_by(
            id=key_id, tenant_id=current_user.tenant_id,
        ).first()
        if not key_obj:
            return jsonify({"error": "not_found"}), 404
        key_obj.is_active = False
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

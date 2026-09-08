"""api/v1/auth.py — Autenticação por API Key para API v1."""
from functools import wraps
import hashlib
from flask import request, jsonify, g
from db.database import SessionLocal
from db import models

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Header X-API-Key or Bearer token or query param
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.headers.get("X-API-Key") or request.args.get("api_key") or ""

        if not token:
            return jsonify({
                "error": "unauthorized",
                "message": "API Key obrigatória via header X-API-Key, Authorization: Bearer, ou ?api_key=",
            }), 401

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        db = SessionLocal()
        try:
            key_obj = db.query(models.PublicApiKey).filter_by(
                key_hash=token_hash,
                is_active=True,
            ).first()
            if not key_obj:
                return jsonify({"error": "invalid_api_key", "message": "API Key inválida ou desativada."}), 401

            g.tenant_id = key_obj.tenant_id
            g.api_key_id = key_obj.id
            g.api_tier = key_obj.tier

            # Incrementar estatísticas de uso da chave de API
            from datetime import datetime, timezone
            key_obj.total_requests = (key_obj.total_requests or 0) + 1
            key_obj.last_used_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

        return f(*args, **kwargs)
    return decorated

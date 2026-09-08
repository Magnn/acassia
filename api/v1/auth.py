"""Header-only API key authentication with per-key scopes."""
from functools import wraps
import hashlib
from flask import request, jsonify, g
from db.database import SessionLocal
from db import models


def require_api_key(scope_or_function=None):
    required_scope = scope_or_function if isinstance(scope_or_function, str) else None

    def decorator(function):
        @wraps(function)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
            token = token or request.headers.get("X-API-Key", "")
            if not token:
                return jsonify({"error": "unauthorized", "message": "Envie a API Key em X-API-Key ou Authorization: Bearer."}), 401
            db = SessionLocal()
            try:
                token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                key_obj = db.query(models.PublicApiKey).filter_by(key_hash=token_hash, is_active=True).first()
                if not key_obj:
                    return jsonify({"error": "invalid_api_key"}), 401
                if key_obj.scopes is None:
                    scopes = None
                else:
                    scopes = set(key_obj.scopes)

                if required_scope and scopes is not None and required_scope not in scopes:
                    return jsonify({"error": "insufficient_scope", "required_scope": required_scope}), 403
                g.tenant_id, g.api_key_id, g.api_tier = key_obj.tenant_id, key_obj.id, key_obj.tier
                g.api_scopes = sorted(scopes) if scopes is not None else ["*"]
                from datetime import datetime, timezone
                key_obj.total_requests = (key_obj.total_requests or 0) + 1
                key_obj.last_used_at = datetime.now(timezone.utc)
                db.commit()
            finally:
                db.close()
            return function(*args, **kwargs)
        return decorated

    if callable(scope_or_function):
        return decorator(scope_or_function)
    return decorator

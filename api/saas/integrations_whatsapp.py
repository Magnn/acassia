"""
Onboarding multi-tenant do WhatsApp Cloud API (Frente 1).

Permite ao tenant:
    - Cadastrar/atualizar credenciais Meta (access_token, phone_number_id, waba_id, app_secret)
    - Validar credenciais chamando GET /<phone_number_id> na Graph API
    - Definir verify_token proprio (alternativa ao token global do .env)
    - Remover binding (revoga acesso)

Endpoints:
    GET    /saas/integrations/whatsapp           — estado atual + URL do webhook
    POST   /saas/integrations/whatsapp/test      — valida credenciais sem salvar
    POST   /saas/integrations/whatsapp           — salva credenciais + cria binding
    DELETE /saas/integrations/whatsapp           — remove binding + secrets

Persistencia:
    - access_token + app_secret -> TenantFlowSecret (descrypta via _decrypt_secret)
    - phone_number_id + waba_id -> TenantFlowVariable (whatsapp.* keys consumidas
      por get_provider_for_tenant)
    - mapping phone_number_id -> tenant_id -> WaPhoneTenantBinding (lookup do webhook)
"""

from __future__ import annotations

import logging
import os
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
integrations_wa_bp = Blueprint(
    "saas_integrations_whatsapp", __name__,
    url_prefix="/saas/integrations/whatsapp",
)


GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")


# ─── Helpers ──────────────────────────────────────────────────────────


def _public_webhook_url() -> str:
    base = (os.getenv("PUBLIC_URL") or "").rstrip("/")
    if not base:
        # Best-effort: do que vem na request (dev)
        base = request.host_url.rstrip("/") if request else ""
    return f"{base}/webhook" if base else "/webhook"


def _store_secret(db, tenant_id: str, key: str, value: str) -> None:
    row = db.query(models.TenantFlowSecret).filter_by(
        tenant_id=tenant_id, key=key,
    ).first()
    if row:
        row.value_cipher = value
    else:
        db.add(models.TenantFlowSecret(
            tenant_id=tenant_id, key=key, value_cipher=value,
        ))


def _delete_secret(db, tenant_id: str, key: str) -> None:
    db.query(models.TenantFlowSecret).filter_by(
        tenant_id=tenant_id, key=key,
    ).delete()


def _store_variable(db, tenant_id: str, key: str, value) -> None:
    row = db.query(models.TenantFlowVariable).filter_by(
        tenant_id=tenant_id, key=key,
    ).first()
    if row:
        row.value_json = value
    else:
        db.add(models.TenantFlowVariable(
            tenant_id=tenant_id, key=key, value_json=value,
        ))


def _delete_variable(db, tenant_id: str, key: str) -> None:
    db.query(models.TenantFlowVariable).filter_by(
        tenant_id=tenant_id, key=key,
    ).delete()


def _meta_get(path: str, access_token: str, timeout: int = 8) -> tuple[int, dict]:
    """GET na Graph API. Retorna (status, body_json_or_error)."""
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{path.lstrip('/')}"
    if "?" in url:
        url = f"{url}&{urlencode({'access_token': access_token})}"
    else:
        url = f"{url}?{urlencode({'access_token': access_token})}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            import json
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            import json
            body = json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            body = {"error": {"message": e.reason}}
        return e.code, body
    except Exception as exc:
        return 0, {"error": {"message": str(exc)}}


def _validate_token_and_phone(access_token: str, phone_number_id: str) -> tuple[bool, dict]:
    """
    Valida se access_token tem permissao em phone_number_id.
    Retorna (ok, info) onde info contem display_phone_number, verified_name etc.
    """
    if not access_token or not phone_number_id:
        return False, {"error": "missing_credentials"}
    status, body = _meta_get(phone_number_id, access_token)
    if status == 200 and isinstance(body, dict) and not body.get("error"):
        return True, body
    err = body.get("error") if isinstance(body, dict) else {"message": "unknown"}
    return False, {"error": err, "http_status": status}


def _serialize_binding(b: models.WaPhoneTenantBinding) -> dict:
    return {
        "phone_number_id": b.phone_number_id,
        "tenant_id": b.tenant_id,
        "waba_id": b.waba_id,
        "display_phone_number": b.display_phone_number,
        "has_verify_token": bool(b.verify_token),
        "has_app_secret": bool(b.app_secret),
        "status": b.status,
        "last_verified_at": b.last_verified_at.isoformat() if b.last_verified_at else None,
        "last_error": b.last_error,
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────


@integrations_wa_bp.route("", methods=["GET"])
@login_required
def get_status():
    db = SessionLocal()
    try:
        binding = db.query(models.WaPhoneTenantBinding).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()

        # Variables snapshot (sem expor secrets)
        wa_vars = {
            row.key: row.value_json
            for row in db.query(models.TenantFlowVariable).filter(
                models.TenantFlowVariable.tenant_id == current_user.tenant_id,
                models.TenantFlowVariable.key.like("whatsapp.%"),
            ).all()
        }
        secret_keys = [
            row.key for row in db.query(models.TenantFlowSecret).filter(
                models.TenantFlowSecret.tenant_id == current_user.tenant_id,
                models.TenantFlowSecret.key.like("whatsapp.%"),
            ).all()
        ]

        return jsonify({
            "binding": _serialize_binding(binding) if binding else None,
            "variables": wa_vars,
            "secrets_set": secret_keys,
            "webhook_url": _public_webhook_url(),
            "graph_api_version": GRAPH_API_VERSION,
            "global_verify_token_set": bool(os.getenv("META_VERIFY_TOKEN")),
        })
    finally:
        db.close()


@integrations_wa_bp.route("/test", methods=["POST"])
@login_required
def test_credentials():
    body = request.get_json(silent=True) or {}
    access_token = (body.get("access_token") or "").strip()
    phone_number_id = (body.get("phone_number_id") or "").strip()

    if not access_token or not phone_number_id:
        return jsonify({"error": "missing_fields"}), 422

    ok, info = _validate_token_and_phone(access_token, phone_number_id)
    if not ok:
        return jsonify({"ok": False, **info}), 200

    return jsonify({
        "ok": True,
        "display_phone_number": info.get("display_phone_number"),
        "verified_name": info.get("verified_name"),
        "quality_rating": info.get("quality_rating"),
    })


@integrations_wa_bp.route("", methods=["POST"])
@login_required
def save_binding():
    """
    Salva (ou atualiza) credenciais Meta WhatsApp Cloud do tenant.

    Body:
        access_token         (obrigatorio)
        phone_number_id      (obrigatorio)
        waba_id              (opcional mas recomendado)
        app_secret           (opcional — pra HMAC validation per-tenant)
        verify_token         (opcional — gera aleatorio se vazio)
        provider             (opcional: 'meta_cloud' default)
        skip_validation      (opcional: pula chamada Graph API; util em dev offline)
    """
    body = request.get_json(silent=True) or {}
    access_token = (body.get("access_token") or "").strip()
    phone_number_id = (body.get("phone_number_id") or "").strip()
    waba_id = (body.get("waba_id") or "").strip() or None
    app_secret = (body.get("app_secret") or "").strip() or None
    verify_token = (body.get("verify_token") or "").strip()
    provider = (body.get("provider") or "meta_cloud").strip().lower()
    skip_validation = bool(body.get("skip_validation"))

    if not access_token or not phone_number_id:
        return jsonify({"error": "missing_fields", "required": ["access_token", "phone_number_id"]}), 422

    if not verify_token:
        verify_token = secrets.token_urlsafe(32)

    info: dict = {}
    if not skip_validation:
        ok, info = _validate_token_and_phone(access_token, phone_number_id)
        if not ok:
            return jsonify({"ok": False, "error": "credentials_invalid", **info}), 422

    db = SessionLocal()
    try:
        # 1) Garante que phone_number_id nao esta vinculado a OUTRO tenant
        existing = db.query(models.WaPhoneTenantBinding).filter_by(
            phone_number_id=phone_number_id,
        ).first()
        if existing and existing.tenant_id != current_user.tenant_id:
            return jsonify({
                "ok": False,
                "error": "phone_already_bound_to_other_tenant",
                "message": "Esse phone_number_id ja esta vinculado a outro tenant. "
                           "Solicite ao admin remover o binding antes.",
            }), 409

        # 2) Persiste secrets (access_token + app_secret) e variables (phone_id, waba_id, provider)
        _store_secret(db, current_user.tenant_id, "whatsapp.access_token", access_token)
        _store_variable(db, current_user.tenant_id, "whatsapp.phone_number_id", phone_number_id)
        if waba_id:
            _store_variable(db, current_user.tenant_id, "whatsapp.waba_id", waba_id)
        _store_variable(db, current_user.tenant_id, "whatsapp.provider", provider)
        if app_secret:
            _store_secret(db, current_user.tenant_id, "whatsapp.app_secret", app_secret)

        # 3) Upsert binding
        if existing:
            binding = existing
        else:
            binding = models.WaPhoneTenantBinding(phone_number_id=phone_number_id)
            db.add(binding)

        binding.tenant_id = current_user.tenant_id
        binding.waba_id = waba_id
        binding.display_phone_number = info.get("display_phone_number") if isinstance(info, dict) else None
        binding.verify_token = verify_token
        binding.app_secret = app_secret
        binding.status = "active" if not skip_validation else "pending"
        binding.last_verified_at = datetime.now(timezone.utc) if not skip_validation else None
        binding.last_error = None
        binding.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(binding)

        # 4) Invalida caches in-memory
        try:
            from api.tenant_config import clear_cache as clear_tenant_cfg
            clear_tenant_cfg(current_user.tenant_id)
        except Exception:
            pass
        try:
            from wa_tenant_resolver import invalidate_cache as invalidate_resolver
            invalidate_resolver(phone_number_id)
        except Exception:
            pass

        # 5) Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="integrations.whatsapp.bound",
                target_type="phone_number_id",
                target_id=phone_number_id,
                payload={
                    "waba_id": waba_id,
                    "provider": provider,
                    "validated": not skip_validation,
                    "display_phone_number": info.get("display_phone_number") if isinstance(info, dict) else None,
                },
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({
            "ok": True,
            "binding": _serialize_binding(binding),
            "verify_token": verify_token,
            "webhook_url": _public_webhook_url(),
            "instructions": [
                "1. Va em developers.facebook.com -> seu app -> WhatsApp -> Configuracao",
                f"2. Cole '{_public_webhook_url()}' no Webhook callback URL",
                f"3. Cole o verify_token gerado: {verify_token}",
                "4. Em 'Webhook fields', assine ao menos: messages",
                "5. Pronto — mande uma msg pro numero pra testar",
            ],
        })
    finally:
        db.close()


@integrations_wa_bp.route("", methods=["DELETE"])
@login_required
def remove_binding():
    """Remove binding + secrets (revoga conexao)."""
    db = SessionLocal()
    try:
        binding = db.query(models.WaPhoneTenantBinding).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()
        phone_id = binding.phone_number_id if binding else None
        if binding:
            db.delete(binding)

        # Limpa variables/secrets relacionados a whatsapp
        for key in ("whatsapp.access_token", "whatsapp.app_secret"):
            _delete_secret(db, current_user.tenant_id, key)
        for key in ("whatsapp.phone_number_id", "whatsapp.waba_id"):
            _delete_variable(db, current_user.tenant_id, key)

        db.commit()

        try:
            from api.tenant_config import clear_cache as clear_tenant_cfg
            clear_tenant_cfg(current_user.tenant_id)
        except Exception:
            pass
        try:
            from wa_tenant_resolver import invalidate_cache as invalidate_resolver
            invalidate_resolver(phone_id)
        except Exception:
            pass

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="integrations.whatsapp.unbound",
                target_type="phone_number_id",
                target_id=phone_id or "(none)",
                payload={},
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({"ok": True})
    finally:
        db.close()


@integrations_wa_bp.route("/rotate-verify-token", methods=["POST"])
@login_required
def rotate_verify_token():
    """Gera novo verify_token (depois precisa atualizar no painel da Meta)."""
    db = SessionLocal()
    try:
        binding = db.query(models.WaPhoneTenantBinding).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()
        if not binding:
            return jsonify({"error": "no_binding"}), 404

        binding.verify_token = secrets.token_urlsafe(32)
        binding.updated_at = datetime.now(timezone.utc)
        db.commit()

        try:
            from wa_tenant_resolver import invalidate_cache as invalidate_resolver
            invalidate_resolver(binding.phone_number_id)
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "verify_token": binding.verify_token,
            "webhook_url": _public_webhook_url(),
        })
    finally:
        db.close()

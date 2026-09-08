"""
Endpoints WhatsApp Connect (multi-provider) — JSON pra consumo do React.

Rotas (todas /saas/whatsapp/*):

  GET  /status              status do provider ativo (configured, ok, hint)
  GET  /config              config atual do tenant (provider + chaves não-sensíveis)
  PUT  /config              atualiza provider escolhido e chaves
  POST /test                manda mensagem de teste pra um número

Segredos (access_token, api_key) entram cifrados em TenantFlowSecret;
ids/URLs ficam em TenantFlowVariable (visíveis no painel).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from api.tenant_config import clear_cache, get_tenant_config
from api.whatsapp_providers import (
    ProviderError,
    ProviderMode,
    get_provider_for_tenant,
)
from db import models
from db.database import SessionLocal
from api.utils.tenant_secrets import encrypt_tenant_secret

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint("saas_whatsapp", __name__, url_prefix="/saas/whatsapp")


# ── Helpers DB ─────────────────────────────────────────────────────────

def _set_var(tenant_id: str, key: str, value: Any) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=key,
        ).first()
        if existing:
            existing.value_json = value
        else:
            db.add(models.TenantFlowVariable(
                tenant_id=tenant_id, key=key, value_json=value,
            ))
        db.commit()
    finally:
        db.close()


def _del_var(tenant_id: str, key: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=key,
        ).first()
        if existing:
            db.delete(existing)
            db.commit()
    finally:
        db.close()


def _set_secret(tenant_id: str, key: str, value: str) -> None:
    """Encrypta e grava no formato versionado do cofre."""
    cipher = encrypt_tenant_secret(value)
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key=key,
        ).first()
        if existing:
            existing.value_cipher = cipher
        else:
            db.add(models.TenantFlowSecret(
                tenant_id=tenant_id, key=key, value_cipher=cipher,
            ))
        db.commit()
    finally:
        db.close()


def _del_secret(tenant_id: str, key: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key=key,
        ).first()
        if existing:
            db.delete(existing)
            db.commit()
    finally:
        db.close()


# ── Routes ─────────────────────────────────────────────────────────────

@whatsapp_bp.route("/status", methods=["GET"])
@login_required
def status():
    tid = current_user.tenant_id
    provider = get_provider_for_tenant(tid)
    return jsonify(provider.status()), 200


@whatsapp_bp.route("/config", methods=["GET"])
@login_required
def config_get():
    """Retorna config atual SEM expor segredos (só flags has_*)."""
    tid = current_user.tenant_id
    cfg = get_tenant_config(tid)
    wa = cfg.get("whatsapp") if isinstance(cfg, dict) else None
    wa = wa if isinstance(wa, dict) else {}

    coex = wa.get("coex") if isinstance(wa.get("coex"), dict) else {}
    evo = wa.get("evolution") if isinstance(wa.get("evolution"), dict) else {}

    return jsonify({
        "provider": str(wa.get("provider") or "meta_cloud"),
        "meta_cloud": {
            "phone_number_id": wa.get("phone_number_id") or "",
            "waba_id": wa.get("waba_id") or "",
            "has_access_token": bool(wa.get("access_token")),
        },
        "coex": {
            "api_url": coex.get("api_url") or "",
            "instance": coex.get("instance") or "",
            "has_api_key": bool(coex.get("api_key")),
        },
        "evolution": {
            "server_url": evo.get("server_url") or "",
            "instance": evo.get("instance") or "",
            "has_api_key": bool(evo.get("api_key")),
        },
    }), 200


@whatsapp_bp.route("/config", methods=["PUT"])
@login_required
def config_put():
    """
    Atualiza config. Body JSON:
      { provider: 'meta_cloud'|'coex'|'evolution',
        meta_cloud?: { phone_number_id, waba_id, access_token? },
        coex?:       { api_url, instance, api_key? },
        evolution?:  { server_url, instance, api_key? } }

    Segredos (access_token, api_key) só são gravados se ENVIADOS no body
    (omitir mantém o atual). Para apagar, mande string vazia.
    """
    tid = current_user.tenant_id
    body = request.get_json(silent=True) or {}

    valid_modes = {m.value for m in ProviderMode}
    mode = str(body.get("provider") or "").strip().lower()
    if mode and mode not in valid_modes:
        return jsonify({"error": f"provider inválido: {mode}"}), 400

    if mode:
        _set_var(tid, "whatsapp.provider", mode)

    mc = body.get("meta_cloud") or {}
    if isinstance(mc, dict):
        if "phone_number_id" in mc:
            _set_var(tid, "whatsapp.phone_number_id", str(mc["phone_number_id"]).strip())
        if "waba_id" in mc:
            _set_var(tid, "whatsapp.waba_id", str(mc["waba_id"]).strip())
        if "access_token" in mc:
            tok = str(mc["access_token"] or "")
            if tok.strip():
                _set_secret(tid, "whatsapp.access_token", tok.strip())
            else:
                _del_secret(tid, "whatsapp.access_token")

    coex = body.get("coex") or {}
    if isinstance(coex, dict):
        if "api_url" in coex:
            _set_var(tid, "whatsapp.coex.api_url", str(coex["api_url"]).strip())
        if "instance" in coex:
            _set_var(tid, "whatsapp.coex.instance", str(coex["instance"]).strip())
        if "api_key" in coex:
            k = str(coex["api_key"] or "")
            if k.strip():
                _set_secret(tid, "whatsapp.coex.api_key", k.strip())
            else:
                _del_secret(tid, "whatsapp.coex.api_key")

    evo = body.get("evolution") or {}
    if isinstance(evo, dict):
        if "server_url" in evo:
            _set_var(tid, "whatsapp.evolution.server_url", str(evo["server_url"]).strip())
        if "instance" in evo:
            _set_var(tid, "whatsapp.evolution.instance", str(evo["instance"]).strip())
        if "api_key" in evo:
            k = str(evo["api_key"] or "")
            if k.strip():
                _set_secret(tid, "whatsapp.evolution.api_key", k.strip())
            else:
                _del_secret(tid, "whatsapp.evolution.api_key")

    clear_cache(tid)
    return jsonify({"ok": True}), 200


@whatsapp_bp.route("/test", methods=["POST"])
@login_required
def test():
    """Manda mensagem-teste pro número informado. Body: { to: '5511...' }"""
    tid = current_user.tenant_id
    body = request.get_json(silent=True) or {}
    to = str(body.get("to") or "").strip()
    if not to:
        return jsonify({"error": "to obrigatório (com DDI+DDD+número)"}), 400
    provider = get_provider_for_tenant(tid)
    try:
        result = provider.test_connection(to)
        return jsonify({
            "ok": result.ok,
            "message_id": result.message_id,
            "error": result.error,
        }), (200 if result.ok else 400)
    except ProviderError as exc:
        logger.error("[whatsapp/test] tenant=%s falha: %s", tid, exc)
        return jsonify({"ok": False, "error": str(exc)}), 500


@whatsapp_bp.route("/qr", methods=["GET"])
@login_required
def qr():
    """Para Evolution: retorna QR code pra parear a instância."""
    tid = current_user.tenant_id
    provider = get_provider_for_tenant(tid)
    if not isinstance(provider.mode, ProviderMode) or provider.mode != ProviderMode.EVOLUTION:
        return jsonify({"error": "QR só disponível pro provider Evolution"}), 400
    # Provider tem método específico
    fn = getattr(provider, "get_qr_code", None)
    if fn is None:
        return jsonify({"error": "provider não suporta QR"}), 500
    res = fn()
    return jsonify({
        "ok": res.ok,
        "data": res.raw,
        "error": res.error,
    }), (200 if res.ok else 400)

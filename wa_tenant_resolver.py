"""
Resolve tenant_id a partir de phone_number_id da Meta (Frente 1).

Usado pelo webhook /webhook pra rotear inbound para o tenant correto.
Cache local 60s pra evitar query a cada msg.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


_CACHE_TTL = 60.0
_PHONE_TO_TENANT: dict[str, tuple[float, str]] = {}
_VERIFY_TOKEN_TO_PHONE: dict[str, tuple[float, str]] = {}


def _now() -> float:
    return time.time()


def resolve_tenant_for_phone_id(phone_number_id: str | None) -> str:
    """
    Mapeia phone_number_id -> tenant_id consultando WaPhoneTenantBinding.
    Cache 60s.

    Fallback: se ENV MEU_MISTERIO_TENANT_ID estiver setado, usa ele.
              Senao, retorna 'default' (modo single-tenant legado).
    """
    if not phone_number_id:
        return _legacy_default()

    pid = str(phone_number_id).strip()
    cached = _PHONE_TO_TENANT.get(pid)
    if cached and cached[0] > _now():
        return cached[1]

    db = SessionLocal()
    try:
        row = db.query(models.WaPhoneTenantBinding).filter_by(
            phone_number_id=pid,
        ).first()
        if row and row.tenant_id:
            _PHONE_TO_TENANT[pid] = (_now() + _CACHE_TTL, row.tenant_id)
            return row.tenant_id
    except Exception as exc:
        logger.warning("[wa_tenant_resolver] falha consultando binding: %s", exc)
    finally:
        db.close()

    fallback = _legacy_default()
    # Cache curto pro caso de phone_id desconhecido (evita query toda msg)
    _PHONE_TO_TENANT[pid] = (_now() + 10.0, fallback)
    return fallback


def resolve_tenant_for_verify_token(verify_token: str | None) -> tuple[str, str] | None:
    """
    Mapeia verify_token -> (tenant_id, phone_number_id) para validacao GET
    do webhook quando o token nao bate com o global.

    Retorna None se nao encontrar binding.
    """
    if not verify_token:
        return None

    token = str(verify_token).strip()
    cached = _VERIFY_TOKEN_TO_PHONE.get(token)
    if cached and cached[0] > _now():
        pid = cached[1]
        # tenant pode ter mudado; sempre re-resolve
        return (resolve_tenant_for_phone_id(pid), pid)

    db = SessionLocal()
    try:
        row = db.query(models.WaPhoneTenantBinding).filter(
            models.WaPhoneTenantBinding.verify_token == token,
        ).first()
        if row:
            _VERIFY_TOKEN_TO_PHONE[token] = (_now() + _CACHE_TTL, row.phone_number_id)
            return (row.tenant_id, row.phone_number_id)
    except Exception as exc:
        logger.warning("[wa_tenant_resolver] verify lookup falhou: %s", exc)
    finally:
        db.close()

    return None


_PATH_TO_BINDING: dict[str, tuple[float, dict]] = {}


def resolve_binding_by_webhook_path(webhook_path: str | None) -> dict | None:
    """
    Resolve binding pelo webhook_path (per-tenant URL). Cache 60s.

    Retorna dict {tenant_id, phone_number_id, verify_token, app_secret}
    ou None se nao encontrar.
    """
    if not webhook_path:
        return None
    path = str(webhook_path).strip()
    cached = _PATH_TO_BINDING.get(path)
    if cached and cached[0] > _now():
        return cached[1]

    db = SessionLocal()
    try:
        row = db.query(models.WaPhoneTenantBinding).filter_by(
            webhook_path=path,
        ).first()
        if row:
            payload = {
                "tenant_id": row.tenant_id,
                "phone_number_id": row.phone_number_id,
                "verify_token": row.verify_token,
                "app_secret": row.app_secret,
            }
            _PATH_TO_BINDING[path] = (_now() + _CACHE_TTL, payload)
            return payload
    except Exception as exc:
        logger.warning("[wa_tenant_resolver] webhook_path lookup falhou: %s", exc)
    finally:
        db.close()
    return None


def get_app_secret_for_phone_id(phone_number_id: str | None) -> str | None:
    """Retorna app_secret do binding (ou None se nao houver — usar global)."""
    if not phone_number_id:
        return None
    db = SessionLocal()
    try:
        row = db.query(models.WaPhoneTenantBinding).filter_by(
            phone_number_id=str(phone_number_id).strip(),
        ).first()
        return row.app_secret if (row and row.app_secret) else None
    except Exception:
        return None
    finally:
        db.close()


def invalidate_cache(phone_number_id: Optional[str] = None) -> None:
    if phone_number_id is None:
        _PHONE_TO_TENANT.clear()
        _VERIFY_TOKEN_TO_PHONE.clear()
        _PATH_TO_BINDING.clear()
        return
    _PHONE_TO_TENANT.pop(str(phone_number_id).strip(), None)


def invalidate_webhook_path_cache(webhook_path: str | None = None) -> None:
    if webhook_path is None:
        _PATH_TO_BINDING.clear()
    else:
        _PATH_TO_BINDING.pop(str(webhook_path).strip(), None)


def _legacy_default() -> str:
    raw = (os.getenv("MEU_MISTERIO_TENANT_ID") or "default").strip()
    return raw or "default"


def extract_phone_number_id_from_payload(data: dict) -> str | None:
    """
    Webhooks Meta enviam phone_number_id em
        data.entry[0].changes[0].value.metadata.phone_number_id
    """
    if not isinstance(data, dict):
        return None
    try:
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value") or {}
        meta = value.get("metadata") or {}
        pid = meta.get("phone_number_id")
        return str(pid).strip() if pid else None
    except Exception:
        return None

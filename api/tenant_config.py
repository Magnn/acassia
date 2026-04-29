"""
Configuração por tenant — façade que substitui o uso direto de CONFIG_CLIENTE.

Carrega valores do DB (TenantFlowVariable, TenantFlowSecret, StudioAgent) com
fallback pra CONFIG_CLIENTE (legado, single-tenant via .env).

Forma de retorno espelha CONFIG_CLIENTE pra que consumidores existentes
(engine, recovery_engine, flows/fase_*) migrem com mudança mínima:

    # antes:
    from config_cliente import CONFIG_CLIENTE
    preco = CONFIG_CLIENTE["preco_servico"]

    # depois:
    from api.tenant_config import get_tenant_config
    cfg = get_tenant_config(self.tenant_id)
    preco = cfg["preco_servico"]

Cache:
    Read-through TTL 60s in-memory por processo. Após editar config no painel,
    o caller (UI ou API) deve chamar `clear_cache(tenant_id)` pra invalidar.

Ver: docs/MIGRACAO_CONFIG_CLIENTE.md
"""

from __future__ import annotations

import copy
import logging
import time
from types import MappingProxyType
from typing import Any, Mapping, Optional

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60.0
_CACHE: dict[str, tuple[float, Mapping[str, Any]]] = {}


def get_tenant_config(tenant_id: str) -> Mapping[str, Any]:
    """
    Retorna config consolidada do tenant (read-only via MappingProxyType).

    Resolução em ordem (do menos pro mais específico):
      1. CONFIG_CLIENTE (legado/.env) — base
      2. TenantFlowVariable (key/value_json) — sobrescreve
      3. TenantFlowSecret (key/value_cipher) — sobrescreve com decrypt

    Args:
        tenant_id: identificador do tenant. Use ``"default"`` pra modo legado.

    Returns:
        ``MappingProxyType`` (proxy read-only) com mesma estrutura de
        CONFIG_CLIENTE legado.
    """
    if not tenant_id:
        tenant_id = "default"

    now = time.time()
    cached = _CACHE.get(tenant_id)
    if cached and cached[0] > now:
        return cached[1]

    cfg = _build_tenant_config(tenant_id)
    _CACHE[tenant_id] = (now + _CACHE_TTL_SECONDS, cfg)
    return cfg


def clear_cache(tenant_id: Optional[str] = None) -> None:
    """
    Invalida cache. Sem argumento, limpa tudo. Caller deve chamar quando
    edita TenantFlowVariable/Secret no painel SaaS.
    """
    if tenant_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(tenant_id, None)


def _build_tenant_config(tenant_id: str) -> Mapping[str, Any]:
    """Monta o dict consolidado e devolve proxy somente-leitura."""
    # Base: CONFIG_CLIENTE (legado/.env). Deep copy pra evitar mutação cruzada.
    from config_cliente import CONFIG_CLIENTE
    cfg = copy.deepcopy(CONFIG_CLIENTE)

    db = None
    try:
        db = SessionLocal()
        for var in db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id).all():
            _apply_dotted_key(cfg, var.key, var.value_json)

        for secret in db.query(models.TenantFlowSecret).filter_by(tenant_id=tenant_id).all():
            value = _decrypt_secret(secret.value_cipher)
            _apply_dotted_key(cfg, secret.key, value)
    except Exception as exc:
        # Defensivo: se DB cai, retornamos o legado puro (degradação graciosa)
        logger.exception(
            "[tenant_config] DB indisponível pra tenant=%s — usando fallback CONFIG_CLIENTE: %s",
            tenant_id, exc,
        )
    finally:
        if db is not None:
            db.close()

    return MappingProxyType(cfg)


def _apply_dotted_key(cfg: dict, key: str, value: Any) -> None:
    """
    Aplica ``key`` no dict ``cfg``. Suporta dotted keys pra nested dicts:

      - ``"preco_servico"`` → ``cfg["preco_servico"] = value``
      - ``"perfil_negocio.tom_voz"`` → ``cfg["perfil_negocio"]["tom_voz"] = value``
      - ``"checkout_urls.130"`` → ``cfg["checkout_urls"]["130"] = value``
    """
    if "." not in key:
        cfg[key] = value
        return

    parts = key.split(".")
    cursor = cfg
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _decrypt_secret(value_cipher: str) -> str:
    """
    Stub de descriptografia. Em dev, value_cipher é texto puro.

    Em produção: substituir por Fernet/AWS KMS/Vault. O contrato mantém-se:
    string in → string out.
    """
    return value_cipher or ""

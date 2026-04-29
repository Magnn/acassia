"""
Isolamento por conta (multi-tenant): cada assinatura = um tenant_id estável.

Uso típico:
  - Uma instância / um número WhatsApp: variável de ambiente ACASSIA_TENANT_ID (default: default).
  - API / dashboard: cabeçalho X-Acassia-Tenant (ou query ?tenant=) quando o mesmo servidor atende várias contas.
  - Webhook multi-tenant: ``tenant_override_ctx(tenant_id)`` define o tenant pra
    duração de uma chamada do engine via contextvar (thread-safe).

O funil, leads, agentes publicados e publicação do Studio ficam escopados por tenant_id.
"""
from __future__ import annotations

import contextlib
import contextvars
import os
import re
from typing import Iterator, Optional

_MAX_LEN = 64
_RE_SAFE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")


def normalize_tenant_id(raw: Optional[str]) -> str:
    s = (raw or "").strip()
    if not s:
        return "default"
    if len(s) > _MAX_LEN:
        s = s[:_MAX_LEN]
    if not _RE_SAFE.match(s):
        return "default"
    return s


_ENGINE_TENANT_OVERRIDE: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "acassia_engine_tenant_override", default=None,
)


def get_engine_tenant_id() -> str:
    """
    Motor WhatsApp / recovery.

    Resolução em ordem:
      1. Override per-call via ``tenant_override_ctx(...)`` (multi-tenant webhook).
      2. ENV ``ACASSIA_TENANT_ID`` (legado single-tenant).
      3. ``"default"`` como fallback.
    """
    override = _ENGINE_TENANT_OVERRIDE.get()
    if override:
        return normalize_tenant_id(override)
    return normalize_tenant_id(os.getenv("ACASSIA_TENANT_ID", "default"))


@contextlib.contextmanager
def tenant_override_ctx(tenant_id: Optional[str]) -> Iterator[Optional[str]]:
    """
    Context manager que define o tenant_id corrente da thread/task.

    Uso:
        with tenant_override_ctx(resolved_tenant):
            motor.processar_mensagem(...)

    O override e revertido automaticamente ao sair do bloco, mesmo em excecao.
    Funciona thread-safe via ContextVar.
    """
    if not tenant_id:
        yield None
        return
    token = _ENGINE_TENANT_OVERRIDE.set(normalize_tenant_id(tenant_id))
    try:
        yield tenant_id
    finally:
        _ENGINE_TENANT_OVERRIDE.reset(token)


def get_request_tenant_id() -> str:
    """Rotas Flask: header ou query; fallback env; default default."""
    try:
        from flask import has_request_context, request

        if has_request_context():
            h = (request.headers.get("X-Acassia-Tenant") or "").strip()
            if h:
                return normalize_tenant_id(h)
            q = (request.args.get("tenant") or "").strip()
            if q:
                return normalize_tenant_id(q)
    except Exception:
        pass
    return normalize_tenant_id(os.getenv("ACASSIA_TENANT_ID", "default"))

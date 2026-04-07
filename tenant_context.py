"""
Isolamento por conta (multi-tenant): cada assinatura = um tenant_id estável.

Uso típico:
  - Uma instância / um número WhatsApp: variável de ambiente ACASSIA_TENANT_ID (default: default).
  - API / dashboard: cabeçalho X-Acassia-Tenant (ou query ?tenant=) quando o mesmo servidor atende várias contas.

O funil, leads, agentes publicados e publicação do Studio ficam escopados por tenant_id.
"""
from __future__ import annotations

import os
import re
from typing import Optional

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


def get_engine_tenant_id() -> str:
    """Motor WhatsApp / recovery: um tenant por processo (env)."""
    return normalize_tenant_id(os.getenv("ACASSIA_TENANT_ID", "default"))


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

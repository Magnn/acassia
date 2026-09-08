"""
api/utils/correlation.py — Correlation ID middleware
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Adiciona um X-Correlation-ID único a cada request para
rastreabilidade de logs e debugging em produção.
"""

import uuid
import logging
from flask import g, request

logger = logging.getLogger(__name__)


def init_correlation_id(app):
    """Registra middleware de correlation ID no app Flask."""

    @app.before_request
    def _set_correlation_id():
        cid = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex[:16]
        g.correlation_id = cid

    @app.after_request
    def _add_correlation_header(response):
        cid = getattr(g, "correlation_id", None)
        if cid:
            response.headers["X-Correlation-ID"] = cid
        return response


def get_correlation_id() -> str:
    """Retorna o correlation ID do request atual."""
    return getattr(g, "correlation_id", "no-request")

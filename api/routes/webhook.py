"""
api/routes/webhook.py — Rotas de Webhook (Meta + Cakto)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extraído do app.py monolítico.
Contém os endpoints de webhook para:
  - Meta/WhatsApp (verificação + processamento de mensagens)
  - Multi-tenant webhook (/<webhook_path>)
  - Cakto (pós-venda)
"""

import hashlib
import hmac
import logging
import os
import time
import json
import threading
from collections import deque

from flask import Blueprint, request, jsonify

from db.database import SessionLocal
from db import models
from sqlalchemy.exc import IntegrityError
from tenant_context import get_engine_tenant_id

logger = logging.getLogger(__name__)

webhook_bp = Blueprint("webhook", __name__)

# Cache de Idempotência
CACHE_MENSAGENS = deque(maxlen=2000)
LOCK_IDEMPOTENCIA = threading.Lock()


def _try_claim_wamid_db(wamid: str) -> bool:
    """True = primeira vez. False = wamid já persistido."""
    if not wamid:
        return True
    tid = get_engine_tenant_id()
    db = SessionLocal()
    try:
        db.add(
            models.WhatsAppInboundReceipt(
                tenant_id=tid,
                wamid=str(wamid)[:128],
                lead_id=None,
            )
        )
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    except Exception as e:
        db.rollback()
        logger.warning("⚠️ [WEBHOOK] claim wamid falhou (fail-open): %s", e)
        return True
    finally:
        db.close()


def _validate_hmac(payload_bytes: bytes) -> bool:
    """Validação HMAC SHA256 do webhook Meta."""
    app_secret = os.getenv("APP_SECRET", "")
    if not app_secret:
        # Em produção, sem secret configurado → rejeitar
        # Em dev/test, permitir (PYTEST_CURRENT_TEST ou FLASK_ENV=development)
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("FLASK_ENV") == "development":
            return True
        logger.warning("[WEBHOOK] APP_SECRET não configurado — rejeitando requisição")
        return False
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if not sig_header:
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig_header, expected)


# Nota: as rotas de webhook reais (com toda a lógica de processamento Meta/Cakto)
# continuam em app.py por enquanto, pois dependem de `motor` e `inbox_manager`
# que são singletons inicializados lá. A migração completa virá quando o
# motor for refatorado para injeção de dependência.
#
# Este blueprint serve como ponto de montagem preparatório para a migração.

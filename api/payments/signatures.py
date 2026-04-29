"""
Validação de signatures de webhooks.

- **Stripe** segue o protocolo oficial (timestamp + HMAC-SHA256 + tolerância
  anti-replay). Header ``Stripe-Signature``: ``t=<unix>,v1=<sig>[,v1=<sig2>]``.
- **Cakto** usa HMAC-SHA256 simples do payload bruto, header configurável.
  Aceitamos prefixo ``sha256=`` opcional.

Comparações usam ``hmac.compare_digest`` (constant-time) — nunca ``==`` —
pra evitar timing attacks.
"""

import hashlib
import hmac
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Tolerância de deriva de relógio anti-replay (segundos). Padrão Stripe.
STRIPE_TOLERANCE_SECONDS = 300


def verify_cakto_signature(
    raw_payload: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """
    Valida HMAC-SHA256(secret, raw_payload) batendo com signature_header.

    Header pode vir com ou sem prefixo ``sha256=`` — normalizamos.

    Returns:
        True se signature bate, False caso contrário (incluindo args vazios).
    """
    if not signature_header or not secret or not raw_payload:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        msg=raw_payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    sig_clean = signature_header.strip()
    if sig_clean.startswith("sha256="):
        sig_clean = sig_clean[len("sha256="):]

    return hmac.compare_digest(expected, sig_clean)


def verify_stripe_signature(
    raw_payload: bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = STRIPE_TOLERANCE_SECONDS,
    *,
    _now_unix: Optional[float] = None,  # injetável apenas pra testes
) -> bool:
    """
    Valida o header ``Stripe-Signature`` seguindo o protocolo oficial:
    https://stripe.com/docs/webhooks/signatures

    Algoritmo:
      1. Parseia ``t=<ts>,v1=<sig>[,v1=<sig2>...]``
      2. Verifica que ``ts`` está dentro da janela (anti-replay)
      3. Calcula HMAC-SHA256 de ``f"{ts}.{payload}"``
      4. Compara (constant-time) contra cada ``v1=`` do header

    Stripe pode enviar múltiplos ``v1`` durante rotação de secret — qualquer
    um válido aceita. Se ``v0`` aparecer (legado), é ignorado.
    """
    if not signature_header or not secret or not raw_payload:
        return False

    # Parse: chave -> lista de valores (suporta múltiplos v1=)
    parts: dict[str, list[str]] = {}
    for pair in signature_header.split(","):
        if "=" not in pair:
            continue
        k, v = pair.strip().split("=", 1)
        parts.setdefault(k, []).append(v)

    timestamps = parts.get("t", [])
    v1_signatures = parts.get("v1", [])
    if not timestamps or not v1_signatures:
        return False

    try:
        ts_int = int(timestamps[0])
    except ValueError:
        return False

    # Anti-replay
    now = _now_unix if _now_unix is not None else time.time()
    if abs(now - ts_int) > tolerance_seconds:
        logger.warning(
            "[payments] Stripe sig timestamp fora da tolerância: ts=%s now=%s",
            ts_int, int(now),
        )
        return False

    # Compute HMAC esperado
    signed_payload = f"{ts_int}.".encode("utf-8") + raw_payload
    expected = hmac.new(
        secret.encode("utf-8"),
        msg=signed_payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Compara contra cada v1 (qualquer válido aceita)
    for sig in v1_signatures:
        if hmac.compare_digest(expected, sig):
            return True

    return False

"""
Pix provider abstraction (Frente 7.1).

V1: Mercado Pago direto via REST API.
V2: Asaas, Pagar.me adapters com mesma interface.

Use case: tenant configura access_token MP em TenantFlowSecret. Endpoint
POST /api/payments/pix cria QR code dinâmico, retorna {qr_image, qr_text, expires_at}.

O webhook consulta o pagamento na API antes de aceitar qualquer mudança de status.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests


logger = logging.getLogger(__name__)


class PixProviderError(Exception):
    pass


class PixResult:
    """Resultado de criação de pagamento Pix."""
    def __init__(
        self,
        provider_payment_id: str,
        qr_code_text: str,
        qr_code_image_url: Optional[str],
        expires_at: datetime,
        amount_brl_cents: int,
        raw: dict,
    ):
        self.provider_payment_id = provider_payment_id
        self.qr_code_text = qr_code_text
        self.qr_code_image_url = qr_code_image_url
        self.expires_at = expires_at
        self.amount_brl_cents = amount_brl_cents
        self.raw = raw


# ─── Mercado Pago adapter ──────────────────────────────────────────────


_MP_API_BASE = "https://api.mercadopago.com"


def _mp_token(tenant_id: str) -> Optional[str]:
    """
    Resolve access_token Mercado Pago do tenant.
    Lê de tenant_flow_secrets primeiro, fallback env var MP_ACCESS_TOKEN (dev).
    """
    try:
        from db.database import SessionLocal
        from db import models
        db = SessionLocal()
        try:
            row = db.query(models.TenantFlowSecret).filter_by(
                tenant_id=tenant_id, key="mercadopago.access_token",
            ).first()
            if row and row.value_cipher:
                from api.utils.tenant_secrets import decrypt_tenant_secret
                return decrypt_tenant_secret(row.value_cipher, allow_plaintext_legacy=True)
        finally:
            db.close()
    except Exception:
        pass
    return os.getenv("MP_ACCESS_TOKEN")


def create_pix_mercadopago(
    *,
    tenant_id: str,
    amount_brl: float,
    description: str,
    expires_min: int = 30,
    payer_email: Optional[str] = None,
    external_reference: Optional[str] = None,
) -> PixResult:
    """
    Cria Pix dinâmico via Mercado Pago Payments API.

    Docs: https://www.mercadopago.com.br/developers/pt/reference/payments/_payments/post

    Returns PixResult ou raises PixProviderError.
    """
    token = _mp_token(tenant_id)
    if not token:
        raise PixProviderError("Mercado Pago access_token não configurado pra este tenant")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_min)
    payload = {
        "transaction_amount": round(float(amount_brl), 2),
        "description": (description or "Pagamento")[:200],
        "payment_method_id": "pix",
        "date_of_expiration": expires_at.isoformat(),
    }
    if payer_email:
        payload["payer"] = {"email": payer_email}
    if external_reference:
        payload["external_reference"] = external_reference[:128]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": f"meumisterio-{tenant_id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
    }

    try:
        resp = requests.post(
            f"{_MP_API_BASE}/v1/payments",
            json=payload,
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise PixProviderError(f"Falha de rede com Mercado Pago: {exc}")

    if resp.status_code >= 400:
        logger.warning("[pix.mp] erro %s: %s", resp.status_code, resp.text[:500])
        raise PixProviderError(f"Mercado Pago retornou {resp.status_code}: {resp.text[:200]}")

    data = resp.json() or {}

    # Pix data está em data["point_of_interaction"]["transaction_data"]
    poi = data.get("point_of_interaction") or {}
    tx_data = poi.get("transaction_data") or {}
    qr_text = tx_data.get("qr_code") or ""
    qr_b64 = tx_data.get("qr_code_base64") or ""
    qr_image_url = f"data:image/png;base64,{qr_b64}" if qr_b64 else None

    return PixResult(
        provider_payment_id=str(data.get("id") or ""),
        qr_code_text=qr_text,
        qr_code_image_url=qr_image_url,
        expires_at=expires_at,
        amount_brl_cents=int(round(float(amount_brl) * 100)),
        raw=data,
    )


def get_payment_status_mercadopago(
    *,
    tenant_id: str,
    provider_payment_id: str,
) -> str:
    """
    Consulta status de um payment. Retorna status MP (approved|pending|cancelled|...).
    """
    token = _mp_token(tenant_id)
    if not token:
        return "unknown"

    try:
        resp = requests.get(
            f"{_MP_API_BASE}/v1/payments/{provider_payment_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return "unknown"
        return (resp.json() or {}).get("status") or "unknown"
    except Exception as exc:
        logger.warning("[pix.mp.status] falha: %s", exc)
        return "unknown"

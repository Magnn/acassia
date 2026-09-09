"""
Idempotência durável de webhooks de pagamento (Stripe + Cakto).

`claim_payment_event` retorna True na PRIMEIRA vez que (provider, event_id,
tenant) é visto, e False em todas as subsequentes. Tudo persistido em DB
via :class:`db.models.PaymentEventReceipt` — sobrevive a restart do processo.

A garantia atômica vem do ``UniqueConstraint(tenant_id, provider, event_id)``:
sob concorrência, a 2ª inserção lança ``IntegrityError``, que tratamos como
"alguém já reivindicou" — sem race condition.
"""

import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def claim_payment_event(
    provider: str,
    event_id: str,
    tenant_id: str = "default",
    event_type: Optional[str] = None,
    raw_payload: Optional[dict] = None,
    lead_id: Optional[int] = None,
) -> bool:
    """
    Reivindica o processamento deste evento.

    Returns:
        True na primeira reivindicação (chamador deve processar)
        False se já foi reivindicado antes (chamador deve ignorar)

    Raises:
        ValueError: se ``provider`` ou ``event_id`` vierem vazios.
    """
    if not provider or not event_id:
        raise ValueError("provider e event_id são obrigatórios")

    db = SessionLocal()
    try:
        receipt = models.PaymentEventReceipt(
            tenant_id=tenant_id,
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            lead_id=lead_id,
            raw_payload=raw_payload or {},
        )
        db.add(receipt)
        db.commit()
        logger.info(
            "[payments] claim provider=%s event_id=%s tenant=%s",
            provider, event_id, tenant_id,
        )
        return True
    except IntegrityError:
        db.rollback()
        logger.info(
            "[payments] duplicate ignored provider=%s event_id=%s tenant=%s",
            provider, event_id, tenant_id,
        )
        return False
    finally:
        db.close()


def release_payment_event(provider: str, event_id: str, tenant_id: str = "default") -> None:
    """Libera uma claim quando o evento não chegou à fila durável."""
    db = SessionLocal()
    try:
        db.query(models.PaymentEventReceipt).filter_by(
            tenant_id=tenant_id, provider=provider, event_id=event_id
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

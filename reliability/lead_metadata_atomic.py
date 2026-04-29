"""
Atualização atômica de `leads.metadata_json` com `metadata_version` (merge otimista).

Evita lost update quando o turno do motor e a thread de envio gravam metadata quase ao mesmo tempo.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from db.models import Lead

logger = logging.getLogger(__name__)

PatchFn = Callable[[Dict[str, Any]], Dict[str, Any]]


def atomic_patch_metadata_json(
    db: Session,
    lead_id: int,
    patch_fn: PatchFn,
    *,
    max_retries: int = 5,
    audit_fn: Optional[Callable[[int, int], None]] = None,
) -> bool:
    """
    Lê metadata atual, aplica patch_fn(old) -> new_meta, grava só se metadata_version bater.

    audit_fn(lead_id, attempt_index) opcional (ex.: EventoAudit).
    """
    for attempt in range(max_retries):
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return False
        v = int(getattr(lead, "metadata_version", 0) or 0)
        old = dict(lead.metadata_json or {})
        try:
            new_meta = patch_fn(old)
        except Exception as e:
            logger.error("event=atomic_patch_metadata_fn_err lead_id=%s err=%s", lead_id, e, exc_info=True)
            return False
        if not isinstance(new_meta, dict):
            new_meta = dict(old)

        n = (
            db.query(Lead)
            .filter(Lead.id == lead_id, Lead.metadata_version == v)
            .update(
                {"metadata_json": new_meta, "metadata_version": v + 1},
                synchronize_session=False,
            )
        )
        if n:
            try:
                db.commit()
            except Exception:
                db.rollback()
                continue
            return True
        db.rollback()
        if audit_fn:
            try:
                audit_fn(lead_id, attempt)
            except Exception:
                pass
        logger.info(
            "event=lead_metadata_version_retry lead_id=%s attempt=%s/%s",
            lead_id,
            attempt + 1,
            max_retries,
        )
    logger.warning("event=lead_metadata_atomic_exhausted lead_id=%s", lead_id)
    return False


def atomic_update_lead_columns(
    db: Session,
    lead_id: int,
    build_patch: Callable[[Lead], Optional[Dict[str, Any]]],
    *,
    max_retries: int = 5,
) -> bool:
    """
    Atualização condicional de várias colunas de `Lead` na mesma linha que `metadata_version`.

    `build_patch(lead)` retorna dict com atributos mapeados (ex.: `Lead.metadata_json`) —
    **sem** incluir `metadata_version` (o helper soma +1).

    Retorna False se esgotar retries (caller pode fazer fallback commit simples).
    """
    for attempt in range(max_retries):
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return False
        v = int(getattr(lead, "metadata_version", 0) or 0)
        patch = build_patch(lead)
        if patch is None:
            return True
        if not patch:
            return True
        patch = dict(patch)
        patch["metadata_version"] = v + 1
        try:
            n = (
                db.query(Lead)
                .filter(Lead.id == lead_id, Lead.metadata_version == v)
                .update(patch, synchronize_session=False)
            )
        except Exception as e:
            logger.warning("event=atomic_update_lead_columns_exc lead_id=%s err=%s", lead_id, e)
            db.rollback()
            continue
        if n:
            try:
                db.commit()
            except Exception:
                db.rollback()
                continue
            return True
        db.rollback()
        logger.info(
            "event=lead_full_row_version_retry lead_id=%s attempt=%s/%s",
            lead_id,
            attempt + 1,
            max_retries,
        )
    logger.warning("event=lead_full_row_atomic_exhausted lead_id=%s", lead_id)
    return False

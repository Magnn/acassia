"""
Runtime do Studio AcassIA: snapshot publicado injetado no motor (engine → personalizer).
Escopado por tenant_id (uma publicação ativa por conta).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def ensure_publish_row(db, tenant_id: str = "default") -> models.StudioPublish:
    """Garante uma linha studio_publish por tenant."""
    tid = (tenant_id or "default").strip() or "default"
    row = db.query(models.StudioPublish).filter_by(tenant_id=tid).first()
    if row is None:
        row = models.StudioPublish(tenant_id=tid, published_version_id=None)
        db.add(row)
        db.flush()
    return row


def load_published_studio_snapshot(tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retorna dict para metadata['__meumisterio_studio__'] ou None se nada publicado.
    """
    tid = (tenant_id or "default").strip() or "default"
    db = SessionLocal()
    try:
        pub = db.query(models.StudioPublish).filter_by(tenant_id=tid).first()
        if not pub or not pub.published_version_id:
            return None
        ver = (
            db.query(models.StudioAgentVersion)
            .filter_by(id=pub.published_version_id)
            .first()
        )
        if not ver:
            return None
        agent = db.query(models.StudioAgent).filter_by(id=ver.agent_id).first()
        if not agent:
            return None
        if str(getattr(agent, "tenant_id", "default") or "default") != tid:
            return None
        body = ver.body_json if isinstance(ver.body_json, dict) else {}
        return {
            "agent_id": agent.id,
            "agent_name": agent.name or "",
            "version_id": ver.id,
            "version_number": int(ver.version_number or 0),
            "data": body,
        }
    except Exception as e:
        logger.warning("⚠️ [STUDIO] Falha ao carregar snapshot publicado: %s", e)
        return None
    finally:
        db.close()


def inject_published_studio_into_metadata(metadata: Optional[dict], tenant_id: Optional[str] = None) -> None:
    """Anexa __meumisterio_studio__ ao metadata do contexto (motor / recuperação / webhook)."""
    if not isinstance(metadata, dict):
        return
    snap = load_published_studio_snapshot(tenant_id)
    if snap:
        metadata["__meumisterio_studio__"] = snap

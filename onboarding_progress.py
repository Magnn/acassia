"""
Onboarding gamificado — milestones de ativação (Frente 5.1).

Milestones detectados automaticamente em hot paths:
    persona_created       — agente criado (Studio)
    whatsapp_connected    — conexão WA ativa
    first_flow_published  — fluxo publicado
    first_message_sent    — bot mandou 1ª msg pra lead real
    first_lead_captured   — primeiro lead na inbox
    first_sale            — primeira PaymentEventReceipt
    invited_member        — primeiro convite de team

Helpers:
    mark_milestone(user_id, key, metadata?) — idempotente
    list_milestones(user_id) — todas + computed status
    progress(user_id) — % completado + next suggested
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


MILESTONES = [
    {
        "key": "persona_created",
        "label": "Persona criada",
        "description": "Você criou seu primeiro atendente IA",
        "order": 1,
    },
    {
        "key": "whatsapp_connected",
        "label": "WhatsApp conectado",
        "description": "Seu número WhatsApp está pronto pra receber leads",
        "order": 2,
    },
    {
        "key": "first_flow_published",
        "label": "Primeiro fluxo publicado",
        "description": "Seu funil está vivo e pronto pra atender",
        "order": 3,
    },
    {
        "key": "first_message_sent",
        "label": "Primeira mensagem enviada",
        "description": "Bot já está conversando com leads",
        "order": 4,
    },
    {
        "key": "first_lead_captured",
        "label": "Primeiro lead capturado",
        "description": "Alguém entrou na sua jornada",
        "order": 5,
    },
    {
        "key": "first_sale",
        "label": "Primeira venda",
        "description": "🎉 Conversão confirmada — você ganhou dinheiro",
        "order": 6,
    },
    {
        "key": "invited_member",
        "label": "Convidou um membro",
        "description": "Você está escalando o atendimento (opcional)",
        "order": 7,
    },
]

MILESTONE_BY_KEY = {m["key"]: m for m in MILESTONES}


def mark_milestone(
    user_id: int,
    milestone_key: str,
    *,
    metadata: Optional[dict] = None,
    db_session=None,
) -> bool:
    """
    Marca milestone como completo. Idempotente — se já existe, retorna False.
    Returns True se foi a primeira vez (ou seja, deve disparar UI confete).
    """
    if milestone_key not in MILESTONE_BY_KEY:
        logger.warning("[onboarding] milestone_key inválido: %s", milestone_key)
        return False

    own = db_session is None
    db = db_session or SessionLocal()
    try:
        existing = db.query(models.OnboardingMilestone).filter_by(
            user_id=user_id, milestone_key=milestone_key,
        ).first()
        if existing:
            return False
        ms = models.OnboardingMilestone(
            user_id=user_id,
            milestone_key=milestone_key,
            metadata_json=metadata,
        )
        db.add(ms)
        db.commit()
        logger.info("[onboarding.milestone_completed] user=%s key=%s", user_id, milestone_key)
        return True
    finally:
        if own:
            db.close()


def list_milestones(user_id: int) -> list[dict]:
    """Retorna lista de milestones com flag completed."""
    db = SessionLocal()
    try:
        completed_keys = set(
            row.milestone_key for row in
            db.query(models.OnboardingMilestone).filter_by(user_id=user_id).all()
        )
        out = []
        for m in MILESTONES:
            done = m["key"] in completed_keys
            out.append({
                **m,
                "completed": done,
            })
        return out
    finally:
        db.close()


def progress(user_id: int) -> dict:
    """
    Retorna progresso completo:
        {milestones: [...], total, completed_count, pct, next_suggested?}
    """
    items = list_milestones(user_id)
    completed = [m for m in items if m["completed"]]
    pct = round(len(completed) / len(items) * 100) if items else 0
    next_suggested = next((m for m in items if not m["completed"]), None)
    return {
        "milestones": items,
        "total": len(items),
        "completed_count": len(completed),
        "pct": pct,
        "next_suggested": {
            "key": next_suggested["key"],
            "label": next_suggested["label"],
            "description": next_suggested["description"],
        } if next_suggested else None,
        "all_done": pct == 100,
    }


# ─── Auto-detect helpers (chamáveis de hot paths) ─────────────────────


def auto_detect_for_tenant(tenant_id: str, db_session=None) -> int:
    """
    Detecta milestones automaticamente checando estado do tenant.
    Útil pra rodar em batch ou após eventos chave.
    Retorna número de milestones marcados.
    """
    own = db_session is None
    db = db_session or SessionLocal()
    marked = 0
    try:
        user = db.query(models.User).filter_by(tenant_id=tenant_id).first()
        if not user:
            return 0
        uid = user.id

        # persona_created — tem StudioAgent
        if db.query(models.StudioAgent).filter_by(tenant_id=tenant_id).first():
            if mark_milestone(uid, "persona_created", db_session=db):
                marked += 1

        # whatsapp_connected — TenantFlowVariable whatsapp.provider
        kv = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key="whatsapp.provider",
        ).first()
        if kv and kv.value_json:
            if mark_milestone(uid, "whatsapp_connected", db_session=db):
                marked += 1

        # first_flow_published — FlowPublish com published_blueprint_id != null
        pub = db.query(models.FlowPublish).filter_by(tenant_id=tenant_id).first()
        if pub and pub.published_blueprint_id:
            if mark_milestone(uid, "first_flow_published", db_session=db):
                marked += 1

        # first_message_sent — Mensagem.remetente=bot existe
        bot_msg = db.query(models.Mensagem).join(
            models.Lead, models.Mensagem.lead_id == models.Lead.id,
        ).filter(
            models.Lead.tenant_id == tenant_id,
            models.Mensagem.remetente == "bot",
        ).first()
        if bot_msg:
            if mark_milestone(uid, "first_message_sent", db_session=db):
                marked += 1

        # first_lead_captured — qualquer Lead
        lead = db.query(models.Lead).filter_by(tenant_id=tenant_id).first()
        if lead:
            if mark_milestone(uid, "first_lead_captured", db_session=db):
                marked += 1

        # first_sale — qualquer PaymentEventReceipt
        pmt = db.query(models.PaymentEventReceipt).filter_by(tenant_id=tenant_id).first()
        if pmt:
            if mark_milestone(uid, "first_sale", db_session=db):
                marked += 1

        return marked
    finally:
        if own:
            db.close()

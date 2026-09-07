"""
Tiragem agendada (Frente 4.28).

Funcoes:
    schedule_for_lead(lead_id, trigger_type, spread, question?, when?)
    cancel_scheduled(reading_id)
    process_due_readings()  ← cron horario
        - Marca warning_sent quando faltam <= 60min
        - Roda tiragem + envia leitura quando scheduled_for <= now

Triggers suportados:
    lunar_full      — proxima lua cheia (calculada via lunar.py)
    lunar_new       — proxima lua nova
    date_specific   — when (datetime) explicito
    sign_transit    — V2

A tiragem usa o pipeline existente do api/saas/tarot.py:
  - Random sample com seed deterministico
  - Persiste TarotReading + interpretacao Gemini
  - Envia mensagem via WhatsApp formato=texto
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


# ─── Resolver scheduled_for por trigger_type ──────────────────────────


def _next_lunar(target_phase: str, after: datetime | None = None) -> datetime:
    """Proxima lua-fase apos `after` (default agora)."""
    after = after or datetime.now(timezone.utc)
    try:
        import lunar
        return lunar.next_phase(target_phase, from_date=after)
    except Exception as exc:
        logger.warning("[scheduled_readings.next_lunar] falha %s: %s", target_phase, exc)
        # Fallback: chuta 14 dias adiante
        return after + timedelta(days=14)


def resolve_scheduled_for(
    trigger_type: str,
    when: Optional[datetime] = None,
) -> datetime:
    """
    Resolve scheduled_for absoluto pra cada trigger_type.
    Levanta ValueError se trigger_type invalido ou when faltando pra
    date_specific.
    """
    trigger_type = (trigger_type or "").strip().lower()
    if trigger_type == "lunar_full":
        return _next_lunar("cheia")
    if trigger_type == "lunar_new":
        return _next_lunar("nova")
    if trigger_type == "date_specific":
        if when is None:
            raise ValueError("date_specific requer when")
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return when
    raise ValueError(f"trigger_type invalido: {trigger_type}")


# ─── Public API ────────────────────────────────────────────────────────


def schedule_for_lead(
    *,
    tenant_id: str,
    lead_id: int,
    trigger_type: str,
    spread_type: str = "3card",
    deck_id: str = "marselha",
    question: Optional[str] = None,
    when: Optional[datetime] = None,
    db_session=None,
) -> models.ScheduledReading:
    """
    Cria ScheduledReading. Levanta ValueError se trigger_type invalido.
    """
    scheduled_for = resolve_scheduled_for(trigger_type, when)

    own = db_session is None
    db = db_session or SessionLocal()
    try:
        # Garantir lead pertence ao tenant
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=tenant_id,
        ).first()
        if not lead:
            raise ValueError("lead_not_found_for_tenant")

        sr = models.ScheduledReading(
            tenant_id=tenant_id,
            lead_id=lead_id,
            scheduled_for=scheduled_for,
            trigger_type=trigger_type,
            spread_type=spread_type,
            deck_id=deck_id,
            question=(question or "").strip()[:500] or None,
            status="pending",
        )
        db.add(sr)
        db.commit()
        db.refresh(sr)

        try:
            db.add(models.AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=None,
                event_type="scheduled_reading.created",
                target_type="scheduled_reading",
                target_id=str(sr.id),
                payload={
                    "lead_id": lead_id,
                    "trigger_type": trigger_type,
                    "scheduled_for": scheduled_for.isoformat(),
                },
            ))
            db.commit()
        except Exception:
            db.rollback()

        return sr
    finally:
        if own:
            db.close()


def cancel_scheduled(reading_id: int, *, tenant_id: str, db_session=None) -> bool:
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        sr = db.query(models.ScheduledReading).filter_by(
            id=reading_id, tenant_id=tenant_id,
        ).first()
        if not sr:
            return False
        if sr.status in ("completed", "cancelled"):
            return False
        sr.status = "cancelled"
        sr.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
    finally:
        if own:
            db.close()


# ─── Cron processor ───────────────────────────────────────────────────


def _send_warning(sr: models.ScheduledReading, lead: models.Lead) -> bool:
    """Envia "preparando sua tiragem..." 1h antes."""
    text = (
        f"✦ Já estou preparando sua tiragem para daqui a pouco. "
        f"Vou puxar as cartas em momento certo e te conto o que elas trazem."
    )
    try:
        from api.whatsapp_api import whatsapp_client
        return bool(whatsapp_client.enviar_mensagem(lead.telefone, text, formato="texto"))
    except Exception as exc:
        logger.warning("[scheduled_readings.warning] falha: %s", exc)
        return False


def _execute_reading(sr: models.ScheduledReading, lead: models.Lead, db) -> bool:
    """
    Roda tiragem + persiste TarotReading + envia leitura via WhatsApp.
    Retorna True se enviou ok.
    """
    import hashlib
    import random as _random

    SPREADS = {
        "1card": ["mensagem"],
        "3card": ["passado", "presente", "futuro"],
        "cross5": ["situação", "obstáculo", "passado", "presente", "futuro"],
        "celtic10": [
            "presente", "obstáculo", "consciente", "subconsciente",
            "passado", "futuro", "você", "ambiente", "esperanças", "resultado",
        ],
    }
    positions = SPREADS.get(sr.spread_type, SPREADS["3card"])
    n_cards = len(positions)

    cards = db.query(models.TarotCard).filter_by(deck_id=sr.deck_id).all()
    if len(cards) < n_cards:
        logger.warning(
            "[scheduled_readings.execute] deck=%s tem %s cartas, precisa %s",
            sr.deck_id, len(cards), n_cards,
        )
        return False

    # Seed deterministico baseado em scheduled_for + lead — reproduzivel
    seed_str = f"sched_{sr.id}_{lead.id}_{sr.scheduled_for.isoformat()}"
    seed_int = int(hashlib.sha256(seed_str.encode()).hexdigest()[:16], 16)
    rng = _random.Random(seed_int)

    chosen = rng.sample(cards, n_cards)
    cards_data = []
    for i, card in enumerate(chosen):
        reversed_ = rng.random() < 0.3
        cards_data.append({
            "position": positions[i],
            "card_id": card.id,
            "name": card.name,
            "arcana": card.arcana,
            "reversed": reversed_,
            "meaning": card.meaning_reversed if reversed_ else card.meaning_upright,
            "keywords": card.keywords,
        })

    # Interpretacao via Gemini — reusa helper de api/saas/tarot.py
    interpretation = None
    try:
        from api.saas.tarot import _generate_interpretation
        interpretation = _generate_interpretation(
            cards_data, sr.question or "", sr.spread_type,
        )
    except Exception as exc:
        logger.warning("[scheduled_readings.execute] interp falhou: %s", exc)

    # Persiste TarotReading
    reading = models.TarotReading(
        tenant_id=sr.tenant_id,
        lead_id=lead.id,
        attended_by_user_id=None,
        spread_type=sr.spread_type,
        deck_id=sr.deck_id,
        cards=cards_data,
        question=sr.question,
        interpretation=interpretation,
    )
    db.add(reading)
    db.flush()

    # Monta mensagem outbound
    cards_block = "\n".join([
        f"• {c['position'].capitalize()}: {c['name']}"
        f"{' (invertida)' if c['reversed'] else ''}"
        for c in cards_data
    ])
    spread_name = {
        "1card": "Carta do dia",
        "3card": "Passado, Presente e Futuro",
        "cross5": "Cruz simples",
        "celtic10": "Cruz Celta",
    }.get(sr.spread_type, sr.spread_type)

    intro_lines = [f"✦ Sua tiragem agendada chegou — {spread_name}"]
    if sr.question:
        intro_lines.append(f"Pergunta: {sr.question}")
    intro = "\n".join(intro_lines)

    body = f"{intro}\n\n{cards_block}"
    if interpretation:
        body += f"\n\n{interpretation}"

    try:
        from api.whatsapp_api import whatsapp_client
        ok = bool(whatsapp_client.enviar_mensagem(lead.telefone, body, formato="texto"))
    except Exception as exc:
        logger.warning("[scheduled_readings.execute] envio falhou: %s", exc)
        ok = False

    if ok:
        reading.sent_to_lead = True
        reading.sent_at = datetime.now(timezone.utc)
        sr.reading_id = reading.id
        sr.status = "completed"
        sr.completed_at = datetime.now(timezone.utc)
    else:
        sr.status = "failed"
        sr.error_message = "send_failed"

    db.commit()
    return ok


def process_due_readings() -> dict:
    """
    Processa vencidos:
      - status=pending + scheduled_for-1h <= now < scheduled_for: envia warning
      - status=pending + scheduled_for <= now: roda tiragem
      - status=warning_sent + scheduled_for <= now: roda tiragem

    Retorna stats {warnings_sent, completed, failed, errors}.
    """
    db = SessionLocal()
    stats = {"warnings_sent": 0, "completed": 0, "failed": 0, "errors": 0}
    now = datetime.now(timezone.utc)
    cutoff_warning = now + timedelta(hours=1)

    try:
        # Warning candidates: pending dentro de 1h
        warning_candidates = db.query(models.ScheduledReading).filter(
            models.ScheduledReading.status == "pending",
            models.ScheduledReading.scheduled_for > now,
            models.ScheduledReading.scheduled_for <= cutoff_warning,
            models.ScheduledReading.warning_sent_at.is_(None),
        ).all()

        for sr in warning_candidates:
            try:
                lead = db.query(models.Lead).filter_by(id=sr.lead_id).first()
                if not lead or lead.opt_out:
                    sr.status = "cancelled"
                    sr.error_message = "lead_opted_out_or_missing"
                    db.commit()
                    continue

                # Tenant context para envio
                try:
                    from tenant_context import tenant_override_ctx
                    with tenant_override_ctx(sr.tenant_id):
                        ok = _send_warning(sr, lead)
                except Exception:
                    ok = _send_warning(sr, lead)

                if ok:
                    sr.warning_sent_at = now
                    sr.status = "warning_sent"
                    db.commit()
                    stats["warnings_sent"] += 1
            except Exception as exc:
                logger.exception("[scheduled_readings.warning] erro: %s", exc)
                stats["errors"] += 1

        # Execution candidates: pending+warning_sent vencidos
        exec_candidates = db.query(models.ScheduledReading).filter(
            models.ScheduledReading.status.in_(["pending", "warning_sent"]),
            models.ScheduledReading.scheduled_for <= now,
        ).all()

        for sr in exec_candidates:
            try:
                lead = db.query(models.Lead).filter_by(id=sr.lead_id).first()
                if not lead or lead.opt_out:
                    sr.status = "cancelled"
                    sr.error_message = "lead_opted_out_or_missing"
                    db.commit()
                    continue

                try:
                    from tenant_context import tenant_override_ctx
                    with tenant_override_ctx(sr.tenant_id):
                        ok = _execute_reading(sr, lead, db)
                except Exception:
                    ok = _execute_reading(sr, lead, db)

                if ok:
                    stats["completed"] += 1
                else:
                    stats["failed"] += 1
            except Exception as exc:
                logger.exception("[scheduled_readings.execute] erro: %s", exc)
                stats["errors"] += 1
                try:
                    sr.status = "failed"
                    sr.error_message = str(exc)[:500]
                    db.commit()
                except Exception:
                    db.rollback()

        return stats
    finally:
        db.close()

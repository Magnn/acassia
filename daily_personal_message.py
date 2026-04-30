"""
Mensagem do dia personalizada por lead (Frente 4.27).

Difere do horoscopo (Frente 4.13) que e por signo: aqui cada lead recebe
um insight unico, com contexto:
    - Nome
    - Signo + fase lunar + elemento dominante
    - Ultima intencao (amor/dinheiro/saude/...)
    - Tom suave/poetico

Cron horario verifica todos tenants com daily_message.enabled=true e
processa leads com consents.daily_personal_message=true cuja hora local
casa com daily_message.hour_local.

Idempotencia: tabela DailyPersonalMessage com unique (tenant, lead, date).
"""

from __future__ import annotations

import logging
import os
from datetime import date as DateT, datetime, timezone
from typing import Optional

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


_FALLBACK_TEMPLATES = [
    "Hoje, {nome}, a energia pede que voce confie nos sinais pequenos.",
    "{nome}, sinto que algo bonito esta sendo preparado pra voce.",
    "Respire fundo, {nome}. O que parece atraso tem proposito.",
    "Confie no seu intuito hoje, {nome} — ele esta especialmente forte.",
    "{nome}, seu signo de {signo} brilha hoje em silencio. Observe o que vem.",
]


def _fallback_for_lead(lead) -> str:
    import random
    nome = (lead.nome or "querida").split()[0]
    signo = (lead.signo or "luz").lower()
    template = random.choice(_FALLBACK_TEMPLATES)
    return template.format(nome=nome, signo=signo)


def _gemini_for_lead(lead) -> Optional[str]:
    """Gera texto via Gemini com contexto rico. Retorna None em qualquer falha."""
    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            return None

        first_name = (lead.nome or "").split()[0] if lead.nome else "querida"
        signo = lead.signo or None

        moon_phase = None
        try:
            import lunar
            phase_info = lunar.phase_for_date()
            moon_phase = (phase_info.get("phase_name") or "").lower()
        except Exception:
            pass

        ctx_bits: list[str] = []
        if signo:
            ctx_bits.append(f"signo de {signo}")
        if moon_phase:
            ctx_bits.append(f"lua {moon_phase}")
        if lead.ultima_intencao:
            ctx_bits.append(f"intencao recente: {lead.ultima_intencao}")
        if lead.spiritual_category:
            ctx_bits.append(f"tema dominante: {lead.spiritual_category}")
        ctx_str = ", ".join(ctx_bits) or "(sem contexto extra)"

        prompt = (
            "Voce e cigana mistica, falando direto e curto no WhatsApp. "
            "Crie a 'mensagem do dia' personalizada para esta pessoa. "
            "Maximo 220 caracteres. Tom acolhedor, poetico, em pt-BR. "
            "Use o primeiro nome dela. Nao seja generico — referencie o "
            "contexto fornecido. Nao use emoji. Nao termine com pergunta.\n\n"
            f"Nome: {first_name}\n"
            f"Contexto: {ctx_str}\n\n"
            "Apenas a mensagem em si, sem explicacao."
        )
        resp = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 200, "temperature": 0.95},
        )
        text = (resp.text or "").strip().strip('"\'')
        if not text:
            return None
        return text[:280]
    except Exception as exc:
        logger.warning("[daily_personal_message.gemini] falha: %s", exc)
        return None


def generate_for_lead(lead, *, target_date: DateT | None = None,
                      db_session=None) -> models.DailyPersonalMessage:
    """
    Gera (ou retorna existente) mensagem do dia para o lead.
    Idempotente por (tenant, lead, date).
    """
    target_date = target_date or DateT.today()
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        existing = db.query(models.DailyPersonalMessage).filter_by(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            date=target_date,
        ).first()
        if existing:
            return existing

        text = _gemini_for_lead(lead)
        source = "gemini"
        if not text:
            text = _fallback_for_lead(lead)
            source = "fallback"

        msg = models.DailyPersonalMessage(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            date=target_date,
            text=text,
            source=source,
            chars_count=len(text),
            status="generated",
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg
    finally:
        if own:
            db.close()


def send_to_lead(message_row: models.DailyPersonalMessage,
                 lead: models.Lead,
                 db_session) -> bool:
    """Envia a msg via WhatsApp + atualiza status. Retorna True se ok."""
    try:
        from api.whatsapp_api import whatsapp_client
        ok = whatsapp_client.enviar_mensagem(
            lead.telefone, message_row.text, formato="texto",
        )
    except Exception as exc:
        logger.warning("[daily_personal_message.send] falha: %s", exc)
        message_row.status = "failed"
        message_row.error_message = str(exc)[:500]
        db_session.commit()
        return False

    if ok:
        message_row.status = "sent"
        message_row.sent_at = datetime.now(timezone.utc)
        # Persist no historico
        try:
            db_session.add(models.Mensagem(
                lead_id=lead.id,
                remetente="bot",
                texto=message_row.text,
                tipo="text",
            ))
        except Exception:
            pass
        db_session.commit()
        return True

    message_row.status = "failed"
    message_row.error_message = "send_returned_false"
    db_session.commit()
    return False


def fanout_for_tenant(tenant_id: str, target_date: DateT | None = None,
                      *, dry_run: bool = False) -> dict:
    """
    Gera + envia mensagem do dia pros leads opt-in do tenant.

    Filtro: consents.daily_personal_message=True, opt_out=False,
    bot_pausado=False (mesmas guardas do horoscopo).
    """
    target_date = target_date or DateT.today()
    db = SessionLocal()
    stats = {
        "sent": 0, "failed": 0, "skipped": 0, "opted_out": 0,
        "generated": 0, "skipped_existing": 0,
    }
    try:
        # Tenant config check
        try:
            from api.tenant_config import get_tenant_config
            cfg = get_tenant_config(tenant_id)
            dm_cfg = (cfg.get("daily_message") or {}) if isinstance(cfg, dict) else {}
            if not dm_cfg.get("enabled"):
                return {**stats, "reason": "disabled"}
        except Exception:
            return {**stats, "reason": "config_error"}

        leads = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.opt_out == False,  # noqa: E712
            models.Lead.bot_pausado == False,  # noqa: E712
        ).all()

        for lead in leads:
            consents = lead.consents or {}
            if consents.get("daily_personal_message") is not True:
                stats["opted_out"] += 1
                continue

            existing = db.query(models.DailyPersonalMessage).filter_by(
                tenant_id=tenant_id, lead_id=lead.id, date=target_date,
            ).first()
            if existing and existing.status == "sent":
                stats["skipped_existing"] += 1
                continue

            try:
                msg = existing if existing else generate_for_lead(
                    lead, target_date=target_date, db_session=db,
                )
                if not existing:
                    stats["generated"] += 1
            except Exception as exc:
                logger.warning("[dpm.fanout] gen falhou lead=%s: %s", lead.id, exc)
                stats["failed"] += 1
                continue

            if dry_run:
                stats["sent"] += 1
                continue

            ok = send_to_lead(msg, lead, db)
            if ok:
                stats["sent"] += 1
            else:
                stats["failed"] += 1

        # Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=None,
                event_type="daily_personal_message.fanout",
                target_type="tenant",
                target_id=tenant_id,
                payload=stats,
            ))
            db.commit()
        except Exception:
            db.rollback()

        return stats
    finally:
        db.close()


def hourly_dispatch_due_tenants() -> int:
    """
    Cron: percorre tenants com daily_message.enabled e processa quando
    hora local bate. Retorna numero de tenants processados.
    """
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        return 0

    db = SessionLocal()
    processed = 0
    try:
        # Lista tenants com TenantFlowVariable daily_message.enabled = true
        rows = db.query(models.TenantFlowVariable).filter(
            models.TenantFlowVariable.key == "daily_message.enabled",
        ).all()
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()

        for row in rows:
            if not row.value_json:
                continue
            tenant_id = row.tenant_id
            try:
                from api.tenant_config import get_tenant_config
                cfg = get_tenant_config(tenant_id)
                dm = (cfg.get("daily_message") or {}) if isinstance(cfg, dict) else {}
                hour = int(dm.get("hour_local") or 8)
                tz_name = dm.get("timezone") or "America/Sao_Paulo"
                last_run = dm.get("last_run_date") or ""
                if last_run == today.isoformat():
                    continue
                try:
                    tz = ZoneInfo(tz_name)
                except Exception:
                    tz = ZoneInfo("America/Sao_Paulo")
                local_now = now_utc.astimezone(tz)
                if local_now.hour != hour:
                    continue

                stats = fanout_for_tenant(tenant_id, local_now.date())
                logger.info(
                    "[cron.daily_personal_message] tenant=%s sent=%d failed=%d",
                    tenant_id, stats.get("sent", 0), stats.get("failed", 0),
                )
                processed += 1

                # Marca last_run via TenantFlowVariable update
                try:
                    var_lr = db.query(models.TenantFlowVariable).filter_by(
                        tenant_id=tenant_id, key="daily_message.last_run_date",
                    ).first()
                    if var_lr:
                        var_lr.value_json = today.isoformat()
                    else:
                        db.add(models.TenantFlowVariable(
                            tenant_id=tenant_id,
                            key="daily_message.last_run_date",
                            value_json=today.isoformat(),
                        ))
                    db.commit()
                    try:
                        from api.tenant_config import clear_cache
                        clear_cache(tenant_id)
                    except Exception:
                        pass
                except Exception:
                    db.rollback()
            except Exception as exc:
                logger.warning("[cron.daily_personal_message] tenant=%s falha: %s",
                               tenant_id, exc)
                continue
        return processed
    finally:
        db.close()

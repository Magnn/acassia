"""
Cron jobs / scheduled background tasks.

Cada job é idempotente (pode rodar múltiplas vezes sem efeito colateral).
Recomendado rodar a cada hora via systemd timer ou cron host:

    # Hourly
    0 * * * * cd /opt/acassia && python -m cron_jobs hourly

    # Daily 2am UTC (off-peak)
    0 2 * * * cd /opt/acassia && python -m cron_jobs daily

Jobs:
    hourly_trial_warnings  — D-12, D-7, D-3, D-1 emails (Frente 2.19)
    hourly_quota_warnings  — 80%, 95%, 100% emails (Frente 2.11)
    daily_hard_delete      — soft-deleted > 30d → hard delete (Frente 1.9)
    daily_at_risk_signals  — gera tenant_health + at_risk_signals (Frente 1.15/1.16)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone, timedelta

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ─── Trial warnings (Frente 2.19) ─────────────────────────────────────


TRIAL_WARNING_DAYS = (12, 7, 3, 1)  # D-N antes do trial expirar


def hourly_trial_warnings():
    """
    Para cada user com trial ativo: identifica se está em D-N marker (12/7/3/1)
    e emite log estruturado. (Email transacional fica pra integração 7.25 Resend.)

    Idempotência: usa AuditEvent pra rastrear quais warnings já foram enviados.
    """
    db = SessionLocal()
    sent_count = 0
    expired_count = 0
    try:
        now = datetime.now(timezone.utc)
        # Trial ativo
        users = db.query(models.User).filter(
            models.User.trial_ends_at.isnot(None),
            models.User.is_active == True,  # noqa: E712
            models.User.deleted_at.is_(None),
        ).all()

        for user in users:
            trial_ends = _aware(user.trial_ends_at)
            if trial_ends is None:
                continue

            # Se já expirou: log evento expired (uma vez)
            if trial_ends < now:
                already = db.query(models.AuditEvent).filter(
                    models.AuditEvent.tenant_id == user.tenant_id,
                    models.AuditEvent.event_type == "trial.expired",
                ).first()
                if not already:
                    ev = models.AuditEvent(
                        tenant_id=user.tenant_id,
                        actor_user_id=None,
                        event_type="trial.expired",
                        target_type="user",
                        target_id=str(user.id),
                        payload={"trial_ended_at": trial_ends.isoformat()},
                    )
                    db.add(ev)
                    expired_count += 1
                continue

            # Quantos dias até expirar
            days_left = (trial_ends - now).days
            if days_left not in TRIAL_WARNING_DAYS:
                continue

            # Já enviou aviso pra esse marker?
            event_type = f"trial.warning_d{days_left}"
            already = db.query(models.AuditEvent).filter(
                models.AuditEvent.tenant_id == user.tenant_id,
                models.AuditEvent.event_type == event_type,
            ).first()
            if already:
                continue

            ev = models.AuditEvent(
                tenant_id=user.tenant_id,
                actor_user_id=None,
                event_type=event_type,
                target_type="user",
                target_id=str(user.id),
                payload={"days_left": days_left, "trial_ends_at": trial_ends.isoformat()},
            )
            db.add(ev)
            sent_count += 1
            logger.info(
                "[trial.warning] user=%s tenant=%s d-%d ends=%s",
                user.id, user.tenant_id, days_left, trial_ends.isoformat(),
            )
            # TODO Frente 7.25: send email via Resend

        if sent_count or expired_count:
            db.commit()
            logger.info(
                "[cron.hourly_trial_warnings] sent=%d expired_logged=%d",
                sent_count, expired_count,
            )
    finally:
        db.close()


# ─── Quota warnings (Frente 2.11) ─────────────────────────────────────


QUOTA_WARNING_THRESHOLDS = (80, 95, 100)


def hourly_quota_warnings():
    """
    Para cada (tenant, kind) com count > threshold, dispara warning 1x/mês/threshold.

    Idempotência: usa TenantUsageQuotaWarning como dedup table.
    """
    import plans as plans_module

    db = SessionLocal()
    sent_count = 0
    try:
        now = datetime.now(timezone.utc)
        yyyymm = now.year * 100 + now.month

        # Para cada tenant com counter ativo no período corrente
        counters = db.query(models.TenantUsageCounter).filter_by(
            period_yyyymm=yyyymm,
        ).all()

        for c in counters:
            limit = plans_module.effective_quota(c.tenant_id, c.kind, db_session=db)
            if limit == plans_module.UNLIMITED or limit <= 0:
                continue

            pct = (c.count / limit) * 100 if limit > 0 else 0

            for threshold in QUOTA_WARNING_THRESHOLDS:
                if pct < threshold:
                    continue
                # Já enviou esse threshold neste período?
                existing = db.query(models.TenantUsageQuotaWarning).filter_by(
                    tenant_id=c.tenant_id,
                    period_yyyymm=yyyymm,
                    kind=c.kind,
                    threshold_pct=threshold,
                ).first()
                if existing:
                    continue

                # Marca enviado
                db.add(models.TenantUsageQuotaWarning(
                    tenant_id=c.tenant_id,
                    period_yyyymm=yyyymm,
                    kind=c.kind,
                    threshold_pct=threshold,
                ))

                # Audit event
                db.add(models.AuditEvent(
                    tenant_id=c.tenant_id,
                    actor_user_id=None,
                    event_type=f"quota.warning_{threshold}pct",
                    target_type="quota",
                    target_id=c.kind,
                    payload={
                        "kind": c.kind, "count": c.count, "limit": limit,
                        "pct": round(pct, 2), "threshold": threshold,
                    },
                ))
                sent_count += 1
                logger.info(
                    "[quota.warning] tenant=%s kind=%s threshold=%d count=%d/%d (%.1f%%)",
                    c.tenant_id, c.kind, threshold, c.count, limit, pct,
                )
                # TODO Frente 7.25: send email + push notification

        if sent_count:
            db.commit()
            logger.info("[cron.hourly_quota_warnings] sent=%d", sent_count)
    finally:
        db.close()


# ─── Hard delete (Frente 1.9) ─────────────────────────────────────────


def daily_hard_delete():
    """
    Hard delete users soft-deleted há > 30 dias.
    CASCADE FK remove leads, mensagens, etc.

    Em prod: confirm via dry_run first; ativar só após teste manual.
    """
    db = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        targets = db.query(models.User).filter(
            models.User.deleted_at.isnot(None),
            models.User.deleted_at < cutoff,
        ).all()
        if not targets:
            return

        for u in targets:
            logger.warning(
                "[cron.daily_hard_delete] HARD DELETING user=%s tenant=%s deleted_at=%s",
                u.id, u.tenant_id, u.deleted_at,
            )
            # TODO: delete cascading data manualmente onde FK não tem ON DELETE CASCADE
            # Por enquanto, soft-delete protege; hard-delete fica como TODO V2

        # SAFETY: NÃO commit ainda — implementação real precisa de:
        # 1. Cancelar Stripe subscriptions ativas
        # 2. Limpar Redis queues do tenant
        # 3. Confirmar que CASCADE está em todas FKs (auditar via Alembic)
        # 4. Email final ao user
        # 5. Audit event hard_delete_executed
        logger.warning(
            "[cron.daily_hard_delete] DRY RUN — %d users seriam deletados, mas hard-delete está desabilitado V1",
            len(targets),
        )
    finally:
        db.close()


# ─── Tenant health score (Frente 1.15) ────────────────────────────────


def daily_recompute_tenant_health():
    """
    Recalcula health score pra todos tenants ativos.
    Score = peso(activity 40, result 30, billing 15, engagement 15) × 100.
    """
    db = SessionLocal()
    updated = 0
    try:
        users = db.query(models.User).filter(
            models.User.is_active == True,  # noqa: E712
            models.User.deleted_at.is_(None),
        ).all()

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        for u in users:
            # Activity (40%): last_login + msgs/week + leads/week
            last_login = _aware(u.last_login_at)
            login_score = 100 if last_login and last_login > week_ago else \
                (50 if last_login and last_login > now - timedelta(days=30) else 0)

            from sqlalchemy import func as sql_func
            msgs_7d = db.query(sql_func.count(models.Mensagem.id)).join(
                models.Lead, models.Mensagem.lead_id == models.Lead.id,
            ).filter(
                models.Lead.tenant_id == u.tenant_id,
                models.Mensagem.timestamp > week_ago,
            ).scalar() or 0
            msgs_score = min(100, msgs_7d * 5)  # 20+ msgs/7d = 100
            activity = (login_score + msgs_score) / 2

            # Result (30%): vendas + sentiment proxy
            sales_30d = db.query(sql_func.count(models.PaymentEventReceipt.id)).filter(
                models.PaymentEventReceipt.tenant_id == u.tenant_id,
                models.PaymentEventReceipt.processed_at > now - timedelta(days=30),
            ).scalar() or 0
            sales_score = min(100, sales_30d * 20)  # 5+ vendas/30d = 100
            result = sales_score

            # Billing (15%): plano pago, sem dunning
            billing = 100 if u.dunning_status is None else 30

            # Engagement (15%): proxy via leads totais (proxy weak)
            leads_total = db.query(sql_func.count(models.Lead.id)).filter(
                models.Lead.tenant_id == u.tenant_id,
            ).scalar() or 0
            engagement = min(100, leads_total * 2)  # 50+ leads = 100

            score = int(
                activity * 0.40 +
                result * 0.30 +
                billing * 0.15 +
                engagement * 0.15
            )
            band = "healthy" if score >= 80 else ("at_risk" if score >= 50 else "critical")

            existing = db.query(models.TenantHealth).filter_by(tenant_id=u.tenant_id).first()
            if existing:
                old_band = existing.band
                existing.score = score
                existing.band = band
                existing.components = {
                    "activity": int(activity), "result": int(result),
                    "billing": int(billing), "engagement": int(engagement),
                }
                existing.updated_at = now
                # Audit transição de banda
                if old_band != band:
                    db.add(models.AuditEvent(
                        tenant_id=u.tenant_id,
                        actor_user_id=None,
                        event_type=f"health.band_changed",
                        target_type="tenant",
                        target_id=u.tenant_id,
                        payload={"from": old_band, "to": band, "score": score},
                    ))
            else:
                db.add(models.TenantHealth(
                    tenant_id=u.tenant_id,
                    score=score, band=band,
                    components={
                        "activity": int(activity), "result": int(result),
                        "billing": int(billing), "engagement": int(engagement),
                    },
                ))
            updated += 1

        db.commit()
        logger.info("[cron.daily_recompute_tenant_health] updated=%d", updated)
    finally:
        db.close()


# ─── CLI dispatch ─────────────────────────────────────────────────────


def run_hourly():
    logger.info("[cron] starting hourly jobs")
    hourly_trial_warnings()
    hourly_quota_warnings()
    hourly_apply_pending_downgrades()
    hourly_fire_lunar_triggers()
    hourly_dispatch_daily_horoscopes()
    hourly_dispatch_daily_personal_messages()
    logger.info("[cron] hourly done")


def hourly_dispatch_daily_personal_messages():
    """Mensagem do dia personalizada por lead (Frente 4.27)."""
    try:
        import daily_personal_message as dpm
        n = dpm.hourly_dispatch_due_tenants()
        if n:
            logger.info(
                "[cron.hourly_dispatch_daily_personal_messages] tenants_processed=%d", n,
            )
    except Exception as exc:
        logger.warning("[cron.daily_personal_message] falha: %s", exc)


def hourly_dispatch_daily_horoscopes():
    """Dispara horoscopo diario para tenants cuja hora local bateu (Frente 4.13)."""
    try:
        import horoscope as horoscope_engine
        n = horoscope_engine.hourly_dispatch_due_tenants()
        if n:
            logger.info("[cron.hourly_dispatch_daily_horoscopes] tenants_processed=%d", n)
    except Exception as exc:
        logger.warning("[cron.daily_horoscope] falha: %s", exc)


def hourly_apply_pending_downgrades():
    """
    Aplica downgrades agendados quando current_period_end passou.
    Chama Stripe pra atualizar o subscription pro plano menor (Frente 2.18).
    """
    db = SessionLocal()
    applied = 0
    try:
        from api.payments.stripe_client import update_subscription_to_plan, price_id_for_plan
        now = datetime.now(timezone.utc)

        rows = db.query(models.TenantBilling).filter(
            models.TenantBilling.pending_plan.isnot(None),
        ).all()
        for billing in rows:
            effective_at = _aware(billing.pending_effective_at)
            if effective_at is None or effective_at > now:
                continue  # ainda não chegou a hora
            if not billing.subscription_id:
                continue

            new_price_id = price_id_for_plan(
                billing.pending_plan,
                billing_period=billing.pending_billing_period or "monthly",
            )
            if not new_price_id:
                logger.warning(
                    "[cron.downgrade] tenant=%s sem price_id pra %s — pulando",
                    billing.tenant_id, billing.pending_plan,
                )
                continue

            try:
                update_subscription_to_plan(
                    billing.subscription_id, new_price_id,
                    proration_behavior="none",  # sem cobrar diferença em downgrade
                    metadata={"tenant_id": billing.tenant_id, "scheduled_downgrade": "true"},
                )
            except Exception as exc:
                logger.exception("[cron.downgrade] stripe error tenant=%s: %s",
                                billing.tenant_id, exc)
                continue

            # Webhook customer.subscription.updated vai sincronizar TenantBilling
            # Limpa pending fields
            billing.pending_plan = None
            billing.pending_billing_period = None
            billing.pending_effective_at = None
            applied += 1

            db.add(models.AuditEvent(
                tenant_id=billing.tenant_id,
                actor_user_id=None,
                event_type="billing.downgrade.applied",
                target_type="tenant_billing",
                target_id=billing.tenant_id,
                payload={"plan": billing.pending_plan},
            ))

        if applied:
            db.commit()
            logger.info("[cron.hourly_apply_pending_downgrades] applied=%d", applied)
    finally:
        db.close()


def hourly_fire_lunar_triggers():
    """
    Verifica triggers lunares ativos. Dispara fluxo se:
    - Janela atingida (now é dentro do window_hours_before da fase target)
    - Trigger não foi disparado nas últimas 23h (anti-double-fire)

    V1: marca last_fired_at + envia broadcast genérico.
    V2: realmente executa flow via engine pra cada lead matching.
    """
    try:
        import lunar
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            triggers = db.query(models.LunarTrigger).filter_by(active=True).all()
            fired = 0

            today_phase = lunar.phase_for_date(now)["phase_name"]

            for tr in triggers:
                # Anti double-fire: skipa se disparou nas últimas 23h
                last_fired = _aware(tr.last_fired_at)
                if last_fired and (now - last_fired).total_seconds() < 23 * 3600:
                    continue

                # Está na fase correta agora?
                if today_phase != tr.trigger_phase:
                    continue

                # Janela: por enquanto, dispara sempre que estamos na fase
                # window_hours_before pra futuro V2 com timing antecipado

                tr.last_fired_at = now
                tr.fire_count = (tr.fire_count or 0) + 1
                fired += 1

                # Audit
                db.add(models.AuditEvent(
                    tenant_id=tr.tenant_id,
                    actor_user_id=None,
                    event_type="lunar_trigger.fired",
                    target_type="lunar_trigger",
                    target_id=str(tr.id),
                    payload={
                        "phase": tr.trigger_phase,
                        "flow_id": tr.flow_id,
                        "flow_slug": tr.flow_slug,
                    },
                ))
                logger.info(
                    "[lunar.trigger.fired] tenant=%s phase=%s flow=%s",
                    tr.tenant_id, tr.trigger_phase, tr.flow_slug or tr.flow_id,
                )

            if fired:
                db.commit()
                logger.info("[cron.hourly_fire_lunar_triggers] fired=%d", fired)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("[cron.lunar_triggers] falha: %s", exc)


def daily_recompute_lead_scores():
    """
    Recalcula score de todos os leads ativos. Frente 3.24.
    """
    try:
        import lead_scoring
        updated = lead_scoring.recompute_all()
        logger.info("[cron.daily_recompute_lead_scores] updated=%d", updated)
    except Exception as exc:
        logger.warning("[cron.daily_recompute_lead_scores] falha: %s", exc)


def run_daily():
    logger.info("[cron] starting daily jobs")
    daily_recompute_tenant_health()
    daily_recompute_lead_scores()
    daily_recompute_spiritual_intents()
    daily_hard_delete()
    logger.info("[cron] daily done")


def daily_recompute_spiritual_intents():
    """Reclassifica intent espiritual de leads ativos (Frente 4.19)."""
    try:
        import spiritual_classifier
        n = spiritual_classifier.recompute_recent_leads(days_back=7, max_leads=200)
        logger.info("[cron.daily_recompute_spiritual_intents] leads_processed=%d", n)
    except Exception as exc:
        logger.warning("[cron.spiritual_intents] falha: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    cmd = sys.argv[1] if len(sys.argv) > 1 else "hourly"
    if cmd == "hourly":
        run_hourly()
    elif cmd == "daily":
        run_daily()
    else:
        print(f"Unknown command: {cmd}. Use 'hourly' or 'daily'.")
        sys.exit(1)

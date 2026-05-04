"""
Prometheus metrics exporter (Frente 1 — observabilidade prod).

Sem dependencia de prometheus_client. Output formato Prometheus exposition
construido manualmente — leve e zero dep extra.

Metrics expostas em /metrics:
    meumisterio_uptime_seconds                                   gauge
    meumisterio_active_tenants                                   gauge
    meumisterio_active_bindings                                  gauge
    meumisterio_subscribed_bindings                              gauge
    meumisterio_inbound_total{tenant_id,phone_number_id}         gauge (cumulativo)
    meumisterio_published_flows                                  gauge
    meumisterio_wa_inbound_events_24h{event_type}                gauge
    meumisterio_leads_total{tenant_id}                           gauge
    meumisterio_messages_total{tenant_id,direction}              gauge (24h)
    meumisterio_rate_limiter_remaining{phone_number_id}          gauge

Uso (Prometheus):
    scrape_config:
      - job_name: 'meumisterio'
        bearer_token: 'xxx'  # METRICS_TOKEN
        static_configs:
          - targets: ['meumisterio.example.com']
        metrics_path: /metrics
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone, timedelta


logger = logging.getLogger(__name__)

_METRIC_NAME_RE = ("a-z", "A-Z", "0-9", "_")  # documental


def _escape_label(value: str) -> str:
    """Escape label value para formato Prometheus."""
    return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _fmt_metric(name: str, value: float, labels: dict | None = None) -> str:
    if labels:
        label_str = ",".join(
            f'{k}="{_escape_label(v)}"' for k, v in labels.items() if v is not None
        )
        return f"{name}{{{label_str}}} {value}"
    return f"{name} {value}"


def render_metrics(*, app_started_at: float) -> str:
    """
    Coleta metricas de varios componentes e renderiza no formato exposition.
    Best-effort: cada secao e isolada num try/except.
    """
    lines: list[str] = []

    # ── Uptime ────────────────────────────────────────────────────────
    lines.append("# HELP meumisterio_uptime_seconds Uptime do processo em segundos")
    lines.append("# TYPE meumisterio_uptime_seconds gauge")
    lines.append(_fmt_metric("meumisterio_uptime_seconds", int(time.time() - app_started_at)))

    # ── Tenant + binding stats ────────────────────────────────────────
    try:
        from db.database import SessionLocal
        from db import models
        from sqlalchemy import func

        db = SessionLocal()
        try:
            # Tenants ativos = users.is_active
            active_tenants = db.query(func.count(func.distinct(models.User.tenant_id))).filter(
                models.User.is_active == True,  # noqa: E712
                models.User.deleted_at.is_(None),
            ).scalar() or 0
            lines.append("# HELP meumisterio_active_tenants Tenants ativos (users.is_active)")
            lines.append("# TYPE meumisterio_active_tenants gauge")
            lines.append(_fmt_metric("meumisterio_active_tenants", int(active_tenants)))

            # Bindings totais e subscribed
            bindings_total = db.query(func.count(models.WaPhoneTenantBinding.phone_number_id)).scalar() or 0
            bindings_subs = db.query(func.count(models.WaPhoneTenantBinding.phone_number_id)).filter(
                models.WaPhoneTenantBinding.subscribed_at.isnot(None),
            ).scalar() or 0
            lines.append("# HELP meumisterio_active_bindings Total de WaPhoneTenantBinding")
            lines.append("# TYPE meumisterio_active_bindings gauge")
            lines.append(_fmt_metric("meumisterio_active_bindings", int(bindings_total)))
            lines.append("# HELP meumisterio_subscribed_bindings Bindings subscribed ao WABA")
            lines.append("# TYPE meumisterio_subscribed_bindings gauge")
            lines.append(_fmt_metric("meumisterio_subscribed_bindings", int(bindings_subs)))

            # Por binding: inbound total
            lines.append("# HELP meumisterio_inbound_total Total inbound desde a conexao por binding")
            lines.append("# TYPE meumisterio_inbound_total gauge")
            for b in db.query(models.WaPhoneTenantBinding).all():
                lines.append(_fmt_metric(
                    "meumisterio_inbound_total",
                    int(b.inbound_count or 0),
                    {"tenant_id": b.tenant_id, "phone_number_id": b.phone_number_id},
                ))

            # FlowPublish ativos
            published = db.query(func.count(models.FlowPublish.tenant_id)).filter(
                models.FlowPublish.published_blueprint_id.isnot(None),
            ).scalar() or 0
            lines.append("# HELP meumisterio_published_flows Tenants com flow publicado")
            lines.append("# TYPE meumisterio_published_flows gauge")
            lines.append(_fmt_metric("meumisterio_published_flows", int(published)))

            # Inbound events ultimas 24h por tipo
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            evt_rows = db.query(
                models.WaInboundLog.event_type,
                func.count(models.WaInboundLog.id),
            ).filter(
                models.WaInboundLog.created_at >= cutoff,
            ).group_by(models.WaInboundLog.event_type).all()
            lines.append("# HELP meumisterio_wa_inbound_events_24h Eventos WaInboundLog ultimas 24h")
            lines.append("# TYPE meumisterio_wa_inbound_events_24h gauge")
            for evt_type, cnt in evt_rows:
                lines.append(_fmt_metric(
                    "meumisterio_wa_inbound_events_24h", int(cnt),
                    {"event_type": evt_type or "unknown"},
                ))

            # Leads por tenant
            lead_rows = db.query(
                models.Lead.tenant_id,
                func.count(models.Lead.id),
            ).filter(
                models.Lead.opt_out == False,  # noqa: E712
            ).group_by(models.Lead.tenant_id).all()
            lines.append("# HELP meumisterio_leads_total Leads ativos (opt_out=false) por tenant")
            lines.append("# TYPE meumisterio_leads_total gauge")
            for tenant_id, cnt in lead_rows:
                lines.append(_fmt_metric(
                    "meumisterio_leads_total", int(cnt),
                    {"tenant_id": tenant_id or "default"},
                ))

            # Messages por direcao (24h)
            msg_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            msg_rows = db.query(
                models.Lead.tenant_id,
                models.Mensagem.remetente,
                func.count(models.Mensagem.id),
            ).join(
                models.Lead, models.Mensagem.lead_id == models.Lead.id,
            ).filter(
                models.Mensagem.timestamp >= msg_cutoff,
            ).group_by(models.Lead.tenant_id, models.Mensagem.remetente).all()
            lines.append("# HELP meumisterio_messages_total Mensagens ultimas 24h por tenant e direcao")
            lines.append("# TYPE meumisterio_messages_total gauge")
            for tenant_id, direction, cnt in msg_rows:
                lines.append(_fmt_metric(
                    "meumisterio_messages_total", int(cnt),
                    {
                        "tenant_id": tenant_id or "default",
                        "direction": (direction or "unknown"),
                    },
                ))
        finally:
            db.close()
    except Exception as exc:
        logger.warning("[metrics_exporter] db section falhou: %s", exc)

    # ── Rate limiter snapshot ─────────────────────────────────────────
    try:
        from wa_rate_limiter import stats as rate_stats
        snap = rate_stats() or {}
        lines.append("# HELP meumisterio_rate_limiter_remaining Tokens restantes no bucket por phone_number_id")
        lines.append("# TYPE meumisterio_rate_limiter_remaining gauge")
        for phone_id, info in snap.items():
            lines.append(_fmt_metric(
                "meumisterio_rate_limiter_remaining",
                int(info.get("tokens_remaining", 0)),
                {"phone_number_id": phone_id},
            ))
    except Exception as exc:
        logger.warning("[metrics_exporter] rate_limiter section falhou: %s", exc)

    return "\n".join(lines) + "\n"


def check_metrics_auth(token_header: str | None) -> bool:
    """
    Valida Authorization header. Se METRICS_TOKEN nao setada, /metrics e
    publicamente acessivel (uso em ambientes com firewall na frente).
    """
    expected = (os.getenv("METRICS_TOKEN") or "").strip()
    if not expected:
        return True
    if not token_header:
        return False
    # Aceita "Bearer xxx" ou "xxx"
    parts = token_header.strip().split(None, 1)
    actual = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else token_header.strip()
    import hmac
    return hmac.compare_digest(expected, actual.strip())

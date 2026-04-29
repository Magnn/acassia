"""
Funnel waterfall analytics (Frente 3.26-3.27).

Computa drop-off por nó pra cada fluxo do tenant.

API:
    record_node_entry(lead_id, flow_id, flow_slug, node_id) — chamar do engine
    record_node_exit(visit_id, exit_reason) — quando lead sai
    funnel_for_flow(flow_id|slug, period_days, segment) → {steps, conversion_pct}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def record_node_entry(
    *,
    lead_id: int,
    tenant_id: str,
    node_id: str,
    flow_id: Optional[int] = None,
    flow_slug: Optional[str] = None,
    db_session=None,
) -> Optional[int]:
    """
    Marca entrada do lead em um nó. Auto-fecha visita anterior do mesmo lead/flow
    com exit_reason="next".

    Retorna ID da nova visita (ou None se falha).
    """
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        # Fecha visita anterior (sem exited_at) do mesmo lead+flow
        prev = db.query(models.FlowNodeVisit).filter(
            models.FlowNodeVisit.lead_id == lead_id,
            models.FlowNodeVisit.exited_at.is_(None),
        ).all()
        for p in prev:
            p.exited_at = datetime.now(timezone.utc)
            p.exit_reason = "next"

        visit = models.FlowNodeVisit(
            tenant_id=tenant_id,
            flow_id=flow_id,
            flow_slug=flow_slug,
            node_id=node_id,
            lead_id=lead_id,
        )
        db.add(visit)
        db.commit()
        db.refresh(visit)
        return visit.id
    except Exception as exc:
        logger.warning("[funnel.record_entry] falha: %s", exc)
        return None
    finally:
        if own:
            db.close()


def record_node_exit(visit_id: int, exit_reason: str = "response", db_session=None) -> None:
    """Marca saída de um nó com motivo."""
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        v = db.query(models.FlowNodeVisit).filter_by(id=visit_id).first()
        if v and v.exited_at is None:
            v.exited_at = datetime.now(timezone.utc)
            v.exit_reason = exit_reason[:40]
            db.commit()
    finally:
        if own:
            db.close()


def funnel_for_flow(
    *,
    tenant_id: str,
    flow_id: Optional[int] = None,
    flow_slug: Optional[str] = None,
    period_days: int = 30,
    score_band: Optional[str] = None,
) -> dict:
    """
    Computa funnel waterfall.

    Output:
    {
        "flow_id": ...,
        "flow_slug": ...,
        "period_days": 30,
        "low_confidence": false,    # True se < 50 leads
        "total_runs": int,
        "overall_conversion_pct": float,  # % chegou ao último nó
        "steps": [
            {
                "node_id": "1_apresentacao",
                "entered": 1247,
                "responded": 1100,         # exited com response
                "drop": 147,
                "drop_pct": 11.8,
                "median_time_in_node_s": 45,
            }, ...
        ]
    }
    """
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        q = db.query(models.FlowNodeVisit).filter(
            models.FlowNodeVisit.tenant_id == tenant_id,
            models.FlowNodeVisit.entered_at >= since,
        )
        if flow_id is not None:
            q = q.filter(models.FlowNodeVisit.flow_id == flow_id)
        elif flow_slug:
            q = q.filter(models.FlowNodeVisit.flow_slug == flow_slug)

        # Filter por score_band se fornecido (join com leads)
        if score_band:
            q = q.join(models.Lead, models.FlowNodeVisit.lead_id == models.Lead.id)
            q = q.filter(models.Lead.score_band == score_band)

        visits = q.all()

        # Agrupa por node_id, mantendo ordem de aparição global
        node_order: list[str] = []
        node_stats: dict[str, dict] = {}
        for v in visits:
            if v.node_id not in node_stats:
                node_stats[v.node_id] = {
                    "node_id": v.node_id,
                    "entered_count": 0,
                    "responded_count": 0,
                    "exit_reasons": {},
                    "durations_s": [],
                }
                node_order.append(v.node_id)
            stats = node_stats[v.node_id]
            stats["entered_count"] += 1

            if v.exited_at:
                entered_ts = _aware(v.entered_at)
                exited_ts = _aware(v.exited_at)
                if entered_ts and exited_ts:
                    stats["durations_s"].append((exited_ts - entered_ts).total_seconds())
                if v.exit_reason == "response":
                    stats["responded_count"] += 1
                stats["exit_reasons"][v.exit_reason or "unknown"] = (
                    stats["exit_reasons"].get(v.exit_reason or "unknown", 0) + 1
                )

        # Compute drop entre nós consecutivos
        # node N → node N+1: lead avançou se há visita do mesmo lead em N+1
        # drop = entered N - entered N+1 (no mesmo período)
        steps = []
        for i, node_id in enumerate(node_order):
            s = node_stats[node_id]
            entered = s["entered_count"]
            durations = sorted(s["durations_s"])
            median_s = durations[len(durations) // 2] if durations else None

            # Compute drop comparado com próximo nó na ordem
            next_entered = (
                node_stats[node_order[i + 1]]["entered_count"]
                if i + 1 < len(node_order) else None
            )
            if next_entered is not None and entered > 0:
                drop = max(0, entered - next_entered)
                drop_pct = round(drop / entered * 100, 1)
            else:
                # Último nó: não há "próximo" — drop calculado como leads que ficaram
                # parados nesse nó (entrou mas não saiu/converteu)
                no_exit = sum(1 for v in visits if v.node_id == node_id and v.exited_at is None)
                drop = no_exit
                drop_pct = round(no_exit / entered * 100, 1) if entered > 0 else 0

            steps.append({
                "node_id": node_id,
                "entered": entered,
                "drop": drop,
                "drop_pct": drop_pct,
                "exit_reasons": s["exit_reasons"],
                "median_time_s": int(median_s) if median_s is not None else None,
                "is_high_drop": drop_pct >= 30,  # flag pra UI destacar
            })

        total_leads = len(set(v.lead_id for v in visits))
        # Conversão geral: % do total que chegaram ao último nó
        last_step_count = steps[-1]["entered"] if steps else 0
        first_step_count = steps[0]["entered"] if steps else 0
        overall_conversion_pct = round(
            last_step_count / first_step_count * 100, 1
        ) if first_step_count > 0 else 0.0

        return {
            "flow_id": flow_id,
            "flow_slug": flow_slug,
            "period_days": period_days,
            "score_band_filter": score_band,
            "total_runs": len(visits),
            "unique_leads": total_leads,
            "low_confidence": total_leads < 50,
            "overall_conversion_pct": overall_conversion_pct,
            "steps": steps,
        }
    finally:
        db.close()


def list_flows_with_visits(tenant_id: str, *, period_days: int = 30) -> list[dict]:
    """Lista todos os fluxos que tiveram pelo menos 1 visita no período."""
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=period_days)
        rows = (
            db.query(
                models.FlowNodeVisit.flow_id,
                models.FlowNodeVisit.flow_slug,
                func.count(models.FlowNodeVisit.id).label("visits"),
                func.count(func.distinct(models.FlowNodeVisit.lead_id)).label("unique_leads"),
            )
            .filter(
                models.FlowNodeVisit.tenant_id == tenant_id,
                models.FlowNodeVisit.entered_at >= since,
            )
            .group_by(models.FlowNodeVisit.flow_id, models.FlowNodeVisit.flow_slug)
            .order_by(func.count(models.FlowNodeVisit.id).desc())
            .all()
        )
        return [
            {
                "flow_id": r.flow_id,
                "flow_slug": r.flow_slug,
                "visits": r.visits,
                "unique_leads": r.unique_leads,
            } for r in rows
        ]
    finally:
        db.close()

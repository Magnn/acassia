"""Execução durável de blueprints iniciados pela API da plataforma."""
from __future__ import annotations

from db import models
from db.database import SessionLocal
from flow_executor import document_to_acoes, flow_context_from_lead
from schema import ContextoConversa


def execute_flow_job(tenant_id: str, blueprint_id: int, lead_id: int, run_id: int) -> None:
    from api.payments.dispatch import _build_worker_engine

    db = SessionLocal()
    try:
        bp = db.query(models.FlowBlueprint).filter_by(id=blueprint_id, tenant_id=tenant_id).first()
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        run = db.query(models.FlowRun).filter_by(id=run_id, tenant_id=tenant_id).first()
        if not bp or not lead or not run:
            raise ValueError("flow_job_resource_not_found")
        run.status = "running"
        db.add(models.FlowRunEvent(run_id=run.id, seq=2, event_type="run_started", payload_json={}))
        db.commit()

        values = flow_context_from_lead(lead, tenant_id=tenant_id)
        actions = document_to_acoes(bp.body_json or {}, context=values, tenant_id=tenant_id, blueprint_id=bp.id)
        if not actions:
            raise ValueError("flow_blueprint_without_actions")
        runtime = _build_worker_engine(tenant_id)
        ctx = ContextoConversa(
            lead_id=lead.id, telefone=lead.telefone, node_atual=lead.node_atual or "1_apresentacao",
            historico=runtime._buscar_historico(db, lead.id, 20), texto_recebido="[FLOW_RUN]",
            tipo_mensagem="system", personalizer=runtime.personalizer,
        )
        ctx.metadata.update(values)
        runtime._processar_fila(lead.id, ctx, actions)
        run.status = "completed"
        db.add(models.FlowRunEvent(run_id=run.id, seq=3, event_type="run_completed", payload_json={"actions": len(actions)}))
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.query(models.FlowRun).filter_by(id=run_id, tenant_id=tenant_id).first()
        if run:
            run.status = "failed"
            db.add(models.FlowRunEvent(run_id=run.id, seq=99, event_type="run_failed", payload_json={"error": str(exc)[:500]}))
            db.commit()
        raise
    finally:
        db.close()

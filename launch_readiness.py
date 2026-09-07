"""Checklist de ativação calculado por conta, sem chamadas externas ou mutações."""
from db import models
from db.database import SessionLocal
from flow_builder_runtime import validate_flow_document


def launch_readiness(tenant_id: str) -> dict:
    with SessionLocal() as db:
        variables = {v.key: v.value_json for v in db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id
        ).all()}
        phone = variables.get("whatsapp.phone_number_id")
        binding = db.query(models.WaPhoneTenantBinding).filter_by(
            tenant_id=tenant_id, phone_number_id=str(phone)
        ).first() if phone else None
        connected = bool(binding and binding.status == "active" and binding.last_verified_at)
        agent = db.query(models.StudioAgent).filter_by(tenant_id=tenant_id).first()
        blueprint = db.query(models.FlowBlueprint).filter_by(tenant_id=tenant_id).first()
        publication = db.query(models.FlowPublish).filter_by(tenant_id=tenant_id).first()
        published = db.query(models.FlowBlueprint).filter_by(
            tenant_id=tenant_id, id=publication.published_blueprint_id
        ).first() if publication and publication.published_blueprint_id else None
        valid = bool(published and validate_flow_document(published.body_json or {}, strict=True).get("ok"))
        sent = db.query(models.Mensagem).join(models.Lead, models.Mensagem.lead_id == models.Lead.id).filter(
            models.Lead.tenant_id == tenant_id, models.Mensagem.remetente == "bot"
        ).first() is not None
        steps = [
            ("business", "Configurar atendente e oferta", bool(agent and variables.get("oferta.nome")), "/onboarding"),
            ("whatsapp", "Validar conexão do WhatsApp", connected, "/integrations"),
            ("inbound", "Receber uma mensagem de teste", bool(connected and binding.inbound_count), "/integrations"),
            ("flow", "Preparar seu funil", bool(blueprint), "/blueprints"),
            ("published", "Publicar um fluxo válido", valid, "/blueprints"),
            ("reply", "Conferir a primeira resposta do bot", sent, "/inbox"),
        ]
        items = [dict(key=key, label=label, completed=done, href=href) for key, label, done, href in steps]
        return {
            "steps": items,
            "completed_count": sum(item["completed"] for item in items),
            "total": len(items),
            "next_step": next((item for item in items if not item["completed"]), None),
            "checks_complete": all(item["completed"] for item in items),
        }

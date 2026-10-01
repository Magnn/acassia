from db.database import SessionLocal
from db.models import EventoAudit, FlowBlueprint, FlowPublish, Lead
from engine import Engine
from schema import ContextoConversa


def test_engine_reads_published_blueprint_and_executes_canvas_path():
    tenant_id = "tenant-published-engine-bridge"
    db = SessionLocal()
    try:
        db.query(FlowPublish).filter_by(tenant_id=tenant_id).delete()
        db.query(FlowBlueprint).filter_by(tenant_id=tenant_id).delete()
        db.query(Lead).filter_by(tenant_id=tenant_id).delete()
        db.commit()

        lead = Lead(
            tenant_id=tenant_id,
            telefone="5592999990001",
            nome="Bia",
            metadata_json={},
        )
        blueprint = FlowBlueprint(
            tenant_id=tenant_id,
            slug="bridge-test",
            title="Bridge test",
            body_json={
                "format": "meumisterio-flow",
                "version": 1,
                "title": "Bridge test",
                "graph": {
                    "nodes": [
                        {
                            "id": "trigger",
                            "type": "trigger",
                            "config": {"integration": "whatsapp", "event": "keyword", "keyword": "começar"},
                        },
                        {"id": "message", "type": "conteudo", "config": {"body": "Olá {{lead.nome}}"}},
                        {"id": "end", "type": "end", "config": {}},
                    ],
                    "edges": [
                        {"from": "trigger", "to": "message"},
                        {"from": "message", "to": "end"},
                    ],
                },
            },
        )
        second_lead = Lead(
            tenant_id=tenant_id,
            telefone="5592999990003",
            nome="Caio",
            metadata_json={},
        )
        second_blueprint = FlowBlueprint(
            tenant_id=tenant_id,
            slug="bridge-test-support",
            title="Bridge support",
            body_json={
                "format": "meumisterio-flow",
                "version": 1,
                "title": "Bridge support",
                "graph": {
                    "nodes": [
                        {"id": "trigger", "type": "trigger", "config": {"integration": "whatsapp", "event": "keyword", "keyword": "ajuda"}},
                        {"id": "message", "type": "conteudo", "config": {"body": "Support for {{lead.nome}}"}},
                        {"id": "end", "type": "end", "config": {}},
                    ],
                    "edges": [{"from": "trigger", "to": "message"}, {"from": "message", "to": "end"}],
                },
            },
        )
        db.add_all([lead, blueprint, second_lead, second_blueprint])
        db.flush()
        db.add_all([
            FlowPublish(tenant_id=tenant_id, published_blueprint_id=blueprint.id),
            FlowPublish(tenant_id=tenant_id, published_blueprint_id=second_blueprint.id),
        ])
        db.commit()

        ctx = ContextoConversa(
            lead_id=lead.id,
            telefone=lead.telefone,
            node_atual=lead.node_atual,
            texto_recebido="começar",
            nome_lead=lead.nome or "",
        )
        flow_engine = object.__new__(Engine)
        flow_engine._tenant_id_static = tenant_id

        handled, actions = flow_engine._try_published_flow_turn(db, lead, ctx)

        assert handled is True
        assert [action.conteudo for action in actions] == ["Olá Bia"]
        assert ctx.metadata["flow_builder_runtime"]["status"] == "completed"

        second_ctx = ContextoConversa(
            lead_id=second_lead.id,
            telefone=second_lead.telefone,
            node_atual=second_lead.node_atual,
            texto_recebido="ajuda",
            nome_lead=second_lead.nome or "",
        )
        second_handled, second_actions = flow_engine._try_published_flow_turn(db, second_lead, second_ctx)
        assert second_handled is True
        assert [action.conteudo for action in second_actions] == ["Support for Caio"]
        assert second_ctx.metadata["flow_builder_runtime"]["blueprint_id"] == second_blueprint.id
    finally:
        db.rollback()
        lead_ids = [row[0] for row in db.query(Lead.id).filter_by(tenant_id=tenant_id).all()]
        if lead_ids:
            db.query(EventoAudit).filter(EventoAudit.lead_id.in_(lead_ids)).delete(synchronize_session=False)
        db.query(FlowPublish).filter_by(tenant_id=tenant_id).delete()
        db.query(FlowBlueprint).filter_by(tenant_id=tenant_id).delete()
        db.query(Lead).filter_by(tenant_id=tenant_id).delete()
        db.commit()
        db.close()


def test_notify_attendant_effect_pauses_bot_and_preserves_context():
    tenant_id = "tenant-handoff-engine-bridge"
    db = SessionLocal()
    try:
        lead = Lead(tenant_id=tenant_id, telefone="5592999990002", metadata_json={})
        db.add(lead)
        db.flush()
        ctx = ContextoConversa(
            lead_id=lead.id,
            telefone=lead.telefone,
            node_atual=lead.node_atual,
            texto_recebido="Quero falar com alguém",
        )
        flow_engine = object.__new__(Engine)
        flow_engine._tenant_id_static = tenant_id

        flow_engine._apply_published_flow_effects(
            db,
            lead,
            ctx,
            [{"kind": "notify_attendant", "payload": "Dúvida: Como agendar?"}],
        )

        assert lead.bot_pausado is True
        assert ctx.metadata["flow_chat_status"] == "waiting_attendant"
        db.flush()
        event = db.query(EventoAudit).filter_by(lead_id=lead.id, evento="flow_builder_side_effect").one()
        assert event.dados["kind"] == "notify_attendant"
        assert "Como agendar?" in event.dados["payload"]
    finally:
        db.rollback()
        lead_ids = [row[0] for row in db.query(Lead.id).filter_by(tenant_id=tenant_id).all()]
        if lead_ids:
            db.query(EventoAudit).filter(EventoAudit.lead_id.in_(lead_ids)).delete(synchronize_session=False)
        db.query(Lead).filter_by(tenant_id=tenant_id).delete()
        db.commit()
        db.close()

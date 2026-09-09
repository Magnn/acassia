"""
Dispatch de eventos de pagamento aprovados → blueprint editável.

Após signature ([signatures.py]) + idempotência ([idempotency.py]), o handler
de webhook chama :func:`dispatch_post_payment_blueprint` que:

1. Carrega o blueprint do tenant pelo slug ``post_payment``
2. Valida que o lead existe (e pertence ao tenant — isolamento estrito)
3. Enfileira um job durável no Redis; o worker compila o blueprint e entrega
   as ações pela mesma fila do motor usada pelos fluxos manuais.

Ver ADR_006 (post_payment híbrido).
"""

import logging
import os
from typing import Optional

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

POST_PAYMENT_SLUG = "post_payment"


def dispatch_post_payment_blueprint(
    tenant_id: str,
    lead_id: int,
    provider: str,
    event_id: str,
    payment_metadata: Optional[dict] = None,
) -> bool:
    """
    Enfileira o blueprint ``post_payment`` do tenant na fila durável.

    Args:
        tenant_id: identificador do tenant (multi-tenant strict).
        lead_id: id do :class:`db.models.Lead` que pagou.
        provider: ``'stripe'`` | ``'cakto'`` (informação que vai pro contexto).
        event_id: id do evento (correlação em logs e métricas).
        payment_metadata: dict opcional com produto, valor, currency etc — vai
            pro context do blueprint sob a chave ``payment``.

    Returns:
        ``True`` se o dispatch foi enfileirado.
        ``False`` se blueprint não existe ou lead não foi encontrado / é de
        outro tenant.

    Se o Redis estiver indisponível, retorna ``False`` para o webhook poder
    responder com falha e receber uma nova tentativa do provedor.
    """
    db = SessionLocal()
    try:
        blueprint = db.query(models.FlowBlueprint).filter_by(
            tenant_id=tenant_id,
            slug=POST_PAYMENT_SLUG,
        ).first()
        if not blueprint:
            logger.warning(
                "[payments.dispatch] SKIP: tenant=%s sem blueprint slug=%s",
                tenant_id, POST_PAYMENT_SLUG,
            )
            return False

        lead = db.query(models.Lead).filter_by(
            id=lead_id,
            tenant_id=tenant_id,
        ).first()
        if not lead:
            logger.warning(
                "[payments.dispatch] SKIP: lead=%s não encontrado pro tenant=%s",
                lead_id, tenant_id,
            )
            return False

        blueprint_id = blueprint.id

        delivery = db.query(models.PaymentDelivery).filter_by(
            tenant_id=tenant_id,
            provider=provider,
            event_id=event_id,
        ).first()

        if delivery and delivery.status == "delivered":
            logger.info(
                "[payments.dispatch] ALREADY_DELIVERED: tenant=%s event=%s",
                tenant_id, event_id,
            )
            return True

        if not delivery:
            delivery = models.PaymentDelivery(
                tenant_id=tenant_id,
                lead_id=lead_id,
                blueprint_id=blueprint_id,
                provider=provider,
                event_id=event_id,
                status="pending",
                payment_metadata=payment_metadata or {},
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)
        delivery_id = delivery.id
    finally:
        db.close()

    from api.utils.task_queue import enqueue_post_payment

    queued = enqueue_post_payment(
        delivery_id=delivery_id,
        tenant_id=tenant_id,
        blueprint_id=blueprint_id,
        lead_id=lead_id,
        provider=provider,
        event_id=event_id,
        payment_metadata=payment_metadata or {},
    )
    if not queued:
        logger.error("[payments.dispatch] queue unavailable: tenant=%s event=%s", tenant_id, event_id)
        db = SessionLocal()
        try:
            d = db.query(models.PaymentDelivery).filter_by(id=delivery_id).first()
            if d:
                d.status = "failed"
                d.last_error = "queue_unavailable"
                db.commit()
        finally:
            db.close()
        return False
    logger.info(
        "[payments.dispatch] QUEUED: tenant=%s lead=%s provider=%s event=%s delivery=%s",
        tenant_id, lead_id, provider, event_id, delivery_id,
    )
    return True


def _run_post_payment(
    tenant_id: str,
    blueprint_id: int,
    lead_id: int,
    provider: str,
    event_id: str,
    payment_metadata: dict,
    delivery_id: Optional[int] = None,
    engine=None,
) -> None:
    """
    Executa o blueprint na thread. Captura todas as exceções pra não morrer
    silenciosamente (exceções em threads do Python somem por default).

    Imports são locais pra evitar ciclos no import-time do módulo.
    """
    db = SessionLocal()
    delivery = None
    try:
        from flow_executor import document_to_acoes, flow_context_from_lead

        if delivery_id:
            delivery = db.query(models.PaymentDelivery).filter_by(id=delivery_id).first()
        if not delivery:
            delivery = db.query(models.PaymentDelivery).filter_by(
                tenant_id=tenant_id, provider=provider, event_id=event_id,
            ).first()

        if delivery and delivery.status == "delivered":
            logger.info("[payments.dispatch] Already delivered, skipping: %s", event_id)
            return

        if delivery:
            delivery.status = "delivering"
            delivery.attempts = (delivery.attempts or 0) + 1
            db.commit()

        bp = db.query(models.FlowBlueprint).filter_by(id=blueprint_id, tenant_id=tenant_id).first()
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not bp or not lead:
            logger.error(
                "[payments.dispatch] ABORT: blueprint=%s lead=%s sumiram entre dispatch e execução",
                blueprint_id, lead_id,
            )
            if delivery:
                delivery.status = "failed"
                delivery.last_error = "blueprint_or_lead_missing"
                db.commit()
            return

        ctx = flow_context_from_lead(lead, tenant_id=tenant_id)
        ctx["payment"] = {
            "provider": provider,
            "event_id": event_id,
            **payment_metadata,
        }

        acoes = document_to_acoes(
            bp.body_json or {},
            context=ctx,
            tenant_id=tenant_id,
            blueprint_id=bp.id,
        )

        if not acoes:
            raise ValueError("post_payment_blueprint_without_actions")

        runtime = engine or _build_worker_engine(tenant_id)
        from schema import ContextoConversa

        runtime_ctx = ContextoConversa(
            lead_id=lead.id,
            telefone=lead.telefone,
            node_atual=lead.node_atual or "9_entrega",
            historico=runtime._buscar_historico(db, lead.id, 20),
            texto_recebido="[PAYMENT_APPROVED]",
            tipo_mensagem="system",
            personalizer=runtime.personalizer,
        )
        runtime_ctx.metadata.update(ctx)
        runtime._processar_fila(lead.id, runtime_ctx, acoes)

        if delivery:
            from datetime import datetime, timezone
            delivery.status = "delivered"
            delivery.delivered_at = datetime.now(timezone.utc)
            delivery.last_error = None
            db.commit()

        logger.info("[payments.dispatch] DELIVERED: blueprint=%s lead=%s acoes=%d", bp.id, lead_id, len(acoes))
    except Exception as exc:
        if delivery:
            delivery.status = "failed"
            delivery.last_error = str(exc)[:500]
            try:
                db.commit()
            except Exception:
                pass
        logger.exception(
            "[payments.dispatch] CRASHED: tenant=%s lead=%s event=%s",
            tenant_id, lead_id, event_id,
        )
        raise
    finally:
        db.close()


def _build_worker_engine(tenant_id: str):
    """Cria o motor no processo worker sem importar ``app`` (evita ciclos)."""
    from personalizer import Personalizer
    from engine import Engine

    gemini_key = os.getenv("GEMINI_API_KEY")
    return Engine(
        whatsapp_token=os.getenv("WEBAPP_TOKEN"),
        whatsapp_phone_id=os.getenv("PHONE_NUMBER_ID"),
        personalizer=Personalizer(api_key=gemini_key),
        gemini_api_key=gemini_key,
        tenant_id=tenant_id,
    )


# ─── API SaaS para Auditoria e Retry de Entregas ───
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

payments_bp = Blueprint("saas_payments", __name__, url_prefix="/saas/payments")


@payments_bp.route("/deliveries", methods=["GET"])
@login_required
def list_deliveries():
    """Lista o histórico do outbox de entregas pós-pagamento."""
    db = SessionLocal()
    try:
        query = db.query(models.PaymentDelivery).filter_by(tenant_id=current_user.tenant_id)
        status = request.args.get("status")
        if status:
            query = query.filter_by(status=status)
        deliveries = query.order_by(models.PaymentDelivery.created_at.desc()).limit(100).all()
        return jsonify({
            "deliveries": [
                {
                    "id": d.id,
                    "lead_id": d.lead_id,
                    "blueprint_id": d.blueprint_id,
                    "provider": d.provider,
                    "event_id": d.event_id,
                    "status": d.status,
                    "attempts": d.attempts,
                    "last_error": d.last_error,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                }
                for d in deliveries
            ]
        })
    finally:
        db.close()


@payments_bp.route("/deliveries/<int:delivery_id>/retry", methods=["POST"])
@login_required
def retry_delivery(delivery_id: int):
    """Reenfileira manualmente uma entrega pós-pagamento que falhou."""
    db = SessionLocal()
    try:
        delivery = db.query(models.PaymentDelivery).filter_by(
            id=delivery_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not delivery:
            return jsonify({"error": "delivery_not_found"}), 404

        from api.utils.task_queue import enqueue_post_payment
        delivery.status = "pending"
        db.commit()

        queued = enqueue_post_payment(
            delivery_id=delivery.id,
            tenant_id=delivery.tenant_id,
            blueprint_id=delivery.blueprint_id,
            lead_id=delivery.lead_id,
            provider=delivery.provider,
            event_id=delivery.event_id,
            payment_metadata=delivery.payment_metadata or {},
        )
        return jsonify({"ok": True, "enqueued": bool(queued), "delivery_id": delivery.id})
    finally:
        db.close()

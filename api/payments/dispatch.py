"""
Dispatch de eventos de pagamento aprovados → blueprint editável.

Após signature ([signatures.py]) + idempotência ([idempotency.py]), o handler
de webhook chama :func:`dispatch_post_payment_blueprint` que:

1. Carrega o blueprint do tenant pelo slug ``post_payment``
2. Valida que o lead existe (e pertence ao tenant — isolamento estrito)
3. Compila o blueprint pra lista de ``Acao`` em thread separada (não bloqueia
   a resposta do webhook — Stripe/Cakto têm timeout curto)

A integração concreta da fila do motor (envio efetivo das ``Acao`` ao
WhatsApp) entra em **G5b**, junto com o desenho dos blueprints semente.
Por enquanto, esta função compila e loga — bom o bastante pra:

* validar que o blueprint do tenant existe e é parseável
* exercitar o caminho completo signature → idempotência → dispatch
* gerar telemetria de dispatch que vai virar feature de UI no painel

Ver ADR_006 (post_payment híbrido).
"""

import logging
import threading
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
    Dispara o blueprint ``post_payment`` do tenant em thread daemon.

    Args:
        tenant_id: identificador do tenant (multi-tenant strict).
        lead_id: id do :class:`db.models.Lead` que pagou.
        provider: ``'stripe'`` | ``'cakto'`` (informação que vai pro contexto).
        event_id: id do evento (correlação em logs e métricas).
        payment_metadata: dict opcional com produto, valor, currency etc — vai
            pro context do blueprint sob a chave ``payment``.

    Returns:
        ``True`` se o dispatch foi enfileirado (thread iniciada).
        ``False`` se blueprint não existe ou lead não foi encontrado / é de
        outro tenant.

    A thread é daemon — não prende shutdown do processo.
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
    finally:
        db.close()

    thread = threading.Thread(
        target=_run_post_payment,
        args=(tenant_id, blueprint_id, lead_id, provider, event_id, payment_metadata or {}),
        name=f"post_payment_{provider}_{str(event_id)[:16]}",
        daemon=True,
    )
    thread.start()
    logger.info(
        "[payments.dispatch] QUEUED: tenant=%s lead=%s provider=%s event=%s",
        tenant_id, lead_id, provider, event_id,
    )
    return True


def _run_post_payment(
    tenant_id: str,
    blueprint_id: int,
    lead_id: int,
    provider: str,
    event_id: str,
    payment_metadata: dict,
) -> None:
    """
    Executa o blueprint na thread. Captura todas as exceções pra não morrer
    silenciosamente (exceções em threads do Python somem por default).

    Imports são locais pra evitar ciclos no import-time do módulo.
    """
    try:
        from flow_executor import document_to_acoes, flow_context_from_lead

        db = SessionLocal()
        try:
            bp = db.query(models.FlowBlueprint).filter_by(id=blueprint_id).first()
            lead = db.query(models.Lead).filter_by(id=lead_id).first()
            if not bp or not lead:
                logger.error(
                    "[payments.dispatch] ABORT: blueprint=%s lead=%s sumiram entre dispatch e execução",
                    blueprint_id, lead_id,
                )
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

            logger.info(
                "[payments.dispatch] RAN: blueprint=%s lead=%s acoes=%d",
                bp.id, lead_id, len(acoes) if acoes else 0,
            )

            # G5b vai ligar a lista `acoes` na fila do motor (motor.enfileirar()
            # ou equivalente). Hoje só compila — útil pra:
            #   - validar que o blueprint do cliente compila
            #   - gerar telemetria de dispatch (logs)
            #   - exercitar o caminho completo end-to-end em testes
            _enfileirar_acoes_pendente(lead, acoes)
        finally:
            db.close()
    except Exception:
        logger.exception(
            "[payments.dispatch] CRASHED: tenant=%s lead=%s event=%s",
            tenant_id, lead_id, event_id,
        )


def _enfileirar_acoes_pendente(lead: models.Lead, acoes) -> None:
    """
    Hook pra ligar com a fila de envio do motor.
    Implementação concreta vem com G5b.
    """
    if not acoes:
        logger.warning(
            "[payments.dispatch] blueprint vazio — sem acoes pra enviar (lead=%s)",
            lead.id,
        )
        return
    logger.info(
        "[payments.dispatch] PENDING ENQUEUE: lead=%s acoes=%d (TODO G5b: ligar com motor)",
        lead.id, len(acoes),
    )

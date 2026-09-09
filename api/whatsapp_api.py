"""
WhatsApp client legado — agora um shim por cima do sistema multi-provider.

Mantém a API ``whatsapp_client.enviar_mensagem(...)`` que o motor já usa,
mas internamente delega pro provider configurado do tenant em curso. Em
runtime, o tenant é resolvido via ``tenant_context.get_request_tenant_id``
quando há request Flask, ou via env ``MEU_MISTERIO_TENANT_ID`` (default)
em workers / threads.

Para uso explícito multi-tenant, use:

    from api.whatsapp_providers import get_provider_for_tenant
    p = get_provider_for_tenant(tenant_id)
    p.enviar_mensagem(...)
"""

from __future__ import annotations

import logging
import os
import threading

from dotenv import load_dotenv

from api.whatsapp_providers import get_provider_for_tenant

load_dotenv()

logger = logging.getLogger(__name__)


def _current_tenant_id() -> str:
    try:
        from flask import has_request_context
        from tenant_context import get_request_tenant_id

        if has_request_context():
            return get_request_tenant_id()
    except Exception:
        pass
    return os.getenv("MEU_MISTERIO_TENANT_ID", "default")


# Cache em memória de tenants que já tiveram primeira msg enviada na vida
# desse processo. A checagem cara (DB count) só roda uma vez por tenant.
_first_msg_cache: set[str] = set()
_first_msg_lock = threading.Lock()


def _maybe_track_first_message_sent(tenant_id: str) -> None:
    """
    Dispara ``first_message_sent`` apenas na primeira mensagem outbound
    histórica do tenant. Após disparar, marca em cache pra evitar query.
    Falhas são silenciosas — telemetria nunca quebra o envio.
    """
    if tenant_id in _first_msg_cache:
        return
    try:
        from db import models
        from db.database import SessionLocal
        from analytics_telemetry import track

        db = SessionLocal()
        try:
            existing = (
                db.query(models.Mensagem.id)
                .join(models.Lead, models.Mensagem.lead_id == models.Lead.id)
                .filter(models.Lead.tenant_id == tenant_id)
                .filter(models.Mensagem.remetente == "bot")
                .limit(1)
                .first()
            )
            if not existing:
                track("first_message_sent", tenant_id=tenant_id)
            with _first_msg_lock:
                _first_msg_cache.add(tenant_id)
        finally:
            db.close()
    except Exception as exc:
        logger.debug("[telemetry] first_message_sent check falhou: %s", exc)


class WhatsAppAPI:
    """
    Compat shim: mantém a forma do client antigo (singleton, método
    enviar_mensagem) mas resolve provider per-tenant em cada chamada.
    """

    def enviar_mensagem(self, numero: str, conteudo: str, formato: str = "texto") -> bool:
        tid = _current_tenant_id()

        # Opt-out check (Frente 8.17): se lead pediu STOP, não envia
        try:
            from db.database import SessionLocal
            from db import models
            from api.saas.privacy import is_lead_opted_out
            db = SessionLocal()
            try:
                lead = db.query(models.Lead).filter_by(
                    tenant_id=tid, telefone=numero,
                ).first()
                if lead and is_lead_opted_out(lead):
                    logger.warning(
                        "[privacy.opt_out] tenant=%s numero=%s — bloqueado envio (lead opted out)",
                        tid, numero,
                    )
                    return False
            finally:
                db.close()
        except Exception as exc:
            logger.warning("[privacy.opt_out] check falhou (fail open): %s", exc)

        # Quota check ANTES do envio (Frente 2.5)
        try:
            import quota
            allowed, current, limit = quota.consume_quota(tid, "wa_msgs_month", 1)
            if not allowed:
                logger.warning(
                    "[quota.wa_msgs.exceeded] tenant=%s current=%s limit=%s — bloqueando envio",
                    tid, current, limit,
                )
                return False
        except Exception as exc:
            logger.warning("[quota.wa_msgs] check falhou (fail open): %s", exc)

        provider = get_provider_for_tenant(tid)
        ok = provider.enviar_mensagem(numero, conteudo, formato=formato)
        if ok:
            _maybe_track_first_message_sent(tid)
        else:
            try:
                import quota as quota_mod
                quota_mod.refund_quota(tid, "wa_msgs_month", 1, reason="provider_send_failed")
            except Exception:
                pass
        return ok

    def simulate_presence(
        self,
        numero: str,
        presence: str = "composing",
        delay_seconds: float = 0.0,
    ) -> bool:
        """
        Simula presença humana (digitando / gravando áudio) no canal WhatsApp
        do tenant atual antes do envio efetivo.
        """
        tid = _current_tenant_id()
        try:
            provider = get_provider_for_tenant(tid)
            if hasattr(provider, "simulate_presence"):
                return provider.simulate_presence(
                    numero, presence=presence, delay_seconds=delay_seconds
                )
        except Exception as exc:
            logger.debug("[simulate_presence] falha silenciosa: %s", exc)
        return False


whatsapp_client = WhatsAppAPI()


def get_client_for_tenant(tenant_id: str):
    """Retorna o provider configurado para o tenant informado."""
    return get_provider_for_tenant(tenant_id)

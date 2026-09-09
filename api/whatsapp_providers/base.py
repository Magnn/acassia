"""
Interface base para providers WhatsApp.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ProviderMode(str, Enum):
    META_CLOUD = "meta_cloud"   # Meta WhatsApp Cloud API direta
    COEX = "coex"               # Coex BSP (parceiro Meta)
    EVOLUTION = "evolution"     # Evolution API (não oficial, QR-based)


class ProviderError(Exception):
    """Erro de provider — falha de auth, conexão, formato, etc."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        provider: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider = provider
        self.details = details or {}


@dataclass
class SendResult:
    """Resultado de envio de mensagem."""

    ok: bool
    message_id: Optional[str] = None
    raw: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class WhatsAppProvider(ABC):
    """
    Interface abstrata. Cada modo (meta_cloud/coex/evolution) implementa
    estes métodos com a lógica específica do backend.
    """

    mode: ProviderMode

    def __init__(self, tenant_id: str, config: dict[str, Any]):
        self.tenant_id = tenant_id
        self.config = config or {}

    @abstractmethod
    def enviar_mensagem(
        self,
        numero: str,
        conteudo: str,
        formato: str = "texto",
    ) -> bool:
        """
        Envia mensagem para ``numero`` no formato indicado.

        formato ∈ {"texto", "audio", "imagem", "video", "documento"}.
        Retorna True em sucesso, False em qualquer falha (loga internamente).

        Mantém retrocompat com o singleton ``WhatsAppAPI`` legado.
        """

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """
        Health-check do provider. Retorna ``{ok, mode, configured, hint?, details?}``.
        Usado pela UI pra saber se a conexão está pronta.
        """

    def send_message_result(
        self, numero: str, conteudo: str, formato: str = "texto", media_url: Optional[str] = None
    ) -> SendResult:
        """Contrato estruturado para novos consumidores, preservando o legado bool."""
        kwargs = {"formato": formato}
        if media_url is not None:
            kwargs["media_url"] = media_url
        try:
            ok = self.enviar_mensagem(numero, conteudo, **kwargs)
        except TypeError:
            ok = self.enviar_mensagem(numero, conteudo, formato=formato)
        message_id = None
        if self.mode == ProviderMode.META_CLOUD:
            try:
                from .meta_cloud import pop_last_wamid
                message_id = pop_last_wamid()
            except Exception:
                pass
        elif self.mode == ProviderMode.EVOLUTION:
            try:
                from .evolution import pop_last_evolution_msg_id
                message_id = pop_last_evolution_msg_id()
            except Exception:
                pass
        return SendResult(ok=bool(ok), message_id=message_id, error=None if ok else "envio_falhou")

    def test_connection(self, target_number: str) -> SendResult:
        """
        Manda uma mensagem-teste curta. Default: usa enviar_mensagem texto.
        Providers podem sobrescrever para fazer ping específico.
        """
        return self.send_message_result(
            target_number, "Teste de conexão Sibila — se você recebeu, a integração está OK.", formato="texto"
        )

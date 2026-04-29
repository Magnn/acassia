"""
Envio de mídia do tarô via WhatsApp Cloud API.

Sequência ritual herdada da `cigana_tarot/03_zara_sorteio_cartas.json`:
baralho fechado → pausa → 3 cartas com pausa entre cada (2s default).
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

from api.whatsapp_api import whatsapp_client
from flows.tarot.cartas import (
    Carta,
    sortear_3_cartas,
    url_baralho_fechado,
    url_imagem,
)

logger = logging.getLogger(__name__)

PAUSA_DEFAULT_S = 2.0  # paridade com o sub-workflow n8n


@dataclass
class ResultadoEnvio:
    carta: Carta
    sucesso: bool
    erro: Optional[str] = None


def enviar_baralho_fechado(numero: str, base_url: str) -> bool:
    """Envia foto ritualística "9 cartas de costas" antes da leitura."""
    url = url_baralho_fechado(base_url)
    ok = whatsapp_client.enviar_mensagem(numero, url, formato="imagem")
    logger.info("[tarot] baralho_fechado enviado=%s para %s", ok, numero)
    return ok


def enviar_tres_cartas(
    numero: str,
    cartas: list[Carta],
    base_url: str,
    pausa_segundos: float = PAUSA_DEFAULT_S,
) -> list[ResultadoEnvio]:
    """
    Envia 3 cartas em sequência com pausa entre cada.

    Args:
        numero: telefone E.164 (ex. "5511999999999").
        cartas: 3 cartas sorteadas.
        base_url: URL base do bucket Supabase Storage (ver ADR_004).
        pausa_segundos: pausa entre envios; default 2s espelha o ritmo n8n.

    Returns:
        list[ResultadoEnvio] na mesma ordem das cartas — uma falha não
        interrompe as próximas (resiliência).
    """
    if len(cartas) != 3:
        raise ValueError(f"Esperado 3 cartas, recebido {len(cartas)}")

    resultados: list[ResultadoEnvio] = []
    for i, carta in enumerate(cartas):
        url = url_imagem(carta, base_url)
        try:
            ok = whatsapp_client.enviar_mensagem(numero, url, formato="imagem")
            resultados.append(ResultadoEnvio(carta=carta, sucesso=ok))
            logger.info(
                "[tarot] carta %d/3 (%s) enviada=%s para %s",
                i + 1, carta.nome, ok, numero,
            )
        except Exception as exc:
            logger.exception("[tarot] erro ao enviar %s: %s", carta.nome, exc)
            resultados.append(ResultadoEnvio(carta=carta, sucesso=False, erro=str(exc)))

        # Pausa entre cartas, exceto após a última
        if i < len(cartas) - 1:
            time.sleep(pausa_segundos)

    return resultados


def sortear_e_enviar_3_cartas(
    numero: str,
    base_url: str,
    pausa_segundos: float = PAUSA_DEFAULT_S,
    seed: Optional[int] = None,
) -> tuple[list[Carta], list[ResultadoEnvio]]:
    """
    Helper que combina sorteio + envio numa chamada.
    Útil pro nó motor_ref do canvas (ADR_006) chamar como uma operação atômica
    e devolver as cartas pra IA usar na leitura.
    """
    cartas = sortear_3_cartas(seed=seed)
    resultados = enviar_tres_cartas(numero, cartas, base_url, pausa_segundos)
    return cartas, resultados

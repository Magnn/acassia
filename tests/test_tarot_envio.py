"""Testes do envio de mídia do tarô — flows.tarot.envio."""

from unittest.mock import patch

import pytest

from flows.tarot.cartas import sortear_3_cartas
from flows.tarot.envio import (
    enviar_baralho_fechado,
    enviar_tres_cartas,
    sortear_e_enviar_3_cartas,
)

BASE_URL = "https://abc.supabase.co/storage/v1/object/public/templates-public"
NUMERO = "5511999999999"


@pytest.fixture
def mock_whatsapp():
    """Patcha o singleton whatsapp_client dentro do módulo envio."""
    with patch("flows.tarot.envio.whatsapp_client") as mock:
        mock.enviar_mensagem.return_value = True
        yield mock


# ─── Baralho fechado ─────────────────────────────────────────────────────────

def test_enviar_baralho_fechado_chama_whatsapp_com_url_correta(mock_whatsapp):
    ok = enviar_baralho_fechado(NUMERO, BASE_URL)
    assert ok is True
    mock_whatsapp.enviar_mensagem.assert_called_once_with(
        NUMERO,
        f"{BASE_URL}/marselha/baralho_fechado.jpg",
        formato="imagem",
    )


def test_enviar_baralho_fechado_propaga_falha(mock_whatsapp):
    mock_whatsapp.enviar_mensagem.return_value = False
    assert enviar_baralho_fechado(NUMERO, BASE_URL) is False


# ─── 3 cartas ────────────────────────────────────────────────────────────────

def test_enviar_tres_cartas_faz_3_chamadas(mock_whatsapp):
    cartas = sortear_3_cartas(seed=42)
    resultados = enviar_tres_cartas(NUMERO, cartas, BASE_URL, pausa_segundos=0)
    assert len(resultados) == 3
    assert all(r.sucesso for r in resultados)
    assert mock_whatsapp.enviar_mensagem.call_count == 3


def test_enviar_tres_cartas_url_por_carta(mock_whatsapp):
    cartas = sortear_3_cartas(seed=0)
    enviar_tres_cartas(NUMERO, cartas, BASE_URL, pausa_segundos=0)

    chamadas = mock_whatsapp.enviar_mensagem.call_args_list
    for i, carta in enumerate(cartas):
        # call_args = (args, kwargs)
        args, kwargs = chamadas[i]
        assert args == (NUMERO, f"{BASE_URL}/marselha/{carta.slug}.jpg")
        assert kwargs == {"formato": "imagem"}


def test_enviar_tres_cartas_continua_apos_falha_de_uma(mock_whatsapp):
    cartas = sortear_3_cartas(seed=0)
    mock_whatsapp.enviar_mensagem.side_effect = [True, False, True]

    resultados = enviar_tres_cartas(NUMERO, cartas, BASE_URL, pausa_segundos=0)
    assert [r.sucesso for r in resultados] == [True, False, True]


def test_enviar_tres_cartas_captura_excecao(mock_whatsapp):
    cartas = sortear_3_cartas(seed=0)
    mock_whatsapp.enviar_mensagem.side_effect = [True, RuntimeError("network down"), True]

    resultados = enviar_tres_cartas(NUMERO, cartas, BASE_URL, pausa_segundos=0)
    assert [r.sucesso for r in resultados] == [True, False, True]
    assert resultados[1].erro is not None
    assert "network down" in resultados[1].erro


def test_enviar_tres_cartas_rejeita_qtd_diferente(mock_whatsapp):
    cartas = list(sortear_3_cartas(seed=0))[:2]
    with pytest.raises(ValueError, match="Esperado 3 cartas"):
        enviar_tres_cartas(NUMERO, cartas, BASE_URL, pausa_segundos=0)


def test_enviar_tres_cartas_pausa_2x_entre_3(mock_whatsapp):
    """Pausa acontece entre carta 1→2 e 2→3, mas não após a 3."""
    cartas = sortear_3_cartas(seed=0)

    with patch("flows.tarot.envio.time.sleep") as mock_sleep:
        enviar_tres_cartas(NUMERO, cartas, BASE_URL, pausa_segundos=2.0)

    assert mock_sleep.call_count == 2
    for call in mock_sleep.call_args_list:
        assert call.args[0] == 2.0


def test_enviar_tres_cartas_pausa_zero_nao_dorme(mock_whatsapp):
    cartas = sortear_3_cartas(seed=0)
    with patch("flows.tarot.envio.time.sleep") as mock_sleep:
        enviar_tres_cartas(NUMERO, cartas, BASE_URL, pausa_segundos=0)
    # Mesmo com pausa_segundos=0 ele chama time.sleep(0) — checa intenção, não otimização
    # Isso é um ok semântico; se preferir skip total seria outra decisão.
    assert mock_sleep.call_count == 2


# ─── Combinador sortear+enviar ───────────────────────────────────────────────

def test_sortear_e_enviar_combina(mock_whatsapp):
    cartas, resultados = sortear_e_enviar_3_cartas(
        NUMERO, BASE_URL, pausa_segundos=0, seed=99
    )
    assert len(cartas) == 3
    assert len(resultados) == 3
    assert mock_whatsapp.enviar_mensagem.call_count == 3
    # determinismo via seed
    cartas2, _ = sortear_e_enviar_3_cartas(
        NUMERO, BASE_URL, pausa_segundos=0, seed=99
    )
    assert [c.id for c in cartas] == [c.id for c in cartas2]

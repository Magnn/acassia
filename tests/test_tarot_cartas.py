"""Testes do módulo flows.tarot.cartas — invariantes do baralho e sorteio."""

import pytest

from flows.tarot.cartas import (
    BARALHO_MARSELHA,
    Carta,
    carta_por_id,
    carta_por_nome,
    sortear_3_cartas,
    url_baralho_fechado,
    url_imagem,
)


# ─── Invariantes de estrutura ────────────────────────────────────────────────

def test_baralho_tem_78_cartas():
    assert len(BARALHO_MARSELHA) == 78


def test_22_arcanos_maiores():
    maiores = [c for c in BARALHO_MARSELHA if c.arcano == "maior"]
    assert len(maiores) == 22


def test_56_arcanos_menores():
    menores = [c for c in BARALHO_MARSELHA if c.arcano == "menor"]
    assert len(menores) == 56


def test_4_naipes_com_14_cartas_cada():
    for naipe in ("copas", "espadas", "ouros", "bastoes"):
        cartas = [c for c in BARALHO_MARSELHA if c.naipe == naipe]
        assert len(cartas) == 14, f"naipe {naipe} tem {len(cartas)} cartas"


def test_arcanos_maiores_nao_tem_naipe():
    for c in BARALHO_MARSELHA:
        if c.arcano == "maior":
            assert c.naipe is None
        else:
            assert c.naipe is not None


def test_ids_unicos_e_sequenciais():
    ids = [c.id for c in BARALHO_MARSELHA]
    assert ids == list(range(78))


def test_slugs_unicos():
    slugs = [c.slug for c in BARALHO_MARSELHA]
    assert len(set(slugs)) == 78


def test_nomes_unicos():
    nomes = [c.nome for c in BARALHO_MARSELHA]
    assert len(set(nomes)) == 78


def test_arcanos_maiores_canonicos_presentes():
    nomes = {c.nome for c in BARALHO_MARSELHA if c.arcano == "maior"}
    obrigatorios = {"O Louco", "O Mago", "A Lua", "A Torre", "A Morte", "O Mundo"}
    assert obrigatorios.issubset(nomes)


def test_carta_eh_imutavel():
    # frozen=True deve impedir mutação acidental
    carta = BARALHO_MARSELHA[0]
    with pytest.raises(Exception):  # FrozenInstanceError ou AttributeError
        carta.nome = "outra coisa"  # type: ignore


# ─── Sorteio ─────────────────────────────────────────────────────────────────

def test_sortear_retorna_3_cartas_distintas():
    cartas = sortear_3_cartas()
    assert len(cartas) == 3
    assert len({c.id for c in cartas}) == 3


def test_sortear_com_seed_eh_deterministico():
    a = sortear_3_cartas(seed=42)
    b = sortear_3_cartas(seed=42)
    assert [c.id for c in a] == [c.id for c in b]


def test_sortear_seeds_diferentes_dao_resultados_diferentes():
    # Risco infinitesimal de colisão — usar seeds simples deterministicas
    a = sortear_3_cartas(seed=1)
    b = sortear_3_cartas(seed=2)
    assert [c.id for c in a] != [c.id for c in b]


def test_sortear_cobre_o_baralho_inteiro_com_iteracoes():
    # Em N sorteios suficientes, todas as cartas devem aparecer pelo menos 1x.
    vistas: set[int] = set()
    rng_seed = 0
    while len(vistas) < 78 and rng_seed < 5000:
        for c in sortear_3_cartas(seed=rng_seed):
            vistas.add(c.id)
        rng_seed += 1
    assert len(vistas) == 78, f"só vi {len(vistas)} cartas em 5000 sorteios"


# ─── URLs (Supabase Storage, ADR_004) ────────────────────────────────────────

def test_url_imagem_constrói_path_correto():
    carta = carta_por_id(16)  # A Torre
    base = "https://abc.supabase.co/storage/v1/object/public/templates-public"
    assert url_imagem(carta, base) == f"{base}/marselha/a_torre.jpg"


def test_url_imagem_normaliza_trailing_slash():
    carta = carta_por_id(0)  # O Louco
    assert url_imagem(carta, "https://abc.com/base/") == "https://abc.com/base/marselha/o_louco.jpg"


def test_url_baralho_fechado():
    base = "https://abc.com/x"
    assert url_baralho_fechado(base) == "https://abc.com/x/marselha/baralho_fechado.jpg"


# ─── Lookup ──────────────────────────────────────────────────────────────────

def test_carta_por_id_extremos():
    assert carta_por_id(0).nome == "O Louco"
    assert carta_por_id(21).nome == "O Mundo"
    assert carta_por_id(77).nome == "Rei de Bastões"


def test_carta_por_id_invalido_levanta():
    with pytest.raises(IndexError):
        carta_por_id(78)


def test_carta_por_nome_encontra_exato():
    carta = carta_por_nome("A Torre")
    assert carta is not None and carta.id == 16


def test_carta_por_nome_eh_case_insensitive():
    assert carta_por_nome("a torre") is not None
    assert carta_por_nome("A TORRE") is not None


def test_carta_por_nome_ignora_espaços_extras():
    assert carta_por_nome("  A Lua  ") is not None


def test_carta_por_nome_inexistente_retorna_none():
    assert carta_por_nome("Carta Inexistente") is None


def test_carta_por_nome_arcano_menor():
    carta = carta_por_nome("Dez de Espadas")
    assert carta is not None
    assert carta.arcano == "menor"
    assert carta.naipe == "espadas"


# ─── Slugs (sanidade — formato pra URL) ──────────────────────────────────────

def test_slugs_sao_lowercase_sem_acento():
    import re
    pattern = re.compile(r"^[a-z0-9_]+$")
    for c in BARALHO_MARSELHA:
        assert pattern.match(c.slug), f"slug inválido: {c.slug} ({c.nome})"

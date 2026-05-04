"""
Baralho de Tarot (Marselha) com 78 cartas + sorteio sem reposição.

URLs das imagens vêm do Supabase Storage seguindo o padrão de ADR_004.
A função ``url_imagem`` constrói a URL final a partir de uma base configurável
por tenant ou por env var.

Uso típico::

    from flows.tarot.cartas import sortear_3_cartas, url_imagem

    cartas = sortear_3_cartas()
    for carta in cartas:
        print(carta.nome, url_imagem(carta, base_url=BASE))
"""

from dataclasses import dataclass
from random import Random
from typing import Optional


@dataclass(frozen=True)
class Carta:
    id: int                       # 0-77, índice canônico no baralho
    nome: str                     # nome PT-BR ("A Torre")
    slug: str                     # slug pra URL ("a_torre")
    arcano: str                   # "maior" | "menor"
    naipe: Optional[str] = None   # "copas" | "espadas" | "ouros" | "bastoes" | None


# 22 Arcanos Maiores (ids 0-21) — ordem canônica de Marselha.
# Nomes seguem a tradução adotada na meumisterio_tarot original.
_ARCANOS_MAIORES: list[Carta] = [
    Carta(0,  "O Louco",          "o_louco",           "maior"),
    Carta(1,  "O Mago",           "o_mago",            "maior"),
    Carta(2,  "A Sacerdotisa",    "a_sacerdotisa",     "maior"),
    Carta(3,  "A Imperatriz",     "a_imperatriz",      "maior"),
    Carta(4,  "O Imperador",      "o_imperador",       "maior"),
    Carta(5,  "O Hierofante",     "o_hierofante",      "maior"),
    Carta(6,  "O Amante",         "o_amante",          "maior"),
    Carta(7,  "O Carro",          "o_carro",           "maior"),
    Carta(8,  "A Força",          "a_forca",           "maior"),
    Carta(9,  "O Eremita",        "o_eremita",         "maior"),
    Carta(10, "A Roda da Fortuna","a_roda_da_fortuna", "maior"),
    Carta(11, "A Justiça",        "a_justica",         "maior"),
    Carta(12, "O Enforcado",      "o_enforcado",       "maior"),
    Carta(13, "A Morte",          "a_morte",           "maior"),
    Carta(14, "A Temperança",     "a_temperanca",      "maior"),
    Carta(15, "O Diabo",          "o_diabo",           "maior"),
    Carta(16, "A Torre",          "a_torre",           "maior"),
    Carta(17, "A Estrela",        "a_estrela",         "maior"),
    Carta(18, "A Lua",            "a_lua",             "maior"),
    Carta(19, "O Sol",            "o_sol",             "maior"),
    Carta(20, "O Julgamento",     "o_julgamento",      "maior"),
    Carta(21, "O Mundo",          "o_mundo",           "maior"),
]


# 4 naipes em ordem canônica + nome PT-BR pra montar o "X de Naipe".
_NAIPES: list[tuple[str, str]] = [
    ("copas",    "Copas"),
    ("espadas",  "Espadas"),
    ("ouros",    "Ouros"),
    ("bastoes",  "Bastões"),
]

# 14 valores por naipe (Ás → Rei). Tupla = (nome PT-BR, slug).
_VALORES: list[tuple[str, str]] = [
    ("Ás",         "as"),
    ("Dois",       "dois"),
    ("Três",       "tres"),
    ("Quatro",     "quatro"),
    ("Cinco",      "cinco"),
    ("Seis",       "seis"),
    ("Sete",       "sete"),
    ("Oito",       "oito"),
    ("Nove",       "nove"),
    ("Dez",        "dez"),
    ("Pajem",      "pajem"),
    ("Cavaleiro",  "cavaleiro"),
    ("Rainha",     "rainha"),
    ("Rei",        "rei"),
]


def _gerar_arcanos_menores() -> list[Carta]:
    cartas: list[Carta] = []
    proximo_id = 22
    for naipe_slug, naipe_nome in _NAIPES:
        for valor_nome, valor_slug in _VALORES:
            cartas.append(Carta(
                id=proximo_id,
                nome=f"{valor_nome} de {naipe_nome}",
                slug=f"{valor_slug}_de_{naipe_slug}",
                arcano="menor",
                naipe=naipe_slug,
            ))
            proximo_id += 1
    return cartas


# Baralho final. Lista imutável de 78 cartas indexadas por id.
BARALHO_MARSELHA: tuple[Carta, ...] = tuple(_ARCANOS_MAIORES + _gerar_arcanos_menores())

# Invariante de integridade — falha cedo se alguém quebrar a estrutura.
assert len(BARALHO_MARSELHA) == 78
assert all(BARALHO_MARSELHA[i].id == i for i in range(78))


def sortear_3_cartas(seed: Optional[int] = None) -> list[Carta]:
    """
    Sorteia 3 cartas distintas (sem reposição) do baralho de Marselha.

    Args:
        seed: opcional. Se fornecido, sorteio é determinístico — útil pra
              testes e pra reprodutibilidade em auditoria de funil.
    """
    rng = Random(seed) if seed is not None else Random()
    return rng.sample(BARALHO_MARSELHA, 3)


def url_imagem(carta: Carta, base_url: str) -> str:
    """
    Constrói a URL pública da imagem da carta no Supabase Storage (ADR_004).

    Args:
        carta: a Carta sorteada.
        base_url: URL base do bucket público, ex.::

            https://{project}.supabase.co/storage/v1/object/public/templates-public

    Returns:
        URL completa, ex. ``.../templates-public/marselha/a_torre.jpg``.
    """
    return f"{base_url.rstrip('/')}/marselha/{carta.slug}.jpg"


def url_baralho_fechado(base_url: str) -> str:
    """URL da imagem ritualística "9 cartas de costas" (ver G3 do GAP doc)."""
    return f"{base_url.rstrip('/')}/marselha/baralho_fechado.jpg"


def carta_por_id(id: int) -> Carta:
    """Retorna a carta pelo id canônico (0-77). Levanta IndexError se inválido."""
    return BARALHO_MARSELHA[id]


def carta_por_nome(nome: str) -> Optional[Carta]:
    """
    Busca uma carta pelo nome (case-insensitive, ignora espaços extras).
    Retorna None se não encontrar — útil pra parsear nomes vindos do Gemini.
    """
    nome_norm = nome.strip().lower()
    for carta in BARALHO_MARSELHA:
        if carta.nome.lower() == nome_norm:
            return carta
    return None

"""
Numerologia Pitagorica (Frente 4.11 / 4.12).

Calcula 3 numeros principais:
    - Numero da Vida (life_path)         — soma da data de nascimento
    - Numero da Expressao (expression)    — soma de todas letras do nome completo
    - Numero da Alma (soul)               — soma das vogais do nome

Mestre numbers (11, 22, 33) NAO sao reduzidos.

Funcoes principais:
    life_path(birth_date) -> int
    expression(full_name) -> int
    soul(full_name) -> int
    interpret(numbers) -> dict com texto pra cada numero
"""

from __future__ import annotations

import unicodedata
from datetime import date as DateT


_PYTHAGOREAN = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8, "I": 9,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "O": 6, "P": 7, "Q": 8, "R": 9,
    "S": 1, "T": 2, "U": 3, "V": 4, "W": 5, "X": 6, "Y": 7, "Z": 8,
}

_VOWELS = set("AEIOU")  # Y depende de contexto; V1 conta como consoante


def _strip_accents(text: str) -> str:
    """Remove acentos e converte para uppercase ASCII."""
    nf = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nf if not unicodedata.combining(c)).upper()


def _reduce(n: int) -> int:
    """Reduz a 1 digito; preserva mestres 11/22/33."""
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(d) for d in str(n))
    return n


def life_path(birth_date: DateT) -> int:
    """Soma D + M + Y -> reduz."""
    digits = [int(c) for c in birth_date.strftime("%d%m%Y") if c.isdigit()]
    return _reduce(sum(digits))


def _name_value(full_name: str, vowels_only: bool) -> int:
    name = _strip_accents(full_name)
    total = 0
    for ch in name:
        if not ch.isalpha():
            continue
        is_vowel = ch in _VOWELS
        if vowels_only and not is_vowel:
            continue
        if not vowels_only and is_vowel:
            # Para expressao soma todas (vogais + consoantes); para soul so vogais
            pass
        total += _PYTHAGOREAN.get(ch, 0)
    return _reduce(total)


def expression(full_name: str) -> int:
    """Soma do valor numerologico de TODAS as letras."""
    return _name_value(full_name, vowels_only=False)


def soul(full_name: str) -> int:
    """Soma do valor numerologico das VOGAIS apenas."""
    return _name_value(full_name, vowels_only=True)


# ─── Significados ────────────────────────────────────────────────────


_LIFE_PATH_MEANINGS = {
    1: "Lider nato. Ciclo de pioneirismo, autonomia e construcao de algo proprio. Desafio: ego e impaciencia.",
    2: "Diplomata. Ciclo de parcerias, sensibilidade e cooperacao. Desafio: passividade e dependencia emocional.",
    3: "Comunicador criativo. Ciclo de expressao artistica, alegria e contato social. Desafio: dispersao.",
    4: "Construtor. Ciclo de disciplina, base solida e trabalho duro. Desafio: rigidez e medo de mudar.",
    5: "Aventureiro. Ciclo de mudancas, liberdade e novas experiencias. Desafio: instabilidade e excessos.",
    6: "Cuidador. Ciclo de familia, responsabilidade e amor. Desafio: peso emocional dos outros.",
    7: "Buscador espiritual. Ciclo de estudo, intuicao e introspeccao. Desafio: isolamento e ceticismo.",
    8: "Realizador material. Ciclo de poder, dinheiro e organizacao. Desafio: obsessao por resultados.",
    9: "Humanitario. Ciclo de servico, sabedoria e finalizacao de fases. Desafio: desapego e dor da perda.",
    11: "MESTRE 11 — intuitivo iluminado. Missao espiritual de inspirar. Sensibilidade extrema.",
    22: "MESTRE 22 — construtor de obras. Missao de materializar grande projeto que beneficia muitos.",
    33: "MESTRE 33 — mestre do amor universal. Missao de cura coletiva. Sacrificio pessoal.",
}

_EXPRESSION_MEANINGS = {
    1: "Talento de lideranca e iniciativa. Brilha quando comeca algo novo.",
    2: "Talento de mediacao. Brilha em times, parcerias e contextos delicados.",
    3: "Talento de comunicacao e arte. Brilha falando, escrevendo, criando.",
    4: "Talento de organizacao. Brilha estruturando processos e sistemas.",
    5: "Talento de adaptacao. Brilha em ambientes dinamicos e venda.",
    6: "Talento de cuidar. Brilha em saude, educacao e contextos familiares.",
    7: "Talento de pesquisa. Brilha analisando, ensinando, refletindo.",
    8: "Talento executivo. Brilha em negocios, financas e gestao.",
    9: "Talento humanitario. Brilha em causas sociais e arte com proposito.",
    11: "Talento intuitivo raro. Capta o invisivel; precisa aterrar.",
    22: "Talento de visionario pratico. Combina sonho grande com execucao.",
    33: "Talento de cura emocional. Toca pessoas profundamente.",
}

_SOUL_MEANINGS = {
    1: "Sua alma deseja independencia e ser reconhecida pelo proprio caminho.",
    2: "Sua alma deseja amor profundo, parceria e harmonia.",
    3: "Sua alma deseja expressao criativa e ser ouvida.",
    4: "Sua alma deseja seguranca, estabilidade e construir algo duradouro.",
    5: "Sua alma deseja liberdade, aventura e variedade.",
    6: "Sua alma deseja servir e ser amada por quem cuida.",
    7: "Sua alma deseja entender o misterio das coisas.",
    8: "Sua alma deseja prosperidade material e poder pessoal.",
    9: "Sua alma deseja deixar legado e ajudar a humanidade.",
    11: "Sua alma deseja inspirar espiritualmente os outros.",
    22: "Sua alma deseja deixar uma obra concreta de impacto.",
    33: "Sua alma deseja amar incondicionalmente e curar.",
}


def life_path_meaning(n: int) -> str:
    return _LIFE_PATH_MEANINGS.get(n, "Numero fora do padrao numerologico classico.")


def expression_meaning(n: int) -> str:
    return _EXPRESSION_MEANINGS.get(n, "")


def soul_meaning(n: int) -> str:
    return _SOUL_MEANINGS.get(n, "")


def compute_full(name: str | None, birth_date: DateT | None) -> dict:
    """Pacote completo. Campos podem ser None se input faltar."""
    out = {
        "life_path": None,
        "life_path_meaning": None,
        "expression": None,
        "expression_meaning": None,
        "soul": None,
        "soul_meaning": None,
    }
    if birth_date:
        lp = life_path(birth_date)
        out["life_path"] = lp
        out["life_path_meaning"] = life_path_meaning(lp)
    if name and name.strip():
        ex = expression(name)
        sl = soul(name)
        out["expression"] = ex
        out["expression_meaning"] = expression_meaning(ex)
        out["soul"] = sl
        out["soul_meaning"] = soul_meaning(sl)
    return out

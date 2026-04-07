"""
Camada central de politicas de conversa.

Objetivo:
- Padronizar deteccao de problema de entrega ("mensagem cortada/atropelo").
- Padronizar resposta curta de reparo entre nodes.
- Oferecer utilitarios de higiene de baloes para reduzir repeticao de regra.
"""

from __future__ import annotations

import re
from typing import Iterable, List

from schema import Acao

_RE_PROBLEMA_ENTREGA = re.compile(
    r"\b(cortad[ao]|incomplet[ao]|atropel|card|cart[aã]o\s+de\s+contato|"
    r"n[aã]o\s+deu\s+tempo|n[aã]o\s+deu\s+pra\s+ver|veio\s+quebrad[ao]|"
    r"n[aã]o\s+carreg|travou|bugou)\b",
    re.I,
)


def lead_reportou_problema_entrega(texto: str) -> bool:
    t = (texto or "").strip()
    if not t:
        return False
    return bool(_RE_PROBLEMA_ENTREGA.search(t))


def acoes_reparo_entrega_padrao(nome_vocativo: str) -> list[Acao]:
    nv = (nome_vocativo or "").strip() or "meu bem"
    return [
        Acao(
            tipo="text",
            conteudo=f"Obrigada por avisar, {nv}. Vou seguir mais devagar para voce acompanhar certinho.",
            metadata={"skip_gancho_final": True},
        ),
        Acao(tipo="delay", segundos=2),
        Acao(
            tipo="text",
            conteudo="Quando estiver tudo visivel ai, me manda so um *ok* que eu continuo.",
            metadata={"skip_gancho_final": True},
        ),
    ]


def deduplicar_textos(textos: Iterable[str], limite: int = 4) -> List[str]:
    out: List[str] = []
    vistos: set[str] = set()
    for tx in textos or []:
        t = " ".join(str(tx or "").split()).strip()
        if len(t) < 2:
            continue
        k = re.sub(r"\s+", " ", t.lower()).strip(" .!?…")
        if k in vistos:
            continue
        vistos.add(k)
        out.append(t)
        if len(out) >= limite:
            break
    return out


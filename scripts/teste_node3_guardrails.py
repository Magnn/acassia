from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config_cliente import CONFIG_CLIENTE
from schema import ContextoConversa
from flows.fase_1_saudacao import node_3_coleta_profunda


def _ctx(texto: str, meta: dict | None = None, tipo: str = "text") -> ContextoConversa:
    m = {"__config__": CONFIG_CLIENTE, "node3_estado": "inicial"}
    if meta:
        m.update(meta)
    return ContextoConversa(
        lead_id=999003,
        telefone="+5592999999999",
        node_atual="3_coleta_profunda",
        texto_recebido=texto,
        tipo_mensagem=tipo,
        metadata=m,
        nome_lead=str(m.get("nome_lead") or "Magno"),
        personalizer=None,
    )


def _txt(acoes):
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


def run() -> int:
    erros: list[str] = []

    c1 = _ctx("oi")
    a1, p1 = node_3_coleta_profunda.executar_v2(c1)
    if p1 != "3_coleta_profunda":
        erros.append("c1: deveria permanecer no node3 no inicio")
    if not _txt(a1):
        erros.append("c1: sem mensagens de orientação inicial")

    # camada desejo
    c2 = _ctx(
        "quero paz no amor",
        {"node3_estado": "aguardando_desejo", "universo_desejo": "amor_de_volta"},
    )
    a2, p2 = node_3_coleta_profunda.executar_v2(c2)
    if p2 != "3_coleta_profunda":
        erros.append("c2: não deveria sair do node3 nessa etapa")
    if any(len(t) > 210 for t in _txt(a2)):
        erros.append("c2: balão acima de 210 chars")

    # finalização para node4
    c3 = _ctx(
        "há meses e já tentei de tudo",
        {"node3_estado": "aguardando_aprofundamento", "desejo_declarado": "quero paz"},
    )
    a3, p3 = node_3_coleta_profunda.executar_v2(c3)
    if p3 != "4_instagram":
        erros.append("c3: deveria avançar para node4")
    if any(len(t) > 210 for t in _txt(a3)):
        erros.append("c3: balão acima de 210 chars")

    if erros:
        print("NODE3 GUARDRAILS FAIL")
        for e in erros:
            print("-", e)
        return 1
    print("NODE3 GUARDRAILS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())


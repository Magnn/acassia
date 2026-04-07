from __future__ import annotations

import os
import sys
from typing import Any, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config_cliente import CONFIG_CLIENTE
from schema import ContextoConversa
from flows.fase_3_oferta import node_8_oferta_principal as node8


def _ctx(lead_id: int, msg: str, meta_extra: Dict[str, Any] | None = None) -> ContextoConversa:
    meta: Dict[str, Any] = {
        "__config__": CONFIG_CLIENTE,
        "resumo_dor": "saudade e ansiedade desde a separação",
        "tempo_sofrimento": "3 meses",
        "nome_pessoa_envolvida": "Ana",
        "tempo_exato": "3 meses",
        "evento_gatilho": "bloqueio no WhatsApp",
        "desejo_declarado": "quero ela de volta",
        "genero_lead": "masculino",
    }
    if meta_extra:
        meta.update(meta_extra)
    return ContextoConversa(
        lead_id=lead_id,
        telefone=f"559299999{lead_id:04d}",
        node_atual="8_oferta_principal",
        texto_recebido=msg,
        metadata=meta,
        nome_lead="Magno",
        personalizer=None,  # força fallback para teste determinístico
    )


def _resumo_acoes(acoes):
    textos = [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text" and (a.conteudo or "").strip()]
    if not textos:
        return "(sem texto)"
    return " | ".join(textos[:2])


def main():
    print("=== Teste A/B/C ticket inicial ===")
    for lead_id in (1, 2, 3):
        c = _ctx(lead_id, "sim")
        acoes, prox = node8.executar_v2(c)
        print(
            f"lead={lead_id} ticket_inicial={c.metadata.get('node8_ticket_inicial')} "
            f"ticket_atual={c.metadata.get('node8_ticket_atual')} prox={prox}"
        )
        print("  ", _resumo_acoes(acoes))

    print("\n=== Teste negociação (130 -> 100 -> pergunta -> 50) ===")
    c = _ctx(3, "sim")  # lead_id=3 cai em bucket 130
    node8.executar_v2(c)

    c.texto_recebido = "tá caro, não tenho esse valor"
    acoes, _ = node8.executar_v2(c)
    print(f"passo1 ticket_atual={c.metadata.get('node8_ticket_atual')}")
    print("  ", _resumo_acoes(acoes))

    c.texto_recebido = "não consigo 100"
    acoes, _ = node8.executar_v2(c)
    print(f"passo2 ticket_atual={c.metadata.get('node8_ticket_atual')} insist={c.metadata.get('node8_neg_insist_count')}")
    print("  ", _resumo_acoes(acoes))

    c.texto_recebido = "só tenho 50"
    acoes, _ = node8.executar_v2(c)
    print(
        f"passo3 ticket_atual={c.metadata.get('node8_ticket_atual')} "
        f"restante_pendente={c.metadata.get('node8_pagamento_restante_pendente')}"
    )
    print("  ", _resumo_acoes(acoes))

    print("\n=== Teste negociação (65 -> 40 -> 30) ===")
    c2 = _ctx(2, "sim")  # lead_id=2 cai em bucket 65
    node8.executar_v2(c2)

    c2.texto_recebido = "não tenho 65"
    acoes, _ = node8.executar_v2(c2)
    print(f"passo1 ticket_atual={c2.metadata.get('node8_ticket_atual')}")
    print("  ", _resumo_acoes(acoes))

    c2.texto_recebido = "só tenho 30"
    acoes, _ = node8.executar_v2(c2)
    print(
        f"passo2 ticket_atual={c2.metadata.get('node8_ticket_atual')} "
        f"restante_pendente={c2.metadata.get('node8_pagamento_restante_pendente')}"
    )
    print("  ", _resumo_acoes(acoes))


if __name__ == "__main__":
    main()


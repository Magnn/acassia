from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config_cliente import CONFIG_CLIENTE
from schema import ContextoConversa
from flows.fase_1_saudacao import node_1_apresentacao


def _ctx(texto: str) -> ContextoConversa:
    return ContextoConversa(
        lead_id=999001,
        telefone="+5592999999999",
        node_atual="1_apresentacao",
        texto_recebido=texto,
        metadata={"__config__": CONFIG_CLIENTE},
        personalizer=None,  # força fallback estável
    )


def _textos(acoes):
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


def run() -> int:
    cenarios = {
        "oi": _ctx("oi"),
        "preco": _ctx("qual o valor?"),
        "duvida_pergunta": _ctx("como funciona?"),
        "amor": _ctx("quero trazer meu ex de volta"),
        "nome": _ctx("me chamo Magno"),
        "nome_meu_nome_e": _ctx("meu nome é Ana"),
    }
    erros = []
    for nome, ctx in cenarios.items():
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        txt = _textos(acoes)
        if not txt:
            erros.append(f"{nome}: sem baloes de texto")
            continue
        if len(txt) > 4:
            erros.append(f"{nome}: mais de 4 baloes ({len(txt)})")
        if any(len(t) > 210 for t in txt):
            erros.append(f"{nome}: balao acima de 210 chars")
        if prox not in ("2_salvar_contato", "3_coleta_profunda"):
            erros.append(f"{nome}: proximo node invalido {prox}")
        if nome == "oi":
            if len(txt) > 4:
                erros.append("oi: node1 deve manter no maximo 4 baloes")
            joined = " ".join(t.lower() for t in txt)
            if "última vaga" not in joined and "vaga gratuita" not in joined and "consulta inicial" not in joined:
                erros.append("oi: perdeu menção de vaga/consulta inicial")
            if "como você se chama" not in joined and "me diz como você se chama" not in joined:
                erros.append("oi: perdeu pergunta de nome")
        if nome in ("preco", "duvida_pergunta"):
            joined = " ".join(t.lower() for t in txt)
            if "como você se chama" not in joined and "me diz como você se chama" not in joined:
                erros.append(f"{nome}: perdeu pergunta de nome no fechamento do checklist")
    if erros:
        print("NODE1 GUARDRAILS FAIL")
        for e in erros:
            print("-", e)
        return 1
    print("NODE1 GUARDRAILS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())


from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config_cliente import CONFIG_CLIENTE
from schema import ContextoConversa
from flows.fase_1_saudacao import node_1_apresentacao, node_2_salvar_contato, node_3_coleta_profunda
from flows.funnel_gates import snapshot_fase1_coleta


def _ctx(node: str, texto: str, nome: str = "", meta: Dict[str, Any] | None = None, tipo: str = "text") -> ContextoConversa:
    m = {"__config__": CONFIG_CLIENTE}
    if meta:
        m.update(meta)
    return ContextoConversa(
        lead_id=880000,
        telefone="+5592999999999",
        node_atual=node,
        texto_recebido=texto,
        tipo_mensagem=tipo,
        nome_lead=nome,
        metadata=m,
        personalizer=None,
    )


def _textos(acoes: List[Any]) -> List[str]:
    return [str(getattr(a, "conteudo", "") or "") for a in acoes if getattr(a, "tipo", "") == "text"]


def _validar_regras_basicas(label: str, acoes: List[Any], erros: List[str]) -> None:
    textos = _textos(acoes)
    if not textos:
        erros.append(f"{label}: sem mensagens de texto")
        return
    for t in textos:
        if len(t) > 230:
            erros.append(f"{label}: balão > 230 chars")


def run() -> int:
    cenarios = [
        {
            "id": "L01_entrada_curta_sem_nome",
            "run": lambda: node_1_apresentacao.executar_v2(_ctx("1_apresentacao", "oi")),
            "expect_next_in": {"2_salvar_contato", "3_coleta_profunda"},
        },
        {
            "id": "L02_nome_claro",
            "run": lambda: node_1_apresentacao.executar_v2(_ctx("1_apresentacao", "me chamo Bruno", nome="Bruno")),
            "expect_next_in": {"2_salvar_contato", "3_coleta_profunda"},
        },
        {
            "id": "L03_nome_placeholder_sim",
            "run": lambda: node_1_apresentacao.executar_v2(_ctx("1_apresentacao", "sim", nome="sim")),
            "expect_next_in": {"2_salvar_contato", "3_coleta_profunda"},
        },
        {
            "id": "L04_burst_completo_sem_node2",
            "run": lambda: node_1_apresentacao.executar_v2(
                _ctx(
                    "1_apresentacao",
                    "já salvei, mandei a foto e dói muito desde 2023",
                    nome="Marina",
                    meta={
                        "lead_contato_salvo_declarado": True,
                        "foto_recebida": True,
                        "desabafo_recebido": True,
                    },
                )
            ),
            "expect_next_in": {"3_coleta_profunda"},
        },
        {
            "id": "L05_node2_fast_track_contato_ok",
            "run": lambda: node_2_salvar_contato.executar_v2(
                _ctx(
                    "2_salvar_contato",
                    "já salvei aqui",
                    nome="Rafa",
                    meta={"lead_contato_salvo_declarado": True},
                )
            ),
            "expect_next_in": {"3_coleta_profunda"},
        },
        {
            "id": "L06_node2_reenvio_vcard",
            "run": lambda: node_2_salvar_contato.executar_v2(_ctx("2_salvar_contato", "não achei seu contato", nome="Bia")),
            "expect_next_in": {"2_salvar_contato"},
        },
        {
            "id": "L07_node3_sem_foto",
            "run": lambda: node_3_coleta_profunda.executar_v2(
                _ctx(
                    "3_coleta_profunda",
                    "quero resolver isso no amor",
                    nome="Duda",
                    meta={"node3_estado": "inicial", "desabafo_recebido": True, "lead_contato_salvo_declarado": True},
                )
            ),
            "expect_next_in": {"3_coleta_profunda"},
        },
        {
            "id": "L08_node3_sem_desabafo",
            "run": lambda: node_3_coleta_profunda.executar_v2(
                _ctx(
                    "3_coleta_profunda",
                    "mandei a foto",
                    nome="Nina",
                    meta={"node3_estado": "inicial", "foto_recebida": True, "lead_contato_salvo_declarado": True},
                )
            ),
            "expect_next_in": {"3_coleta_profunda"},
        },
        {
            "id": "L09_node3_com_foto_e_desabafo",
            "run": lambda: node_3_coleta_profunda.executar_v2(
                _ctx(
                    "3_coleta_profunda",
                    "faz 2 anos que sofro e tentei de tudo",
                    nome="Leandro",
                    meta={
                        "node3_estado": "aguardando_aprofundamento",
                        "foto_recebida": True,
                        "desabafo_recebido": True,
                        "lead_contato_salvo_declarado": True,
                        "desejo_declarado": "quero paz no amor",
                    },
                )
            ),
            "expect_next_in": {"4_instagram"},
        },
        {
            "id": "L10_node3_feedback_entrega_cortada",
            "run": lambda: node_3_coleta_profunda.executar_v2(
                _ctx("3_coleta_profunda", "a mensagem veio cortada", nome="Cris", meta={"node3_estado": "inicial"})
            ),
            "expect_next_in": {"3_coleta_profunda"},
        },
        {
            "id": "L11_texto_ruido_grande",
            "run": lambda: node_1_apresentacao.executar_v2(
                _ctx("1_apresentacao", "kkkk " * 50 + "quero ajuda no amor", nome="")
            ),
            "expect_next_in": {"2_salvar_contato", "3_coleta_profunda"},
        },
        {
            "id": "L12_snapshot_consistencia_fase1",
            "run": lambda: (
                [],
                "snapshot",
                snapshot_fase1_coleta(
                    {"foto_recebida": True, "desabafo_recebido": True, "lead_contato_salvo_declarado": True},
                    "",
                    "já salvei",
                ),
            ),
            "expect_next_in": {"snapshot"},
        },
    ]

    erros: List[str] = []
    rel: List[Dict[str, Any]] = []
    for c in cenarios:
        out = c["run"]()
        extra = None
        if isinstance(out, tuple) and len(out) == 3:
            acoes, prox, extra = out
        else:
            acoes, prox = out
        if prox not in c["expect_next_in"]:
            erros.append(f"{c['id']}: próximo node inesperado: {prox}")
        if prox != "snapshot":
            _validar_regras_basicas(c["id"], list(acoes or []), erros)
        rel.append(
            {
                "id": c["id"],
                "next": prox,
                "text_count": len(_textos(list(acoes or []))),
                "snapshot": extra if isinstance(extra, dict) else None,
            }
        )

    print(json.dumps({"total": len(cenarios), "errors": len(erros), "results": rel}, ensure_ascii=False, indent=2))
    if erros:
        print("\nFASE1 FANTASMAS FAIL")
        for e in erros:
            print("-", e)
        return 1
    print("\nFASE1 FANTASMAS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())


from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config_cliente import CONFIG_CLIENTE
from schema import Acao, ContextoConversa

from flows.fase_1_saudacao import node_1_apresentacao, node_2_salvar_contato, node_4_instagram
from flows.fase_2_leitura import node_5_processa_leitura, node_6_atencao_dinamica, node_7_interesse_desejo
from flows.fase_3_oferta import node_8_oferta_principal, node_9_recuperacao


def _ctx(node_atual: str, texto: str, meta: Dict[str, Any] | None = None) -> ContextoConversa:
    metadata = dict(meta or {})
    metadata["__config__"] = CONFIG_CLIENTE
    return ContextoConversa(
        lead_id=123456,
        telefone="+5592999999999",
        node_atual=node_atual,
        texto_recebido=texto,
        historico=[],
        nome_lead=metadata.get("nome_lead", "Magno"),
        metadata=metadata,
        personalizer=None,
        intencao="padrao",
        sentimento="padrao",
    )


def _has_text(acoes: List[Acao], trecho: str) -> bool:
    low = (trecho or "").lower()
    for a in acoes:
        if a.tipo != "text":
            continue
        if low in (a.conteudo or "").lower():
            return True
    return False


def _run_case(nome: str, fn) -> Dict[str, Any]:
    try:
        ok, detalhes = fn()
        return {"case": nome, "ok": bool(ok), "details": detalhes}
    except Exception as exc:
        return {"case": nome, "ok": False, "details": f"erro: {exc}"}


def case_reparo_entrega_nodes() -> Tuple[bool, str]:
    nodes = [
        ("2_salvar_contato", node_2_salvar_contato.executar_v2),
        ("4_instagram", node_4_instagram.executar_v2),
        ("5_processa_leitura", node_5_processa_leitura.executar_v2),
        ("6_atencao_dinamica", node_6_atencao_dinamica.executar_v2),
        ("7_interesse_desejo", node_7_interesse_desejo.executar_v2),
        ("8_oferta_principal", node_8_oferta_principal.executar_v2),
    ]
    falhas: List[str] = []
    for node_id, fn in nodes:
        ctx = _ctx(node_id, "mensagem cortada e tá atropelando")
        acoes, prox = fn(ctx)
        if prox != node_id:
            falhas.append(f"{node_id}: deveria permanecer no node")
            continue
        if not _has_text(acoes, "ok"):
            falhas.append(f"{node_id}: reparo sem pedido de ok")
    if falhas:
        return False, "; ".join(falhas)
    return True, "todos os nodes responderam com reparo padrao"


def case_node8_firmo_gate() -> Tuple[bool, str]:
    ctx = _ctx(
        "8_oferta_principal",
        "ok",
        {
            "nome_lead": "Magno",
            "node8_fase": "esperando_firmo",
            "node8_ticket_inicial": 100,
            "node8_ticket_atual": 100,
        },
    )
    acoes, prox = node_8_oferta_principal.executar_v2(ctx)
    if prox != "8_oferta_principal":
        return False, "node8 deveria continuar aguardando FIRMO"
    if not _has_text(acoes, "FIRMO"):
        return False, "node8 nao reforcou confirmacao FIRMO"
    return True, "gate FIRMO ok"


def case_node8_link_pos_firmo() -> Tuple[bool, str]:
    ctx = _ctx(
        "8_oferta_principal",
        "firmo",
        {
            "nome_lead": "Magno",
            "node8_fase": "esperando_firmo",
            "node8_ticket_inicial": 65,
            "node8_ticket_atual": 65,
        },
    )
    acoes, prox = node_8_oferta_principal.executar_v2(ctx)
    if prox != "aguardando_pagamento":
        return False, "node8 deveria ir para aguardando_pagamento apos FIRMO"
    if not any(a.tipo == "text" and "http" in (a.conteudo or "").lower() for a in acoes):
        return False, "node8 nao enviou link apos FIRMO"
    return True, "link liberado corretamente apos FIRMO"


def case_node5_tentativas_previas() -> Tuple[bool, str]:
    ctx = _ctx(
        "5_processa_leitura",
        "estou sofrendo com isso tem tempo e preciso de ajuda",
        {"nome_lead": "Magno"},
    )
    acoes, prox = node_5_processa_leitura.executar_v2(ctx)
    pediu = _has_text(acoes, "antes de eu fechar sua leitura") or _has_text(acoes, "ja tentou")
    if pediu and prox == "5_processa_leitura":
        return True, "coleta de tentativas previa ok"
    if str(ctx.metadata.get("node5_tentativas_previas") or "").strip():
        return True, "node5 capturou tentativa previa no proprio texto do lead"
    return False, "node5 nao coletou nem pediu tentativas previas"


def case_node1_saida_saudacao() -> Tuple[bool, str]:
    ctx = _ctx("1_apresentacao", "oi")
    acoes, prox = node_1_apresentacao.executar_v2(ctx)
    if prox != "2_salvar_contato":
        return False, "node1 deveria encaminhar para node2"
    txt = [a.conteudo for a in acoes if a.tipo == "text"]
    if not txt:
        return False, "node1 sem texto de saudacao"
    return True, f"node1 gerou {len(txt)} baloes"


def case_node9_tentativas() -> Tuple[bool, str]:
    ok_all = True
    for t in (1, 2, 3):
        ctx = _ctx("9_recuperacao", "...")
        acoes, prox = node_9_recuperacao.executar_v2(ctx, tentativa=t)
        if not acoes or prox not in ("aguardando_pagamento", "fluxo_encerrado"):
            ok_all = False
    if not ok_all:
        return False, "node9 nao respondeu corretamente em alguma tentativa"
    return True, "node9 respondeu nas 3 tentativas"


def main() -> int:
    casos = [
        ("saudacao", "node1_saida_saudacao", case_node1_saida_saudacao),
        ("coleta", "node5_tentativas_previas", case_node5_tentativas_previas),
        ("resiliencia_entrega", "reparo_entrega_nodes", case_reparo_entrega_nodes),
        ("oferta", "node8_firmo_gate", case_node8_firmo_gate),
        ("oferta", "node8_link_pos_firmo", case_node8_link_pos_firmo),
        ("recuperacao", "node9_tentativas", case_node9_tentativas),
    ]
    resultados = []
    por_stage: Dict[str, Dict[str, int | float]] = {}
    for stage, nome, fn in casos:
        r = _run_case(nome, fn)
        r["stage"] = stage
        resultados.append(r)
        st = por_stage.setdefault(stage, {"total": 0, "passed": 0, "failed": 0, "score": 0.0})
        st["total"] = int(st["total"]) + 1
        if r["ok"]:
            st["passed"] = int(st["passed"]) + 1
        else:
            st["failed"] = int(st["failed"]) + 1
    for stage, st in por_stage.items():
        tot = int(st["total"]) or 1
        st["score"] = round((int(st["passed"]) / tot) * 100, 2)
    aprovados = sum(1 for r in resultados if r["ok"])
    total = len(resultados)
    score = round((aprovados / total) * 100, 2) if total else 0.0

    rel = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": aprovados,
        "failed": total - aprovados,
        "score": score,
        "score_by_stage": por_stage,
        "results": resultados,
    }

    out_dir = Path(__file__).resolve().parent / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "simular_funil_e2e_report.json"
    out_file.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(rel, ensure_ascii=False, indent=2))
    if score < 100:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


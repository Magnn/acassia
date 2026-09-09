from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


CHECKS: dict[str, list[str]] = {
    "conversation_policy.py": [
        "def lead_reportou_problema_entrega",
        "def acoes_reparo_entrega_padrao",
    ],
    "inbox_manager.py": [
        "class LeadInboxManager",
        "_re_confirmacao_curta",
        "_re_feedback_entrega",
        "Grace pós-texto",
    ],
    "engine.py": [
        "def _lead_reportou_problema_entrega",
        "def _acoes_reparo_entrega",
        "def _ultima_fala_do_bot_e_pergunta",
        "if prox != \"6_atencao_dinamica\"",
        "if self._ultima_fala_do_bot_e_pergunta(res or [])",
        "Balão suprimido por truncamento irreparável",
        "elif acao.tipo == \"vcard\":",
        "if ultimo_tipo_enviado == \"text\":",
        "event=node_exec_timing",
        "Node lento: node=",
        "ctx.metadata[\"node_atual_exec\"]",
    ],
    "personalizer.py": [
        "_aplicar_guardrails_custo",
        "_registrar_consumo_ia",
        "_ia_tokens_gastos_aprox",
    ],
    "flows/fase_2_leitura/node_5_processa_leitura.py": [
        "node5_tentativas_previas",
        "node5_dado_concreto",
        "node5_coleta_tentativas",
        "me conta em uma frase o que você já tentou",
        "_RE_PROBLEMA_ENTREGA",
        "node5_reparo_entrega",
    ],
    "flows/fase_1_saudacao/node_1_apresentacao.py": [
        "_sanear_baloes_saida_node1",
        "_encurtar_balao_node1",
        "_deduplicar_baloes_node1",
        "_aplicar_cap_hierarquico_node1",
        "_ajustar_abertura_curta_node1",
    ],
    "flows/fase_1_saudacao/node_2_salvar_contato.py": [
        "_RE_PROBLEMA_ENTREGA",
        "_RE_OBJECAO_CARD",
        "_sanear_textos_node2",
        "_normalizar_acoes_texto_node2",
        "node2_reparo_entrega",
        "node2_reenvio_card",
        "node2_fast_track_ok",
    ],
    "flows/fase_1_saudacao/node_3_coleta_profunda.py": [
        "_normalizar_acoes_texto_node3",
        "_encurtar_balao_node3",
        "_MAX_CHARS_BALAO_NODE3",
    ],
    "flows/fase_1_saudacao/node_4_instagram.py": [
        "_RE_PROBLEMA_ENTREGA",
        "node4_reparo_entrega",
        "_RE_TEXTO_LINK_IG_QUEBRADO",
    ],
    "flows/fase_2_leitura/node_6_atencao_dinamica.py": [
        "dado_concreto",
        "BLOCO 4 e BLOCO 5 devem citar",
        "Bloco 12: Pergunta visceral",
        "_RE_PROBLEMA_ENTREGA",
        "node6_reparo_entrega",
    ],
    "flows/fase_2_leitura/node_7_interesse_desejo.py": [
        "def _reacao_curta_ao_input",
        "if blocos_gerados:",
        "Reaja à última mensagem",
        "_RE_PROBLEMA_ENTREGA",
        "node7_reparo_entrega",
    ],
    "flows/fase_3_oferta/node_8_oferta_principal.py": [
        "def _eh_bloco_preco",
        "def _ponte_emocional_preco",
        "node8_neg_insist_count",
        "meta[\"node8_fase\"] = \"esperando_firmo\"",
        "escreve *FIRMO*",
        "_RE_PROBLEMA_ENTREGA",
        "node8_reparo_entrega",
    ],
    "flows/fase_3_oferta/node_9_recuperacao.py": [
        "tentativa == 1",
        "tentativa == 2",
        "tentativa == 3",
        "node9_recuperacao_t",
    ],
    "scripts/simular_funil_e2e.py": [
        "case_reparo_entrega_nodes",
        "case_node8_firmo_gate",
        "score_by_stage",
        "simular_funil_e2e_report.json",
    ],
    "scripts/release_gate_funil.py": [
        "release_gate_report.json",
        "release_gate_report.md",
        "scripts/verificar_guardrails_funil.py",
        "scripts/simular_funil_e2e.py",
    ],
    "scripts/custo_ia_por_lead.py": [
        "_ia_tokens_gastos_aprox",
        "custo_ia_por_lead_report.json",
        "orcamento_tokens_por_lead",
    ],
    "scripts/teste_node1_guardrails.py": [
        "NODE1 GUARDRAILS OK",
        "node1 deve manter no maximo 4 baloes",
    ],
    "scripts/teste_node2_guardrails.py": [
        "NODE2 GUARDRAILS OK",
        "mais de uma pergunta no mesmo turno",
    ],
    "scripts/teste_node3_guardrails.py": [
        "NODE3 GUARDRAILS OK",
        "deveria avançar para node4",
    ],
}


def main() -> int:
    missing: list[str] = []
    for rel, needles in CHECKS.items():
        path = ROOT / rel
        if not path.exists():
            missing.append(f"{rel}: arquivo nao encontrado")
            continue
        txt = path.read_text(encoding="utf-8", errors="replace")
        for n in needles:
            if n not in txt:
                missing.append(f"{rel}: faltando '{n}'")

    if missing:
        print("GUARDRAILS FAIL")
        for m in missing:
            print(f"- {m}")
        return 1

    print("GUARDRAILS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


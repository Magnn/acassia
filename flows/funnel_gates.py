"""
flows/funnel_gates.py — predicados centrais da fase 1 (nome, contato, foto, desabafo).

Objetivo: uma única fonte de verdade para regras que antes estavam só no sniffer (engine)
e espalhadas nos nodes. Sniffer continua a *escrever* metadata; aqui *lê-se* de forma
consistente para burst, logs e testes.

Ver também: docs/FUNIL_MATRIZ_OBRIGATORIOS.md
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# Alinhado a copy_sanitizer.extrair_evidencias_conversa (nome_ok) e node_1.
PLACEHOLDER_NOMES = frozenset({"meu bem", "meu anjo", "minha estrela"})

# Valor default do vocativo quando o primeiro nome ainda não foi extraído (copy).
VOCATIVO_SEM_NOME = "meu bem"


def nome_eh_placeholder(nome: str) -> bool:
    """True se ainda não há primeiro nome utilizável (vazio ou placeholder de vocativo)."""
    n = (nome or "").strip().lower()
    if not n:
        return True
    return n in PLACEHOLDER_NOMES


def meta_tem_foto(meta: Optional[Mapping[str, Any]]) -> bool:
    return bool((meta or {}).get("foto_recebida"))


def meta_tem_desabafo(meta: Optional[Mapping[str, Any]]) -> bool:
    return bool((meta or {}).get("desabafo_recebido"))


def meta_declarou_contato_salvo(meta: Optional[Mapping[str, Any]]) -> bool:
    return bool((meta or {}).get("lead_contato_salvo_declarado"))


def texto_declara_contato_salvo(blob_texto_usuario: str) -> bool:
    """Delega para o mesmo detector do node 2 (evita divergência de regex)."""
    from flows.fase_1_saudacao.node_2_salvar_contato import texto_indica_contato_salvo

    return texto_indica_contato_salvo(blob_texto_usuario or "")


def contato_salvo_ou_declarado(
    meta: Optional[Mapping[str, Any]],
    blob_texto_usuario: str,
) -> bool:
    return meta_declarou_contato_salvo(meta) or texto_declara_contato_salvo(blob_texto_usuario)


def pode_burst_coleta_sem_node2(
    meta: Optional[Mapping[str, Any]],
    nome_lead: str,
    blob_texto_usuario: str,
) -> bool:
    """
    Espelha a regra do node 1 (burst inicial → pula node 2, vai à coleta).
    Só True quando nome + (contato declarado) + foto + desabafo já estão satisfeitos.
    """
    if nome_eh_placeholder(nome_lead):
        return False
    if not contato_salvo_ou_declarado(meta, blob_texto_usuario):
        return False
    if not meta_tem_foto(meta):
        return False
    if not meta_tem_desabafo(meta):
        return False
    return True


def pendencias_fase1(
    meta: Optional[Mapping[str, Any]],
    nome_lead: str,
    blob_texto_usuario: str,
) -> Dict[str, bool]:
    """
    Mapa explícito do que ainda falta para o burst completo (referência humana + testes).
    """
    return {
        "falta_nome": nome_eh_placeholder(nome_lead),
        "falta_contato_salvo": not contato_salvo_ou_declarado(meta, blob_texto_usuario),
        "falta_foto": not meta_tem_foto(meta),
        "falta_desabafo": not meta_tem_desabafo(meta),
    }


def snapshot_fase1_coleta(
    meta: Optional[Mapping[str, Any]],
    nome_lead: str,
    blob_texto_usuario: str,
) -> Dict[str, Any]:
    """Telemetria compacta (engine / auditoria)."""
    pend = pendencias_fase1(meta, nome_lead, blob_texto_usuario)
    return {
        "nome_util_ok": not pend["falta_nome"],
        "contato_ok": not pend["falta_contato_salvo"],
        "foto_ok": not pend["falta_foto"],
        "desabafo_ok": not pend["falta_desabafo"],
        "burst_elegivel": pode_burst_coleta_sem_node2(meta, nome_lead, blob_texto_usuario),
        "pendencias": [k for k, v in pend.items() if v],
    }

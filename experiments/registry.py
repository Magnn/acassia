"""
Registro de experimentos — hipótese, métrica alvo e status.
Não executa teste automaticamente; serve para alinhar time copy/dev e auditoria.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# id -> {titulo, hipotese, metrica, node_alvo, status, notas}
_EXPERIMENTOS: Dict[str, Dict[str, Any]] = {
    "exp001_multi_pergunta_prioridade": {
        "titulo": "Prioridade última mensagem + várias dúvidas",
        "hipotese": "Responder todos os tópicos antes do roteiro reduz abandono entre 3→4.",
        "metrica": "transições funnel.node_transition de→para 4_instagram; tempo médio no node 3",
        "node_alvo": "3_coleta_profunda",
        "status": "ativo_no_codigo",
        "notas": "stage_intel + Personalizer (2026)",
    },
    "exp002_ponte_preco": {
        "titulo": "Biblioteca de pontes (preço fora da ordem)",
        "hipotese": "Ponte configurável reduz objeção prematura sem quebrar rapport.",
        "metrica": "preco_prematuro implícito em stage_intel + conversão em 8",
        "node_alvo": "1-7",
        "status": "configuravel",
        "notas": "config pontes_copy",
    },
}


def listar_experimentos() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for eid, data in _EXPERIMENTOS.items():
        row = {"id": eid, **data}
        out.append(row)
    return out


def obter_experimento(exp_id: str) -> Optional[Dict[str, Any]]:
    data = _EXPERIMENTOS.get(exp_id)
    if not data:
        return None
    return {"id": exp_id, **data}

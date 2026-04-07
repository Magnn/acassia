"""
Auditoria de personalização/copy ponta a ponta.

Objetivo:
- Medir se a conversa foi realmente personalizada por lead (não só "fluxo padrão").
- Gerar score explicável (0-100) por conversa com sinais acionáveis.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from db.models import Lead, Mensagem

_RE_WORD = re.compile(r"[a-zà-ú]{3,}", re.I)
_STOPWORDS = {
    "para",
    "com",
    "sem",
    "sobre",
    "isso",
    "essa",
    "esse",
    "como",
    "mais",
    "muito",
    "pouco",
    "hoje",
    "amanha",
    "ontem",
    "aqui",
    "você",
    "voce",
    "meu",
    "minha",
    "seu",
    "sua",
    "uma",
    "uns",
    "umas",
    "que",
    "pra",
    "pro",
    "por",
    "the",
}

_MARCADORES_GENERICOS = (
    "meu bem",
    "meu anjo",
    "energia",
    "caminhos",
    "sinto daqui",
    "respira comigo",
)

_MARCADORES_ENTREGAVEIS = (
    "materiais",
    "honorário",
    "honorario",
    "valor",
    "pix",
    "comprovante",
    "bônus",
    "bonus",
    "ritual",
    "consulta",
)

_MARCADORES_CETICISMO_LEAD = (
    "golpe",
    "funciona",
    "desconfio",
    "desconfiança",
    "desconfianca",
    "verdade",
    "enganado",
)

_MARCADORES_RESPOSTA_CETICISMO_BOT = (
    "sem promessa",
    "honesto",
    "sem milagre",
    "com calma",
    "te explico",
    "ponto a ponto",
)


def _tokens(texto: str) -> List[str]:
    if not texto:
        return []
    out: List[str] = []
    for m in _RE_WORD.findall(texto.lower()):
        if m not in _STOPWORDS:
            out.append(m)
    return out


def _contains_any(texto: str, marcadores: Iterable[str]) -> bool:
    low = (texto or "").lower()
    return any(m in low for m in marcadores)


def _ratio(a: int, b: int) -> float:
    if b <= 0:
        return 0.0
    return float(a) / float(b)


def _sort_key_node(node: str) -> int:
    """
    Ordem aproximada do funil para filtros (prefixo numérico do node).
    """
    n = (node or "").strip().lower()
    if n == "aguardando_pagamento":
        return 8
    m = re.match(r"^(\d+)_", n)
    if m:
        return int(m.group(1))
    return 0


def _estagio_auditoria(node: str) -> str:
    """
    Estágio para pesos/diagnósticos justos:
    - pre6: ainda não há oferta nem mecanismo esperado no fluxo.
    - leitura: nodes 6–7 (mecanismo sim; entregáveis/pagamento ainda não).
    - oferta: node 8+ e estados pós-oferta.
    """
    n = (node or "").strip().lower()
    if n == "aguardando_pagamento":
        return "oferta"
    if n.startswith("14_") or n.startswith("15_") or n.startswith("16_"):
        return "oferta"
    m = re.match(r"^(\d+)_", n)
    if not m:
        return "oferta"
    p = int(m.group(1))
    if p < 6:
        return "pre6"
    if p <= 7:
        return "leitura"
    return "oferta"


def _pesos_normalizados(estagio: str) -> Dict[str, float]:
    """
    Pesos que somam 1.0; dimensões fora do estágio recebem peso 0 e o resto é renormalizado.
    """
    raw = {"nome": 0.17, "mec": 0.18, "leit": 0.18, "ent": 0.16, "tom": 0.11, "ctx": 0.20}
    if estagio == "pre6":
        raw["mec"] = 0.0
        raw["ent"] = 0.0
    elif estagio == "leitura":
        raw["ent"] = 0.0
    total = sum(raw.values())
    if total <= 0:
        return {k: 1.0 / len(raw) for k in raw}
    return {k: v / total for k, v in raw.items()}


def _lead_meta(lead: Lead) -> Mapping[str, Any]:
    val = getattr(lead, "metadata_json", None) or {}
    if isinstance(val, dict):
        return val
    return {}


def score_lead_personalizacao(lead: Lead, mensagens: List[Mensagem]) -> Dict[str, Any]:
    """
    Score explicável de personalização/copy para um lead.
    """
    bot_msgs = [m for m in mensagens if getattr(m, "remetente", "") == "bot" and (getattr(m, "tipo", "") == "text")]
    user_msgs = [m for m in mensagens if getattr(m, "remetente", "") == "user"]

    bot_textos = [str(getattr(m, "texto", "") or "") for m in bot_msgs]
    user_textos = [str(getattr(m, "texto", "") or "") for m in user_msgs]
    bot_concat = " \n ".join(bot_textos)
    user_concat = " \n ".join(user_textos)

    nome = str(getattr(lead, "nome", "") or "").strip()
    node_atual = str(getattr(lead, "node_atual", "") or "")
    estagio = _estagio_auditoria(node_atual)
    pesos = _pesos_normalizados(estagio)
    meta = _lead_meta(lead)
    nome_mecanismo = str(getattr(lead, "nome_mecanismo", "") or "").strip()
    if not nome_mecanismo:
        nome_mecanismo = str(meta.get("nome_mecanismo", "") or "").strip()
    resumo_dor = str(getattr(lead, "resumo_dor", "") or "").strip()
    nome_pessoa_env = str(meta.get("nome_pessoa_envolvida", "") or "").strip()
    tempo_exato = str(meta.get("tempo_exato", "") or "").strip()
    evento_gatilho = str(meta.get("evento_gatilho", "") or "").strip()

    # 1) Vocativo / com quem fala
    nome_ok = bool(nome) and nome.lower() not in {"meu bem", "meu anjo", "minha estrela"}
    nome_mencoes = 0
    if nome_ok:
        alvo = nome.split()[0].lower()
        nome_mencoes = sum(1 for t in bot_textos if re.search(rf"\b{re.escape(alvo)}\b", t.lower()))
    s_nome = 1.0 if (nome_ok and nome_mencoes >= 1) else (0.5 if nome_ok else 0.0)

    # 2) Mecanismo único (nomeado e usado)
    mecanismo_mencionado = bool(nome_mecanismo) and re.search(re.escape(nome_mecanismo.lower()), bot_concat.lower()) is not None
    s_mecanismo = 1.0 if mecanismo_mencionado else (0.4 if nome_mecanismo else 0.0)

    # 3) Leitura fria com âncoras específicas
    ancoras_total = 0
    ancoras_usadas = 0
    for a in (resumo_dor, nome_pessoa_env, tempo_exato, evento_gatilho):
        a = (a or "").strip()
        if not a or a.upper() in {"INDEFINIDO", "INDEFINIDA", "N/A"}:
            continue
        ancoras_total += 1
        frag = a[:28].lower()
        if frag and frag in bot_concat.lower():
            ancoras_usadas += 1
    s_leitura = 1.0 if ancoras_total == 0 else min(1.0, _ratio(ancoras_usadas, ancoras_total))

    # 4) Oferta embalada com entregáveis / bônus (sinais)
    entregaveis_hits = sum(1 for t in bot_textos if _contains_any(t, _MARCADORES_ENTREGAVEIS))
    s_entrega = min(1.0, _ratio(entregaveis_hits, 3))

    # 5) Adaptação de tom para ceticismo
    lead_cetico = _contains_any(user_concat, _MARCADORES_CETICISMO_LEAD)
    bot_responde_ceticismo = _contains_any(bot_concat, _MARCADORES_RESPOSTA_CETICISMO_BOT)
    if lead_cetico:
        s_tom = 1.0 if bot_responde_ceticismo else 0.2
    else:
        s_tom = 0.7

    # 6) Continuidade de contexto (eco de tokens relevantes do usuário no bot)
    user_tokens = _tokens(user_concat)
    bot_tokens = set(_tokens(bot_concat))
    top_user = [w for w, _n in Counter(user_tokens).most_common(18)]
    overlap = sum(1 for w in top_user if w in bot_tokens)
    s_contexto = min(1.0, _ratio(overlap, max(1, min(len(top_user), 10))))

    # 7) Penalidade por genericidade excessiva
    bot_total = max(1, len(bot_textos))
    generic_hits = sum(1 for t in bot_textos if _contains_any(t, _MARCADORES_GENERICOS))
    generic_ratio = _ratio(generic_hits, bot_total)
    penalty_generico = 0.20 if generic_ratio > 0.65 else (0.10 if generic_ratio > 0.45 else 0.0)

    # pesos renormalizados por estágio (pre6 não penaliza mecanismo/entregáveis; leitura não penaliza entregáveis)
    score_base = (
        pesos["nome"] * s_nome
        + pesos["mec"] * s_mecanismo
        + pesos["leit"] * s_leitura
        + pesos["ent"] * s_entrega
        + pesos["tom"] * s_tom
        + pesos["ctx"] * s_contexto
    )
    score = max(0.0, min(1.0, score_base - penalty_generico))
    score_100 = int(round(score * 100))

    diagnosticos: List[str] = []
    if s_nome < 0.6:
        diagnosticos.append("vocativo_fraco_ou_nome_nao_fixado")
    if pesos["mec"] > 0 and s_mecanismo < 0.6:
        diagnosticos.append("mecanismo_unico_fraco")
    if s_leitura < 0.6:
        diagnosticos.append("leitura_fria_com_poucas_ancoras")
    if pesos["ent"] > 0 and s_entrega < 0.5:
        diagnosticos.append("oferta_sem_entregaveis_suficientes")
    if s_contexto < 0.55:
        diagnosticos.append("continuidade_de_contexto_baixa")
    if penalty_generico > 0:
        diagnosticos.append("linguagem_generica_acima_do_ideal")
    if lead_cetico and not bot_responde_ceticismo:
        diagnosticos.append("objecao_cetica_sem_resposta_dedicada")

    return {
        "lead_id": int(getattr(lead, "id", 0) or 0),
        "telefone": str(getattr(lead, "telefone", "") or ""),
        "node_atual": str(getattr(lead, "node_atual", "") or ""),
        "estagio_auditoria": estagio,
        "score_personalizacao": score_100,
        "sinais": {
            "nome_fixado": bool(nome_ok),
            "nome_mencoes_bot": int(nome_mencoes),
            "mecanismo_nomeado": bool(nome_mecanismo),
            "mecanismo_mencionado_no_bot": bool(mecanismo_mencionado),
            "ancoras_total": int(ancoras_total),
            "ancoras_usadas": int(ancoras_usadas),
            "entregaveis_hits": int(entregaveis_hits),
            "lead_cetico": bool(lead_cetico),
            "bot_respondeu_ceticismo": bool(bot_responde_ceticismo),
            "overlap_contexto_tokens": int(overlap),
            "generic_ratio": round(generic_ratio, 3),
        },
        "diagnosticos": diagnosticos,
    }


def auditar_personalizacao(
    db,
    *,
    hours: int = 24,
    limit: int = 80,
    min_msgs: int = 6,
    min_node_prefix: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Audita leads atualizados na janela e devolve visão agregada + ranking de risco.

    min_node_prefix: se definido (ex.: 6), só inclui leads cujo node_atual tem prefixo numérico
    >= esse valor (útil para não misturar fase inicial com métricas de leitura/oferta).
    """
    hours = max(1, min(int(hours or 24), 720))
    limit = max(5, min(int(limit or 80), 400))
    min_msgs = max(2, min(int(min_msgs or 6), 50))
    mn = None
    if min_node_prefix is not None:
        mn = max(0, min(int(min_node_prefix), 99))
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    leads = (
        db.query(Lead)
        .filter(Lead.atualizado_em >= since)
        .order_by(Lead.atualizado_em.desc())
        .limit(limit)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for lead in leads:
        if mn is not None and _sort_key_node(str(getattr(lead, "node_atual", "") or "")) < mn:
            continue
        msgs = (
            db.query(Mensagem)
            .filter(Mensagem.lead_id == lead.id)
            .order_by(Mensagem.timestamp.asc())
            .limit(260)
            .all()
        )
        if len(msgs) < min_msgs:
            continue
        items.append(score_lead_personalizacao(lead, msgs))

    filtros = {
        "min_node_prefix": mn,
        "min_msgs": min_msgs,
    }

    if not items:
        return {
            "window_hours": hours,
            "sample_size": 0,
            "filtros": filtros,
            "kpis": {},
            "kpis_por_estagio": {},
            "top_risco": [],
            "itens": [],
        }

    scores = [int(i["score_personalizacao"]) for i in items]
    avg = round(sum(scores) / len(scores), 1)
    low = [s for s in scores if s < 55]
    mid = [s for s in scores if 55 <= s < 75]
    high = [s for s in scores if s >= 75]

    diag_counter: Counter[str] = Counter()
    for i in items:
        for d in i.get("diagnosticos", []):
            diag_counter[d] += 1

    top_risco = sorted(items, key=lambda x: int(x.get("score_personalizacao", 0)))[:15]

    por_estagio: Dict[str, List[int]] = {}
    for it in items:
        st = str(it.get("estagio_auditoria") or "oferta")
        por_estagio.setdefault(st, []).append(int(it.get("score_personalizacao", 0)))

    kpis_por_estagio: Dict[str, Dict[str, Any]] = {}
    for st, vals in sorted(por_estagio.items()):
        if not vals:
            continue
        kpis_por_estagio[st] = {
            "count": len(vals),
            "score_medio": round(sum(vals) / len(vals), 1),
        }

    return {
        "window_hours": hours,
        "sample_size": len(items),
        "filtros": filtros,
        "kpis": {
            "score_medio": avg,
            "pct_baixo_lt55": round(100.0 * _ratio(len(low), len(scores)), 1),
            "pct_medio_55_74": round(100.0 * _ratio(len(mid), len(scores)), 1),
            "pct_alto_ge75": round(100.0 * _ratio(len(high), len(scores)), 1),
            "diagnosticos_top": dict(diag_counter.most_common(8)),
        },
        "kpis_por_estagio": kpis_por_estagio,
        "top_risco": top_risco,
        "itens": items,
    }

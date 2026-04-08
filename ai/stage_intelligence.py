"""
stage_intelligence.py — Inteligência por etapa (funil WhatsApp + copy avançada)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Injeta em ctx.metadata["stage_intel"] objetivos, skills, sinais comportamentais e
instruções curtas para o Personalizer, sem quebrar a FSM.

Conceitos: pré-frame; dor ≠ problema; situação antes do diagnóstico; pontes para
objeção comercial fora de ordem; ritmo quando o lead “atropela” a cadência.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from flows.funnel_gates import PLACEHOLDER_NOMES, VOCATIVO_SEM_NOME

logger = logging.getLogger(__name__)

# ── Detecção de intenção comercial / preço (PT-BR) ───────────────────────────
_RE_PRECO = re.compile(
    r"\b(pre[cç]o|preco|valor|quanto\s*custa|quanto\s*é|quanto\s*fica|"
    r"pix|parcela|parcelas|cart[aã]o|boleto|checkout|"
    r"link\s+(?:do\s+)?(?:pagamento|pix|checkout)|"
    r"reais|r\$|real|pagar|pagamento|desconto|promo[cç][aã]o|"
    r"divide|dividir|rs\.?)\b",
    re.IGNORECASE | re.UNICODE,
)

# Sinais explícitos de intenção comercial (sem "valor" solto — evita falso positivo em uso emocional)
_RE_PRECO_FORTE = re.compile(
    r"\b(pre[cç]o|preco|quanto\s*custa|quanto\s*é|quanto\s*fica|"
    r"pix|parcela|parcelas|cart[aã]o|boleto|checkout|"
    r"link\s+(?:do\s+)?(?:pagamento|pix|checkout)|"
    r"reais|r\$|real|pagar|pagamento|desconto|promo[cç][aã]o|"
    r"divide|dividir|rs\.?)\b",
    re.IGNORECASE | re.UNICODE,
)

_INTENT_COMERCIAL_PRECO = frozenset({
    "preco",
    "compra",
    "como_comprar",
    "duvida_produto",
    "objecao",
    "confirmacao",
})

# Curiosidade / desconfiança (ponte diferente de preço puro)
_RE_CURIOSIDADE = re.compile(
    r"\b(golpe|mentira|[eé]\s*real|funciona|confi[aá]vel|"
    r"quanto\s*tempo|demora|j[aá]\s*vi|primeira\s*vez|"
    r"s[oó]\s*quero\s*saber|antes\s*de)\b",
    re.IGNORECASE | re.UNICODE,
)

# Nomes genéricos / placeholder — não elogiar como nome próprio (inclui PLACEHOLDER_NOMES)
_NOMES_PLACEHOLDER: Set[str] = frozenset({
    "", "indefinido", "lead", "cliente", "anjo",
    "querida", "querido", "amor",
}) | PLACEHOLDER_NOMES


def _remetente(m: Any) -> str:
    if hasattr(m, "remetente"):
        return str(getattr(m, "remetente", "") or "")
    if isinstance(m, dict):
        return str(m.get("remetente") or "")
    return ""


def _texto_msg(m: Any) -> str:
    t = getattr(m, "texto", None) or (m.get("texto") if isinstance(m, dict) else None)
    return str(t or "").strip()


def _contar_turnos_user(historico: List[Any]) -> int:
    return sum(1 for m in (historico or []) if _remetente(m) == "user")


def _primeira_msg_do_user(historico: List[Any]) -> bool:
    """True se só há uma (ou zero) mensagem do user no histórico — conversa recém-iniciada."""
    return _contar_turnos_user(historico) <= 1


def _prefixo_node(node: str) -> str:
    n = (node or "").strip().lower()
    if not n:
        return ""
    if "_" in n:
        return n.split("_", 1)[0]
    return n[:1]


def _normalizar_nome(nome: str) -> str:
    n = (nome or "").strip().lower()
    return n


def nome_elegivel_para_elogio(nome: str) -> bool:
    """Nome próprio provável (não placeholder) — permite elogio breve ao nome."""
    n = _normalizar_nome(nome)
    if len(n) < 2:
        return False
    return n not in _NOMES_PLACEHOLDER


def detectar_pergunta_preco(texto: str) -> bool:
    if not texto or not texto.strip():
        return False
    return bool(_RE_PRECO.search(texto))


def pergunta_preco_para_funil(texto: str, intencao: Optional[str]) -> bool:
    """
    Combina regex ampla com sinal forte OU intent comercial, para não marcar
    pressão de preço só por 'valor' em contexto emocional.
    """
    if not texto or not texto.strip():
        return False
    if not _RE_PRECO.search(texto):
        return False
    if _RE_PRECO_FORTE.search(texto):
        return True
    inc = (intencao or "").strip().lower()
    return inc in _INTENT_COMERCIAL_PRECO


def detectar_curiosidade_ou_desconfianca(texto: str) -> bool:
    if not texto or not texto.strip():
        return False
    return bool(_RE_CURIOSIDADE.search(texto))


_RE_INTERROG_PT = re.compile(
    r"\b(?:como|quanto|quando|onde|por\s*que|porquê|porque|o\s*q(?:ue)?|qual|quais|quem|"
    r"d[aá]\s+pra|tem\s+como|[eé]\s+poss[ií]vel|funciona|preciso|devo|posso|"
    r"ser[aá]\s+que|me\s+diz|me\s+explica)\b",
    re.IGNORECASE | re.UNICODE,
)


def detectar_varias_perguntas_no_turno(texto: str) -> tuple[bool, int]:
    """
    Heurística para várias dúvidas/tópicos na mesma mensagem (WhatsApp costuma omitir '?').
    Retorna (ativa, estimativa 1–8 para telemetria).
    """
    t = (texto or "").strip()
    if len(t) < 10:
        return False, 0
    n_q = t.count("?")
    if n_q >= 2:
        return True, min(n_q, 8)
    palavras = t.split()
    n_words = len(palavras)
    hits = len(_RE_INTERROG_PT.findall(t.lower()))
    if hits >= 3:
        return True, min(hits, 8)
    if n_q == 1 and hits >= 2 and n_words >= 14:
        return True, min(max(hits, 2), 8)
    linhas = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(linhas) >= 3 and sum(1 for ln in linhas if "?" in ln or _RE_INTERROG_PT.search(ln)) >= 2:
        return True, min(len(linhas), 8)
    return False, max(n_q, min(hits, 1))


def _config_de_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    raw = meta.get("__config__")
    return raw if isinstance(raw, dict) else {}


def _frase_ponte_precificacao(pfx: str, nome_ok: bool) -> str:
    """Uma linha de exemplo mental para o modelo (não é script fixo)."""
    voc = "pelo seu nome" if nome_ok else "quando eu tiver seu nome firme aqui"
    pontes = {
        "1": f"Ex.: reconheça a curiosidade, diga que o investimento {voc} é explicado depois que a conexão estiver fechada — agora é acolher e alinhar energia.",
        "2": "Ex.: valor faz parte do ritual completo; primeiro salvar contato e alinhar o cuidado com que você será atendida(o).",
        "3": "Ex.: o valor entra depois que eu tiver sua situação e a leitura fizer sentido — agora preciso do seu contexto com calma.",
        "4": "Ex.: confiança vem com tempo; sigo te mostrando meu trabalho — preço fechamos quando for a hora da oferta.",
        "5": "Ex.: primeiro fechamos o que as linhas dizem; investimento é o passo seguinte, com clareza total.",
        "6": "Ex.: o valor é proporcional ao cuidado da leitura — ainda estamos preparando o terreno emocional.",
        "7": "Ex.: antes do valor, quero que você sinta o peso do que será resolvido; depois a troca fica justa.",
    }
    return pontes.get(pfx, pontes["3"])


def _perfil_por_node(node: str) -> Dict[str, Any]:
    n = (node or "").strip().lower()
    if n == "aguardando_pagamento":
        return {
            "objetivo_macro": "Pós-clique: confirmar interesse, reduzir fricção (PIX/link), tirar dúvidas objetivas.",
            "skills": ["objecao_curta", "clareza_pagamento", "calma"],
            "preco_cedo": "ok_falar_valor",
            "prioridade": "fechar_friccao",
        }

    p = _prefixo_node(node)
    base = {
        "objetivo_macro": "Manter rapport; avançar só com requisitos da etapa claros.",
        "skills": ["validar_emocao", "uma_ideia_por_vez"],
        "preco_cedo": "acolher_redirecionar",
        "prioridade": "ritmo",
    }

    if p == "1":
        return {
            **base,
            "objetivo_macro": (
                "Chegada: saudação + apresentação curta + calor humano; "
                "capturar primeiro nome se faltar; pré-frame de consulta mística (sem pitch nem valores)."
            ),
            "skills": [
                "pre_frame",
                "elogio_ao_nome_se_proprio",
                "nao_antecipar_diagnostico",
                "ritmo_adaptativo_lead_rapido",
            ],
            "preco_cedo": "acolher_1_balao_ponte_conexao",
            "prioridade": "rapport",
        }
    if p == "2":
        return {
            **base,
            "objetivo_macro": "Identidade + salvar contato com naturalidade; autoridade leve, zero catálogo de preço.",
            "skills": ["credibilidade_minima", "pedido_nome_se_faltar", "prova_social_tardia"],
            "preco_cedo": "curiosidade_ordem_ritual",
            "prioridade": "identidade",
        }
    if p == "3":
        return {
            **base,
            "objetivo_macro": "Situação (SPIN situação): contexto emocional e fatos antes de ‘fechar’ leitura; foto/desabafo se ainda faltarem.",
            "skills": [
                "pergunta_situacao",
                "escuta_ativa",
                "nao_inventar_causa",
                "integrar_sniffer",
            ],
            "preco_cedo": "dor_primeiro_valor_depois",
            "prioridade": "contexto",
        }
    if p == "4":
        return {
            **base,
            "objetivo_macro": "Prova social leve (ex.: Instagram) alinhada à promessa; não desviar para tabela de preços.",
            "skills": ["prova_social_leve", "marca_consistente"],
            "preco_cedo": "confianca_sem_tabela",
            "prioridade": "prova",
        }
    if p == "5":
        return {
            **base,
            "objetivo_macro": "Leitura: suspense respeitoso; não antecipar oferta nem valores fora do roteiro do node.",
            "skills": ["ritual_clareza", "paciencia"],
            "preco_cedo": "agradecer_redirecionar_leitura",
            "prioridade": "leitura",
        }
    if p in ("6", "7"):
        return {
            **base,
            "objetivo_macro": "Atenção/desejo: intensificar ética; preparar valor percebido sem soltar números soltos antes da oferta formal.",
            "skills": ["beneficio_dimensional_emocional", "gradualizacao", "ancoragem_emocional"],
            "preco_cedo": "valor_futuro_sem_chute",
            "prioridade": "desejo",
        }
    if p == "8":
        return {
            **base,
            "objetivo_macro": "Oferta: benefício, prova, conveniência, urgência conforme config.",
            "skills": ["oferta_direta", "ancoragem", "garantia_mental"],
            "preco_cedo": "ok_falar_valor",
            "prioridade": "conversao",
        }
    if p == "9":
        return {
            **base,
            "objetivo_macro": "Recuperação: reengajar sem culpa; abertura + benefício único.",
            "skills": ["recuperacao_leve", "uma_pergunta_aberta"],
            "preco_cedo": "ok_relembrar",
            "prioridade": "retorno",
        }
    if p in ("14", "15", "16"):
        return {
            **base,
            "objetivo_macro": "Pós-venda: entrega, gratidão, próximos passos claros.",
            "skills": ["pos_venda_objetivo", "suporte"],
            "preco_cedo": "objecao_calma",
            "prioridade": "entrega",
        }
    return base


def _instrucao_preco_cedo(
    modo: str,
    *,
    primeiros_turnos: bool,
    conversa_nova: bool,
    nome: str,
    nome_elogio: bool,
    pfx: str,
    curiosidade: bool,
) -> str:
    if modo == "ok_falar_valor":
        return ""

    ponte = _frase_ponte_precificacao(pfx, nome_elogio)
    blocos: List[str] = [
        "⚠️ Objeção comercial (preço/valor/pagamento) fora da ordem ideal desta etapa.",
        f"1) Valide em uma frase (use «{nome}» com naturalidade se for nome próprio; não invente nome).",
        "2) Não invente valores, links nem parcelas que não estejam na configuração injetada no fluxo.",
        "3) Transição obrigatória para a META desta etapa (uma ideia por balão).",
        ponte,
    ]
    if curiosidade:
        blocos.append(
            "4) Se misturar desconfiança/curiosidade (‘é golpe?’, ‘demora?’), acolha sem ironia; "
            "separe: primeiro confiança/contexto, depois condições comerciais na hora certa."
        )
    if conversa_nova:
        blocos.append(
            "5) Conversa no início: o lead pode ter vindo ‘quente’ do anúncio — não brigue com o ritmo; "
            "devolva acolhimento e recoloque um passo por vez."
        )
    elif primeiros_turnos:
        blocos.append("5) Primeiros turnos: priorize conexão antes de tabela.")

    return "\n".join(blocos)


def _camada_intent_sentimento(
    intencao: Optional[str],
    sentimento: Optional[str],
) -> str:
    if not intencao and not sentimento:
        return ""
    linhas = []
    if intencao and str(intencao).strip() and str(intencao).lower() not in ("indefinida", "indefinido"):
        linhas.append(f"- Intenção classificada (hint): {intencao}")
    if sentimento and str(sentimento).strip() and str(sentimento).lower() not in ("padrao", "neutro"):
        linhas.append(f"- Tom emocional (hint): {sentimento}")
    if not linhas:
        return ""
    return "SINAIS DO CLASSIFICADOR:\n" + "\n".join(linhas)


def _secao_biblioteca_pontes(
    meta: Dict[str, Any],
    *,
    pfx: str,
    varias_perguntas: bool,
    pergunta_preco: bool,
    curiosidade: bool,
) -> str:
    """Trechos de copy configuráveis (config_cliente.pontes_copy) — modelo adapta, não cola literal."""
    cfg = _config_de_meta(meta)
    lib = cfg.get("pontes_copy") if isinstance(cfg, dict) else None
    if not lib or not isinstance(lib, dict):
        return ""
    linhas: List[str] = []

    def _line(label: str, key: str) -> None:
        t = str(lib.get(key) or "").strip()
        if t:
            linhas.append(f"• [{label}] {t}")

    if pergunta_preco:
        _line("Preço fora da ordem", "preco_fora_da_ordem")
    if curiosidade:
        _line("Desconfiança", "desconfianca")
    if varias_perguntas:
        _line("Várias dúvidas no mesmo turno", "multi_topico")

    por_etapa = lib.get("por_etapa")
    if isinstance(por_etapa, dict) and pfx in por_etapa:
        te = str(por_etapa[pfx] or "").strip()
        if te:
            linhas.append(f"• [Etapa {pfx}] {te}")

    if not linhas and str(lib.get("ponte_geral") or "").strip():
        linhas.append(f"• [Geral] {lib['ponte_geral'].strip()}")

    if not linhas:
        return ""
    return (
        "BIBLIOTECA DE PONTES (adaptar ao tom da Cigana; não copiar em bloco se soar robótico):\n"
        + "\n".join(linhas)
    )


def _bloco_multiplas_perguntas() -> str:
    return (
        "MULTIPLAS DÚVIDAS / TÓPICOS NO MESMO TURNO:\n"
        "• Responda a cada ponto que o lead trouxe antes de só empurrar a meta do funil.\n"
        "• Pode usar linhas curtas ou um micro-parágrafo por tema; não ignore pergunta explícita.\n"
        "• Se misturar preço com outras dúvidas: trate todas (preço com ponte da etapa; resto com clareza acolhedora).\n"
        "• Depois de esclarecer, reancore em UMA vez a chamada para a etapa atual (sem checklist frio)."
    )


def _montar_bloco_instrucao(
    perfil: Dict[str, Any],
    *,
    node: str,
    primeiros_turnos: bool,
    conversa_nova: bool,
    pergunta_preco: bool,
    curiosidade: bool,
    varias_perguntas: bool,
    nome_lead: str,
    nome_elogio: bool,
    meta: Dict[str, Any],
    intencao: Optional[str],
    sentimento: Optional[str],
) -> str:
    obj = perfil.get("objetivo_macro") or ""
    skills = perfil.get("skills") or []
    sk = ", ".join(skills) if skills else ""
    pfx = _prefixo_node(node)

    partes: List[str] = [
        f"ETAPA (node {node}) | foco: {perfil.get('prioridade', 'ritmo')}",
        f"OBJETIVO: {obj}",
        f"SKILLS: {sk}",
    ]

    hint = _camada_intent_sentimento(intencao, sentimento)
    if hint:
        partes.append(hint)

    if varias_perguntas:
        partes.append(_bloco_multiplas_perguntas())

    if nome_elogio:
        partes.append(
            "NOME: há nome próprio — pode fazer um elogio breve e simbólico ao som/presença do nome (sem forçar piada)."
        )
    else:
        partes.append(
            "NOME: ausente ou genérico — peça o primeiro nome com naturalidade antes de aprofundar demais."
        )

    if pergunta_preco:
        modo = str(perfil.get("preco_cedo") or "acolher_redirecionar")
        partes.append(
            _instrucao_preco_cedo(
                modo,
                primeiros_turnos=primeiros_turnos,
                conversa_nova=conversa_nova,
                nome=nome_lead or VOCATIVO_SEM_NOME,
                nome_elogio=nome_elogio,
                pfx=pfx,
                curiosidade=curiosidade,
            )
        )
    elif curiosidade and not varias_perguntas:
        partes.append(
            "CURIOSIDADE / DESCONFIANÇA (sem pedido de preço explícito):\n"
            "• Responda o ponto emocional em 1 frase; em seguida reancore na META desta etapa.\n"
            "• Tom acolhedor, nunca defensivo nem de ‘vendedor irritado’."
        )
    elif curiosidade and varias_perguntas:
        partes.append(
            "CURIOSIDADE / DESCONFIANÇA (vários tópicos): não comprima tudo em uma frase — "
            "dê espaço a cada medo/dúvida; depois reancore na etapa."
        )

    cfg = _config_de_meta(meta)
    if cfg:
        n_low = (node or "").strip().lower()
        if n_low == "aguardando_pagamento" or pfx in ("8", "9"):
            partes.append(
                "CONFIG: preços e link podem ser usados quando o roteiro deste node permitir oferta/recuperação/pagamento."
            )
        else:
            partes.append(
                "CONFIG: existem valores no sistema — nesta etapa NÃO cite números nem link de checkout; "
                "não invente preços; condições comerciais na hora certa (oferta)."
            )

    if meta.get("foto_recebida"):
        partes.append("SNIFER: foto/mídia já registrada — não pedir de novo; integrar na fala se couber.")
    if meta.get("desabafo_recebido"):
        partes.append("SNIFER: desabafo captado — validar peso emocional antes de novo interrogatório.")
    if meta.get("contexto_comprimido"):
        partes.append("MEMÓRIA: contexto comprimido — não contradizer fatos já consolidados.")

    bib = _secao_biblioteca_pontes(
        meta,
        pfx=pfx,
        varias_perguntas=varias_perguntas,
        pergunta_preco=pergunta_preco,
        curiosidade=curiosidade,
    )
    if bib:
        partes.append(bib)

    return "\n".join(partes)


def enriquecer_contexto_stage(
    ctx: Any,
    lead: Any,
    *,
    texto_recebido: str = "",
    intencao: Optional[str] = None,
    sentimento: Optional[str] = None,
) -> None:
    """
    Preenche ctx.metadata['stage_intel'] para o Personalizer e para nodes.
    Não altera node_atual nem FSM.
    """
    try:
        meta: Dict[str, Any] = dict(ctx.metadata or {})
        node = str(getattr(ctx, "node_atual", "") or "").strip()
        historico = getattr(ctx, "historico", None) or []

        n_user = _contar_turnos_user(historico)
        primeiros_turnos = n_user <= 2
        conversa_nova = _primeira_msg_do_user(historico)

        texto = texto_recebido or getattr(ctx, "texto_recebido", "") or ""

        intencao = intencao if intencao is not None else getattr(ctx, "intencao", None)
        pergunta_preco = pergunta_preco_para_funil(texto, intencao)
        curiosidade = detectar_curiosidade_ou_desconfianca(texto)
        varias_perguntas, estimativa_perguntas = detectar_varias_perguntas_no_turno(texto)

        nome_lead = str(meta.get("nome_lead") or getattr(lead, "nome", "") or "").strip()
        nome_elogio = nome_elegivel_para_elogio(nome_lead)
        sentimento = sentimento if sentimento is not None else getattr(ctx, "sentimento", None)

        perfil = _perfil_por_node(node)
        pfx = _prefixo_node(node)

        # Preço “prematuro” = pergunta comercial antes da oferta explícita
        preco_prematuro = pergunta_preco and pfx in ("1", "2", "3", "4", "5", "6", "7")

        bloco = _montar_bloco_instrucao(
            perfil,
            node=node,
            primeiros_turnos=primeiros_turnos,
            conversa_nova=conversa_nova,
            pergunta_preco=pergunta_preco,
            curiosidade=curiosidade,
            varias_perguntas=varias_perguntas,
            nome_lead=nome_lead,
            nome_elogio=nome_elogio,
            meta=meta,
            intencao=intencao,
            sentimento=sentimento,
        )

        meta["stage_intel"] = {
            "node": node,
            "prefixo": pfx,
            "objetivo_macro": perfil.get("objetivo_macro"),
            "prioridade": perfil.get("prioridade"),
            "skills": perfil.get("skills"),
            "pergunta_preco_detectada": pergunta_preco,
            "curiosidade_ou_desconfianca": curiosidade,
            "varias_perguntas_detectadas": varias_perguntas,
            "estimativa_topicos_pergunta": estimativa_perguntas,
            "preco_prematuro": preco_prematuro,
            "primeiros_turnos": primeiros_turnos,
            "conversa_nova": conversa_nova,
            "nome_elegivel_elogio": nome_elogio,
            "turnos_user_aprox": n_user,
            "bloco_instrucao": bloco,
            "hints": {
                "intencao": intencao,
                "sentimento": sentimento,
            },
        }
        ctx.metadata = meta
    except Exception as e:
        logger.warning("stage_intelligence: falha ao enriquecer (não bloqueante): %s", e)


__all__ = [
    "enriquecer_contexto_stage",
    "detectar_pergunta_preco",
    "pergunta_preco_para_funil",
    "detectar_curiosidade_ou_desconfianca",
    "detectar_varias_perguntas_no_turno",
    "nome_elegivel_para_elogio",
]

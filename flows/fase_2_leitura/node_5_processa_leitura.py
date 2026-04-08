"""
flows/fase_2_leitura/node_5_processa_leitura.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O ANALISTA ESTRATÉGICO — v22 (alinhado ao Node 1: Esmeralda Ácassia, tom leitura, PT-BR)

PAPEL NO FUNIL:
  Na rota aprovada, gera a estratégia (Hive Mind) de forma silenciosa.
  Gatekeeper: respostas rasas → copy de redirecionamento com voz de templo, não de cobrança.

Mantém: memória (sofisticação, ceticismo, energia), contexto_extra do Node 4, sentimento no prompt,
pontuação rígida no redirecionamento.
"""

import logging
import re
import random
from typing import Tuple, List
from schema import Acao, slice_historico_para_ia
from copy_sanitizer import (
    genero_efetivo_para_copy,
    genero_hint_para_prompt,
    inferir_masculino_somente_nome,
    limpar_colagem_primeira_msg_whatsapp_em_texto,
    nome_lead_para_exibicao,
    resumo_dor_para_copy,
    resolver_gatilho_emocional,
    tentar_salvar_balao_ia_cortado,
)
from conversation_policy import lead_reportou_problema_entrega

logger = logging.getLogger(__name__)

# ── CONFIGURAÇÕES E REGEX ──
_CONFIANCA_MINIMA = 0.75
_MAX_LOOPS_APROFUNDAMENTO = 2

_RUIDO = {
    "ok", "sim", "não", "nao", "pronto", "feito", "ja", "já", "ta", "tá",
    "beleza", "blz", "certo", "entendi", "consegui", "fiz", "uhum", "hmm",
    "tá bom", "ta bom", "pode", "vamos", "s", "n", "aqui", "prontinho", "visto"
}

_SINAIS_ENVIO_FOTO = re.compile(
    r'\b(mandei|enviei|ta ai|tá aí|foto|palma|mão|mao|imagem|olha ai|segue|pronto|mande)\b',
    re.IGNORECASE
)

# Regex que caça terminações abertas (cortes de IA)
_REGEX_CORTE_FATAL = r"([,;:\-]|\b(?:a|ao|as|e|é|eh|éh|foi|o|os|se|à|em|mas|ou|um|uma|que|de|do|da|com|por|para|sem|são|tão|tbm|também|esse|essa|isso|isto|nele|nela|nisso|nisto|meu|seu|sua|minha))\s*$"

# Valida se termina em pontuação ou emoji
_PONTUACAO_VALIDA = r".*[.\!\?…\u2600-\u26FF\u2700-\u27BF\U0001f300-\U0001faff]$"
_RE_TENTATIVAS = re.compile(
    r"\b(j[aá]\s+tentei|eu\s+tentei|tentei|fiz|procurei|orei|rezei|"
    r"mandei\s+mensagem|conversei|dei\s+tempo|me\s+afastei|bloqueei|desbloqueei)\b",
    re.I,
)
_RE_PROBLEMA_ENTREGA = re.compile(
    r"(?i)(mensagem\s+cortad|t[aá]\s+atropel|n[aã]o\s+deu\s+tempo|"
    r"n[aã]o\s+deu\s+pra\s+ver|n[aã]o\s+carreg|travou|bugou)"
)
_RE_FEEDBACK_EXPERIENCIA = re.compile(
    r"(?i)(transi[cç][aã]o|humaniz|humani[sz]|rob[oô]|mais\s+natural|"
    r"soou\s+(?:a\s+)?sper|ficou\s+(?:meio\s+)?(?:frio|seco))"
)

# ── PROMPTS DE IA ──
_SYSTEM_PROFILER = """Você é o analista silencioso que prepara a leitura para Esmeralda Ácassia (Cigana Esmeralda), quiromancia no WhatsApp.
Sua saída NÃO vai para o lead; só alimenta estratégia interna (Hive Mind).

EXTRAIA EM FORMATO CHAVE::VALOR:
UNIVERSO::[amor_de_volta | encontrar_amor | salvar_relacionamento | prosperidade | familia_cura | superar_padrao | geral]
GENERO::[feminino | masculino | indefinido]
SOFISTICACAO::[1 a 5, onde 1=Iniciante e 5=Cético/Traumatizado]
CETICISMO::[baixo | medio | alto]
ARQUETIPO::[O Mártir | O Cético | O Ansioso | O Ferido | O Esperançoso]
NIVEL_ENERGIA::[Esgotado | Baixo | Ansioso | Alto]
TOM_CIRURGICO::[Maternal | Autoritário | Neutro]
TEMPO_DOR::[período aproximado (ex: '3 meses'). Se não souber, 'muito tempo']
DOR_CENTRAL::[só a ferida emocional em até 18 palavras; nunca copie saudação, "me chamo", nome da fala, nem pergunta de preço/consulta. Se não souber, 'INDEFINIDA']
DESEJO_OCULTO::[o que a pessoa quer de verdade (ex: paz, ser amada)]
OBJECAO_SILENCIOSA::[maior medo agora, em uma linha; concorde com GENERO quando óbvio]
GATILHO_EMOCIONAL::[frase CURTA (máx 12 palavras), trava central para recuperação; específica, não genérica]
NOME_MECANISMO::[nome místico focado na dor. Ex: 'Desmanche de Nó Kármico']
CONFIANCA::[0.0 a 1.0 sobre a riqueza do relato para a leitura das linhas]

Se a mensagem do analista trouxer o bloco ANCORAS_DA_COLETA_NODE3, são percepções já oferecidas ao lead na coleta (camadas emocionais / vínculo / tempo). Mantenha coerência em UNIVERSO, DOR_CENTRAL, DESEJO_OCULTO, OBJECAO_SILENCIOSA e GATILHO_EMOCIONAL: você pode aprofundar e precisar, não reinvente outra história sem motivo forte no texto do lead.

IMPORTANTE: tudo ancora em quiromancia e linhas da mão, não em cartas ou outros oráculos.
"""

_SYSTEM_REDIRECT = """Você é Esmeralda Ácassia (Cigana Esmeralda), mesma voz dos passos anteriores: calma e presença, como no templo.

O lead mandou algo raso, ou só confirmação, ou puxou preço/medo sem abrir o fundo.
GÊNERO PARA CONCORDÂNCIA: {genero_hint}

Acolha sem julgar. Convide a abrir o que pesa de verdade, para você conseguir ler as linhas da mão com honestidade. Sem tom de cobrança nem call center.

FORMATO:
- 2 balões com [BALAO].
- [BALAO] só depois de frase completa com . ou ?
- Sem travessão (—).

EXEMPLOS:
❌ ERRADO: "Eu entendo a sua dúvida, [BALAO] mas me conte..."
✅ CERTO: "Eu entendo a sua dúvida perfeitamente. [BALAO] Mas me conte a verdade..."
"""

# ── FUNÇÕES AUXILIARES ──
def _extrair_matriz(texto_bruto: str) -> dict:
    resultado = {}
    if not texto_bruto: return resultado
    texto = re.sub(r"`{3}(?:json|text)?|`{3}", "", texto_bruto).strip()
    for linha in texto.split("\n"):
        if "::" not in linha: continue
        partes = linha.split("::", 1)
        chave = partes[0].strip().upper().replace(" ", "_")
        valor = partes[1].strip().strip('"').strip("'")
        if valor: resultado[chave] = valor
    return resultado

def _normalizar_genero_ia(raw) -> str:
    r = str(raw or "").strip().lower()
    if r in ("masculino", "masc", "homem", "m"):
        return "masculino"
    if r in ("feminino", "fem", "mulher", "f"):
        return "feminino"
    return ""


def _detectar_genero_local(ctx) -> str:
    if inferir_masculino_somente_nome(ctx.nome_lead or ""):
        return "masculino"
    return "indefinido"


def _resolver_genero_lead(dados_extraidos: dict, ctx) -> str:
    meta = getattr(ctx, "metadata", {}) or {}
    gi_ia = _normalizar_genero_ia(dados_extraidos.get("GENERO"))
    merged = {**meta, "genero_lead": gi_ia}
    texto_scan = " ".join(
        str(x).strip()
        for x in (
            ctx.texto_recebido,
            meta.get("desabafo_original"),
            meta.get("contexto_extra_final"),
        )
        if x
    )
    g = genero_efetivo_para_copy(
        ctx.nome_lead or "", merged, texto_discurso=texto_scan[:4000]
    )
    if g != "indefinido":
        return g
    return _detectar_genero_local(ctx)


def _sintetizar_gatilho_emocional(dados: dict) -> str:
    """Preenche gatilho_emocional se a IA não devolveu ou veio vago."""
    raw = (dados.get("GATILHO_EMOCIONAL") or "").strip()
    if raw and len(raw) >= 6 and raw.lower() not in ("nenhuma", "indefinida"):
        return resolver_gatilho_emocional({"gatilho_emocional": raw})[:200]
    obj = (dados.get("OBJECAO_SILENCIOSA") or "").strip()
    if obj and obj.lower() not in ("nenhuma", "none", ""):
        return resolver_gatilho_emocional({"objecao_silenciosa": obj})[:200]
    dor = (dados.get("DOR_CENTRAL") or "").strip()
    if dor and dor.upper() != "INDEFINIDA":
        return dor[:200]
    return ""

def _delay_digitacao(texto: str) -> int:
    return max(7, min(len(str(texto)) // 15, 22))

def _parse_confianca(val) -> float:
    if not val:
        return 1.0
    try:
        return float(str(val).strip().replace(",", "."))
    except ValueError:
        return 1.0


def _verificar_ruido_foto(texto: str) -> bool:
    limpo = texto.lower().strip()
    palavras = limpo.split()
    return len(palavras) <= 5 and _SINAIS_ENVIO_FOTO.search(limpo)


def _extrair_tentativas_previas(texto: str) -> str:
    t = " ".join((texto or "").split()).strip()
    if len(t) < 12:
        return ""
    if _RE_TENTATIVAS.search(t):
        return t[:220]
    return ""


def _normalizar_fragmento_ctx(s: str) -> str:
    t = " ".join((s or "").split()).strip()
    if not t:
        return ""
    # Remove ruídos frequentes de confirmação que não ajudam a leitura.
    if t.lower() in _RUIDO:
        return ""
    # Evita colar payload com divisores técnicos.
    t = re.sub(r"\s*\|\s*", " | ", t)
    return t


def _montar_texto_contexto_node5(desabafo_pre: str, contexto_extra: str, msg_lead: str) -> str:
    partes: List[str] = []
    vistos: set[str] = set()
    for raw in (desabafo_pre, contexto_extra, msg_lead):
        t = _normalizar_fragmento_ctx(str(raw or ""))
        if not t:
            continue
        k = re.sub(r"\s+", " ", t.lower()).strip(" .!?…")
        if k in vistos:
            continue
        vistos.add(k)
        partes.append(t)
    return " ".join(partes).strip()

# ── EXECUTOR PRINCIPAL ──
def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", {}) or {}
    nome_fmt = nome_lead_para_exibicao((ctx.nome_lead or "").strip())
    
    msg_lead = str(ctx.texto_recebido or "").strip()
    if lead_reportou_problema_entrega(msg_lead):
        ctx.metadata = meta
        ctx.estado_coleta = "node5_reparo_entrega"
        return [
            Acao(tipo="delay", segundos=random.randint(3, 6)),
            Acao(
                tipo="text",
                conteudo=f"Obrigada por avisar, {nome_fmt}. Vou seguir em blocos mais curtos para não cortar nada.",
                metadata={"skip_gancho_final": True},
            ),
            Acao(tipo="delay", segundos=random.randint(2, 4)),
            Acao(
                tipo="text",
                conteudo="Me manda um *ok* quando estiver visível aí e eu continuo.",
                metadata={"skip_gancho_final": True},
            ),
        ], "5_processa_leitura"
    # 💎 RESGATE: consolida contexto sem duplicar ruído entre nodes
    desabafo_pre = meta.get("desabafo_original", "")
    contexto_extra = meta.get("contexto_extra_final", "")
    texto_completo = _montar_texto_contexto_node5(desabafo_pre, contexto_extra, msg_lead)
    loops = meta.get("node5_loops_ativos", 0)

    genero_prelim = genero_efetivo_para_copy(
        ctx.nome_lead or "",
        meta,
        texto_discurso=texto_completo[:4000] if texto_completo else None,
    )
    genero_hint = genero_hint_para_prompt({**meta, "genero_lead": genero_prelim})

    # 1. GATEKEEPER: REDIRECIONAMENTO SE FOR RASO
    is_apenas_foto = _verificar_ruido_foto(msg_lead)
    # Após o Instagram (Node 4), "ok"/"pronto" é confirmação esperada — não redirecionar (evita 2º/3º ciclo de ok).
    skip_ruido_pos_insta = bool(meta.pop("node5_ignorar_ruido_um_turno", None))
    if skip_ruido_pos_insta and (msg_lead.lower() in _RUIDO or is_apenas_foto):
        logger.info("event=node5_skip_gatekeeper_pos_insta lead=%s msg=%r", nome_fmt, msg_lead[:40])
    elif (msg_lead.lower() in _RUIDO or is_apenas_foto) and loops < _MAX_LOOPS_APROFUNDAMENTO:
        meta["node5_loops_ativos"] = loops + 1
        logger.info(f"🔎 [NODE 5] Gatekeeper: {nome_fmt} foi superficial. Redirecionando.")
        
        acoes_redirect = []
        if ctx.personalizer:
            try:
                # Injeta a intenção detectada para ajudar a IA no acolhimento
                situacao = f"Lead enviou '{msg_lead}'. Intenção detectada: {ctx.intencao}."
                resp = ctx.personalizer.gerar_resposta(
                    system_prompt=_SYSTEM_REDIRECT.format(genero_hint=genero_hint),
                    historico_lista=slice_historico_para_ia(ctx),
                    mensagem_lead=(
                        f"{situacao} Convide a pessoa a falar o que pesa de verdade, com calma, "
                        "para a leitura das linhas não ficar no vazio."
                    ),
                    metadata=meta,
                    max_output_tokens=520,
                    temperature=0.65,
                )
                
                # 🛡️ STRICT PUNCTUATION SHIELD + recuperação de truncamento
                partes = re.split(r'\[?BAL[AÃ]O\]?', resp, flags=re.IGNORECASE)

                def _ok_n5(s: str) -> bool:
                    return (
                        len(s) >= 5
                        and re.match(_PONTUACAO_VALIDA, s)
                        and not re.search(_REGEX_CORTE_FATAL, s.lower())
                    )

                candidatos: List[str] = []
                for b in partes:
                    c = re.sub(r"\[.*?\]", "", b).strip()
                    if len(c) < 5:
                        continue
                    if not _ok_n5(c):
                        c = tentar_salvar_balao_ia_cortado(c, _REGEX_CORTE_FATAL)
                    if not _ok_n5(c):
                        logger.warning("⚠️ [NODE 5] Balão cortado ignorado: '%s'", c[:200])
                        continue
                    candidatos.append(c)
                for i, c in enumerate(candidatos):
                    acoes_redirect.append(Acao(tipo="delay", segundos=_delay_digitacao(c)))
                    ultimo = i == len(candidatos) - 1
                    _c = limpar_colagem_primeira_msg_whatsapp_em_texto(c)
                    acoes_redirect.append(
                        Acao(
                            tipo="text",
                            conteudo=_c,
                            metadata={} if ultimo else {"skip_gancho_final": True},
                        )
                    )

                if acoes_redirect:
                    ctx.metadata = meta
                    ctx.estado_coleta = "node5_gatekeeper_redireciona"
                    return acoes_redirect, "5_processa_leitura"
            except Exception:
                pass

        ctx.metadata = meta
        ctx.estado_coleta = "node5_gatekeeper_fallback"
        return [
            Acao(tipo="delay", segundos=random.randint(6, 10)),
            Acao(
                tipo="text",
                conteudo=(
                    f"Recebi sua mensagem, {nome_fmt}. Pra eu enxergar direito nas linhas, preciso que você me diga: "
                    "o que mais aperta o peito aí hoje? 👇"
                ),
            ),
        ], "5_processa_leitura"

    # 2. COLETA DE TENTATIVAS PRÉVIAS (evita presunção no node 6/7)
    tentativas_salvas = str(meta.get("node5_tentativas_previas") or "").strip()
    if not tentativas_salvas:
        ap_blob = str(meta.get("aprofundamento_texto") or "").strip()
        if ap_blob:
            meta["node5_tentativas_previas"] = ap_blob[:220]
            meta["node5_pediu_tentativas"] = False
            if not meta.get("node5_dado_concreto"):
                meta["node5_dado_concreto"] = ap_blob[:140]
            tentativas_salvas = str(meta.get("node5_tentativas_previas") or "").strip()
    if not tentativas_salvas:
        trecho_tentativa = _extrair_tentativas_previas(msg_lead) or _extrair_tentativas_previas(
            texto_completo
        )
        if trecho_tentativa:
            meta["node5_tentativas_previas"] = trecho_tentativa
            meta["node5_pediu_tentativas"] = False
            if not meta.get("node5_dado_concreto"):
                meta["node5_dado_concreto"] = trecho_tentativa[:140]
        else:
            if not bool(meta.get("node5_pediu_tentativas")):
                meta["node5_pediu_tentativas"] = True
                ctx.metadata = meta
                ctx.estado_coleta = "node5_coleta_tentativas"
                return [
                    Acao(tipo="delay", segundos=random.randint(4, 8)),
                    Acao(
                        tipo="text",
                        conteudo=(
                            f"Antes de eu fechar sua leitura com precisão, me conta em uma frase o que você já tentou até aqui."
                        ),
                    ),
                ], "5_processa_leitura"

    # 3. EXTRAÇÃO SILENCIOSA (HIVE MIND)
    dados_extraidos = {}
    if ctx.personalizer:
        try:
            logger.info(f"🧠 [NODE 5 v22] Minerando perfil de {nome_fmt}. Sentimento: {ctx.sentimento}.")
            # Injetamos o sentimento atual na análise técnica
            contexto_ia = (
                f"TEXTO DO LEAD: '{texto_completo}'\n"
                f"SENTIMENTO ATUAL: {ctx.sentimento}\n"
                f"INTENÇÃO: {ctx.intencao}"
            )
            ancoras_n3 = (meta.get("node3_percepcoes_multas") or "").strip()
            if ancoras_n3:
                contexto_ia += (
                    "\n\nANCORAS_DA_COLETA_NODE3 (ecoar na matriz abaixo; não contradizer sem evidência nova no texto):\n"
                    f"{ancoras_n3[:1200]}"
                )

            resp_ext = ctx.personalizer.gerar_resposta(
                system_prompt=_SYSTEM_PROFILER,
                historico_lista=slice_historico_para_ia(ctx, 5),
                mensagem_lead=contexto_ia,
                metadata=meta,
            )
            dados_extraidos = _extrair_matriz(resp_ext)
            
            # 🔥 Backup de DOR: só desabafo (evita colar confirmações tipo "já estou te seguindo" no resumo)
            if not dados_extraidos.get("DOR_CENTRAL") or dados_extraidos.get("DOR_CENTRAL").upper() == "INDEFINIDA":
                _fb = resumo_dor_para_copy((_d or "")[:1200], max_len=100)
                dados_extraidos["DOR_CENTRAL"] = _fb or "esse peso nas suas linhas"
        except Exception as e:
            logger.error(f"🚨 [NODE 5] Erro na extração: {e}")

    confianca = _parse_confianca(dados_extraidos.get("CONFIANCA"))
    loops_conf = int(meta.get("node5_confianca_loops", 0) or 0)
    if confianca < _CONFIANCA_MINIMA and loops_conf < _MAX_LOOPS_APROFUNDAMENTO and ctx.personalizer:
        meta["node5_confianca_loops"] = loops_conf + 1
        logger.info(
            "event=node5_confianca_baixa lead=%s confianca=%s loop=%s",
            nome_fmt,
            confianca,
            meta["node5_confianca_loops"],
        )
        try:
            p_inv = (
                "Você é Esmeralda Ácassia (Cigana Esmeralda). O relato veio fino demais para fechar a leitura das linhas.\n"
                f"GÊNERO PARA CONCORDÂNCIA: {genero_hint}\n"
                "Faça UMA pergunta curta, com tom de templo, que aprofunde: quem está no centro, "
                "há quanto tempo isso pesa, ou o momento em que piorou. Máximo duas linhas. "
                "Sem travessão. Sem 'Claro' ou 'Com certeza'. Termine com interrogação."
            )
            pergunta = ctx.personalizer.gerar_resposta(
                system_prompt=p_inv,
                historico_lista=slice_historico_para_ia(ctx, 8),
                mensagem_lead=f"Trecho do lead: {texto_completo[:900]}",
                metadata=meta,
            )
            pergunta = (pergunta or "").strip()
            if len(pergunta) > 12:
                ctx.metadata = meta
                ctx.estado_coleta = "node5_aprofundar_perfil"
                return [
                    Acao(tipo="delay", segundos=random.randint(4, 9)),
                    Acao(tipo="text", conteudo=pergunta),
                ], "5_processa_leitura"
        except Exception as e:
            logger.error(f"🚨 [NODE 5] Falha pergunta confiança: {e}")

    # 4. PERSISTÊNCIA NA MEMÓRIA (TOTAL MAPPING)
    gatilho_txt = _sintetizar_gatilho_emocional(dados_extraidos)
    meta.update({
        "universo_desejo": dados_extraidos.get("UNIVERSO", "geral").lower(),
        "genero_lead": _resolver_genero_lead(dados_extraidos, ctx),
        "arquetipo_lead": dados_extraidos.get("ARQUETIPO", "O Ferido"),
        "tom_cirurgico": dados_extraidos.get("TOM_CIRURGICO", "Maternal"),
        "tempo_sofrimento": dados_extraidos.get("TEMPO_DOR", "muito tempo"),
        "resumo_dor": resumo_dor_para_copy(
            str(dados_extraidos.get("DOR_CENTRAL") or "esse peso nos caminhos"),
            max_len=140,
        ),
        "desejo_oculto": dados_extraidos.get("DESEJO_OCULTO", ""),
        "objecao_silenciosa": dados_extraidos.get("OBJECAO_SILENCIOSA", "Nenhuma"),
        "gatilho_emocional": gatilho_txt or meta.get("gatilho_emocional", ""),
        "nome_mecanismo": dados_extraidos.get(
            "NOME_MECANISMO", "Trabalho de Firmação e Resgate nas Linhas"
        ),
        "sofisticacao_lead": dados_extraidos.get("SOFISTICACAO", "1"),
        "ceticismo_lead": dados_extraidos.get("CETICISMO", "medio"),
        "nivel_energia": dados_extraidos.get("NIVEL_ENERGIA", "Baixo"),
        "node5_loops_ativos": 0,
        "node5_confianca_loops": 0,
    })

    # Higiene e Finalização
    for k in list(meta.keys()):
        if "url" in k.lower(): meta[k] = ""

    ctx.metadata = meta
    ctx.estado_coleta = "node5_perfil_completo"
    meta["contexto_extra_final"] = ""
    logger.info(f"✅ [NODE 5 v22] Hive Mind mapeado. Handoff para Node 6.")

    acoes_handoff: List[Acao] = []
    if len(msg_lead) > 14 and _RE_FEEDBACK_EXPERIENCIA.search(msg_lead):
        acoes_handoff.extend(
            [
                Acao(tipo="delay", segundos=random.randint(3, 6)),
                Acao(
                    tipo="text",
                    conteudo=(
                        f"Obrigada pelo toque, {nome_fmt}. "
                        "Eu levo isso contigo — e agora fecho o retrato que as tuas linhas pedem com calma."
                    ),
                    metadata={"skip_gancho_final": True},
                ),
            ]
        )
    acoes_handoff.append(Acao(tipo="delay", segundos=random.randint(4, 8)))
    return acoes_handoff, "6_atencao_dinamica"
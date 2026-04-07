"""
flows/fase_2_leitura/node_7_interesse_desejo.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERESSE E DESEJO (AIDA 3) — v17 (ritmo celular: fatiar como nodes 6 e 8)

Reage à emoção do lead depois da leitura fria (Node 6). Sete blocos + injeção opcional de áudio de prova.

Mantém: blindagem de tags, TTS nos índices definidos, depoimento após o bloco 4.
🔥 v17: `fatiar_texto_ritmo_celular` + vocativo unificado + substituições proibidas (paridade node 6/8).
"""

import logging
import random
import re
from typing import Optional
from schema import Acao, slice_historico_para_ia
from copy_sanitizer import (
    aplicar_substituicoes_proibidas,
    contexto_lead_para_nodes,
    fatiar_texto_ritmo_celular,
    frase_dor_contextualizada,
    genero_efetivo_para_copy,
    genero_hint_para_prompt,
    limpar_colagem_primeira_msg_whatsapp_em_texto,
    normalizar_enxerto_dor_sem_contexto,
    parse_blocos_leitura_ia,
    remover_marcadores_bloco_ia_vazados,
    sufixo_ancoras_node3_para_prompt,
    unificar_vocativos_por_genero,
)
from analytics.copy_constituicao_cigana import camada_constituicao_node7
from conversation_policy import lead_reportou_problema_entrega
from analytics.copy_personalization import (
    contexto_desejo_resultado_para_prompt,
    definir_nome_mecanismo_se_generico,
    norte_editorial_venda_fria_direta_para_prompt,
    perfil_copy_para_prompt,
)

logger = logging.getLogger(__name__)

# ── MAPEAMENTO DE CADÊNCIA (0-based) ──
_INDICES_AUDIO   = {1, 3, 4}
_INDICES_IMPACTO = {3, 6}
_RE_PROBLEMA_ENTREGA = re.compile(
    r"(?i)(mensagem\s+cortad|t[aá]\s+atropel|n[aã]o\s+deu\s+tempo|"
    r"n[aã]o\s+deu\s+pra\s+ver|n[aã]o\s+carreg|travou|bugou)"
)

def _delay_digitacao(texto: str, eh_audio: bool = False) -> int:
    if not texto: return 8
    fator = 14 if eh_audio else 18
    return max(10, min(len(str(texto)) // fator, 26))


def _extrair_blocos_fallback(texto: str, max_blocos: int = 7, min_len: int = 8) -> list[str]:
    """
    Recupera blocos quando a IA vem sem BLOCO_N::.
    """
    t = (texto or "").strip()
    if not t:
        return []
    partes = re.split(r"\[?BAL[AÃ]O\]?", t, flags=re.I)
    out: list[str] = []
    for p in partes:
        p = re.sub(r"`{3}(?:json|text)?|`{3}", "", p).strip()
        if not p:
            continue
        for ln in p.splitlines():
            ln2 = re.sub(r"^\s*BLOCO[_\s]*\d+\s*::\s*", "", ln.strip(), flags=re.I).strip()
            if len(ln2) >= min_len:
                out.append(ln2)
        if "\n" not in p:
            p2 = re.sub(r"^\s*BLOCO[_\s]*\d+\s*::\s*", "", p, flags=re.I).strip()
            if len(p2) >= min_len:
                out.append(p2)
        if len(out) >= max_blocos:
            break
    return out[:max_blocos]


def _reacao_curta_ao_input(msg_lead: str, nome_fmt: str) -> str:
    t = (msg_lead or "").strip().lower()
    if re.search(r"\b(sim|faz sentido|bateu|ressonou|verdade)\b", t):
        return f"Perfeito, {nome_fmt}. Obrigada por confirmar isso com sinceridade."
    if re.search(r"\b(n[aã]o|duvid|n[ãa]o sei|talvez)\b", t):
        return f"Eu entendo sua dúvida, {nome_fmt}, e ela faz sentido."
    return f"Recebi o que você me falou agora, {nome_fmt}, e vou ser direta com você."

# ── PROMPT (mesma voz dos nodes 5 e 6; quiromancia + compromisso com o caminho) ──
_SYSTEM_AGITACAO_SUPREMA = """Você é Esmeralda Ácassia (Cigana Esmeralda), mesma presença da leitura anterior: firme, acolhedora, sem tom de telemarketing.

ESTÁGIO: AGITACAO_E_MECANISMO_UNICO (interesse e desejo depois da leitura fria)

IMPORTANTE: Nunca escreva TAG DE ESTÁGIO nem texto entre colchetes [ ] na resposta.

{norte_venda_fria}

{constituicao_camada}

DADOS DA HIVE MIND:
- Lead: {nome} | Gênero: {genero} | Concordância: {genero_hint}
- Arquétipo: {arquetipo} | Tom: {tom}
- Perfil de copy (adapte tom): {perfil_copy}
- Dor (só este resumo curto; não reproduza saudação, "me chamo" nem pergunta de preço): {dor} | Tempo de sofrimento: {tempo} | Energia: {energia}
- Mecanismo da solução (use o nome EXATO abaixo no bloco 4, entre aspas se precisar): {mecanismo}
- Nome/Pessoa envolvida no relato: {nome_pessoa_envolvida}
- Tempo exato citado pelo lead (quando houver): {tempo_exato}
- Evento gatilho citado pelo lead (quando houver): {evento_gatilho}
- Última reação do lead: "{msg_lead}"

{contexto_desejo_resultado}

RITMO WHATSAPP: cada BLOCO_N deve ser CURTO (no máximo ~3 frases ou ~160 caracteres). O sistema pode fatiar, mas escreva já pensando em balão de celular.

MISSÃO (7 BLOCOS, prefixo BLOCO_1:: … BLOCO_7::; pode continuar o texto nas linhas abaixo até o próximo BLOCO_N::; nunca coloque BLOCO_2::, BLOCO_3:: etc. no meio da mesma linha do texto anterior):
1. VALIDAÇÃO DE IMPACTO: Acolha a reação ({msg_lead}). Se a pessoa confirmou a leitura, mostre que o que veio nas linhas ressoa com o que ela sente.
2. ALÍVIO DE CULPA: O fato de sofrer com {dor} há {tempo} não é fraqueza nem "castigo merecido". Fale em nó ou padrão antigo, sem humilhar.
3. URGÊNCIA SENSATA: O tempo aperta o nó; sem terrorismo vazio, mostre que postergar também tem custo.
4. REVELAÇÃO DO MECANISMO: Nomeie o trabalho com o nome exato «{mecanismo}» como caminho de firmação **em direção ao que ela já disse que quer** (volta de alguém, separação honrosa, superar ex, novo amor, salvar o casal… conforme o relato — não empurre "volta do ex" se ela pediu outra coisa). Solenidade, não vitrine de shopping.
5. AUTORIDADE: Histórias parecidas à dela buscavam o mesmo tipo de resultado; o trabalho alinha intenção espiritual a isso, sem prometer milagre nem resultado garantido lá fora.
6. RESGATE: É compromisso com o próprio pedido (o desejo que ela trouxe), com honestidade: trabalho sério, não promessa mágica de prazo nem garantia de volta de pessoa ou de sentença.
7. CONVITE (CTA): Peça permissão, com calma, para explicar valores e como fechar o passo rumo ao que ela busca.
8. MICRO-SINS: conduza com pequenos "sim" lógicos (ressonou -> faz sentido agir -> pedir explicação do próximo passo).
9. POR QUE AGORA FUNCIONA: personalize em 1 linha usando dor + tempo + mecanismo; sem genérico.
10. ANTIBARNUM: se houver {tempo_exato} e/ou {evento_gatilho}, use de forma natural para ancorar; evite abertura genérica.
11. POTENCIAL REPRESADO: inclua um bloco sobre "você já era para estar em patamar mais alto".
12. CTA FORTE: termine pedindo permissão com pergunta de compromisso (sem "me responde sim").

REGRAS:
- Siga {genero} e {genero_hint}. Masculino: ele/dele, "meu filho" se couber. Feminino: ela/dela, "meu anjo". Indefinido: "você", "meu bem".
- Nome no máximo 2 vezes nos 7 blocos.
- Proibido travessão (—). Use reticências ou vírgulas.
- Máximo 2 emojis em todo o fluxo.
- Responda só em formato BLOCO_N::texto.
"""

def executar_v2(ctx) -> tuple:
    meta = getattr(ctx, "metadata", {}) or {}
    _seg = contexto_lead_para_nodes(ctx.nome_lead or "", meta, dor_max_len=72, desabafo_max_len=1200)
    nome_fmt = _seg["nome_fmt"]
    msg_lead = str(ctx.texto_recebido or "").strip()
    if lead_reportou_problema_entrega(msg_lead):
        ctx.estado_coleta = "node7_reparo_entrega"
        ctx.metadata = meta
        return (
            [
                Acao(tipo="delay", segundos=random.randint(3, 6)),
                Acao(
                    tipo="text",
                    conteudo=f"Obrigada por me avisar, {nome_fmt}. Vou manter tudo em balões curtos e no ritmo certo.",
                    metadata={"skip_gancho_final": True},
                ),
                Acao(tipo="delay", segundos=random.randint(2, 4)),
                Acao(
                    tipo="text",
                    conteudo="Quando estiver ok aí, me chama com *ok* que eu continuo.",
                    metadata={"skip_gancho_final": True},
                ),
            ],
            "7_interesse_desejo",
        )
    genero = genero_efetivo_para_copy(
        ctx.nome_lead or "", meta, texto_discurso=msg_lead or None
    )
    meta["genero_lead"] = genero
    genero_hint = genero_hint_para_prompt(meta)
    tts_ativo = meta.get("tts_ativo", False)
    config = meta.get("__config__", {})
    depos = config.get("depoimentos_urls", [])
    
    # Resgate da Inteligência
    arquetipo = meta.get("arquetipo_lead", "O Ferido")
    tom = meta.get("tom_cirurgico", "Maternal")
    dor_clean = _seg["resumo_dor_safe"]
    tempo = meta.get("tempo_sofrimento", "muito tempo")
    energia = meta.get("nivel_energia", "Ansioso")
    mecanismo = definir_nome_mecanismo_se_generico(meta, dor_clean)
    ctx_desejo_res = contexto_desejo_resultado_para_prompt(meta, mecanismo)
    nome_pessoa_envolvida = str(meta.get("nome_pessoa_envolvida", "INDEFINIDO") or "INDEFINIDO")
    tempo_exato = str(meta.get("tempo_exato", "INDEFINIDO") or "INDEFINIDO")
    evento_gatilho = str(meta.get("evento_gatilho", "INDEFINIDO") or "INDEFINIDO")
    perfil_copy = perfil_copy_para_prompt(meta, msg_lead)

    blocos_gerados = []

    _MIN_BLOCOS_OK = 3
    try:
        if ctx.personalizer:
            logger.info(f"🧠 [NODE 7 v17] Agitação para {nome_fmt} (gênero={genero_hint}).")
            meta_ia = dict(meta)
            meta_ia["node_copy_venda_direta"] = True
            prompt_ia = (
                f"Lead: {nome_fmt}. Reaja à última mensagem com empatia e gere os 7 blocos "
                "(BLOCO_1:: … BLOCO_7::), tom de leitura e templo, sem frase de anúncio vazio."
            )
            prompt_ia += sufixo_ancoras_node3_para_prompt(meta)
            sys_f = _SYSTEM_AGITACAO_SUPREMA.format(
                nome=nome_fmt,
                genero=genero,
                genero_hint=genero_hint,
                arquetipo=arquetipo,
                tom=tom,
                perfil_copy=perfil_copy,
                dor=dor_clean,
                tempo=tempo,
                energia=energia,
                mecanismo=mecanismo,
                nome_pessoa_envolvida=nome_pessoa_envolvida,
                tempo_exato=tempo_exato,
                evento_gatilho=evento_gatilho,
                msg_lead=msg_lead,
                contexto_desejo_resultado=ctx_desejo_res,
                norte_venda_fria=norte_editorial_venda_fria_direta_para_prompt(),
                constituicao_camada=camada_constituicao_node7(meta, mecanismo),
            )
            blocos_dict = {}
            ultima_exc: Optional[Exception] = None
            _temps = (0.88, 0.92, 0.9)
            ie = ((ctx.metadata or {}).get("__config__", {}) or {}).get("ia_economia", {}) or {}
            max_tent = max(1, min(int(ie.get("max_tentativas_ia_por_node", 2) or 2), 3))
            for tentativa in range(max_tent):
                try:
                    resposta = ctx.personalizer.gerar_resposta(
                        system_prompt=sys_f,
                        historico_lista=slice_historico_para_ia(ctx),
                        mensagem_lead=prompt_ia,
                        metadata=meta_ia,
                        max_output_tokens=6144,
                        temperature=_temps[min(tentativa, len(_temps) - 1)],
                    )
                    blocos_dict = parse_blocos_leitura_ia(resposta, max_bloco=7, min_len=8)
                    blocos_gerados = [blocos_dict.get(i, "") for i in range(1, 8) if blocos_dict.get(i)]
                    if len(blocos_gerados) < _MIN_BLOCOS_OK:
                        blocos_gerados = _extrair_blocos_fallback(resposta, max_blocos=7, min_len=8)
                    if len(blocos_gerados) >= _MIN_BLOCOS_OK:
                        break
                    raise ValueError("Agitação inconsistente.")
                except Exception as ex:
                    ultima_exc = ex
                    blocos_gerados = []
            if len(blocos_gerados) < _MIN_BLOCOS_OK:
                raise ValueError(str(ultima_exc) if ultima_exc else "Agitação inconsistente.")
        else:
            raise ValueError("IA Offline.")

    except Exception as e:
        err_txt = str(e or "").replace("aagitação", "agitação")
        logger.warning("⚠️ [NODE 7] IA incompleta (%s). Backup de agitação aplicado.", err_txt)
        meta["node7_fallback_acionado_turno"] = True
        meta["node7_fallback_motivo"] = err_txt[:180]
        dor_ctx = frase_dor_contextualizada(dor_clean, abertura="quando você traz")
        tempo_ctx = tempo_exato if tempo_exato.upper() != "INDEFINIDO" else tempo
        gatilho_ctx = (
            f" Quando você lembra de {evento_gatilho}, isso fica ainda mais evidente."
            if evento_gatilho.upper() != "INDEFINIDO"
            else ""
        )
        blocos_gerados = [
            f"O que você confirmou agora bate exatamente com o que eu vi nas linhas, {nome_fmt}. Não é impressão solta, é padrão real.",
            f"{dor_ctx}, e isso não é de hoje: há {tempo_ctx} esse ciclo vem drenando sua energia.{gatilho_ctx}",
            "Se continuar do mesmo jeito, o custo cresce em silêncio. A dor muda de roupa, mas continua no comando.",
            f"O {mecanismo} é firmação voltada ao que você pediu, com honestidade: corta o nó na raiz, sem promessa de milagre nem prazo mágico.",
            "Com o que vejo em você, já era para estar em um patamar muito mais alto do que está agora.",
            "Não é falta de fé nem de força sua. É causa ativa, ainda sem corte correto.",
            "Se eu te mostrar agora, passo a passo, como esse resgate funciona para o seu caso, você topa seguir comigo?",
        ]

    if blocos_gerados:
        b1 = str(blocos_gerados[0] or "").strip().lower()
        if not re.search(r"\b(confirm|entendo\s+sua\s+d[uú]vida|recebi\s+o\s+que\s+voc[eê]\s+falou)\b", b1):
            blocos_gerados[0] = f"{_reacao_curta_ao_input(msg_lead, nome_fmt)} {blocos_gerados[0]}".strip()

    acoes = []
    leitura_pre = max(7, min(len(msg_lead) // 22, 12))
    acoes.append(Acao(tipo="delay", segundos=leitura_pre))

    for i, conteudo_raw in enumerate(blocos_gerados):
        if not conteudo_raw: continue
        
        # 🛡️ BLINDAGEM DE TAGS: Extermínio de colchetes e formatação de IA
        conteudo_str = re.sub(r'\[.*?\]', '', str(conteudo_raw).strip())
        conteudo_str = re.sub(r'[-–—*•]+', '', conteudo_str).strip()
        conteudo_str = limpar_colagem_primeira_msg_whatsapp_em_texto(conteudo_str)
        conteudo_str = normalizar_enxerto_dor_sem_contexto(conteudo_str)
        conteudo_str = remover_marcadores_bloco_ia_vazados(conteudo_str)
        conteudo_str = unificar_vocativos_por_genero(conteudo_str, genero, nome_fmt)
        conteudo_str = aplicar_substituicoes_proibidas(conteudo_str)
        if not conteudo_str:
            continue

        num_bloco = i + 1
        pedacos = fatiar_texto_ritmo_celular(conteudo_str, max_linhas_visuais=4, chars_por_linha=38)
        eh_audio = (
            (num_bloco in _INDICES_AUDIO)
            and tts_ativo
            and ctx.personalizer is not None
            and len(pedacos) == 1
        )

        for j, pedaco in enumerate(pedacos):
            if not (pedaco or "").strip():
                continue
            delay_pre = _delay_digitacao(pedaco, eh_audio and j == 0)
            if num_bloco in _INDICES_IMPACTO:
                delay_pre += random.randint(5, 10)

            acoes.append(Acao(tipo="delay", segundos=delay_pre))

            if eh_audio and j == 0:
                acoes.append(Acao(tipo="tts", tts_template=pedaco))
                acoes.append(Acao(tipo="delay", segundos=12))
            else:
                acoes.append(Acao(tipo="text", conteudo=pedaco))
                pausa_pos = 15 if num_bloco in _INDICES_IMPACTO else 8
                acoes.append(Acao(tipo="delay", segundos=pausa_pos))

        if num_bloco == 4 and depos:
            depo_url = random.choice(depos)
            acoes += [
                Acao(tipo="delay", segundos=8),
                Acao(
                    tipo="text",
                    conteudo="Escuta o que vou te mandar agora… é um áudio de alguém que passava pela mesma provação que você:",
                ),
                Acao(tipo="delay", segundos=6),
                Acao(tipo="audio", url=depo_url),
                Acao(tipo="delay", segundos=22),
                Acao(
                    tipo="text",
                    conteudo=f"É essa leveza que eu quero ver o {mecanismo} trazer pros seus dias, {nome_fmt}. ✨",
                ),
                Acao(tipo="delay", segundos=10),
            ]

    ctx.estado_coleta = "node7_agitacao_enviada"
    ctx.metadata = meta
    logger.info(f"🔥 [NODE 7 v17] Agitação finalizada para {nome_fmt}.")
    return acoes, "8_oferta_principal"
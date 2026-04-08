"""
flows/fase_2_leitura/node_6_atencao_dinamica.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORQUESTRADOR DA LEITURA — v15 (alinhado ao Node 1: Esmeralda Ácassia, tom leitura, PT-BR)

PAPEL NO FUNIL:
  Atenção e identificação (AIDA 2): leitura fria em 12 blocos a partir da Hive Mind (Node 5).

Mantém: guard de cortes (regex), estrutura BLOCO_1..12, TTS/impacto, gênero consistente.
🔥 v15: voz Esmeralda Ácassia; genero_hint nos prompts; fallback em português do Brasil.
"""

import logging
import random
import re
from typing import Optional
from datetime import datetime, timezone, timedelta
from schema import Acao, slice_historico_para_ia
from copy_sanitizer import (
    MOBILE_CHARS_POR_LINHA,
    MOBILE_MAX_LINHAS_BALO,
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
from analytics.copy_constituicao_cigana import camada_constituicao_node6
from conversation_policy import lead_reportou_problema_entrega
from analytics.copy_personalization import (
    definir_nome_mecanismo_se_generico,
    instrucao_ancoragem_node6,
    instrucao_eco_esforco_concreto,
    perfil_copy_para_prompt,
)

logger = logging.getLogger(__name__)


# ── CONFIGURAÇÕES DE CADÊNCIA ──
DIAS_SEMANA = [
    "segunda-feira", "terça-feira", "quarta-feira",
    "quinta-feira", "sexta-feira", "sábado", "domingo"
]

# Mapeamento para TTS e Impacto (0-based)
_INDICES_AUDIO   = {1, 2, 4, 5, 6, 7, 8, 10}
_INDICES_IMPACTO = {3, 5, 9, 11} # Blocos de revelação profunda
_RE_PROBLEMA_ENTREGA = re.compile(
    r"(?i)(mensagem\s+cortad|t[aá]\s+atropel|n[aã]o\s+deu\s+tempo|"
    r"n[aã]o\s+deu\s+pra\s+ver|n[aã]o\s+carreg|travou|bugou)"
)

def _delay_digitacao(texto: str, eh_audio: bool = False, tom: str = "Maternal") -> int:
    if not texto: return 8
    base_fator = 14 if eh_audio else 18
    fator = base_fator - 2 if tom == "Autoritário" else base_fator
    return max(10, min(len(str(texto)) // fator, 28))


def _resolver_pausa_ritual_por_periodo(config: dict, hora: int) -> int:
    """
    Resolve pausa do ritual por janela horária com fallback único.
    """
    padrao = int(config.get("node6_pausa_leitura_segundos", 180) or 180)
    manha = int(config.get("node6_pausa_leitura_manha_segundos", padrao) or padrao)
    tarde = int(config.get("node6_pausa_leitura_tarde_segundos", padrao) or padrao)
    noite = int(config.get("node6_pausa_leitura_noite_segundos", padrao) or padrao)
    if hora < 12:
        val = manha
    elif hora < 18:
        val = tarde
    else:
        val = noite
    return max(45, min(val, 300))


def _extrair_blocos_fallback(texto: str, max_blocos: int = 12, min_len: int = 8) -> list[str]:
    """
    Recupera blocos quando a IA não respeita BLOCO_N::, usando [BALAO], quebras e frases.
    """
    t = (texto or "").strip()
    if not t:
        return []
    partes = re.split(r"\[?BAL[AÃ]O\]?", t, flags=re.I)
    base: list[str] = []
    for p in partes:
        p = re.sub(r"`{3}(?:json|text)?|`{3}", "", p).strip()
        if not p:
            continue
        if "\n" in p:
            for ln in p.splitlines():
                ln = ln.strip().strip("-•* ").strip()
                if len(ln) >= min_len:
                    base.append(ln)
        else:
            base.append(p)
    out: list[str] = []
    for b in base:
        b = re.sub(r"^\s*BLOCO[_\s]*\d+\s*::\s*", "", b, flags=re.I).strip()
        if len(b) >= min_len:
            out.append(b)
        if len(out) >= max_blocos:
            break
    return out[:max_blocos]


def _limpar_meta_textual(v: str, max_len: int = 220) -> str:
    t = " ".join((v or "").split()).strip()
    if not t:
        return ""
    if t.upper() in {"INDEFINIDO", "NONE", "NULL", "N/A"}:
        return ""
    return t[:max_len]


def _aplicar_framework_fechamento(blocos: list[str], nome_fmt: str) -> list[str]:
    """
    Framework de fechamento universal:
    1) Você quer resolver isso?
    2) Se eu te mostrar um caminho claro, você topa seguir?
    """
    base = [str(b or "").strip() for b in (blocos or []) if str(b or "").strip()]
    if not base:
        return [
            f"{nome_fmt}, você quer resolver isso?",
            "Se eu te mostrar um caminho claro, você topa seguir?",
        ]
    if len(base) == 1:
        return base + ["Se eu te mostrar um caminho claro, você topa seguir?"]
    base[-2] = f"{nome_fmt}, você quer resolver isso?"
    base[-1] = "Se eu te mostrar um caminho claro, você topa seguir?"
    return base


def _assinar_semantica_curta(texto: str) -> str:
    t = re.sub(r"[^a-z0-9\s]", " ", (texto or "").lower())
    toks = [w for w in t.split() if len(w) > 2]
    if not toks:
        return ""
    # assinatura curta para bloquear repetições do mesmo sentido
    return " ".join(toks[:8])

# ── PROMPT DE GERAÇÃO DA LEITURA (quiromancia, mesma voz dos nodes anteriores) ──
_SYSTEM_LEITURA_SUPREMA = """Você é Esmeralda Ácassia (Cigana Esmeralda), a mesma voz calorosa e firme da conversa: quiromancia com presença, como no templo, não como telemarketing.

ESTÁGIO: LEITURA_FRIA_SUPREMA (leitura das linhas da mão)

IMPORTANTE: Nunca escreva TAG DE ESTÁGIO nem texto entre colchetes [ ] na resposta.
RITMO WHATSAPP: cada BLOCO_N deve ser CURTO (no máximo ~3 frases ou ~160 caracteres). O sistema pode fatiar, mas escreva já pensando em balão de celular.

FIO ÚNICO (venda fria / funil): a leitura pode ser densa, mas é **uma narrativa só** ancorada na dor e no pedido que o lead já trouxe — não abra um segundo grande tema (outra área da vida, filosofia, conselho genérico) se o lead não puxou agora; isso quebra a linha até a oferta.

{constituicao_camada}

DADOS DA HIVE MIND (use tudo com respeito):
- Lead: {nome} | Gênero: {genero} | Instrução de concordância: {genero_hint}
- Arquétipo: {arquetipo} | Tom sugerido: {tom}
- Perfil de copy (adapte tom e ritmo): {perfil_copy}
- Dor (resumo curto, não repita como citação longa): {dor} | Tempo de sofrimento: {tempo} | Energia: {energia}
- Objeção silenciosa: {obj_silenciosa}
- Nome/Pessoa envolvida no relato: {nome_pessoa_envolvida}
- Tempo exato citado pelo lead (quando houver): {tempo_exato}
- Evento gatilho citado pelo lead (quando houver): {evento_gatilho}
- Dado concreto do lead para ecoar no diagnóstico (quando houver): {dado_concreto}
- Última interação: "{msg_lead}"
- Nome provisório do trabalho espiritual (use como fio condutor, pode ecoar em 1–2 blocos): {nome_mecanismo}

{instrucao_ancoragem}

{instrucao_eco_esforco}

MISSÃO: Leitura "raio-X" ancorada no que a mão mostra, ecoando a dor ({dor}) sem humilhar a pessoa.
1. MÃO EM NARRATIVA: fale do que a leitura revela como história vivida. PROIBIDO aula de quiromancia (ex.: descrever "Linha do Coração" como manual, traço contínuo vs interrompido, glossário de livro). Isso destrói autoridade.
2. ALÍVIO DE CULPA: interferências ou padrões antigos sem culpar com crueldade; tom de mesa, não acusação.
3. ANTIBARNUM: evite frases genéricas. Se houver {tempo_exato} e/ou {evento_gatilho}, use de forma natural.
3.0 CONTINUIDADE: cada bloco avança a mesma história (não repita a mesma ideia com outras palavras no bloco seguinte). Uma ideia por bloco.
4. CONSTRUÇÃO: cotidiano -> padrão que se repete -> diagnóstico (sem salto brusco).
4.1 BLOCO 4 e BLOCO 5 devem citar pelo menos 1 dado concreto do lead (frase, tempo, tentativa, evento) quando disponível.
5. POTENCIAL REPRESADO: um momento de "você já era para estar em patamar mais alto".
6. XEQUE-MATE: pergunta de confirmação forte no bloco 12 (obrigatório ?).
7. PROIBIDO somar voz de robô: nada de "eco kármico", "tessitura", "é aqui que se abre a possibilidade de uma", "nó afetivo invisível" duas vezes seguidas com a mesma ideia, nem búzios/tremor se não for o teu costume fixo na conversa.

REGRAS DE VOCATIVO (uma identidade só):
- Feminino: use "meu anjo" OU o primeiro nome, nunca misturar "meu bem" e "meu anjo".
- Masculino: "meu filho" ou nome, nunca "meu anjo".
- Indefinido: "meu bem" ou só o nome.

ESTRUTURA DOS 12 BLOCOS (prefixo exato BLOCO_1:: … BLOCO_12::; texto curto por bloco):
   - Bloco 1: Acolhimento + validação de força.
   - Bloco 2: Esforço solitário.
   - Bloco 3: Contraste do cansaço.
   - Bloco 4: Imagem viva do que a mão aponta (sem catálogo técnico de linhas).
   - Bloco 5: Padrão que volta na vida dela (sem rótulo esotérico vazio).
   - Bloco 6: Diagnóstico forte (sem deboche).
   - Bloco 7: Causa invisível.
   - Bloco 8: Injustiça vivida.
   - Bloco 9: Validação das tentativas que ela já fez (se ela citou lugares/rotinas, ecoar aqui).
   - Bloco 10: Ponte de esperança.
   - Bloco 11: Por que atalhos rasos não seguram.
   - Bloco 12: Pergunta visceral (terminar com ?).

OUTRAS REGRAS:
- Concordância: {genero_hint}
- Primeiro nome no máximo 2 vezes nos 12 blocos; no restante "você"/"seu"/"sua".
- Proibido travessão (—). Use vírgulas ou reticências.
- Tom {tom}. Autoritário: "escute bem" com respeito.
- Responda só no formato BLOCO_N::texto (sem markdown extra).
"""

def executar_v2(ctx) -> tuple:
    meta = getattr(ctx, "metadata", {}) or {}
    _seg = contexto_lead_para_nodes(ctx.nome_lead or "", meta, dor_max_len=72, desabafo_max_len=1200)
    nome_fmt = _seg["nome_fmt"]
    msg_lead = str(ctx.texto_recebido or "").strip()
    if lead_reportou_problema_entrega(msg_lead):
        ctx.estado_coleta = "node6_reparo_entrega"
        ctx.metadata = meta
        return (
            [
                Acao(tipo="delay", segundos=random.randint(3, 6)),
                Acao(
                    tipo="text",
                    conteudo=f"Perfeito, {nome_fmt}. Eu vou te mandar em partes menores e com pausa para não atropelar.",
                    metadata={"skip_gancho_final": True},
                ),
                Acao(tipo="delay", segundos=random.randint(2, 4)),
                Acao(
                    tipo="text",
                    conteudo="Me confirma com *ok* e eu retomo da leitura daqui.",
                    metadata={"skip_gancho_final": True},
                ),
            ],
            "6_atencao_dinamica",
        )
    genero = genero_efetivo_para_copy(
        ctx.nome_lead or "", meta, texto_discurso=msg_lead or None
    )
    meta["genero_lead"] = genero
    genero_hint = genero_hint_para_prompt(meta)
    tts_ativo = meta.get("tts_ativo", False)
    config = meta.get("__config__", {})
    img_altar = config.get("imagem_altar", "")
    
    # Extração de Dados do Oráculo
    arquetipo = meta.get("arquetipo_lead", "O Ferido")
    tom = meta.get("tom_cirurgico", "Maternal")
    dor_fb = _seg["resumo_dor_safe"]
    tempo = meta.get("tempo_sofrimento", "muito tempo")
    energia = meta.get("nivel_energia", "Ansioso")
    obj_silenciosa = meta.get("objecao_silenciosa", "Nenhuma")
    nome_pessoa_envolvida_raw = _limpar_meta_textual(str(meta.get("nome_pessoa_envolvida", "INDEFINIDO") or "INDEFINIDO"), 80)
    tempo_exato_raw = _limpar_meta_textual(str(meta.get("tempo_exato", "INDEFINIDO") or "INDEFINIDO"), 60)
    evento_gatilho_raw = _limpar_meta_textual(str(meta.get("evento_gatilho", "INDEFINIDO") or "INDEFINIDO"), 120)
    dado_concreto = _limpar_meta_textual(str(
        meta.get("node5_dado_concreto")
        or meta.get("node5_tentativas_previas")
        or meta.get("desejo_declarado")
        or ""
    ).strip(), 180)
    nome_pessoa_envolvida = nome_pessoa_envolvida_raw or "INDEFINIDO"
    tempo_exato = tempo_exato_raw or "INDEFINIDO"
    evento_gatilho = evento_gatilho_raw or "INDEFINIDO"

    nome_mecanismo_ctx = definir_nome_mecanismo_se_generico(meta, dor_fb)
    perfil_copy = perfil_copy_para_prompt(meta, msg_lead)
    instrucao_anc = instrucao_ancoragem_node6(nome_pessoa_envolvida, tempo_exato, evento_gatilho)
    instrucao_eco_esf = instrucao_eco_esforco_concreto(meta) or (
        "Sem detecção automática de rotinas/lugares no texto salvo: se o lead citou tentativas concretas "
        "no histórico, ainda assim ecoe com as palavras dela (não generalize)."
    )

    # 1. Ancoragem Temporal
    fuso_br = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_br)
    periodo = "nesta manhã" if agora.hour < 12 else "nesta tarde" if agora.hour < 18 else "nesta noite"
    dia = DIAS_SEMANA[agora.weekday()]
    
    saudacao_temporal = (
        f"Tenho sua mão direita aberta aqui comigo {periodo} de {dia}, {nome_fmt}… "
        "Vou te falar o que as linhas já começam a mostrar."
    )

    blocos_gerados = []

    # Leitura fria: mais tokens e mais tentativas que nodes curtos — precisa fechar 12 blocos com densidade.
    _MIN_BLOCOS_OK = 5
    _MAX_OUT_TOKENS_NODE6 = 8192
    try:
        if ctx.personalizer:
            logger.info(f"🧠 [NODE 6 v15] Leitura para {nome_fmt} (gênero={genero_hint}).")
            meta_ia = dict(meta)
            meta_ia["node_leitura_profunda"] = True
            prompt_ia = (
                f"Lead: {nome_fmt}. Gere agora os 12 blocos (BLOCO_1:: … BLOCO_12::), "
                "tom de leitura das linhas, sem frases genéricas de propaganda. "
                f"O trabalho espiritual já tem nome provisório: «{nome_mecanismo_ctx}» — pode ecoar com leveza, sem vender ainda."
            )
            prompt_ia += sufixo_ancoras_node3_para_prompt(meta)
            sys_f = _SYSTEM_LEITURA_SUPREMA.format(
                nome=nome_fmt,
                genero=genero,
                genero_hint=genero_hint,
                arquetipo=arquetipo,
                tom=tom,
                perfil_copy=perfil_copy,
                dor=dor_fb,
                tempo=tempo,
                energia=energia,
                obj_silenciosa=obj_silenciosa,
                nome_pessoa_envolvida=nome_pessoa_envolvida,
                tempo_exato=tempo_exato,
                evento_gatilho=evento_gatilho,
                dado_concreto=dado_concreto or "INDEFINIDO",
                msg_lead=msg_lead,
                nome_mecanismo=nome_mecanismo_ctx,
                instrucao_ancoragem=instrucao_anc,
                instrucao_eco_esforco=instrucao_eco_esf,
                constituicao_camada=camada_constituicao_node6(meta, nome_mecanismo_ctx),
            )
            blocos_dict = {}
            ultima_exc: Optional[Exception] = None
            _temps = (0.86, 0.9, 0.88)
            ie = ((ctx.metadata or {}).get("__config__", {}) or {}).get("ia_economia", {}) or {}
            max_tent = max(1, min(int(ie.get("max_tentativas_ia_por_node", 2) or 2), 3))
            for tentativa in range(max_tent):
                try:
                    resposta = ctx.personalizer.gerar_resposta(
                        system_prompt=sys_f,
                        historico_lista=slice_historico_para_ia(ctx),
                        mensagem_lead=prompt_ia,
                        metadata=meta_ia,
                        max_output_tokens=_MAX_OUT_TOKENS_NODE6,
                        temperature=_temps[min(tentativa, len(_temps) - 1)],
                    )
                    blocos_dict = parse_blocos_leitura_ia(resposta, max_bloco=12, min_len=8)
                    blocos_gerados = [blocos_dict.get(i, "") for i in range(1, 13) if blocos_dict.get(i)]
                    if len(blocos_gerados) < _MIN_BLOCOS_OK:
                        blocos_gerados = _extrair_blocos_fallback(resposta, max_blocos=12, min_len=8)
                    if len(blocos_gerados) >= _MIN_BLOCOS_OK:
                        break
                    raise ValueError("Leitura muito curta ou formato inválido.")
                except Exception as ex:
                    ultima_exc = ex
                    blocos_gerados = []
            if len(blocos_gerados) < _MIN_BLOCOS_OK:
                raise ValueError(str(ultima_exc) if ultima_exc else "Leitura muito curta ou formato inválido.")
        else:
            raise ValueError("IA Offline.")

    except Exception as e:
        err_txt = str(e or "").replace("inváliido", "inválido").replace("inv\u00e1liido", "inválido")
        logger.warning("⚠️ [NODE 6] IA incompleta (%s). Fallback místico aplicado.", err_txt)
        meta["node6_fallback_acionado_turno"] = True
        meta["node6_fallback_motivo"] = err_txt[:180]
        dor_ctx = frase_dor_contextualizada(dor_fb, abertura="Quando você me diz")
        tempo_ctx = tempo_exato if tempo_exato.upper() != "INDEFINIDO" else tempo
        gatilho_ctx = (
            f" Quando você lembra de {evento_gatilho}, esse padrão fica ainda mais nítido."
            if evento_gatilho.upper() != "INDEFINIDO"
            else ""
        )
        eco_dado = (
            f"Você mesma(o) trouxe isso com clareza: {dado_concreto}."
            if dado_concreto
            else ""
        )
        blocos_gerados = [
            f"O que aparece primeiro nas suas linhas, {nome_fmt}, é força de construção: você levantou muita coisa com as próprias mãos.",
            "Mas tem dias em que o peso chega antes da manhã abrir, e você segue firme sem mostrar tudo por dentro.",
            f"Isso não nasceu ontem. Há {tempo_ctx}, esse fio se repete: você se entrega, algo interrompe, e fica tentando entender onde travou.{gatilho_ctx}",
            f"{dor_ctx} {eco_dado} As linhas não mostram fraqueza sua; mostram um vínculo mal encerrado que mantém o ciclo rodando.",
            "Esse nó não fica só no amor: ele vaza para decisões, energia e foco, mesmo quando você tenta seguir em frente.",
            "O que está travando não saiu de dentro de você. Entrou de fora, e foi se firmando em silêncio.",
            "Com o que vejo aqui, você já era pra estar em um patamar muito mais alto do que está hoje.",
            "Esse bloqueio está represando caminho, resultado e paz, como se segurasse aquilo que já era seu por direito.",
            f"Você já tentou por conta própria e não viu o resultado que queria. Não é falta de fé, é causa não tocada na raiz.",
            f"Eu não trabalho com promessa vazia. O que fecha com o que a mão mostra é o {nome_mecanismo_ctx}: corte na raiz, não maquiagem.",
            "Respira comigo: o que vem depois é objetivo, sem teatro, para destravar o que está preso.",
            f"Isso está longe da sua realidade, {nome_fmt}… ou tocou exatamente onde dói?",
        ]

    blocos_gerados = _aplicar_framework_fechamento(blocos_gerados, nome_fmt)
    acoes = []
    
    if img_altar:
        acoes.append(Acao(tipo="image", url=img_altar))
        acoes.append(Acao(tipo="delay", segundos=random.randint(6, 9)))
    
    # Ritual de leitura: pausa perceptível antes de entregar os blocos (por janela horária).
    pausa_leitura = _resolver_pausa_ritual_por_periodo(config, agora.hour)
    acoes.append(Acao(tipo="delay", segundos=random.randint(7, 10)))
    acoes.append(Acao(tipo="text", conteudo=saudacao_temporal))
    acoes.append(Acao(tipo="delay", segundos=random.randint(5, 8)))
    acoes.append(
        Acao(
            tipo="text",
            conteudo="Me dá 3 minutinhos rapidinho, que eu já te entrego a leitura completa. 🔮",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=pausa_leitura))

    # Expressão Regular Expandida contra QUALQUER palavra de conexão que fique pendurada no final
    regex_corte_fatal = r'([,;:-]|\b(e|mas|ou|que|de|da|do|em|no|na|seu|sua|meu|minha|o|a|os|as|um|uma|com|por|para|se|é|são|sao|foi|vai|como|quando|onde|porque|qual|quem|pelo|pela|dos|das|nos|nas|este|esta|esse|essa|isso|isto|aquilo|aquele|aquela|sendo|tendo|estando))\s*$'

    assinaturas_vistas = set()
    for i, conteudo_raw in enumerate(blocos_gerados):
        if not conteudo_raw: continue
        
        # 🛡️ BLINDAGEM DE TAGS E CARACTERES TÉCNICOS
        conteudo_str = re.sub(r'\[.*?\]', '', str(conteudo_raw).strip())
        conteudo_str = re.sub(r'[-–—*•]+', '', conteudo_str).strip()
        conteudo_str = limpar_colagem_primeira_msg_whatsapp_em_texto(conteudo_str)
        conteudo_str = normalizar_enxerto_dor_sem_contexto(conteudo_str)
        conteudo_str = remover_marcadores_bloco_ia_vazados(conteudo_str)
        conteudo_str = unificar_vocativos_por_genero(conteudo_str, genero, nome_fmt)
        conteudo_str = aplicar_substituicoes_proibidas(conteudo_str)
        assinatura = _assinar_semantica_curta(conteudo_str)
        if assinatura and assinatura in assinaturas_vistas:
            logger.info("event=node6_bloco_suprimido_redundancia bloco=%s", i + 1)
            continue
        if assinatura:
            assinaturas_vistas.add(assinatura)

        # 🛡️ SMART COMPLETION GUARD v5 (O Exterminador de Cortes)
        if len(conteudo_str) < 5 or re.search(regex_corte_fatal, conteudo_str.lower()):
            logger.warning(f"⚠️ [NODE 6] Bloco {i+1} ignorado por corte prematuro ou palavra pendurada: '{conteudo_str}'")
            continue
        
        num_bloco = i + 1
        pedacos = fatiar_texto_ritmo_celular(
            conteudo_str,
            max_linhas_visuais=MOBILE_MAX_LINHAS_BALO,
            chars_por_linha=MOBILE_CHARS_POR_LINHA,
        )
        eh_audio = (
            (num_bloco in _INDICES_AUDIO)
            and tts_ativo
            and ctx.personalizer is not None
            and len(pedacos) == 1
        )

        for j, pedaco in enumerate(pedacos):
            if not (pedaco or "").strip():
                continue
            delay_pre = _delay_digitacao(pedaco, eh_audio and j == 0, tom)
            if num_bloco in _INDICES_IMPACTO:
                delay_pre += random.randint(6, 12)

            acoes.append(Acao(tipo="delay", segundos=delay_pre))

            if eh_audio and j == 0:
                acoes.append(Acao(tipo="tts", tts_template=pedaco))
                acoes.append(Acao(tipo="delay", segundos=14))
            else:
                acoes.append(Acao(tipo="text", conteudo=pedaco))
                pausa_pos = 16 if num_bloco in _INDICES_IMPACTO else 9
                acoes.append(Acao(tipo="delay", segundos=pausa_pos))

    ctx.estado_coleta = "node6_leitura_enviada"
    ctx.metadata = meta
    logger.info(f"🔮 [NODE 6 v15] Leitura enviada para {nome_fmt}.")
    return acoes, "7_interesse_desejo"
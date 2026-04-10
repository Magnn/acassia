"""
config_cliente.py — SUPREME v1.5 (SOVEREIGN MAPPING & CLEAN BOOT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Configuração centralizada com mapeamento inteligente entre nomes de elite 
do .env e chaves técnicas do motor de estados.

🔥 UPGRADES DESTA VERSÃO (v1.5):
  1. PONTE DE ELITE: Mapeia automaticamente 'CLIENTE_PASSO_FE' para 'preco_materiais'
     e 'CLIENTE_HONORARIO_SUCESSO' para 'preco_servico'.
  2. SILÊNCIO TÉCNICO: Remove avisos de conversão desnecessários no boot do app.py.
  3. HIGIENIZAÇÃO RADICAL: Remove aspas, espaços e caracteres invisíveis que 
     costumam corromper valores vindos do .env no Windows.
  4. FALLBACK INTELIGENTE: Se o .env estiver incompleto, assume os valores da 
     estratégia de 65+65 de forma silenciosa.
"""

import os
import re
import logging
from dotenv import load_dotenv

# .env na pasta do projeto (não depende do cwd ao subir o Flask de outro diretório)
_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_ROOT, ".env"))
load_dotenv()  # cwd pode sobrescrever em dev

logger = logging.getLogger(__name__)

# ── Defaults da biblioteca de pontes (copy aprovada — sobrescreva via .env se quiser) ──
_DEFAULT_PONTES: dict = {
    "preco_fora_da_ordem": (
        "Eu te entendo querendo saber valores — isso mostra que você já tá considerando dar esse passo. "
        "Aqui a gente primeiro alinha energia e contexto; o investimento eu te explico na hora certa, com tudo que tá incluso, sem surpresa."
    ),
    "desconfianca": (
        "É normal desconfiar no começo, principalmente quando a dor tá alta. "
        "Eu não prometo milagre de novela — meu trabalho é leitura honesta e acolhimento. "
        "Você vai sentindo o meu jeito nas mensagens; se não fizer sentido, você para."
    ),
    "multi_topico": (
        "Vou responder ponto a ponto pra nada ficar no ar — depois a gente segue o passo desta etapa com calma."
    ),
    "reancorar_apos_resposta": (
        "Agora que clareamos isso: me conta [um detalhe da etapa atual] pra eu te acompanhar direitinho."
    ),
    "pos_oferta_sem_pressao": (
        "Quando você quiser dar o passo, eu te mando o caminho com calma — sem pressão de shopping."
    ),
    "ponte_geral": (
        "O que importa agora é você se sentir acolhida(o) e eu entender sua história com respeito."
    ),
}


def _normalizar_url_https(val: str) -> str:
    """
    Garante esquema https:// para links do .env (Cakto, Instagram, etc.).
    Evita URLs sem protocolo, que no WhatsApp muitas vezes não abrem ao toque.
    Remove espaços internos (evita https://www. instagram .com colado no .env).
    """
    s = re.sub(r"\s+", "", (val or "").strip())
    if not s or s.startswith("["):
        return s
    if s.lower().startswith("https://"):
        return s
    if s.lower().startswith("http://"):
        return "https://" + s[len("http://") :]
    if s.lower().startswith("www."):
        return "https://" + s
    if re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}", s):
        return "https://" + s
    return s


def _obter_limpo(key: str, fallback_key: str = None, default: str = "") -> str:
    """Busca o valor no env, limpa impurezas e tenta a chave secundária."""
    val = os.getenv(key)
    if val is None and fallback_key:
        val = os.getenv(fallback_key)
    
    if val is None:
        return str(default).strip()
    
    # Remove aspas duplas, simples e espaços laterais (comum em erros de .env)
    return str(val).replace('"', '').replace("'", "").strip()

def carregar() -> dict:
    """
    Carrega a inteligência comercial do cliente injetando-a no metadata do bot.
    """
    
    # ── MAPEAMENTO DE PREÇOS (Ponte de Elite) ──
    # Prioriza os nomes sofisticados do .env v8.7
    p_mat  = _obter_limpo("CLIENTE_PASSO_FE",         "CLIENTE_PRECO_MATERIAIS", "65")
    p_serv = _obter_limpo("CLIENTE_HONORARIO_SUCESSO", "CLIENTE_PRECO_SERVICO",   "65")
    p_orig = _obter_limpo("CLIENTE_VALOR_TOTAL",       "CLIENTE_PRECO_ORIGINAL",  "360")
    
    # ── MAPEAMENTO DE LINKS E MÍDIA ──
    # Checkout por ticket (A/B): CHECKOUT_URL_65 / _100 / _130 — alinhados ao node8_ticket_atual.
    checkout_urls: dict[str, str] = {}
    for _tk in (130, 100, 65, 50, 40, 30):
        _raw_tk = _obter_limpo(f"CHECKOUT_URL_{_tk}", None, "").strip()
        if _raw_tk:
            checkout_urls[str(_tk)] = _normalizar_url_https(_raw_tk)

    # Checkout único (fallback genérico e negociação sem URL específica).
    _chk = (
        _obter_limpo("LINK_CHECKOUT", "CHECKOUT_URL", "")
        or _obter_limpo("CAKTO_CHECKOUT_URL", "CLIENTE_LINK_PAGAMENTO", "")
    )
    if _chk:
        link_pgto = _normalizar_url_https(_chk)
    elif checkout_urls:
        # Sem LINK_CHECKOUT: usa faixa “cheia” como default (130 > 100 > 65).
        link_pgto = (
            checkout_urls.get("130")
            or checkout_urls.get("100")
            or checkout_urls.get("65")
            or next(iter(checkout_urls.values()))
        )
    else:
        link_pgto = "[LINK_NÃO_CONFIGURADO]"

    _link_ds_raw = _obter_limpo("CLIENTE_LINK_DOWNSELL", None, "").strip()
    if not _link_ds_raw:
        _link_ds_raw = link_pgto
    link_downsell = _normalizar_url_https(_link_ds_raw)

    _ig_raw = _obter_limpo("LINK_INSTAGRAM", "CLIENTE_LINK_PROVA_SOCIAL", "") or _obter_limpo(
        "INSTAGRAM_URL", "URL_INSTAGRAM", "https://www.instagram.com/meumisterio_oficial/"
    )
    link_prova_social = _normalizar_url_https(_ig_raw) if _ig_raw else ""

    # Foto do perfil (Node 4): .env explícito OU, se existir ficheiro em assets/, URL = PUBLIC_URL + caminho.
    # A Meta só aceita https acessível publicamente (não use 127.0.0.1 em produção).
    _img_ig_raw = (
        _obter_limpo("CLIENTE_IMAGEM_PERFIL_INSTAGRAM", "IMAGEM_PERFIL_INSTAGRAM_URL", "")
        or _obter_limpo("CLIENTE_IMAGEM_INSTAGRAM", "INSTAGRAM_PROFILE_IMAGE_URL", "")
        or _obter_limpo("CLIENTE_FOTO_PERFIL_INSTAGRAM", None, "")
    ).strip()
    _bundled_ig_profile = os.path.join(_ROOT, "assets", "instagram", "perfil_meumisterio.png")
    if not _img_ig_raw and os.path.isfile(_bundled_ig_profile):
        _pub_base = (_obter_limpo("PUBLIC_URL", None, "") or "").strip().rstrip("/")
        if _pub_base.startswith(("http://", "https://")):
            _img_ig_raw = f"{_pub_base}/assets/instagram/perfil_meumisterio.png"

    # Cakto API (OAuth2 + recursos products/offers/orders/webhooks)
    cakto_base_url = _obter_limpo("CAKTO_BASE_URL", None, "https://api.cakto.com.br")
    cakto_client_id = _obter_limpo("CAKTO_CLIENT_ID", None, "")
    cakto_client_secret = _obter_limpo("CAKTO_CLIENT_SECRET", None, "")
    cakto_offer_id = _obter_limpo("CAKTO_OFFER_ID", None, "")
    cakto_offer_slug = _obter_limpo("CAKTO_OFFER_SLUG", None, "")
    cakto_webhook_secret = _obter_limpo("CAKTO_WEBHOOK_SECRET", None, "")
    cakto_offer_id_130 = _obter_limpo("CAKTO_OFFER_ID_130", None, "")
    cakto_offer_id_100 = _obter_limpo("CAKTO_OFFER_ID_100", None, "")
    cakto_offer_id_65 = _obter_limpo("CAKTO_OFFER_ID_65", None, "")
    cakto_offer_id_50 = _obter_limpo("CAKTO_OFFER_ID_50", None, "")
    cakto_offer_id_40 = _obter_limpo("CAKTO_OFFER_ID_40", None, "")
    cakto_offer_id_30 = _obter_limpo("CAKTO_OFFER_ID_30", None, "")

    raw_urls = _obter_limpo("CLIENTE_DEPOIMENTOS_URLS", "", "")
    depoimentos = (
        [_normalizar_url_https(u.strip()) for u in raw_urls.split(",") if u.strip()]
        if raw_urls
        else []
    )

    tts_raw = _obter_limpo("CLIENTE_TTS_ATIVO", "", "false").lower()
    tts_ativo = tts_raw in ("true", "1", "yes", "sim")

    # Perfil de negócio (base para multi-tenant / wizard — preencher via .env)
    perfil_negocio = {
        "slug": _obter_limpo("NEGOCIO_SLUG", "CLIENTE_SLUG", "cigana_piloto"),
        "nome_exibicao": _obter_limpo("NEGOCIO_NOME", "CLIENTE_NOME_EXIBICAO", "Cigana Esmeralda"),
        "vertical": _obter_limpo("NEGOCIO_VERTICAL", None, "consultoria_mistica"),
        "oferta_resumo": _obter_limpo("NEGOCIO_OFERTA_RESUMO", None, "Leitura guiada + ritual personalizado no WhatsApp"),
        "publico_hint": _obter_limpo("NEGOCIO_PUBLICO", None, "Pessoas em crise afetiva buscando clareza"),
        "para_quem_nao_e": _obter_limpo("NEGOCIO_NAO_E", None, "Quem busca garantia mágica instantânea ou substituto de terapia/psiquiatria"),
        "promessa_principal": _obter_limpo("NEGOCIO_PROMESSA", None, "Clareza simbólica e acolhimento honesto no WhatsApp — sem prometer o que não é da consulta"),
        "prova_curta": _obter_limpo("NEGOCIO_PROVA_CURTA", None, "Trabalho contínuo no Instagram e depoimentos reais de quem passou pelo ritual"),
        "tom_voz": _obter_limpo("NEGOCIO_TOM_VOZ", None, "acolhedor_mistico"),
        "moeda": _obter_limpo("NEGOCIO_MOEDA", None, "BRL"),
        "timezone": _obter_limpo("NEGOCIO_TIMEZONE", None, "America/Manaus"),
    }

    pontes_copy = dict(_DEFAULT_PONTES)
    # Overrides opcionais via .env (texto longo — use aspas no .env se necessário)
    ov = _obter_limpo("PONTE_PRECO_FORA_ORDEM", None, "")
    if ov:
        pontes_copy["preco_fora_da_ordem"] = ov
    ov = _obter_limpo("PONTE_DESCONFIANCA", None, "")
    if ov:
        pontes_copy["desconfianca"] = ov
    ov = _obter_limpo("PONTE_MULTI_TOPICO", None, "")
    if ov:
        pontes_copy["multi_topico"] = ov

    copy_guardrails = {
        "tom_evitar": [
            x.strip()
            for x in _obter_limpo("COPY_EVITAR_TOM", None, "").split(",")
            if x.strip()
        ]
        or [
            "URGENTE HOJE",
            "última chance",
            "golpe",
            "garantido 100%",
            "cura garantida",
            "você vai ficar rico",
        ],
        "nao_prometer": _obter_limpo(
            "COPY_NAO_PROMETER",
            None,
            "cura de doença, substituição de tratamento médico, resultado financeiro garantido",
        ),
    }

    def _int_seguro(key: str, default: int) -> int:
        try:
            return int(_obter_limpo(key, None, str(default)) or str(default))
        except ValueError:
            return default

    def _float_seguro(key: str, default: float) -> float:
        try:
            return float(_obter_limpo(key, None, str(default)) or str(default))
        except ValueError:
            return default

    compliance = {
        "respeitar_opt_out": True,
        "limite_recovery_ciclos_sugerido": _int_seguro("COMPLIANCE_MAX_RECOVERY_CICLOS", 3),
        "intervalo_min_entre_recovery_min": _int_seguro("COMPLIANCE_MIN_MIN_ENTRE_RECOVERY", 5),
        "documentacao": "Lead pode pedir exclusão/parar; não insistir após opt-out. Frequência: recovery já limitado pelo motor.",
    }

    # Montagem do Dicionário de Configuração
    config = {
        "perfil_negocio": perfil_negocio,
        "pontes_copy": pontes_copy,
        "copy_guardrails": copy_guardrails,
        "compliance": compliance,
        "recovery_max_leads_por_ciclo": _int_seguro("RECOVERY_MAX_LEADS_POR_CICLO", 120),
        "inbox_max_concorrencia_processamento": _int_seguro("INBOX_MAX_CONCORRENCIA_PROCESSAMENTO", 24),
        "inbox_max_retries_busy": _int_seguro("INBOX_MAX_RETRIES_BUSY", 8),
        "inbox_max_tamanho_fila_por_lead": _int_seguro("INBOX_MAX_TAMANHO_FILA_POR_LEAD", 96),
        # Legado: micro-espera (ainda usada só se inbox_silence_seconds=0 em alguns fluxos internos).
        "inbox_coalesce_seconds": max(1, min(_int_seguro("INBOX_COALESCE_SECONDS", 3), 12)),
        # Sem silêncio do lead por N segundos, não dispara o motor (lê o lote completo antes).
        # Funil estático: controla a espera após a última mensagem antes de avançar (ex.: B3→B4).
        "inbox_silence_seconds": max(0, min(_int_seguro("INBOX_SILENCE_SECONDS", 18), 120)),
        # Após o lote principal: espera extra só para texto longo (imagem costuma chegar em webhook separado).
        "inbox_after_text_grace_seconds": max(0, min(_int_seguro("INBOX_AFTER_TEXT_GRACE_SECONDS", 20), 60)),
        "inbox_after_text_grace_min_chars": max(20, min(_int_seguro("INBOX_AFTER_TEXT_GRACE_MIN_CHARS", 40), 2000)),
        # Log de "node lento" no engine (nodes com Gemini costumam 4–10s; default 3.5 gerava ruído)
        "node_exec_sla_warn_seconds": max(
            2.0,
            min(_float_seguro("NODE_EXEC_SLA_WARN_SECONDS", 6.0), 60.0),
        ),
        # URL pública do app (https) — mídias em /assets/... para WhatsApp Cloud API
        "public_url": (_obter_limpo("PUBLIC_URL", None, "") or "").strip().rstrip("/"),
        # Funil estático B3: URL completa do .ogg (opcional; senão usa PUBLIC_URL + path do roteiro)
        "audio_bloco3_url": (_obter_limpo("CLIENTE_AUDIO_BLOCO3_URL", None, "") or "").strip(),
        "audio_bloco4_principal": (_obter_limpo("CLIENTE_AUDIO_BLOCO4", "CLIENTE_AUDIO_BLOCO4_PRINCIPAL", "") or "").strip(),
        "audio_bloco4_d1": (_obter_limpo("CLIENTE_AUDIO_BLOCO4_D1", None, "") or "").strip(),
        "audio_bloco4_d2": (_obter_limpo("CLIENTE_AUDIO_BLOCO4_D2", None, "") or "").strip(),
        "audio_bloco4_d3": (_obter_limpo("CLIENTE_AUDIO_BLOCO4_D3", None, "") or "").strip(),
        "audio_bloco5_url": (_obter_limpo("CLIENTE_AUDIO_BLOCO5_URL", None, "") or "").strip(),
        "link_pagamento_b5": (_obter_limpo("LINK_PAGAMENTO_B5", "CLIENTE_LINK_PAGAMENTO_B5", "") or "").strip(),
        "audio_bloco6_a": (_obter_limpo("CLIENTE_AUDIO_BLOCO6_A", None, "") or "").strip(),
        "audio_bloco6_b": (_obter_limpo("CLIENTE_AUDIO_BLOCO6_B", None, "") or "").strip(),
        "audio_bloco6_c": (_obter_limpo("CLIENTE_AUDIO_BLOCO6_C", None, "") or "").strip(),
        "audio_bloco6_d": (_obter_limpo("CLIENTE_AUDIO_BLOCO6_D", None, "") or "").strip(),
        "audio_bloco7_01": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_01", None, "") or "").strip(),
        "audio_bloco7_02": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_02", None, "") or "").strip(),
        "audio_bloco7_03": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_03", None, "") or "").strip(),
        "audio_bloco7_04": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_04", None, "") or "").strip(),
        "audio_bloco7_05": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_05", None, "") or "").strip(),
        "audio_bloco7_06": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_06", None, "") or "").strip(),
        "audio_bloco7_07": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_07", None, "") or "").strip(),
        "audio_bloco7_08": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_08", None, "") or "").strip(),
        "audio_bloco7_09": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_09", None, "") or "").strip(),
        "audio_bloco7_10": (_obter_limpo("CLIENTE_AUDIO_BLOCO7_10", None, "") or "").strip(),
        # Indicadores typing na API Cloud (muitas contas devolvem #100 — default desligado)
        "whatsapp_typing_enabled": (
            _obter_limpo("WHATSAPP_TYPING_ENABLED", None, "0").lower() in ("1", "true", "yes", "sim")
        ),
        # Novo lead: "1_apresentacao" (padrão Cigana) ou "static_meumisterio_b1" (funil estático Meu Mistério)
        "funil_entrada_inicial": (_obter_limpo("FUNIL_ENTRADA_INICIAL", None, "") or "").strip(),

        # Identidade
        "numero_whatsapp": _obter_limpo("CLIENTE_NUMERO_WHATSAPP", None, "+55 92 8497-9419"),

        # Valores Estratégicos (Mantidos como string para formatação direta na copy)
        "preco_materiais": p_mat,
        "preco_servico":   p_serv,
        "preco_original":  p_orig,
        "dias_resultado":  _obter_limpo("CLIENTE_DIAS_RESULTADO", None, "5 a 7"),

        # Links e Prova Social
        "link_pagamento":    link_pgto,
        "checkout_urls":     checkout_urls,
        "link_downsell":     link_downsell,
        "link_prova_social": link_prova_social,
        "imagem_perfil_instagram": _img_ig_raw,
        "imagem_altar":      _obter_limpo("CLIENTE_IMAGEM_ALTAR", None, ""),
        "depoimentos_urls":  depoimentos,
        "cakto": {
            "base_url": cakto_base_url,
            "client_id": cakto_client_id,
            "client_secret": cakto_client_secret,
            "offer_id": cakto_offer_id,
            "offer_slug": cakto_offer_slug,
            "offer_id_map": {
                "130": cakto_offer_id_130,
                "100": cakto_offer_id_100,
                "65": cakto_offer_id_65,
                "50": cakto_offer_id_50,
                "40": cakto_offer_id_40,
                "30": cakto_offer_id_30,
            },
            "webhook_secret": cakto_webhook_secret,
            "enabled": bool(cakto_client_id and cakto_client_secret),
            # Webhook /webhook/cakto (venda aprovada): disjuntor — não dispara `iniciar_fluxo_post_venda` para funil IA
            # por defeito; mantém disparo para leads em `static_meumisterio_*`.
            "webhook_dispara_pos_venda_ia": _obter_limpo("CAKTO_WEBHOOK_POS_VENDA_IA", None, "0").lower()
            in ("1", "true", "yes", "sim"),
            "webhook_dispara_pos_venda_funil_estatico": _obter_limpo(
                "CAKTO_WEBHOOK_POS_VENDA_FUNIL_ESTATICO", None, "1"
            ).lower()
            in ("1", "true", "yes", "sim"),
        },

        # IA e Speech
        "tts_ativo": tts_ativo,
        "modelo_ia": _obter_limpo("CLIENTE_MODELO_IA", None, "gemini-2.5-flash"),
        "modelo_stt": _obter_limpo("CLIENTE_MODELO_STT", "MODELO_STT", "gemini-2.5-flash"),
        # Node 6: pausa ritual antes da leitura (segundos)
        "node6_pausa_leitura_segundos": _int_seguro("NODE6_PAUSA_LEITURA_SEGUNDOS", 180),
        "node6_pausa_leitura_manha_segundos": _int_seguro("NODE6_PAUSA_LEITURA_MANHA_SEGUNDOS", 180),
        "node6_pausa_leitura_tarde_segundos": _int_seguro("NODE6_PAUSA_LEITURA_TARDE_SEGUNDOS", 120),
        "node6_pausa_leitura_noite_segundos": _int_seguro("NODE6_PAUSA_LEITURA_NOITE_SEGUNDOS", 90),

        # Node 1: última vaga gratuita (consulta inicial) — desligue com false se não quiser usar
        "node1_vaga_gratis": {
            "ativo": _obter_limpo("CLIENTE_NODE1_VAGA_GRATIS", None, "true").lower()
            in ("true", "1", "yes", "sim"),
            "texto_override": _obter_limpo("CLIENTE_NODE1_COPY_VAGA_GRATIS", None, ""),
        },
        # Node 1: estratégia de abertura (safe|adaptive|auto)
        "node1_modo_abertura": (_obter_limpo("NODE1_MODO_ABERTURA", None, "safe") or "safe").strip().lower(),
        "node1_adaptive_min_chars": max(4, min(_int_seguro("NODE1_ADAPTIVE_MIN_CHARS", 10), 240)),
        # Controle de custo de IA por lead (aproximação por caracteres/tokens)
        "ia_economia": {
            "orcamento_tokens_por_lead": _int_seguro("IA_ORCAMENTO_TOKENS_POR_LEAD", 12000),
            "modo_economico_ratio": float(_obter_limpo("IA_MODO_ECONOMICO_RATIO", None, "0.8") or "0.8"),
            "max_tentativas_ia_por_node": _int_seguro("IA_MAX_TENTATIVAS_POR_NODE", 2),
            "max_output_tokens_default": _int_seguro("IA_MAX_OUTPUT_TOKENS_DEFAULT", 900),
            "max_output_tokens_por_node": {
                "1_apresentacao": _int_seguro("IA_MAX_OUTPUT_NODE1", 700),
                "2_salvar_contato": _int_seguro("IA_MAX_OUTPUT_NODE2", 700),
                "3_coleta_profunda": _int_seguro("IA_MAX_OUTPUT_NODE3", 900),
                "4_instagram": _int_seguro("IA_MAX_OUTPUT_NODE4", 1100),
                "5_processa_leitura": _int_seguro("IA_MAX_OUTPUT_NODE5", 1100),
                "6_atencao_dinamica": _int_seguro("IA_MAX_OUTPUT_NODE6", 2200),
                "7_interesse_desejo": _int_seguro("IA_MAX_OUTPUT_NODE7", 1800),
                "8_oferta_principal": _int_seguro("IA_MAX_OUTPUT_NODE8", 1600),
                "9_recuperacao": _int_seguro("IA_MAX_OUTPUT_NODE9", 1000),
            },
        },
    }

    # Funil estático Meu Mistério no mesmo número WABA: novos leads entram em static_meumisterio_b1
    # e o motor não chama NLU/Gemini nos nodes (personalizer=None). Desligue com FUNIL_ESTATICO_ATIVO=0.
    _fe_raw = (_obter_limpo("FUNIL_ESTATICO_ATIVO", None, "") or "").strip().lower()
    _funil_estatico_ativo = _fe_raw in ("1", "true", "yes", "sim", "on")
    if _funil_estatico_ativo:
        config["funil_estatico_meu_misterio_ativo"] = True
        config["ia_motor_desligada"] = True
        config["funil_entrada_inicial"] = "static_meumisterio_b1"
    else:
        config["funil_estatico_meu_misterio_ativo"] = False
        config["ia_motor_desligada"] = False

    # ── LOGGING IMPERIAL DE BOOT ──
    _chk_ok = "[LINK" not in config["link_pagamento"]
    _ig_ok = bool((config.get("link_prova_social") or "").strip())
    logger.info(
        f"✅ [CONFIG v1.5] Império Carregado: "
        f"PassoFé=R${config['preco_materiais']} | "
        f"Honorário=R${config['preco_servico']} | "
        f"Total={config['preco_original']}"
    )
    logger.info(
        "📎 [CONFIG] Links: checkout=%s | instagram=%s | inbox silence=%ss grace_midia=%ss busy_retries=%s fila_max=%s",
        "ok" if _chk_ok else "FALTANDO",
        "ok" if _ig_ok else "vazio",
        config.get("inbox_silence_seconds"),
        config.get("inbox_after_text_grace_seconds"),
        config.get("inbox_max_retries_busy"),
        config.get("inbox_max_tamanho_fila_por_lead"),
    )
    if config.get("checkout_urls"):
        logger.info(
            "📎 [CONFIG] CHECKOUT_URL_* por faixa (R$): %s",
            ", ".join(sorted(config["checkout_urls"].keys(), key=lambda x: int(x))),
        )
    logger.info(
        "🧾 [CONFIG] Cakto API: %s | offer_id=%s | offer_slug=%s | webhook_pos_venda_ia=%s | webhook_pos_venda_estatico=%s",
        "ok" if config["cakto"]["enabled"] else "desativada",
        "ok" if config["cakto"]["offer_id"] else "vazio",
        "ok" if config["cakto"]["offer_slug"] else "vazio",
        config["cakto"].get("webhook_dispara_pos_venda_ia"),
        config["cakto"].get("webhook_dispara_pos_venda_funil_estatico"),
    )
    if config.get("funil_estatico_meu_misterio_ativo"):
        logger.info(
            "🧭 [CONFIG] FUNIL_ESTATICO_ATIVO=1 — novos leads → static_meumisterio_b1; "
            "NLU/personalizer do motor desligados. Volte ao funil IA com FUNIL_ESTATICO_ATIVO=0 e reinicie o processo."
        )

    if not config["imagem_altar"]:
        logger.debug("CLIENTE_IMAGEM_ALTAR ausente — altar sem imagem (opcional).")

    if "[LINK" in config["link_pagamento"]:
        logger.error("🚨 [CONFIG] LINK DE PAGAMENTO NÃO ENCONTRADO NO .ENV!")
    if not (config.get("link_prova_social") or "").strip():
        logger.warning(
            "⚠️ [CONFIG] LINK_INSTAGRAM / CLIENTE_LINK_PROVA_SOCIAL vazio — Node 4 não enviará URL até configurar no .env."
        )
    elif not (config.get("imagem_perfil_instagram") or "").strip():
        if os.path.isfile(os.path.join(_ROOT, "assets", "instagram", "perfil_meumisterio.png")):
            logger.warning(
                "⚠️ [CONFIG] Há assets/instagram/perfil_meumisterio.png mas imagem_perfil_instagram vazio — "
                "defina PUBLIC_URL com o teu domínio/https público (ex.: túnel ngrok) para o WhatsApp poder buscar a imagem, "
                "ou defina CLIENTE_IMAGEM_PERFIL_INSTAGRAM com URL completa."
            )
        else:
            logger.warning(
                "⚠️ [CONFIG] Instagram com link ok, mas IMAGEM_PERFIL_INSTAGRAM* vazio — Node 4 envia só texto + link, "
                "sem foto do perfil antes (defina CLIENTE_IMAGEM_PERFIL_INSTAGRAM ou IMAGEM_PERFIL_INSTAGRAM_URL: URL https pública acessível pela API do WhatsApp)."
            )

    return config


def cakto_webhook_deve_iniciar_pos_venda(node_atual, cakto_cfg=None):
    """
    Se o lead está no funil estático (`static_meumisterio_*`), respeita
    `webhook_dispara_pos_venda_funil_estatico`. Caso contrário (funil IA), respeita
    `webhook_dispara_pos_venda_ia`. Evita que o motor dispare `14_confirmacao_entrega`
    quando só se quer entrega automática para compradores do fluxo estático.
    """
    cfg = cakto_cfg if cakto_cfg is not None else {}
    na = str(node_atual or "").strip()
    if na.startswith("static_meumisterio_"):
        return bool(cfg.get("webhook_dispara_pos_venda_funil_estatico", True))
    return bool(cfg.get("webhook_dispara_pos_venda_ia", False))


# Inicialização Única (Singleton)
CONFIG_CLIENTE: dict = carregar()
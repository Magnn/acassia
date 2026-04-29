"""
Roteiro único do funil estático Meu Mistério — textos, delays, paths de assets e helpers.

Os nós `node_static_meumisterio_b*.py` só orquestram estado; copy e tempos vivem aqui.

Copy colada aqui (emojis, espaços duplos, quebras de linha) deve ir em constantes multilinha e ser
enviada via `acao_texto_copy_exata(...)` — o motor não fatia nem passa por sanitização que altera
espaços (ver `engine_copy_estatica` + `engine_texto_unico`).
"""

from __future__ import annotations

import os
import re
from typing import Any, List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio.static_funnel_state import dispatch_em_andamento_recente


def acao_texto_copy_exata(conteudo: str, **metadata: Any) -> Acao:
    """
    Texto do funil estático: enviado no WhatsApp igual ao que está em `conteudo`
    (emojis, espaços, quebras de linha), sem fatiar nem colapsar espaços.
    """
    meta: dict[str, Any] = {
        "engine_texto_unico": True,
        "engine_copy_estatica": True,
        "skip_gancho_final": True,
        **metadata,
    }
    return Acao(tipo="text", conteudo=conteudo, metadata=meta)

# Raiz do repositório (flows/funil_estatico_meu_misterio/roteiro.py → 2 níveis acima)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Assets (servidos em {PUBLIC_URL}/...) ─────────────────────────────────────
DIR_AUDIO = os.path.join(_PROJECT_ROOT, "assets", "funil_estatico_meu_misterio", "audio")
AUDIO_B2_PRIORIDADE: Tuple[str, ...] = (
    "bloco2_interpretacao_ptt.ogg",
    "bloco2_ptt.ogg",
)
URL_REL_PERFIL_IG_FALLBACK = "assets/instagram/perfil_meumisterio.png"

# ── Bloco 1 ───────────────────────────────────────────────────────────────────
B1_DELAY_APOS_GATILHO_S = 8
B1_DELAY_APOS_LINK_S = 12
B1_DELAY_APOS_TEXTO_LINK_S = 8
B1_DELAY_ANTES_PERGUNTA_S = 28
# Após o lead responder ao último balão do B1, espera antes de iniciar o B2 (fila do próximo nó).
B1_DELAY_ANTES_B2_S = 15

# Copy exata do roteiro (um único balão; engine não aplica fatiamento nem sanitização agressiva).
B1_TEXTO_INTRO = """Olá, tudo bem! 😄

Eu sou Esmeralda e sou especialista em casos amorosos do Centro Meu Mistério, que é um Centro de Espiritualidade, Harmonia e Paz. ✨💙

Já vou te explicar tudo direitinho, mas antes, quero te pedir para seguir nosso Centro no Instagram. 🙏😍

Posto vários depoimentos e mostro como é nossa rotina aqui no nosso Centro 🥳

👇😍 Segue o link do meu Instagram 😍👇"""

B1_TEXTO_PERGUNTA = """💢Agora que já nos conhecemos vamos iniciar seu atendimento, ok! 😍🙏

💫Por favor me envie uma foto da sua mão direita 🖐️,

💔 Me faça uma pergunta sobre a área amorosa

Estou no seu aguardo, ok 😇"""

B1_LINK_IG_DEFAULT = "https://www.instagram.com/meumisterio_oficial"

RE_GATILHO_B1 = re.compile(
    r"(?is)\b("
    r"quero\s+minha\s+consulta|quero\s+consulta|minha\s+consulta|"
    r"consulta\s+inicial|quero\s+fazer\s+consulta"
    r")\b"
)

# ── Bloco 2 ───────────────────────────────────────────────────────────────────
# O tempo de espera pós-resposta do B1 está em `B1_DELAY_ANTES_B2_S` (transição no node b1).
B2_DELAY_APOS_RESPOSTA_B1_S = 0
B2_DELAY_PRE_AUDIO_S = 90
B2_DELAY_POS_AUDIO_S = 26

B2_TEXTO_INTERPRETACAO = (
    "Meu anjo, comecei a interpretar suas energias agora e, em breve, vou te revelar o que está "
    "acontecendo no seu campo amoroso, tudo bem?"
)

B2_TEXTO_PERGUNTA_NOME = (
    "Vamos abrir o campo do seu 💔 amor agora, me fala o nome da pessoa amada pra eu iniciar? 🤩🙏"
)

# ── Metadata keys (persistidas no lead) ───────────────────────────────────────
META_B1_PHASE = "static_mm_b1_phase"
META_B2_PHASE = "static_mm_b2_phase"
META_B2_SEQ = "static_mm_b2_seq_dispatched"
META_NOME_AMADO = "nome_pessoa_amada_b2"
META_B3_PHASE = "static_mm_b3_phase"
META_B3_SEQ = "static_mm_b3_seq_dispatched"

# ── Bloco 3 ─────────────────────────────────────────────────────────────────
B3_DELAY_PRE_AUDIO_S = 65
B3_DELAY_POS_AUDIO_ANTES_PERGUNTA_S = 12
# Transição B3→B4: sem delay extra na fila — o `LeadInboxManager` já só dispara o batch após
# `INBOX_SILENCE_SECONDS` sem nova mensagem (fila após a última mensagem do lead).
B3_DELAY_ANTES_B4_S = 0

B3_TEXTO_PERGUNTA = "Posso continuar Falando Sobre a Hipnose Astral 🎆😇?"

# Áudio público (produção); com PUBLIC_URL local usa o mesmo path em /assets/...
B3_AUDIO_FILENAME = "bloco3_ptt.ogg"
B3_AUDIO_URL_FALLBACK = (
    "https://meumisterio.com/assets/funil_estatico_meu_misterio/audio/bloco3_ptt.ogg"
)

# ── Bloco 4 ─────────────────────────────────────────────────────────────────
B4_DELAY_PRE_PRIMEIRO_AUDIO_S = 45
B4_DELAY_APOS_AUDIO_PRINCIPAL_S = 22
B4_DELAY_APOS_AUDIO_D1_S = 18
B4_DELAY_APOS_AUDIO_D2_S = 14
B4_DELAY_APOS_AUDIO_D3_S = 16
# Após resposta à pergunta final + fila do inbox; delay extra antes do B5.
B4_DELAY_ANTES_B5_S = 15

_B4_BASE = "https://meumisterio.com/assets/funil_estatico_meu_misterio/audio"
B4_AUDIO_PRINCIPAL_DEFAULT = f"{_B4_BASE}/bloco4.ogg"
B4_AUDIO_D1_DEFAULT = f"{_B4_BASE}/bloco4_d1.ogg"
B4_AUDIO_D2_DEFAULT = f"{_B4_BASE}/bloco4_d2.ogg"
B4_AUDIO_D3_DEFAULT = f"{_B4_BASE}/bloco4_d3.ogg"

B4_TEXTO_PERGUNTA_FINAL = (
    "🎯 Depois de ouvir esses relatos, tenho certeza de que vai gostar do que vem a seguir.✨ "
    "Então, posso dar continuidade à sua leitura?🔮"
)

META_B4_PHASE = "static_mm_b4_phase"
META_B4_SEQ = "static_mm_b4_seq_dispatched"

# ── Bloco 5 ─────────────────────────────────────────────────────────────────
B5_DELAY_PRE_AUDIO_S = 45
B5_DELAY_APOS_AUDIO_S = 14
B5_DELAY_APOS_TEXTO_INTRO_S = 12
B5_DELAY_APOS_LINK_S = 26
B5_DELAY_APOS_TEXTO_DETALHE_S = 16
B5_DELAY_ANTES_B6_S = 15

B5_AUDIO_DEFAULT = "https://meumisterio.com/assets/funil_estatico_meu_misterio/audio/bloco5.ogg"
B5_LINK_PAGAMENTO_DEFAULT = "https://pay.cakto.com.br/37fuusy"

B5_TEXTO_INTRO_PAGAMENTO = """Irei te enviar o link de pagamento do nosso parceiro, ok
aperta no link e escolhe opção de pix ou cartão👇👇👇"""

B5_TEXTO_PERGUNTA_GARANTIA = "Quer saber qual será a Garantia que você irá ter?"

META_B5_PHASE = "static_mm_b5_phase"
META_B5_SEQ = "static_mm_b5_seq_dispatched"

# ── Bloco 6 (FIM do funil estático) ───────────────────────────────────────────
B6_DELAY_PRE_TEXTO_S = 36
B6_DELAY_APOS_TEXTO_GARANTIA_S = 26
B6_DELAY_APOS_AUDIO_A_S = 22
B6_DELAY_APOS_AUDIO_B_S = 26
B6_DELAY_APOS_AUDIO_C_S = 24
B6_DELAY_APOS_AUDIO_D_S = 22

_B6_BASE = "https://meumisterio.com/assets/funil_estatico_meu_misterio/audio"
B6_AUDIO_A_DEFAULT = f"{_B6_BASE}/bloco6_a.ogg"
B6_AUDIO_B_DEFAULT = f"{_B6_BASE}/bloco6_b.ogg"
B6_AUDIO_C_DEFAULT = f"{_B6_BASE}/bloco6_c.ogg"
B6_AUDIO_D_DEFAULT = f"{_B6_BASE}/bloco6_d.ogg"

B6_TEXTO_GARANTIA = (
    "💬Minha garantia é que eu vou te 👀acompanhar durante todo processo do trabalho, meu anjo😉, "
    "sei que está sendo difícil pra você confiar em trabalhos espirituais hoje em dia devido ao "
    "aumento de golpes na internet, por esse motivo eu deixei o valor bem abaixo do valor normal, "
    "tenho certeza que você vai ✨😊amar o trabalho que vamos fazer por você.💖"
)

B6_TEXTO_FIM = "🔥 Posso segurar sua vaga? SIM ou NÃO, por favor! ⏳✨"

META_B6_SEQ = "static_mm_b6_seq_dispatched"

# ── Bloco 7 — pós-pagamento aprovado (webhook Cakto → `static_meumisterio_b7`) ───
B7_DELAY_PRE_TEXTO_NOMES_S = 50
B7_DELAY_APOS_TEXTO_NOMES_S = 35
B7_DELAY_APOS_AUDIO_01_S = 20 * 60  # 20 min
B7_DELAY_APOS_TEXTO_MATERIAL_S = 15 * 60  # 15 min
B7_DELAY_APOS_AUDIO_02_S = 16
B7_DELAY_APOS_AUDIO_03_S = 35
B7_DELAY_APOS_AUDIO_04_S = 50
B7_DELAY_APOS_AUDIO_05_S = 2 * 60 * 60  # 2 h
B7_DELAY_APOS_TEXTO_TRABALHO_S = 60  # 1 min
B7_DELAY_APOS_AUDIO_06_S = 36
B7_DELAY_APOS_AUDIO_07_S = 2 * 60  # 2 min
B7_DELAY_APOS_TEXTO_ORIENTACOES_S = 5 * 60  # 5 min
B7_DELAY_APOS_AUDIO_08_S = 26
B7_DELAY_APOS_AUDIO_09_S = 15

_B7_BASE = "https://meumisterio.com/assets/funil_estatico_meu_misterio/audio"
B7_AUDIO_01_DEFAULT = f"{_B7_BASE}/01%20do%20Entreg%C3%A1vel.ogg"
B7_AUDIO_02_DEFAULT = f"{_B7_BASE}/02%20%20-%20Entrega.ogg"
B7_AUDIO_03_DEFAULT = f"{_B7_BASE}/03%20-%20entregavel.ogg"
B7_AUDIO_04_DEFAULT = f"{_B7_BASE}/04%20-%20Entreg%C3%A1vel.mp3"
B7_AUDIO_05_DEFAULT = f"{_B7_BASE}/05%20-Entreg%C3%A1vel.mp3"
B7_AUDIO_06_DEFAULT = f"{_B7_BASE}/06%20-%20Entregav%C3%A9l.ogg"
B7_AUDIO_07_DEFAULT = f"{_B7_BASE}/07%20Entregav%C3%A9l.ogg"
B7_AUDIO_08_DEFAULT = f"{_B7_BASE}/08%20-%20Entregav%C3%A9l.ogg"
B7_AUDIO_09_DEFAULT = f"{_B7_BASE}/09%20-%20Entregav%C3%A9l.ogg"
B7_AUDIO_10_DEFAULT = f"{_B7_BASE}/10%20-%20Entregav%C3%A9l.ogg"

B7_TEXTO_NOMES_FOTOS = (
    "Vou precisar dos nomes de vocês e se tiver fotos pode enviar também.."
)
B7_TEXTO_MATERIAL = "Acabamos de identificar seus materiais e já vamos dar início, tá bom?"
B7_TEXTO_TRABALHO = (
    "Acabei de iniciar seu trabalho, meu amor ❤️✨ e vou te passar suas orientações agora 📜🙏."
)
B7_TEXTO_ORIENTACOES_BANHO = """💢Preparação do ambiente: Escolha um local tranquilo onde você possa realizar o banho sem interrupções. Acenda velas e incensos, se desejar, para criar uma atmosfera relaxante e propícia pra limpeza espiritual.
💢Preparação do banho: Ferva cerca de 2 litros de água e adicione erva, umas 10 gramas de alecrim, arruda, sal grosso. Deixe as ervas em infusão na água quente por alguns minutos.
Coar e resfriar: Após a infusão, coe o líquido para remover as ervas ou cristais e deixe a água esfriar até uma temperatura agradável para o banho.
Preparação pessoal: Tome um banho de chuveiro normal antes de começar o banho de limpeza espiritual. Isso ajuda a limpar o corpo físico e preparar você para a limpeza espiritual.
Realização do banho: Despeje a água preparada sobre o corpo, começando pela cabeça e descendo até os pés. Concentre-se em visualizar a água removendo qualquer energia negativa ou impureza espiritual do seu corpo e aura.
💢Intenção: Enquanto realiza o banho, concentre-se em suas intenções de limpeza espiritual. Pode ser útil recitar uma oração ou mantra que ressoe com você.
💢Finalização: Após o banho, deixe o corpo secar naturalmente, se possível, para permitir que as energias negativas sejam removidas completamente. Você pode vestir roupas limpas e leves após o banho."""

META_B7_SEQ = "static_mm_b7_seq_dispatched"


def cfg(ctx) -> dict:
    return (getattr(ctx, "metadata", None) or {}).get("__config__") or {}


def texto_sistema_ignorar(txt: str) -> bool:
    t = (txt or "").strip()
    return bool(t.startswith("[") and t.endswith("]"))


def lead_respondeu_texto_ou_midia(ctx) -> bool:
    if texto_sistema_ignorar(ctx.texto_recebido or ""):
        return False
    if (ctx.texto_recebido or "").strip():
        return True
    tp = (getattr(ctx, "tipo_mensagem", None) or "").lower()
    return tp in ("image", "video", "audio", "document")


def url_imagem_perfil_instagram(cfg: dict) -> str:
    u = (cfg.get("imagem_perfil_instagram") or "").strip()
    if u:
        return u
    base = (cfg.get("public_url") or "").strip().rstrip("/")
    if base.startswith("http"):
        return f"{base}/{URL_REL_PERFIL_IG_FALLBACK}"
    return ""


def arquivo_audio_b2_resolvido() -> tuple[str, str]:
    """(path_absoluto_ou_vazio, rel_url_para_public)."""
    for name in AUDIO_B2_PRIORIDADE:
        p = os.path.join(DIR_AUDIO, name)
        if os.path.isfile(p):
            return p, f"assets/funil_estatico_meu_misterio/audio/{name}"
    return "", ""


def url_audio_b2_publica(cfg: dict) -> str:
    base = (cfg.get("public_url") or "").strip().rstrip("/")
    _, rel = arquivo_audio_b2_resolvido()
    if base.startswith("http") and rel:
        return f"{base}/{rel}"
    return ""


def url_audio_b3_publica(cfg: dict) -> str:
    expl = (cfg.get("audio_bloco3_url") or "").strip()
    if expl.startswith("http"):
        return expl
    base = (cfg.get("public_url") or "").strip().rstrip("/")
    rel = f"assets/funil_estatico_meu_misterio/audio/{B3_AUDIO_FILENAME}"
    if base.startswith("http"):
        return f"{base}/{rel}"
    return B3_AUDIO_URL_FALLBACK


def acao_typing_whatsapp(whatsapp_kind: str, **metadata: Any) -> Acao:
    """whatsapp_kind: 'text' | 'audio' (Cloud API typing indicator)."""
    k = (whatsapp_kind or "text").strip().lower()
    if k not in ("text", "audio"):
        k = "text"
    meta = {"whatsapp_typing": k, **metadata}
    return Acao(tipo="typing", conteudo="", metadata=meta)


def montar_acoes_bloco3(cfg: dict) -> List[Acao]:
    """
    Nota: indicadores "digitando/gravando" via `typing` não são aceites no endpoint
    `POST .../messages` desta conta (erro #100). Reativar só quando a Meta expuser
    suporte compatível; use `cfg['whatsapp_typing_enabled']` + `acao_typing_whatsapp`.
    """
    au = url_audio_b3_publica(cfg)
    typing_on = bool(cfg.get("whatsapp_typing_enabled"))
    acoes: List[Acao] = [Acao(tipo="delay", segundos=B3_DELAY_PRE_AUDIO_S)]
    if typing_on:
        acoes.append(acao_typing_whatsapp("audio", source="static_meumisterio_b3", kind="typing_pre_audio"))
    if au:
        acoes.append(
            Acao(
                tipo="audio",
                url=au,
                conteudo=au,
                metadata={
                    "source": "static_meumisterio_b3",
                    "kind": "ptt_bloco3",
                    "whatsapp_voice": True,
                },
            )
        )
    acoes.append(Acao(tipo="delay", segundos=B3_DELAY_POS_AUDIO_ANTES_PERGUNTA_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b3", kind="typing_pre_pergunta"))
    acoes.append(
        acao_texto_copy_exata(
            B3_TEXTO_PERGUNTA,
            source="static_meumisterio_b3",
            kind="pergunta_hipnose_astral",
        )
    )
    return acoes


def _url_audio_b4(cfg: dict, chave_cfg: str, fallback: str) -> str:
    u = (cfg.get(chave_cfg) or "").strip()
    if u.startswith("http"):
        return u
    return fallback


def montar_acoes_bloco4(cfg: dict) -> List[Acao]:
    """
    Áudios 2–4: sem `voice` (ficheiro), mais próximo de “encaminhado” que nota de voz.
    A Cloud API não expõe rótulo Encaminhado para links arbitrários.
    """
    typing_on = bool(cfg.get("whatsapp_typing_enabled"))
    a0 = _url_audio_b4(cfg, "audio_bloco4_principal", B4_AUDIO_PRINCIPAL_DEFAULT)
    a1 = _url_audio_b4(cfg, "audio_bloco4_d1", B4_AUDIO_D1_DEFAULT)
    a2 = _url_audio_b4(cfg, "audio_bloco4_d2", B4_AUDIO_D2_DEFAULT)
    a3 = _url_audio_b4(cfg, "audio_bloco4_d3", B4_AUDIO_D3_DEFAULT)

    acoes: List[Acao] = [Acao(tipo="delay", segundos=B4_DELAY_PRE_PRIMEIRO_AUDIO_S)]
    if typing_on:
        acoes.append(acao_typing_whatsapp("audio", source="static_meumisterio_b4", kind="typing_pre_bloco4"))

    def _aud(url: str, kind: str, *, voice: bool) -> Acao:
        meta: dict[str, Any] = {"source": "static_meumisterio_b4", "kind": kind}
        meta["whatsapp_voice"] = bool(voice)
        return Acao(tipo="audio", url=url, conteudo=url, metadata=meta)

    if a0:
        acoes.append(_aud(a0, "audio_bloco4_principal", voice=True))
    acoes.append(Acao(tipo="delay", segundos=B4_DELAY_APOS_AUDIO_PRINCIPAL_S))
    if a1:
        acoes.append(_aud(a1, "audio_bloco4_d1", voice=False))
    acoes.append(Acao(tipo="delay", segundos=B4_DELAY_APOS_AUDIO_D1_S))
    if a2:
        acoes.append(_aud(a2, "audio_bloco4_d2", voice=False))
    acoes.append(Acao(tipo="delay", segundos=B4_DELAY_APOS_AUDIO_D2_S))
    if a3:
        acoes.append(_aud(a3, "audio_bloco4_d3", voice=False))
    acoes.append(Acao(tipo="delay", segundos=B4_DELAY_APOS_AUDIO_D3_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b4", kind="typing_pre_pergunta_final"))
    acoes.append(
        acao_texto_copy_exata(
            B4_TEXTO_PERGUNTA_FINAL,
            source="static_meumisterio_b4",
            kind="pergunta_continuidade_leitura",
        )
    )
    return acoes


def url_audio_b5(cfg: dict) -> str:
    u = (cfg.get("audio_bloco5_url") or "").strip()
    if u.startswith("http"):
        return u
    base = (cfg.get("public_url") or "").strip().rstrip("/")
    rel = "assets/funil_estatico_meu_misterio/audio/bloco5.ogg"
    if base.startswith("http"):
        return f"{base}/{rel}"
    return B5_AUDIO_DEFAULT


def url_link_pagamento_b5(cfg: dict) -> str:
    u = (cfg.get("link_pagamento_b5") or "").strip()
    if u.startswith("http"):
        return u.rstrip("/")
    return B5_LINK_PAGAMENTO_DEFAULT


def texto_detalhe_pagamento_b5(cfg: dict) -> str:
    lk = url_link_pagamento_b5(cfg)
    return (
        "Aqui está o link de pagamento com seu desconto exclusivo de hoje:\n"
        "Está em nome Cakto Pay LTD no valor de 100 reais\n\n"
        "⚠️ Ele é válido apenas HOJE, pois as vagas com esse valor são limitadas:\n\n"
        f"👉 {lk}\n"
        "✅ Clica no link e gera seu pix ou cartão.\n"
        "➖➖➖➖➖➖➖➖\n"
        "✅ Plataforma de pagamento segura e confiável\n"
        "✅ Pode ser pix ou cartão\n"
        "✅ Acesso imediato após a compra\n"
        "➖➖➖➖➖➖➖➖"
    )


def montar_acoes_bloco5(cfg: dict) -> List[Acao]:
    typing_on = bool(cfg.get("whatsapp_typing_enabled"))
    au = url_audio_b5(cfg)
    acoes: List[Acao] = [Acao(tipo="delay", segundos=B5_DELAY_PRE_AUDIO_S)]
    if typing_on:
        acoes.append(acao_typing_whatsapp("audio", source="static_meumisterio_b5", kind="typing_pre_audio"))
    if au:
        acoes.append(
            Acao(
                tipo="audio",
                url=au,
                conteudo=au,
                metadata={
                    "source": "static_meumisterio_b5",
                    "kind": "ptt_bloco5",
                    "whatsapp_voice": True,
                },
            )
        )
    acoes.append(Acao(tipo="delay", segundos=B5_DELAY_APOS_AUDIO_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b5", kind="typing_pos_audio"))
    acoes.append(
        acao_texto_copy_exata(
            B5_TEXTO_INTRO_PAGAMENTO,
            source="static_meumisterio_b5",
            kind="intro_link_fornecedor",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B5_DELAY_APOS_TEXTO_INTRO_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b5", kind="typing_pre_link"))
    acoes.append(
        acao_texto_copy_exata(
            url_link_pagamento_b5(cfg),
            source="static_meumisterio_b5",
            kind="link_pagamento_cakto",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B5_DELAY_APOS_LINK_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b5", kind="typing_pre_detalhe"))
    acoes.append(
        acao_texto_copy_exata(
            texto_detalhe_pagamento_b5(cfg),
            source="static_meumisterio_b5",
            kind="detalhe_pagamento_desconto",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B5_DELAY_APOS_TEXTO_DETALHE_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b5", kind="typing_pre_garantia"))
    acoes.append(
        acao_texto_copy_exata(
            B5_TEXTO_PERGUNTA_GARANTIA,
            source="static_meumisterio_b5",
            kind="pergunta_garantia",
        )
    )
    return acoes


def _url_audio_b6(cfg: dict, chave_cfg: str, fallback: str) -> str:
    u = (cfg.get(chave_cfg) or "").strip()
    if u.startswith("http"):
        return u
    base = (cfg.get("public_url") or "").strip().rstrip("/")
    name = fallback.rsplit("/", 1)[-1]
    rel = f"assets/funil_estatico_meu_misterio/audio/{name}"
    if base.startswith("http"):
        return f"{base}/{rel}"
    return fallback


def montar_acoes_bloco6(cfg: dict) -> List[Acao]:
    """Último bloco do funil estático — após enviar, o nó fica em espera (FIM)."""
    typing_on = bool(cfg.get("whatsapp_typing_enabled"))
    ua = _url_audio_b6(cfg, "audio_bloco6_a", B6_AUDIO_A_DEFAULT)
    ub = _url_audio_b6(cfg, "audio_bloco6_b", B6_AUDIO_B_DEFAULT)
    uc = _url_audio_b6(cfg, "audio_bloco6_c", B6_AUDIO_C_DEFAULT)
    ud = _url_audio_b6(cfg, "audio_bloco6_d", B6_AUDIO_D_DEFAULT)

    def _aud(url: str, kind: str) -> Acao:
        return Acao(
            tipo="audio",
            url=url,
            conteudo=url,
            metadata={
                "source": "static_meumisterio_b6",
                "kind": kind,
                "whatsapp_voice": True,
            },
        )

    acoes: List[Acao] = [Acao(tipo="delay", segundos=B6_DELAY_PRE_TEXTO_S)]
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b6", kind="typing_pre_garantia"))
    acoes.append(
        acao_texto_copy_exata(
            B6_TEXTO_GARANTIA,
            source="static_meumisterio_b6",
            kind="texto_garantia",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B6_DELAY_APOS_TEXTO_GARANTIA_S))
    if ua:
        acoes.append(_aud(ua, "audio_bloco6_a"))
    acoes.append(Acao(tipo="delay", segundos=B6_DELAY_APOS_AUDIO_A_S))
    if ub:
        acoes.append(_aud(ub, "audio_bloco6_b"))
    acoes.append(Acao(tipo="delay", segundos=B6_DELAY_APOS_AUDIO_B_S))
    if uc:
        acoes.append(_aud(uc, "audio_bloco6_c"))
    acoes.append(Acao(tipo="delay", segundos=B6_DELAY_APOS_AUDIO_C_S))
    if ud:
        acoes.append(_aud(ud, "audio_bloco6_d"))
    acoes.append(Acao(tipo="delay", segundos=B6_DELAY_APOS_AUDIO_D_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b6", kind="typing_pre_fim"))
    acoes.append(
        acao_texto_copy_exata(
            B6_TEXTO_FIM,
            source="static_meumisterio_b6",
            kind="pergunta_segurar_vaga",
        )
    )
    return acoes


def _url_audio_b7(cfg: dict, chave_cfg: str, fallback: str) -> str:
    u = (cfg.get(chave_cfg) or "").strip()
    if u.startswith("http"):
        return u
    base = (cfg.get("public_url") or "").strip().rstrip("/")
    name = fallback.rsplit("/", 1)[-1]
    rel = f"assets/funil_estatico_meu_misterio/audio/{name}"
    if base.startswith("http"):
        return f"{base}/{rel}"
    return fallback


def montar_acoes_bloco7(cfg: dict) -> List[Acao]:
    """Entrega pós-compra (Cakto aprovado). Uma execução por lead (`META_B7_SEQ`)."""
    typing_on = bool(cfg.get("whatsapp_typing_enabled"))
    u01 = _url_audio_b7(cfg, "audio_bloco7_01", B7_AUDIO_01_DEFAULT)
    u02 = _url_audio_b7(cfg, "audio_bloco7_02", B7_AUDIO_02_DEFAULT)
    u03 = _url_audio_b7(cfg, "audio_bloco7_03", B7_AUDIO_03_DEFAULT)
    u04 = _url_audio_b7(cfg, "audio_bloco7_04", B7_AUDIO_04_DEFAULT)
    u05 = _url_audio_b7(cfg, "audio_bloco7_05", B7_AUDIO_05_DEFAULT)
    u06 = _url_audio_b7(cfg, "audio_bloco7_06", B7_AUDIO_06_DEFAULT)
    u07 = _url_audio_b7(cfg, "audio_bloco7_07", B7_AUDIO_07_DEFAULT)
    u08 = _url_audio_b7(cfg, "audio_bloco7_08", B7_AUDIO_08_DEFAULT)
    u09 = _url_audio_b7(cfg, "audio_bloco7_09", B7_AUDIO_09_DEFAULT)
    u10 = _url_audio_b7(cfg, "audio_bloco7_10", B7_AUDIO_10_DEFAULT)

    def _aud(url: str, kind: str) -> Acao:
        return Acao(
            tipo="audio",
            url=url,
            conteudo=url,
            metadata={
                "source": "static_meumisterio_b7",
                "kind": kind,
                "whatsapp_voice": True,
            },
        )

    acoes: List[Acao] = [Acao(tipo="delay", segundos=B7_DELAY_PRE_TEXTO_NOMES_S)]
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b7", kind="typing_pre_nomes"))
    acoes.append(
        acao_texto_copy_exata(
            B7_TEXTO_NOMES_FOTOS,
            source="static_meumisterio_b7",
            kind="texto_nomes_fotos",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_TEXTO_NOMES_S))
    if u01:
        acoes.append(_aud(u01, "audio_bloco7_01"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_01_S))
    if typing_on:
        acoes.append(acao_typing_whatsapp("text", source="static_meumisterio_b7", kind="typing_pre_material"))
    acoes.append(
        acao_texto_copy_exata(
            B7_TEXTO_MATERIAL,
            source="static_meumisterio_b7",
            kind="texto_materiais",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_TEXTO_MATERIAL_S))
    if u02:
        acoes.append(_aud(u02, "audio_bloco7_02"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_02_S))
    if u03:
        acoes.append(_aud(u03, "audio_bloco7_03"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_03_S))
    if u04:
        acoes.append(_aud(u04, "audio_bloco7_04"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_04_S))
    if u05:
        acoes.append(_aud(u05, "audio_bloco7_05"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_05_S))
    acoes.append(
        acao_texto_copy_exata(
            B7_TEXTO_TRABALHO,
            source="static_meumisterio_b7",
            kind="texto_trabalho_iniciado",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_TEXTO_TRABALHO_S))
    if u06:
        acoes.append(_aud(u06, "audio_bloco7_06"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_06_S))
    if u07:
        acoes.append(_aud(u07, "audio_bloco7_07"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_07_S))
    acoes.append(
        acao_texto_copy_exata(
            B7_TEXTO_ORIENTACOES_BANHO,
            source="static_meumisterio_b7",
            kind="texto_orientacoes_banho",
        )
    )
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_TEXTO_ORIENTACOES_S))
    if u08:
        acoes.append(_aud(u08, "audio_bloco7_08"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_08_S))
    if u09:
        acoes.append(_aud(u09, "audio_bloco7_09"))
    acoes.append(Acao(tipo="delay", segundos=B7_DELAY_APOS_AUDIO_09_S))
    if u10:
        acoes.append(_aud(u10, "audio_bloco7_10"))
    return acoes


def montar_acoes_bloco1(cfg: dict) -> List[Acao]:
    ig = (cfg.get("link_prova_social") or B1_LINK_IG_DEFAULT).strip()
    if not ig.startswith("http"):
        ig = B1_LINK_IG_DEFAULT
    img_url = url_imagem_perfil_instagram(cfg)

    acoes: List[Acao] = [
        Acao(tipo="delay", segundos=B1_DELAY_APOS_GATILHO_S),
        acao_texto_copy_exata(
            B1_TEXTO_INTRO,
            source="static_meumisterio_b1",
            kind="intro",
        ),
        Acao(tipo="delay", segundos=B1_DELAY_APOS_LINK_S),
        acao_texto_copy_exata(
            ig,
            source="static_meumisterio_b1",
            kind="link_instagram",
        ),
        Acao(tipo="delay", segundos=B1_DELAY_APOS_TEXTO_LINK_S),
    ]
    if img_url:
        acoes.append(
            Acao(
                tipo="image",
                url=img_url,
                conteudo=img_url,
                metadata={"source": "static_meumisterio_b1", "kind": "print_instagram"},
            )
        )
    acoes.append(Acao(tipo="delay", segundos=B1_DELAY_ANTES_PERGUNTA_S))
    acoes.append(
        acao_texto_copy_exata(
            B1_TEXTO_PERGUNTA,
            source="static_meumisterio_b1",
            kind="pedido_foto_pergunta",
        )
    )
    return acoes


def montar_acoes_bloco2(cfg: dict) -> List[Acao]:
    au = url_audio_b2_publica(cfg)
    acoes: List[Acao] = [
        Acao(tipo="delay", segundos=B2_DELAY_APOS_RESPOSTA_B1_S),
        acao_texto_copy_exata(
            B2_TEXTO_INTERPRETACAO,
            source="static_meumisterio_b2",
            kind="interpretacao",
        ),
        Acao(tipo="delay", segundos=B2_DELAY_PRE_AUDIO_S),
    ]
    if au:
        acoes.append(
            Acao(
                tipo="audio",
                url=au,
                conteudo=au,
                metadata={
                    "source": "static_meumisterio_b2",
                    "kind": "ptt_interpretacao",
                    "whatsapp_voice": True,
                },
            )
        )
    acoes.append(Acao(tipo="delay", segundos=B2_DELAY_POS_AUDIO_S))
    acoes.append(
        acao_texto_copy_exata(
            B2_TEXTO_PERGUNTA_NOME,
            source="static_meumisterio_b2",
            kind="pergunta_nome_amado",
        )
    )
    return acoes

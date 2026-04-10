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
B1_DELAY_APOS_GATILHO_S = 35
B1_DELAY_APOS_LINK_S = 12
B1_DELAY_APOS_TEXTO_LINK_S = 8
B1_DELAY_ANTES_PERGUNTA_S = 28
# Após o lead responder ao último balão do B1, espera antes de iniciar o B2 (fila do próximo nó).
B1_DELAY_ANTES_B2_S = 15

# Copy exata do roteiro (um único balão; engine não aplica fatiamento nem sanitização agressiva).
B1_TEXTO_INTRO = """Olá, tudo bem! 😄

Eu sou  Esmeralda  e sou Especialista em casos amorosos Centro Meu Mistério, que e um  Centro de Espiritualidade e Harmonia e Paz. 🏥💙

Já vou te explicar tudo certinho , mas antes, Quero te pedir para Seguir nosso Centro no Instagram. 🙏😍

Posto Vários Depoimentos E Mostro Como e Nossa Rotina Aqui em Nosso Centro 🥳

👇😍Segue O Link Do Meu Instagram 😍👇"""

B1_TEXTO_PERGUNTA = """💢Agora que já nos conhecemos vamos iniciar seu atendimento, ok!😍🙏

💫Por Favor me envie uma foto da sua mão Direita 🖐️ , 

💔 Me faça uma Pergunta sobre sobre a área Amorosa

Estou no seu Aguardo, ok 😇"""

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
B2_DELAY_PRE_AUDIO_S = 180
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

B5_TEXTO_INTRO_PAGAMENTO = """Irei te enviar o link de pagamento do Nosso Fornecedor, ok
aperta no link e escolhe opção de pix ou cartão👇👇👇"""

B5_TEXTO_PERGUNTA_GARANTIA = "Quer saber qual será a Garantia que você irá ter?"

META_B5_PHASE = "static_mm_b5_phase"
META_B5_SEQ = "static_mm_b5_seq_dispatched"


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
    u = (cfg.get("link_pagamento_b5") or cfg.get("link_pagamento") or "").strip()
    if u.startswith("http"):
        return u.rstrip("/")
    return B5_LINK_PAGAMENTO_DEFAULT


def texto_detalhe_pagamento_b5(cfg: dict) -> str:
    lk = url_link_pagamento_b5(cfg)
    return (
        "Aqui está o link de pagamento com seu desconto exclusivo de hoje:\n"
        "Está em nome Cackto Pay LTD no valor de 100 reais\n\n"
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

"""
Suporte curto quando o lead está em estados silenciosos de pagamento mas escreve sobre
link, PIX, checkout ou erro — evita só o ack genérico sem ação (gargalo de conversão).
"""

from __future__ import annotations

import logging
import random
import re
from typing import List

from schema import Acao
from copy_sanitizer import normalizar_link_para_envio, preparar_texto_envio
from flows.funnel_gates import VOCATIVO_SEM_NOME

logger = logging.getLogger(__name__)

_RE_AJUDA_CHECKOUT = re.compile(
    r"(?i)\b("
    r"link|pix|pagamento|checkout|cakto|comprovante|pagar|"
    r"n[aã]o\s+abre|n[aã]o\s+funciona|n[aã]o\s+esta|não\s+está|"
    r"errad|quebrad|expirad|cart[aã]o|boleto|"
    r"valor|reais|r\$|preco|pre[cç]o|\.env"
    r")\b"
)

_NODES_CHECKOUT = frozenset(
    {
        "aguardando_pagamento",
        "aguardando_pagamento_servico",
        "aguardando_pagamento_downsell",
    }
)


def texto_pedido_ajuda_checkout(texto: str) -> bool:
    t = (texto or "").strip()
    if len(t) < 2:
        return False
    return bool(_RE_AJUDA_CHECKOUT.search(t))


def node_e_checkout_silencioso(node: str) -> bool:
    return (node or "").strip().lower() in _NODES_CHECKOUT


def link_efetivo_para_node(node_atual: str, config: dict) -> str:
    cfg = config if isinstance(config, dict) else {}
    n = (node_atual or "").lower()
    if "downsell" in n:
        raw = (cfg.get("link_downsell") or cfg.get("link_pagamento") or "").strip()
    else:
        raw = (cfg.get("link_pagamento") or "").strip()
    raw = normalizar_link_para_envio(raw, instagram_mode=False) or raw
    return preparar_texto_envio(raw, "suporte_checkout_link").strip()


def _link_eh_configurado(link: str) -> bool:
    s = (link or "").strip()
    if not s or s.startswith("["):
        return False
    return s.lower().startswith("http://") or s.lower().startswith("https://")


def montar_acoes_suporte_checkout(
    *,
    nome_vocativo: str,
    link: str,
    node_atual: str,
) -> List[Acao]:
    nome = (nome_vocativo or "").strip() or VOCATIVO_SEM_NOME
    tem_link = _link_eh_configurado(link)
    acoes: List[Acao] = []

    acoes.append(Acao(tipo="delay", segundos=random.randint(4, 8)))
    acoes.append(
        Acao(
            tipo="text",
            conteudo=(
                f"Recebi, {nome}. Quando o link trava ou dá erro, muitas vezes é rede, "
                "app do banco ou o navegador bloqueando o checkout — não é você que fez errado."
            ),
            metadata={"skip_gancho_final": True},
        )
    )

    if tem_link:
        acoes.append(Acao(tipo="delay", segundos=random.randint(5, 9)))
        acoes.append(
            Acao(
                tipo="text",
                conteudo="Abre de novo por aqui. Se não tocar, segura o dedo no link pra copiar e colar no navegador:",
                metadata={"skip_gancho_final": True},
            )
        )
        acoes.append(Acao(tipo="delay", segundos=random.randint(3, 6)))
        acoes.append(
            Acao(
                tipo="text",
                conteudo=link,
                metadata={"skip_gancho_final": True},
            )
        )
    else:
        logger.warning(
            "event=suporte_checkout_sem_link node=%s — configure LINK_CHECKOUT no .env",
            node_atual,
        )
        acoes.append(Acao(tipo="delay", segundos=random.randint(5, 9)))
        acoes.append(
            Acao(
                tipo="text",
                conteudo=(
                    "O link automático não está disponível da minha cabine agora. "
                    "Responde *link* ou *FIRMO* que eu tento reenviar o checkout na sequência, "
                    "ou me diz exatamente o que aparece na tela."
                ),
                metadata={"skip_gancho_final": True},
            )
        )

    acoes.append(Acao(tipo="delay", segundos=random.randint(6, 11)))
    acoes.append(
        Acao(
            tipo="text",
            conteudo=(
                "Se ainda falhar, manda um print ou a mensagem de erro em uma frase "
                "que eu te oriento no próximo passo. Combinado?"
            ),
        )
    )
    return acoes

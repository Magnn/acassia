"""
ai/sentiment_router.py — Roteamento de Emergência por Sentimento
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analisa o resultado do SentimentAnalyzer e decide se o lead deve
ser marcado como URGENTE no CRM. O operador humano vê esse lead
no topo absoluto da lista, com alerta visual.

Regras de urgência:
1. Sentimento "frustrado" com score < 0.3 → URGENTE
2. Sentimento "resistente" com sinais de crise emocional → URGENTE
3. Texto contém keywords de crise → URGENTE (fast-path sem IA)
4. Score de engajamento extremamente baixo (<0.15) → URGENTE

Uso no engine.py (após sentiment_analyzer.analisar):
    from ai.sentiment_router import evaluate_urgency
    urgency = evaluate_urgency(sent_result, texto_recebido)
    if urgency.is_urgent:
        lead.is_urgent = True
        lead.urgent_reason = urgency.reason
        lead.urgent_at = datetime.now(timezone.utc)
        # SSE push → CRM atualiza em tempo real
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Keywords que indicam crise emocional (fast-path, sem precisar de IA)
_CRISE_KEYWORDS = re.compile(
    r"\b("
    r"suicid[ao]|me\s*mat[ao]r|quero\s*morrer|"
    r"n[aã]o\s*aguento\s*mais|desistir\s*de\s*tudo|"
    r"vou\s*me\s*machucar|estou\s*desesper|"
    r"crise\s*(de\s*)?p[aâ]nico|ataque\s*de\s*p[aâ]nico|"
    r"urg[eê]ncia|socorro|"
    r"est[aá]\s*muito\s*mal|perdi\s*tudo|n[aã]o\s*sei\s*o\s*que\s*fazer"
    r")\b",
    re.IGNORECASE,
)

# Sinais do SentimentAnalyzer que indicam crise
_SINAIS_CRISE = {
    "desespero", "crise", "pânico", "pânico_severo",
    "suicídio", "autolesão", "dor_extrema", "abandono_total",
    "choro_intenso", "solidão_profunda", "luto_agudo",
}


@dataclass(frozen=True)
class UrgencyResult:
    is_urgent: bool
    reason: str
    severity: str  # "critical" | "high" | "medium" | "none"


def evaluate_urgency(
    sentiment_result: dict | None,
    texto_recebido: str = "",
) -> UrgencyResult:
    """
    Avalia se o lead deve ser marcado como urgente.
    
    Args:
        sentiment_result: Output do SentimentAnalyzer.analisar()
        texto_recebido: Texto da mensagem (para fast-path keywords)
    
    Returns:
        UrgencyResult com is_urgent, reason e severity
    """
    texto = (texto_recebido or "").strip().lower()
    sent = sentiment_result or {}
    sentimento = str(sent.get("sentimento", "padrao")).lower()
    score = float(sent.get("score", 0.5))
    sinais = set(str(s).lower() for s in (sent.get("sinais") or []))

    # ── Fast-path: keywords de crise no texto (não depende da IA) ──
    match = _CRISE_KEYWORDS.search(texto)
    if match:
        keyword = match.group(0).strip()
        reason = f"Keyword de crise detectada: '{keyword}'"
        logger.warning("🚨 [URGENCY] CRITICAL — %s", reason)
        return UrgencyResult(is_urgent=True, reason=reason, severity="critical")

    # ── Sinais de crise da IA ──
    crise_sinais = sinais & _SINAIS_CRISE
    if crise_sinais:
        reason = f"Sinais de crise da IA: {', '.join(sorted(crise_sinais))}"
        logger.warning("🚨 [URGENCY] HIGH — %s", reason)
        return UrgencyResult(is_urgent=True, reason=reason, severity="high")

    # ── Frustração severa (score muito baixo) ──
    if sentimento == "frustrado" and score < 0.3:
        reason = f"Frustração severa (score={score:.2f})"
        logger.info("⚠️ [URGENCY] HIGH — %s", reason)
        return UrgencyResult(is_urgent=True, reason=reason, severity="high")

    # ── Resistência com engajamento muito baixo ──
    if sentimento == "resistente" and score < 0.2:
        reason = f"Resistência extrema (score={score:.2f})"
        logger.info("⚠️ [URGENCY] MEDIUM — %s", reason)
        return UrgencyResult(is_urgent=True, reason=reason, severity="medium")

    # ── Score de engajamento extremamente baixo (qualquer sentimento) ──
    if score < 0.15 and sentimento not in ("padrao", "curioso"):
        reason = f"Engajamento crítico ({sentimento}, score={score:.2f})"
        logger.info("⚠️ [URGENCY] MEDIUM — %s", reason)
        return UrgencyResult(is_urgent=True, reason=reason, severity="medium")

    # ── Sem urgência ──
    return UrgencyResult(is_urgent=False, reason="", severity="none")


def clear_urgency_if_resolved(
    sentiment_result: dict | None,
) -> bool:
    """
    Retorna True se o sentimento melhorou o suficiente para limpar a urgência.
    Chamado quando lead.is_urgent=True para auto-resolver.
    """
    sent = sentiment_result or {}
    sentimento = str(sent.get("sentimento", "padrao")).lower()
    score = float(sent.get("score", 0.5))

    # Se voltou a engajar positivamente, remove urgência
    if sentimento in ("interessado", "animado", "comprador", "curioso") and score >= 0.4:
        return True
    if score >= 0.6:
        return True
    return False

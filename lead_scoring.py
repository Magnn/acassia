"""
Lead scoring engine (Frente 3.24-3.25).

Score 0-100 composto por 4 componentes:
    1. Engagement (40%)  — num_msgs últimos 7d, tempo desde última msg, tempo médio resposta
    2. Sentiment (20%)   — sentimento médio últimas N msgs, palavras de intenção
    3. Funnel (20%)      — profundidade no fluxo (% nós atravessados), oferta clicada
    4. Commercial (20%)  — LTV histórico, tem pagamento, tempo desde última compra

Banda:
    70-100  → 🔥 hot
    40-69   → 🟡 warm
    0-39    → ❄️ cold

API pública:
    compute_score(lead_id, db_session=None) → (score, band, components)
    update_lead_score(lead_id) → atualiza row, retorna novo score
    recompute_all(tenant_id=None) → batch (uso em cron)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


HOT_THRESHOLD = 70
WARM_THRESHOLD = 40

INTENT_KEYWORDS_POSITIVE = {
    "preciso", "quero", "comprar", "vou pagar", "vamos", "topa", "fechado",
    "perfeito", "amei", "adorei", "obrigad", "interessante", "sim",
    "como faço", "quanto custa", "pix", "agendar",
}
INTENT_KEYWORDS_NEGATIVE = {
    "não", "depois", "amanhã", "talvez", "deixa", "pensar", "caro",
    "nao tenho", "no momento", "não dá", "fica pra próxima",
}


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _engagement_score(lead, db) -> int:
    """0-100 baseado em msgs/dias e responsividade."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Total de msgs nos últimos 7 dias (inbound + outbound)
    msgs_7d = db.query(func.count(models.Mensagem.id)).filter(
        models.Mensagem.lead_id == lead.id,
        models.Mensagem.timestamp > week_ago,
    ).scalar() or 0

    # Score logarítmico — 20 msgs/7d ≈ 100
    msgs_pts = min(100, int(40 * math.log1p(msgs_7d)))

    # Tempo desde última msg (recency boost)
    last_msg = db.query(models.Mensagem).filter(
        models.Mensagem.lead_id == lead.id,
    ).order_by(models.Mensagem.timestamp.desc()).first()

    recency_pts = 0
    if last_msg:
        last_ts = _aware(last_msg.timestamp)
        if last_ts:
            hours_ago = (now - last_ts).total_seconds() / 3600
            if hours_ago < 1:
                recency_pts = 100
            elif hours_ago < 24:
                recency_pts = 70
            elif hours_ago < 72:
                recency_pts = 40
            elif hours_ago < 7 * 24:
                recency_pts = 20
            else:
                recency_pts = 5

    # Combina (peso: msgs 60%, recency 40%)
    return int(0.6 * msgs_pts + 0.4 * recency_pts)


def _sentiment_score(lead, db) -> int:
    """
    0-100 baseado em sentimento das últimas 10 msgs do USER (lead) +
    keywords de intenção positivas/negativas.
    """
    last_user_msgs = db.query(models.Mensagem).filter(
        models.Mensagem.lead_id == lead.id,
        models.Mensagem.remetente == "user",
    ).order_by(models.Mensagem.timestamp.desc()).limit(10).all()

    if not last_user_msgs:
        return 30  # neutro-baixo (lead ainda não respondeu)

    pos_count = 0
    neg_count = 0
    intent_pos = 0
    intent_neg = 0

    for m in last_user_msgs:
        sent = (m.sentimento or "").lower()
        if "pos" in sent:
            pos_count += 1
        elif "neg" in sent:
            neg_count += 1

        text_lower = (m.texto or "").lower()
        for kw in INTENT_KEYWORDS_POSITIVE:
            if kw in text_lower:
                intent_pos += 1
                break  # 1 match por msg
        for kw in INTENT_KEYWORDS_NEGATIVE:
            if kw in text_lower:
                intent_neg += 1
                break

    total = len(last_user_msgs)
    sentiment_pts = 50 + int((pos_count - neg_count) / total * 50)  # 0-100
    intent_pts = min(100, max(0, 50 + (intent_pos - intent_neg) * 10))

    return int(0.5 * sentiment_pts + 0.5 * intent_pts)


def _funnel_score(lead, db) -> int:
    """
    Profundidade no fluxo + sinais de oferta clicada.
    Heurística simples: usa node_atual + node_historico se disponível.
    """
    historico = lead.node_historico or []
    if not isinstance(historico, list):
        historico = []

    # Profundidade aproximada — quanto mais nós passou, melhor
    # 10+ nós ≈ 100 pts
    depth_pts = min(100, len(historico) * 10)

    # Bonus por palavras-chave do node atual indicando "fim do funil"
    node_atual = (lead.node_atual or "").lower()
    if any(k in node_atual for k in ("oferta", "pagamento", "checkout", "pix", "fechar", "8_oferta", "9_entrega")):
        depth_pts = min(100, depth_pts + 30)

    # Tag/metadata: pagamento clicado
    meta = lead.metadata_json or {}
    if isinstance(meta, dict):
        if meta.get("pix_clicked") or meta.get("checkout_clicked"):
            depth_pts = min(100, depth_pts + 20)

    return depth_pts


def _commercial_score(lead, db) -> int:
    """
    LTV proxy: tem PaymentEventReceipt? Quanto tempo desde última compra?
    """
    if not lead.tenant_id:
        return 0

    payments = db.query(models.PaymentEventReceipt).filter(
        models.PaymentEventReceipt.lead_id == lead.id,
    ).order_by(models.PaymentEventReceipt.processed_at.desc()).all()

    if not payments:
        return 20  # baixo-neutro (potencial mas não comprou)

    # Tem pelo menos 1 pagamento → bonus base
    base = 50
    # +10 por pagamento adicional (max 90)
    base += min(40, len(payments) * 10)

    # Recency boost
    last = payments[0]
    last_ts = _aware(last.processed_at)
    if last_ts:
        days_ago = (datetime.now(timezone.utc) - last_ts).days
        if days_ago < 7:
            base = min(100, base + 10)
        elif days_ago > 90:
            base = max(40, base - 20)  # cliente antigo, esfriou

    return min(100, base)


def compute_score(lead_id: int, db_session=None) -> tuple[int, str, dict]:
    """
    Calcula score composto do lead. Retorna (score, band, components).
    """
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        if not lead:
            return 0, "cold", {"error": "lead_not_found"}

        engagement = _engagement_score(lead, db)
        sentiment = _sentiment_score(lead, db)
        funnel = _funnel_score(lead, db)
        commercial = _commercial_score(lead, db)

        score = int(
            0.40 * engagement +
            0.20 * sentiment +
            0.20 * funnel +
            0.20 * commercial
        )
        score = max(0, min(100, score))
        band = "hot" if score >= HOT_THRESHOLD else ("warm" if score >= WARM_THRESHOLD else "cold")

        components = {
            "engagement": engagement,
            "sentiment": sentiment,
            "funnel": funnel,
            "commercial": commercial,
        }
        return score, band, components
    finally:
        if own:
            db.close()


def update_lead_score(lead_id: int, db_session=None) -> int:
    """Recalcula e persiste score. Retorna novo score."""
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        score, band, components = compute_score(lead_id, db_session=db)
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        if not lead:
            return 0
        old_band = lead.score_band
        lead.score_value = score
        lead.score_band = band
        lead.score_components = components
        lead.score_updated_at = datetime.now(timezone.utc)
        db.commit()

        # Audit transição de banda
        if old_band != band:
            logger.info(
                "[lead_scoring.band_changed] lead=%s tenant=%s %s→%s score=%d",
                lead_id, lead.tenant_id, old_band, band, score,
            )
        return score
    finally:
        if own:
            db.close()


def recompute_all(tenant_id: Optional[str] = None, *, batch_size: int = 100) -> int:
    """
    Batch recompute pra todos os leads. Use em cron daily.
    Returns número de leads atualizados.
    """
    db = SessionLocal()
    updated = 0
    try:
        q = db.query(models.Lead.id)
        if tenant_id:
            q = q.filter(models.Lead.tenant_id == tenant_id)
        ids = [r[0] for r in q.all()]

        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            for lead_id in batch:
                try:
                    update_lead_score(lead_id, db_session=db)
                    updated += 1
                except Exception as exc:
                    logger.warning("[lead_scoring.recompute] lead=%s falha: %s", lead_id, exc)
            db.commit()

        logger.info("[lead_scoring.recompute_all] tenant=%s updated=%d", tenant_id, updated)
    finally:
        db.close()
    return updated

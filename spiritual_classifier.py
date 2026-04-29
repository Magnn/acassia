"""
Classifier de intent espiritual (Frente 4.19).

Categorias canonicas:
    amor         — relacionamento, ex/atual, paixao
    dinheiro     — prosperidade, financas, divida
    saude        — doenca propria/familia, mente/corpo
    carreira     — trabalho, profissao, demissao, estudo
    familia      — pais/filhos/irmaos, conflitos
    espiritual   — protecao, mediunidade, fe
    decisao      — encruzilhada, escolha entre A/B
    luto         — perda, viuvez, terminos significativos

Heuristica + Gemini (fallback heuristica se IA off/quota).
classify_text() retorna {categories, urgency, emotion}.
classify_lead_recent() agrega ultimas N msgs e atualiza Lead.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from collections import Counter
from datetime import datetime, timezone

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


CATEGORIES = (
    "amor", "dinheiro", "saude", "carreira",
    "familia", "espiritual", "decisao", "luto",
)
URGENCY_LEVELS = ("low", "med", "high")


_KEYWORDS = {
    "amor": ("ex", "namorad", "marido", "esposa", "amor", "paixa", "relacao", "trair", "voltar", "infidel", "casamento", "ficar", "ela me", "ele me"),
    "dinheiro": ("dinheiro", "divida", "boleto", "salario", "emprest", "renda", "finance", "pagar", "conta atras", "falencia", "negocio"),
    "saude": ("doenca", "diagnost", "medic", "hospital", "saude", "exame", "depres", "ansied", "panico", "insonia"),
    "carreira": ("trabalho", "emprego", "carreira", "demit", "patrao", "concurso", "facul", "estud", "promocao", "negocio"),
    "familia": ("filho", "filha", "mae", "pai", "mae e", "irmao", "familia", "sogra", "sogro", "criancas"),
    "espiritual": ("protec", "mau olh", "feiti", "guia", "espirit", "rezar", "fe", "deus", "anjos", "encosto", "mediun", "limpeza"),
    "decisao": ("escolh", "decid", "encruzilhad", "duas estrad", "ficar ou", "qual caminho", "o que faco"),
    "luto": ("morr", "faleceu", "viuva", "luto", "saudade", "perdi", "termin", "acabou tudo", "morte"),
}


def _normalize(text: str) -> str:
    """Lowercase + remove acentos pra matching estavel."""
    nf = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nf if not unicodedata.combining(c)).lower()


def _heuristic_classify(text: str) -> dict:
    t = _normalize(text)
    cats: Counter = Counter()
    for cat, kws in _KEYWORDS.items():
        for kw in kws:
            if kw in t:
                cats[cat] += 1

    categories = [c for c, _ in cats.most_common(3)]

    # Urgencia heuristica
    urgency = "low"
    if any(w in t for w in ("urgente", "preciso muito", "agora", "ja", "hoje", "n aguento", "nao consigo mais", "to desespera", "to em panico")):
        urgency = "high"
    elif any(w in t for w in ("estou pensando", "queria saber", "duvida", "talvez", "as vezes")):
        urgency = "med"

    # Emocao dominante
    emotion = None
    if any(w in t for w in ("trist", "chor", "deprim", "vazio")):
        emotion = "tristeza"
    elif any(w in t for w in ("ansiedad", "panic", "nervos", "preocup")):
        emotion = "ansiedade"
    elif any(w in t for w in ("raiva", "odeio", "irritad", "fur")):
        emotion = "raiva"
    elif any(w in t for w in ("medo", "assust", "perigo")):
        emotion = "medo"
    elif any(w in t for w in ("esperan", "feliz", "anim", "alegr", "ria")):
        emotion = "esperanca"

    return {
        "categories": categories,
        "urgency": urgency,
        "emotion": emotion,
        "source": "heuristic",
    }


def _gemini_classify(text: str) -> dict | None:
    """Tenta Gemini; retorna None em qualquer falha."""
    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            return None
        prompt = (
            "Classifique a mensagem abaixo segundo o tema espiritual dominante. "
            "Categorias validas: amor, dinheiro, saude, carreira, familia, "
            "espiritual, decisao, luto. Pode listar ate 3.\n"
            "Retorne JSON {\"categories\": [...], \"urgency\": \"low|med|high\", "
            "\"emotion\": \"<uma palavra>\"}. Apenas o JSON.\n\n"
            f"Mensagem: \"\"\"{text[:1000]}\"\"\""
        )
        resp = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 200, "temperature": 0.2,
                    "response_mime_type": "application/json"},
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        cats = parsed.get("categories") or []
        cats = [c.lower() for c in cats if isinstance(c, str) and c.lower() in CATEGORIES][:3]
        urgency = (parsed.get("urgency") or "low").lower()
        if urgency not in URGENCY_LEVELS:
            urgency = "low"
        emotion = (parsed.get("emotion") or None)
        if emotion:
            emotion = str(emotion).strip().lower()[:30] or None
        return {
            "categories": cats,
            "urgency": urgency,
            "emotion": emotion,
            "source": "gemini",
        }
    except Exception as exc:
        logger.warning("[spiritual_classifier.gemini] falha: %s", exc)
        return None


def classify_text(text: str, *, prefer_gemini: bool = True) -> dict:
    if not text or not text.strip():
        return {"categories": [], "urgency": "low", "emotion": None, "source": "empty"}
    if prefer_gemini:
        result = _gemini_classify(text)
        if result and result.get("categories"):
            return result
    return _heuristic_classify(text)


def classify_message(msg: models.Mensagem, *, prefer_gemini: bool = True) -> dict:
    intent = classify_text(msg.texto or "", prefer_gemini=prefer_gemini)
    msg.spiritual_intent = intent
    return intent


def aggregate_lead(lead_id: int, *, last_n: int = 10, db_session=None) -> dict:
    """
    Classifica ate as ultimas N msgs do lead e atualiza Lead.spiritual_*.
    Retorna {top_category, intent_aggregate}.
    """
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        if not lead:
            return {"error": "lead_not_found"}

        msgs = db.query(models.Mensagem).filter_by(
            lead_id=lead_id, remetente="lead",
        ).order_by(models.Mensagem.timestamp.desc()).limit(last_n).all()

        if not msgs:
            return {"top_category": None, "intent": None}

        cat_counter: Counter = Counter()
        urgencies = []
        emotions: Counter = Counter()
        for m in msgs:
            existing = m.spiritual_intent
            if not existing or not existing.get("categories"):
                # Quota check: classifica via Gemini so as 3 mais recentes;
                # demais via heuristica.
                use_gemini = msgs.index(m) < 3
                existing = classify_message(m, prefer_gemini=use_gemini)
            for c in existing.get("categories") or []:
                cat_counter[c] += 1
            urgencies.append(existing.get("urgency") or "low")
            emo = existing.get("emotion")
            if emo:
                emotions[emo] += 1

        top_category = cat_counter.most_common(1)[0][0] if cat_counter else None

        # Urgencia dominante (max)
        urgency_rank = {"low": 0, "med": 1, "high": 2}
        top_urgency = "low"
        for u in urgencies:
            if urgency_rank.get(u, 0) > urgency_rank.get(top_urgency, 0):
                top_urgency = u

        top_emotion = emotions.most_common(1)[0][0] if emotions else None

        intent = {
            "categories": [c for c, _ in cat_counter.most_common(3)],
            "categories_distribution": dict(cat_counter),
            "urgency": top_urgency,
            "emotion": top_emotion,
            "msgs_analyzed": len(msgs),
        }

        lead.spiritual_category = top_category
        lead.spiritual_intent = intent
        lead.spiritual_intent_at = datetime.now(timezone.utc)
        db.commit()

        return {"top_category": top_category, "intent": intent}
    finally:
        if own:
            db.close()


def recompute_recent_leads(*, days_back: int = 7, max_leads: int = 200) -> int:
    """Cron job: recomputa intents de leads ativos nos ultimos N dias."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    db = SessionLocal()
    n = 0
    try:
        leads = db.query(models.Lead).filter(
            models.Lead.atualizado_em > cutoff,
            models.Lead.opt_out == False,  # noqa: E712
        ).order_by(models.Lead.atualizado_em.desc()).limit(max_leads).all()
        for lead in leads:
            try:
                aggregate_lead(lead.id, last_n=10, db_session=db)
                n += 1
            except Exception as exc:
                logger.warning("[spiritual_classifier.recompute] lead=%s falha: %s",
                               lead.id, exc)
        return n
    finally:
        db.close()

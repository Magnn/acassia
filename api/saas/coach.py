"""
AI Coach endpoints (Frente 6.1, 6.2, 6.6).

Endpoints:
    POST /saas/coach/copy/generate    — gera 5 variações de copy
    POST /saas/coach/copy/rewrite     — reescreve msg pra outro tom/comprimento
    POST /saas/coach/lead/summary     — resume conversa do lead em bullets
    POST /saas/coach/persona/generate — gera persona completa a partir de inputs
"""

from __future__ import annotations

import json
import logging
import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from extensions import limiter


logger = logging.getLogger(__name__)
coach_bp = Blueprint("saas_coach", __name__, url_prefix="/saas/coach")


def _gemini():
    """Returns Personalizer instance (Gemini client) ou None."""
    try:
        from personalizer import Personalizer
        p = Personalizer()
        return p if p.client else None
    except Exception as exc:
        logger.warning("[coach] gemini init falhou: %s", exc)
        return None


def _generate(prompt: str, *, expect_json: bool = False, max_tokens: int = 800) -> str | dict | None:
    """Wrapper genérico Gemini com tratamento de erro + parse JSON."""
    p = _gemini()
    if not p:
        return None
    try:
        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
        )
        text = (resp.text or "").strip()
        if not text:
            return None
        if expect_json:
            # Remove markdown code fences se houver
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning("[coach] JSON parse falhou: %s", text[:200])
                return None
        return text
    except Exception as exc:
        logger.warning("[coach.generate] erro: %s", exc)
        return None


def _consume_quota_safe(tenant_id: str, estimated_tokens: int) -> bool:
    """Consome quota Gemini. False se exceeded — endpoint retorna 402."""
    try:
        import quota
        allowed, _, _ = quota.consume_quota(
            tenant_id, "gemini_tokens_month", estimated_tokens,
        )
        return allowed
    except Exception:
        return True  # fail open


# ─── Auto-copy generator (Frente 6.1) ─────────────────────────────────


@coach_bp.route("/copy/generate", methods=["POST"])
@login_required
@limiter.limit("30/hour")
def generate_copy():
    """
    Gera 5 variações de copy persuasiva pra WhatsApp espiritual.
    Body: {intent, persona?, tone?, length?, include_cta?}
    """
    body = request.get_json(silent=True) or {}
    intent = (body.get("intent") or "").strip()
    persona = (body.get("persona") or "").strip()
    tone = (body.get("tone") or "casual").strip().lower()
    length = (body.get("length") or "medium").strip().lower()
    include_cta = bool(body.get("include_cta", False))

    if not intent or len(intent) < 5:
        return jsonify({"error": "intent_required", "min": 5}), 422
    if tone not in ("casual", "formal", "mistico", "direto"):
        return jsonify({"error": "tone_invalid"}), 422
    if length not in ("curto", "medium", "longo"):
        return jsonify({"error": "length_invalid"}), 422

    if not _consume_quota_safe(current_user.tenant_id, 1500):
        return jsonify({"error": "quota_exceeded", "kind": "gemini_tokens_month"}), 402

    length_chars = {"curto": "max 80 chars", "medium": "120-200 chars", "longo": "300-500 chars"}[length]
    cta_hint = "Inclua um CTA claro no final." if include_cta else ""

    prompt = f"""Você é especialista em copy persuasiva pra WhatsApp do nicho espiritual brasileiro
(tarot, astrologia, espiritualidade). Gere 5 variações curtas, em pt-BR.

Persona da tarólaga (se informada): {persona or "tom geral acolhedor"}
Tom: {tone}
Comprimento: {length_chars}
{cta_hint}

Intenção da mensagem: {intent}

Retorne JSON estrito (sem comentários, sem ```):
{{"variations": [
  {{"text": "...", "style": "rótulo curto do estilo (ex: poética, direta, urgente)"}},
  ...
]}}
Exatamente 5 variações."""

    result = _generate(prompt, expect_json=True, max_tokens=1500)
    if not result or "variations" not in result:
        return jsonify({"error": "generation_failed"}), 500

    return jsonify({
        "ok": True,
        "variations": result["variations"][:5],
    })


# ─── Rewrite / improve message (Frente 6.6) ───────────────────────────


@coach_bp.route("/copy/rewrite", methods=["POST"])
@login_required
@limiter.limit("30/hour")
def rewrite_copy():
    """
    Reescreve uma msg existente. Útil pra "msg ruim" identificada em analytics.
    Body: {original, target_tone?, target_length?, count?}
    """
    body = request.get_json(silent=True) or {}
    original = (body.get("original") or "").strip()
    target_tone = (body.get("target_tone") or "casual").strip().lower()
    target_length = (body.get("target_length") or "medium").strip().lower()
    count = min(int(body.get("count") or 3), 5)

    if not original:
        return jsonify({"error": "original_required"}), 422

    if not _consume_quota_safe(current_user.tenant_id, 1200):
        return jsonify({"error": "quota_exceeded"}), 402

    prompt = f"""Você é editor de copy pra WhatsApp. Reescreva a mensagem abaixo
em {count} variações, mantendo o significado central mas variando tom e fraseado.

Tom alvo: {target_tone}
Comprimento alvo: {target_length}

Original:
{original}

Retorne JSON estrito:
{{"rewrites": [{{"text": "...", "improvement_reason": "rótulo curto"}}, ...]}}
Exatamente {count} variações."""

    result = _generate(prompt, expect_json=True)
    if not result or "rewrites" not in result:
        return jsonify({"error": "generation_failed"}), 500

    return jsonify({"ok": True, "rewrites": result["rewrites"][:count]})


# ─── Lead summary (Frente 6.2) ────────────────────────────────────────


@coach_bp.route("/lead/<int:lead_id>/summary", methods=["POST"])
@login_required
@limiter.limit("60/hour")
def lead_summary(lead_id: int):
    """
    Resume conversa do lead em bullets. Output JSON com:
        - main_question
        - personal_info_collected
        - current_funnel_stage
        - sentiment_dominant
        - suggested_next_action
    """
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        msgs = db.query(models.Mensagem).filter_by(
            lead_id=lead_id,
        ).order_by(models.Mensagem.timestamp.asc()).limit(80).all()
        if not msgs:
            return jsonify({"error": "no_messages"}), 400

        if not _consume_quota_safe(current_user.tenant_id, 2000):
            return jsonify({"error": "quota_exceeded"}), 402

        # Monta histórico compacto
        history_lines = []
        for m in msgs:
            role = "USUARIO" if m.remetente == "user" else "BOT"
            text = (m.texto or "")[:300]
            history_lines.append(f"{role}: {text}")
        history = "\n".join(history_lines[-50:])  # últimas 50

        prompt = f"""Você é um analista de conversas de WhatsApp do nicho espiritual.
Analise o histórico e retorne JSON estrito com 5 campos:

- main_question: pergunta principal/urgência do lead em 1 frase
- personal_info_collected: lista de info pessoal coletada (signo, idade, status, etc)
- current_funnel_stage: estágio atual em palavras simples (ex: "perguntou preço", "indeciso após oferta")
- sentiment_dominant: positive|negative|neutral|mixed + justificativa curta
- suggested_next_action: próxima ação concreta pro tarólogo (1-2 frases)

Lead: {lead.nome or lead.telefone}
Score: {lead.score_value or 0} ({lead.score_band or "cold"})
Nó atual: {lead.node_atual or "?"}

Histórico (oldest first):
{history}

Retorne SOMENTE o JSON sem markdown:"""

        result = _generate(prompt, expect_json=True, max_tokens=1500)
        if not result:
            return jsonify({"error": "generation_failed"}), 500

        return jsonify({"ok": True, "summary": result, "msgs_analyzed": len(msgs)})
    finally:
        db.close()


# ─── Persona generator (Frente 5.4 / 6.7) ─────────────────────────────


@coach_bp.route("/persona/generate", methods=["POST"])
@login_required
@limiter.limit("20/hour")
def generate_persona():
    """
    Gera persona completa a partir de inputs simples.
    Body: {tom, energia, emoji_level, length, specialty, name?}
    """
    body = request.get_json(silent=True) or {}
    tom = (body.get("tom") or "casual").strip().lower()
    energia = (body.get("energia") or "media").strip().lower()
    emoji_level = (body.get("emoji_level") or "moderado").strip().lower()
    length = (body.get("length") or "medium").strip().lower()
    specialty = (body.get("specialty") or "geral").strip().lower()
    name = (body.get("name") or "").strip()

    if not _consume_quota_safe(current_user.tenant_id, 1500):
        return jsonify({"error": "quota_exceeded"}), 402

    prompt = f"""Você é especialista em criação de personas pra atendentes IA do nicho espiritual brasileiro.

Crie uma persona completa baseada nesses inputs:
- Tom: {tom}
- Energia: {energia}
- Nível de emojis: {emoji_level}
- Comprimento das mensagens: {length}
- Especialidade: {specialty}
- Nome desejado: {name or "sugerir um"}

Retorne JSON estrito (sem markdown):
{{
  "name": "nome curto (1-2 palavras)",
  "presentation": "apresentação em 2-3 frases curtas",
  "greeting_template": "saudação inicial pra novo lead (max 200 chars)",
  "reading_style": "estilo de fazer leituras em 1 frase",
  "instructions": {{
    "do": ["3-5 itens do que SEMPRE fazer"],
    "dont": ["3-5 itens do que NUNCA fazer"]
  }},
  "tom_descritor": "1 frase descritiva do tom"
}}"""

    result = _generate(prompt, expect_json=True, max_tokens=1500)
    if not result:
        return jsonify({"error": "generation_failed"}), 500

    return jsonify({"ok": True, "persona": result})


# ─── Coach review do funil (Frente 6.5) ───────────────────────────────


@coach_bp.route("/funnel-review", methods=["POST"])
@login_required
@limiter.limit("10/hour")
def funnel_review():
    """
    Coach analisa funnel + dados do tenant e gera review acionável.
    Body: {flow_id|flow_slug, period_days?}
    """
    body = request.get_json(silent=True) or {}
    flow_id = body.get("flow_id")
    flow_slug = body.get("flow_slug")
    period_days = int(body.get("period_days") or 30)

    if not flow_id and not flow_slug:
        return jsonify({"error": "flow_required"}), 422

    import funnel_analytics
    funnel = funnel_analytics.funnel_for_flow(
        tenant_id=current_user.tenant_id,
        flow_id=int(flow_id) if flow_id else None,
        flow_slug=flow_slug,
        period_days=period_days,
    )

    if funnel.get("low_confidence"):
        return jsonify({
            "ok": True,
            "low_confidence": True,
            "message": "Dados insuficientes pra review (precisa de pelo menos 50 leads).",
        })

    if not _consume_quota_safe(current_user.tenant_id, 2500):
        return jsonify({"error": "quota_exceeded"}), 402

    steps_str = "\n".join([
        f"- {s['node_id']}: {s['entered']} entered, {s['drop']} drop ({s['drop_pct']}%)"
        for s in funnel["steps"]
    ])

    prompt = f"""Você é Cigana Coach, conselheira de tarólogas SaaS. Analise esse funnel
e gere review acionável em pt-BR.

Funnel: {flow_slug or f'flow {flow_id}'}
Período: {period_days} dias
Conversão geral: {funnel['overall_conversion_pct']}%
Total leads: {funnel['unique_leads']}

Steps:
{steps_str}

Retorne JSON estrito:
{{
  "overall_score": 0-100,
  "strengths": ["2-3 pontos fortes"],
  "opportunities": [
    {{"node_id": "...", "issue": "1 frase do problema", "suggestion": "1 ação concreta"}}
  ],
  "key_metric_callout": "1 frase destacando a métrica mais importante"
}}"""

    result = _generate(prompt, expect_json=True, max_tokens=2000)
    if not result:
        return jsonify({"error": "generation_failed"}), 500

    return jsonify({"ok": True, "review": result, "funnel_summary": {
        "conversion_pct": funnel["overall_conversion_pct"],
        "unique_leads": funnel["unique_leads"],
        "high_drop_nodes": [
            s["node_id"] for s in funnel["steps"] if s.get("is_high_drop")
        ],
    }})

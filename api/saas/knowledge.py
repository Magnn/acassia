"""
api/saas/knowledge.py — Base de Conhecimento Dinâmica (Context Stuffing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRUD de fatos + Wizard batch + Auto-learn hook.
Cache Redis: tenant:{tenant_id}:knowledge_base (TTL 300s).
Invalidação automática em toda operação de escrita.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
knowledge_bp = Blueprint("saas_knowledge", __name__, url_prefix="/saas/knowledge")

_REDIS_KB_PREFIX = "tenant:"
_REDIS_KB_SUFFIX = ":knowledge_base"
_REDIS_KB_TTL = 300  # 5 min


# ─── Redis helpers ──────────────────────────────────────────────────

def _redis():
    """Obtém conexão Redis (fail-open: retorna None se indisponível)."""
    try:
        from reliability.redis_inbound import _client as redis_client_fn
        return redis_client_fn()
    except Exception:
        return None


def _cache_key(tenant_id: str) -> str:
    return f"{_REDIS_KB_PREFIX}{tenant_id}{_REDIS_KB_SUFFIX}"


def _invalidate_cache(tenant_id: str) -> None:
    """Apaga cache do tenant no Redis → próxima leitura recarrega do DB."""
    r = _redis()
    if r:
        try:
            r.delete(_cache_key(tenant_id))
        except Exception:
            pass


def get_knowledge_base_cached(tenant_id: str) -> str:
    """
    Retorna o bloco formatado da Knowledge Base para injeção no prompt.
    Fluxo: Redis cache → DB fallback → formata → salva no Redis.

    Retorna string vazia se não houver fatos.
    """
    r = _redis()
    key = _cache_key(tenant_id)

    # 1. Tenta Redis
    if r:
        try:
            cached = r.get(key)
            if cached is not None:
                return cached
        except Exception:
            pass

    # 2. Fallback: consulta DB
    db = SessionLocal()
    try:
        facts = (
            db.query(models.AIKnowledgeFact)
            .filter_by(tenant_id=tenant_id, active=True)
            .order_by(models.AIKnowledgeFact.category, models.AIKnowledgeFact.id)
            .limit(200)
            .all()
        )
        if not facts:
            # Cache vazio para evitar query repetida
            if r:
                try:
                    r.setex(key, _REDIS_KB_TTL, "")
                except Exception:
                    pass
            return ""

        # 3. Formata com delimitadores XML anti-alucinação
        lines = ["<BASE_DE_CONHECIMENTO>"]
        current_cat = None
        for f in facts:
            if f.category != current_cat:
                current_cat = f.category
                cat_label = {
                    "servico": "SERVIÇOS E TERAPIAS",
                    "preco": "PREÇOS E CONDIÇÕES",
                    "politica": "POLÍTICAS E REGRAS",
                    "faq": "PERGUNTAS FREQUENTES",
                    "tom": "TOM DE VOZ E PERSONALIDADE",
                }.get(current_cat, current_cat.upper() if current_cat else "GERAL")
                lines.append(f"\n[{cat_label}]")
            if f.question:
                lines.append(f"P: {f.question}")
            lines.append(f"R: {f.answer}")

        lines.append("</BASE_DE_CONHECIMENTO>")
        lines.append("")
        lines.append(
            "REGRA ABSOLUTA: A <BASE_DE_CONHECIMENTO> acima é a verdade absoluta do seu negócio. "
            "NUNCA invente preços, terapias, prazos ou regras que não estejam explicitamente "
            "detalhados nela. Se o paciente perguntar algo fora dessa base, diga que vai verificar "
            "e encaminhe para atendimento humano."
        )
        lines.append("")

        block = "\n".join(lines)

        # 4. Salva no Redis
        if r:
            try:
                r.setex(key, _REDIS_KB_TTL, block)
            except Exception:
                pass

        return block
    finally:
        db.close()


# ─── CRUD Endpoints ─────────────────────────────────────────────────

@knowledge_bp.route("/facts", methods=["GET"])
@login_required
def list_facts():
    """Lista todos os fatos da base de conhecimento do tenant."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        category = request.args.get("category")
        active_only = request.args.get("active", "true").lower() != "false"

        q = db.query(models.AIKnowledgeFact).filter_by(tenant_id=tid)
        if category:
            q = q.filter_by(category=category)
        if active_only:
            q = q.filter_by(active=True)
        q = q.order_by(models.AIKnowledgeFact.category, models.AIKnowledgeFact.id)

        facts = q.limit(500).all()
        return jsonify({
            "facts": [
                {
                    "id": f.id,
                    "category": f.category,
                    "question": f.question,
                    "answer": f.answer,
                    "source": f.source,
                    "active": f.active,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in facts
            ],
            "total": len(facts),
        })
    finally:
        db.close()


@knowledge_bp.route("/facts", methods=["POST"])
@login_required
def create_fact():
    """Cria um fato individual."""
    db = SessionLocal()
    try:
        data = request.json or {}
        answer = (data.get("answer") or "").strip()
        if not answer:
            return jsonify({"error": "answer is required"}), 422

        fact = models.AIKnowledgeFact(
            tenant_id=current_user.tenant_id,
            category=data.get("category", "geral"),
            question=(data.get("question") or "").strip() or None,
            answer=answer,
            source=data.get("source", "manual"),
        )
        db.add(fact)
        db.commit()
        _invalidate_cache(current_user.tenant_id)
        return jsonify({"ok": True, "fact_id": fact.id}), 201
    finally:
        db.close()


@knowledge_bp.route("/facts/<int:fact_id>", methods=["PATCH"])
@login_required
def update_fact(fact_id):
    """Atualiza um fato existente."""
    db = SessionLocal()
    try:
        fact = db.query(models.AIKnowledgeFact).filter_by(
            id=fact_id, tenant_id=current_user.tenant_id,
        ).first()
        if not fact:
            return jsonify({"error": "not_found"}), 404

        data = request.json or {}
        if "category" in data:
            fact.category = data["category"]
        if "question" in data:
            fact.question = (data["question"] or "").strip() or None
        if "answer" in data:
            answer = (data["answer"] or "").strip()
            if not answer:
                return jsonify({"error": "answer cannot be empty"}), 422
            fact.answer = answer
        if "active" in data:
            fact.active = bool(data["active"])

        db.commit()
        _invalidate_cache(current_user.tenant_id)
        return jsonify({"ok": True})
    finally:
        db.close()


@knowledge_bp.route("/facts/<int:fact_id>", methods=["DELETE"])
@login_required
def delete_fact(fact_id):
    """Remove um fato (hard delete)."""
    db = SessionLocal()
    try:
        fact = db.query(models.AIKnowledgeFact).filter_by(
            id=fact_id, tenant_id=current_user.tenant_id,
        ).first()
        if not fact:
            return jsonify({"error": "not_found"}), 404
        db.delete(fact)
        db.commit()
        _invalidate_cache(current_user.tenant_id)
        return jsonify({"ok": True})
    finally:
        db.close()


# ─── Wizard Batch Import ────────────────────────────────────────────

@knowledge_bp.route("/wizard", methods=["POST"])
@login_required
def wizard_import():
    """
    Importação batch via wizard interativo.
    Converte respostas do wizard em fatos estruturados.

    Body: {
      "services": [{"name": "Tarot", "price": 120, "duration": "40min"}],
      "cancellation_policy": "24h antes sem custo",
      "tone_of_voice": "Acolhedora, emojis de lua",
      "faq": [{"q": "Atende criança?", "a": "Sim, a partir de 7 anos"}],
      "about": "Terapeuta holística com 10 anos de experiência..."
    }
    """
    db = SessionLocal()
    try:
        data = request.json or {}
        tid = current_user.tenant_id
        created = 0

        # Serviços → category=servico
        for svc in (data.get("services") or []):
            if not isinstance(svc, dict):
                continue
            name = (svc.get("name") or "").strip()
            if not name:
                continue
            parts = [name]
            if svc.get("price"):
                parts.append(f"R$ {svc['price']}")
            if svc.get("duration"):
                parts.append(f"duração: {svc['duration']}")
            answer = " — ".join(parts)
            db.add(models.AIKnowledgeFact(
                tenant_id=tid, category="servico",
                question=f"Quais são os serviços oferecidos? ({name})",
                answer=answer, source="wizard",
            ))
            created += 1

        # Preços individuais → category=preco
        for svc in (data.get("services") or []):
            if isinstance(svc, dict) and svc.get("price") and svc.get("name"):
                db.add(models.AIKnowledgeFact(
                    tenant_id=tid, category="preco",
                    question=f"Quanto custa {svc['name']}?",
                    answer=f"O valor de {svc['name']} é R$ {svc['price']}.",
                    source="wizard",
                ))
                created += 1

        # Política de cancelamento → category=politica
        cancel = (data.get("cancellation_policy") or "").strip()
        if cancel:
            db.add(models.AIKnowledgeFact(
                tenant_id=tid, category="politica",
                question="Qual a política de cancelamento ou reagendamento?",
                answer=cancel, source="wizard",
            ))
            created += 1

        # Tom de voz → category=tom
        tone = (data.get("tone_of_voice") or "").strip()
        if tone:
            db.add(models.AIKnowledgeFact(
                tenant_id=tid, category="tom",
                answer=f"Tom de voz desejado: {tone}", source="wizard",
            ))
            created += 1

        # FAQ → category=faq
        for faq in (data.get("faq") or []):
            if not isinstance(faq, dict):
                continue
            q = (faq.get("q") or faq.get("question") or "").strip()
            a = (faq.get("a") or faq.get("answer") or "").strip()
            if a:
                db.add(models.AIKnowledgeFact(
                    tenant_id=tid, category="faq",
                    question=q or None, answer=a, source="wizard",
                ))
                created += 1

        # Sobre o negócio → category=geral
        about = (data.get("about") or "").strip()
        if about:
            db.add(models.AIKnowledgeFact(
                tenant_id=tid, category="geral",
                answer=about, source="wizard",
            ))
            created += 1

        db.commit()
        _invalidate_cache(tid)

        return jsonify({"ok": True, "facts_created": created}), 201
    finally:
        db.close()


# ─── Auto-Learn Hook (CRM) ─────────────────────────────────────────

@knowledge_bp.route("/learn", methods=["POST"])
@login_required
def auto_learn():
    """
    Hook de auto-aprendizado: operador confirma que a IA deve aprender
    a partir de uma resposta humana no CRM.

    Body: {
      "question": "Atende criança com autismo?",
      "answer": "Sim! Atendemos crianças a partir de 7 anos...",
      "category": "faq",
      "lead_id": 123  (opcional, para referência)
    }
    """
    db = SessionLocal()
    try:
        data = request.json or {}
        answer = (data.get("answer") or "").strip()
        if not answer:
            return jsonify({"error": "answer is required"}), 422

        question = (data.get("question") or "").strip() or None
        category = data.get("category", "faq")
        tid = current_user.tenant_id

        # Deduplica: se já existe fato com mesma pergunta, atualiza a resposta
        existing = None
        if question:
            existing = db.query(models.AIKnowledgeFact).filter_by(
                tenant_id=tid, question=question, active=True,
            ).first()

        if existing:
            existing.answer = answer
            existing.updated_at = datetime.now(timezone.utc)
            fact_id = existing.id
            action = "updated"
        else:
            fact = models.AIKnowledgeFact(
                tenant_id=tid,
                category=category,
                question=question,
                answer=answer,
                source="auto_learn",
            )
            db.add(fact)
            db.flush()
            fact_id = fact.id
            action = "created"

        db.commit()
        _invalidate_cache(tid)

        logger.info(
            "[knowledge.learn] tenant=%s action=%s fact_id=%s q=%s",
            tid, action, fact_id, (question or "")[:60],
        )

        return jsonify({"ok": True, "fact_id": fact_id, "action": action}), 201
    finally:
        db.close()


# ─── Stats ──────────────────────────────────────────────────────────

@knowledge_bp.route("/stats", methods=["GET"])
@login_required
def kb_stats():
    """Estatísticas da base de conhecimento."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        tid = current_user.tenant_id
        total = db.query(func.count(models.AIKnowledgeFact.id)).filter_by(
            tenant_id=tid, active=True,
        ).scalar() or 0
        by_category = dict(
            db.query(models.AIKnowledgeFact.category, func.count(models.AIKnowledgeFact.id))
            .filter_by(tenant_id=tid, active=True)
            .group_by(models.AIKnowledgeFact.category).all()
        )
        by_source = dict(
            db.query(models.AIKnowledgeFact.source, func.count(models.AIKnowledgeFact.id))
            .filter_by(tenant_id=tid, active=True)
            .group_by(models.AIKnowledgeFact.source).all()
        )
        return jsonify({
            "total_facts": total,
            "by_category": by_category,
            "by_source": by_source,
        })
    finally:
        db.close()

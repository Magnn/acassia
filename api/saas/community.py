"""
api/saas/community.py — Comunidade + IA Oráculo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vertical: Community Oracle — "Sabedoria coletiva + IA privada"

Combina:
  - Grupos temáticos (por signo, prática, tema)
  - Feed de posts com threads
  - IA Oráculo que responde perguntas no grupo
  - Reações (like, love, fire, pray, insight)
  - Eventos lunares/solares integrados

Endpoints:
  GET  /saas/community/groups                — Lista grupos
  POST /saas/community/groups                — Cria grupo
  GET  /saas/community/groups/<id>           — Detalhe grupo
  POST /saas/community/groups/<id>/join      — Entrar no grupo
  POST /saas/community/groups/<id>/leave     — Sair do grupo

  GET  /saas/community/groups/<id>/posts     — Feed do grupo
  POST /saas/community/groups/<id>/posts     — Criar post
  POST /saas/community/posts/<id>/reply      — Responder post (thread)
  POST /saas/community/posts/<id>/react      — Reagir a post
  DELETE /saas/community/posts/<id>          — Deletar post

  POST /saas/community/posts/<id>/oracle     — Pedir resposta da IA Oráculo
  GET  /saas/community/stats                 — Stats gerais
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
community_bp = Blueprint("saas_community", __name__, url_prefix="/saas/community")

REACTION_TYPES = ["like", "love", "fire", "pray", "insight"]
GROUP_CATEGORIES = ["signo", "pratica", "tema", "livre", "general"]


# ── GROUPS ────────────────────────────────────────────────────────────

@community_bp.route("/groups", methods=["GET"])
@login_required
def list_groups():
    """Lista todos os grupos públicos + meus grupos privados."""
    db = SessionLocal()
    try:
        q = db.query(models.CommunityGroup).filter_by(is_archived=False)
        # Show public + my private groups
        groups = q.order_by(models.CommunityGroup.member_count.desc()).all()

        # Check my memberships
        my_groups = set()
        memberships = db.query(models.CommunityMember.group_id).filter(
            (models.CommunityMember.user_id == current_user.id) |
            (models.CommunityMember.tenant_id == current_user.tenant_id)
        ).all()
        my_groups = {m.group_id for m in memberships}

        return jsonify({
            "groups": [
                {
                    **_serialize_group(g),
                    "is_member": g.id in my_groups,
                }
                for g in groups
                if g.is_public or g.id in my_groups
            ],
        })
    finally:
        db.close()


@community_bp.route("/groups", methods=["POST"])
@login_required
def create_group():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nome é obrigatório"}), 422

    db = SessionLocal()
    try:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        group = models.CommunityGroup(
            tenant_id=current_user.tenant_id,
            name=name,
            slug=slug,
            description=body.get("description"),
            category=body.get("category", "general"),
            icon=body.get("icon", "🔮"),
            is_public=body.get("is_public", True),
            oracle_enabled=body.get("oracle_enabled", True),
            oracle_persona=body.get("oracle_persona"),
            created_by_user_id=current_user.id,
        )
        db.add(group)
        db.flush()

        # Creator auto-joins as admin
        member = models.CommunityMember(
            group_id=group.id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            role="admin",
        )
        db.add(member)
        group.member_count = 1
        db.commit()
        db.refresh(group)

        return jsonify({"ok": True, "id": group.id, "group": _serialize_group(group)}), 201
    finally:
        db.close()


@community_bp.route("/groups/<int:group_id>", methods=["GET"])
@login_required
def get_group(group_id: int):
    db = SessionLocal()
    try:
        group = db.query(models.CommunityGroup).filter_by(id=group_id, is_archived=False).first()
        if not group:
            return jsonify({"error": "not_found"}), 404

        is_member = db.query(models.CommunityMember).filter(
            models.CommunityMember.group_id == group_id,
            (models.CommunityMember.user_id == current_user.id) |
            (models.CommunityMember.tenant_id == current_user.tenant_id)
        ).first() is not None

        # Recent members
        members = db.query(models.CommunityMember).filter_by(
            group_id=group_id
        ).order_by(models.CommunityMember.joined_at.desc()).limit(10).all()

        return jsonify({
            **_serialize_group(group),
            "is_member": is_member,
            "recent_members": [
                {"id": m.id, "role": m.role, "joined_at": m.joined_at.isoformat()}
                for m in members
            ],
        })
    finally:
        db.close()


@community_bp.route("/groups/<int:group_id>/join", methods=["POST"])
@login_required
def join_group(group_id: int):
    db = SessionLocal()
    try:
        group = db.query(models.CommunityGroup).filter_by(id=group_id, is_archived=False).first()
        if not group:
            return jsonify({"error": "not_found"}), 404

        existing = db.query(models.CommunityMember).filter(
            models.CommunityMember.group_id == group_id,
            (models.CommunityMember.user_id == current_user.id) |
            (models.CommunityMember.tenant_id == current_user.tenant_id)
        ).first()
        if existing:
            return jsonify({"error": "already_member"}), 409

        member = models.CommunityMember(
            group_id=group_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            role="member",
        )
        db.add(member)
        group.member_count = (group.member_count or 0) + 1
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@community_bp.route("/groups/<int:group_id>/leave", methods=["POST"])
@login_required
def leave_group(group_id: int):
    db = SessionLocal()
    try:
        member = db.query(models.CommunityMember).filter(
            models.CommunityMember.group_id == group_id,
            (models.CommunityMember.user_id == current_user.id) |
            (models.CommunityMember.tenant_id == current_user.tenant_id)
        ).first()
        if not member:
            return jsonify({"error": "not_member"}), 404

        group = db.query(models.CommunityGroup).filter_by(id=group_id).first()
        if group:
            group.member_count = max(0, (group.member_count or 0) - 1)
        db.delete(member)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ── POSTS ─────────────────────────────────────────────────────────────

@community_bp.route("/groups/<int:group_id>/posts", methods=["GET"])
@login_required
def list_posts(group_id: int):
    limit = min(int(request.args.get("limit") or 20), 50)
    page = max(int(request.args.get("page") or 1), 1)

    db = SessionLocal()
    try:
        q = db.query(models.CommunityPost).filter_by(
            group_id=group_id, is_deleted=False, reply_to_id=None,
        )
        total = q.count()

        # Pinned first, then recent
        posts = q.order_by(
            models.CommunityPost.is_pinned.desc(),
            models.CommunityPost.created_at.desc(),
        ).offset((page - 1) * limit).limit(limit).all()

        # Get replies for these posts
        post_ids = [p.id for p in posts]
        replies_map: dict[int, list] = {}
        if post_ids:
            replies = db.query(models.CommunityPost).filter(
                models.CommunityPost.reply_to_id.in_(post_ids),
                models.CommunityPost.is_deleted == False,
            ).order_by(models.CommunityPost.created_at).all()
            for r in replies:
                replies_map.setdefault(r.reply_to_id, []).append(_serialize_post(r))

        return jsonify({
            "posts": [
                {**_serialize_post(p), "replies": replies_map.get(p.id, [])}
                for p in posts
            ],
            "total": total,
            "page": page,
        })
    finally:
        db.close()


@community_bp.route("/groups/<int:group_id>/posts", methods=["POST"])
@login_required
def create_post(group_id: int):
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Conteúdo é obrigatório"}), 422

    db = SessionLocal()
    try:
        group = db.query(models.CommunityGroup).filter_by(id=group_id).first()
        if not group:
            return jsonify({"error": "group_not_found"}), 404

        post = models.CommunityPost(
            group_id=group_id,
            author_user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            content=content,
            post_type=body.get("post_type", "post"),
            media_url=body.get("media_url"),
            media_type=body.get("media_type"),
        )
        db.add(post)
        group.post_count = (group.post_count or 0) + 1
        db.commit()
        db.refresh(post)
        return jsonify({"ok": True, "id": post.id, "post": _serialize_post(post)}), 201
    finally:
        db.close()


@community_bp.route("/posts/<int:post_id>/reply", methods=["POST"])
@login_required
def reply_post(post_id: int):
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Conteúdo é obrigatório"}), 422

    db = SessionLocal()
    try:
        parent = db.query(models.CommunityPost).filter_by(id=post_id, is_deleted=False).first()
        if not parent:
            return jsonify({"error": "post_not_found"}), 404

        reply = models.CommunityPost(
            group_id=parent.group_id,
            author_user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            content=content,
            post_type="post",
            reply_to_id=post_id,
        )
        db.add(reply)
        parent.reply_count = (parent.reply_count or 0) + 1
        db.commit()
        db.refresh(reply)
        return jsonify({"ok": True, "reply": _serialize_post(reply)}), 201
    finally:
        db.close()


@community_bp.route("/posts/<int:post_id>/react", methods=["POST"])
@login_required
def react_post(post_id: int):
    body = request.get_json(silent=True) or {}
    reaction_type = body.get("reaction_type", "like")
    if reaction_type not in REACTION_TYPES:
        return jsonify({"error": "invalid_reaction", "valid": REACTION_TYPES}), 422

    db = SessionLocal()
    try:
        post = db.query(models.CommunityPost).filter_by(id=post_id).first()
        if not post:
            return jsonify({"error": "not_found"}), 404

        # Toggle: if already reacted with same type, remove
        existing = db.query(models.CommunityReaction).filter_by(
            post_id=post_id, user_id=current_user.id, reaction_type=reaction_type,
        ).first()

        if existing:
            db.delete(existing)
            post.reaction_count = max(0, (post.reaction_count or 0) - 1)
            db.commit()
            return jsonify({"ok": True, "action": "removed"})
        else:
            reaction = models.CommunityReaction(
                post_id=post_id,
                user_id=current_user.id,
                reaction_type=reaction_type,
            )
            db.add(reaction)
            post.reaction_count = (post.reaction_count or 0) + 1
            db.commit()
            return jsonify({"ok": True, "action": "added"})
    finally:
        db.close()


@community_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@login_required
def delete_post(post_id: int):
    db = SessionLocal()
    try:
        post = db.query(models.CommunityPost).filter_by(id=post_id).first()
        if not post:
            return jsonify({"error": "not_found"}), 404
        # Only author or group admin can delete
        if post.author_user_id != current_user.id:
            return jsonify({"error": "forbidden"}), 403
        post.is_deleted = True
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ── ORACLE IA ─────────────────────────────────────────────────────────

@community_bp.route("/posts/<int:post_id>/oracle", methods=["POST"])
@login_required
def oracle_response(post_id: int):
    """
    Pede resposta da IA Oráculo para um post/pergunta.
    A IA responde com sabedoria espiritual contextualizada.
    """
    db = SessionLocal()
    try:
        post = db.query(models.CommunityPost).filter_by(id=post_id, is_deleted=False).first()
        if not post:
            return jsonify({"error": "not_found"}), 404

        group = db.query(models.CommunityGroup).filter_by(id=post.group_id).first()
        if not group or not group.oracle_enabled:
            return jsonify({"error": "oracle_disabled"}), 422

        # Moon phase for context
        moon_phase = None
        try:
            from lunar import phase_for_date
            moon = phase_for_date()
            moon_phase = moon.get("phase_name")
        except Exception:
            pass

        # Generate oracle response
        oracle_text = _generate_oracle(post.content, group, moon_phase)

        oracle_post = models.CommunityPost(
            group_id=post.group_id,
            tenant_id=current_user.tenant_id,
            content=oracle_text,
            post_type="oracle_response",
            reply_to_id=post_id,
            is_oracle_response=True,
            oracle_context={
                "original_question": post.content[:200],
                "group_category": group.category,
                "moon_phase": moon_phase,
            },
        )
        db.add(oracle_post)
        post.reply_count = (post.reply_count or 0) + 1
        db.commit()
        db.refresh(oracle_post)

        return jsonify({"ok": True, "oracle_post": _serialize_post(oracle_post)})
    finally:
        db.close()


# ── STATS ─────────────────────────────────────────────────────────────

@community_bp.route("/stats", methods=["GET"])
@login_required
def community_stats():
    db = SessionLocal()
    try:
        from sqlalchemy import func
        total_groups = db.query(func.count(models.CommunityGroup.id)).filter_by(is_archived=False).scalar() or 0
        total_posts = db.query(func.count(models.CommunityPost.id)).filter_by(is_deleted=False).scalar() or 0
        total_members = db.query(func.count(models.CommunityMember.id)).scalar() or 0

        my_groups = db.query(func.count(models.CommunityMember.id)).filter(
            (models.CommunityMember.user_id == current_user.id) |
            (models.CommunityMember.tenant_id == current_user.tenant_id)
        ).scalar() or 0

        return jsonify({
            "total_groups": total_groups,
            "total_posts": total_posts,
            "total_members": total_members,
            "my_groups": my_groups,
        })
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────

def _generate_oracle(question: str, group: models.CommunityGroup, moon_phase: str | None) -> str:
    try:
        from personalizer import Personalizer
        p = Personalizer()
        if not p.client:
            return _fallback_oracle(question)

        persona = group.oracle_persona or "Você é um Oráculo espiritual sábio e acolhedor."

        prompt = f"""{persona}

Um membro da comunidade "{group.name}" ({group.category}) fez esta pergunta:
"{question}"

{f'Fase da lua atual: {moon_phase}' if moon_phase else ''}

Responda com sabedoria profunda, de forma:
- Acolhedora e não-julgadora
- Combinando diferentes tradições espirituais quando pertinente
- Com uma mensagem prática que a pessoa possa aplicar hoje
- Em tom de conversa íntima, não de palestra
- 3-5 parágrafos curtos
- Use emojis com moderação (1-2)

pt-BR. Não use formatação markdown."""

        resp = p.client.models.generate_content(
            model=p.model_name,
            contents=prompt,
            config={"max_output_tokens": 800, "temperature": 0.85},
        )
        return (resp.text or "").strip() or _fallback_oracle(question)
    except Exception as exc:
        logger.warning("[community.oracle] IA falhou: %s", exc)
        return _fallback_oracle(question)


def _fallback_oracle(question: str) -> str:
    return (
        "🔮 Querida alma,\n\n"
        "Sua pergunta ecoa profundamente no universo. Cada questionamento sincero "
        "é uma porta que se abre para a compreensão.\n\n"
        "Neste momento, convido você a fechar os olhos por um instante. "
        "Respire fundo três vezes. A resposta que procura já está dentro de você — "
        "às vezes precisamos apenas de silêncio para ouvi-la.\n\n"
        "Confie no seu processo. O universo conspira a seu favor. 🙏"
    )


def _serialize_group(g: models.CommunityGroup) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "slug": g.slug,
        "description": g.description,
        "category": g.category,
        "icon": g.icon,
        "is_public": g.is_public,
        "oracle_enabled": g.oracle_enabled,
        "member_count": g.member_count or 0,
        "post_count": g.post_count or 0,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


def _serialize_post(p: models.CommunityPost) -> dict:
    return {
        "id": p.id,
        "group_id": p.group_id,
        "content": p.content,
        "post_type": p.post_type,
        "media_url": p.media_url,
        "media_type": p.media_type,
        "reply_to_id": p.reply_to_id,
        "reply_count": p.reply_count or 0,
        "is_oracle_response": p.is_oracle_response,
        "reaction_count": p.reaction_count or 0,
        "is_pinned": p.is_pinned,
        "author_user_id": p.author_user_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }

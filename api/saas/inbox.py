"""
Inbox SaaS — lista de conversas + takeover humano.

Endpoints:
    GET  /saas/inbox                       — lista conversas (filtrável)
    GET  /saas/inbox/<lead_id>             — conversa individual
    POST /saas/inbox/<lead_id>/takeover    — toggle bot_pausado (humano assume / libera bot)

Multi-tenant strict: lookup sempre filtra por ``current_user.tenant_id``.
"""

from __future__ import annotations

import logging

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

inbox_bp = Blueprint("saas_inbox", __name__, url_prefix="/saas/inbox")

ALLOWED_FILTERS = ("todos", "ativas", "pausadas", "convertidas", "perdidas")


@inbox_bp.route("/", methods=["GET"])
@login_required
def list_view():
    tenant_id = current_user.tenant_id
    filtro = request.args.get("filtro", "todos").lower()
    if filtro not in ALLOWED_FILTERS:
        filtro = "todos"

    db = SessionLocal()
    try:
        q = db.query(models.Lead).filter_by(tenant_id=tenant_id)
        if filtro == "ativas":
            q = q.filter_by(opt_out=False, bot_pausado=False, convertido=False)
        elif filtro == "pausadas":
            q = q.filter_by(bot_pausado=True)
        elif filtro == "convertidas":
            q = q.filter_by(convertido=True)
        elif filtro == "perdidas":
            q = q.filter_by(opt_out=True)

        leads = q.order_by(models.Lead.atualizado_em.desc()).limit(100).all()

        items = []
        for lead in leads:
            last_msg = db.query(models.Mensagem).filter_by(lead_id=lead.id).order_by(
                models.Mensagem.timestamp.desc()
            ).first()
            items.append({
                "id": lead.id,
                "telefone": lead.telefone,
                "nome": (lead.nome or "(sem nome)")[:40],
                "node_atual": lead.node_atual,
                "convertido": bool(lead.convertido),
                "bot_pausado": bool(lead.bot_pausado),
                "opt_out": bool(lead.opt_out),
                "ultima_msg": (last_msg.texto[:80] + "…") if last_msg and len(last_msg.texto or "") > 80
                              else (last_msg.texto if last_msg else ""),
                "ultima_em": last_msg.timestamp if last_msg else None,
            })

        return render_template(
            "inbox/list.html",
            items=items,
            filtro=filtro,
            filtros_disponiveis=ALLOWED_FILTERS,
            total=len(items),
        )
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>", methods=["GET"])
@login_required
def conversation(lead_id: int):
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            abort(404)
        messages = db.query(models.Mensagem).filter_by(lead_id=lead_id).order_by(
            models.Mensagem.timestamp.asc()
        ).limit(200).all()
        return render_template(
            "inbox/conversation.html",
            lead=lead,
            messages=messages,
        )
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/takeover", methods=["POST"])
@login_required
def takeover(lead_id: int):
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            abort(404)
        lead.bot_pausado = not lead.bot_pausado  # toggle
        db.commit()
        action = "pausado" if lead.bot_pausado else "liberado"
        flash(f"Bot {action} pra {lead.telefone}", "success")
        logger.info(
            "[inbox] takeover toggle tenant=%s lead=%s bot_pausado=%s",
            tenant_id, lead_id, lead.bot_pausado,
        )
    finally:
        db.close()
    return redirect(url_for("saas_inbox.conversation", lead_id=lead_id))

# --- JSON API Endpoints for React Frontend ---

from flask import jsonify

@inbox_bp.route("/data", methods=["GET"])
@login_required
def list_view_data():
    """
    Lista leads com filtros + score band + last message preview.

    Query params:
        ?filtro=todos|ativas|pausadas|convertidas|perdidas
        &score_band=hot|warm|cold     (multi via vírgula: hot,warm)
        &search=string                 (telefone ou nome)
        &sort=score|recency|name       (default: recency)
        &limit=100
    """
    tenant_id = current_user.tenant_id
    filtro = request.args.get("filtro", "todos").lower()
    if filtro not in ALLOWED_FILTERS:
        filtro = "todos"
    search = (request.args.get("search") or "").strip()
    band_filter = (request.args.get("score_band") or "").strip()
    sort = request.args.get("sort", "recency")
    limit = min(int(request.args.get("limit") or 100), 500)

    db = SessionLocal()
    try:
        q = db.query(models.Lead).filter_by(tenant_id=tenant_id)
        if filtro == "ativas":
            q = q.filter_by(opt_out=False, bot_pausado=False, convertido=False)
        elif filtro == "pausadas":
            q = q.filter_by(bot_pausado=True)
        elif filtro == "convertidas":
            q = q.filter_by(convertido=True)
        elif filtro == "perdidas":
            q = q.filter_by(opt_out=True)

        if band_filter:
            bands = [b.strip() for b in band_filter.split(",") if b.strip()]
            if bands:
                q = q.filter(models.Lead.score_band.in_(bands))

        if search:
            like = f"%{search.lower()}%"
            q = q.filter(or_(
                models.Lead.telefone.like(like),
                models.Lead.nome.ilike(like),
            ))

        if sort == "score":
            q = q.order_by(models.Lead.score_value.desc(), models.Lead.atualizado_em.desc())
        elif sort == "name":
            q = q.order_by(models.Lead.nome.asc())
        else:  # recency default
            q = q.order_by(models.Lead.atualizado_em.desc())

        leads = q.limit(limit).all()
        items = []
        for lead in leads:
            last_msg = db.query(models.Mensagem).filter_by(lead_id=lead.id).order_by(
                models.Mensagem.timestamp.desc()
            ).first()
            items.append({
                "id": lead.id,
                "telefone": lead.telefone,
                "nome": lead.nome or "",
                "node_atual": lead.node_atual,
                "convertido": bool(lead.convertido),
                "bot_pausado": bool(lead.bot_pausado),
                "opt_out": bool(lead.opt_out),
                "score_value": lead.score_value or 0,
                "score_band": lead.score_band or "cold",
                "tags": lead.tags or [],
                "ultima_msg": last_msg.texto if last_msg else "",
                "ultima_em": last_msg.timestamp.isoformat() if last_msg and last_msg.timestamp else None,
                "ultima_remetente": last_msg.remetente if last_msg else None,
            })
        return jsonify({
            "items": items, "filtro": filtro, "total": len(items),
            "sort": sort, "score_band": band_filter or None,
        })
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/score/refresh", methods=["POST"])
@login_required
def refresh_lead_score(lead_id: int):
    """Força recompute do score (Frente 3.24). Chamável pelo frontend."""
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404
        try:
            import lead_scoring
            lead_scoring.update_lead_score(lead_id, db_session=db)
            db.refresh(lead)
            return jsonify({
                "ok": True,
                "score_value": lead.score_value,
                "score_band": lead.score_band,
                "components": lead.score_components,
            })
        except Exception as exc:
            return jsonify({"error": "compute_failed", "details": str(exc)[:200]}), 500
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/data", methods=["GET"])
@login_required
def conversation_data(lead_id: int):
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({"error": "Not found"}), 404
            
        messages = db.query(models.Mensagem).filter_by(lead_id=lead_id).order_by(
            models.Mensagem.timestamp.asc()
        ).limit(200).all()
        
        msgs_data = []
        for m in messages:
            msgs_data.append({
                "id": m.id,
                "texto": m.texto,
                "origem": m.origem,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "media_url": m.media_url,
                "media_type": m.media_type
            })
            
        return jsonify({
            "lead": {
                "id": lead.id,
                "telefone": lead.telefone,
                "nome": lead.nome or "",
                "bot_pausado": bool(lead.bot_pausado),
                "node_atual": lead.node_atual
            },
            "messages": msgs_data
        })
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/takeover/data", methods=["POST"])
@login_required
def takeover_data(lead_id: int):
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({"error": "Not found"}), 404
        lead.bot_pausado = not lead.bot_pausado
        db.commit()
        return jsonify({"status": "ok", "bot_pausado": lead.bot_pausado})
    finally:
        db.close()

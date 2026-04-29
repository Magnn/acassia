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

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

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

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
from sqlalchemy import case, or_, func, desc

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
        lead_ids = [l.id for l in leads]
        last_msgs_map = {}
        if lead_ids:
            subq = (
                db.query(
                    models.Mensagem.lead_id,
                    func.max(models.Mensagem.id).label("max_msg_id")
                )
                .filter(models.Mensagem.lead_id.in_(lead_ids))
                .group_by(models.Mensagem.lead_id)
                .subquery()
            )
            for m in db.query(models.Mensagem).join(subq, models.Mensagem.id == subq.c.max_msg_id).all():
                last_msgs_map[m.lead_id] = m

        items = []
        for lead in leads:
            last_msg = last_msgs_map.get(lead.id)
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
        &score_band=hot|warm|cold              (multi via vírgula: hot,warm)
        &spiritual_category=amor|dinheiro|...  (multi via vírgula)
        &search=string                          (telefone ou nome)
        &sort=score|recency|name                (default: recency)
        &limit=100
    """
    tenant_id = current_user.tenant_id
    filtro = request.args.get("filtro", "todos").lower()
    if filtro not in ALLOWED_FILTERS:
        filtro = "todos"
    search = (request.args.get("search") or "").strip()
    band_filter = (request.args.get("score_band") or "").strip()
    spiritual_filter = (request.args.get("spiritual_category") or "").strip()
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

        if spiritual_filter:
            cats = [c.strip().lower() for c in spiritual_filter.split(",") if c.strip()]
            if cats:
                q = q.filter(models.Lead.spiritual_category.in_(cats))

        if search:
            like = f"%{search.lower()}%"
            q = q.filter(or_(
                models.Lead.telefone.like(like),
                models.Lead.nome.ilike(like),
            ))

        # Build sort column
        if sort == "score":
            sort_col = models.Lead.score_value.desc()
        elif sort == "name":
            sort_col = models.Lead.nome.asc()
        else:  # recency default
            sort_col = models.Lead.atualizado_em.desc()

        # Urgent-first: leads urgentes sempre flutuam pro topo, independente do sort
        urgent_first = case((models.Lead.is_urgent == True, 0), else_=1)  # noqa: E712
        q = q.order_by(urgent_first, sort_col)

        leads = q.limit(limit).all()
        lead_ids = [l.id for l in leads]
        
        # Batch-fetch últimas mensagens para eliminar o gargalo N+1
        last_msgs_map = {}
        if lead_ids:
            # Subquery buscando o max timestamp de cada lead retornado
            subq = (
                db.query(
                    models.Mensagem.lead_id,
                    func.max(models.Mensagem.id).label("max_msg_id")
                )
                .filter(models.Mensagem.lead_id.in_(lead_ids))
                .group_by(models.Mensagem.lead_id)
                .subquery()
            )
            # Busca mensagens completas dos IDs máximos em uma única query
            msgs = (
                db.query(models.Mensagem)
                .join(subq, models.Mensagem.id == subq.c.max_msg_id)
                .all()
            )
            for m in msgs:
                last_msgs_map[m.lead_id] = m

        items = []
        for lead in leads:
            last_msg = last_msgs_map.get(lead.id)
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
                "spiritual_category": lead.spiritual_category,
                "spiritual_urgency": (lead.spiritual_intent or {}).get("urgency") if lead.spiritual_intent else None,
                "ultima_msg": last_msg.texto if last_msg else "",
                "ultima_em": last_msg.timestamp.isoformat() if last_msg and last_msg.timestamp else None,
                "ultima_remetente": last_msg.remetente if last_msg else None,
                "is_urgent": bool(getattr(lead, "is_urgent", False)),
                "urgent_reason": getattr(lead, "urgent_reason", None),
                "urgent_at": lead.urgent_at.isoformat() if getattr(lead, "urgent_at", None) else None,
                "ultimo_sentimento": getattr(lead, "ultimo_sentimento", None),
                "metadata_json": lead.metadata_json or {},
                "is_starred": bool((lead.metadata_json or {}).get("is_starred", False)),
                "is_archived": bool((lead.metadata_json or {}).get("is_archived", False)),
                "is_blocked": bool((lead.metadata_json or {}).get("is_blocked", False)),
            })
        return jsonify({
            "items": items, "filtro": filtro, "total": len(items),
            "sort": sort, "score_band": band_filter or None,
            "spiritual_category": spiritual_filter or None,
        })
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/context", methods=["GET"])
@login_required
def lead_context(lead_id: int):
    """
    Painel de contexto rico do lead (Frente 3.18-3.22).
    Retorna:
        - dados básicos (signo, idade, cidade, custom_fields)
        - jornada no fluxo (nó atual, histórico, tempo)
        - sentimento últimas 10 msgs
        - LTV / histórico compras
        - notas livres (futuro)
        - tarot readings count
    """
    from datetime import datetime, timezone
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        now = datetime.now(timezone.utc)

        # Sentiment últimos 10 user msgs
        last_user_msgs = db.query(models.Mensagem).filter(
            models.Mensagem.lead_id == lead_id,
            models.Mensagem.remetente == "user",
        ).order_by(models.Mensagem.timestamp.desc()).limit(10).all()
        sentiments = []
        pos = 0
        neg = 0
        for m in last_user_msgs:
            s = (m.sentimento or "").lower()
            if "pos" in s:
                pos += 1
                sentiments.append("pos")
            elif "neg" in s:
                neg += 1
                sentiments.append("neg")
            else:
                sentiments.append("neutral")

        # Jornada
        node_historico = lead.node_historico or []
        if not isinstance(node_historico, list):
            node_historico = []
        last_msg = db.query(models.Mensagem).filter_by(lead_id=lead_id).order_by(
            models.Mensagem.timestamp.desc(),
        ).first()
        last_msg_iso = last_msg.timestamp.isoformat() if last_msg and last_msg.timestamp else None

        # Tempo no nó atual (desde última FlowNodeVisit não-fechada)
        time_in_node_s = None
        try:
            last_visit = db.query(models.FlowNodeVisit).filter_by(
                lead_id=lead_id, exited_at=None,
            ).order_by(models.FlowNodeVisit.entered_at.desc()).first()
            if last_visit and last_visit.entered_at:
                entered_aware = last_visit.entered_at
                if entered_aware.tzinfo is None:
                    entered_aware = entered_aware.replace(tzinfo=timezone.utc)
                time_in_node_s = int((now - entered_aware).total_seconds())
        except Exception:
            pass

        # Histórico de pagamentos / LTV
        payments = db.query(models.PaymentEventReceipt).filter_by(
            lead_id=lead_id,
        ).order_by(models.PaymentEventReceipt.processed_at.desc()).all()

        # Total de tarot readings desse lead
        tarot_count = db.query(models.TarotReading).filter_by(
            tenant_id=tenant_id, lead_id=lead_id,
        ).count()

        # Tags
        tags = lead.tags or []
        if not isinstance(tags, list):
            tags = []

        return jsonify({
            "lead": {
                "id": lead.id,
                "telefone": lead.telefone,
                "nome": lead.nome,
                "email": lead.email,
                "signo": getattr(lead, "signo", None),
                "idade": getattr(lead, "idade", None),
                "cidade": getattr(lead, "cidade", None),
                "tags": tags,
                "custom_fields": getattr(lead, "custom_fields", {}) or {},
                "criado_em": lead.criado_em.isoformat() if lead.criado_em else None,
            },
            "score": {
                "value": lead.score_value or 0,
                "band": lead.score_band or "cold",
                "components": lead.score_components or {},
                "updated_at": lead.score_updated_at.isoformat() if lead.score_updated_at else None,
            },
            "journey": {
                "node_atual": lead.node_atual,
                "node_historico": node_historico,
                "depth": len(node_historico),
                "time_in_node_s": time_in_node_s,
                "last_msg_at": last_msg_iso,
                "convertido": bool(lead.convertido),
                "bot_pausado": bool(lead.bot_pausado),
                "opt_out": bool(lead.opt_out),
            },
            "sentiment": {
                "recent": sentiments,
                "positive_count": pos,
                "negative_count": neg,
                "trend": "positive" if pos > neg else ("negative" if neg > pos else "neutral"),
            },
            "commercial": {
                "payments_count": len(payments),
                "payments": [
                    {
                        "id": p.id, "provider": p.provider,
                        "event_type": p.event_type,
                        "processed_at": p.processed_at.isoformat() if p.processed_at else None,
                    } for p in payments[:5]
                ],
            },
            "tarot_readings_count": tarot_count,
            "spiritual": {
                "category": lead.spiritual_category,
                "intent": lead.spiritual_intent,
                "computed_at": lead.spiritual_intent_at.isoformat() if lead.spiritual_intent_at else None,
            },
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
                "origem": getattr(m, "remetente", None),
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "media_url": getattr(m, "media_url", None),
                "media_type": getattr(m, "tipo", None),
                "wamid": getattr(m, "wamid", None),
                "delivery_status": getattr(m, "delivery_status", None),
                "delivery_status_at": (
                    m.delivery_status_at.isoformat()
                    if getattr(m, "delivery_status_at", None) else None
                ),
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
        # Notificar browsers conectados via SSE
        try:
            from api.saas.realtime_hooks import notify_lead_updated
            notify_lead_updated(tenant_id, lead_id, {"bot_pausado": lead.bot_pausado})
        except Exception:
            pass
        return jsonify({"status": "ok", "bot_pausado": lead.bot_pausado})
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/action", methods=["POST"])
@login_required
def lead_context_action(lead_id: int):
    """
    Ações de contexto de atendimento (ChatbotX Live Chat parity):
      - toggle_star: Seguir contato (Follow-up)
      - toggle_archive: Arquivar conversa
      - toggle_block: Bloquear contato (e pausar automações)
      - mark_unread: Marcar conversa como não lida
    """
    tenant_id = current_user.tenant_id
    body = request.get_json(silent=True) or {}
    action = body.get("action")

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({"error": "not_found"}), 404

        meta = dict(lead.metadata_json or {})
        tags = list(lead.tags) if isinstance(lead.tags, list) else []

        if action == "toggle_star":
            is_starred = not meta.get("is_starred", False)
            meta["is_starred"] = is_starred
            if is_starred and "followup" not in tags:
                tags.append("followup")
            elif not is_starred and "followup" in tags:
                tags = [t for t in tags if t != "followup"]
        elif action == "toggle_archive":
            is_archived = not meta.get("is_archived", False)
            meta["is_archived"] = is_archived
            if is_archived and "arquivado" not in tags:
                tags.append("arquivado")
            elif not is_archived and "arquivado" in tags:
                tags = [t for t in tags if t != "arquivado"]
        elif action == "toggle_block":
            is_blocked = not meta.get("is_blocked", False)
            meta["is_blocked"] = is_blocked
            lead.bot_pausado = is_blocked or lead.bot_pausado
            if is_blocked and "bloqueado" not in tags:
                tags.append("bloqueado")
            elif not is_blocked and "bloqueado" in tags:
                tags = [t for t in tags if t != "bloqueado"]
        elif action == "mark_unread":
            meta["unread_manual"] = True

        lead.metadata_json = meta
        lead.tags = tags
        db.commit()

        try:
            from api.saas.realtime_hooks import notify_lead_updated
            notify_lead_updated(tenant_id, lead_id, {
                "metadata_json": meta,
                "tags": tags,
                "bot_pausado": lead.bot_pausado
            })
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "lead_id": lead_id,
            "is_starred": bool(meta.get("is_starred")),
            "is_archived": bool(meta.get("is_archived")),
            "is_blocked": bool(meta.get("is_blocked")),
            "tags": tags,
            "bot_pausado": lead.bot_pausado,
        })
    finally:
        db.close()


@inbox_bp.route("/tags", methods=["GET"])
@login_required
def get_tenant_tags():
    """Retorna lista de todas as tags únicas usadas no tenant para autocomplete."""
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        leads = db.query(models.Lead.tags).filter_by(tenant_id=tenant_id).filter(models.Lead.tags.isnot(None)).all()
        tag_set = set()
        for (t_list,) in leads:
            if isinstance(t_list, list):
                for t in t_list:
                    clean = str(t).strip().lower()
                    if clean:
                        tag_set.add(clean)
        return jsonify({"tags": sorted(list(tag_set))})
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/tags", methods=["POST"])
@login_required
def add_lead_tag(lead_id: int):
    """Adiciona uma ou mais tags ao lead."""
    tenant_id = current_user.tenant_id
    body = request.get_json(silent=True) or {}
    new_tag = body.get("tag")
    new_tags = body.get("tags")

    tags_to_add = []
    if new_tag and isinstance(new_tag, str):
        tags_to_add.append(new_tag.strip().lower())
    if new_tags and isinstance(new_tags, list):
        for t in new_tags:
            if isinstance(t, str) and t.strip():
                tags_to_add.append(t.strip().lower())

    if not tags_to_add:
        return jsonify({"error": "missing_tag"}), 400

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({"error": "not_found"}), 404

        current_tags = list(lead.tags) if isinstance(lead.tags, list) else []
        modified = False
        for t in tags_to_add:
            if t not in current_tags:
                current_tags.append(t)
                modified = True

        if modified:
            lead.tags = current_tags
            db.commit()
            try:
                from api.saas.realtime_hooks import notify_lead_updated
                notify_lead_updated(tenant_id, lead_id, {"tags": current_tags})
            except Exception:
                pass

        return jsonify({"ok": True, "tags": current_tags})
    finally:
        db.close()


@inbox_bp.route("/<int:lead_id>/tags/<path:tag_name>", methods=["DELETE"])
@login_required
def remove_lead_tag(lead_id: int, tag_name: str):
    """Remove uma tag do lead."""
    tenant_id = current_user.tenant_id
    target = tag_name.strip().lower()

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({"error": "not_found"}), 404

        current_tags = list(lead.tags) if isinstance(lead.tags, list) else []
        new_tags = [t for t in current_tags if t.strip().lower() != target]

        if len(new_tags) != len(current_tags):
            lead.tags = new_tags
            db.commit()
            try:
                from api.saas.realtime_hooks import notify_lead_updated
                notify_lead_updated(tenant_id, lead_id, {"tags": new_tags})
            except Exception:
                pass

        return jsonify({"ok": True, "tags": new_tags})
    finally:
        db.close()


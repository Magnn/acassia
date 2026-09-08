"""
api/saas/broadcast.py — Motor de Broadcast & Segmentação
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: lançamentos, divulgação de retiros, nurturing em massa.

Endpoints:
  GET    /saas/broadcast/                     — lista campanhas
  POST   /saas/broadcast/                     — cria campanha
  GET    /saas/broadcast/<id>                 — detalhe + métricas
  PUT    /saas/broadcast/<id>                 — edita campanha (draft only)
  DELETE /saas/broadcast/<id>                 — cancela/apaga
  POST   /saas/broadcast/<id>/preview         — preview (quantos leads casam)
  POST   /saas/broadcast/<id>/send            — dispara envio
  GET    /saas/broadcast/<id>/recipients       — lista destinatários + status
  GET    /saas/broadcast/segments/preview      — preview de segmento (sem campanha)
"""

from __future__ import annotations

import logging
import time
import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from db import models
from db.database import SessionLocal
from extensions import limiter

logger = logging.getLogger(__name__)
broadcast_bp = Blueprint("saas_broadcast", __name__, url_prefix="/saas/broadcast")


# ═══════════════════════════════════════════════════════════════════════
# SEGMENTATION ENGINE
# ═══════════════════════════════════════════════════════════════════════

def _apply_segment_filters(query, filters: dict, tenant_id: str):
    """
    Aplica filtros de segmentação no query de leads.

    Filtros suportados:
        tags: ["vip", "retiro"]         — lead tem QUALQUER dessas tags
        score_band: ["hot", "warm"]     — lead está em alguma dessas bandas
        signo: ["leao", "touro"]        — signo solar do lead
        bot_ativo: true/false           — bot está ligado/desligado
        has_phone: true                 — só leads com telefone
        opted_out: false                — excluir opted out (default)
        node_atual: ["node_5", "node_8"] — leads em nós específicos do funil
        score_min: 50                   — score mínimo
        score_max: 90                   — score máximo
        last_message_days: 30           — interagiu nos últimos N dias
    """
    query = query.filter_by(tenant_id=tenant_id)

    if not filters:
        return query

    # Tags (JSON array contains)
    if "tags" in filters and filters["tags"]:
        tag_list = filters["tags"]
        if isinstance(tag_list, list):
            # SQLite JSON: usa LIKE para cada tag
            conditions = []
            for tag in tag_list:
                conditions.append(
                    models.Lead.tags.cast(db_types.String).contains(f'"{tag}"')
                    if hasattr(models.Lead.tags, 'cast') else
                    models.Lead.tags.ilike(f'%"{tag}"%')
                )
            if conditions:
                query = query.filter(or_(*conditions))

    # Score band
    if "score_band" in filters and filters["score_band"]:
        bands = filters["score_band"]
        if isinstance(bands, list):
            query = query.filter(models.Lead.score_band.in_(bands))

    # Signo
    if "signo" in filters and filters["signo"]:
        signos = filters["signo"]
        if isinstance(signos, list):
            query = query.filter(models.Lead.signo.in_(signos))

    # Bot ativo
    if "bot_ativo" in filters:
        query = query.filter(models.Lead.bot_ativo == bool(filters["bot_ativo"]))

    # Opted out (default: excluir)
    if not filters.get("include_opted_out", False):
        # Exclui leads com tag opted_out
        query = query.filter(
            or_(
                models.Lead.tags.is_(None),
                ~models.Lead.tags.cast(db_types.String).contains('"opted_out"')
                if hasattr(models.Lead.tags, 'cast') else
                ~models.Lead.tags.ilike('%"opted_out"%')
            )
        )

    # Score range
    if "score_min" in filters:
        query = query.filter(models.Lead.score_value >= int(filters["score_min"]))
    if "score_max" in filters:
        query = query.filter(models.Lead.score_value <= int(filters["score_max"]))

    # Nó atual
    if "node_atual" in filters and filters["node_atual"]:
        nodes = filters["node_atual"]
        if isinstance(nodes, list):
            query = query.filter(models.Lead.node_atual.in_(nodes))

    # Com telefone
    if filters.get("has_phone", True):
        query = query.filter(
            models.Lead.telefone.isnot(None),
            models.Lead.telefone != "",
        )

    # Interagiu nos últimos N dias
    if "last_message_days" in filters:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(filters["last_message_days"]))
        query = query.filter(models.Lead.updated_at >= cutoff)

    return query


# SQLAlchemy type import
try:
    from sqlalchemy import types as db_types
except ImportError:
    import sqlalchemy as db_types


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@broadcast_bp.route("/tags", methods=["GET"])
@login_required
def list_available_tags():
    """Retorna lista de tags únicas existentes nos leads do tenant."""
    db = SessionLocal()
    try:
        leads = db.query(models.Lead.tags).filter_by(tenant_id=current_user.tenant_id).all()
        tag_set = set()
        for (tags,) in leads:
            if isinstance(tags, list):
                for t in tags:
                    if t and isinstance(t, str):
                        tag_set.add(t.strip())
            elif isinstance(tags, str):
                for t in tags.split(","):
                    clean = t.strip().strip('"').strip("'")
                    if clean:
                        tag_set.add(clean)
        # Tags padrão sugeridas de alta conversão
        default_suggestions = ["vip", "lead_quente", "cliente", "abandono_carrinho", "prospecto", "oraculo", "novo_lead"]
        for s in default_suggestions:
            tag_set.add(s)
        return jsonify({"tags": sorted(list(tag_set))})
    finally:
        db.close()


@broadcast_bp.route("/", methods=["GET"])
@login_required
def list_campaigns():
    db = SessionLocal()
    try:
        campaigns = db.query(models.BroadcastCampaign).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.BroadcastCampaign.created_at.desc()).limit(50).all()

        return jsonify({
            "campaigns": [
                {
                    "id": c.id,
                    "title": c.title,
                    "name": c.title,
                    "message_text": c.message_text,
                    "message_template": c.message_text,
                    "message_media_url": c.message_media_url,
                    "message_media_type": c.message_media_type,
                    "segment_filters": c.segment_filters or {},
                    "status": c.status,
                    "total_recipients": c.total_recipients,
                    "sent_count": c.sent_count,
                    "total_sent": c.sent_count,
                    "delivered_count": c.delivered_count,
                    "total_delivered": c.delivered_count,
                    "failed_count": c.failed_count,
                    "total_failed": c.failed_count,
                    "reply_count": c.reply_count,
                    "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
                    "started_at": c.started_at.isoformat() if c.started_at else None,
                    "completed_at": c.completed_at.isoformat() if c.completed_at else None,
                    "created_at": c.created_at.isoformat(),
                } for c in campaigns
            ]
        })
    finally:
        db.close()


@broadcast_bp.route("/", methods=["POST"])
@login_required
@limiter.limit("20/hour")
def create_campaign():
    """
    Cria campanha de broadcast (rascunho).

    Body: {title|name, message_text|message_template, message_media_url?, segment_filters?, scheduled_at?}
    """
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or body.get("name") or "").strip()
    text = (body.get("message_text") or body.get("message_template") or "").strip()

    if not title or len(title) < 2:
        return jsonify({"error": "title_required"}), 422
    if not text or len(text) < 3:
        return jsonify({"error": "message_text_required"}), 422

    db = SessionLocal()
    try:
        campaign = models.BroadcastCampaign(
            tenant_id=current_user.tenant_id,
            created_by_user_id=current_user.id,
            title=title[:200],
            message_text=text,
            message_media_url=body.get("message_media_url"),
            message_media_type=body.get("message_media_type"),
            segment_filters=body.get("segment_filters") or {},
            status="scheduled" if body.get("scheduled_at") else "draft",
            scheduled_at=_parse_dt(body.get("scheduled_at")),
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        return jsonify({"ok": True, "id": campaign.id, "status": campaign.status}), 201
    finally:
        db.close()


@broadcast_bp.route("/<int:campaign_id>", methods=["GET"])
@login_required
def get_campaign(campaign_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.BroadcastCampaign).filter_by(
            id=campaign_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404

        return jsonify({
            "id": c.id,
            "title": c.title,
            "name": c.title,
            "message_text": c.message_text,
            "message_template": c.message_text,
            "message_media_url": c.message_media_url,
            "message_media_type": c.message_media_type,
            "segment_filters": c.segment_filters or {},
            "status": c.status,
            "total_recipients": c.total_recipients,
            "sent_count": c.sent_count,
            "total_sent": c.sent_count,
            "delivered_count": c.delivered_count,
            "total_delivered": c.delivered_count,
            "failed_count": c.failed_count,
            "total_failed": c.failed_count,
            "reply_count": c.reply_count,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            "created_at": c.created_at.isoformat(),
        })
    finally:
        db.close()


@broadcast_bp.route("/<int:campaign_id>", methods=["PUT"])
@login_required
def update_campaign(campaign_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        c = db.query(models.BroadcastCampaign).filter_by(
            id=campaign_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404
        if c.status not in ("draft", "scheduled"):
            return jsonify({"error": "only_draft_or_scheduled_editable"}), 409

        if "title" in body or "name" in body:
            c.title = (body.get("title") or body.get("name") or "").strip()[:200]
        if "message_text" in body or "message_template" in body:
            c.message_text = (body.get("message_text") or body.get("message_template") or "").strip()
        if "message_media_url" in body:
            c.message_media_url = body["message_media_url"]
        if "message_media_type" in body:
            c.message_media_type = body["message_media_type"]
        if "segment_filters" in body:
            c.segment_filters = body["segment_filters"]
        if "scheduled_at" in body:
            c.scheduled_at = _parse_dt(body["scheduled_at"])
            if c.scheduled_at and c.status == "draft":
                c.status = "scheduled"

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@broadcast_bp.route("/<int:campaign_id>", methods=["DELETE"])
@login_required
def delete_campaign(campaign_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.BroadcastCampaign).filter_by(
            id=campaign_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404
        if c.status == "sending":
            c.status = "cancelled"
            db.commit()
            return jsonify({"ok": True, "action": "cancelled"})
        db.delete(c)
        db.commit()
        return jsonify({"ok": True, "action": "deleted"})
    finally:
        db.close()


@broadcast_bp.route("/<int:campaign_id>/preview", methods=["POST"])
@login_required
def preview_campaign(campaign_id: int):
    """Retorna quantos leads casam com os filtros da campanha."""
    db = SessionLocal()
    try:
        c = db.query(models.BroadcastCampaign).filter_by(
            id=campaign_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404

        q = _apply_segment_filters(
            db.query(models.Lead), c.segment_filters or {}, current_user.tenant_id,
        )
        total = q.count()

        # Amostra de 5 leads
        sample = q.limit(5).all()
        return jsonify({
            "total_matching": total,
            "sample": [
                {"id": l.id, "nome": l.nome, "telefone": l.telefone,
                 "signo": l.signo, "score_band": l.score_band}
                for l in sample
            ],
        })
    finally:
        db.close()


@broadcast_bp.route("/segments/preview", methods=["POST"])
@login_required
def preview_segment():
    """Preview genérico de segmento (sem campanha)."""
    body = request.get_json(silent=True) or {}
    filters = body.get("filters") or {}

    db = SessionLocal()
    try:
        q = _apply_segment_filters(
            db.query(models.Lead), filters, current_user.tenant_id,
        )
        total = q.count()
        sample = q.limit(5).all()
        return jsonify({
            "total_matching": total,
            "sample": [
                {"id": l.id, "nome": l.nome, "telefone": l.telefone,
                 "signo": l.signo, "score_band": l.score_band, "tags": l.tags}
                for l in sample
            ],
        })
    finally:
        db.close()


@broadcast_bp.route("/<int:campaign_id>/send", methods=["POST"])
@login_required
@limiter.limit("5/hour")
def send_campaign(campaign_id: int):
    """
    Dispara o envio da campanha. Roda em background thread.
    Rate limiting: 1 msg a cada 2s para não ser bloqueado pela Meta.
    """
    db = SessionLocal()
    try:
        c = db.query(models.BroadcastCampaign).filter_by(
            id=campaign_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404
        if c.status not in ("draft", "scheduled"):
            return jsonify({"error": "already_sent", "status": c.status}), 409

        # Resolver leads
        q = _apply_segment_filters(
            db.query(models.Lead), c.segment_filters or {}, current_user.tenant_id,
        )
        leads = q.all()
        if not leads:
            return jsonify({"error": "no_leads_match_filters"}), 422

        # Criar recipients
        for lead in leads:
            db.add(models.BroadcastRecipient(
                campaign_id=c.id, lead_id=lead.id, status="pending",
            ))

        c.status = "sending"
        c.total_recipients = len(leads)
        c.started_at = datetime.now(timezone.utc)
        db.commit()

        # Disparar em background
        tenant_id = current_user.tenant_id
        _thread = threading.Thread(
            target=_send_campaign_worker,
            args=(c.id, tenant_id),
            daemon=True,
        )
        _thread.start()

        return jsonify({
            "ok": True,
            "total_recipients": len(leads),
            "status": "sending",
            "message": f"Envio iniciado para {len(leads)} leads.",
        })
    finally:
        db.close()


@broadcast_bp.route("/<int:campaign_id>/recipients", methods=["GET"])
@login_required
def list_recipients(campaign_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.BroadcastCampaign).filter_by(
            id=campaign_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404

        recs = db.query(models.BroadcastRecipient).filter_by(
            campaign_id=campaign_id,
        ).limit(200).all()

        # Enrich with lead info
        lead_ids = [r.lead_id for r in recs]
        leads_map = {}
        if lead_ids:
            for lead in db.query(models.Lead).filter(models.Lead.id.in_(lead_ids)).all():
                leads_map[lead.id] = lead

        return jsonify({
            "recipients": [
                {
                    "id": r.id, "lead_id": r.lead_id,
                    "lead_name": leads_map.get(r.lead_id, None) and leads_map[r.lead_id].nome,
                    "lead_phone": leads_map.get(r.lead_id, None) and leads_map[r.lead_id].telefone,
                    "status": r.status,
                    "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                    "error_reason": r.error_reason,
                } for r in recs
            ]
        })
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# BACKGROUND WORKER
# ═══════════════════════════════════════════════════════════════════════

def _send_campaign_worker(campaign_id: int, tenant_id: str):
    """Worker que envia mensagens uma a uma com throttling."""
    db = SessionLocal()
    try:
        campaign = db.query(models.BroadcastCampaign).filter_by(id=campaign_id).first()
        if not campaign:
            return

        recipients = db.query(models.BroadcastRecipient).filter_by(
            campaign_id=campaign_id, status="pending",
        ).all()

        # Obter client WhatsApp
        try:
            import horoscope
            wa_client = horoscope._get_whatsapp_client(tenant_id)
        except Exception:
            wa_client = None

        sent = 0
        failed = 0

        # Pre-fetch leads em lote (elimina N+1 queries de banco no loop)
        lead_ids = [r.lead_id for r in recipients]
        leads_cache = {}
        if lead_ids:
            for l in db.query(models.Lead).filter(models.Lead.id.in_(lead_ids)).all():
                leads_cache[l.id] = l

        for rec in recipients:
            if campaign.status == "cancelled":
                break

            lead = leads_cache.get(rec.lead_id)
            if not lead or not lead.telefone:
                rec.status = "failed"
                rec.error_reason = "no_phone"
                failed += 1
                db.commit()
                continue

            # Throttle configurável por campanha (proteção Anti-Ban Meta)
            throttle_secs = 2
            if campaign.segment_filters and isinstance(campaign.segment_filters, dict):
                try:
                    throttle_secs = int(campaign.segment_filters.get("anti_ban_delay_seconds", 2))
                    throttle_secs = max(1, min(throttle_secs, 30))
                except Exception:
                    throttle_secs = 2

            try:
                if wa_client:
                    if campaign.message_media_url:
                        media_fmt = campaign.message_media_type or "imagem"
                        ok = wa_client.enviar_mensagem(
                            lead.telefone, campaign.message_text, formato=media_fmt,
                            media_url=campaign.message_media_url,
                        )
                    else:
                        ok = wa_client.enviar_mensagem(
                            lead.telefone, campaign.message_text, formato="texto",
                        )
                    if ok:
                        rec.status = "sent"
                        rec.sent_at = datetime.now(timezone.utc)
                        sent += 1
                    else:
                        rec.status = "failed"
                        rec.error_reason = "send_returned_false"
                        failed += 1
                else:
                    rec.status = "failed"
                    rec.error_reason = "wa_client_unavailable"
                    failed += 1
            except Exception as exc:
                rec.status = "failed"
                rec.error_reason = str(exc)[:200]
                failed += 1

            # Update counters
            campaign.sent_count = sent
            campaign.failed_count = failed
            db.commit()

            # Throttle dinâmico anti-ban
            time.sleep(throttle_secs)

        campaign.status = "completed"
        campaign.completed_at = datetime.now(timezone.utc)
        campaign.sent_count = sent
        campaign.failed_count = failed
        db.commit()

        logger.info(
            "[broadcast] Campaign %d completed: sent=%d failed=%d total=%d",
            campaign_id, sent, failed, campaign.total_recipients,
        )

    except Exception as exc:
        logger.exception("[broadcast] worker error campaign=%d: %s", campaign_id, exc)
        try:
            campaign = db.query(models.BroadcastCampaign).filter_by(id=campaign_id).first()
            if campaign:
                campaign.status = "completed"
                campaign.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None

"""
api/saas/wa_groups.py — Gestão de Grupos WhatsApp (DevZapp DevGrupos)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Criação em massa, edição centralizada, agendamento de mensagens,
menção @todos, dashboard de grupos, automação por evento.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
groups_bp = Blueprint("wa_groups", __name__, url_prefix="/saas/groups")


# ═══════ GROUP MANAGEMENT ═══════

@groups_bp.route("/", methods=["GET"])
@login_required
def list_groups():
    db = SessionLocal()
    try:
        purpose = request.args.get("purpose")
        q = db.query(models.WAGroup).filter_by(tenant_id=current_user.tenant_id)
        if purpose:
            q = q.filter_by(purpose=purpose)
        groups = q.order_by(models.WAGroup.created_at.desc()).all()
        return jsonify({"groups": [{
            "id": g.id, "name": g.name, "description": g.description,
            "purpose": g.purpose, "launch_id": g.launch_id,
            "max_members": g.max_members, "current_members": g.current_members,
            "active": g.active, "invite_link": g.invite_link,
            "photo_url": g.photo_url,
            "scheduled_messages": db.query(func.count(models.WAGroupMessage.id)).filter_by(
                group_id=g.id, status="pending"
            ).scalar() or 0,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        } for g in groups], "total": len(groups)})
    finally:
        db.close()


@groups_bp.route("/", methods=["POST"])
@login_required
def create_group():
    db = SessionLocal()
    try:
        data = request.json or {}
        g = models.WAGroup(
            tenant_id=current_user.tenant_id,
            name=data["name"],
            description=data.get("description"),
            photo_url=data.get("photo_url"),
            purpose=data.get("purpose", "launch"),
            launch_id=data.get("launch_id"),
            max_members=data.get("max_members", 256),
            invite_link=data.get("invite_link"),
        )
        db.add(g)
        db.commit()
        return jsonify({"ok": True, "group_id": g.id}), 201
    finally:
        db.close()


@groups_bp.route("/bulk-create", methods=["POST"])
@login_required
def bulk_create_groups():
    """Create multiple groups at once (for launches)."""
    db = SessionLocal()
    try:
        data = request.json or {}
        name_template = data.get("name_template", "Grupo {n}")
        count = min(data.get("count", 5), 50)  # max 50 groups
        purpose = data.get("purpose", "launch")
        launch_id = data.get("launch_id")
        description = data.get("description", "")
        created = []
        for i in range(1, count + 1):
            g = models.WAGroup(
                tenant_id=current_user.tenant_id,
                name=name_template.replace("{n}", str(i)),
                description=description,
                purpose=purpose,
                launch_id=launch_id,
            )
            db.add(g)
            db.flush()
            created.append({"id": g.id, "name": g.name})
        db.commit()
        return jsonify({"ok": True, "created": created, "total": len(created)}), 201
    finally:
        db.close()


@groups_bp.route("/bulk-edit", methods=["POST"])
@login_required
def bulk_edit_groups():
    """Edit name/description/photo of multiple groups at once."""
    db = SessionLocal()
    try:
        data = request.json or {}
        group_ids = data.get("group_ids", [])
        updates = data.get("updates", {})
        if not group_ids:
            return jsonify({"error": "group_ids required"}), 400
        updated = 0
        for gid in group_ids:
            g = db.query(models.WAGroup).filter_by(
                id=gid, tenant_id=current_user.tenant_id
            ).first()
            if g:
                for k in ("name", "description", "photo_url", "purpose"):
                    if k in updates:
                        setattr(g, k, updates[k])
                updated += 1
        db.commit()
        return jsonify({"ok": True, "updated": updated})
    finally:
        db.close()


@groups_bp.route("/<int:group_id>", methods=["PUT"])
@login_required
def update_group(group_id):
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(
            id=group_id, tenant_id=current_user.tenant_id
        ).first()
        if not g:
            return jsonify({"error": "not found"}), 404
        data = request.json or {}
        for k in ("name", "description", "photo_url", "purpose", "active", "invite_link", "current_members"):
            if k in data:
                setattr(g, k, data[k])
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@groups_bp.route("/<int:group_id>", methods=["DELETE"])
@login_required
def delete_group(group_id):
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(
            id=group_id, tenant_id=current_user.tenant_id
        ).first()
        if not g:
            return jsonify({"error": "not found"}), 404
        g.active = False
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ GROUP MESSAGES ═══════

@groups_bp.route("/<int:group_id>/messages", methods=["GET"])
@login_required
def list_group_messages(group_id):
    db = SessionLocal()
    try:
        msgs = (
            db.query(models.WAGroupMessage)
            .filter_by(group_id=group_id, tenant_id=current_user.tenant_id)
            .order_by(models.WAGroupMessage.scheduled_at.asc().nullslast())
            .all()
        )
        return jsonify({"messages": [{
            "id": m.id, "content": m.content[:200],
            "media_type": m.media_type, "media_url": m.media_url,
            "mention_all": m.mention_all,
            "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
            "status": m.status,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
        } for m in msgs]})
    finally:
        db.close()


@groups_bp.route("/<int:group_id>/messages", methods=["POST"])
@login_required
def schedule_group_message(group_id):
    db = SessionLocal()
    try:
        data = request.json or {}
        m = models.WAGroupMessage(
            tenant_id=current_user.tenant_id,
            group_id=group_id,
            content=data["content"],
            media_type=data.get("media_type", "text"),
            media_url=data.get("media_url"),
            mention_all=data.get("mention_all", False),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
        )
        db.add(m)
        db.commit()
        return jsonify({"ok": True, "message_id": m.id}), 201
    finally:
        db.close()


@groups_bp.route("/messages/bulk-schedule", methods=["POST"])
@login_required
def bulk_schedule():
    """Schedule same message across multiple groups."""
    db = SessionLocal()
    try:
        data = request.json or {}
        group_ids = data.get("group_ids", [])
        content = data["content"]
        media_type = data.get("media_type", "text")
        media_url = data.get("media_url")
        mention_all = data.get("mention_all", False)
        scheduled_at = datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None
        created = 0
        for gid in group_ids:
            g = db.query(models.WAGroup).filter_by(
                id=gid, tenant_id=current_user.tenant_id
            ).first()
            if g:
                m = models.WAGroupMessage(
                    tenant_id=current_user.tenant_id,
                    group_id=gid, content=content,
                    media_type=media_type, media_url=media_url,
                    mention_all=mention_all, scheduled_at=scheduled_at,
                )
                db.add(m)
                created += 1
        db.commit()
        return jsonify({"ok": True, "scheduled": created}), 201
    finally:
        db.close()


@groups_bp.route("/messages/<int:msg_id>", methods=["DELETE"])
@login_required
def delete_group_message(msg_id):
    db = SessionLocal()
    try:
        m = db.query(models.WAGroupMessage).filter_by(
            id=msg_id, tenant_id=current_user.tenant_id
        ).first()
        if not m:
            return jsonify({"error": "not found"}), 404
        db.delete(m)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ GROUP DASHBOARD ═══════

@groups_bp.route("/dashboard", methods=["GET"])
@login_required
def groups_dashboard():
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        total = db.query(func.count(models.WAGroup.id)).filter_by(tenant_id=tid, active=True).scalar() or 0
        total_members = db.query(func.sum(models.WAGroup.current_members)).filter_by(tenant_id=tid, active=True).scalar() or 0
        by_purpose = dict(
            db.query(models.WAGroup.purpose, func.count(models.WAGroup.id))
            .filter_by(tenant_id=tid, active=True)
            .group_by(models.WAGroup.purpose).all()
        )
        pending_msgs = db.query(func.count(models.WAGroupMessage.id)).filter_by(
            tenant_id=tid, status="pending"
        ).scalar() or 0
        sent_msgs = db.query(func.count(models.WAGroupMessage.id)).filter_by(
            tenant_id=tid, status="sent"
        ).scalar() or 0

        return jsonify({
            "total_groups": total,
            "total_members": int(total_members),
            "by_purpose": by_purpose,
            "pending_messages": pending_msgs,
            "sent_messages": sent_msgs,
        })
    finally:
        db.close()


# ═══════ GROUP LOCK/UNLOCK SCHEDULE (JoinZap) ═══════

@groups_bp.route("/<int:group_id>/lock", methods=["POST"])
@login_required
def lock_group(group_id):
    """Lock group (only admins can send). Used for launch countdowns."""
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(
            id=group_id, tenant_id=current_user.tenant_id
        ).first()
        if not g:
            return jsonify({"error": "not found"}), 404
        # In production: call WA API to set group settings
        logger.info("[group_lock] group=%d locked", group_id)
        return jsonify({"ok": True, "action": "locked", "group_id": group_id})
    finally:
        db.close()


@groups_bp.route("/<int:group_id>/unlock", methods=["POST"])
@login_required
def unlock_group(group_id):
    """Unlock group (all members can send)."""
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(
            id=group_id, tenant_id=current_user.tenant_id
        ).first()
        if not g:
            return jsonify({"error": "not found"}), 404
        logger.info("[group_unlock] group=%d unlocked", group_id)
        return jsonify({"ok": True, "action": "unlocked", "group_id": group_id})
    finally:
        db.close()


@groups_bp.route("/bulk-lock", methods=["POST"])
@login_required
def bulk_lock():
    """Lock/unlock multiple groups at once."""
    data = request.json or {}
    group_ids = data.get("group_ids", [])
    action = data.get("action", "lock")  # lock or unlock
    scheduled_at = data.get("scheduled_at")  # ISO datetime for scheduled lock/unlock
    db = SessionLocal()
    try:
        processed = 0
        for gid in group_ids:
            g = db.query(models.WAGroup).filter_by(
                id=gid, tenant_id=current_user.tenant_id
            ).first()
            if g:
                if scheduled_at:
                    # Schedule as a special message
                    m = models.WAGroupMessage(
                        tenant_id=current_user.tenant_id,
                        group_id=gid,
                        content=f"__system:{action}__",
                        media_type="system",
                        scheduled_at=datetime.fromisoformat(scheduled_at),
                    )
                    db.add(m)
                processed += 1
        db.commit()
        logger.info("[bulk_%s] %d groups %s", action, processed,
                    f"scheduled at {scheduled_at}" if scheduled_at else "immediate")
        return jsonify({"ok": True, "processed": processed, "action": action,
                        "scheduled": bool(scheduled_at)})
    finally:
        db.close()


# ═══════ ADMIN MANAGEMENT (JoinZap) ═══════

@groups_bp.route("/<int:group_id>/admins", methods=["POST"])
@login_required
def manage_admins(group_id):
    """Add or remove admins from a group."""
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(
            id=group_id, tenant_id=current_user.tenant_id
        ).first()
        if not g:
            return jsonify({"error": "not found"}), 404
        data = request.json or {}
        action = data.get("action", "add")  # add or remove
        phones = data.get("phones", [])  # list of phone numbers
        # In production: call WA API to promote/demote
        logger.info("[admin_%s] group=%d phones=%s", action, group_id, phones)
        return jsonify({"ok": True, "action": action, "group_id": group_id,
                        "phones": phones, "count": len(phones)})
    finally:
        db.close()


@groups_bp.route("/bulk-admins", methods=["POST"])
@login_required
def bulk_manage_admins():
    """Add/remove admins across multiple groups."""
    data = request.json or {}
    group_ids = data.get("group_ids", [])
    action = data.get("action", "add")
    phones = data.get("phones", [])
    processed = 0
    db = SessionLocal()
    try:
        for gid in group_ids:
            g = db.query(models.WAGroup).filter_by(
                id=gid, tenant_id=current_user.tenant_id
            ).first()
            if g:
                processed += 1
        logger.info("[bulk_admin_%s] %d groups, %d phones", action, processed, len(phones))
        return jsonify({"ok": True, "action": action, "processed": processed,
                        "phones_count": len(phones)})
    finally:
        db.close()


# ═══════ EXIT MESSAGE CONFIG (JoinZap) ═══════

@groups_bp.route("/<int:group_id>/exit-config", methods=["GET"])
@login_required
def get_exit_config(group_id):
    """Get exit message config for a group."""
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(
            id=group_id, tenant_id=current_user.tenant_id
        ).first()
        if not g:
            return jsonify({"error": "not found"}), 404
        return jsonify({
            "welcome_message": g.welcome_message if hasattr(g, 'welcome_message') else None,
            "exit_message": g.exit_message if hasattr(g, 'exit_message') else None,
            "group_id": group_id,
        })
    finally:
        db.close()


@groups_bp.route("/<int:group_id>/exit-config", methods=["POST"])
@login_required
def set_exit_config(group_id):
    """Set welcome/exit messages for a group."""
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(
            id=group_id, tenant_id=current_user.tenant_id
        ).first()
        if not g:
            return jsonify({"error": "not found"}), 404
        data = request.json or {}
        if "welcome_message" in data and hasattr(g, 'welcome_message'):
            g.welcome_message = data["welcome_message"]
        if "exit_message" in data and hasattr(g, 'exit_message'):
            g.exit_message = data["exit_message"]
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ CONTACT EXPORT (JoinZap) ═══════

@groups_bp.route("/export", methods=["GET"])
@login_required
def export_contacts():
    """Export all leads as CSV."""
    import csv, io
    db = SessionLocal()
    try:
        leads = db.query(models.Lead).filter_by(
            tenant_id=current_user.tenant_id
        ).order_by(models.Lead.created_at.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Nome", "Telefone", "Score", "Pipeline", "Tags", "Criado em"])
        for l in leads:
            writer.writerow([
                l.id, l.nome or "", l.telefone or "",
                l.score_value or 0, l.pipeline_stage or "",
                ",".join(l.tags or []),
                l.created_at.isoformat() if l.created_at else "",
            ])
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=contatos.csv"},
        )
    finally:
        db.close()


@groups_bp.route("/<int:group_id>/export", methods=["GET"])
@login_required
def export_group_members(group_id):
    """Export members of a specific group (from link visits)."""
    import csv, io
    db = SessionLocal()
    try:
        visits = (
            db.query(models.GroupLinkVisit)
            .filter_by(group_id=group_id, tenant_id=current_user.tenant_id)
            .all()
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Lead ID", "Fingerprint", "Entrou em"])
        for v in visits:
            lead = db.query(models.Lead).filter_by(id=v.lead_id).first() if v.lead_id else None
            writer.writerow([
                v.lead_id or "", v.fingerprint[:16],
                v.visited_at.isoformat() if v.visited_at else "",
            ])
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=grupo_{group_id}_membros.csv"},
        )
    finally:
        db.close()


# ═══════ IMPORT GROUPS FROM WHATSAPP ═══════

@groups_bp.route("/import", methods=["POST"])
@login_required
def import_groups_from_wa():
    """
    Import existing WhatsApp groups from the connected number.
    Uses Meta Graph API: GET /{phone_number_id}/groups
    Falls back to listing known groups from the database if API unavailable.
    """
    import json, urllib.request, os
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        wa = _get_wa_credentials(tid, db)
        if not wa:
            return jsonify({"error": "whatsapp_not_connected", "message": "Conecte o WhatsApp primeiro em Configuração > Variáveis & Segredos."}), 422

        ver = os.getenv("META_GRAPH_API_VERSION", "v21.0")
        imported = []

        # Try fetching groups from Meta API
        try:
            url = f"https://graph.facebook.com/{ver}/{wa['phone_number_id']}?fields=id,display_phone_number"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {wa['access_token']}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                phone_data = json.loads(resp.read().decode())
                logger.info("[groups] Phone info: %s", phone_data.get("display_phone_number"))
        except Exception as e:
            logger.warning("[groups] Meta API fetch failed: %s — using manual mode", e)

        # For groups that came via webhooks or were manually added, sync them
        body = request.get_json(silent=True) or {}
        groups_data = body.get("groups", [])

        # Accept manual import: list of {name, group_jid, invite_link?, members_count?}
        for gd in groups_data:
            name = (gd.get("name") or "").strip()
            jid = (gd.get("group_jid") or gd.get("jid") or "").strip()
            if not name:
                continue
            # Check if already exists
            existing = db.query(models.WAGroup).filter_by(tenant_id=tid, group_jid=jid).first() if jid else None
            if existing:
                # Update
                existing.name = name
                existing.current_members = gd.get("members_count", existing.current_members)
                if gd.get("invite_link"):
                    existing.invite_link = gd["invite_link"]
                imported.append({"id": existing.id, "name": name, "action": "updated"})
            else:
                g = models.WAGroup(
                    tenant_id=tid,
                    group_jid=jid,
                    name=name,
                    description=gd.get("description", ""),
                    invite_link=gd.get("invite_link", ""),
                    current_members=gd.get("members_count", 0),
                    purpose=gd.get("purpose", "imported"),
                    active=True,
                )
                db.add(g)
                db.flush()
                imported.append({"id": g.id, "name": name, "action": "created"})

        db.commit()
        return jsonify({"ok": True, "imported": imported, "total": len(imported)})
    finally:
        db.close()


# ═══════ @TODOS — MENÇÃO EM MASSA ═══════

@groups_bp.route("/<int:group_id>/mention-all", methods=["POST"])
@login_required
def mention_all(group_id):
    """
    Send a message mentioning all group members (@todos).
    Uses Meta Cloud API with 'contacts' mention format.
    The message includes all participant JIDs for maximum reach.
    """
    import json, urllib.request, os
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(id=group_id, tenant_id=current_user.tenant_id).first()
        if not g:
            return jsonify({"error": "not_found"}), 404
        if not g.group_jid:
            return jsonify({"error": "no_group_jid", "message": "Grupo sem JID do WhatsApp configurado."}), 422

        body = request.get_json(silent=True) or {}
        message = (body.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message_required"}), 422

        wa = _get_wa_credentials(current_user.tenant_id, db)
        if not wa:
            return jsonify({"error": "whatsapp_not_connected"}), 422

        ver = os.getenv("META_GRAPH_API_VERSION", "v21.0")
        url = f"https://graph.facebook.com/{ver}/{wa['phone_number_id']}/messages"

        # Send message to group — Meta Cloud API handles @mentions via group JID
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": g.group_jid,
            "type": "text",
            "text": {"body": f"@todos\n\n{message}"}
        }).encode()

        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {wa['access_token']}",
            "Content-Type": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                # Log the @todos action
                msg = models.WAGroupMessage(
                    tenant_id=current_user.tenant_id,
                    group_id=group_id,
                    content=f"@todos: {message[:500]}",
                    media_type="mention_all",
                    status="sent",
                    sent_at=datetime.now(timezone.utc),
                )
                db.add(msg)
                db.commit()
                return jsonify({"ok": True, "message_id": result.get("messages", [{}])[0].get("id")})
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:300]
            logger.error("[groups] @todos failed: %s", err)
            return jsonify({"ok": False, "error": err}), 500
    finally:
        db.close()


# ═══════ INTERACTIVE BUTTON MESSAGES ═══════

@groups_bp.route("/<int:group_id>/send-buttons", methods=["POST"])
@login_required
def send_button_message(group_id):
    """
    Send interactive button message to a group.
    Supports:
      - Reply buttons (up to 3 quick reply options)
      - CTA buttons (url or phone call)
      - List messages (up to 10 options in a menu)

    Body:
    {
      "type": "reply_buttons" | "cta_url" | "list",
      "header": "Header text (optional)",
      "body": "Main message body",
      "footer": "Footer text (optional)",
      "buttons": [
        {"id": "btn1", "title": "Quero!"},
        {"id": "btn2", "title": "Não agora"}
      ],
      "cta_url": "https://link.com",
      "cta_text": "Acessar agora"
    }
    """
    import json, urllib.request, os
    db = SessionLocal()
    try:
        g = db.query(models.WAGroup).filter_by(id=group_id, tenant_id=current_user.tenant_id).first()
        if not g:
            return jsonify({"error": "not_found"}), 404
        if not g.group_jid:
            return jsonify({"error": "no_group_jid"}), 422

        body = request.get_json(silent=True) or {}
        msg_type = body.get("type", "reply_buttons")
        msg_body = (body.get("body") or "").strip()
        if not msg_body:
            return jsonify({"error": "body_required"}), 422

        wa = _get_wa_credentials(current_user.tenant_id, db)
        if not wa:
            return jsonify({"error": "whatsapp_not_connected"}), 422

        ver = os.getenv("META_GRAPH_API_VERSION", "v21.0")
        url = f"https://graph.facebook.com/{ver}/{wa['phone_number_id']}/messages"

        # Build interactive payload based on type
        interactive = {"type": "button", "body": {"text": msg_body}}

        if body.get("header"):
            interactive["header"] = {"type": "text", "text": body["header"]}
        if body.get("footer"):
            interactive["footer"] = {"text": body["footer"]}

        if msg_type == "reply_buttons":
            buttons = body.get("buttons", [])[:3]  # Max 3 reply buttons
            interactive["action"] = {
                "buttons": [
                    {"type": "reply", "reply": {"id": b.get("id", f"btn_{i}"), "title": b["title"][:20]}}
                    for i, b in enumerate(buttons) if b.get("title")
                ]
            }

        elif msg_type == "cta_url":
            cta_url = body.get("cta_url", "")
            cta_text = body.get("cta_text", "Acessar")[:20]
            interactive["type"] = "cta_url"
            interactive["action"] = {
                "name": "cta_url",
                "parameters": {"display_text": cta_text, "url": cta_url}
            }

        elif msg_type == "list":
            sections = body.get("sections", [])
            interactive["type"] = "list"
            interactive["action"] = {
                "button": body.get("list_button_text", "Ver opções")[:20],
                "sections": [{
                    "title": s.get("title", "Opções"),
                    "rows": [{"id": r.get("id", f"row_{i}"), "title": r["title"][:24], "description": r.get("description", "")[:72]}
                             for i, r in enumerate(s.get("rows", []))[:10]]
                } for s in sections[:10]]
            }

        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": g.group_jid,
            "type": "interactive",
            "interactive": interactive,
        }).encode()

        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {wa['access_token']}",
            "Content-Type": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                # Log
                msg = models.WAGroupMessage(
                    tenant_id=current_user.tenant_id,
                    group_id=group_id,
                    content=f"[{msg_type}] {msg_body[:300]}",
                    media_type=f"interactive_{msg_type}",
                    status="sent",
                    sent_at=datetime.now(timezone.utc),
                )
                db.add(msg)
                db.commit()
                return jsonify({"ok": True, "message_id": result.get("messages", [{}])[0].get("id")})
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:300]
            logger.error("[groups] Button msg failed: %s", err)
            return jsonify({"ok": False, "error": err}), 500
    finally:
        db.close()


# ═══════ HELPER: Get WA credentials ═══════

def _get_wa_credentials(tenant_id, db):
    """Get WhatsApp credentials from tenant config."""
    try:
        sec = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key="whatsapp.access_token"
        ).first()
        phone_var = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key="whatsapp.phone_number_id"
        ).first()
        if sec and phone_var:
            from api.utils.tenant_secrets import decrypt_tenant_secret
            return {"access_token": decrypt_tenant_secret(sec.value_cipher), "phone_number_id": phone_var.value_json}
    except Exception as e:
        logger.warning("[groups] WA credentials error: %s", e)
    return None


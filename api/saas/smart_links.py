"""
api/saas/smart_links.py — Smart Group Links (JoinZap)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Link inteligente (1 link → N grupos, auto-rotação)
2. Página de vagas encerradas + formulário reserva
3. Anti-duplicidade (fingerprint → mesmo grupo)
4. Facebook Pixel + Google Analytics tracking
"""
from __future__ import annotations
import logging, hashlib, uuid, re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, redirect, render_template_string
from flask_login import login_required, current_user
from sqlalchemy import func

from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
smart_bp = Blueprint("smart_links", __name__, url_prefix="/saas/smart")


# ═══════ MANAGEMENT (Auth required) ═══════

@smart_bp.route("/links", methods=["GET"])
@login_required
def list_smart_links():
    db = SessionLocal()
    try:
        links = db.query(models.SmartGroupLink).filter_by(
            tenant_id=current_user.tenant_id
        ).order_by(models.SmartGroupLink.created_at.desc()).all()
        result = []
        for sl in links:
            groups = db.query(models.WAGroup).filter_by(
                tenant_id=current_user.tenant_id, active=True
            ).filter(models.WAGroup.purpose.in_(["launch", "community", "vip"])).all()
            if sl.launch_id:
                groups = [g for g in groups if g.launch_id == sl.launch_id]
            result.append({
                "id": sl.id, "slug": sl.slug, "name": sl.name,
                "launch_id": sl.launch_id, "max_per_group": sl.max_per_group,
                "active": sl.active,
                "closed_title": sl.closed_title, "closed_message": sl.closed_message,
                "fb_pixel_id": sl.fb_pixel_id, "ga_tracking_id": sl.ga_tracking_id,
                "total_clicks": sl.total_clicks, "total_redirects": sl.total_redirects,
                "total_waitlist": sl.total_waitlist,
                "groups_count": len(groups),
                "url": f"{request.host_url}join/{sl.slug}",
                "created_at": sl.created_at.isoformat() if sl.created_at else None,
            })
        return jsonify({"links": result})
    finally:
        db.close()


@smart_bp.route("/links", methods=["POST"])
@login_required
def create_smart_link():
    db = SessionLocal()
    try:
        data = request.json or {}
        slug = data.get("slug") or uuid.uuid4().hex[:8]
        sl = models.SmartGroupLink(
            tenant_id=current_user.tenant_id,
            slug=slug, name=data["name"],
            launch_id=data.get("launch_id"),
            max_per_group=data.get("max_per_group", 200),
            closed_title=data.get("closed_title", "Vagas Encerradas! 😢"),
            closed_message=data.get("closed_message", "Deixe seu contato para a próxima turma!"),
            closed_cta=data.get("closed_cta", "Quero ser avisado(a)!"),
            fb_pixel_id=data.get("fb_pixel_id"),
            ga_tracking_id=data.get("ga_tracking_id"),
        )
        db.add(sl)
        db.commit()
        return jsonify({"ok": True, "id": sl.id, "url": f"{request.host_url}join/{slug}"}), 201
    finally:
        db.close()


@smart_bp.route("/links/<int:sid>", methods=["PUT"])
@login_required
def update_smart_link(sid):
    db = SessionLocal()
    try:
        sl = db.query(models.SmartGroupLink).filter_by(
            id=sid, tenant_id=current_user.tenant_id
        ).first()
        if not sl:
            return jsonify({"error": "not found"}), 404
        data = request.json or {}
        for k in ("name", "max_per_group", "active", "closed_title", "closed_message",
                   "closed_cta", "fb_pixel_id", "ga_tracking_id", "launch_id"):
            if k in data:
                setattr(sl, k, data[k])
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@smart_bp.route("/links/<int:sid>", methods=["DELETE"])
@login_required
def delete_smart_link(sid):
    db = SessionLocal()
    try:
        sl = db.query(models.SmartGroupLink).filter_by(
            id=sid, tenant_id=current_user.tenant_id
        ).first()
        if not sl:
            return jsonify({"error": "not found"}), 404
        db.delete(sl)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@smart_bp.route("/links/<int:sid>/stats", methods=["GET"])
@login_required
def smart_link_stats(sid):
    db = SessionLocal()
    try:
        sl = db.query(models.SmartGroupLink).filter_by(
            id=sid, tenant_id=current_user.tenant_id
        ).first()
        if not sl:
            return jsonify({"error": "not found"}), 404
        groups = db.query(models.WAGroup).filter_by(
            tenant_id=current_user.tenant_id, active=True
        ).all()
        if sl.launch_id:
            groups = [g for g in groups if g.launch_id == sl.launch_id]
        return jsonify({
            "total_clicks": sl.total_clicks,
            "total_redirects": sl.total_redirects,
            "total_waitlist": sl.total_waitlist,
            "groups": [{"id": g.id, "name": g.name, "members": g.current_members, "max": g.max_members} for g in groups],
            "conversion_rate": round(sl.total_redirects / max(sl.total_clicks, 1) * 100, 1),
        })
    finally:
        db.close()


# ═══════ PUBLIC REDIRECT (No auth — this is the magic) ═══════

CLOSED_PAGE_HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',system-ui,sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;display:flex;align-items:center;justify-content:center;color:#fff}
.card{background:rgba(255,255,255,.08);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.12);border-radius:24px;padding:48px;max-width:480px;width:90%;text-align:center}
h1{font-size:28px;margin-bottom:12px;background:linear-gradient(135deg,#f093fb,#f5576c);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
p{color:rgba(255,255,255,.7);font-size:14px;line-height:1.6;margin-bottom:24px}
form{display:flex;flex-direction:column;gap:12px}
input{padding:14px 20px;border-radius:14px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.06);color:#fff;font-size:14px;outline:none}
input:focus{border-color:#f093fb}
button{padding:14px;border-radius:14px;border:none;background:linear-gradient(135deg,#f093fb,#f5576c);color:#fff;font-size:14px;font-weight:700;cursor:pointer;transition:transform .2s}
button:hover{transform:scale(1.03)}
.ok{color:#4ade80;font-size:13px;margin-top:8px;display:none}
</style>
{{ pixel_code }}
</head><body>
<div class="card">
<h1>{{ title }}</h1>
<p>{{ message }}</p>
<form id="wf" onsubmit="return submitForm(event)">
<input name="name" placeholder="Seu nome" required>
<input name="phone" placeholder="Seu WhatsApp (com DDD)" required>
<button type="submit">{{ cta }}</button>
</form>
<div class="ok" id="ok">✅ Cadastro realizado! Você será avisado(a).</div>
</div>
<script>
function submitForm(e){
e.preventDefault();
var f=document.getElementById('wf');
var d={name:f.name.value,phone:f.phone.value,slug:'{{ slug }}'};
fetch('/saas/smart/waitlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})
.then(function(){document.getElementById('ok').style.display='block';f.style.display='none'});
return false;
}
</script>
</body></html>"""


@smart_bp.route("/join/<slug>", methods=["GET"])
def public_redirect(slug):
    """PUBLIC: Smart redirect to next available group with anti-duplicity."""
    db = SessionLocal()
    try:
        sl = db.query(models.SmartGroupLink).filter_by(slug=slug, active=True).first()
        if not sl:
            return "Link não encontrado", 404

        sl.total_clicks = (sl.total_clicks or 0) + 1

        # Generate fingerprint for anti-duplicity
        ip = request.remote_addr or "unknown"
        ua = request.headers.get("User-Agent", "")
        fp = hashlib.md5(f"{ip}:{ua}".encode()).hexdigest()

        # Check anti-duplicity: did this person visit before?
        existing = db.query(models.GroupLinkVisit).filter_by(
            smart_link_id=sl.id, fingerprint=fp
        ).first()
        if existing and existing.group_id:
            group = db.query(models.WAGroup).filter_by(id=existing.group_id, active=True).first()
            if group and group.invite_link:
                sl.total_redirects = (sl.total_redirects or 0) + 1
                db.commit()
                return redirect(group.invite_link)

        # Find next available group
        q = db.query(models.WAGroup).filter_by(tenant_id=sl.tenant_id, active=True)
        if sl.launch_id:
            q = q.filter_by(launch_id=sl.launch_id)
        groups = q.order_by(models.WAGroup.current_members.asc()).all()

        target = None
        for g in groups:
            if g.current_members < sl.max_per_group and g.invite_link:
                target = g
                break

        if not target:
            # All groups full → show closed page
            sl.total_waitlist = (sl.total_waitlist or 0) + 1
            db.commit()
            pixel_code = ""
            if sl.fb_pixel_id:
                pixel_code += f"<script>!function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init','{sl.fb_pixel_id}');fbq('track','PageView');</script>"
            if sl.ga_tracking_id:
                pixel_code += f"<script async src='https://www.googletagmanager.com/gtag/js?id={sl.ga_tracking_id}'></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{sl.ga_tracking_id}');</script>"
            html = CLOSED_PAGE_HTML.replace("{{ title }}", sl.closed_title or "Vagas Encerradas!")
            html = html.replace("{{ message }}", sl.closed_message or "")
            html = html.replace("{{ cta }}", sl.closed_cta or "Quero ser avisado(a)!")
            html = html.replace("{{ slug }}", sl.slug)
            html = html.replace("{{ pixel_code }}", pixel_code)
            return html

        # Record visit for anti-duplicity
        visit = models.GroupLinkVisit(
            tenant_id=sl.tenant_id, smart_link_id=sl.id,
            fingerprint=fp, group_id=target.id,
        )
        db.add(visit)
        target.current_members = (target.current_members or 0) + 1
        sl.total_redirects = (sl.total_redirects or 0) + 1

        # Fire pixel events
        db.commit()
        return redirect(target.invite_link)
    finally:
        db.close()


@smart_bp.route("/waitlist", methods=["POST"])
def waitlist_signup():
    """PUBLIC: Waitlist signup from closed page."""
    db = SessionLocal()
    try:
        data = request.json or {}
        slug = data.get("slug")
        sl = db.query(models.SmartGroupLink).filter_by(slug=slug).first()
        if not sl:
            return jsonify({"error": "not found"}), 404

        phone = re.sub(r'\D', '', data.get("phone", ""))
        if len(phone) == 11:
            phone = "55" + phone
        name = data.get("name", "")

        lead = db.query(models.Lead).filter_by(tenant_id=sl.tenant_id, telefone=phone).first()
        if not lead:
            lead = models.Lead(
                tenant_id=sl.tenant_id, telefone=phone, nome=name,
                genero="desconhecido", pipeline_stage="novo",
            )
            db.add(lead)
            db.flush()

        tags = list(lead.tags or [])
        if "waitlist" not in tags:
            lead.tags = tags + ["waitlist", f"waitlist:{slug}"]

        sl.total_waitlist = (sl.total_waitlist or 0) + 1
        db.commit()
        return jsonify({"ok": True, "lead_id": lead.id})
    finally:
        db.close()

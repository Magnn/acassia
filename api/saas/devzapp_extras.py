"""
api/saas/devzapp_extras.py — Features extras do DevZapp
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. DevVoice — Templates de áudio PTT humanizado
2. Tracked Links — Links rastreáveis com contagem de cliques
3. Anti-Bloqueio — Configuração de delay, aquecimento, limites
4. Enquetes — Polls em grupos WA
5. Fake Call — Simulação de chamada
6. Variáveis Personalizadas — Substituição dinâmica em templates
"""
from __future__ import annotations
import logging, uuid, re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, redirect
from flask_login import login_required, current_user
from sqlalchemy import func

from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
extras_bp = Blueprint("devzapp_extras", __name__, url_prefix="/saas/extras")


# ═══════ AUTO-SETUP (cria tudo automático na 1ª visita) ═══════

@extras_bp.route("/auto-setup", methods=["POST"])
@login_required
def auto_setup():
    """Auto-configures everything on first visit. Zero manual config."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        created = []

        # 1. Auto-create default departments if none exist
        dept_count = db.query(func.count(models.Department.id)).filter_by(tenant_id=tid).scalar() or 0
        if dept_count == 0:
            defaults = [
                ("Consultas", "consultas", "🔮", "Agendamento e dúvidas sobre consultas", "Olá! 💜 Você foi direcionado(a) para o setor de Consultas. Em breve um atendente vai te ajudar ✨"),
                ("Suporte", "suporte", "🛟", "Dúvidas técnicas e problemas", "Oi! Você está no Suporte. Vamos resolver isso rapidinho! 🚀"),
                ("Financeiro", "financeiro", "💳", "Pagamentos, boletos e reembolsos", "Olá! Setor Financeiro aqui. Como posso ajudar? 💰"),
                ("Cursos", "cursos", "📚", "Informações sobre cursos e workshops", "Bem-vindo(a) ao setor de Cursos! 🌟 Vou te passar todas as informações."),
            ]
            for name, slug, emoji, desc, auto_reply in defaults:
                d = models.Department(
                    tenant_id=tid, name=name, slug=slug, emoji=emoji,
                    description=desc, auto_reply=auto_reply, sort_order=defaults.index((name, slug, emoji, desc, auto_reply)),
                )
                db.add(d)
            created.append("departments")

        # 2. Auto-create safety config if none exists
        safety = db.query(models.SendingSafetyConfig).filter_by(tenant_id=tid).first()
        if not safety:
            safety = models.SendingSafetyConfig(
                tenant_id=tid,
                min_delay_sec=3, max_delay_sec=12,
                max_msgs_per_hour=50, max_msgs_per_day=400,
                warmup_enabled=True, warmup_days=7, warmup_start_pct=20,
                fake_typing_enabled=True, fake_typing_sec=3,
            )
            db.add(safety)
            created.append("safety")

        # 3. Auto-create business hours if none exists
        bh = db.query(models.BusinessHours).filter_by(tenant_id=tid).first()
        if not bh:
            bh = models.BusinessHours(
                tenant_id=tid,
                timezone="America/Sao_Paulo",
                schedule={
                    "mon": {"start": "09:00", "end": "18:00"},
                    "tue": {"start": "09:00", "end": "18:00"},
                    "wed": {"start": "09:00", "end": "18:00"},
                    "thu": {"start": "09:00", "end": "18:00"},
                    "fri": {"start": "09:00", "end": "18:00"},
                },
                away_message="Olá! 💜 Nosso atendimento é de seg-sex 9h-18h. Recebemos sua mensagem e responderemos no próximo horário útil ✨",
            )
            db.add(bh)
            created.append("business_hours")

        # 4. Auto-create default audio templates if none exist
        audio_count = db.query(func.count(models.AudioTemplate.id)).filter_by(tenant_id=tid).scalar() or 0
        if audio_count == 0:
            audio_defaults = [
                ("Boas-vindas", "welcome", "Olá! Que bom ter você aqui! 💜 Sou terapeuta e estou pronta para te ajudar nessa jornada de autoconhecimento."),
                ("Follow-up consulta", "follow_up", "Oi! Tudo bem? Vi que você demonstrou interesse na consulta. Queria saber se ainda posso te ajudar com alguma dúvida? 🌟"),
                ("Oferta especial", "offer", "Oi! Tenho uma novidade especial para você! Estou com vagas limitadas para consultas com um valor especial essa semana. Quer saber mais? ✨"),
                ("Pós-consulta", "follow_up", "Olá! Como você está se sentindo após nossa consulta? Lembre-se que estou aqui se precisar de qualquer coisa! 💜🙏"),
                ("Lembrete pagamento", "follow_up", "Oi! Passando para lembrar do seu pagamento pendente. Se precisar de ajuda, é só me chamar! 💳"),
            ]
            for name, cat, transcript in audio_defaults:
                t = models.AudioTemplate(
                    tenant_id=tid, name=name, category=cat,
                    transcript=transcript, send_as_ptt=True,
                )
                db.add(t)
            created.append("audio_templates")

        db.commit()

        # Calculate setup progress
        progress = _calc_progress(db, tid)

        return jsonify({"ok": True, "created": created, "progress": progress})
    finally:
        db.close()


@extras_bp.route("/progress", methods=["GET"])
@login_required
def get_progress():
    """Gamification: show setup completion progress."""
    db = SessionLocal()
    try:
        progress = _calc_progress(db, current_user.tenant_id)
        return jsonify(progress)
    finally:
        db.close()


def _calc_progress(db, tid: str) -> dict:
    """Calculate setup completion progress for gamification."""
    steps = []
    # 1. Departments
    dept_count = db.query(func.count(models.Department.id)).filter_by(tenant_id=tid, active=True).scalar() or 0
    steps.append({"key": "departments", "label": "Departamentos criados", "done": dept_count > 0, "count": dept_count, "emoji": "🏢"})
    # 2. Business hours
    bh = db.query(models.BusinessHours).filter_by(tenant_id=tid).first()
    steps.append({"key": "business_hours", "label": "Horário de atendimento", "done": bh is not None, "emoji": "🕐"})
    # 3. Safety config
    safety = db.query(models.SendingSafetyConfig).filter_by(tenant_id=tid).first()
    steps.append({"key": "safety", "label": "Anti-bloqueio ativado", "done": safety is not None, "emoji": "🛡️"})
    # 4. Audio templates
    audio_count = db.query(func.count(models.AudioTemplate.id)).filter_by(tenant_id=tid).scalar() or 0
    steps.append({"key": "audio_templates", "label": "Áudios gravados", "done": audio_count > 0, "count": audio_count, "emoji": "🎙️"})
    # 5. Tracked links
    link_count = db.query(func.count(models.TrackedLink.id)).filter_by(tenant_id=tid).scalar() or 0
    steps.append({"key": "tracked_links", "label": "Links rastreáveis", "done": link_count > 0, "count": link_count, "emoji": "🔗"})
    # 6. Checkout webhooks events
    event_count = db.query(func.count(models.CheckoutWebhookEvent.id)).filter_by(tenant_id=tid).scalar() or 0
    steps.append({"key": "checkout_events", "label": "Webhook de checkout recebido", "done": event_count > 0, "count": event_count, "emoji": "💰"})
    # 7. WA Groups
    group_count = db.query(func.count(models.WAGroup.id)).filter_by(tenant_id=tid, active=True).scalar() or 0
    steps.append({"key": "wa_groups", "label": "Grupos WhatsApp", "done": group_count > 0, "count": group_count, "emoji": "👥"})
    # 8. NPS Ratings
    rating_count = db.query(func.count(models.ServiceRating.id)).filter_by(tenant_id=tid).scalar() or 0
    steps.append({"key": "ratings", "label": "Primeira avaliação", "done": rating_count > 0, "count": rating_count, "emoji": "⭐"})

    done_count = sum(1 for s in steps if s["done"])
    total = len(steps)
    pct = round(done_count / total * 100) if total > 0 else 0

    level = "Iniciante"
    if pct >= 100:
        level = "Mestre das Automações 🏆"
    elif pct >= 75:
        level = "Expert 💎"
    elif pct >= 50:
        level = "Avançado 🚀"
    elif pct >= 25:
        level = "Aprendiz ✨"

    return {
        "steps": steps,
        "done": done_count,
        "total": total,
        "pct": pct,
        "level": level,
    }



# ═══════ DEVVOICE — Audio Templates ═══════

@extras_bp.route("/audio-templates", methods=["GET"])
@login_required
def list_audio_templates():
    db = SessionLocal()
    try:
        templates = (
            db.query(models.AudioTemplate)
            .filter_by(tenant_id=current_user.tenant_id)
            .order_by(models.AudioTemplate.use_count.desc())
            .all()
        )
        return jsonify({"templates": [{
            "id": t.id, "name": t.name, "category": t.category,
            "audio_url": t.audio_url, "transcript": t.transcript,
            "duration_sec": t.duration_sec, "send_as_ptt": t.send_as_ptt,
            "use_count": t.use_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in templates]})
    finally:
        db.close()


@extras_bp.route("/audio-templates", methods=["POST"])
@login_required
def create_audio_template():
    db = SessionLocal()
    try:
        data = request.json or {}
        t = models.AudioTemplate(
            tenant_id=current_user.tenant_id,
            name=data["name"],
            category=data.get("category", "general"),
            audio_url=data.get("audio_url"),
            transcript=data.get("transcript"),
            duration_sec=data.get("duration_sec"),
            send_as_ptt=data.get("send_as_ptt", True),
        )
        db.add(t)
        db.commit()
        return jsonify({"ok": True, "template_id": t.id}), 201
    finally:
        db.close()


@extras_bp.route("/audio-templates/<int:tid>", methods=["DELETE"])
@login_required
def delete_audio_template(tid):
    db = SessionLocal()
    try:
        t = db.query(models.AudioTemplate).filter_by(
            id=tid, tenant_id=current_user.tenant_id
        ).first()
        if not t:
            return jsonify({"error": "not found"}), 404
        db.delete(t)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@extras_bp.route("/audio-templates/<int:tid>/use", methods=["POST"])
@login_required
def use_audio_template(tid):
    """Record usage of an audio template."""
    db = SessionLocal()
    try:
        t = db.query(models.AudioTemplate).filter_by(
            id=tid, tenant_id=current_user.tenant_id
        ).first()
        if t:
            t.use_count = (t.use_count or 0) + 1
            db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ TRACKED LINKS ═══════

@extras_bp.route("/links", methods=["GET"])
@login_required
def list_links():
    db = SessionLocal()
    try:
        links = (
            db.query(models.TrackedLink)
            .filter_by(tenant_id=current_user.tenant_id)
            .order_by(models.TrackedLink.created_at.desc())
            .all()
        )
        return jsonify({"links": [{
            "id": l.id, "slug": l.slug, "destination_url": l.destination_url,
            "label": l.label, "clicks": l.clicks, "unique_clicks": l.unique_clicks,
            "tracking_url": f"{request.host_url}go/{l.slug}",
            "last_clicked_at": l.last_clicked_at.isoformat() if l.last_clicked_at else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        } for l in links]})
    finally:
        db.close()


@extras_bp.route("/links", methods=["POST"])
@login_required
def create_link():
    db = SessionLocal()
    try:
        data = request.json or {}
        slug = data.get("slug") or uuid.uuid4().hex[:8]
        l = models.TrackedLink(
            tenant_id=current_user.tenant_id,
            slug=slug,
            destination_url=data["destination_url"],
            label=data.get("label"),
        )
        db.add(l)
        db.commit()
        return jsonify({
            "ok": True, "link_id": l.id, "slug": slug,
            "tracking_url": f"{request.host_url}go/{slug}",
        }), 201
    finally:
        db.close()


@extras_bp.route("/links/<int:lid>", methods=["DELETE"])
@login_required
def delete_link(lid):
    db = SessionLocal()
    try:
        l = db.query(models.TrackedLink).filter_by(
            id=lid, tenant_id=current_user.tenant_id
        ).first()
        if not l:
            return jsonify({"error": "not found"}), 404
        db.delete(l)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@extras_bp.route("/links/stats", methods=["GET"])
@login_required
def link_stats():
    db = SessionLocal()
    try:
        total_clicks = db.query(func.sum(models.TrackedLink.clicks)).filter_by(
            tenant_id=current_user.tenant_id
        ).scalar() or 0
        total_links = db.query(func.count(models.TrackedLink.id)).filter_by(
            tenant_id=current_user.tenant_id
        ).scalar() or 0
        top = (
            db.query(models.TrackedLink)
            .filter_by(tenant_id=current_user.tenant_id)
            .order_by(models.TrackedLink.clicks.desc())
            .limit(10).all()
        )
        return jsonify({
            "total_clicks": int(total_clicks),
            "total_links": total_links,
            "top_links": [{
                "slug": l.slug, "label": l.label,
                "clicks": l.clicks, "destination_url": l.destination_url[:80],
            } for l in top],
        })
    finally:
        db.close()


# ═══════ LINK REDIRECT (Public) ═══════

@extras_bp.route("/go/<slug>", methods=["GET"])
def redirect_link(slug):
    """Public: redirect and track click."""
    db = SessionLocal()
    try:
        link = db.query(models.TrackedLink).filter_by(slug=slug).first()
        if not link:
            return jsonify({"error": "Link not found"}), 404
        link.clicks = (link.clicks or 0) + 1
        link.last_clicked_at = datetime.now(timezone.utc)
        db.commit()
        return redirect(link.destination_url)
    finally:
        db.close()


# ═══════ ANTI-BLOQUEIO (Sending Safety) ═══════

@extras_bp.route("/safety", methods=["GET"])
@login_required
def get_safety():
    db = SessionLocal()
    try:
        cfg = db.query(models.SendingSafetyConfig).filter_by(
            tenant_id=current_user.tenant_id
        ).first()
        if not cfg:
            return jsonify({"config": None})
        return jsonify({"config": {
            "min_delay_sec": cfg.min_delay_sec,
            "max_delay_sec": cfg.max_delay_sec,
            "max_msgs_per_hour": cfg.max_msgs_per_hour,
            "max_msgs_per_day": cfg.max_msgs_per_day,
            "warmup_enabled": cfg.warmup_enabled,
            "warmup_days": cfg.warmup_days,
            "warmup_start_pct": cfg.warmup_start_pct,
            "fake_typing_enabled": cfg.fake_typing_enabled,
            "fake_typing_sec": cfg.fake_typing_sec,
            "active": cfg.active,
        }})
    finally:
        db.close()


@extras_bp.route("/safety", methods=["POST"])
@login_required
def set_safety():
    db = SessionLocal()
    try:
        data = request.json or {}
        cfg = db.query(models.SendingSafetyConfig).filter_by(
            tenant_id=current_user.tenant_id
        ).first()
        if not cfg:
            cfg = models.SendingSafetyConfig(tenant_id=current_user.tenant_id)
            db.add(cfg)
        for k in ("min_delay_sec", "max_delay_sec", "max_msgs_per_hour",
                   "max_msgs_per_day", "warmup_enabled", "warmup_days",
                   "warmup_start_pct", "fake_typing_enabled", "fake_typing_sec", "active"):
            if k in data:
                setattr(cfg, k, data[k])
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ GROUP POLLS (Enquetes) ═══════

@extras_bp.route("/polls", methods=["GET"])
@login_required
def list_polls():
    db = SessionLocal()
    try:
        polls = (
            db.query(models.GroupPoll)
            .filter_by(tenant_id=current_user.tenant_id)
            .order_by(models.GroupPoll.created_at.desc())
            .limit(50).all()
        )
        return jsonify({"polls": [{
            "id": p.id, "group_id": p.group_id,
            "question": p.question, "options": p.options,
            "votes": p.votes, "multi_select": p.multi_select,
            "status": p.status,
            "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        } for p in polls]})
    finally:
        db.close()


@extras_bp.route("/polls", methods=["POST"])
@login_required
def create_poll():
    db = SessionLocal()
    try:
        data = request.json or {}
        p = models.GroupPoll(
            tenant_id=current_user.tenant_id,
            group_id=data["group_id"],
            question=data["question"],
            options=data.get("options", []),
            multi_select=data.get("multi_select", False),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
        )
        db.add(p)
        db.commit()
        return jsonify({"ok": True, "poll_id": p.id}), 201
    finally:
        db.close()


@extras_bp.route("/polls/<int:pid>", methods=["DELETE"])
@login_required
def delete_poll(pid):
    db = SessionLocal()
    try:
        p = db.query(models.GroupPoll).filter_by(
            id=pid, tenant_id=current_user.tenant_id
        ).first()
        if not p:
            return jsonify({"error": "not found"}), 404
        db.delete(p)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ FAKE CALL ═══════

@extras_bp.route("/fake-call", methods=["POST"])
@login_required
def trigger_fake_call():
    """
    Triggers a 'fake call' to a lead — sends a brief ring notification
    via WA to get attention, then auto-cancels.
    Returns the lead_id and status.
    """
    data = request.json or {}
    lead_id = data.get("lead_id")
    duration_sec = data.get("duration_sec", 5)  # ring for N seconds
    logger.info("[fake_call] tenant=%s lead=%s duration=%ds",
                current_user.tenant_id, lead_id, duration_sec)
    # In production this would trigger the WA API voice call endpoint
    return jsonify({
        "ok": True, "lead_id": lead_id,
        "action": "fake_call_queued",
        "ring_duration_sec": duration_sec,
    })


# ═══════ VARIABLE REPLACEMENT ENGINE ═══════

@extras_bp.route("/variables/preview", methods=["POST"])
@login_required
def preview_variables():
    """
    Replace {{variables}} in a template with lead data.
    Used to preview personalized messages before sending.
    """
    db = SessionLocal()
    try:
        data = request.json or {}
        template = data.get("template", "")
        lead_id = data.get("lead_id")

        variables = {
            "nome": "Cliente",
            "primeiro_nome": "Cliente",
            "telefone": "",
            "signo": "",
            "produto": "",
            "valor": "",
            "link_boleto": "",
            "link_pix": "",
            "data_hoje": datetime.now().strftime("%d/%m/%Y"),
            "hora_atual": datetime.now().strftime("%H:%M"),
        }

        if lead_id:
            lead = db.query(models.Lead).filter_by(
                id=lead_id, tenant_id=current_user.tenant_id
            ).first()
            if lead:
                nome = lead.nome or lead.telefone
                variables.update({
                    "nome": nome,
                    "primeiro_nome": nome.split(" ")[0] if nome else "",
                    "telefone": lead.telefone or "",
                    "signo": lead.signo or "",
                    "produto": getattr(lead, "produto_comprado", "") or "",
                    "valor": str(lead.deal_value or ""),
                    "score": str(lead.score_value or 0),
                    "engagement": getattr(lead, "engagement_level", "") or "",
                })

        # Replace {{var}} patterns
        result = template
        for key, val in variables.items():
            result = result.replace("{{" + key + "}}", str(val))

        return jsonify({
            "original": template,
            "rendered": result,
            "variables": variables,
        })
    finally:
        db.close()


@extras_bp.route("/variables/list", methods=["GET"])
@login_required
def list_variables():
    """List all available variables for message templates."""
    return jsonify({"variables": [
        {"key": "nome", "label": "Nome completo", "example": "Maria Silva"},
        {"key": "primeiro_nome", "label": "Primeiro nome", "example": "Maria"},
        {"key": "telefone", "label": "Telefone", "example": "5511999999999"},
        {"key": "signo", "label": "Signo", "example": "Touro"},
        {"key": "produto", "label": "Produto comprado", "example": "Consulta VIP"},
        {"key": "valor", "label": "Valor da compra", "example": "197.00"},
        {"key": "score", "label": "Score do lead", "example": "85"},
        {"key": "engagement", "label": "Nível de engagement", "example": "engaged"},
        {"key": "link_boleto", "label": "Link do boleto", "example": "https://..."},
        {"key": "link_pix", "label": "Código PIX", "example": "00020126..."},
        {"key": "data_hoje", "label": "Data de hoje", "example": "04/05/2026"},
        {"key": "hora_atual", "label": "Hora atual", "example": "14:30"},
    ]})

"""
api/saas/launch_manager.py — Sistema de Lançamento com Grupos WhatsApp
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gerencia lançamentos completos: aquecimento, carrinho aberto, escassez, fechamento.
Cada fase tem: data/hora, mensagem, nome do grupo, ação automática.

Endpoints:
  GET    /saas/launch/                    — lista lançamentos
  POST   /saas/launch/                    — cria lançamento
  GET    /saas/launch/<id>                — detalhe com fases
  PUT    /saas/launch/<id>                — edita lançamento
  DELETE /saas/launch/<id>                — apaga
  POST   /saas/launch/<id>/phases         — adiciona fase
  PUT    /saas/launch/<id>/phases/<pid>   — edita fase
  DELETE /saas/launch/<id>/phases/<pid>   — remove fase
  POST   /saas/launch/<id>/activate       — ativa (agenda cron)
  POST   /saas/launch/<id>/pause          — pausa
  POST   /saas/launch/<id>/execute-phase/<pid> — executa fase manualmente
  POST   /saas/launch/<id>/test           — envia teste no grupo
  GET    /saas/launch/templates           — templates prontos de lançamento
"""
from __future__ import annotations
import json, logging, threading, time
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
launch_bp = Blueprint("saas_launch", __name__, url_prefix="/saas/launch")

# ── Templates de lançamento prontos ──────────────────────────────────
LAUNCH_TEMPLATES = [
    {
        "id": "classico_7d",
        "name": "Lançamento Clássico (7 dias)",
        "description": "Aquecimento de 5 dias + carrinho aberto 48h com escassez final",
        "phases": [
            {"name": "🔥 Aquecimento D-5", "phase_type": "warmup", "offset_hours": 0,
             "group_name": "🔮 [NOME] — Preparem-se ✨",
             "message": "Fala, galera! 🔥\n\nEm 5 dias algo GRANDE vai acontecer aqui dentro.\n\nFiquem atentos às próximas mensagens. Quem estiver aqui no dia, vai ter acesso EXCLUSIVO.\n\n🗓️ Marquem na agenda: {data_lancamento}"},
            {"name": "📚 Conteúdo D-4", "phase_type": "warmup", "offset_hours": 24,
             "group_name": "🔮 [NOME] — Conteúdo Exclusivo 📚",
             "message": "Bom dia! ☀️\n\nHoje quero compartilhar algo que mudou minha vida...\n\n{conteudo_valor}\n\n💬 Me conta aqui: vocês já passaram por isso?"},
            {"name": "🎯 Prova Social D-3", "phase_type": "warmup", "offset_hours": 48,
             "group_name": "🔮 [NOME] — Resultados Reais 🎯",
             "message": "Olha esse depoimento que recebi:\n\n\"{depoimento}\"\n\n✨ E esse é só UM dos resultados.\n\nAmanhã tem mais... 👀"},
            {"name": "⚡ Revelação D-2", "phase_type": "warmup", "offset_hours": 72,
             "group_name": "🔮 [NOME] — Revelação Amanhã ⚡",
             "message": "Amanhã às {hora_abertura} eu vou abrir as inscrições para algo que vai transformar sua vida.\n\n🔒 Vagas LIMITADAS\n💰 Condição especial SÓ pra quem está neste grupo\n\nFiquem de olho! 👁️"},
            {"name": "🗣️ Último aquecimento D-1", "phase_type": "warmup", "offset_hours": 96,
             "group_name": "🔮 [NOME] — AMANHÃ! 🚀",
             "message": "É AMANHÃ! 🚀\n\n⏰ Às {hora_abertura} eu abro as inscrições\n🎁 Bônus exclusivo pra quem entrar nas primeiras 2 horas\n\nQuem vai estar aqui? Manda um 🔥"},
            {"name": "🛒 CARRINHO ABERTO", "phase_type": "cart_open", "offset_hours": 120,
             "group_name": "🛒 [NOME] — INSCRIÇÕES ABERTAS 🔥",
             "message": "🚨 ABRIU! 🚨\n\nAs inscrições estão ABERTAS!\n\n🎁 BÔNUS pra quem entrar AGORA:\n{lista_bonus}\n\n👉 Link: {link_vendas}\n\n⚠️ Condição especial válida só até {data_fechamento}"},
            {"name": "⏰ Lembrete 6h", "phase_type": "reminder", "offset_hours": 126,
             "group_name": "🛒 [NOME] — ÚLTIMAS HORAS ⏰",
             "message": "⏰ Já se passaram 6 horas desde a abertura...\n\n✅ {num_inscritos} pessoas já garantiram a vaga\n\nVocê vai ficar de fora? 🤔\n\n👉 {link_vendas}"},
            {"name": "🔴 ESCASSEZ 12h", "phase_type": "scarcity", "offset_hours": 132,
             "group_name": "🔴 [NOME] — ÚLTIMAS VAGAS ⚠️",
             "message": "🔴 ATENÇÃO!\n\nRestam POUCAS vagas.\n\nDepois de {data_fechamento}, o preço sobe de R${preco_lancamento} para R${preco_normal}.\n\nNão vai dar pra reabrir.\n\n👉 {link_vendas}"},
            {"name": "⚠️ ÚLTIMA CHAMADA", "phase_type": "scarcity", "offset_hours": 142,
             "group_name": "⚠️ [NOME] — FECHA EM 2H ⏳",
             "message": "⚠️ ÚLTIMA CHAMADA ⚠️\n\nFECHA EM 2 HORAS!\n\nDepois disso, acabou. Sem exceções.\n\nSe você sabe que precisa disso, é AGORA.\n\n👉 {link_vendas}\n\n⏳ Contagem regressiva..."},
            {"name": "🔒 CARRINHO FECHADO", "phase_type": "cart_close", "offset_hours": 144,
             "group_name": "🔒 [NOME] — Encerrado ✅",
             "message": "🔒 ENCERRADO!\n\nAs inscrições foram FECHADAS.\n\n✅ {num_inscritos} pessoas garantiram a vaga!\n\nPra quem ficou de fora: me chama no privado.\n\n🙏 Obrigado a todos que estiveram aqui nessa jornada!"},
        ],
    },
    {
        "id": "rapido_3d",
        "name": "Lançamento Rápido (3 dias)",
        "description": "Aquecimento de 1 dia + carrinho 48h com urgência forte",
        "phases": [
            {"name": "🔥 Aquecimento", "phase_type": "warmup", "offset_hours": 0,
             "group_name": "🔮 [NOME] — Novidade Chegando 🔥",
             "message": "🔥 Algo incrível está chegando!\n\nAmanhã às {hora_abertura} vou abrir algo EXCLUSIVO pra este grupo.\n\nFiquem atentos! 👁️"},
            {"name": "🛒 ABERTURA", "phase_type": "cart_open", "offset_hours": 24,
             "group_name": "🛒 [NOME] — ABERTO AGORA! 🚀",
             "message": "🚀 ABRIU!\n\n{descricao_oferta}\n\n💰 De R${preco_normal} por apenas R${preco_lancamento}\n🎁 Bônus: {lista_bonus}\n\n👉 {link_vendas}\n\n⏰ Válido até {data_fechamento}"},
            {"name": "⏰ Meio do caminho", "phase_type": "reminder", "offset_hours": 48,
             "group_name": "🛒 [NOME] — FECHA AMANHÃ ⏰",
             "message": "⏰ Metade do tempo já passou!\n\n{num_inscritos} pessoas já entraram.\n\nAmanhã às {hora_fechamento} eu FECHO.\n\n👉 {link_vendas}"},
            {"name": "⚠️ ÚLTIMA CHAMADA", "phase_type": "scarcity", "offset_hours": 70,
             "group_name": "🔴 [NOME] — 2 HORAS PRA FECHAR ⚠️",
             "message": "🔴 2 HORAS!\n\nÉ sua última chance.\n\n👉 {link_vendas}\n\nDepois disso, não tem volta."},
            {"name": "🔒 FECHAMENTO", "phase_type": "cart_close", "offset_hours": 72,
             "group_name": "🔒 [NOME] — Encerrado",
             "message": "🔒 Encerrado! {num_inscritos} inscritos.\n\nObrigado a todos! 🙏"},
        ],
    },
]


@launch_bp.route("/templates", methods=["GET"])
@login_required
def list_templates():
    return jsonify({"templates": LAUNCH_TEMPLATES})


@launch_bp.route("/", methods=["GET"])
@login_required
def list_launches():
    db = SessionLocal()
    try:
        launches = db.query(models.LaunchCampaign).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.LaunchCampaign.created_at.desc()).limit(20).all()
        return jsonify({"launches": [_serialize_launch(l, db) for l in launches]})
    finally:
        db.close()


@launch_bp.route("/", methods=["POST"])
@login_required
def create_launch():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name_required"}), 422

    db = SessionLocal()
    try:
        launch = models.LaunchCampaign(
            tenant_id=current_user.tenant_id,
            name=name[:200],
            description=(body.get("description") or "")[:500],
            group_jid=body.get("group_jid", ""),
            device_id=body.get("device_id") or None,
            product_name=(body.get("product_name") or "")[:200],
            link_vendas=body.get("link_vendas", ""),
            preco_lancamento=body.get("preco_lancamento", ""),
            preco_normal=body.get("preco_normal", ""),
            start_date=_parse_dt(body.get("start_date")),
            status="draft",
            variables=body.get("variables") or {},
        )
        db.add(launch)
        db.commit()
        db.refresh(launch)

        # Auto-create phases from template
        template_id = body.get("template_id")
        if template_id:
            tpl = next((t for t in LAUNCH_TEMPLATES if t["id"] == template_id), None)
            if tpl and launch.start_date:
                for p in tpl["phases"]:
                    phase = models.LaunchPhase(
                        launch_id=launch.id,
                        name=p["name"],
                        phase_type=p["phase_type"],
                        scheduled_at=launch.start_date + timedelta(hours=p["offset_hours"]),
                        group_name_template=p["group_name"].replace("[NOME]", launch.product_name or name),
                        message_template=p["message"],
                        status="pending",
                        sort_order=p["offset_hours"],
                    )
                    db.add(phase)
                db.commit()

        return jsonify({"ok": True, "id": launch.id}), 201
    finally:
        db.close()


@launch_bp.route("/<int:lid>", methods=["GET"])
@login_required
def get_launch(lid):
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_serialize_launch(l, db))
    finally:
        db.close()


@launch_bp.route("/<int:lid>", methods=["PUT"])
@login_required
def update_launch(lid):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        for k in ("name", "description", "group_jid", "product_name", "link_vendas", "preco_lancamento", "preco_normal"):
            if k in body:
                setattr(l, k, body[k])
        if "start_date" in body:
            l.start_date = _parse_dt(body["start_date"])
        if "variables" in body:
            l.variables = body["variables"]
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@launch_bp.route("/<int:lid>", methods=["DELETE"])
@login_required
def delete_launch(lid):
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        db.query(models.LaunchPhase).filter_by(launch_id=lid).delete()
        db.delete(l)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ── Phase CRUD ───────────────────────────────────────────────────────
@launch_bp.route("/<int:lid>/phases", methods=["POST"])
@login_required
def add_phase(lid):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        phase = models.LaunchPhase(
            launch_id=lid,
            name=(body.get("name") or "Nova Fase")[:200],
            phase_type=body.get("phase_type", "custom"),
            scheduled_at=_parse_dt(body.get("scheduled_at")),
            group_name_template=body.get("group_name_template", ""),
            message_template=body.get("message_template", ""),
            status="pending",
            sort_order=body.get("sort_order", 0),
        )
        db.add(phase)
        db.commit()
        db.refresh(phase)
        return jsonify({"ok": True, "id": phase.id}), 201
    finally:
        db.close()


@launch_bp.route("/<int:lid>/phases/<int:pid>", methods=["PUT"])
@login_required
def update_phase(lid, pid):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        p = db.query(models.LaunchPhase).filter_by(id=pid, launch_id=lid).first()
        if not p:
            return jsonify({"error": "phase_not_found"}), 404
        for k in ("name", "phase_type", "group_name_template", "message_template", "sort_order"):
            if k in body:
                setattr(p, k, body[k])
        if "scheduled_at" in body:
            p.scheduled_at = _parse_dt(body["scheduled_at"])
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@launch_bp.route("/<int:lid>/phases/<int:pid>", methods=["DELETE"])
@login_required
def delete_phase(lid, pid):
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        db.query(models.LaunchPhase).filter_by(id=pid, launch_id=lid).delete()
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ── Activation & Execution ───────────────────────────────────────────
@launch_bp.route("/<int:lid>/activate", methods=["POST"])
@login_required
def activate_launch(lid):
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        phases = db.query(models.LaunchPhase).filter_by(launch_id=lid).all()
        if not phases:
            return jsonify({"error": "no_phases"}), 422
        l.status = "active"
        db.commit()
        return jsonify({"ok": True, "status": "active", "phases": len(phases)})
    finally:
        db.close()


@launch_bp.route("/<int:lid>/pause", methods=["POST"])
@login_required
def pause_launch(lid):
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        l.status = "paused"
        db.commit()
        return jsonify({"ok": True, "status": "paused"})
    finally:
        db.close()


@launch_bp.route("/<int:lid>/execute-phase/<int:pid>", methods=["POST"])
@login_required
def execute_phase_manual(lid, pid):
    """Executa uma fase manualmente (envia mensagem + muda nome do grupo)."""
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        p = db.query(models.LaunchPhase).filter_by(id=pid, launch_id=lid).first()
        if not p:
            return jsonify({"error": "phase_not_found"}), 404

        result = _execute_phase(l, p, db)
        return jsonify(result)
    finally:
        db.close()


# ── Phase Executor ───────────────────────────────────────────────────
def _execute_phase(launch, phase, db) -> dict:
    """Executa uma fase: envia mensagem no grupo + muda nome."""
    results = {"phase": phase.name, "actions": []}
    vars_ = launch.variables or {}
    vars_.update({
        "link_vendas": launch.link_vendas or "",
        "preco_lancamento": launch.preco_lancamento or "",
        "preco_normal": launch.preco_normal or "",
        "produto": launch.product_name or launch.name,
    })

    # Resolve message
    msg = phase.message_template or ""
    for k, v in vars_.items():
        msg = msg.replace(f"{{{k}}}", str(v))

    # Resolve group name
    grp_name = phase.group_name_template or ""
    for k, v in vars_.items():
        grp_name = grp_name.replace(f"{{{k}}}", str(v))

    # Get WA client
    wa_client = _get_wa_client(launch.tenant_id, db)

    # 1) Change group name
    if grp_name and launch.group_jid and wa_client:
        try:
            _change_group_name(wa_client, launch.group_jid, grp_name, launch.tenant_id, db)
            results["actions"].append({"type": "group_name_changed", "name": grp_name, "ok": True})
        except Exception as e:
            results["actions"].append({"type": "group_name_changed", "ok": False, "error": str(e)[:200]})

    # 2) Send message
    if msg and launch.group_jid and wa_client:
        try:
            _send_group_message(wa_client, launch.group_jid, msg, launch.tenant_id, db)
            results["actions"].append({"type": "message_sent", "ok": True})
        except Exception as e:
            results["actions"].append({"type": "message_sent", "ok": False, "error": str(e)[:200]})

    # Mark as executed
    phase.status = "executed"
    phase.executed_at = datetime.now(timezone.utc)
    db.commit()

    results["ok"] = True
    return results


def _get_wa_client(tenant_id, db):
    """Obtém client WhatsApp do tenant."""
    try:
        sec = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key="whatsapp.access_token"
        ).first()
        phone_var = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key="whatsapp.phone_number_id"
        ).first()
        if sec and phone_var:
            return {"access_token": sec.value_cipher, "phone_number_id": phone_var.value_json}
    except Exception as e:
        logger.warning("[launch] WA client error: %s", e)
    return None


def _send_group_message(wa_client, group_jid, message, tenant_id, db):
    """Envia mensagem para grupo via Meta Cloud API."""
    import urllib.request, urllib.error
    import os
    ver = os.getenv("META_GRAPH_API_VERSION", "v21.0")
    url = f"https://graph.facebook.com/{ver}/{wa_client['phone_number_id']}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": group_jid,
        "type": "text",
        "text": {"body": message}
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"Bearer {wa_client['access_token']}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _change_group_name(wa_client, group_jid, new_name, tenant_id, db):
    """Muda o nome/subject do grupo WhatsApp."""
    import urllib.request
    import os
    ver = os.getenv("META_GRAPH_API_VERSION", "v21.0")
    url = f"https://graph.facebook.com/{ver}/{group_jid}"
    payload = json.dumps({"subject": new_name}).encode()
    req = urllib.request.Request(url, data=payload, method="PUT", headers={
        "Authorization": f"Bearer {wa_client['access_token']}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


# ── Cron: auto-execute phases ────────────────────────────────────────
def check_and_execute_due_phases():
    """Chamado pelo cron_jobs.py a cada minuto."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = db.query(models.LaunchPhase).join(models.LaunchCampaign).filter(
            models.LaunchCampaign.status == "active",
            models.LaunchPhase.status == "pending",
            models.LaunchPhase.scheduled_at <= now,
        ).all()

        for phase in due:
            launch = db.query(models.LaunchCampaign).filter_by(id=phase.launch_id).first()
            if launch:
                try:
                    _execute_phase(launch, phase, db)
                    logger.info("[launch] Phase '%s' executed for launch %d", phase.name, launch.id)
                except Exception as e:
                    logger.error("[launch] Phase execution failed: %s", e)
                    phase.status = "failed"
                    phase.error_message = str(e)[:500]
                    db.commit()
    finally:
        db.close()


# ── Clone & Test ─────────────────────────────────────────────────────
@launch_bp.route("/<int:lid>/clone", methods=["POST"])
@login_required
def clone_launch(lid):
    """Duplica um lançamento inteiro (com todas as fases)."""
    db = SessionLocal()
    try:
        orig = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not orig:
            return jsonify({"error": "not_found"}), 404
        clone = models.LaunchCampaign(
            tenant_id=current_user.tenant_id, name=f"{orig.name} (cópia)",
            description=orig.description, group_jid=orig.group_jid,
            product_name=orig.product_name, link_vendas=orig.link_vendas,
            preco_lancamento=orig.preco_lancamento, preco_normal=orig.preco_normal,
            start_date=None, status="draft", variables=orig.variables or {},
        )
        db.add(clone)
        db.commit()
        db.refresh(clone)
        for p in db.query(models.LaunchPhase).filter_by(launch_id=lid).order_by(models.LaunchPhase.sort_order).all():
            db.add(models.LaunchPhase(
                launch_id=clone.id, name=p.name, phase_type=p.phase_type,
                scheduled_at=None, group_name_template=p.group_name_template,
                message_template=p.message_template, media_url=getattr(p, 'media_url', None),
                status="pending", sort_order=p.sort_order,
            ))
        db.commit()
        return jsonify({"ok": True, "id": clone.id}), 201
    finally:
        db.close()


@launch_bp.route("/<int:lid>/test", methods=["POST"])
@login_required
def test_launch(lid):
    """Envia primeira fase pendente pra o próprio número (teste)."""
    db = SessionLocal()
    try:
        l = db.query(models.LaunchCampaign).filter_by(id=lid, tenant_id=current_user.tenant_id).first()
        if not l:
            return jsonify({"error": "not_found"}), 404
        phase = db.query(models.LaunchPhase).filter_by(launch_id=lid, status="pending").order_by(models.LaunchPhase.sort_order).first()
        if not phase:
            return jsonify({"error": "no_pending_phases", "message": "Todas as fases já foram executadas."}), 422
        wa = _get_wa_client(l.tenant_id, db)
        if not wa:
            return jsonify({"error": "whatsapp_not_connected", "message": "Conecte o WhatsApp primeiro."}), 422
        # Send to own number
        vars_ = {**(l.variables or {}), "link_vendas": l.link_vendas or "", "preco_lancamento": l.preco_lancamento or "", "preco_normal": l.preco_normal or "", "produto": l.product_name or l.name}
        msg = phase.message_template or ""
        for k, v in vars_.items():
            msg = msg.replace(f"{{{k}}}", str(v))
        import urllib.request, os
        ver = os.getenv("META_GRAPH_API_VERSION", "v21.0")
        # Get own phone from binding
        binding = db.query(models.WaPhoneTenantBinding).filter_by(tenant_id=l.tenant_id).first()
        own_phone = binding.display_phone_number.replace("+", "").replace(" ", "") if binding and binding.display_phone_number else None
        if not own_phone:
            return jsonify({"error": "no_phone", "message": "Número não encontrado no binding."}), 422
        url = f"https://graph.facebook.com/{ver}/{wa['phone_number_id']}/messages"
        payload = json.dumps({"messaging_product": "whatsapp", "to": own_phone, "type": "text", "text": {"body": f"[TESTE] {phase.name}\n\n{msg}"}}).encode()
        req = urllib.request.Request(url, data=payload, method="POST", headers={"Authorization": f"Bearer {wa['access_token']}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
        return jsonify({"ok": True, "message": f"Teste da fase '{phase.name}' enviado pro seu número!"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:300]}), 500
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────
def _serialize_launch(l, db) -> dict:
    phases = db.query(models.LaunchPhase).filter_by(launch_id=l.id).order_by(
        models.LaunchPhase.sort_order, models.LaunchPhase.scheduled_at
    ).all()
    return {
        "id": l.id, "name": l.name, "description": l.description,
        "group_jid": l.group_jid, "device_id": getattr(l, 'device_id', None),
        "device_nickname": (l.device.nickname if getattr(l, 'device', None) else None),
        "product_name": l.product_name,
        "link_vendas": l.link_vendas, "preco_lancamento": l.preco_lancamento,
        "preco_normal": l.preco_normal, "status": l.status,
        "start_date": l.start_date.isoformat() if l.start_date else None,
        "variables": l.variables,
        "created_at": l.created_at.isoformat(),
        "phases": [{
            "id": p.id, "name": p.name, "phase_type": p.phase_type,
            "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            "group_name_template": p.group_name_template,
            "message_template": p.message_template,
            "media_url": getattr(p, 'media_url', None),
            "status": p.status, "sort_order": p.sort_order,
            "executed_at": p.executed_at.isoformat() if p.executed_at else None,
        } for p in phases],
        "total_phases": len(phases),
        "executed_phases": sum(1 for p in phases if p.status == "executed"),
    }

def _parse_dt(val):
    if not val: return None
    if isinstance(val, datetime): return val
    try: return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except: return None


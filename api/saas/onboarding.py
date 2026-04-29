"""
Wizard de onboarding em 4 passos.

Estado é COMPUTADO a partir de dados no DB (não armazenado em session) —
sobrevive a restart, troca de browser, navegação direta.

Passos:
  1. **persona**  → cria StudioAgent + StudioAgentVersion v1
  2. **oferta**   → cria TenantFlowVariable (oferta.*)
  3. **template** → clona FlowBlueprint do seed escolhido
  4. **whatsapp** → salva phone_number_id/waba_id (var) + access_token (secret)

Endpoints (todos exigem ``@login_required``):
    GET  /onboarding                    → renderiza step atual
    POST /onboarding/persona
    POST /onboarding/oferta
    POST /onboarding/template
    POST /onboarding/whatsapp           → após este, onboarding completo

Wiring no app.py (1 linha)::

    from api.saas.onboarding import onboarding_bp
    app.register_blueprint(onboarding_bp)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from flows.post_payment.seeds import AVAILABLE_SEEDS, load_seed

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint("saas_onboarding", __name__, url_prefix="/saas/onboarding")

STEP_PERSONA = "persona"
STEP_OFERTA = "oferta"
STEP_TEMPLATE = "template"
STEP_WHATSAPP = "whatsapp"
STEP_DONE = "done"

ALLOWED_TONES = ("acolhedor", "direto", "mistico", "sedutor")
ALLOWED_GATEWAYS = ("stripe", "cakto")
ALLOWED_TEMPLATES = ("tarot_express", "quiromancia_premium", "em_branco")
ALLOWED_RESTRICTIONS = (
    "nao_promete_cura",
    "nao_da_conselho_medico",
    "nao_da_conselho_juridico",
    "nao_promete_resultado_financeiro",
)


# ─── State detection ─────────────────────────────────────────────────────────


def detect_current_step(tenant_id: str) -> str:
    """Detecta qual step o tenant precisa fazer baseado em dados existentes."""
    db = SessionLocal()
    try:
        if not db.query(models.StudioAgent).filter_by(tenant_id=tenant_id).first():
            return STEP_PERSONA
        if not _has_var(db, tenant_id, "oferta.nome"):
            return STEP_OFERTA
        if not db.query(models.FlowBlueprint).filter_by(
            tenant_id=tenant_id, slug="post_payment"
        ).first():
            return STEP_TEMPLATE
        if not _has_var(db, tenant_id, "whatsapp.phone_number_id"):
            return STEP_WHATSAPP
        return STEP_DONE
    finally:
        db.close()


def _has_var(db, tenant_id: str, key: str) -> bool:
    return db.query(models.TenantFlowVariable).filter_by(
        tenant_id=tenant_id, key=key
    ).first() is not None


# ─── Step handlers (funções puras testáveis) ─────────────────────────────────


def save_persona(
    tenant_id: str,
    name: str,
    tone: str,
    backstory: str,
    restrictions: list[str],
) -> models.StudioAgent:
    """Cria StudioAgent + StudioAgentVersion v1. Levanta ValueError se inválido."""
    name = (name or "").strip()
    tone = (tone or "").strip().lower()
    backstory = (backstory or "").strip()

    if not name:
        raise ValueError("nome da cigana é obrigatório")
    if tone not in ALLOWED_TONES:
        raise ValueError(f"tom inválido; aceitos: {ALLOWED_TONES}")
    if len(backstory) < 20:
        raise ValueError("história de origem precisa de no mínimo 20 caracteres")

    valid_restrictions = [r for r in (restrictions or []) if r in ALLOWED_RESTRICTIONS]

    db = SessionLocal()
    try:
        # Garante 1 StudioAgent por tenant — se já existir, atualiza
        agent = db.query(models.StudioAgent).filter_by(tenant_id=tenant_id).first()
        if agent:
            agent.name = name[:200]
        else:
            agent = models.StudioAgent(tenant_id=tenant_id, name=name[:200])
            db.add(agent)
        db.flush()

        body = {
            "tone": tone,
            "backstory": backstory[:2000],
            "restrictions": valid_restrictions,
        }
        version = models.StudioAgentVersion(
            agent_id=agent.id,
            version_number=1,
            body_json=body,
            note="onboarding wizard step 1",
        )
        db.add(version)
        db.commit()
        db.refresh(agent)
        logger.info("[onboarding] persona saved tenant=%s agent=%s", tenant_id, agent.id)
        return agent
    finally:
        db.close()


def save_oferta(
    tenant_id: str,
    nome: str,
    preco: str,
    descricao: str,
    gateway: str,
) -> None:
    """Salva campos de oferta como TenantFlowVariable."""
    nome = (nome or "").strip()
    descricao = (descricao or "").strip()
    gateway = (gateway or "").strip().lower()

    if not nome:
        raise ValueError("nome do produto é obrigatório")
    try:
        preco_float = float((preco or "").replace(",", ".").strip())
    except ValueError:
        raise ValueError("preço inválido")
    if preco_float <= 0:
        raise ValueError("preço deve ser positivo")
    if gateway not in ALLOWED_GATEWAYS:
        raise ValueError(f"gateway inválido; aceitos: {ALLOWED_GATEWAYS}")

    _set_var(tenant_id, "oferta.nome", nome[:300])
    _set_var(tenant_id, "oferta.preco", round(preco_float, 2))
    _set_var(tenant_id, "oferta.descricao", descricao[:1000])
    _set_var(tenant_id, "oferta.gateway_padrao", gateway)
    logger.info("[onboarding] oferta saved tenant=%s gateway=%s", tenant_id, gateway)


def save_template(tenant_id: str, template: str) -> Optional[int]:
    """
    Clona blueprint semente pro tenant. ``em_branco`` cria blueprint vazio.
    Returns blueprint_id ou None.
    """
    template = (template or "").strip().lower()
    if template not in ALLOWED_TEMPLATES:
        raise ValueError(f"template inválido; aceitos: {ALLOWED_TEMPLATES}")

    _set_var(tenant_id, "template_escolhido", template)

    if template == "em_branco":
        body = {
            "format": "acassia-flow",
            "version": 1,
            "title": "Pós-pagamento (em branco)",
            "graph": {"nodes": [], "edges": []},
        }
        title = "Pós-pagamento (em branco)"
    else:
        seed_name = "express" if template == "tarot_express" else "premium"
        if seed_name not in AVAILABLE_SEEDS:
            raise ValueError(f"seed inexistente: {seed_name}")
        body = load_seed(seed_name)
        title = body.get("title", f"Pós-pagamento {template}")

    db = SessionLocal()
    try:
        existing = db.query(models.FlowBlueprint).filter_by(
            tenant_id=tenant_id, slug="post_payment"
        ).first()
        if existing:
            existing.body_json = body
            existing.title = title[:300]
            db.commit()
            db.refresh(existing)
            logger.info("[onboarding] template updated tenant=%s template=%s", tenant_id, template)
            return existing.id

        bp = models.FlowBlueprint(
            tenant_id=tenant_id,
            slug="post_payment",
            title=title[:300],
            body_json=body,
        )
        db.add(bp)
        db.commit()
        db.refresh(bp)
        logger.info("[onboarding] template saved tenant=%s template=%s blueprint=%s", tenant_id, template, bp.id)
        return bp.id
    finally:
        db.close()


def save_whatsapp(
    tenant_id: str,
    phone_number_id: str,
    waba_id: str,
    access_token: str,
) -> None:
    """Salva credenciais WhatsApp. Token vira TenantFlowSecret; ids são vars."""
    phone_number_id = (phone_number_id or "").strip()
    waba_id = (waba_id or "").strip()
    access_token = (access_token or "").strip()

    if not phone_number_id or not phone_number_id.isdigit():
        raise ValueError("phone_number_id deve ser numérico")
    if not waba_id or not waba_id.isdigit():
        raise ValueError("waba_id deve ser numérico")
    if len(access_token) < 20:
        raise ValueError("access_token parece inválido (muito curto)")

    _set_var(tenant_id, "whatsapp.phone_number_id", phone_number_id)
    _set_var(tenant_id, "whatsapp.waba_id", waba_id)
    _set_secret(tenant_id, "whatsapp.access_token", access_token)
    logger.info(
        "[onboarding] whatsapp saved tenant=%s phone_id=%s",
        tenant_id, phone_number_id,
    )


# ─── Helpers DB ──────────────────────────────────────────────────────────────


def _set_var(tenant_id: str, key: str, value: Any) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=key
        ).first()
        if existing:
            existing.value_json = value
        else:
            db.add(models.TenantFlowVariable(tenant_id=tenant_id, key=key, value_json=value))
        db.commit()
    finally:
        db.close()


def _set_secret(tenant_id: str, key: str, cipher: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key=key
        ).first()
        if existing:
            existing.value_cipher = cipher
        else:
            db.add(models.TenantFlowSecret(tenant_id=tenant_id, key=key, value_cipher=cipher))
        db.commit()
    finally:
        db.close()


# ─── Endpoints ───────────────────────────────────────────────────────────────


@onboarding_bp.route("/", methods=["GET"])
@login_required
def index():
    step = detect_current_step(current_user.tenant_id)
    if step == STEP_DONE:
        if request.accept_mimetypes.accept_json:
            return jsonify({"current_step": step, "done": True})
        return redirect(url_for("saas_auth.signup_done"))
    
    if request.accept_mimetypes.accept_json:
        return jsonify({"current_step": step})
    return render_template("onboarding/wizard.html", current_step=step)


@onboarding_bp.route("/persona", methods=["POST"])
@login_required
def persona():
    data = request.get_json() if request.is_json else request.form
    try:
        save_persona(
            tenant_id=current_user.tenant_id,
            name=data.get("name", ""),
            tone=data.get("tone", ""),
            backstory=data.get("backstory", ""),
            restrictions=data.getlist("restrictions") if hasattr(data, 'getlist') else data.get("restrictions", []),
        )
    except ValueError as exc:
        if request.is_json:
            return jsonify({"error": str(exc)}), 400
        flash(str(exc), "error")
        return render_template("onboarding/wizard.html", current_step=STEP_PERSONA), 400
    
    if request.is_json:
        return jsonify({"ok": True, "next_step": detect_current_step(current_user.tenant_id)})
    return redirect(url_for("saas_onboarding.index"))


@onboarding_bp.route("/oferta", methods=["POST"])
@login_required
def oferta():
    data = request.get_json() if request.is_json else request.form
    try:
        save_oferta(
            tenant_id=current_user.tenant_id,
            nome=data.get("nome", ""),
            preco=data.get("preco", ""),
            descricao=data.get("descricao", ""),
            gateway=data.get("gateway", ""),
        )
    except ValueError as exc:
        if request.is_json:
            return jsonify({"error": str(exc)}), 400
        flash(str(exc), "error")
        return render_template("onboarding/wizard.html", current_step=STEP_OFERTA), 400
    
    if request.is_json:
        return jsonify({"ok": True, "next_step": detect_current_step(current_user.tenant_id)})
    return redirect(url_for("saas_onboarding.index"))


@onboarding_bp.route("/template", methods=["POST"])
@login_required
def template_step():
    data = request.get_json() if request.is_json else request.form
    try:
        save_template(
            tenant_id=current_user.tenant_id,
            template=data.get("template", ""),
        )
    except ValueError as exc:
        if request.is_json:
            return jsonify({"error": str(exc)}), 400
        flash(str(exc), "error")
        return render_template("onboarding/wizard.html", current_step=STEP_TEMPLATE), 400
    
    if request.is_json:
        return jsonify({"ok": True, "next_step": detect_current_step(current_user.tenant_id)})
    return redirect(url_for("saas_onboarding.index"))


@onboarding_bp.route("/whatsapp", methods=["POST"])
@login_required
def whatsapp():
    data = request.get_json() if request.is_json else request.form
    try:
        save_whatsapp(
            tenant_id=current_user.tenant_id,
            phone_number_id=data.get("phone_number_id", ""),
            waba_id=data.get("waba_id", ""),
            access_token=data.get("access_token", ""),
        )
    except ValueError as exc:
        if request.is_json:
            return jsonify({"error": str(exc)}), 400
        flash(str(exc), "error")
        return render_template("onboarding/wizard.html", current_step=STEP_WHATSAPP), 400
    
    if request.is_json:
        return jsonify({"ok": True, "next_step": STEP_DONE})
    flash("Onboarding concluído! Tua cigana está pronta pra ser ativada.", "success")
    return redirect(url_for("saas_auth.signup_done"))

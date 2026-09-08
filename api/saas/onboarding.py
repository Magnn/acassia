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
import math
from typing import Any, Optional

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, has_request_context
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from api.utils.tenant_secrets import encrypt_tenant_secret
from flows.post_payment.seeds import AVAILABLE_SEEDS, load_seed

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint("saas_onboarding", __name__, url_prefix="/saas/onboarding")

STEP_PERSONA = "persona"
STEP_OFERTA = "oferta"
STEP_TEMPLATE = "template"
STEP_WHATSAPP = "whatsapp"
STEP_DONE = "done"

ALLOWED_TONES = ("acolhedor", "direto", "mistico", "sedutor", "consultivo", "persuasivo", "tecnico")
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
        if not db.query(models.FlowBlueprint).filter_by(tenant_id=tenant_id).first():
            return STEP_TEMPLATE
        phone = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key="whatsapp.phone_number_id"
        ).first()
        binding = db.query(models.WaPhoneTenantBinding).filter_by(
            tenant_id=tenant_id, phone_number_id=str(phone.value_json)
        ).first() if phone and phone.value_json else None
        if not binding or binding.status != "active" or not binding.last_verified_at:
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
        raise ValueError("nome do atendente é obrigatório")
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
        latest = db.query(models.StudioAgentVersion).filter_by(agent_id=agent.id).order_by(
            models.StudioAgentVersion.version_number.desc()
        ).first()
        version = models.StudioAgentVersion(
            agent_id=agent.id,
            version_number=(latest.version_number + 1) if latest else 1,
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
    if not math.isfinite(preco_float) or preco_float <= 0:
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

    Aceita 3 formas de template (Frente 4.23):
      1. Constante legada (``tarot_express``, ``quiromancia_premium``,
         ``em_branco``) -> seeds via load_seed
      2. ID de FlowTemplate (``tarot-amor-express``, etc) -> clona
         blueprint_json da tabela
      3. ``em_branco`` -> blueprint vazio

    Returns blueprint_id ou None.
    """
    raw_template = (template or "").strip()
    template = raw_template.lower().replace(" ", "_")

    body = None
    title = None
    slug = "post_payment"

    # 1. em_branco
    if template == "atendimento_comercial":
        from flows.business_templates import sales_starter
        with SessionLocal() as config_db:
            offer = {v.key: v.value_json for v in config_db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id).all()}
        if not offer.get("oferta.nome"):
            raise ValueError("Cadastre a oferta antes de escolher este modelo")
        body = sales_starter(str(offer["oferta.nome"]), str(offer.get("oferta.descricao") or ""))
        title = body["title"]
        slug = "atendimento_comercial"
    elif template == "em_branco":
        body = {
            "format": "meumisterio-flow",
            "version": 1,
            "title": "Pós-pagamento (em branco)",
            "graph": {"nodes": [], "edges": []},
        }
        title = "Pós-pagamento (em branco)"
    # 2. Tenta constante legada
    elif template in ALLOWED_TEMPLATES:
        seed_name = "express" if template == "tarot_express" else "premium"
        if seed_name not in AVAILABLE_SEEDS:
            raise ValueError(f"seed inexistente: {seed_name}")
        body = load_seed(seed_name)
        title = body.get("title", f"Pós-pagamento {template}")
    # 3. Tenta como FlowTemplate.id (suporta hifen e underscore)
    else:
        ft_db = SessionLocal()
        try:
            ft_id_candidates = [raw_template, raw_template.replace("_", "-"), raw_template.replace("-", "_")]
            ft = None
            for cand in ft_id_candidates:
                ft = ft_db.query(models.FlowTemplate).filter_by(id=cand).first()
                if ft:
                    break
            if ft is None:
                raise ValueError(
                    f"template inválido; aceitos: legados {ALLOWED_TEMPLATES} ou "
                    f"FlowTemplate.id existente"
                )
            # Increment usage_count
            ft.usage_count = (ft.usage_count or 0) + 1
            ft_db.commit()
            body_in = ft.blueprint_json or {}
            # Normaliza pra formato meumisterio-flow se o seed estiver no formato antigo
            if "graph" in body_in:
                body = body_in
            else:
                # Converte nodes simples em formato meumisterio-flow
                body = {
                    "format": "meumisterio-flow",
                    "version": 1,
                    "title": ft.name,
                    "graph": {
                        "nodes": body_in.get("nodes") or [],
                        "edges": body_in.get("edges") or [],
                    },
                }
            title = ft.name
        finally:
            ft_db.close()

    db = SessionLocal()
    try:
        existing = db.query(models.FlowBlueprint).filter_by(
            tenant_id=tenant_id, slug=slug
        ).first()
        if existing:
            existing.body_json = body
            existing.title = title[:300]
            _set_var(tenant_id, "template_escolhido", template, db_session=db)
            db.commit()
            db.refresh(existing)
            logger.info("[onboarding] template updated tenant=%s template=%s", tenant_id, template)
            return existing.id

        bp = models.FlowBlueprint(
            tenant_id=tenant_id,
            slug=slug,
            title=title[:300],
            body_json=body,
        )
        db.add(bp)
        _set_var(tenant_id, "template_escolhido", template, db_session=db)
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
    *,
    skip_validation: bool = False,
) -> dict:
    """
    Salva credenciais WhatsApp + cria/atualiza WaPhoneTenantBinding (multi-tenant
    ready). Auto-subscribe ao WABA é tentado se waba_id presente.

    Token vira TenantFlowSecret; ids são vars; binding mapeia phone_id->tenant.

    Retorna dict {binding, verify_token, webhook_url} pra UI mostrar
    instruções da Meta.
    """
    import secrets as _secrets
    from datetime import datetime as _dt, timezone as _tz

    phone_number_id = (phone_number_id or "").strip()
    waba_id = (waba_id or "").strip()
    access_token = (access_token or "").strip()

    if not phone_number_id or not phone_number_id.isdigit():
        raise ValueError("phone_number_id deve ser numérico")
    if not waba_id or not waba_id.isdigit():
        raise ValueError("waba_id deve ser numérico")
    if len(access_token) < 20:
        raise ValueError("access_token parece inválido (muito curto)")

    # 1) Validação Graph API (best-effort: se falhar e skip_validation=False, levanta)
    info: dict = {}
    if not skip_validation:
        try:
            from api.saas.integrations_whatsapp import _validate_token_and_phone
            ok, info = _validate_token_and_phone(access_token, phone_number_id)
            if not ok:
                err = (info.get("error") or {}).get("message") if isinstance(info, dict) else None
                raise ValueError(f"credenciais inválidas: {err or 'verifique token e phone_number_id'}")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Não foi possível validar o WhatsApp. Tente novamente.") from exc

    # 3) Upsert binding + auto-subscribe
    db = SessionLocal()
    try:
        existing = db.query(models.WaPhoneTenantBinding).filter_by(
            phone_number_id=phone_number_id,
        ).first()
        if existing and existing.tenant_id != tenant_id:
            raise ValueError("phone_number_id já vinculado a outro tenant")

        # Configuração e vínculo são uma única transação; conflito não altera a conta.
        _set_var(tenant_id, "whatsapp.phone_number_id", phone_number_id, db_session=db)
        _set_var(tenant_id, "whatsapp.waba_id", waba_id, db_session=db)
        _set_var(tenant_id, "whatsapp.provider", "meta_cloud", db_session=db)
        _set_secret(tenant_id, "whatsapp.access_token", access_token, db_session=db)

        if existing:
            binding = existing
        else:
            binding = models.WaPhoneTenantBinding(phone_number_id=phone_number_id)
            db.add(binding)

        binding.tenant_id = tenant_id
        binding.waba_id = waba_id
        binding.display_phone_number = info.get("display_phone_number") if isinstance(info, dict) else None
        binding.verify_token = binding.verify_token or _secrets.token_urlsafe(32)
        binding.webhook_path = binding.webhook_path or f"wh_{_secrets.token_urlsafe(24)}"
        binding.status = "pending" if skip_validation else "active"
        binding.last_verified_at = None if skip_validation else _dt.now(_tz.utc)
        binding.last_error = None
        binding.subscribed_at = None
        binding.subscribe_error = None
        binding.updated_at = _dt.now(_tz.utc)

        # Auto-subscribe (best-effort)
        if not skip_validation and waba_id:
            try:
                from meta_graph_admin import subscribe_apps_to_waba
                ok_sub, body_sub = subscribe_apps_to_waba(waba_id, access_token)
                if ok_sub and (body_sub.get("success") is True or body_sub.get("data") is not None):
                    binding.subscribed_at = _dt.now(_tz.utc)
                    binding.subscribe_error = None
                else:
                    binding.subscribe_error = str(
                        (body_sub.get("error") or {}).get("message") or "unknown"
                    )[:500]
            except Exception as exc:
                binding.subscribe_error = str(exc)[:500]

        db.commit()
        db.refresh(binding)

        # Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=None,
                event_type="onboarding.whatsapp.bound",
                target_type="phone_number_id",
                target_id=phone_number_id,
                payload={
                    "waba_id": waba_id,
                    "display_phone_number": binding.display_phone_number,
                    "subscribed": binding.subscribed_at is not None,
                },
            ))
            db.commit()
        except Exception:
            db.rollback()

        # Cache invalidation
        try:
            from api.tenant_config import clear_cache as _clear_cfg
            _clear_cfg(tenant_id)
        except Exception:
            pass
        try:
            from wa_tenant_resolver import invalidate_cache as _invalidate_resolver
            _invalidate_resolver(phone_number_id)
        except Exception:
            pass

        logger.info(
            "[onboarding] whatsapp saved tenant=%s phone_id=%s subscribed=%s",
            tenant_id, phone_number_id, binding.subscribed_at is not None,
        )

        # Webhook URL pra UI mostrar
        import os
        public_url = (os.getenv("PUBLIC_URL") or "").rstrip("/")
        if not public_url and has_request_context():
            public_url = request.host_url.rstrip("/")
        webhook_url = f"{public_url}/webhook/{binding.webhook_path}"

        return {
            "phone_number_id": binding.phone_number_id,
            "verify_token": binding.verify_token,
            "webhook_url": webhook_url,
            "subscribed": binding.subscribed_at is not None,
            "subscribe_error": binding.subscribe_error,
            "display_phone_number": binding.display_phone_number,
        }
    finally:
        db.close()


# ─── Helpers DB ──────────────────────────────────────────────────────────────


def _set_var(tenant_id: str, key: str, value: Any, *, db_session=None) -> None:
    db = db_session if db_session is not None else SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=key
        ).first()
        if existing:
            existing.value_json = value
        else:
            db.add(models.TenantFlowVariable(tenant_id=tenant_id, key=key, value_json=value))
        if db_session is None:
            db.commit()
    finally:
        if db_session is None:
            db.close()


def _set_secret(tenant_id: str, key: str, cipher: str, *, db_session=None) -> None:
    cipher = encrypt_tenant_secret(cipher)
    db = db_session if db_session is not None else SessionLocal()
    try:
        existing = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key=key
        ).first()
        if existing:
            existing.value_cipher = cipher
        else:
            db.add(models.TenantFlowSecret(tenant_id=tenant_id, key=key, value_cipher=cipher))
        if db_session is None:
            db.commit()
    finally:
        if db_session is None:
            db.close()


# ─── Endpoints ───────────────────────────────────────────────────────────────


@onboarding_bp.route("/readiness", methods=["GET"])
@login_required
def readiness():
    from launch_readiness import launch_readiness
    return jsonify(launch_readiness(current_user.tenant_id))


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
    skip_validation = data.get("skip_validation") in (True, "true", "1", "on")
    try:
        result = save_whatsapp(
            tenant_id=current_user.tenant_id,
            phone_number_id=data.get("phone_number_id", ""),
            waba_id=data.get("waba_id", ""),
            access_token=data.get("access_token", ""),
            skip_validation=skip_validation,
        )
    except ValueError as exc:
        if request.is_json:
            return jsonify({"error": str(exc)}), 400
        flash(str(exc), "error")
        return render_template("onboarding/wizard.html", current_step=STEP_WHATSAPP), 400

    if request.is_json:
        return jsonify({
            "ok": True,
            "next_step": detect_current_step(current_user.tenant_id),
            "binding": result,
            "instructions": [
                "1. Va em developers.facebook.com -> seu app -> WhatsApp -> Configuracao",
                f"2. Cole '{result['webhook_url']}' no Webhook callback URL",
                f"3. Cole o verify_token: {result['verify_token']}",
                "4. Em 'Webhook fields', assine ao menos: messages",
                "5. Mande uma msg pro numero pra confirmar — vai aparecer aqui em segundos",
            ],
        })
    if detect_current_step(current_user.tenant_id) != STEP_DONE:
        flash("Configuração salva. Valide a conexão para continuar.", "info")
        return redirect(url_for("saas_onboarding.index"))
    flash("Configuração salva. Confirme o recebimento de uma mensagem e teste seu fluxo.", "success")
    return redirect(url_for("saas_auth.signup_done"))

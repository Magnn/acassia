"""
Settings UI — single page com seções (recovery cadence, WhatsApp, Stripe).

Endpoints:
    GET  /saas/settings           — página única com 3 sections
    POST /saas/settings/recovery  — atualiza cadência (ADR_005)
"""

from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from api.tenant_config import clear_cache, get_tenant_config
from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

settings_bp = Blueprint("saas_settings", __name__, url_prefix="/saas/settings")

MIN_INTERVAL_MIN = 5
MAX_INTERVAL_MIN = 7 * 24 * 60   # 7 dias
MAX_TOQUES = 7


def _parse_cadence(raw: str) -> list[int]:
    """
    Parse "5, 60, 180" → [5, 60, 180]. Levanta ValueError se inválido.
    """
    if not raw or not raw.strip():
        raise ValueError("cadência não pode ser vazia")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("cadência não pode ser vazia")
    if len(parts) > MAX_TOQUES:
        raise ValueError(f"máximo {MAX_TOQUES} toques")

    result: list[int] = []
    for p in parts:
        try:
            n = int(p)
        except ValueError:
            raise ValueError(f"valor inválido: {p!r}")
        if n < MIN_INTERVAL_MIN:
            raise ValueError(f"intervalo mínimo é {MIN_INTERVAL_MIN}min")
        if n > MAX_INTERVAL_MIN:
            raise ValueError(f"intervalo máximo é 7 dias ({MAX_INTERVAL_MIN}min)")
        result.append(n)
    return result


def _set_var(tenant_id: str, key: str, value) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=key,
        ).first()
        if existing:
            existing.value_json = value
        else:
            db.add(models.TenantFlowVariable(
                tenant_id=tenant_id, key=key, value_json=value,
            ))
        db.commit()
    finally:
        db.close()
    clear_cache(tenant_id)


@settings_bp.route("/", methods=["GET"])
@login_required
def index():
    tenant_id = current_user.tenant_id
    cfg = get_tenant_config(tenant_id)

    recovery = cfg.get("recovery") or {}
    cadence = recovery.get("cadence_minutes") or [5, 60, 180]
    if not isinstance(cadence, list):
        cadence = [5, 60, 180]

    whatsapp = cfg.get("whatsapp") or {}
    stripe_cfg = cfg.get("stripe") or {}

    return render_template(
        "settings/index.html",
        cadence_str=", ".join(str(x) for x in cadence),
        whatsapp_phone_id=whatsapp.get("phone_number_id") or "",
        whatsapp_waba_id=whatsapp.get("waba_id") or "",
        whatsapp_configured=bool(whatsapp.get("phone_number_id")),
        subscription_status=stripe_cfg.get("subscription_status") or "",
        connect_payouts=bool(stripe_cfg.get("connect_payouts_enabled")),
    )


@settings_bp.route("/recovery", methods=["POST"])
@login_required
def recovery():
    tenant_id = current_user.tenant_id
    raw = request.form.get("cadence_minutes", "")
    try:
        cadence = _parse_cadence(raw)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("saas_settings.index"))

    _set_var(tenant_id, "recovery.cadence_minutes", cadence)
    flash(f"Cadência atualizada: {cadence}", "success")
    return redirect(url_for("saas_settings.index"))

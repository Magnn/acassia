"""
api/saas/growth_links.py — Gerador de Links WhatsApp e QR Codes (Growth Tools)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paridade ChatbotX: "Growth Tools: Generate conversation starters, QR Codes, and shareable links"
Permite gerar links wa.me personalizados com mensagens pré-definidas, QR Codes PNG
para impressão/embalagens e rastreamento de cliques/scans.
"""

from __future__ import annotations

import base64
import io
import logging
import urllib.parse
import uuid
from datetime import datetime, timezone
from flask import Blueprint, jsonify, redirect, request
from flask_login import current_user, login_required
import qrcode
from qrcode.image.pil import PilImage

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
growth_links_bp = Blueprint("growth_links", __name__, url_prefix="/saas/growth")


def _serialize(link: models.GrowthLink) -> dict:
    return {"id": link.id, "name": link.name, "phone": link.phone, "message": link.message or "",
            "tags": link.tags or [], "wa_url": link.wa_url, "short_url": link.short_url,
            "qr_code": link.qr_code, "clicks": link.clicks or 0,
            "created_at": link.created_at.isoformat() if link.created_at else None}


def _migrate_legacy_links(db, tenant_id: str) -> None:
    """One-way lazy migration from the previous JSON blob."""
    row = db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id, key="growth.links").first()
    if not row or not isinstance(row.value_json, list):
        return
    for item in row.value_json:
        link_id = item.get("id")
        if link_id and not db.get(models.GrowthLink, link_id):
            db.add(models.GrowthLink(
                id=link_id, tenant_id=tenant_id, name=item.get("name") or "Link WhatsApp",
                phone=item.get("phone") or "", message=item.get("message"), tags=item.get("tags") or [],
                wa_url=item.get("wa_url") or f"https://wa.me/{item.get('phone', '')}",
                short_url=item.get("short_url") or "", qr_code=item.get("qr_code"), clicks=item.get("clicks") or 0,
            ))
    db.delete(row)
    db.commit()


def _generate_qr_base64(url: str) -> str:
    """Gera QR code PNG e retorna como data URL base64."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    b64_str = base64.b64encode(buffered.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64_str}"


@growth_links_bp.route("/links", methods=["GET"])
@login_required
def list_links():
    """Lista todos os links e QR codes do tenant."""
    db = SessionLocal()
    try:
        _migrate_legacy_links(db, current_user.tenant_id)
        links = db.query(models.GrowthLink).filter_by(tenant_id=current_user.tenant_id).order_by(models.GrowthLink.created_at.desc()).all()
        return jsonify({"links": [_serialize(link) for link in links]})
    finally:
        db.close()


@growth_links_bp.route("/links", methods=["POST"])
@login_required
def create_link():
    """
    Cria um novo link WhatsApp com mensagem pré-definida e QR Code.
    Body: {"name": "Panfleto Loja", "phone": "5511999999999", "message": "Olá!", "tags": ["panfleto"]}
    """
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "Link WhatsApp").strip()
    raw_phone = str(body.get("phone") or "").strip()
    clean_phone = "".join(ch for ch in raw_phone if ch.isdigit())
    message = (body.get("message") or "").strip()
    tags = body.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    if not clean_phone or len(clean_phone) < 8:
        return jsonify({"error": "phone_required", "message": "Número de WhatsApp válido é obrigatório"}), 422

    link_id = f"gl_{uuid.uuid4().hex[:10]}"
    encoded_msg = urllib.parse.quote(message) if message else ""
    wa_url = f"https://wa.me/{clean_phone}" + (f"?text={encoded_msg}" if encoded_msg else "")

    # Host URL para o redirect tracking
    base_url = request.host_url.rstrip("/")
    short_url = f"{base_url}/saas/growth/r/{link_id}"

    qr_code_base64 = _generate_qr_base64(short_url)

    db = SessionLocal()
    try:
        link = models.GrowthLink(id=link_id, tenant_id=current_user.tenant_id, name=name,
            phone=clean_phone, message=message, tags=tags, wa_url=wa_url, short_url=short_url,
            qr_code=qr_code_base64, clicks=0)
        db.add(link)
        db.commit()
        db.refresh(link)
        return jsonify({"ok": True, "link": _serialize(link)}), 201
    finally:
        db.close()


@growth_links_bp.route("/links/<link_id>", methods=["DELETE"])
@login_required
def delete_link(link_id: str):
    """Remove um link do tenant."""
    db = SessionLocal()
    try:
        link = db.query(models.GrowthLink).filter_by(id=link_id, tenant_id=current_user.tenant_id).first()
        if not link:
            return jsonify({"error": "not_found"}), 404
        db.delete(link)
        db.commit()
        return jsonify({"ok": True, "message": "Link removido com sucesso."})
    finally:
        db.close()


@growth_links_bp.route("/r/<link_id>", methods=["GET"])
def redirect_growth_link(link_id: str):
    """Redirecionamento público para WhatsApp com incremento de clique."""
    db = SessionLocal()
    try:
        link = db.get(models.GrowthLink, link_id)
        if not link:
            return "Link não encontrado", 404
        target = link.wa_url or f"https://wa.me/{link.phone}"
        db.query(models.GrowthLink).filter_by(id=link_id).update(
            {models.GrowthLink.clicks: models.GrowthLink.clicks + 1}, synchronize_session=False,
        )
        db.commit()
        return redirect(target, code=302)
    except Exception as exc:
        logger.exception("[GROWTH_LINK] Erro no redirect: %s", exc)
        return "Erro ao redirecionar", 500
    finally:
        db.close()

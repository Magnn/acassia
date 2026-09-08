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


def _get_links(db, tenant_id: str) -> list[dict]:
    row = db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id, key="growth.links").first()
    raw = row.value_json if row and isinstance(row.value_json, list) else []
    return raw


def _save_links(db, tenant_id: str, links: list[dict]) -> None:
    row = db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id, key="growth.links").first()
    if row:
        row.value_json = links
    else:
        db.add(models.TenantFlowVariable(tenant_id=tenant_id, key="growth.links", value_json=links))
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
        links = _get_links(db, current_user.tenant_id)
        return jsonify({"links": links})
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

    new_link = {
        "id": link_id,
        "name": name,
        "phone": clean_phone,
        "message": message,
        "tags": tags,
        "wa_url": wa_url,
        "short_url": short_url,
        "qr_code": qr_code_base64,
        "clicks": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    db = SessionLocal()
    try:
        links = _get_links(db, current_user.tenant_id)
        links.insert(0, new_link)
        _save_links(db, current_user.tenant_id, links)
        return jsonify({"ok": True, "link": new_link}), 201
    finally:
        db.close()


@growth_links_bp.route("/links/<link_id>", methods=["DELETE"])
@login_required
def delete_link(link_id: str):
    """Remove um link do tenant."""
    db = SessionLocal()
    try:
        links = _get_links(db, current_user.tenant_id)
        filtered = [l for l in links if l.get("id") != link_id]
        if len(filtered) != len(links):
            _save_links(db, current_user.tenant_id, filtered)
            return jsonify({"ok": True, "message": "Link removido com sucesso."})
        return jsonify({"error": "not_found"}), 404
    finally:
        db.close()


@growth_links_bp.route("/r/<link_id>", methods=["GET"])
def redirect_growth_link(link_id: str):
    """Redirecionamento público para WhatsApp com incremento de clique."""
    db = SessionLocal()
    try:
        # Busca em todos os tenants onde growth.links existe
        rows = db.query(models.TenantFlowVariable).filter_by(key="growth.links").all()
        for row in rows:
            links = row.value_json if isinstance(row.value_json, list) else []
            for item in links:
                if item.get("id") == link_id:
                    # Incrementa cliques
                    item["clicks"] = (item.get("clicks") or 0) + 1
                    row.value_json = list(links)
                    db.commit()

                    target = item.get("wa_url") or f"https://wa.me/{item.get('phone')}"
                    return redirect(target, code=302)

        return "Link não encontrado", 404
    except Exception as exc:
        logger.exception("[GROWTH_LINK] Erro no redirect: %s", exc)
        return "Erro ao redirecionar", 500
    finally:
        db.close()

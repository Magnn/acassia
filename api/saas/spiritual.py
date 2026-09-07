"""
Perfil espiritual por lead (Frente 4.3-4.12).

Combina mapa astral lite + numerologia + interpretacao Gemini.
Cache em LeadNatalChart e LeadNumerology — recalcula on-demand.

Endpoints:
    GET    /saas/spiritual/leads/<lead_id>         — profile completo (compute se faltar)
    POST   /saas/spiritual/leads/<lead_id>/natal   — upsert natal (recompute) + opcional birth_time/place
    POST   /saas/spiritual/leads/<lead_id>/natal/interpret  — gera/regen interpretacao (focus opcional)
    POST   /saas/spiritual/leads/<lead_id>/numerology  — recompute numerologia
    POST   /saas/spiritual/leads/<lead_id>/numerology/interpret — gera interpretacao
    POST   /saas/spiritual/leads/<lead_id>/send-summary  — envia resumo via WhatsApp
"""

from __future__ import annotations

import logging
from datetime import date as DateT, datetime, time as TimeT, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
spiritual_bp = Blueprint("saas_spiritual", __name__, url_prefix="/saas/spiritual")


# ─── Helpers ──────────────────────────────────────────────────────────


def _get_lead_or_404(db, lead_id: int):
    lead = db.query(models.Lead).filter_by(
        id=lead_id, tenant_id=current_user.tenant_id,
    ).first()
    if not lead:
        return None
    return lead


def _serialize_natal(row: models.LeadNatalChart | None) -> dict | None:
    if row is None:
        return None
    return {
        "lead_id": row.lead_id,
        "birth_date": row.birth_date.isoformat() if row.birth_date else None,
        "birth_time": row.birth_time,
        "birth_place": row.birth_place,
        "lat": row.birth_lat, "lon": row.birth_lon,
        "timezone_offset": row.timezone_offset,
        "chart": row.chart_json,
        "interpretation": row.interpretation_text,
        "interpretation_focus": row.interpretation_focus,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        "interpreted_at": row.interpreted_at.isoformat() if row.interpreted_at else None,
    }


def _serialize_numerology(row: models.LeadNumerology | None) -> dict | None:
    if row is None:
        return None
    return {
        "lead_id": row.lead_id,
        "full_name": row.full_name,
        "birth_date": row.birth_date.isoformat() if row.birth_date else None,
        "life_path": row.life_path,
        "expression": row.expression,
        "soul": row.soul,
        "components": row.components,
        "interpretation": row.interpretation_text,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        "interpreted_at": row.interpreted_at.isoformat() if row.interpreted_at else None,
    }


def _parse_birth_time(t: str | None) -> TimeT | None:
    if not t or not t.strip():
        return None
    try:
        h, m = t.strip().split(":")[:2]
        return TimeT(int(h), int(m))
    except Exception:
        return None


# ─── Profile completo ─────────────────────────────────────────────────


@spiritual_bp.route("/leads/<int:lead_id>", methods=["GET"])
@login_required
def get_profile(lead_id: int):
    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        natal = db.query(models.LeadNatalChart).filter_by(lead_id=lead_id).first()
        numero = db.query(models.LeadNumerology).filter_by(lead_id=lead_id).first()

        return jsonify({
            "lead": {
                "id": lead.id,
                "nome": lead.nome,
                "telefone": lead.telefone,
                "birth_date": lead.birth_date.isoformat() if lead.birth_date else None,
                "signo": lead.signo,
            },
            "natal": _serialize_natal(natal),
            "numerology": _serialize_numerology(numero),
        })
    finally:
        db.close()


# ─── Natal chart ──────────────────────────────────────────────────────


@spiritual_bp.route("/leads/<int:lead_id>/natal", methods=["POST"])
@login_required
def compute_natal(lead_id: int):
    """Recomputa natal chart. Body opcional: birth_time, birth_place, lat, lon, timezone_offset."""
    import astrology_lite

    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404
        if not lead.birth_date:
            return jsonify({"error": "lead_missing_birth_date"}), 422

        # Atualiza dados de nascimento se vierem no body
        bt_str = body.get("birth_time")
        bt = _parse_birth_time(bt_str)
        place = (body.get("birth_place") or "").strip() or None
        lat = body.get("lat")
        lon = body.get("lon")
        tz_off = body.get("timezone_offset")

        try:
            tz_off_f = float(tz_off) if tz_off is not None else -3.0
        except (TypeError, ValueError):
            return jsonify({"error": "timezone_offset_invalid"}), 422

        if lat is not None:
            try:
                lat = float(lat)
            except (TypeError, ValueError):
                return jsonify({"error": "lat_invalid"}), 422
        if lon is not None:
            try:
                lon = float(lon)
            except (TypeError, ValueError):
                return jsonify({"error": "lon_invalid"}), 422

        chart = astrology_lite.natal_chart_lite(
            lead.birth_date, bt,
            lat=lat, lon=lon,
            timezone_offset_hours=tz_off_f,
        )

        # Atualiza signo do lead (acerto fino) se mudou
        if chart.get("sun") and chart["sun"].get("sign"):
            lead.signo = chart["sun"]["sign"]

        natal = db.query(models.LeadNatalChart).filter_by(lead_id=lead_id).first()
        if natal is None:
            natal = models.LeadNatalChart(
                lead_id=lead_id,
                tenant_id=current_user.tenant_id,
            )
            db.add(natal)

        natal.birth_date = lead.birth_date
        natal.birth_time = bt_str if bt else None
        natal.birth_place = place
        natal.birth_lat = lat
        natal.birth_lon = lon
        natal.timezone_offset = tz_off_f
        natal.chart_json = chart
        natal.computed_at = datetime.now(timezone.utc)
        # Interpretacao expira em recompute
        natal.interpretation_text = None
        natal.interpretation_focus = None
        natal.interpreted_at = None

        db.commit()
        return jsonify({"ok": True, "natal": _serialize_natal(natal)})
    finally:
        db.close()


@spiritual_bp.route("/leads/<int:lead_id>/natal/interpret", methods=["POST"])
@login_required
def interpret_natal(lead_id: int):
    import astrology_lite

    body = request.get_json(silent=True) or {}
    focus = (body.get("focus") or "geral").strip().lower()
    if focus not in {"geral", "amor", "carreira", "familia"}:
        focus = "geral"

    db = SessionLocal()
    try:
        natal = db.query(models.LeadNatalChart).filter_by(lead_id=lead_id).first()
        if not natal or not natal.chart_json:
            return jsonify({"error": "natal_not_computed"}), 404
        # Tenant guard
        if natal.tenant_id != current_user.tenant_id:
            return jsonify({"error": "forbidden"}), 403

        text = astrology_lite.interpret_chart(natal.chart_json, focus=focus)
        natal.interpretation_text = text
        natal.interpretation_focus = focus
        natal.interpreted_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "interpretation": text, "focus": focus})
    finally:
        db.close()


# ─── Numerologia ─────────────────────────────────────────────────────


@spiritual_bp.route("/leads/<int:lead_id>/numerology", methods=["POST"])
@login_required
def compute_numerology(lead_id: int):
    """Recomputa numerologia (life_path/expression/soul) com nome+birth_date."""
    import numerology

    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        # Nome: usa o body ou cai pro do lead
        name = (body.get("full_name") or lead.nome or "").strip() or None
        if not name and not lead.birth_date:
            return jsonify({"error": "missing_name_and_birth_date"}), 422

        nums = numerology.compute_full(name, lead.birth_date)
        components = {
            "life_path_meaning": nums.get("life_path_meaning"),
            "expression_meaning": nums.get("expression_meaning"),
            "soul_meaning": nums.get("soul_meaning"),
        }

        row = db.query(models.LeadNumerology).filter_by(lead_id=lead_id).first()
        if row is None:
            row = models.LeadNumerology(
                lead_id=lead_id,
                tenant_id=current_user.tenant_id,
            )
            db.add(row)

        row.full_name = name[:300] if name else None
        row.birth_date = lead.birth_date
        row.life_path = nums.get("life_path")
        row.expression = nums.get("expression")
        row.soul = nums.get("soul")
        row.components = components
        row.computed_at = datetime.now(timezone.utc)
        row.interpretation_text = None
        row.interpreted_at = None

        db.commit()
        return jsonify({"ok": True, "numerology": _serialize_numerology(row)})
    finally:
        db.close()


@spiritual_bp.route("/leads/<int:lead_id>/numerology/interpret", methods=["POST"])
@login_required
def interpret_numerology_route(lead_id: int):
    import astrology_lite

    db = SessionLocal()
    try:
        row = db.query(models.LeadNumerology).filter_by(lead_id=lead_id).first()
        if not row:
            return jsonify({"error": "numerology_not_computed"}), 404
        if row.tenant_id != current_user.tenant_id:
            return jsonify({"error": "forbidden"}), 403

        nums = {
            "life_path": row.life_path,
            "life_path_meaning": (row.components or {}).get("life_path_meaning"),
            "expression": row.expression,
            "expression_meaning": (row.components or {}).get("expression_meaning"),
            "soul": row.soul,
            "soul_meaning": (row.components or {}).get("soul_meaning"),
        }
        text = astrology_lite.interpret_numerology(nums, name=row.full_name)
        row.interpretation_text = text
        row.interpreted_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "interpretation": text})
    finally:
        db.close()


# ─── Send summary via WhatsApp ────────────────────────────────────────


@spiritual_bp.route("/extract-birth-date", methods=["POST"])
@login_required
def extract_birth_date():
    """
    Extrai data de nascimento de mensagem livre (Frente 4.25).

    Body: {text: "23 de maio de 1986", lead_id?: int, persist?: bool, prefer_gemini?: bool}

    Se persist=True e lead_id fornecido e parse confiante (date+year+month+day),
    grava lead.birth_date e calcula signo automaticamente.

    Retorna sempre o resultado do parse (mesmo parcial), pra UI ou flow node
    decidir qual mensagem de clarificacao mandar.
    """
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    lead_id = body.get("lead_id")
    persist = bool(body.get("persist"))
    prefer_gemini = bool(body.get("prefer_gemini"))

    if not text:
        return jsonify({"error": "text_required"}), 422

    try:
        import birthdate_extractor
    except Exception as exc:
        return jsonify({"error": "extractor_unavailable", "message": str(exc)}), 500

    result = birthdate_extractor.extract_birth_date(text, prefer_gemini=prefer_gemini)
    response = {
        "date": result.date.isoformat() if result.date else None,
        "year": result.year,
        "month": result.month,
        "day": result.day,
        "confidence": round(result.confidence, 3),
        "source": result.source,
        "needs_clarification": result.needs_clarification,
        "clarification_question": result.clarification_question,
        "parse_error": result.parse_error,
        "confirmation_message": birthdate_extractor.confirmation_message(result),
    }

    persisted = False
    if persist and lead_id and result.date:
        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter_by(
                id=int(lead_id), tenant_id=current_user.tenant_id,
            ).first()
            if lead:
                lead.birth_date = result.date
                # Calcula signo automaticamente
                try:
                    import horoscope
                    signo = horoscope.compute_sun_sign(result.date)
                    if signo:
                        lead.signo = signo
                        response["computed_sign"] = signo
                except Exception as exc:
                    logger.warning("[spiritual.extract_birth_date] signo falhou: %s", exc)
                db.commit()
                persisted = True
                response["persisted"] = True
        finally:
            db.close()

    if not persisted:
        response["persisted"] = False

    return jsonify(response)


@spiritual_bp.route("/leads/<int:lead_id>/send-summary", methods=["POST"])
@login_required
def send_summary(lead_id: int):
    """Monta texto curto com sun/moon/life_path + envia via WhatsApp."""
    db = SessionLocal()
    try:
        lead = _get_lead_or_404(db, lead_id)
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        natal = db.query(models.LeadNatalChart).filter_by(lead_id=lead_id).first()
        numero = db.query(models.LeadNumerology).filter_by(lead_id=lead_id).first()

        lines = [f"✦ {lead.nome or 'Querida'}, seu perfil espiritual:"]
        if natal and natal.chart_json:
            chart = natal.chart_json
            if chart.get("sun"): lines.append(f"  Sol em {chart['sun']['sign']}")
            if chart.get("moon"): lines.append(f"  Lua em {chart['moon']['sign']}")
            if chart.get("asc"): lines.append(f"  Ascendente em {chart['asc']['sign']}")
        if numero:
            if numero.life_path: lines.append(f"  Numero da vida: {numero.life_path}")
            if numero.expression: lines.append(f"  Expressao: {numero.expression}")
            if numero.soul: lines.append(f"  Alma: {numero.soul}")
        lines.append("")
        if natal and natal.interpretation_text:
            lines.append(natal.interpretation_text)
        elif numero and numero.interpretation_text:
            lines.append(numero.interpretation_text)

        msg = "\n".join(lines).strip()
        if not msg:
            return jsonify({"error": "nothing_to_send"}), 422

        try:
            import horoscope
            client = horoscope._get_whatsapp_client(current_user.tenant_id)
            if client is None:
                return jsonify({"error": "whatsapp_unavailable"}), 502
            client.enviar_mensagem(lead.telefone, msg, formato="texto")
        except Exception as exc:
            return jsonify({"error": "send_failed", "message": str(exc)[:200]}), 502

        # Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="spiritual.summary.sent",
                target_type="lead",
                target_id=str(lead.id),
                payload={"chars": len(msg)},
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({"ok": True, "preview": msg[:500]})
    finally:
        db.close()

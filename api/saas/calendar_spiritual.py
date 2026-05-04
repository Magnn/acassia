"""
Calendario espiritual (Frente 4.22).

Endpoints:
    GET  /saas/calendar                       — datas no range com filtro de tradicao
    GET  /saas/calendar/today                 — eventos hoje + proximos 14 dias
    POST /saas/calendar/dates                 — cria data custom do tenant
    DELETE /saas/calendar/dates/<id>          — remove data custom
    POST /saas/calendar/<id>/suggest-message  — Gemini sugere mensagem do dia
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date as DateT, datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
calendar_bp = Blueprint("saas_calendar", __name__, url_prefix="/saas/calendar")


VALID_TRADITIONS = {"crista", "afro", "paga", "astronomica", "secular"}
SUGGEST_CACHE: dict[tuple[str, int], tuple[float, dict]] = {}
SUGGEST_TTL_SEC = 21600  # 6 horas


def _serialize_date(d: models.SpiritualDate) -> dict:
    return {
        "id": d.id,
        "tradition": d.tradition,
        "name": d.name,
        "description": d.description,
        "recurring": d.recurring,
        "month": d.month,
        "day": d.day,
        "fixed_date": d.fixed_date.isoformat() if d.fixed_date else None,
        "is_custom": d.tenant_id is not None,
    }


def _ocurrences_in_range(d: models.SpiritualDate, from_date: DateT, to_date: DateT) -> list[DateT]:
    """Retorna lista de datas concretas que esta entrada cai no range pedido."""
    occs: list[DateT] = []
    if d.recurring == "annual_fixed" and d.month and d.day:
        for year in range(from_date.year, to_date.year + 1):
            try:
                occ = DateT(year, d.month, d.day)
            except ValueError:
                continue
            if from_date <= occ <= to_date:
                occs.append(occ)
    elif d.recurring == "annual_movable":
        # V1: nao calculamos data movel — retorna vazia (UI exibe so quando admin marcar fixed_date)
        if d.fixed_date and from_date <= d.fixed_date <= to_date:
            occs.append(d.fixed_date)
    elif d.fixed_date:
        if from_date <= d.fixed_date <= to_date:
            occs.append(d.fixed_date)
    return occs


def _query_dates(db, *, traditions: list[str] | None, tenant_id: str):
    q = db.query(models.SpiritualDate).filter(
        or_(
            models.SpiritualDate.tenant_id.is_(None),
            models.SpiritualDate.tenant_id == tenant_id,
        )
    )
    if traditions:
        q = q.filter(models.SpiritualDate.tradition.in_(traditions))
    return q.all()


# ─── Listing ──────────────────────────────────────────────────────────


@calendar_bp.route("", methods=["GET"])
@login_required
def list_range():
    """
    Range de datas + lunar opcional.
    Query: ?from=YYYY-MM-DD&to=YYYY-MM-DD&traditions=afro,crista&include_lunar=1
    Default: mes corrente +/- 30 dias.
    """
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    tradition_filter = (request.args.get("traditions") or "").strip().lower()
    include_lunar = request.args.get("include_lunar", "1") in ("1", "true", "yes")

    today = DateT.today()
    if from_str:
        try:
            from_date = DateT.fromisoformat(from_str)
        except ValueError:
            return jsonify({"error": "from_invalid"}), 422
    else:
        from_date = today.replace(day=1)

    if to_str:
        try:
            to_date = DateT.fromisoformat(to_str)
        except ValueError:
            return jsonify({"error": "to_invalid"}), 422
    else:
        to_date = today + timedelta(days=60)

    if (to_date - from_date).days > 730:
        return jsonify({"error": "range_too_large", "max_days": 730}), 422

    traditions = None
    if tradition_filter:
        traditions = [
            t.strip() for t in tradition_filter.split(",")
            if t.strip() in VALID_TRADITIONS
        ]

    db = SessionLocal()
    try:
        rows = _query_dates(db, traditions=traditions, tenant_id=current_user.tenant_id)

        events: list[dict] = []
        for d in rows:
            for occ in _ocurrences_in_range(d, from_date, to_date):
                events.append({
                    "date": occ.isoformat(),
                    "tradition": d.tradition,
                    "name": d.name,
                    "description": d.description,
                    "is_custom": d.tenant_id is not None,
                    "id": d.id,
                })

        if include_lunar:
            try:
                import lunar
                # Range pode ser longo; consulta dia a dia (rápido o suficiente até 730d).
                cur = from_date
                while cur <= to_date:
                    info = lunar.phase_for_date(datetime(cur.year, cur.month, cur.day, 12, 0, tzinfo=timezone.utc))
                    if info.get("is_special") or info["phase_name"] in ("nova", "cheia"):
                        events.append({
                            "date": cur.isoformat(),
                            "tradition": "astronomica",
                            "name": (info.get("special_label") or info["phase_name"]).capitalize() + " Lua",
                            "description": f"Fase {info['phase_name']} ({info.get('illumination_pct', 0)}% iluminada).",
                            "is_custom": False,
                            "id": None,
                        })
                    cur += timedelta(days=1)
            except Exception as exc:
                logger.warning("[calendar.lunar] falha: %s", exc)

        events.sort(key=lambda e: e["date"])
        return jsonify({
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "events": events,
            "total": len(events),
        })
    finally:
        db.close()


@calendar_bp.route("/today", methods=["GET"])
@login_required
def today_view():
    """Eventos de hoje + proximos 14 dias."""
    today = DateT.today()
    horizon = today + timedelta(days=14)

    db = SessionLocal()
    try:
        rows = _query_dates(db, traditions=None, tenant_id=current_user.tenant_id)
        events: list[dict] = []
        for d in rows:
            for occ in _ocurrences_in_range(d, today, horizon):
                events.append({
                    "date": occ.isoformat(),
                    "days_from_today": (occ - today).days,
                    "tradition": d.tradition,
                    "name": d.name,
                    "description": d.description,
                    "id": d.id,
                })

        # Lua de hoje
        try:
            import lunar
            info = lunar.phase_for_date()
            events.append({
                "date": today.isoformat(),
                "days_from_today": 0,
                "tradition": "astronomica",
                "name": f"Lua {info['phase_name']}",
                "description": f"{info.get('illumination_pct', 0)}% iluminada{' · ' + info['special_label'] if info.get('special_label') else ''}",
                "id": None,
                "lunar": info,
            })
        except Exception:
            pass

        events.sort(key=lambda e: (e["date"], e.get("name", "")))
        return jsonify({
            "today": today.isoformat(),
            "horizon": horizon.isoformat(),
            "events": events,
        })
    finally:
        db.close()


# ─── CRUD custom dates ────────────────────────────────────────────────


@calendar_bp.route("/dates", methods=["POST"])
@login_required
def create_custom_date():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    tradition = (body.get("tradition") or "secular").strip().lower()
    month = body.get("month")
    day = body.get("day")
    fixed_date_str = body.get("fixed_date")
    description = (body.get("description") or "").strip() or None

    if not name or len(name) < 3:
        return jsonify({"error": "name_too_short"}), 422
    if tradition not in VALID_TRADITIONS:
        return jsonify({"error": "tradition_invalid", "valid": sorted(VALID_TRADITIONS)}), 422

    fixed_date = None
    if fixed_date_str:
        try:
            fixed_date = DateT.fromisoformat(fixed_date_str)
        except ValueError:
            return jsonify({"error": "fixed_date_invalid"}), 422

    if fixed_date is None:
        try:
            month = int(month) if month else None
            day = int(day) if day else None
            if month is None or day is None or not (1 <= month <= 12) or not (1 <= day <= 31):
                return jsonify({"error": "month_day_required"}), 422
        except (TypeError, ValueError):
            return jsonify({"error": "month_day_invalid"}), 422

    db = SessionLocal()
    try:
        d = models.SpiritualDate(
            tradition=tradition,
            name=name[:200],
            description=description,
            recurring="fixed" if fixed_date else "annual_fixed",
            month=month,
            day=day,
            fixed_date=fixed_date,
            tenant_id=current_user.tenant_id,
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        return jsonify({"ok": True, "date": _serialize_date(d)}), 201
    finally:
        db.close()


@calendar_bp.route("/dates/<int:date_id>", methods=["DELETE"])
@login_required
def delete_custom_date(date_id: int):
    db = SessionLocal()
    try:
        d = db.query(models.SpiritualDate).filter_by(
            id=date_id, tenant_id=current_user.tenant_id,
        ).first()
        if not d:
            return jsonify({"error": "not_found_or_global"}), 404
        db.delete(d)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ─── Sugestao de mensagem do dia ──────────────────────────────────────


@calendar_bp.route("/<int:date_id>/suggest-message", methods=["POST"])
@login_required
def suggest_message(date_id: int):
    cache_key = (current_user.tenant_id, date_id)
    cached = SUGGEST_CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < SUGGEST_TTL_SEC:
        return jsonify({"ok": True, "suggestion": cached[1], "cached": True})

    try:
        import quota
        allowed, _, _ = quota.consume_quota(
            current_user.tenant_id, "gemini_tokens_month", 1500,
        )
        if not allowed:
            return jsonify({"error": "quota_exceeded"}), 402
    except Exception:
        pass

    db = SessionLocal()
    try:
        d = db.query(models.SpiritualDate).filter(
            models.SpiritualDate.id == date_id,
            or_(
                models.SpiritualDate.tenant_id.is_(None),
                models.SpiritualDate.tenant_id == current_user.tenant_id,
            ),
        ).first()
        if not d:
            return jsonify({"error": "not_found"}), 404

        suggestion = _generate_message_for_date(d)
        SUGGEST_CACHE[cache_key] = (time.time(), suggestion)
        return jsonify({"ok": True, "suggestion": suggestion, "cached": False})
    finally:
        db.close()


def _generate_message_for_date(d: models.SpiritualDate) -> dict:
    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            raise RuntimeError("personalizer_unavailable")
        prompt = (
            f"Voce e meumisterio mistica respondendo no WhatsApp. "
            f"Hoje e dia de {d.name} ({d.tradition}). "
            f"Contexto: {d.description or '(sem descricao adicional)'}\n\n"
            "Gere 3 sugestoes de mensagem curtas (max 250 chars cada), em pt-BR, "
            "tom acolhedor e mistico, para enviar aos leads conectando o dia com "
            "uma mensagem espiritual simples e pratica.\n"
            "Retorne JSON {\"messages\": [\"...\", \"...\", \"...\"]}. Apenas o JSON."
        )
        resp = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 600, "temperature": 0.85,
                    "response_mime_type": "application/json"},
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        msgs = parsed.get("messages") if isinstance(parsed, dict) else None
        if not isinstance(msgs, list):
            raise ValueError("invalid_format")
        return {
            "messages": [(m or "").strip()[:280] for m in msgs[:3] if m],
            "source": "gemini",
        }
    except Exception as exc:
        logger.warning("[calendar.suggest] fallback: %s", exc)
        return {
            "messages": [
                f"Hoje e {d.name}. {d.description or 'Energia especial pra parar e respirar.'}",
                f"Aproveite a vibracao de {d.name} pra acender uma vela de intencao.",
                f"Em {d.name}, mande luz pra quem voce ama. Pequeno gesto, grande efeito.",
            ],
            "source": "fallback",
        }

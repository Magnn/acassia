"""
Daily horoscope automation endpoints (Frente 4.13).

Tenant config + manual run + listing per-sign cache.

Endpoints:
    GET    /saas/horoscope/config            — config do tenant
    PATCH  /saas/horoscope/config            — atualiza config
    GET    /saas/horoscope/today             — 12 signos do dia (cache + gera se faltar)
    POST   /saas/horoscope/preview/<signo>   — gera/forca regen pra preview
    POST   /saas/horoscope/run-now           — dispara fanout agora (override hour)
    GET    /saas/horoscope/deliveries        — historico recente
    POST   /saas/horoscope/backfill-signs    — calcula signo dos leads via birth_date
"""

from __future__ import annotations

import logging
from datetime import date as DateT, datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from db import models
from db.database import SessionLocal

import horoscope as horoscope_engine


logger = logging.getLogger(__name__)
horoscope_bp = Blueprint("saas_horoscope", __name__, url_prefix="/saas/horoscope")


_VALID_SEGMENTS = {"all", "hot", "warm", "hot_warm"}
_VALID_SOURCES = {"gemini", "manual"}


def _serialize_config(cfg: models.HoroscopeAutomation) -> dict:
    return {
        "id": cfg.id,
        "enabled": cfg.enabled,
        "send_hour_local": cfg.send_hour_local,
        "timezone": cfg.timezone,
        "source": cfg.source,
        "segment_filter": cfg.segment_filter,
        "custom_prefix": cfg.custom_prefix,
        "last_run_date": cfg.last_run_date.isoformat() if cfg.last_run_date else None,
        "total_sent": cfg.total_sent,
    }


def _get_or_create_config(db, tenant_id: str) -> models.HoroscopeAutomation:
    cfg = db.query(models.HoroscopeAutomation).filter_by(tenant_id=tenant_id).first()
    if cfg:
        return cfg
    cfg = models.HoroscopeAutomation(
        tenant_id=tenant_id,
        enabled=False, send_hour_local=7,
        timezone="America/Sao_Paulo",
        source="gemini", segment_filter="all",
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


@horoscope_bp.route("/config", methods=["GET"])
@login_required
def get_config():
    db = SessionLocal()
    try:
        cfg = _get_or_create_config(db, current_user.tenant_id)
        # Estatisticas: leads opt-in + total candidates
        candidates = db.query(func.count(models.Lead.id)).filter(
            models.Lead.tenant_id == current_user.tenant_id,
            models.Lead.signo.isnot(None),
            models.Lead.opt_out == False,  # noqa: E712
        ).scalar() or 0

        opt_in_count = db.query(func.count(models.Lead.id)).filter(
            models.Lead.tenant_id == current_user.tenant_id,
            models.Lead.signo.isnot(None),
            models.Lead.opt_out == False,  # noqa: E712
            func.json_extract(models.Lead.consents, "$.daily_horoscope") == 1,  # SQLite
        ).scalar() or 0

        return jsonify({
            "config": _serialize_config(cfg),
            "stats": {
                "candidates_with_sign": int(candidates),
                "opted_in": int(opt_in_count),
            },
        })
    finally:
        db.close()


@horoscope_bp.route("/config", methods=["PATCH"])
@login_required
def update_config():
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        cfg = _get_or_create_config(db, current_user.tenant_id)

        if "enabled" in body:
            cfg.enabled = bool(body["enabled"])
        if "send_hour_local" in body:
            try:
                hr = int(body["send_hour_local"])
                if 0 <= hr <= 23:
                    cfg.send_hour_local = hr
            except (TypeError, ValueError):
                return jsonify({"error": "send_hour_local_invalid"}), 422
        if "timezone" in body:
            tz = (body["timezone"] or "").strip()
            if tz:
                cfg.timezone = tz[:60]
        if "source" in body:
            src = (body["source"] or "").strip().lower()
            if src not in _VALID_SOURCES:
                return jsonify({"error": "source_invalid", "valid": sorted(_VALID_SOURCES)}), 422
            cfg.source = src
        if "segment_filter" in body:
            seg = (body["segment_filter"] or "").strip().lower()
            if seg not in _VALID_SEGMENTS:
                return jsonify({"error": "segment_invalid", "valid": sorted(_VALID_SEGMENTS)}), 422
            cfg.segment_filter = seg
        if "custom_prefix" in body:
            prefix = (body["custom_prefix"] or "").strip()
            cfg.custom_prefix = prefix[:1000] or None

        cfg.updated_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "config": _serialize_config(cfg)})
    finally:
        db.close()


@horoscope_bp.route("/today", methods=["GET"])
@login_required
def today_all_signs():
    """Retorna texto cacheado pros 12 signos. Gera se faltar (source=gemini)."""
    db = SessionLocal()
    try:
        cfg = _get_or_create_config(db, current_user.tenant_id)
        today = DateT.today()
        rows = horoscope_engine.ensure_all_signs_for_date(today, source=cfg.source)
        return jsonify({
            "date": today.isoformat(),
            "signs": [{"signo": s, "text": rows.get(s, "")} for s in horoscope_engine.ALL_SIGNS],
        })
    finally:
        db.close()


@horoscope_bp.route("/preview/<signo>", methods=["POST"])
@login_required
def preview_sign(signo: str):
    """Gera/regen para um signo (force=true regera mesmo se cacheado)."""
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force"))
    if signo not in horoscope_engine.ALL_SIGNS:
        return jsonify({"error": "signo_invalid", "valid": horoscope_engine.ALL_SIGNS}), 422

    db = SessionLocal()
    try:
        today = DateT.today()
        if force:
            db.query(models.DailyHoroscope).filter_by(
                date=today, signo=signo, lang="pt-BR",
            ).delete()
            db.commit()

        cfg = _get_or_create_config(db, current_user.tenant_id)
        row = horoscope_engine.ensure_daily_text(
            signo, today, source=cfg.source, db_session=db,
        )
        return jsonify({
            "signo": row.signo,
            "text": row.text,
            "source": row.source,
            "generated_by": row.generated_by,
            "date": row.date.isoformat(),
        })
    finally:
        db.close()


@horoscope_bp.route("/run-now", methods=["POST"])
@login_required
def run_now():
    """Dispara fanout imediato (override do horario configurado)."""
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run"))

    db = SessionLocal()
    try:
        cfg = _get_or_create_config(db, current_user.tenant_id)
        if not cfg.enabled and not dry_run:
            return jsonify({"error": "automation_disabled"}), 409
    finally:
        db.close()

    stats = horoscope_engine.fanout_for_tenant(
        current_user.tenant_id,
        DateT.today(),
        dry_run=dry_run,
    )
    return jsonify({"ok": True, "dry_run": dry_run, "stats": stats})


@horoscope_bp.route("/deliveries", methods=["GET"])
@login_required
def deliveries():
    days = int(request.args.get("days", 7))
    days = max(1, min(days, 60))
    cutoff = DateT.today() - timedelta(days=days)

    db = SessionLocal()
    try:
        rows = db.query(models.HoroscopeDelivery).filter(
            models.HoroscopeDelivery.tenant_id == current_user.tenant_id,
            models.HoroscopeDelivery.date >= cutoff,
        ).order_by(models.HoroscopeDelivery.sent_at.desc()).limit(500).all()

        # Resumo
        summary = db.query(
            models.HoroscopeDelivery.status,
            func.count(models.HoroscopeDelivery.id),
        ).filter(
            models.HoroscopeDelivery.tenant_id == current_user.tenant_id,
            models.HoroscopeDelivery.date >= cutoff,
        ).group_by(models.HoroscopeDelivery.status).all()

        return jsonify({
            "days": days,
            "summary": {status: count for status, count in summary},
            "deliveries": [
                {
                    "id": r.id,
                    "lead_id": r.lead_id,
                    "date": r.date.isoformat(),
                    "signo": r.signo,
                    "status": r.status,
                    "error_message": r.error_message,
                    "sent_at": r.sent_at.isoformat(),
                } for r in rows
            ],
        })
    finally:
        db.close()


@horoscope_bp.route("/backfill-signs", methods=["POST"])
@login_required
def backfill_signs():
    updated = horoscope_engine.backfill_signs_for_tenant(current_user.tenant_id)
    return jsonify({"ok": True, "updated": updated})

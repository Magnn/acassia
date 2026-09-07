"""
Lunar phase calculator (Frente 4.1).

Algoritmo de aproximação simples (Conway, ±0.5 dia precisão):
    - Reference new moon: 2000-01-06 18:14 UTC
    - Synodic period: 29.53059 dias
    - Phase = (days_since_reference % synodic) / synodic

Pra precisão astronômica real, usar pyswisseph ou ephem em V2.

API:
    phase_for_date(date) → dict {phase_name, illumination_pct, is_special, special_label}
    next_phase(phase_name, from_date) → datetime do próximo
    seed_calendar(months_forward=12) → preenche tabela lunar_phases

Phases:
    nova         (0-1.85% illumination)
    crescente    (1.85-49%)
    cheia        (>= 99%)
    minguante    (49-99% decrescente)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


_REFERENCE_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_SYNODIC_PERIOD_DAYS = 29.53059


def _phase_age_days(date: datetime) -> float:
    """Idade da lua em dias desde nova lua mais recente."""
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    diff = (date - _REFERENCE_NEW_MOON).total_seconds() / 86400.0
    return diff % _SYNODIC_PERIOD_DAYS


def _phase_name_from_age(age: float, prev_age: float | None = None) -> str:
    """
    Mapeia idade → nome da fase.
        0-1.85 days   → nova
        1.85-7.4      → crescente
        7.4-14.77     → crescente (gibosa)
        14.77-16.62   → cheia
        16.62-22.15   → minguante (gibosa)
        22.15-27.68   → minguante
        27.68-29.53   → nova approaching
    """
    if age < 1.85 or age > 27.68:
        return "nova"
    if 14.0 < age < 15.5:  # ~ apex full moon
        return "cheia"
    if age < 14.77:
        return "crescente"
    return "minguante"


def _illumination_pct(age: float) -> float:
    """% iluminada (0-100). Aproximação cosseno simples."""
    phase_angle = 2 * math.pi * age / _SYNODIC_PERIOD_DAYS
    illum = (1 - math.cos(phase_angle)) / 2
    return round(illum * 100, 1)


def _is_special_event(date: datetime) -> tuple[bool, str | None]:
    """
    Detecta eventos lunares especiais. Heurística simples por enquanto.
    V2: integrar com tabela de eclipses pré-calculada.
    """
    age = _phase_age_days(date)
    # Super lua: lua cheia próxima do perigeu (heurística simples — não é precisa)
    # Por enquanto, marca apenas lua cheia + lua nova como "especiais"
    if 14.5 < age < 15.5:
        return True, "Lua Cheia"
    if age < 0.5 or age > 29.0:
        return True, "Lua Nova"
    return False, None


def phase_for_date(date: datetime | None = None) -> dict:
    """
    Calcula fase lunar pra uma data. Retorna dict completo.
    """
    if date is None:
        date = datetime.now(timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)

    age = _phase_age_days(date)
    phase_name = _phase_name_from_age(age)
    illumination = _illumination_pct(age)
    is_special, label = _is_special_event(date)

    return {
        "date": date.strftime("%Y-%m-%d"),
        "phase_name": phase_name,
        "illumination_pct": illumination,
        "age_days": round(age, 2),
        "is_special": is_special,
        "special_label": label,
        "emoji": _phase_emoji(phase_name, age),
    }


def _phase_emoji(phase_name: str, age: float) -> str:
    if phase_name == "nova":
        return "🌑"
    if phase_name == "cheia":
        return "🌕"
    if phase_name == "crescente":
        if age < 7.4:
            return "🌒"
        return "🌔"
    # minguante
    if age < 22.15:
        return "🌖"
    return "🌘"


def next_phase(target_phase: str, from_date: datetime | None = None) -> datetime:
    """
    Encontra a próxima ocorrência de uma fase específica (cheia|nova|crescente|minguante).
    Faz busca dia-a-dia a partir de from_date até max 30d.
    """
    if from_date is None:
        from_date = datetime.now(timezone.utc)
    if from_date.tzinfo is None:
        from_date = from_date.replace(tzinfo=timezone.utc)

    for d in range(1, 31):
        check_date = from_date + timedelta(days=d)
        info = phase_for_date(check_date)
        if info["phase_name"] == target_phase:
            # Encontra o dia mais próximo do pico (centro da fase)
            return check_date

    return from_date  # fallback


def seed_calendar(*, months_forward: int = 12, months_back: int = 1) -> int:
    """
    Pré-calcula fases pra range de datas e persiste em lunar_phases.
    Idempotente — só insere datas faltantes.
    """
    db = SessionLocal()
    inserted = 0
    try:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=months_back * 31)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        end = (now + timedelta(days=months_forward * 31)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )

        # Busca quais datas já existem
        existing_dates = set(
            row.date.date() for row in db.query(models.LunarPhase.date).filter(
                models.LunarPhase.date >= start,
                models.LunarPhase.date <= end,
            ).all()
        )

        cur = start
        while cur <= end:
            if cur.date() not in existing_dates:
                info = phase_for_date(cur)
                db.add(models.LunarPhase(
                    date=cur,
                    phase_name=info["phase_name"],
                    illumination_pct=info["illumination_pct"],
                    is_special=info["is_special"],
                    special_label=info["special_label"],
                ))
                inserted += 1
            cur += timedelta(days=1)
        db.commit()
        logger.info("[lunar.seed] inserted=%d range %s..%s", inserted, start.date(), end.date())
        return inserted
    finally:
        db.close()


def calendar_range(*, from_date: datetime, to_date: datetime) -> list[dict]:
    """Retorna lista de fases pro range. Calcula on-the-fly se não em cache."""
    db = SessionLocal()
    try:
        rows = db.query(models.LunarPhase).filter(
            models.LunarPhase.date >= from_date,
            models.LunarPhase.date <= to_date,
        ).order_by(models.LunarPhase.date.asc()).all()

        # Se cobre todo o range, retorna do cache
        days_in_range = (to_date - from_date).days + 1
        if len(rows) >= days_in_range:
            return [
                {
                    "date": r.date.strftime("%Y-%m-%d"),
                    "phase_name": r.phase_name,
                    "illumination_pct": r.illumination_pct,
                    "is_special": r.is_special,
                    "special_label": r.special_label,
                    "emoji": _phase_emoji(r.phase_name, 14.5 if r.phase_name == "cheia" else 0),
                } for r in rows
            ]
        # Fallback: calcula on-the-fly
        out = []
        cur = from_date
        while cur <= to_date:
            out.append(phase_for_date(cur))
            cur += timedelta(days=1)
        return out
    finally:
        db.close()

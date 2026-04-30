"""
Smart greeting baseado em hora + lua + signo (Frente 4.26).

Substitui {{smart_greeting}} em qualquer template/copy do bot.

Uso:
    from smart_greeting import build_greeting, render_smart_greeting_in_text
    text = render_smart_greeting_in_text(
        "{{smart_greeting}} hoje as cartas falam de voce.",
        lead=lead,
    )

Componentes:
    - Periodo do dia (bom dia/tarde/noite) baseado no horario local do tenant
    - Saudacao contextual com signo + lua atual
    - Tom suave/poetico se lead.score_band==hot, neutro se cold
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


def _period_pt(local_hour: int) -> str:
    if 5 <= local_hour < 12:
        return "Bom dia"
    if 12 <= local_hour < 18:
        return "Boa tarde"
    if 18 <= local_hour < 24:
        return "Boa noite"
    return "Boa madrugada"


def _resolve_local_hour(tenant_id: str | None, lead) -> int:
    """
    Resolve hora local. Prioridade:
      1. lead.timezone (IANA)
      2. tenant whatsapp.timezone
      3. America/Sao_Paulo default
    """
    tz_name = None
    try:
        if lead and getattr(lead, "timezone", None):
            tz_name = lead.timezone
    except Exception:
        pass
    if not tz_name:
        try:
            from api.tenant_config import get_tenant_config
            cfg = get_tenant_config(tenant_id or "default")
            wa = cfg.get("whatsapp") if isinstance(cfg, dict) else None
            if isinstance(wa, dict):
                tz_name = wa.get("timezone")
        except Exception:
            pass
    if not tz_name:
        tz_name = "America/Sao_Paulo"
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_name)).hour
    except Exception:
        return datetime.now(timezone.utc).hour - 3  # crude fallback


def _moon_phase_today() -> dict | None:
    try:
        import lunar
        return lunar.phase_for_date()
    except Exception:
        return None


def _first_name(lead) -> str:
    nome = (getattr(lead, "nome", None) or "").strip()
    if not nome:
        return "querida"
    parts = nome.split()
    return parts[0]


def build_greeting(lead, *, tenant_id: str | None = None) -> str:
    """
    Monta a saudacao final.
    Ex.:
      "Bom dia, querida Maria. Hoje a lua nova traz silencio bom para o seu Touro."
    """
    if lead is None:
        return "Olá"
    hour = _resolve_local_hour(tenant_id or getattr(lead, "tenant_id", None), lead)
    period = _period_pt(hour)
    first = _first_name(lead)
    signo = (getattr(lead, "signo", None) or "").strip() or None

    moon = _moon_phase_today() or {}
    moon_phase = (moon.get("phase_name") or "").lower()
    moon_text_map = {
        "nova": "lua nova traz silêncio bom para a alma",
        "crescente": "lua crescente convida a plantar intenções",
        "cheia": "lua cheia ilumina o que ainda estava escondido",
        "minguante": "lua minguante pede soltura do que pesa",
    }
    moon_phrase = moon_text_map.get(moon_phase)

    parts = [f"{period}, {first}"]
    if signo and moon_phrase:
        parts.append(f"hoje a {moon_phrase}, e ela ressoa especial pra você de {signo}")
    elif signo:
        parts.append(f"a energia de {signo} acompanha seu dia")
    elif moon_phrase:
        parts.append(f"hoje a {moon_phrase}")

    out = ". ".join(parts).strip()
    if not out.endswith(("!", ".", "?")):
        out += "."
    return out


_GREETING_RE = re.compile(r"\{\{\s*smart_greeting\s*\}\}", re.IGNORECASE)


def render_smart_greeting_in_text(text: str, lead, *, tenant_id: str | None = None) -> str:
    """Substitui {{smart_greeting}} pelo texto computado."""
    if not text or "{{" not in text:
        return text
    if not _GREETING_RE.search(text):
        return text
    greeting = build_greeting(lead, tenant_id=tenant_id)
    return _GREETING_RE.sub(lambda _m: greeting, text)

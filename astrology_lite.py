"""
Astrologia LITE (Frente 4.5 / 4.6 — V1 sem pyswisseph).

Calcula o que e possivel sem ephemeris completa:
    - Sun sign  (data de nascimento) — preciso
    - Moon sign (aproximacao por elongacao lunar) — ~75% precisao
    - Ascendente (se birth_time + lat conhecidos) — aproximacao simples

V2 troca pra pyswisseph e adiciona Mercurio/Venus/Marte/etc.

Funcoes:
    natal_chart_lite(birth_date, birth_time?, lat?, lon?) -> dict
    chart_summary_text(chart) -> str (input p/ Gemini)
"""

from __future__ import annotations

import math
from datetime import date as DateT, datetime, time as TimeT, timezone

from horoscope import compute_sun_sign, ALL_SIGNS


# Ordem zodiacal canonica (degraus 0-360 a partir de Aries)
ZODIAC_ORDER = [
    "Aries", "Touro", "Gemeos", "Cancer", "Leao", "Virgem",
    "Libra", "Escorpiao", "Sagitario", "Capricornio", "Aquario", "Peixes",
]


def _sign_for_longitude(lon_deg: float) -> tuple[str, float]:
    """Retorna (signo, grau dentro do signo) para uma longitude eclíptica."""
    lon = lon_deg % 360.0
    idx = int(lon // 30)
    deg_in_sign = lon - idx * 30
    return ZODIAC_ORDER[idx], round(deg_in_sign, 2)


# ─── Lua: aproximacao via elongacao + posicao do Sol ──────────────────


_REF_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_SYNODIC = 29.53059
# Velocidade media do Sol: 360°/365.25 dias ~ 0.9856°/dia
_SUN_DEG_PER_DAY = 360.0 / 365.25


def _sun_longitude(dt_utc: datetime) -> float:
    """
    Longitude eclíptica aproximada do Sol (anomalia uniforme).
    Reference: 21/03 (~Aries 0°). Aproximacao linear suficiente p/ V1.
    """
    year = dt_utc.year
    spring_eq = datetime(year, 3, 20, 21, 0, tzinfo=timezone.utc)
    days = (dt_utc - spring_eq).total_seconds() / 86400.0
    return (days * _SUN_DEG_PER_DAY) % 360.0


def _moon_age_days(dt_utc: datetime) -> float:
    diff = (dt_utc - _REF_NEW_MOON).total_seconds() / 86400.0
    return diff % _SYNODIC


def _moon_longitude(dt_utc: datetime) -> float:
    """
    Aproximacao da longitude da Lua via elongacao + Sol.
    elongacao = idade lunar / synodico * 360°
    longitude_lua ~= longitude_sol + elongacao
    Erro ~ ±5°. Suficiente pra estimar signo (~75% acerto).
    """
    age = _moon_age_days(dt_utc)
    elongation = (age / _SYNODIC) * 360.0
    sun = _sun_longitude(dt_utc)
    return (sun + elongation) % 360.0


# ─── Ascendente: aproximacao se time + lat ────────────────────────────


def _ascendant_lon(dt_utc: datetime, lat_deg: float, lon_deg: float) -> float:
    """
    Aproximacao do ascendente via tempo sideral.
    Formula simplificada (Meeus light):
        GMST (graus) = 280.46 + 360.98564736629 * dias_J2000
        LST = GMST + lon_geo
        ASC ~= atan(cos(LST) / -(sin(LST)*cos(epsilon) + tan(lat)*sin(epsilon)))
    """
    j2000 = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    days = (dt_utc - j2000).total_seconds() / 86400.0
    gmst = (280.46061837 + 360.98564736629 * days) % 360.0
    lst = (gmst + lon_deg) % 360.0
    epsilon = math.radians(23.4392911)  # obliquidade
    lst_rad = math.radians(lst)
    lat_rad = math.radians(lat_deg)
    y = -math.cos(lst_rad)
    x = math.sin(lst_rad) * math.cos(epsilon) + math.tan(lat_rad) * math.sin(epsilon)
    asc_rad = math.atan2(y, x)
    asc_deg = math.degrees(asc_rad) % 360.0
    return asc_deg


# ─── API publica ──────────────────────────────────────────────────────


def natal_chart_lite(
    birth_date: DateT,
    birth_time: TimeT | None = None,
    *,
    lat: float | None = None,
    lon: float | None = None,
    timezone_offset_hours: float = -3,
) -> dict:
    """
    Retorna mapa basico:
        sun:    {sign, deg}
        moon:   {sign, deg, approx}
        asc:    {sign, deg}  (so se birth_time + lat + lon)
        elements: {fogo, terra, ar, agua}  contagem dos pontos calculados
    """
    # Constroi datetime UTC
    if birth_time is None:
        # Default 12:00 local
        local_dt = datetime.combine(birth_date, TimeT(12, 0))
    else:
        local_dt = datetime.combine(birth_date, birth_time)

    # Aplica offset (assume input fornecido em local-time + timezone do tenant)
    utc_dt = local_dt.replace(tzinfo=timezone.utc) - _hours(timezone_offset_hours)

    sun_sign = compute_sun_sign(birth_date)
    moon_lon = _moon_longitude(utc_dt)
    moon_sign, moon_deg = _sign_for_longitude(moon_lon)

    out: dict = {
        "sun": {"sign": sun_sign, "deg": _sun_deg_in_sign(birth_date)},
        "moon": {"sign": moon_sign, "deg": moon_deg, "approx": True},
        "asc": None,
    }

    if birth_time is not None and lat is not None and lon is not None:
        asc_lon = _ascendant_lon(utc_dt, lat, lon)
        asc_sign, asc_deg = _sign_for_longitude(asc_lon)
        out["asc"] = {"sign": asc_sign, "deg": asc_deg}

    out["elements"] = _element_balance(out)
    return out


def _hours(h: float):
    """timedelta em horas usando datetime (evita import extra)."""
    from datetime import timedelta
    return timedelta(hours=h)


def _sun_deg_in_sign(birth_date: DateT) -> float:
    """Aproxima grau do Sol dentro do signo: dias desde inicio do signo."""
    # Aries comeca 21/03; cada signo ~30 dias
    # Para V1 retorna 15.0 (centro). Suficiente pra interpretacao.
    return 15.0


_ELEMENT = {
    "Aries": "fogo", "Leao": "fogo", "Sagitario": "fogo",
    "Touro": "terra", "Virgem": "terra", "Capricornio": "terra",
    "Gemeos": "ar", "Libra": "ar", "Aquario": "ar",
    "Cancer": "agua", "Escorpiao": "agua", "Peixes": "agua",
}


def _element_balance(chart: dict) -> dict:
    counts = {"fogo": 0, "terra": 0, "ar": 0, "agua": 0}
    for key in ("sun", "moon", "asc"):
        v = chart.get(key)
        if v and v.get("sign"):
            el = _ELEMENT.get(v["sign"])
            if el:
                counts[el] += 1
    return counts


def chart_summary_text(chart: dict) -> str:
    """Resumo curto pra alimentar Gemini ou exibir no front."""
    parts = []
    if chart.get("sun"):
        parts.append(f"Sol em {chart['sun']['sign']}")
    if chart.get("moon"):
        parts.append(f"Lua em {chart['moon']['sign']} (aprox)")
    if chart.get("asc"):
        parts.append(f"Ascendente em {chart['asc']['sign']}")
    el = chart.get("elements") or {}
    dom = max(el, key=lambda k: el[k]) if el and any(el.values()) else None
    if dom:
        parts.append(f"elemento dominante: {dom}")
    return " · ".join(parts)


# ─── Interpretacao via Gemini ─────────────────────────────────────────


def interpret_chart(chart: dict, focus: str = "geral") -> str:
    """
    Gera interpretacao de mapa via Gemini (ou fallback texto generico).
    focus: 'geral' | 'amor' | 'carreira' | 'familia'
    """
    summary = chart_summary_text(chart)
    if not summary:
        return ""

    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            raise RuntimeError("personalizer_unavailable")
        prompt = (
            f"Voce e uma astrologa empatica. Faca interpretacao breve (max 180 palavras), "
            f"em pt-BR, foco em {focus}. NAO use jargao tecnico. "
            f"Use o seguinte mapa:\n{summary}\n\n"
            f"Termine com 1 conselho pratico do dia."
        )
        resposta = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 320, "temperature": 0.85},
        )
        text = (resposta.text or "").strip()
        return text or _fallback_interpretation(chart)
    except Exception:
        return _fallback_interpretation(chart)


def _fallback_interpretation(chart: dict) -> str:
    sun = (chart.get("sun") or {}).get("sign")
    moon = (chart.get("moon") or {}).get("sign")
    if not sun:
        return "Nao foi possivel calcular o mapa."
    base = f"Com Sol em {sun}, voce expressa-se com a energia tipica desse signo."
    if moon:
        base += f" A Lua em {moon} colore o mundo emocional, dando outra camada a forma como voce sente."
    return base + " Confie nos pequenos sinais do dia — eles geralmente apontam o proximo passo."


def interpret_numerology(numbers: dict, name: str | None = None) -> str:
    """Gera interpretacao numerologica via Gemini ou fallback."""
    lp = numbers.get("life_path")
    ex = numbers.get("expression")
    sl = numbers.get("soul")
    if lp is None and ex is None and sl is None:
        return ""

    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            raise RuntimeError("personalizer_unavailable")
        bits = []
        if lp is not None: bits.append(f"numero da vida {lp}")
        if ex is not None: bits.append(f"expressao {ex}")
        if sl is not None: bits.append(f"alma {sl}")
        prompt = (
            f"Voce e uma numerologa empatica. Em ate 150 palavras pt-BR, "
            f"interprete a numerologia de {name or 'esta pessoa'}: {', '.join(bits)}. "
            f"Conecte os tres numeros em uma narrativa coerente sobre proposito de vida, "
            f"talentos e desejo da alma. Termine com 1 conselho concreto."
        )
        resposta = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 280, "temperature": 0.85},
        )
        text = (resposta.text or "").strip()
        return text or _fallback_numerology(numbers)
    except Exception:
        return _fallback_numerology(numbers)


def _fallback_numerology(numbers: dict) -> str:
    parts = []
    if numbers.get("life_path"):
        parts.append(numbers.get("life_path_meaning") or "")
    if numbers.get("expression"):
        parts.append(numbers.get("expression_meaning") or "")
    if numbers.get("soul"):
        parts.append(numbers.get("soul_meaning") or "")
    return " ".join(p for p in parts if p)


__all__ = [
    "natal_chart_lite",
    "chart_summary_text",
    "interpret_chart",
    "interpret_numerology",
    "ZODIAC_ORDER",
    "ALL_SIGNS",
]

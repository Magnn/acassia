"""
Extrator de data de nascimento em linguagem natural (Frente 4.25).

Usado pelo motor pra capturar birth_date de mensagens conversacionais
sem formulario. Ex.:
    "23 de maio de 1986"  -> 1986-05-23 confidence=0.95
    "23/5/86"             -> 1986-05-23 confidence=0.95
    "23-05-1986"          -> 1986-05-23 confidence=0.95
    "maio de 86"          -> 1986-05-?  (incomplete -> needs day)
    "23 de maio"          -> ?-05-23    (incomplete -> needs year)
    "nasci em 1986"       -> 1986-?-?   (incomplete -> needs day+month)

Estrategia em camadas:
    1. Regex hardcoded (rapido, deterministico, alto recall pra formato BR)
    2. Heuristica (mes-por-extenso, abreviacoes)
    3. Gemini fallback (raros formatos como "no dia que cai a pascoa de 86")
"""

from __future__ import annotations

import calendar
import logging
import re
from dataclasses import dataclass
from datetime import date as DateT, datetime
from typing import Optional


logger = logging.getLogger(__name__)


@dataclass
class BirthDateResult:
    date: Optional[DateT]
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]
    confidence: float
    raw: str
    source: str  # regex|gemini|heuristic|invalid|empty
    needs_clarification: bool
    clarification_question: Optional[str] = None
    parse_error: Optional[str] = None


# ─── Mapas de meses ────────────────────────────────────────────────────


_MONTH_NAMES = {
    "jan": 1, "janeiro": 1, "janei": 1,
    "fev": 2, "fevereiro": 2, "fever": 2,
    "mar": 3, "marco": 3, "marco": 3, "março": 3, "março": 3,
    "abr": 4, "abril": 4,
    "mai": 5, "maio": 5,
    "jun": 6, "junho": 6,
    "jul": 7, "julho": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "setembro": 9, "sete": 9,
    "out": 10, "outubro": 10,
    "nov": 11, "novembro": 11,
    "dez": 12, "dezembro": 12,
}


def _strip_accents(text: str) -> str:
    import unicodedata
    nf = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nf if not unicodedata.combining(c))


def _normalize_year(year_str: str) -> Optional[int]:
    """
    Normaliza ano: 86 -> 1986, 05 -> 2005, 1986 -> 1986.
    Heuristica: 2 digitos viram 19xx se >=30, senao 20xx (default).
    Range valido: 1900..ano_atual.
    """
    try:
        y = int(year_str)
    except (TypeError, ValueError):
        return None
    if y < 100:
        # 2 digitos: pivot ~30 (assume nascimento ate 30 anos atras = 20xx)
        y = 1900 + y if y >= 30 else 2000 + y
    cur_year = datetime.now().year
    if y < 1900 or y > cur_year:
        return None
    return y


def _make_date(year: int, month: int, day: int) -> tuple[DateT | None, str | None]:
    """Constroi date com validacao bissexto. Retorna (date, error_msg)."""
    if month < 1 or month > 12:
        return None, "month_invalid"
    if day < 1:
        return None, "day_invalid"
    try:
        max_day = calendar.monthrange(year, month)[1]
    except Exception:
        return None, "year_invalid"
    if day > max_day:
        return None, f"day_exceeds_month_max_{max_day}"
    try:
        return DateT(year, month, day), None
    except (ValueError, TypeError) as exc:
        return None, str(exc)


# ─── Regex patterns ───────────────────────────────────────────────────


# DD/MM/YYYY ou DD/MM/YY ou DD-MM-YY ou DD.MM.YY
_RX_NUMERIC = re.compile(
    r"\b(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{2,4})\b"
)

# YYYY-MM-DD (ISO)
_RX_ISO = re.compile(r"\b(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\b")

# DD de mes de YYYY  (com "de" ou espacos)
_RX_FULL_PT = re.compile(
    r"\b(\d{1,2})\s+(?:de\s+)?([a-z]+?)\s+(?:de\s+)?(\d{2,4})\b",
    re.IGNORECASE,
)

# DD de mes (sem ano)
_RX_DAY_MONTH = re.compile(
    r"\b(\d{1,2})\s+(?:de\s+)?([a-z]+)\b",
    re.IGNORECASE,
)

# mes de YYYY (sem dia)
_RX_MONTH_YEAR = re.compile(
    r"\b([a-z]+)\s+(?:de\s+)?(\d{2,4})\b",
    re.IGNORECASE,
)

# Apenas ano isolado: "nasci em 1986" / "em 86"
_RX_YEAR_ONLY = re.compile(r"\b(?:em\s+|de\s+)?(\d{2,4})\b")


# ─── Parsers ───────────────────────────────────────────────────────────


def _parse_numeric(text: str) -> Optional[BirthDateResult]:
    m = _RX_NUMERIC.search(text)
    if not m:
        return None
    d_str, mo_str, y_str = m.group(1), m.group(2), m.group(3)
    year = _normalize_year(y_str)
    try:
        day = int(d_str)
        month = int(mo_str)
    except ValueError:
        return None
    if year is None:
        return None
    dt, err = _make_date(year, month, day)
    if dt is None:
        return BirthDateResult(
            date=None, year=year, month=month, day=day,
            confidence=0.6, raw=m.group(0), source="regex",
            needs_clarification=True,
            clarification_question=(
                f"Conferi aqui — {day:02d}/{month:02d}/{year} parece invalida. "
                "Pode confirmar o dia/mes pra mim?"
            ),
            parse_error=err,
        )
    return BirthDateResult(
        date=dt, year=year, month=month, day=day,
        confidence=0.95, raw=m.group(0), source="regex",
        needs_clarification=False,
    )


def _parse_iso(text: str) -> Optional[BirthDateResult]:
    m = _RX_ISO.search(text)
    if not m:
        return None
    try:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
    except ValueError:
        return None
    cur_year = datetime.now().year
    if year < 1900 or year > cur_year:
        return None
    dt, err = _make_date(year, month, day)
    if dt is None:
        return BirthDateResult(
            date=None, year=year, month=month, day=day,
            confidence=0.6, raw=m.group(0), source="regex",
            needs_clarification=True,
            clarification_question=f"Hum, {day:02d}/{month:02d}/{year} nao bate — pode conferir?",
            parse_error=err,
        )
    return BirthDateResult(
        date=dt, year=year, month=month, day=day,
        confidence=0.95, raw=m.group(0), source="regex",
        needs_clarification=False,
    )


def _parse_full_pt(text_norm: str) -> Optional[BirthDateResult]:
    m = _RX_FULL_PT.search(text_norm)
    if not m:
        return None
    d_str, mo_word, y_str = m.group(1), m.group(2).lower(), m.group(3)
    month = _MONTH_NAMES.get(mo_word)
    if month is None:
        return None
    try:
        day = int(d_str)
    except ValueError:
        return None
    year = _normalize_year(y_str)
    if year is None:
        return None
    dt, err = _make_date(year, month, day)
    if dt is None:
        return BirthDateResult(
            date=None, year=year, month=month, day=day,
            confidence=0.6, raw=m.group(0), source="regex",
            needs_clarification=True,
            clarification_question=f"Hum, {day:02d}/{month:02d}/{year} parece invalida — pode conferir?",
            parse_error=err,
        )
    return BirthDateResult(
        date=dt, year=year, month=month, day=day,
        confidence=0.95, raw=m.group(0), source="regex",
        needs_clarification=False,
    )


def _parse_day_month_no_year(text_norm: str) -> Optional[BirthDateResult]:
    """Ex.: '23 de maio' — falta ano."""
    # Procura toda ocorrencia: o full_pt vai pegar antes se tiver ano. Se chegou aqui,
    # ja sabemos que nao tem ano. Mas garante que nao tem digitos seguindo o mes.
    matches = _RX_DAY_MONTH.findall(text_norm)
    for d_str, mo_word in matches:
        month = _MONTH_NAMES.get(mo_word.lower())
        if month is None:
            continue
        try:
            day = int(d_str)
        except ValueError:
            continue
        if 1 <= day <= 31:
            return BirthDateResult(
                date=None, year=None, month=month, day=day,
                confidence=0.5, raw=f"{d_str} {mo_word}", source="regex",
                needs_clarification=True,
                clarification_question="Em que ano voce nasceu?",
            )
    return None


def _parse_month_year_no_day(text_norm: str) -> Optional[BirthDateResult]:
    """Ex.: 'maio de 86'."""
    matches = _RX_MONTH_YEAR.findall(text_norm)
    for mo_word, y_str in matches:
        month = _MONTH_NAMES.get(mo_word.lower())
        if month is None:
            continue
        year = _normalize_year(y_str)
        if year is None:
            continue
        return BirthDateResult(
            date=None, year=year, month=month, day=None,
            confidence=0.5, raw=f"{mo_word} de {y_str}", source="regex",
            needs_clarification=True,
            clarification_question=f"Que dia de {mo_word.lower()} de {year}?",
        )
    return None


def _parse_year_only(text_norm: str) -> Optional[BirthDateResult]:
    """Ex.: 'nasci em 86'."""
    if not re.search(r"\b(nasci|naixi|nascida?o?|naceu)\b", text_norm):
        return None
    matches = _RX_YEAR_ONLY.findall(text_norm)
    for y_str in matches:
        year = _normalize_year(y_str)
        if year is None:
            continue
        return BirthDateResult(
            date=None, year=year, month=None, day=None,
            confidence=0.4, raw=y_str, source="regex",
            needs_clarification=True,
            clarification_question=f"E em que dia/mes de {year}?",
        )
    return None


# ─── Public API ────────────────────────────────────────────────────────


def extract_birth_date(text: str, *, prefer_gemini: bool = False) -> BirthDateResult:
    """
    Extrai data de nascimento de mensagem natural.

    Pipeline:
        1. Numerico DD/MM/YY ou DD-MM-YYYY (mais comum)
        2. ISO YYYY-MM-DD
        3. Full PT 'DD de MES de YYYY'
        4. Parcial dia+mes / mes+ano / ano-isolado
        5. Gemini fallback (opt-in via prefer_gemini=True ou se outras
           camadas nao acharem nada e text e suficientemente longo)
    """
    text = text or ""
    text_norm = _strip_accents(text).lower()

    if not text.strip():
        return BirthDateResult(
            date=None, year=None, month=None, day=None,
            confidence=0.0, raw="", source="empty",
            needs_clarification=True,
            clarification_question="Em que dia voce nasceu?",
        )

    # Camada 1-3: regex deterministico
    for parser in (_parse_iso, _parse_numeric):
        r = parser(text)
        if r is not None:
            return r
    r = _parse_full_pt(text_norm)
    if r is not None:
        return r

    # Camada 4: parcial
    r = _parse_day_month_no_year(text_norm)
    if r is not None:
        return r
    r = _parse_month_year_no_day(text_norm)
    if r is not None:
        return r
    r = _parse_year_only(text_norm)
    if r is not None:
        return r

    # Camada 5: Gemini (raros)
    if prefer_gemini and len(text.strip()) >= 5:
        gem = _gemini_extract(text)
        if gem is not None:
            return gem

    # Detecta "nao lembro"
    if re.search(r"\b(nao|n[~]?ao)\s+(lembr|sei|fa[cç]o\s+ide)", text_norm):
        return BirthDateResult(
            date=None, year=None, month=None, day=None,
            confidence=0.0, raw=text, source="invalid",
            needs_clarification=False,
        )

    return BirthDateResult(
        date=None, year=None, month=None, day=None,
        confidence=0.0, raw=text, source="invalid",
        needs_clarification=True,
        clarification_question=(
            "Nao consegui entender. Pode me dizer no formato dia/mes/ano? "
            "Ex: 23/05/1986."
        ),
    )


def _gemini_extract(text: str) -> Optional[BirthDateResult]:
    """Fallback Gemini pra formatos exoticos. Retorna None em qualquer falha."""
    try:
        from app import personalizer as client
        if client is None or not hasattr(client, "client"):
            return None
        prompt = (
            "Extraia a data de nascimento desta mensagem. "
            "Retorne APENAS JSON com chaves: "
            "year (int ou null), month (int 1-12 ou null), day (int 1-31 ou null), "
            "confidence (float 0-1).\n\n"
            f"Mensagem: \"\"\"{text[:500]}\"\"\"\n\n"
            "Se nao for possivel extrair nada, retorne todos null com confidence=0."
        )
        resp = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={
                "max_output_tokens": 150,
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        )
        import json
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        year = parsed.get("year")
        month = parsed.get("month")
        day = parsed.get("day")
        confidence = float(parsed.get("confidence") or 0.0)
        if year is None and month is None and day is None:
            return None
        if year is not None:
            year = _normalize_year(str(year))
        if year is not None and month is not None and day is not None:
            dt, err = _make_date(int(year), int(month), int(day))
            if dt is not None:
                return BirthDateResult(
                    date=dt, year=year, month=int(month), day=int(day),
                    confidence=min(0.85, confidence),  # cap < regex
                    raw=text, source="gemini",
                    needs_clarification=False,
                )
            return BirthDateResult(
                date=None, year=year, month=int(month), day=int(day),
                confidence=0.4, raw=text, source="gemini",
                needs_clarification=True,
                clarification_question=f"Conferi {day:02d}/{int(month):02d}/{year} — invalida. Pode confirmar?",
                parse_error=err,
            )
        # Parcial
        return BirthDateResult(
            date=None, year=year, month=int(month) if month else None,
            day=int(day) if day else None,
            confidence=min(0.5, confidence),
            raw=text, source="gemini",
            needs_clarification=True,
            clarification_question=_clarification_for_partial(year, month, day),
        )
    except Exception as exc:
        logger.warning("[birthdate.gemini] falha: %s", exc)
        return None


def _clarification_for_partial(year, month, day) -> str:
    if year and month and not day:
        return f"Que dia de {month:02d}/{year}?"
    if year and not month and not day:
        return f"E em que dia/mes de {year}?"
    if month and day and not year:
        return "Em que ano?"
    return "Pode me dizer no formato dia/mes/ano? Ex: 23/05/1986."


def confirmation_message(result: BirthDateResult) -> str:
    """Frase de confirmacao pra mostrar ao lead antes de persistir."""
    if result.date:
        return (
            f"Anotei aqui: {result.date.strftime('%d/%m/%Y')}. "
            "Esta correto? (responda sim ou corrija)"
        )
    return result.clarification_question or "Pode me confirmar o dia/mes/ano?"


# ─── Ambient sniffer pra engine ────────────────────────────────────────


_HIGH_CONFIDENCE_THRESHOLD = 0.90
# So tenta sniffer se a msg parece envolver data — evita custos em conversas normais
_DATE_HINT_RX = re.compile(
    r"\b(\d{1,2}\s*[/\-\.]\s*\d{1,2}|\d{4}[\-/]\d{1,2}|"
    r"jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|"
    r"nasci|nasce|nascimento|aniversario)\b",
    re.IGNORECASE,
)


def sniff_and_persist(text: str, lead) -> Optional[BirthDateResult]:
    """
    Sniffer ambient: tenta extrair date com regex apenas (sem Gemini),
    persistindo SO em casos de alta confianca + lead sem birth_date previo.

    Retorna o resultado se persistiu (mutacao no objeto lead), None caso
    contrario. O caller (engine) faz commit do session em batch.

    Usar dentro de processar_mensagem — apenas em mensagens do lead.
    """
    if not text or not lead or getattr(lead, "birth_date", None):
        return None
    if not _DATE_HINT_RX.search(_strip_accents(text).lower()):
        return None

    result = extract_birth_date(text, prefer_gemini=False)
    if not result.date or result.confidence < _HIGH_CONFIDENCE_THRESHOLD:
        return None

    try:
        lead.birth_date = result.date
        try:
            import horoscope
            sign = horoscope.compute_sun_sign(result.date)
            if sign and not getattr(lead, "signo", None):
                lead.signo = sign
        except Exception as exc:
            logger.warning("[birthdate.sniff] signo falhou: %s", exc)
        # commit deferido pro caller (engine ja faz em batch)
        return result
    except Exception as exc:
        logger.warning("[birthdate.sniff] persist falhou: %s", exc)
        return None

"""
Horoscope engine (Frente 4.13).

Funcoes:
    compute_sun_sign(birth_date)            — date -> "Touro" etc
    ensure_daily_text(signo, date, source)  — pega/gera texto cacheado
    fanout_for_tenant(tenant_id, today_date) — envia broadcast pros leads opt-in
    backfill_signs_for_tenant(tenant_id)    — popula leads.signo a partir de birth_date

Convenções:
    - signos em portugues capitalizados: Aries, Touro, Gemeos, ...
    - cache (date, signo, lang='pt-BR') é compartilhado entre tenants → economia
    - opt-in: lead.consents['daily_horoscope'] = True
    - opt-out: opt_out=True OU consents.daily_horoscope == False
"""

from __future__ import annotations

import logging
from datetime import date as DateT, datetime, timezone

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


# Sun sign ranges (mes, dia inicial) -> nome. Aries começa 21/03.
ZODIAC_RANGES = [
    ((3, 21), (4, 19), "Aries"),
    ((4, 20), (5, 20), "Touro"),
    ((5, 21), (6, 20), "Gemeos"),
    ((6, 21), (7, 22), "Cancer"),
    ((7, 23), (8, 22), "Leao"),
    ((8, 23), (9, 22), "Virgem"),
    ((9, 23), (10, 22), "Libra"),
    ((10, 23), (11, 21), "Escorpiao"),
    ((11, 22), (12, 21), "Sagitario"),
    ((12, 22), (1, 19), "Capricornio"),
    ((1, 20), (2, 18), "Aquario"),
    ((2, 19), (3, 20), "Peixes"),
]

ALL_SIGNS = [s for _, _, s in ZODIAC_RANGES]


def compute_sun_sign(birth_date: DateT) -> str:
    """Retorna nome do signo solar pra data de nascimento."""
    if birth_date is None:
        return ""
    m, d = birth_date.month, birth_date.day
    for (sm, sd), (em, ed), name in ZODIAC_RANGES:
        if sm == em:
            if m == sm and sd <= d <= ed:
                return name
        else:
            # Caso Capricornio (22/12 a 19/01)
            if (m == sm and d >= sd) or (m == em and d <= ed):
                return name
    return ""


# ─── Geracao de texto via Gemini ──────────────────────────────────────


_FALLBACK_TEXTS = {
    "Aries": "Hoje a energia pede coragem. Algo que voce vinha adiando ganha forca pra ser feito agora.",
    "Touro": "Volte sua atencao para o conforto e o que sustenta voce. Pequenos prazeres hoje recarregam.",
    "Gemeos": "Conversas trazem informacoes valiosas. Escute o que vem antes de responder.",
    "Cancer": "Cuide do seu interior. A intuicao esta forte e mostra o caminho certo nas decisoes.",
    "Leao": "Sua presenca brilha hoje — use com generosidade. Reconhecimento chega de onde voce nao espera.",
    "Virgem": "Organize um detalhe que vinha incomodando. A clareza chega quando voce poe ordem.",
    "Libra": "Equilibrio e a palavra do dia. Uma escolha cuidadosa entre dois caminhos abre uma porta.",
    "Escorpiao": "Algo se transforma em silencio. Confie no processo — o que parece fim e recomeço.",
    "Sagitario": "Expansao chama. Uma ideia ou viagem entra no horizonte e merece atencao.",
    "Capricornio": "Foco e disciplina rendem hoje. Um passo concreto vale mais do que tres planos vagos.",
    "Aquario": "Inovacao guia voce. Uma ideia diferente do habitual pode mudar uma situação parada.",
    "Peixes": "Sensibilidade aflorada — escute sonhos e sinais. A inspiracao traz uma resposta esperada.",
}


def _generate_via_gemini(signo: str, target_date: DateT) -> tuple[str, str] | None:
    """
    Usa o personalizer/Gemini pra gerar 2-3 frases de horoscopo.
    Retorna (texto, model_id) ou None se falhar.
    """
    try:
        # Reaproveita a instancia ja construida em app.py (com api_key + cliente Gemini)
        try:
            from app import personalizer as client
        except Exception:
            client = None
        if client is None or not hasattr(client, "client"):
            return None

        prompt = (
            f"Voce e uma cigana mistica. Escreva o horoscopo de hoje "
            f"({target_date.strftime('%d/%m/%Y')}) para o signo de {signo}. "
            f"Use 2 a 3 frases curtas, tom acolhedor e mistico, em portugues do Brasil. "
            f"Nao use emoji. Nao mencione o nome do signo no inicio. "
            f"Foque em emocao, decisao do dia ou sinal a observar."
        )
        resposta = client.client.models.generate_content(
            model=client.model_name,
            contents=prompt,
            config={"max_output_tokens": 220, "temperature": 0.85},
        )
        text = (resposta.text or "").strip()
        if not text:
            return None
        return text[:600], client.model_name
    except Exception as exc:
        logger.warning("[horoscope.gemini] falha p/ %s: %s", signo, exc)
        return None


def ensure_daily_text(
    signo: str,
    target_date: DateT | None = None,
    *,
    source: str = "gemini",
    lang: str = "pt-BR",
    db_session=None,
) -> models.DailyHoroscope:
    """
    Garante que existe horoscopo cacheado pra (date, signo, lang).
    Se nao existe e source==gemini, tenta gerar; senao usa fallback.
    """
    target_date = target_date or DateT.today()
    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        existing = db.query(models.DailyHoroscope).filter_by(
            date=target_date, signo=signo, lang=lang,
        ).first()
        if existing:
            return existing

        text = ""
        used_source = source
        generated_by = None
        if source == "gemini":
            result = _generate_via_gemini(signo, target_date)
            if result:
                text, generated_by = result

        if not text:
            text = _FALLBACK_TEXTS.get(signo, "Hoje pede atencao aos sinais. Ouca o que vem em silencio.")
            used_source = "fallback"
            generated_by = None

        row = models.DailyHoroscope(
            date=target_date, signo=signo, lang=lang,
            text=text, source=used_source, generated_by=generated_by,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        if own_session:
            db.close()


def ensure_all_signs_for_date(
    target_date: DateT | None = None, *, source: str = "gemini",
) -> dict[str, str]:
    """Garante que os 12 signos tem texto cacheado pra essa data. Retorna {signo: texto}."""
    target_date = target_date or DateT.today()
    db = SessionLocal()
    out: dict[str, str] = {}
    try:
        for signo in ALL_SIGNS:
            row = ensure_daily_text(signo, target_date, source=source, db_session=db)
            out[signo] = row.text
    finally:
        db.close()
    return out


# ─── Fanout pra leads do tenant ───────────────────────────────────────


def _segment_matches(lead: "models.Lead", segment: str) -> bool:
    if segment == "all":
        return True
    band = (lead.score_band or "cold").lower()
    if segment == "hot":
        return band == "hot"
    if segment == "warm":
        return band == "warm"
    if segment == "hot_warm":
        return band in ("hot", "warm")
    return True


def _format_message(prefix: str | None, signo: str, text: str) -> str:
    head = (prefix.strip() + "\n\n") if prefix else ""
    return f"{head}Horoscopo de hoje • {signo}\n\n{text}"


def fanout_for_tenant(
    tenant_id: str,
    target_date: DateT | None = None,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Envia horoscopo do dia pros leads opt-in do tenant.
    Idempotente: se ja existe HoroscopeDelivery para (tenant, lead, date), pula.

    Retorna {sent, skipped, failed, opted_out, by_sign}.
    """
    target_date = target_date or DateT.today()
    db = SessionLocal()
    stats = {"sent": 0, "skipped": 0, "failed": 0, "opted_out": 0, "by_sign": {}}
    try:
        cfg = db.query(models.HoroscopeAutomation).filter_by(tenant_id=tenant_id).first()
        if cfg is None or not cfg.enabled:
            return {**stats, "reason": "disabled"}

        # Garante cache de signos
        ensure_all_signs_for_date(target_date, source=cfg.source)

        # Leads candidatos: signo preenchido + nao opted-out + consents.daily_horoscope==True
        leads = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.signo.isnot(None),
            models.Lead.opt_out == False,  # noqa: E712
            models.Lead.bot_pausado == False,  # noqa: E712
        ).all()

        if not leads:
            return {**stats, "reason": "no_candidates"}

        # Pre-carrega textos
        texts = {
            r.signo: r.text for r in db.query(models.DailyHoroscope).filter_by(
                date=target_date, lang="pt-BR",
            ).all()
        }

        wa_client = _get_whatsapp_client(tenant_id)

        for lead in leads:
            consents = lead.consents or {}
            if consents.get("daily_horoscope") is not True:
                stats["opted_out"] += 1
                continue
            if not _segment_matches(lead, cfg.segment_filter):
                stats["skipped"] += 1
                continue

            # Idempotência
            already = db.query(models.HoroscopeDelivery).filter_by(
                tenant_id=tenant_id, lead_id=lead.id, date=target_date,
            ).first()
            if already:
                stats["skipped"] += 1
                continue

            text = texts.get(lead.signo)
            if not text:
                stats["failed"] += 1
                continue

            msg = _format_message(cfg.custom_prefix, lead.signo, text)

            if dry_run:
                stats["sent"] += 1
                stats["by_sign"][lead.signo] = stats["by_sign"].get(lead.signo, 0) + 1
                continue

            try:
                if wa_client is not None:
                    wa_client.enviar_mensagem(lead.telefone, msg, formato="texto")
                else:
                    raise RuntimeError("whatsapp_client_unavailable")
                db.add(models.HoroscopeDelivery(
                    tenant_id=tenant_id, lead_id=lead.id,
                    date=target_date, signo=lead.signo, status="sent",
                ))
                stats["sent"] += 1
                stats["by_sign"][lead.signo] = stats["by_sign"].get(lead.signo, 0) + 1
            except Exception as exc:
                db.add(models.HoroscopeDelivery(
                    tenant_id=tenant_id, lead_id=lead.id,
                    date=target_date, signo=lead.signo, status="failed",
                    error_message=str(exc)[:500],
                ))
                stats["failed"] += 1
                logger.warning("[horoscope.fanout] tenant=%s lead=%s falhou: %s",
                               tenant_id, lead.id, exc)

        cfg.last_run_date = target_date
        cfg.total_sent = (cfg.total_sent or 0) + stats["sent"]
        cfg.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=None,
                event_type="horoscope.daily.fanout",
                target_type="horoscope",
                target_id=target_date.isoformat(),
                payload=stats,
            ))
            db.commit()
        except Exception:
            db.rollback()

        return stats
    finally:
        db.close()


def _get_whatsapp_client(tenant_id: str):
    """
    Resolve client WhatsApp pro tenant. Reaproveita o sender padrao do projeto.
    Retorna None se nao houver client configurado.
    """
    try:
        import api.whatsapp_api as wa_module
        # Estrategia: procurar fabrica padrao "WhatsAppAPI" ou instancia global
        if hasattr(wa_module, "get_client_for_tenant"):
            return wa_module.get_client_for_tenant(tenant_id)
        if hasattr(wa_module, "whatsapp_global"):
            return wa_module.whatsapp_global
        Cls = getattr(wa_module, "WhatsAppAPI", None)
        if Cls is None:
            return None
        return Cls()
    except Exception as exc:
        logger.warning("[horoscope.wa_client] falha: %s", exc)
        return None


# ─── Backfill signos a partir de birth_date ───────────────────────────


def backfill_signs_for_tenant(tenant_id: str) -> int:
    """Calcula signo pra leads que tem birth_date mas signo vazio."""
    db = SessionLocal()
    updated = 0
    try:
        leads = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.birth_date.isnot(None),
            models.Lead.signo.is_(None),
        ).all()
        for lead in leads:
            sign = compute_sun_sign(lead.birth_date)
            if sign:
                lead.signo = sign
                updated += 1
        if updated:
            db.commit()
    finally:
        db.close()
    return updated


# ─── Cron entrypoint ──────────────────────────────────────────────────


def hourly_dispatch_due_tenants() -> int:
    """
    Para cada tenant com automacao enabled cuja hora_local atual ==
    send_hour_local E ainda nao rodou hoje, dispara fanout.

    Retorna quantos tenants processados.
    """
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        return 0

    db = SessionLocal()
    processed = 0
    try:
        configs = db.query(models.HoroscopeAutomation).filter_by(enabled=True).all()
        now_utc = datetime.now(timezone.utc)
        for cfg in configs:
            try:
                tz = ZoneInfo(cfg.timezone or "America/Sao_Paulo")
            except Exception:
                tz = ZoneInfo("America/Sao_Paulo")

            local_now = now_utc.astimezone(tz)
            if local_now.hour != cfg.send_hour_local:
                continue
            if cfg.last_run_date == local_now.date():
                continue

            try:
                stats = fanout_for_tenant(cfg.tenant_id, local_now.date())
                logger.info(
                    "[cron.horoscope] tenant=%s sent=%d skipped=%d failed=%d",
                    cfg.tenant_id, stats.get("sent", 0),
                    stats.get("skipped", 0), stats.get("failed", 0),
                )
                processed += 1
            except Exception as exc:
                logger.exception("[cron.horoscope] tenant=%s falha: %s",
                                 cfg.tenant_id, exc)
    finally:
        db.close()
    return processed

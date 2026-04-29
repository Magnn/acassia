"""
app.py — Versão SUPREME v8.7 (IMPÉRIO DA CIGANA - FULL INTEGRATION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O CENTRO DE COMANDO DEFINITIVO — VERSÃO INTEGRAL E SEM RESUMOS

ESTA VERSÃO É O ÁPICE DA ARQUITETURA MAGNO 2026:
  - Dashboard Server: Serve o dashboard.html e fornece dados via API.
  - LeadInboxManager: Fila inteligente com fusão de mensagens (Coalescing).
  - Webhook Meta: Processamento multimodal (Texto, Imagem, Áudio).
  - STT Gemini Pro: Transcrição nativa de áudios para o motor de estados.
  - Webhook Cakto: Gatilho imediato de pós-venda e entrega.
  - Segurança de Elite: Validação HMAC SHA256 obrigatória.
  - CORS Master: Habilitado para comunicação fluida entre front e back.
"""

import os
import sys
import hmac
import hashlib
import logging
import threading
import time
import requests
import base64
import glob
import queue
import json
import random
import re
import uuid
from decimal import Decimal
from collections import deque
from flask import Flask, request, jsonify, redirect, send_from_directory
from flask_login import login_required
from api.saas.auth import require_role

# Atalho: rotas administrativas (criar/editar fluxos, agentes, segredos) usam:
#   @login_required
#   @require_admin
# Tarólogos comuns (role='user') ficam restritos às rotas /saas/* já protegidas
# pelos blueprints SaaS dedicados.
require_admin = require_role("admin")
from werkzeug.utils import secure_filename
from flask_cors import CORS 
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# ── AJUSTE DE PATH E AMBIENTE ────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

load_dotenv()

# ── SENTRY (opcional) ────────────────────────────────────────────────
_SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
if _SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        import logging as _logging_sentry

        _sentry_traces = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1") or "0.1")
        _sentry_profile = float(os.getenv("SENTRY_PROFILE_SAMPLE_RATE", "0.1") or "0.1")
        _sentry_env     = os.getenv("SENTRY_ENVIRONMENT", "production")

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            environment=_sentry_env,
            # Logs nativos (Sentry Logs tab) — requer sentry-sdk >= 2.x
            enable_logs=True,
            # Tracing: % das requisições Flask que viram transações de performance
            traces_sample_rate=_sentry_traces,
            # Profiling: % das transações tracadas que também fazem profiling de CPU
            profile_session_sample_rate=_sentry_profile,
            profile_lifecycle="trace",
            # Não enviar IPs nem headers de usuário (LGPD)
            send_default_pii=False,
            integrations=[
                FlaskIntegration(),
                # logger.error() → Issue Sentry  |  logger.warning() → Breadcrumb
                LoggingIntegration(
                    level=_logging_sentry.WARNING,   # breadcrumbs a partir de WARNING
                    event_level=_logging_sentry.ERROR,  # Issue a partir de ERROR
                ),
            ],
        )
        print(f"[SENTRY] Inicializado — env={_sentry_env} traces={_sentry_traces} profile={_sentry_profile}")
    except ImportError:
        print("[SENTRY] sentry-sdk não instalado. Execute: pip install 'sentry-sdk[flask]'")
    except Exception as _sentry_err:
        print(f"[SENTRY] Falha ao inicializar: {_sentry_err}")

# Consola Windows: evita linhas de log partidas com emojis (UTF-8).
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── INFRAESTRUTURA DE BANCO E MODELOS ────────────────────────────────
from sqlalchemy import func, case, text
from sqlalchemy.exc import IntegrityError
from db import database, models
from db.database import engine, Base, SessionLocal
from tenant_context import get_request_tenant_id, get_engine_tenant_id
from analytics.personalizacao_audit import auditar_personalizacao

# ── MOTOR DE PROCESSAMENTO E IA ──────────────────────────────────────
from engine import Engine
from personalizer import Personalizer
from config_cliente import CONFIG_CLIENTE, cakto_webhook_deve_iniciar_pos_venda
from schema import Acao

# ── CONFIGURAÇÃO DE LOGGING ESTRUTURADO ───────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Menos ruído: requisições HTTP da SDK e "AFC is enabled" em cada chamada ao Gemini
for _log_ruido in ("httpx", "httpcore", "google_genai.models", "werkzeug"):
    logging.getLogger(_log_ruido).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
_APP_STARTED_AT = time.time()

# ── CONFIGURAÇÕES GLOBAIS ────────────────────────────────────────────
VERIFY_TOKEN    = os.getenv("VERIFY_TOKEN")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
WEBAPP_TOKEN    = os.getenv("WEBAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WABA_ID         = (os.getenv("WABA_ID") or "").strip()
APP_SECRET      = os.getenv("APP_SECRET", "") 
STT_MODEL       = CONFIG_CLIENTE.get("modelo_stt", "gemini-2.5-flash")

# Diretórios de Sistema
DOWNLOAD_DIR    = os.path.join(_ROOT, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
REPORTS_DIR = os.path.join(_ROOT, "scripts", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Cache de Idempotência (Evita processar a mesma msg do WhatsApp 2x)
CACHE_MENSAGENS   = deque(maxlen=2000)
LOCK_IDEMPOTENCIA = threading.Lock()


def _try_claim_wamid_db(wamid: str) -> bool:
    """
    True = primeira vez (seguir para a fila). False = wamid já persistido (at-least-once / restart).
    """
    if not wamid:
        return True
    tid = get_engine_tenant_id()
    db = SessionLocal()
    try:
        db.add(
            models.WhatsAppInboundReceipt(
                tenant_id=tid,
                wamid=str(wamid)[:128],
                lead_id=None,
            )
        )
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    except Exception as e:
        db.rollback()
        logger.warning("⚠️ [WEBHOOK] claim wamid falhou (fail-open processa 1x): %s", e)
        return True
    finally:
        db.close()

# ── INICIALIZAÇÃO DA APLICAÇÃO ───────────────────────────────────────
app = Flask(__name__)

# Secret key — necessária para sessions (flask-login flash, CSRF, etc).
# Em prod, defina FLASK_SECRET_KEY no .env (estável; mudar invalida sessões).
# Em dev, gera uma chave volátil ao subir (sessões morrem ao reiniciar — OK).
import secrets as _secrets_module
_secret = (os.getenv("FLASK_SECRET_KEY") or "").strip()
if not _secret:
    _secret = _secrets_module.token_urlsafe(48)
    logger.warning(
        "⚠️ [SECURITY] FLASK_SECRET_KEY não definida — usando chave volátil (sessões morrem ao restart). "
        "Em prod, defina no .env.",
    )
app.config["SECRET_KEY"] = _secret


# ── CORS ─────────────────────────────────────────────────────────────
# Em prod, FRONTEND_ORIGINS deve listar origens permitidas (vírgula-separadas).
# Ex.: FRONTEND_ORIGINS=https://app.acassia.com.br,https://acassia.com.br
# Em dev, fallback liberal pra localhost:5173 (Vite) e 5000 (Flask same-origin).
_cors_env = (os.getenv("FRONTEND_ORIGINS") or "").strip()
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    _cors_origins = [
        "http://localhost:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5173",
    ]
    logger.warning(
        "⚠️ [SECURITY] FRONTEND_ORIGINS não definida — usando lista dev (localhost). "
        "Em prod, defina no .env com domínios reais separados por vírgula.",
    )
CORS(app, origins=_cors_origins, supports_credentials=True)

# ── Rate limiting ────────────────────────────────────────────────────
# Protege endpoints sensíveis contra brute-force.
# Storage: Redis (se REDIS_URL setada) ou memória (single-process só).
# Limiter vive em extensions.py pra ser importável de blueprints sem
# import circular (auth.py decora rotas com @limiter.limit(...)).
from extensions import limiter

_limiter_storage = (os.getenv("REDIS_URL") or "").strip()
app.config["RATELIMIT_STORAGE_URI"] = _limiter_storage if _limiter_storage else "memory://"
app.config["RATELIMIT_HEADERS_ENABLED"] = True  # X-RateLimit-* nas respostas
limiter.init_app(app)
if not _limiter_storage:
    logger.warning(
        "⚠️ [SECURITY] flask-limiter usando storage in-memory — limites zeram a cada restart "
        "e não são compartilhados entre workers. Configure REDIS_URL pra prod.",
    )

# ─────────────────────────────────────────────────────────────────────
# REGISTRO DE BLUEPRINTS SaaS
# Os blueprints abaixo definem rotas /saas/* consumidas pelo painel React.
# Se algum import falhar, deixa o erro subir — sem fail silencioso.
# ─────────────────────────────────────────────────────────────────────
def _register_saas_blueprints():
    from api.saas.auth import auth_bp, login_manager
    from api.saas.onboarding import onboarding_bp
    from api.saas.inbox import inbox_bp
    from api.saas.metrics import metrics_bp
    from api.saas.settings import settings_bp
    from api.saas.connect import connect_bp
    from api.saas.billing import billing_bp
    from api.saas.whatsapp import whatsapp_bp
    from api.telemetry import telemetry_bp
    from api.admin.twofa import twofa_bp
    from api.admin.tenants import admin_tenants_bp
    from api.admin.impersonate import impersonate_bp
    from api.admin.lifecycle import lifecycle_bp
    from api.admin.commercial import commercial_bp
    from api.admin.metrics import metrics_bp as admin_metrics_bp
    from api.saas.security import security_bp
    from api.saas.privacy import privacy_bp
    from api.saas.analytics import analytics_bp as saas_analytics_bp
    from api.saas.templates import templates_bp as saas_templates_bp
    from api.saas.tarot import tarot_bp as saas_tarot_bp
    from api.saas.pix import pix_bp as saas_pix_bp
    from api.saas.voice import voice_bp as saas_voice_bp
    from api.saas.coach import coach_bp as saas_coach_bp
    from api.saas.affiliate import affiliate_bp as saas_affiliate_bp, referral_bp as saas_referral_bp
    from api.saas.lunar_api import lunar_bp as saas_lunar_bp
    from api.saas.marketplace import (
        marketplace_bp as saas_marketplace_bp,
        admin_marketplace_bp as saas_admin_marketplace_bp,
    )
    from api.saas.horoscope import horoscope_bp as saas_horoscope_bp
    from api.saas.spiritual import spiritual_bp as saas_spiritual_bp

    login_manager.init_app(app)
    for bp in (
        auth_bp,
        onboarding_bp,
        inbox_bp,
        metrics_bp,
        settings_bp,
        connect_bp,
        billing_bp,
        whatsapp_bp,
        telemetry_bp,
        twofa_bp,
        admin_tenants_bp,
        impersonate_bp,
        lifecycle_bp,
        commercial_bp,
        admin_metrics_bp,
        security_bp,
        privacy_bp,
        saas_analytics_bp,
        saas_templates_bp,
        saas_tarot_bp,
        saas_pix_bp,
        saas_voice_bp,
        saas_coach_bp,
        saas_affiliate_bp,
        saas_referral_bp,
        saas_lunar_bp,
        saas_marketplace_bp,
        saas_admin_marketplace_bp,
        saas_horoscope_bp,
        saas_spiritual_bp,
    ):
        app.register_blueprint(bp)


try:
    _register_saas_blueprints()
except Exception as _e:
    logger.error("[SAAS] Falha registrando blueprints: %s", _e)
    raise

# Sincronização Obrigatória do Banco de Dados
def _ensure_mensagens_media_url_column():
    """Migração leve para bancos existentes: garante `mensagens.media_url`."""
    try:
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(mensagens)")).fetchall()
            names = {str(c[1]).lower() for c in cols if len(c) > 1}
            if "media_url" not in names:
                conn.execute(text("ALTER TABLE mensagens ADD COLUMN media_url TEXT"))
                logger.info("🧩 [DATABASE] Coluna mensagens.media_url adicionada.")
    except Exception as e:
        logger.warning(f"⚠️ [DATABASE] Não foi possível garantir media_url: {e}")

def _ensure_leads_tenant_id_column():
    """Migração leve: garante `leads.tenant_id` em bases antigas."""
    try:
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(leads)")).fetchall()
            names = {str(c[1]).lower() for c in cols if len(c) > 1}
            if "tenant_id" not in names:
                conn.execute(text("ALTER TABLE leads ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'default'"))
                logger.info("🧩 [DATABASE] Coluna leads.tenant_id adicionada.")
    except Exception as e:
        logger.warning(f"⚠️ [DATABASE] Não foi possível garantir tenant_id em leads: {e}")

def _ensure_leads_metadata_version_column():
    """Merge otimista em metadata_json (motor vs fila de envio)."""
    try:
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(leads)")).fetchall()
            names = {str(c[1]).lower() for c in cols if len(c) > 1}
            if "metadata_version" not in names:
                conn.execute(text("ALTER TABLE leads ADD COLUMN metadata_version INTEGER NOT NULL DEFAULT 0"))
                logger.info("🧩 [DATABASE] Coluna leads.metadata_version adicionada.")
    except Exception as e:
        logger.warning(f"⚠️ [DATABASE] Não foi possível garantir metadata_version em leads: {e}")

try:
    Base.metadata.create_all(bind=engine)
    _ensure_leads_tenant_id_column()
    _ensure_mensagens_media_url_column()
    _ensure_leads_metadata_version_column()
    logger.info("✅ [DATABASE] Tabelas sincronizadas com sucesso.")
except Exception as e:
    logger.critical(f"🚨 [DATABASE] Falha ao sincronizar banco: {e}")
    sys.exit(1)

from api.flow_platform import register_flow_platform_routes

register_flow_platform_routes(app)

# Inicialização dos Motores de IA
personalizer = Personalizer(api_key=GEMINI_API_KEY)
motor = Engine(
    whatsapp_token=WEBAPP_TOKEN,
    whatsapp_phone_id=PHONE_NUMBER_ID,
    personalizer=personalizer,
    gemini_api_key=GEMINI_API_KEY,
    tenant_id=get_engine_tenant_id(),
)

# ─────────────────────────────────────────────────────────────────────
# GESTÃO DE FILA POR LEAD (LeadInboxManager)
# ─────────────────────────────────────────────────────────────────────
class LeadInboxManager:
    """
    Ordem cronológica + fusão de texto.
    Fluxo: (1) funde rajada imediata na fila; (2) espera silêncio (sem novas mensagens) por
    inbox_silence_seconds; (3) só então processa um único batch — a IA vê o contexto completo antes de responder.
    """
    def __init__(self):
        self.inboxes = {}
        self.lock = threading.Lock()
        self._dedup_lock = threading.Lock()
        self._recent_fp_by_phone = {}
        self.max_busy_retries = int(CONFIG_CLIENTE.get("inbox_max_retries_busy", 8) or 8)
        self.max_fila_por_lead = int(CONFIG_CLIENTE.get("inbox_max_tamanho_fila_por_lead", 96) or 96)
        self.coalesce_s = max(1.0, min(float(CONFIG_CLIENTE.get("inbox_coalesce_seconds", 3) or 3), 12.0))
        self.silence_s = max(0.0, min(float(CONFIG_CLIENTE.get("inbox_silence_seconds", 25) or 25), 120.0))
        self.dedupe_window_s = max(
            5.0, min(float(CONFIG_CLIENTE.get("inbox_dedupe_window_seconds", 45) or 45), 180.0)
        )
        self.static_block_cooldown_s = max(
            0.0, min(float(CONFIG_CLIENTE.get("inbox_static_block_cooldown_seconds", 90) or 90), 600.0)
        )
        self.after_text_grace_s = max(
            0.0, min(float(CONFIG_CLIENTE.get("inbox_after_text_grace_seconds", 20) or 20), 60.0)
        )
        self.after_text_grace_min_chars = int(CONFIG_CLIENTE.get("inbox_after_text_grace_min_chars", 40) or 40)
        self._sem_processamento = threading.BoundedSemaphore(
            value=max(4, int(CONFIG_CLIENTE.get("inbox_max_concorrencia_processamento", 24) or 24))
        )
        self._re_confirmacao_curta = re.compile(
            r"\b(ok|sim|pronto|salvo|beleza|blz|show|feito|entendi|combinado)\b",
            re.I,
        )
        self._re_feedback_entrega = re.compile(
            r"\b(cortad[ao]|incomplet[ao]|atropel|card|cart[aã]o\s+de\s+contato|"
            r"n[aã]o\s+deu\s+tempo|n[aã]o\s+deu\s+pra\s+ver)\b",
            re.I,
        )
        self._re_intencao_midia = re.compile(
            r"\b(foto|imagem|palma|m[aã]o|mao|print|selfie|enviei\s+foto|mandei\s+foto)\b",
            re.I,
        )

    @staticmethod
    def _parse_iso_utc(raw: str):
        s = str(raw or "").strip()
        if not s:
            return None
        try:
            s = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            return None

    @staticmethod
    def _payload_fingerprint(payload: dict) -> str:
        tipo = str(payload.get("tipo_mensagem") or "text").strip().lower()
        texto = re.sub(r"\s+", " ", str(payload.get("texto_recebido") or "").strip().lower())[:240]
        media_id = str(payload.get("meta_media_id") or "").strip()
        media_url = str(payload.get("media_url") or payload.get("imagem_url") or "").strip().lower()
        if len(media_url) > 160:
            media_url = media_url[-160:]
        msg_id = str(payload.get("meta_msg_id") or "").strip()
        raw = f"{tipo}|{texto}|{media_id}|{media_url}|{msg_id}"
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()

    def _is_recent_duplicate(self, telefone: str, payload: dict) -> bool:
        now = time.time()
        fp = self._payload_fingerprint(payload)
        with self._dedup_lock:
            dq = self._recent_fp_by_phone.setdefault(telefone, deque())
            while dq and (now - float(dq[0][0])) > self.dedupe_window_s:
                dq.popleft()
            if any((old_fp == fp) for _, old_fp in dq):
                return True
            dq.append((now, fp))
            if len(dq) > 300:
                dq.popleft()
        return False

    def _should_skip_static_cooldown(self, telefone: str, payload: dict) -> bool:
        if self.static_block_cooldown_s <= 0:
            return False
        tipo = str(payload.get("tipo_mensagem") or "text").strip().lower()
        if tipo in ("audio", "image", "video"):
            return False
        tx = str(payload.get("texto_recebido") or "").strip()
        if not tx:
            return False
        palavras = tx.split()
        if len(palavras) > 8 or not self._re_confirmacao_curta.search(tx):
            return False
        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter_by(
                telefone=telefone, tenant_id=get_engine_tenant_id()
            ).first()
            if not lead:
                return False
            node = str(getattr(lead, "node_atual", "") or "")
            if not node.startswith("static_meumisterio_"):
                return False
            md = _lead_metadata_as_dict(getattr(lead, "metadata_json", None))
            key = node.replace("static_meumisterio_", "static_mm_") + "_last_sent_at"
            dt_last = self._parse_iso_utc(md.get(key))
            if not dt_last:
                return False
            delta = (datetime.now(timezone.utc) - dt_last).total_seconds()
            if delta < self.static_block_cooldown_s:
                self._auditar_busy_por_telefone(
                    telefone,
                    "inbox_static_cooldown_skip",
                    {
                        "node_atual": node,
                        "delta_s": round(float(delta), 2),
                        "cooldown_s": round(float(self.static_block_cooldown_s), 2),
                    },
                )
                logger.info(
                    "🧊 [FILA] Cooldown estático: suprimindo replay curto para %s (node=%s delta=%.1fs).",
                    telefone,
                    node,
                    delta,
                )
                return True
            return False
        finally:
            db.close()

    @staticmethod
    def _merge_payload(base: dict, extra: dict) -> dict:
        """Funde dois payloads do webhook (texto, imagem, áudio)."""
        if extra.get("tipo_mensagem") == "audio":
            return dict(extra)
        p = dict(base)
        if extra.get("texto_recebido"):
            et = str(extra["texto_recebido"]).strip()
            if et:
                pt = str(p.get("texto_recebido") or "").strip()
                # Não usar "|" como separador: esse símbolo já vazou em prompts/copy.
                p["texto_recebido"] = f"{pt}. {et}".strip(" .") if pt else et
        if extra.get("imagem_url"):
            p["imagem_url"] = extra["imagem_url"]
            p["tipo_mensagem"] = "image"
        if extra.get("media_url"):
            p["media_url"] = extra["media_url"]
        if p.get("imagem_url") and p.get("tipo_mensagem") == "text":
            p["tipo_mensagem"] = "image"
        return p

    def _drenar_rajada_imediata(self, q, payload: dict) -> dict:
        """Consome tudo que já está na fila (mesmo burst Meta) e funde."""
        merged = dict(payload)
        while True:
            try:
                extra = q.get_nowait()
                merged = self._merge_payload(merged, extra)
                q.task_done()
            except queue.Empty:
                break
        return merged

    def _silence_period(self, q, payload: dict, timeout_sec: float) -> dict:
        """Espera `timeout_sec` sem novos itens; cada item reinicia a janela e drena rajada."""
        merged = dict(payload)
        if timeout_sec <= 0:
            return merged
        while True:
            try:
                extra = q.get(timeout=timeout_sec)
                merged = self._merge_payload(merged, extra)
                q.task_done()
                merged = self._drenar_rajada_imediata(q, merged)
            except queue.Empty:
                break
        return merged

    def _esperar_silencio_do_lead(self, q, payload: dict) -> dict:
        """
        Após a última mensagem visível na fila, espera `silence_s` sem novos itens.
        Cada nova mensagem reinicia a janela e volta a drenar rajada.
        """
        return self._silence_period(q, payload, self.silence_s)

    def _deve_grace_midia_pos_texto(self, payload: dict) -> bool:
        if self.after_text_grace_s <= 0:
            return False
        if payload.get("imagem_url"):
            return False
        if payload.get("media_url"):
            return False
        tipo = str(payload.get("tipo_mensagem") or "text").lower()
        if tipo in ("image", "video", "audio"):
            return False
        tx = str(payload.get("texto_recebido") or "").strip()
        if self._re_feedback_entrega.search(tx):
            # Lead reclamou de corte/cadência: não adicionar espera extra para mídia.
            return False
        # Confirmações curtas não precisam grace adicional.
        palavras = tx.split()
        if len(palavras) <= 8 and self._re_confirmacao_curta.search(tx):
            return False
        if len(tx) < self.after_text_grace_min_chars:
            return False
        # Grace só faz sentido quando há chance real de mídia chegar no webhook seguinte.
        if not self._re_intencao_midia.search(tx):
            return False
        return True

    def _esperar_grace_midia_pos_texto(self, q, payload: dict, telefone: str) -> dict:
        """Segunda janela de silêncio após texto longo: imagem costuma vir em webhook separado (latência Meta)."""
        if not self._deve_grace_midia_pos_texto(payload):
            return payload
        logger.info(
            "⏳ [FILA] Grace pós-texto (mídia) para %s: %.1fs extra após lote principal",
            telefone,
            self.after_text_grace_s,
        )
        out = self._silence_period(q, payload, self.after_text_grace_s)
        out["_inbox_after_text_grace"] = True
        return out

    @staticmethod
    def _auditar_busy_por_telefone(telefone: str, evento: str, dados: dict):
        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter_by(
                telefone=telefone, tenant_id=get_engine_tenant_id()
            ).first()
            if not lead:
                return
            payload_audit = dict(dados or {})
            if evento == "engine_busy_discarded":
                payload_audit["node_atual"] = str(getattr(lead, "node_atual", "") or "")
                raw = payload_audit.pop("_texto_recebido_preview", None)
                if raw is not None:
                    s = str(raw).strip()
                    if s:
                        payload_audit["texto_preview"] = (s[:117] + "…") if len(s) > 120 else s
            db.add(
                models.EventoAudit(
                    lead_id=lead.id,
                    evento=evento,
                    dados=payload_audit,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def _auditar_batch_pronto(self, telefone: str, payload: dict) -> None:
        """Regista batch processado com sucesso pelo motor (debounce já aplicado). Sem texto completo nos dados."""
        tx = str(payload.get("texto_recebido") or "").strip()
        partes = max(1, len([s for s in re.split(r"[.!?]\s+", tx) if s.strip()])) if tx else 1
        self._auditar_busy_por_telefone(
            telefone,
            "inbox_batch_pronto",
            {
                "silence_s": round(float(self.silence_s), 2),
                "after_text_grace_s": round(float(self.after_text_grace_s), 2)
                if payload.get("_inbox_after_text_grace")
                else 0.0,
                "chars": len(tx),
                "tipo_mensagem": str(payload.get("tipo_mensagem") or "text"),
                "partes_fundidas": partes,
            },
        )

    def enqueue(self, telefone, payload):
        if self._is_recent_duplicate(telefone, payload):
            logger.info("♻️ [FILA] Duplicata recente suprimida para %s.", telefone)
            self._auditar_busy_por_telefone(
                telefone,
                "inbox_dedupe_suppressed",
                {"window_s": round(float(self.dedupe_window_s), 2)},
            )
            return
        with self.lock:
            if telefone not in self.inboxes:
                self.inboxes[telefone] = queue.Queue()
                thread_name = f"Worker-{telefone[-4:]}"
                threading.Thread(target=self._worker, args=(telefone,), daemon=True, name=thread_name).start()
        q = self.inboxes[telefone]
        merged = dict(payload)
        if q.qsize() >= self.max_fila_por_lead:
            try:
                old = q.get_nowait()
                q.task_done()
                merged = self._merge_payload(old, merged)
                self._auditar_busy_por_telefone(
                    telefone,
                    "inbox_backpressure_merged_oldest",
                    {"max_queue": self.max_fila_por_lead},
                )
                logger.warning("⚠️ [FILA] Backpressure: fundido item mais antigo com novo para %s", telefone)
            except Exception:
                pass
        q.put(merged)
        logger.info(f"📥 [FILA] Mensagem enfileirada para {telefone}.")

    def _worker(self, telefone):
        q = self.inboxes[telefone]
        while True:
            try:
                # Aguarda nova mensagem (timeout de 5 minutos de inatividade)
                payload = q.get(timeout=300)
                q.task_done()

                # 1) Funde tudo que já chegou em seguida (mesmo burst)
                payload = self._drenar_rajada_imediata(q, payload)
                # 2) Só processa após silêncio do lead (config inbox_silence_seconds)
                payload = self._esperar_silencio_do_lead(q, payload)
                # 3) Texto longo sem mídia: espera extra para imagem atrasada (webhook separado)
                payload = self._esperar_grace_midia_pos_texto(q, payload, telefone)

                tx = str(payload.get("texto_recebido") or "").strip()
                logger.info(
                    "📦 [FILA] Batch pronto para %s (silence_s=%.1fs, grace_extra=%s, chars=%s)",
                    telefone,
                    self.silence_s,
                    bool(payload.get("_inbox_after_text_grace")),
                    len(tx),
                )
                if self._should_skip_static_cooldown(telefone, payload):
                    continue

                # Despacha para o motor de estados
                acquired = False
                try:
                    acquired = self._sem_processamento.acquire(timeout=8)
                    if not acquired:
                        retry_payload = dict(payload)
                        retries = int(retry_payload.get("_busy_retries", 0) or 0) + 1
                        retry_payload["_busy_retries"] = retries
                        q.put(retry_payload)
                        self._auditar_busy_por_telefone(
                            telefone,
                            "engine_capacity_requeued",
                            {"tentativa": retries},
                        )
                        continue

                    motor_payload = dict(payload)
                    motor_payload.pop("_inbox_after_text_grace", None)
                    result = motor.processar_mensagem(**motor_payload) or {}
                    if result.get("status") != "busy":
                        self._auditar_batch_pronto(telefone, payload)
                    if result.get("status") == "busy":
                        retries = int(payload.get("_busy_retries", 0) or 0) + 1
                        if retries <= self.max_busy_retries:
                            retry_payload = dict(payload)
                            retry_payload["_busy_retries"] = retries
                            wait_s = min(5.0, 1.5 * retries + random.uniform(0.2, 1.0))
                            logger.info(
                                "⏳ [FILA] Motor busy para %s; requeue automático tentativa=%s em %.1fs.",
                                telefone,
                                retries,
                                wait_s,
                            )
                            self._auditar_busy_por_telefone(
                                telefone,
                                "engine_busy_requeued",
                                {"tentativa": retries, "espera_s": round(float(wait_s), 3)},
                            )
                            time.sleep(wait_s)
                            q.put(retry_payload)
                        else:
                            logger.warning(
                                "⚠️ [FILA] Motor busy persistente para %s; descartando após %s tentativas.",
                                telefone,
                                retries - 1,
                            )
                            self._auditar_busy_por_telefone(
                                telefone,
                                "engine_busy_discarded",
                                {
                                    "tentativas": retries - 1,
                                    "_texto_recebido_preview": payload.get("texto_recebido"),
                                },
                            )
                except Exception as e:
                    logger.error(f"🚨 [ENGINE ERROR] Falha no processamento de {telefone}: {e}", exc_info=True)
                finally:
                    if acquired:
                        try:
                            self._sem_processamento.release()
                        except Exception:
                            pass
            except queue.Empty:
                with self.lock:
                    self.inboxes.pop(telefone, None)
                logger.debug(f"💤 [FILA] Worker para {telefone} encerrado por inatividade.")
                break
            except Exception as e:
                logger.error(f"🚨 [FILA ERROR] Erro fatal no worker de {telefone}: {e}")

inbox_manager = LeadInboxManager()

# ─────────────────────────────────────────────────────────────────────
# ROTAS DO DASHBOARD E API (INTEGRAÇÃO IMPERIAL)
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# FLOW BUILDER REACT (SPA servido a partir de frontend/dist)
# ─────────────────────────────────────────────────────────────────────
_FRONTEND_DIST = os.path.join(_ROOT, "frontend", "dist")


def _flow_builder_react_enabled() -> bool:
    """FLOW_BUILDER_REACT=1/true/yes ativa redirect /dashboard → /builder/."""
    val = (os.getenv("FLOW_BUILDER_REACT", "") or "").strip().lower()
    return val in ("1", "true", "yes", "on")


@app.route("/dashboard")
def render_dashboard():
    """Serve a interface administrativa.

    Se ``FLOW_BUILDER_REACT`` estiver ativo no ambiente E o build React
    estiver disponível, redireciona pra ``/builder/``. Bypass via
    ``?legacy=1`` mantém o builder antigo acessível como fallback.
    """
    use_react = (
        _flow_builder_react_enabled()
        and os.path.isfile(os.path.join(_FRONTEND_DIST, "index.html"))
        and request.args.get("legacy") not in ("1", "true", "yes")
    )
    if use_react:
        return redirect("/builder/", code=302)
    return send_from_directory(_ROOT, "dashboard.html")


@app.route("/builder", defaults={"path": ""})
@app.route("/builder/", defaults={"path": ""})
@app.route("/builder/<path:path>")
def render_builder_spa(path: str):
    """Serve o SPA do Flow Builder; rota client-side cai em index.html."""
    if path:
        candidate = os.path.join(_FRONTEND_DIST, path)
        if os.path.isfile(candidate):
            return send_from_directory(_FRONTEND_DIST, path)
    index_path = os.path.join(_FRONTEND_DIST, "index.html")
    if not os.path.isfile(index_path):
        return (
            "Flow Builder não compilado — rode `cd frontend && npm install && npm run build`.",
            503,
        )
    return send_from_directory(_FRONTEND_DIST, "index.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Logos e ficheiros estáticos do dashboard (ex.: integrações)."""
    return send_from_directory(os.path.join(_ROOT, "assets"), filename)


@app.route("/media/<filename>")
def serve_media(filename):
    """Serve mídias baixadas (fotos da mão/áudios)."""
    return send_from_directory(DOWNLOAD_DIR, filename)


@app.route("/api/media/upload", methods=["POST"])
def api_media_upload():
    """
    Upload para a pasta `downloads/` — URL devolvida (/media/…) para usar no bloco Conteúdo do flow builder.
    Limites: tipos comuns de imagem/vídeo/áudio/documento; máx. 40MB.
    """
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "ficheiro em falta (campo 'file')"}), 400
    f = request.files["file"]
    if not f or not getattr(f, "filename", None):
        return jsonify({"ok": False, "error": "nome de ficheiro inválido"}), 400
    orig = str(f.filename or "")
    ext = os.path.splitext(orig)[1].lower()
    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".mp4",
        ".mov",
        ".webm",
        ".avi",
        ".ogg",
        ".mp3",
        ".m4a",
        ".wav",
        ".pdf",
        ".doc",
        ".docx",
    }
    if ext not in allowed:
        return jsonify({"ok": False, "error": f"extensão não permitida: {ext or '(vazia)'}"}), 400
    max_b = 40 * 1024 * 1024
    try:
        f.seek(0, os.SEEK_END)
        sz = f.tell()
        f.seek(0)
    except Exception:
        sz = int(request.content_length or -1)
    if sz > max_b > 0:
        return jsonify({"ok": False, "error": "ficheiro demasiado grande (máx. 40MB)"}), 400
    safe_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(DOWNLOAD_DIR, safe_name)
    try:
        f.save(path)
    except Exception as e:
        logger.error("[API] /api/media/upload save: %s", e)
        return jsonify({"ok": False, "error": "falha ao gravar ficheiro"}), 500
    orig_disp = secure_filename(orig) or safe_name
    return jsonify(
        {
            "ok": True,
            "url": f"/media/{safe_name}",
            "filename": safe_name,
            "original_filename": orig_disp,
        }
    ), 200


def _humanize_delta_pt(ts: datetime, now: datetime) -> str:
    """Ex.: 'há 10 dias', 'há 3 horas' — para UI do chat."""
    delta = now - ts
    sec = max(0, int(delta.total_seconds()))
    if sec < 60:
        return "agora há pouco"
    if sec < 3600:
        m = sec // 60
        return "há 1 minuto" if m == 1 else f"há {m} minutos"
    if delta.days == 0:
        h = sec // 3600
        return "há 1 hora" if h == 1 else f"há {h} horas"
    d = delta.days
    return "há 1 dia" if d == 1 else f"há {d} dias"


def _whatsapp_care_window_info(db, lead_id: int) -> dict:
    """
    Contexto da janela de atendimento ao cliente (regra comercial usual da Meta:
    ~24h após a última mensagem recebida do usuário para mensagens de sessão).
    Fora desse período, envios proativos costumam exigir templates (HSM) aprovados.
    """
    row = (
        db.query(models.Mensagem)
        .filter_by(lead_id=lead_id, remetente="user")
        .order_by(models.Mensagem.timestamp.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if not row or not row.timestamp:
        return {
            "last_user_message_at": None,
            "customer_care_window_until": None,
            "within_24h_session": False,
            "last_user_message_label_pt": "Nenhuma mensagem recebida do lead ainda.",
        }
    ts = row.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    until = ts + timedelta(hours=24)
    hum = _humanize_delta_pt(ts, now)
    return {
        "last_user_message_at": ts.isoformat(),
        "customer_care_window_until": until.isoformat(),
        "within_24h_session": bool(now <= until),
        "last_user_message_label_pt": f"Última mensagem do lead foi {hum}.",
    }


def _lead_metadata_as_dict(raw) -> dict:
    """metadata_json pode vir como dict (SQLAlchemy JSON) ou string legada."""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        out = dict(raw)
        out.pop("__config__", None)
        return out
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {}


def _normalizar_static_target_node(raw: str) -> str:
    s = (raw or "").strip().lower().replace(" ", "").replace("-", "_")
    if not s:
        return ""
    if s in {"b1", "b2", "b3", "b4", "b5", "b6"}:
        return f"static_meumisterio_{s}"
    if s.startswith("static_meumisterio_"):
        return s
    if s.startswith("static_meumisteriob") and len(s) > len("static_meumisteriob"):
        return "static_meumisterio_" + s.split("static_meumisteriob", 1)[1]
    if s.startswith("static_mm_b"):
        return "static_meumisterio_" + s.split("static_mm_", 1)[1]
    return s


def _next_static_node(node: str) -> str:
    order = (
        "static_meumisterio_b1",
        "static_meumisterio_b2",
        "static_meumisterio_b3",
        "static_meumisterio_b4",
        "static_meumisterio_b5",
        "static_meumisterio_b6",
    )
    try:
        idx = order.index(str(node or ""))
    except ValueError:
        return ""
    if idx >= len(order) - 1:
        return ""
    return order[idx + 1]


def _bot_state_snapshot_for_lead(db, lead) -> dict:
    md = _lead_metadata_as_dict(getattr(lead, "metadata_json", None))
    node = str(getattr(lead, "node_atual", "") or "")
    phase = ""
    if node == "static_meumisterio_b1":
        phase = str(md.get("static_mm_b1_phase") or "")
    elif node == "static_meumisterio_b2":
        phase = str(md.get("static_mm_b2_phase") or "")
    elif node == "static_meumisterio_b3":
        phase = str(md.get("static_mm_b3_phase") or "")
    elif node == "static_meumisterio_b4":
        phase = str(md.get("static_mm_b4_phase") or "")
    elif node == "static_meumisterio_b5":
        phase = str(md.get("static_mm_b5_phase") or "")
    elif node == "static_meumisterio_b6":
        phase = "awaiting_reply"

    last_user = (
        db.query(models.Mensagem)
        .filter(models.Mensagem.lead_id == lead.id, models.Mensagem.remetente == "user")
        .order_by(models.Mensagem.timestamp.desc())
        .first()
    )
    last_bot = (
        db.query(models.Mensagem)
        .filter(models.Mensagem.lead_id == lead.id, models.Mensagem.remetente == "bot")
        .order_by(models.Mensagem.timestamp.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    orphan_s = 0.0
    if last_user and getattr(last_user, "timestamp", None):
        tsu = last_user.timestamp
        if tsu.tzinfo is None:
            tsu = tsu.replace(tzinfo=timezone.utc)
        tsb = None
        if last_bot and getattr(last_bot, "timestamp", None):
            tsb = last_bot.timestamp
            if tsb.tzinfo is None:
                tsb = tsb.replace(tzinfo=timezone.utc)
        if tsb is None or tsb < tsu:
            orphan_s = max(0.0, float((now - tsu).total_seconds()))

    paused = bool(getattr(lead, "bot_pausado", False))
    waiting_reply = phase.startswith("awaiting")
    status = "running"
    action_hint = "Aguardar próximo turno normal."
    if paused:
        status = "paused_handoff"
        action_hint = "Clique em Reativar IA ou Retomar."
    elif waiting_reply:
        status = "waiting_reply"
        action_hint = "Aguardando resposta do lead para avançar."
    elif orphan_s >= 300:
        status = "orphan_waiting_delivery"
        action_hint = "Use Retomar para reprocessar o último turno."

    return _json_safe_for_api(
        {
            "status": status,
            "node_atual": node,
            "phase": phase,
            "waiting_reply": waiting_reply,
            "paused": paused,
            "orphan_wait_seconds": int(orphan_s),
            "last_user_at": last_user.timestamp.isoformat() if last_user and last_user.timestamp else None,
            "last_bot_at": last_bot.timestamp.isoformat() if last_bot and last_bot.timestamp else None,
            "action_hint": action_hint,
        }
    )


def _json_safe_for_api(obj):
    """Garante que metadados aninhados serializam em JSON (datetime, Decimal, etc.)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe_for_api(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe_for_api(x) for x in obj]
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    return str(obj)


def _load_report_json(filename: str) -> dict:
    path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_report_json(filename: str, payload: dict) -> str:
    path = os.path.join(REPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _to_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _load_meta_actions_history() -> list[dict]:
    data = _load_report_json("meta_actions_history.json")
    rows = data.get("rows") if isinstance(data, dict) else []
    return rows if isinstance(rows, list) else []


def _save_meta_actions_history(rows: list[dict]) -> None:
    _save_report_json("meta_actions_history.json", {"rows": rows[-500:]})


def _load_chat_ops_state() -> dict:
    data = _load_report_json("chat_ops_state.json")
    if not isinstance(data, dict):
        return {"operators": [], "rr_index": 0}
    data.setdefault("operators", [])
    data.setdefault("rr_index", 0)
    return data


def _save_chat_ops_state(state: dict) -> None:
    _save_report_json("chat_ops_state.json", state if isinstance(state, dict) else {"operators": [], "rr_index": 0})


def _emit_meta_event(event_name: str, telefone: str, value: float = 0.0, currency: str = "BRL") -> None:
    """
    Emite evento básico para Meta CAPI se os segredos estiverem configurados.
    Usa hash SHA256 do telefone como user_data.
    """
    pixel_id = os.getenv("META_PIXEL_ID", "").strip()
    token = os.getenv("META_ACCESS_TOKEN", "").strip()
    if not pixel_id or not token:
        return
    phone_digits = "".join(ch for ch in str(telefone or "") if ch.isdigit())
    if not phone_digits:
        return
    phone_hash = hashlib.sha256(phone_digits.encode("utf-8")).hexdigest()
    payload = {
        "data": [
            {
                "event_name": event_name,
                "event_time": int(time.time()),
                "action_source": "website",
                "user_data": {"ph": [phone_hash]},
                "custom_data": {"currency": currency, "value": float(value or 0.0)},
            }
        ]
    }
    endpoint = f"https://graph.facebook.com/v20.0/{pixel_id}/events?access_token={token}"
    try:
        requests.post(endpoint, json=payload, timeout=8)
    except Exception:
        pass


def _meta_graph_get(path: str, params: dict) -> dict:
    token = os.getenv("META_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("META_ACCESS_TOKEN não configurado")
    url = f"https://graph.facebook.com/v20.0/{path}"
    q = dict(params or {})
    q["access_token"] = token
    resp = requests.get(url, params=q, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Meta API erro {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _parse_purchase_from_actions(actions) -> float:
    if not isinstance(actions, list):
        return 0.0
    total = 0.0
    for a in actions:
        if not isinstance(a, dict):
            continue
        t = str(a.get("action_type") or "").lower()
        if "purchase" in t or "omni_purchase" in t:
            try:
                total += float(a.get("value") or 0.0)
            except Exception:
                continue
    return total


def _entity_meta_recommendation(entity: dict) -> dict:
    spend = float(entity.get("spend") or 0.0)
    roas = float(entity.get("roas") or 0.0)
    status = str(entity.get("status") or "").lower()
    urgency = "ok"
    action = "manter"
    reason = "Performance estável."
    if status in ("paused", "archived", "deleted"):
        urgency = "normal"
        action = "revisar"
        reason = "Item pausado/arquivado; validar se deve reativar."
    elif spend >= 80 and roas < 1.2:
        urgency = "alta"
        action = "pausar"
        reason = "Gasto alto com retorno baixo."
    elif spend >= 40 and roas < 1.6:
        urgency = "atencao"
        action = "otimizar_copy"
        reason = "ROAS abaixo do ideal; ajuste criativo e segmentação."
    elif roas >= 2.5 and spend >= 20:
        urgency = "ok"
        action = "escalar_10_20"
        reason = "Boa eficiência; pode escalar gradualmente."
    return {"urgency": urgency, "action": action, "reason": reason}


def _estimate_impact_brl(item: dict, action: str) -> float:
    spend = float(item.get("spend") or 0.0)
    purchases = float(item.get("purchases") or 0.0)
    roas = float(item.get("roas") or 0.0)
    if action == "pausar":
        return round(max(0.0, spend * max(0.0, 1.4 - roas)), 2)
    if action.startswith("escalar"):
        return round(max(0.0, purchases * 0.15), 2)
    if action == "otimizar_copy":
        return round(max(0.0, purchases * 0.08 + spend * 0.05), 2)
    return round(max(0.0, spend * 0.03), 2)


def _find_entity_in_snapshot(snapshot: dict, scope: str, entity_id: str) -> dict | None:
    if not isinstance(snapshot, dict):
        return None
    sid = str(entity_id or "").strip()
    if not sid:
        return None
    pools = []
    sc = str(scope or "").lower()
    if sc == "campanhas":
        pools = [snapshot.get("campaigns") or []]
    elif sc == "conjuntos":
        pools = [snapshot.get("top_adsets_by_spend") or []]
    elif sc == "anuncios":
        pools = [snapshot.get("top_ads_by_spend") or [], snapshot.get("top_ads_by_sales") or []]
    else:
        pools = [
            snapshot.get("campaigns") or [],
            snapshot.get("top_adsets_by_spend") or [],
            snapshot.get("top_ads_by_spend") or [],
            snapshot.get("top_ads_by_sales") or [],
        ]
    for arr in pools:
        for row in arr:
            if str((row or {}).get("id") or "").strip() == sid:
                return row
    return None


@app.route("/api/health", methods=["GET"])
def api_health():
    """Liveness para monitoramento e debug rápido."""
    return jsonify({
        "ok": True,
        "service": "cigana",
        "uptime_s": int(time.time() - _APP_STARTED_AT),
    }), 200


@app.route("/api/health/deep", methods=["GET"])
def api_health_deep():
    """
    Readiness probe — checa dependências críticas (DB, Redis, Gemini).
    Retorna 200 se tudo OK ou Redis/Gemini estão "disabled" (não configurados).
    Retorna 503 se algum check obrigatório falhou (DB).

    Use em load balancer / k8s readinessProbe pra evitar rotear tráfego pra
    instância com DB caindo. Liveness (/api/health) continua barato.
    """
    started = time.perf_counter()
    checks: dict[str, dict] = {}

    # ── DB: SELECT 1 ─────────────────────────────────────────────────
    db_ok = False
    try:
        from db.database import SessionLocal
        from sqlalchemy import text
        _db = SessionLocal()
        try:
            _db.execute(text("SELECT 1"))
            db_ok = True
            checks["database"] = {"status": "ok"}
        finally:
            _db.close()
    except Exception as exc:
        checks["database"] = {"status": "error", "error": str(exc)[:200]}

    # ── Redis: ping (skip se REDIS_URL ausente) ──────────────────────
    if (os.getenv("REDIS_URL") or "").strip():
        try:
            from reliability.redis_inbound import _client as _redis_client_fn
            _r = _redis_client_fn()
            if _r is not None:
                _r.ping()
                checks["redis"] = {"status": "ok"}
            else:
                checks["redis"] = {"status": "error", "error": "client not available"}
        except Exception as exc:
            checks["redis"] = {"status": "error", "error": str(exc)[:200]}
    else:
        checks["redis"] = {"status": "disabled", "reason": "REDIS_URL not set"}

    # ── Gemini: API key configurada (não chama API — caro pra probe) ─
    if (os.getenv("GEMINI_API_KEY") or "").strip():
        checks["gemini"] = {"status": "ok", "note": "key configured (not pinged)"}
    else:
        checks["gemini"] = {"status": "disabled", "reason": "GEMINI_API_KEY not set"}

    # DB é o único check obrigatório — Redis e Gemini podem estar "disabled".
    overall_ok = db_ok and all(
        c.get("status") in ("ok", "disabled") for c in checks.values()
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return jsonify({
        "ok": overall_ok,
        "service": "cigana",
        "uptime_s": int(time.time() - _APP_STARTED_AT),
        "elapsed_ms": elapsed_ms,
        "checks": checks,
    }), (200 if overall_ok else 503)


def _scan_flows_motor_nodes():
    """Lista ordenada de nós Python reais (node_*.py) para alinhamento UI ↔ motor."""
    flows_root = os.path.join(_ROOT, "flows")
    out = []
    if not os.path.isdir(flows_root):
        return out
    try:
        for phase in sorted(os.listdir(flows_root)):
            pdir = os.path.join(flows_root, phase)
            if not phase.startswith("fase_") or not os.path.isdir(pdir):
                continue
            for fname in sorted(os.listdir(pdir)):
                if not (fname.startswith("node_") and fname.endswith(".py")):
                    continue
                m = re.match(r"node_(.+)\.py$", fname)
                if not m:
                    continue
                nid = m.group(1)
                out.append({
                    "phase": phase,
                    "node_id": nid,
                    "file": fname,
                    "label": nid.replace("_", " ").title(),
                })
    except OSError:
        return out

    def _sort_key(item):
        mo = re.match(r"^(\d+)_", item["node_id"])
        return (int(mo.group(1)) if mo else 9999, item["node_id"])

    out.sort(key=_sort_key)
    return out


@app.route("/api/flows/summary", methods=["GET"])
def api_flows_summary():
    """Resumo do funil Python (pastas flows/fase_*) + sinais de integração para a UI Fluxos."""
    flows_root = os.path.join(_ROOT, "flows")
    phases = []
    total_nodes = 0
    try:
        for name in sorted(os.listdir(flows_root)):
            if not name.startswith("fase_"):
                continue
            pdir = os.path.join(flows_root, name)
            if not os.path.isdir(pdir):
                continue
            nodes = glob.glob(os.path.join(pdir, "node_*.py"))
            n = len(nodes)
            total_nodes += n
            parts = name.split("_", 2)
            if len(parts) >= 3 and parts[0] == "fase":
                rest = (parts[2] or "").replace("_", " ").strip()
                label = f"Fase {parts[1]} · {rest.title()}" if rest else f"Fase {parts[1]}"
            else:
                label = name.replace("_", " ").title()
            phases.append({"id": name, "label": label, "nodes": n})
    except OSError:
        phases = []
        total_nodes = 0

    motor_nodes = _scan_flows_motor_nodes()

    db = SessionLocal()
    try:
        tid = get_request_tenant_id()
        n_leads = (
            db.query(func.count(models.Lead.id)).filter(models.Lead.tenant_id == tid).scalar() or 0
        )
    except Exception as e:
        logger.warning("[API] /api/flows/summary leads: %s", e)
        n_leads = 0
    finally:
        db.close()

    return jsonify({
        "ok": True,
        "engine": "AcassIA / Cigana",
        "total_nodes": int(total_nodes),
        "phases": phases,
        "motor_nodes": motor_nodes,
        "whatsapp_configured": bool((PHONE_NUMBER_ID or "").strip()),
        "leads_total": int(n_leads),
    }), 200


@app.route("/api/flows/catalog", methods=["GET"])
def api_flows_catalog():
    """Catálogo da aba Fluxos alimentado pelo backend (tenant-aware)."""
    motor_nodes = _scan_flows_motor_nodes()
    nodes_by_phase: dict[str, list[dict]] = {}
    for n in motor_nodes:
        nodes_by_phase.setdefault(str(n.get("phase") or "fase_0"), []).append(n)

    db = SessionLocal()
    try:
        tid = get_request_tenant_id()
        total_leads = int(
            db.query(func.count(models.Lead.id)).filter(models.Lead.tenant_id == tid).scalar() or 0
        )
        top_nodes = (
            db.query(models.Lead.node_atual, func.count(models.Lead.id))
            .filter(models.Lead.tenant_id == tid)
            .group_by(models.Lead.node_atual)
            .order_by(func.count(models.Lead.id).desc())
            .limit(5)
            .all()
        )
    except Exception as e:
        logger.warning("[API] /api/flows/catalog metrics: %s", e)
        total_leads = 0
        top_nodes = []
    finally:
        db.close()

    # Baseado em fases reais para evitar hardcode no front.
    flows = []
    for phase in sorted(nodes_by_phase.keys()):
        nodes = nodes_by_phase.get(phase) or []
        phase_suffix = phase.replace("fase_", "").replace("_", " ").strip() or phase
        fid = abs(hash(phase)) % 90000 + 10000
        flows.append({
            "name": f"Fluxo {phase_suffix.title()}",
            "trigger": f"Motor Python · {len(nodes)} nós",
            "integration": "whatsapp",
            "flow_id": f"#{fid}",
            "last_run": "ativo",
            "open_target": "builder",
            "builder_context": f"Motor · {phase_suffix.title()}",
            "kind": "production",
            "phase": phase,
            "nodes": len(nodes),
        })

    # Entradas especiais úteis para operação comercial.
    has_recovery = any(str(n.get("node_id", "")).startswith("9_") for n in motor_nodes)
    if has_recovery:
        flows.append({
            "name": "Recuperação",
            "trigger": "Node 9 · Recovery",
            "integration": "recovery",
            "flow_id": "#70483",
            "last_run": "monitorado",
            "open_target": "builder",
            "builder_context": "Motor de Recuperação",
            "kind": "production",
            "phase": "fase_3_oferta",
            "nodes": 1,
        })

    # Saúde operacional resumida para a UI (sem query pesada).
    top_nodes_payload = [
        {"node": str(n or ""), "leads": int(c or 0)} for (n, c) in top_nodes
    ]

    return jsonify({
        "ok": True,
        "folders": [{"id": "principal", "name": "Pasta Principal"}],
        "flows": flows,
        "total_leads": total_leads,
        "top_nodes": top_nodes_payload,
    }), 200


@app.route("/api/flows/validate", methods=["POST"])
@login_required
@require_admin
def api_flows_validate():
    """Validação de documento do construtor visual (acassia-flow v1)."""
    try:
        from flow_builder_runtime import validate_flow_document

        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "payload inválido"}), 400
        report = validate_flow_document(body)
        status = 200 if report.get("ok") else 422
        return jsonify(_json_safe_for_api(report)), status
    except Exception as e:
        logger.error("🚨 [API] /api/flows/validate: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/flows/schema", methods=["GET"])
def api_flows_schema():
    """Catálogo de blocos e campos (para o construtor)."""
    try:
        from flow_builder_runtime import public_node_catalog
        from flow_executor import (
            flow_blueprint_allow_http,
            flow_blueprint_allow_llm,
            flow_blueprint_gemini_configured,
        )
        from flow_motor_ref import flow_blueprint_allow_motor_ref

        payload = public_node_catalog()
        payload["runtime"] = {
            "allow_http": flow_blueprint_allow_http(),
            "allow_llm": flow_blueprint_allow_llm(),
            "gemini_configured": flow_blueprint_gemini_configured(),
            "allow_motor_ref": flow_blueprint_allow_motor_ref(),
        }
        return jsonify({"ok": True, **_json_safe_for_api(payload)}), 200
    except Exception as e:
        logger.error("🚨 [API] /api/flows/schema: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/flows/compile", methods=["POST"])
@login_required
@require_admin
def api_flows_compile():
    """Compila documento validado num plano linear (ordem de execução)."""
    try:
        from flow_builder_runtime import compile_flow_plan, validate_flow_document

        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "payload inválido"}), 400
        rep = validate_flow_document(body)
        plan = compile_flow_plan(rep.get("normalized") or body)
        out = {"ok": bool(rep.get("ok")), "validation": rep, "plan": plan}
        return jsonify(_json_safe_for_api(out)), 200 if rep.get("ok") else 422
    except Exception as e:
        logger.error("🚨 [API] /api/flows/compile: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/flows/simulate", methods=["POST"])
@login_required
@require_admin
def api_flows_simulate():
    """Simulação dry-run (trace legível) — não envia WhatsApp."""
    try:
        from flow_builder_runtime import simulate_flow, validate_flow_document

        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "payload inválido"}), 400
        rep = validate_flow_document(body)
        doc = rep.get("normalized") or body
        try:
            ms = int(body.get("max_steps") or 40)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "max_steps inválido"}), 400
        ms = max(1, min(ms, 500))
        sim = simulate_flow(doc, max_steps=ms)
        return jsonify(_json_safe_for_api({"ok": True, "validation": rep, "simulation": sim})), 200
    except Exception as e:
        logger.error("🚨 [API] /api/flows/simulate: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


def _serialize_flow_blueprint_row(row: models.FlowBlueprint) -> dict:
    return {
        "id": row.id,
        "slug": row.slug,
        "title": row.title,
        "updated_at": row.atualizado_em.isoformat() if row.atualizado_em else "",
        "created_at": row.criado_em.isoformat() if row.criado_em else "",
    }


@app.route("/api/flows/blueprints", methods=["GET", "POST"])
@login_required
@require_admin
def api_flows_blueprints():
    """Lista ou cria fluxos persistidos no servidor (tenant)."""
    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        if request.method == "GET":
            rows = (
                db.query(models.FlowBlueprint)
                .filter(models.FlowBlueprint.tenant_id == tid)
                .order_by(models.FlowBlueprint.atualizado_em.desc())
                .all()
            )
            return jsonify({"ok": True, "blueprints": [_serialize_flow_blueprint_row(r) for r in rows]}), 200
        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "").strip()
        slug = (body.get("slug") or "").strip().lower()
        if not title:
            return jsonify({"ok": False, "error": "title obrigatório"}), 400
        if not slug:
            slug = re.sub(r"[^a-z0-9_]+", "_", title.lower()).strip("_")[:120] or "fluxo"
        existing = db.query(models.FlowBlueprint).filter_by(tenant_id=tid, slug=slug).first()
        if existing:
            return jsonify({"ok": False, "error": "slug já existe neste tenant"}), 409

        # Quota check (Frente 2.7) — limite de fluxos por plano
        try:
            import quota
            current = db.query(models.FlowBlueprint).filter_by(tenant_id=tid).count()
            allowed, current_count, limit = quota.check_state_quota(tid, "flows", current, db_session=db)
            if not allowed:
                return jsonify({
                    "ok": False,
                    "error": "quota_exceeded",
                    "kind": "flows",
                    "current": current_count,
                    "limit": limit,
                    "message": f"Seu plano permite {limit} fluxo(s). Faça upgrade pra criar mais.",
                }), 402  # Payment Required
        except Exception:
            pass  # fail open

        doc = body.get("body") if isinstance(body.get("body"), dict) else {}
        row = models.FlowBlueprint(tenant_id=tid, slug=slug[:128], title=title[:300], body_json=doc)
        db.add(row)
        db.commit()
        db.refresh(row)
        return jsonify({"ok": True, "blueprint": _serialize_flow_blueprint_row(row)}), 201
    except Exception as e:
        logger.error("🚨 [API] /api/flows/blueprints: %s", e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/flows/blueprints/<int:bid>", methods=["GET", "PATCH", "DELETE"])
@login_required
@require_admin
def api_flows_blueprint_one(bid: int):
    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        row = db.query(models.FlowBlueprint).filter_by(id=bid, tenant_id=tid).first()
        if not row:
            return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
        if request.method == "GET":
            body = row.body_json if isinstance(row.body_json, dict) else {}
            return jsonify({"ok": True, "blueprint": {**_serialize_flow_blueprint_row(row), "body": body}}), 200
        if request.method == "DELETE":
            pub = db.query(models.FlowPublish).filter_by(tenant_id=tid).first()
            if pub and pub.published_blueprint_id == bid:
                pub.published_blueprint_id = None
            db.delete(row)
            db.commit()
            return jsonify({"ok": True}), 200
        payload = request.get_json(silent=True) or {}
        if "title" in payload:
            t = str(payload.get("title") or "").strip()
            if t:
                row.title = t[:300]
        if "slug" in payload:
            ns = str(payload.get("slug") or "").strip().lower()[:128]
            if ns:
                clash = (
                    db.query(models.FlowBlueprint)
                    .filter(
                        models.FlowBlueprint.tenant_id == tid,
                        models.FlowBlueprint.slug == ns,
                        models.FlowBlueprint.id != bid,
                    )
                    .first()
                )
                if clash:
                    return jsonify({"ok": False, "error": "slug já em uso"}), 409
                row.slug = ns
        if "body" in payload and isinstance(payload.get("body"), dict):
            row.body_json = payload["body"]
        db.commit()
        db.refresh(row)
        return jsonify({"ok": True, "blueprint": _serialize_flow_blueprint_row(row)}), 200
    except Exception as e:
        logger.error("🚨 [API] blueprint %s: %s", bid, e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/flows/blueprints/by-slug/<string:slug>", methods=["GET"])
@login_required
@require_admin
def api_flows_blueprint_by_slug(slug: str):
    """Carrega documento acassia-flow por slug estável (uma ida ao servidor)."""
    tid = get_request_tenant_id()
    ns = (slug or "").strip().lower()[:128]
    if not ns:
        return jsonify({"ok": False, "error": "slug inválido"}), 400
    db = SessionLocal()
    try:
        row = db.query(models.FlowBlueprint).filter_by(tenant_id=tid, slug=ns).first()
        if not row:
            return jsonify({"ok": False, "error": "não encontrado"}), 404
        body = row.body_json if isinstance(row.body_json, dict) else {}
        return jsonify({"ok": True, "blueprint": {**_serialize_flow_blueprint_row(row), "body": body}}), 200
    except Exception as e:
        logger.error("🚨 [API] blueprint by-slug %s: %s", slug, e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


def _ensure_flow_publish_row(db, tenant_id: str) -> models.FlowPublish:
    tid = (tenant_id or "default").strip() or "default"
    row = db.query(models.FlowPublish).filter_by(tenant_id=tid).first()
    if row is None:
        row = models.FlowPublish(tenant_id=tid, published_blueprint_id=None)
        db.add(row)
        db.flush()
    return row


@app.route("/api/flows/publish", methods=["POST"])
@login_required
@require_admin
def api_flows_publish_blueprint():
    """Define o blueprint publicado do construtor para este tenant (metadados + executor)."""
    tid = get_request_tenant_id()
    body = request.get_json(silent=True) or {}
    bid = body.get("blueprint_id")
    if bid is None:
        return jsonify({"ok": False, "error": "blueprint_id obrigatório"}), 400
    try:
        bid = int(bid)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "blueprint_id inválido"}), 400
    db = SessionLocal()
    try:
        bp = db.query(models.FlowBlueprint).filter_by(id=bid, tenant_id=tid).first()
        if not bp:
            return jsonify({"ok": False, "error": "blueprint não encontrado neste tenant"}), 404
        pub = _ensure_flow_publish_row(db, tid)
        pub.published_blueprint_id = bid
        db.commit()
        return jsonify({"ok": True, "published_blueprint_id": bid}), 200
    except Exception as e:
        logger.error("🚨 [API] /api/flows/publish: %s", e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/flows/publish/status", methods=["GET"])
@login_required
@require_admin
def api_flows_publish_blueprint_status():
    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        pub = db.query(models.FlowPublish).filter_by(tenant_id=tid).first()
        if not pub or not pub.published_blueprint_id:
            return jsonify({"ok": True, "published": None}), 200
        bp = db.query(models.FlowBlueprint).filter_by(id=pub.published_blueprint_id, tenant_id=tid).first()
        return jsonify(
            {
                "ok": True,
                "published": {
                    "blueprint_id": pub.published_blueprint_id,
                    "slug": bp.slug if bp else "",
                    "title": bp.title if bp else "",
                },
            }
        ), 200
    except Exception as e:
        logger.error("🚨 [API] /api/flows/publish/status: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/flows/blueprints/<int:bid>/execute", methods=["POST"])
@login_required
@require_admin
def api_flows_blueprint_execute(bid: int):
    """
    Executa o fluxo compilado no motor real: gera Acao(s) e envia pela mesma fila WhatsApp.
    Body JSON: { "lead_id": number }
    """
    tid = get_request_tenant_id()
    body = request.get_json(silent=True) or {}
    lid = body.get("lead_id")
    try:
        lid = int(lid)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "lead_id obrigatório (inteiro)"}), 400

    if str(getattr(motor, "tenant_id", "default") or "default") != tid:
        return jsonify(
            {
                "ok": False,
                "error": "motor_tenant_mismatch",
                "hint": "ACASSIA_TENANT_ID do processo deve coincidir com X-Acassia-Tenant.",
            }
        ), 503

    db = SessionLocal()
    try:
        bp = db.query(models.FlowBlueprint).filter_by(id=bid, tenant_id=tid).first()
        if not bp:
            return jsonify({"ok": False, "error": "blueprint não encontrado"}), 404
        lead = db.get(models.Lead, lid)
        if not lead or str(getattr(lead, "tenant_id", "default") or "default") != tid:
            return jsonify({"ok": False, "error": "lead não encontrado neste tenant"}), 404

        from flow_executor import document_to_acoes, flow_context_from_lead
        from schema import ContextoConversa
        from sqlalchemy.orm.attributes import flag_modified

        doc = bp.body_json if isinstance(bp.body_json, dict) else {}
        div_out = {}
        fv_out = {}
        try:
            acoes = document_to_acoes(
                doc,
                context=flow_context_from_lead(lead, tenant_id=tid),
                blueprint_id=bid,
                tenant_id=tid,
                divisao_metadata_out=div_out,
                flow_vars_metadata_out=fv_out,
            )
        except ValueError as ve:
            return jsonify({"ok": False, "error": str(ve)}), 422
        if not acoes:
            return jsonify({"ok": False, "error": "nenhuma ação gerada (revise blocos message/delay)"}), 422

        if div_out or fv_out:
            meta = dict(lead.metadata_json or {}) if isinstance(lead.metadata_json, dict) else {}
            meta.update(div_out)
            meta.update(fv_out)
            lead.metadata_json = meta
            flag_modified(lead, "metadata_json")

        ctx = ContextoConversa(
            lead_id=lead.id,
            telefone=lead.telefone,
            node_atual=lead.node_atual or "1_apresentacao",
            historico=motor._buscar_historico(db, lead.id, 20),
            texto_recebido="[FLOW_BLUEPRINT_EXECUTE]",
            tipo_mensagem="system",
            personalizer=motor.personalizer,
        )
        ctx.metadata["__config__"] = CONFIG_CLIENTE
        ctx.metadata["flow_blueprint_execute"] = {"blueprint_id": bid, "actions": len(acoes)}
        try:
            from studio_runtime import inject_published_studio_into_metadata

            inject_published_studio_into_metadata(ctx.metadata, tenant_id=tid)
        except Exception:
            pass
        try:
            from flow_executor import inject_published_flow_metadata

            inject_published_flow_metadata(ctx.metadata, tid)
        except Exception:
            pass

        db.add(
            models.EventoAudit(
                lead_id=lead.id,
                evento="flow_blueprint_execute",
                dados={"blueprint_id": bid, "actions": len(acoes)},
            )
        )
        db.commit()

        try:
            from api.flow_platform import record_execute_flow_run

            record_execute_flow_run(tid, bid, lead.id)
        except Exception:
            pass

        threading.Thread(
            target=motor._processar_fila,
            args=(lead.id, ctx, acoes),
            daemon=True,
            name=f"flow-bp-{bid}",
        ).start()
        return jsonify({"ok": True, "queued_actions": len(acoes), "lead_id": lead.id}), 200
    except Exception as e:
        logger.error("🚨 [API] blueprint execute %s: %s", bid, e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """KPIs para o dashboard + campos extras para evolução da UI."""
    db = SessionLocal()
    try:
        tid = get_request_tenant_id()
        msg_counts = (
            db.query(
                func.count(models.Mensagem.id),
                func.coalesce(func.sum(case((models.Mensagem.tipo == "audio", 1), else_=0)), 0),
                func.coalesce(func.sum(case((models.Mensagem.remetente == "bot", 1), else_=0)), 0),
                func.coalesce(func.sum(case((models.Mensagem.remetente == "user", 1), else_=0)), 0),
            )
            .join(models.Lead, models.Mensagem.lead_id == models.Lead.id)
            .filter(models.Lead.tenant_id == tid)
            .one()
        )
        n_msgs = int(msg_counts[0] or 0)
        n_audio = int(msg_counts[1] or 0)
        n_bot = int(msg_counts[2] or 0)
        n_user = int(msg_counts[3] or 0)
        n_leads = (
            db.query(func.count(models.Lead.id)).filter(models.Lead.tenant_id == tid).scalar() or 0
        )
        n_conv = (
            db.query(func.count(models.Lead.id))
            .filter(models.Lead.convertido.is_(True), models.Lead.tenant_id == tid)
            .scalar()
            or 0
        )

        agora = datetime.now(timezone.utc)
        inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        leads_hoje = (
            db.query(func.count(models.Lead.id))
            .filter(models.Lead.atualizado_em >= inicio_dia, models.Lead.tenant_id == tid)
            .scalar()
            or 0
        )

        # Estimativas: TTS por áudio (~400 tokens), LLM por resposta do bot (~150 tokens/msg bot)
        tts_usados = max(0, n_audio * 400)
        gpt_usados = max(0, n_bot * 150)
        api_requests = min(99999, max(1, n_msgs * 2 + n_leads))

        inicio_24h = agora - timedelta(hours=24)
        redund_rows = (
            db.query(models.EventoAudit)
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "engine_redundancia_filtrada",
                models.Lead.tenant_id == tid,
            )
            .order_by(models.EventoAudit.timestamp.desc())
            .limit(5000)
            .all()
        )
        redund_total = 0
        redund_24h = 0
        redund_motivos: dict[str, int] = {}
        for ev in redund_rows:
            d = ev.dados if isinstance(ev.dados, dict) else {}
            motivo = str(d.get("motivo") or "na")
            qtd = int(d.get("qtd") or 1)
            redund_total += qtd
            ts = ev.timestamp
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts and ts >= inicio_24h:
                redund_24h += qtd
            redund_motivos[motivo] = int(redund_motivos.get(motivo, 0) or 0) + qtd

        busy_24h = (
            db.query(func.count(models.EventoAudit.id))
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "engine_busy_detectado",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .scalar()
            or 0
        )
        busy_requeued_24h = (
            db.query(func.count(models.EventoAudit.id))
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "engine_busy_requeued",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .scalar()
            or 0
        )
        busy_discarded_24h = (
            db.query(func.count(models.EventoAudit.id))
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "engine_busy_discarded",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .scalar()
            or 0
        )
        inbox_batch_pronto_24h = (
            db.query(func.count(models.EventoAudit.id))
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "inbox_batch_pronto",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .scalar()
            or 0
        )
        fallback_rows_24h = (
            db.query(models.EventoAudit)
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "node_fallback_acionado",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .all()
        )
        fallback_24h_total = 0
        fallback_por_node: dict[str, int] = {}
        for ev in fallback_rows_24h:
            d = ev.dados if isinstance(ev.dados, dict) else {}
            node = str(d.get("node") or "na")
            fallback_24h_total += 1
            fallback_por_node[node] = int(fallback_por_node.get(node, 0) or 0) + 1

        return jsonify({
            "tts_usados": tts_usados,
            "gpt_usados": gpt_usados,
            "api_requests": api_requests,
            "leads_total": n_leads,
            "mensagens_total": n_msgs,
            "mensagens_user": n_user,
            "mensagens_bot": n_bot,
            "audios_total": n_audio,
            "convertidos": n_conv,
            "leads_atualizados_hoje": leads_hoje,
            "redundancias_filtradas_total": redund_total,
            "redundancias_filtradas_24h": redund_24h,
            "redundancias_filtradas_por_motivo": redund_motivos,
            "engine_busy_24h": int(busy_24h),
            "engine_busy_requeued_24h": int(busy_requeued_24h),
            "engine_busy_discarded_24h": int(busy_discarded_24h),
            "inbox_batch_pronto_24h": int(inbox_batch_pronto_24h),
            "fallback_nodes_24h_total": int(fallback_24h_total),
            "fallback_nodes_24h_por_node": fallback_por_node,
        }), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/stats: %s", e)
        return jsonify({
            "tts_usados": 0,
            "gpt_usados": 0,
            "api_requests": 0,
            "leads_total": 0,
            "mensagens_total": 0,
            "engine_busy_24h": 0,
            "engine_busy_requeued_24h": 0,
            "engine_busy_discarded_24h": 0,
            "inbox_batch_pronto_24h": 0,
            "fallback_nodes_24h_total": 0,
            "fallback_nodes_24h_por_node": {},
            "error": str(e),
        }), 200
    finally:
        db.close()


@app.route("/api/dashboard/kpis", methods=["GET"])
def api_dashboard_kpis():
    """KPIs executivos para leitura rápida no dashboard."""
    db = SessionLocal()
    try:
        tid = get_request_tenant_id()
        now = datetime.now(timezone.utc)
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        days = request.args.get("days", default=7, type=int) or 7
        days = max(1, min(days, 30))
        since = now - timedelta(days=days - 1)

        # Eventos Cakto no período (vendas, reembolsos, funil)
        cakto_rows = (
            db.query(models.EventoAudit)
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "cakto_webhook",
                models.EventoAudit.timestamp >= since,
                models.Lead.tenant_id == tid,
            )
            .all()
        )
        revenue_today = 0.0
        sales_count_today = 0
        cakto_events_today = 0
        by_day_rev = {}
        by_day_tx = {}
        by_day_refund = {}
        for ev in cakto_rows:
            d = ev.dados if isinstance(ev.dados, dict) else {}
            status = str(d.get("status") or "").lower()
            amount = _to_float(d.get("amount") or 0.0, 0.0)
            ts = ev.timestamp
            if not ts:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            key = ts.date().isoformat()
            if ts >= start_today:
                cakto_events_today += 1
            if status in ("paid", "approved", "completed"):
                by_day_rev[key] = float(by_day_rev.get(key, 0.0) or 0.0) + amount
                by_day_tx[key] = int(by_day_tx.get(key, 0) or 0) + 1
                if ts >= start_today:
                    revenue_today += amount
                    sales_count_today += 1
            elif "refund" in status or status == "refunded":
                by_day_refund[key] = float(by_day_refund.get(key, 0.0) or 0.0) + amount

        # Gasto anúncio: snapshot Meta (estimativa diária pela janela)
        snap = _load_report_json("meta_ads_snapshot.json")
        spend_total = _to_float((snap or {}).get("spend_total"), 0.0)
        window_days = int((snap or {}).get("window_days") or days or 7)
        window_days = max(1, window_days)
        spend_today = spend_total / window_days

        # Tokens aproximados do dia por mensagens
        msg_today = (
            db.query(
                func.coalesce(func.sum(case((models.Mensagem.remetente == "bot", 1), else_=0)), 0),
                func.coalesce(func.sum(case((models.Mensagem.tipo == "audio", 1), else_=0)), 0),
            )
            .join(models.Lead, models.Mensagem.lead_id == models.Lead.id)
            .filter(models.Mensagem.timestamp >= start_today, models.Lead.tenant_id == tid)
            .one()
        )
        bot_today = int(msg_today[0] or 0)
        audio_today = int(msg_today[1] or 0)
        tokens_today = max(0, bot_today * 150 + audio_today * 400)

        wa_starts_today = int(
            db.query(func.count(models.Lead.id))
            .filter(models.Lead.tenant_id == tid, models.Lead.criado_em >= start_today)
            .scalar()
            or 0
        )
        avg_ticket = (revenue_today / sales_count_today) if sales_count_today else 0.0
        conv_pct = (sales_count_today / wa_starts_today * 100.0) if wa_starts_today else 0.0

        # Série (últimos N dias): faturamento, nº vendas pagas, reembolsos
        series = []
        for i in range(days):
            d = (now - timedelta(days=(days - 1 - i))).date().isoformat()
            rev = _to_float(by_day_rev.get(d), 0.0)
            tx = int(by_day_tx.get(d, 0) or 0)
            ref = _to_float(by_day_refund.get(d), 0.0)
            series.append(
                {
                    "date": d,
                    "revenue_brl": round(rev, 2),
                    "ad_spend_brl": round(spend_total / window_days, 2),
                    "profit_brl": round(rev - (spend_total / window_days), 2),
                    "transactions_count": tx,
                    "refunded_brl": round(ref, 2),
                }
            )
        return jsonify(
            {
                "ok": True,
                "today": {
                    "revenue_brl": round(revenue_today, 2),
                    "ad_spend_brl": round(spend_today, 2),
                    "tokens_total": int(tokens_today),
                    "profit_brl": round(revenue_today - spend_today, 2),
                    "sales_count": int(sales_count_today),
                    "avg_ticket_brl": round(avg_ticket, 2),
                    "wa_conversations_started": int(wa_starts_today),
                    "payments_initiated": int(cakto_events_today),
                    "conversion_rate_pct": round(min(conv_pct, 100.0), 2),
                },
                "series": series,
            }
        ), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/dashboard/kpis: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/agent/profile", methods=["GET", "POST"])
def api_agent_profile():
    """Configuração completa de personalidade e output da IA."""
    if request.method == "GET":
        data = _load_report_json("agent_profile_config.json")
        if not data:
            data = {
                "business_name": "Meu Negócio",
                "segment": "",
                "tone": "humano_direto",
                "target_audience": "",
                "primary_goal": "vender_no_whatsapp",
                "offer_summary": "",
                "forbidden_terms": [],
                "required_elements": ["clareza", "cta", "objetividade"],
                "output_style": {
                    "max_chars_balloon_default": 210,
                    "max_balloons_per_turn": 3,
                    "must_end_with_question_when_collecting": True,
                },
            }
        return jsonify({"ok": True, "profile": data}), 200
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "payload inválido"}), 400
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_report_json("agent_profile_config.json", payload)
    return jsonify({"ok": True, "profile": payload}), 200


def _studio_default_data():
    return {
        "personalidade": {
            "identidade": "",
            "diretrizes": "",
            "voz": "neutra",
            "estabilidade": 0.5,
            "similaridade": 0.7,
            "sotaque": 0.5,
            "velocidade": 1.0,
        },
        "instrucoes": {"gerais": "", "proibicoes": "", "formato_saida": ""},
        "base": {"contexto_empresa": "", "produtos": "", "politica_preco": ""},
        "faq": {"perguntas": ""},
        "arquivos": {"links": ""},
    }


def _serialize_studio_agent(db, agent: models.StudioAgent, tenant_id: str):
    tid = (tenant_id or "default").strip() or "default"
    pub = db.query(models.StudioPublish).filter_by(tenant_id=tid).first()
    pub_vid = pub.published_version_id if pub else None
    vers_rows = (
        db.query(models.StudioAgentVersion)
        .filter_by(agent_id=agent.id)
        .order_by(models.StudioAgentVersion.version_number.desc())
        .all()
    )
    versions = [
        {
            "id": v.id,
            "version_number": v.version_number,
            "note": v.note or "",
            "created_at": v.criado_em.isoformat() if v.criado_em else "",
            "is_published": v.id == pub_vid,
        }
        for v in vers_rows
    ]
    return {
        "id": agent.id,
        "name": agent.name,
        "avatar": agent.avatar or "#7c3aed",
        "draft": agent.draft_json if isinstance(agent.draft_json, dict) else _studio_default_data(),
        "updated_at": agent.atualizado_em.isoformat() if agent.atualizado_em else "",
        "created_at": agent.criado_em.isoformat() if agent.criado_em else "",
        "versions": versions,
        "published_version_id": pub_vid if any(v.id == pub_vid for v in vers_rows) else None,
    }


@app.route("/api/studio/agents", methods=["GET", "POST"])
@login_required
@require_admin
def api_studio_agents():
    """Lista ou cria agentes do Studio (persistência servidor)."""
    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        if request.method == "GET":
            rows = (
                db.query(models.StudioAgent)
                .filter(models.StudioAgent.tenant_id == tid)
                .order_by(models.StudioAgent.atualizado_em.desc())
                .all()
            )
            return jsonify({"ok": True, "agents": [_serialize_studio_agent(db, a, tid) for a in rows]}), 200
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "").strip()
        if not name:
            return jsonify({"ok": False, "error": "name obrigatório"}), 400

        # Quota check (Frente 2.8) — limite de agentes por plano
        try:
            import quota
            current = db.query(models.StudioAgent).filter_by(tenant_id=tid).count()
            allowed, current_count, limit = quota.check_state_quota(tid, "agents", current, db_session=db)
            if not allowed:
                return jsonify({
                    "ok": False, "error": "quota_exceeded", "kind": "agents",
                    "current": current_count, "limit": limit,
                    "message": f"Seu plano permite {limit} agente(s). Faça upgrade pra criar mais.",
                }), 402
        except Exception:
            pass

        avatar = (body.get("avatar") or "#7c3aed").strip()
        agent = models.StudioAgent(
            tenant_id=tid,
            name=name[:200],
            avatar=avatar[:32],
            draft_json=_studio_default_data(),
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return jsonify({"ok": True, "agent": _serialize_studio_agent(db, agent, tid)}), 201
    except Exception as e:
        logger.error("🚨 [STUDIO] /api/studio/agents: %s", e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/studio/agents/<int:aid>", methods=["GET", "PATCH", "DELETE"])
@login_required
@require_admin
def api_studio_agent_one(aid: int):
    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        agent = db.query(models.StudioAgent).filter_by(id=aid, tenant_id=tid).first()
        if not agent:
            return jsonify({"ok": False, "error": "agente não encontrado"}), 404
        if request.method == "GET":
            return jsonify({"ok": True, "agent": _serialize_studio_agent(db, agent, tid)}), 200
        if request.method == "DELETE":
            db.delete(agent)
            db.commit()
            return jsonify({"ok": True}), 200
        body = request.get_json(silent=True) or {}
        if "name" in body:
            n = str(body.get("name") or "").strip()
            if n:
                agent.name = n[:200]
        if "avatar" in body:
            agent.avatar = str(body.get("avatar") or "#7c3aed")[:32]
        if "draft" in body and isinstance(body.get("draft"), dict):
            agent.draft_json = body["draft"]
        db.commit()
        db.refresh(agent)
        return jsonify({"ok": True, "agent": _serialize_studio_agent(db, agent, tid)}), 200
    except Exception as e:
        logger.error("🚨 [STUDIO] agent %s: %s", aid, e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/studio/agents/<int:aid>/versions", methods=["POST"])
@login_required
@require_admin
def api_studio_agent_version_create(aid: int):
    """Cria snapshot de versão a partir do rascunho atual."""
    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        agent = db.query(models.StudioAgent).filter_by(id=aid, tenant_id=tid).first()
        if not agent:
            return jsonify({"ok": False, "error": "agente não encontrado"}), 404
        body = request.get_json(silent=True) or {}
        note = (body.get("note") or "").strip() or None
        last = (
            db.query(models.StudioAgentVersion)
            .filter_by(agent_id=agent.id)
            .order_by(models.StudioAgentVersion.version_number.desc())
            .first()
        )
        vn = (last.version_number + 1) if last else 1
        snap = agent.draft_json if isinstance(agent.draft_json, dict) else _studio_default_data()
        ver = models.StudioAgentVersion(agent_id=agent.id, version_number=vn, body_json=snap, note=note)
        db.add(ver)
        db.commit()
        db.refresh(ver)
        return jsonify(
            {
                "ok": True,
                "version": {
                    "id": ver.id,
                    "version_number": ver.version_number,
                    "note": ver.note or "",
                    "created_at": ver.criado_em.isoformat() if ver.criado_em else "",
                },
                "agent": _serialize_studio_agent(db, agent, tid),
            }
        ), 201
    except Exception as e:
        logger.error("🚨 [STUDIO] version create %s: %s", aid, e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/studio/agents/<int:aid>/publish", methods=["POST"])
@login_required
@require_admin
def api_studio_agent_publish(aid: int):
    """Define qual versão está no ar (motor WhatsApp / IA)."""
    from studio_runtime import ensure_publish_row

    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        body = request.get_json(silent=True) or {}
        version_id = body.get("version_id")
        if version_id is None:
            return jsonify({"ok": False, "error": "version_id obrigatório"}), 400
        try:
            version_id = int(version_id)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "version_id inválido"}), 400
        ver = (
            db.query(models.StudioAgentVersion)
            .filter_by(id=version_id, agent_id=aid)
            .first()
        )
        if not ver:
            return jsonify({"ok": False, "error": "versão não encontrada para este agente"}), 404
        ag = db.query(models.StudioAgent).filter_by(id=aid, tenant_id=tid).first()
        if not ag:
            return jsonify({"ok": False, "error": "agente não encontrado"}), 404
        pub = ensure_publish_row(db, tid)
        pub.published_version_id = ver.id
        db.commit()
        return jsonify(
            {
                "ok": True,
                "published_version_id": ver.id,
                "published_version_number": ver.version_number,
                "agent_id": aid,
            }
        ), 200
    except Exception as e:
        logger.error("🚨 [STUDIO] publish %s: %s", aid, e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/studio/publish/status", methods=["GET"])
@login_required
@require_admin
def api_studio_publish_status():
    tid = get_request_tenant_id()
    db = SessionLocal()
    try:
        pub = db.query(models.StudioPublish).filter_by(tenant_id=tid).first()
        if not pub or not pub.published_version_id:
            return jsonify({"ok": True, "published": None}), 200
        ver = (
            db.query(models.StudioAgentVersion)
            .filter_by(id=pub.published_version_id)
            .first()
        )
        if not ver:
            return jsonify({"ok": True, "published": None}), 200
        agent = db.query(models.StudioAgent).filter_by(id=ver.agent_id, tenant_id=tid).first()
        return jsonify(
            {
                "ok": True,
                "published": {
                    "version_id": ver.id,
                    "version_number": ver.version_number,
                    "agent_id": ver.agent_id,
                    "agent_name": agent.name if agent else "",
                    "note": ver.note or "",
                    "created_at": ver.criado_em.isoformat() if ver.criado_em else "",
                },
            }
        ), 200
    except Exception as e:
        logger.error("🚨 [STUDIO] publish status: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/executive/overview", methods=["GET"])
def api_executive_overview():
    """
    Visão executiva geral com departamentos:
    - funil
    - atendimento
    - custo_ia
    - vendas
    - integracoes
    """
    db = SessionLocal()
    try:
        tid = get_request_tenant_id()
        now = datetime.now(timezone.utc)
        inicio_24h = now - timedelta(hours=24)
        leads_total = int(
            db.query(func.count(models.Lead.id)).filter(models.Lead.tenant_id == tid).scalar() or 0
        )
        conv_total = int(
            db.query(func.count(models.Lead.id))
            .filter(models.Lead.convertido.is_(True), models.Lead.tenant_id == tid)
            .scalar()
            or 0
        )
        opt_out_total = int(
            db.query(func.count(models.Lead.id))
            .filter(models.Lead.opt_out.is_(True), models.Lead.tenant_id == tid)
            .scalar()
            or 0
        )
        msgs_24h = int(
            db.query(func.count(models.Mensagem.id))
            .join(models.Lead, models.Mensagem.lead_id == models.Lead.id)
            .filter(models.Mensagem.timestamp >= inicio_24h, models.Lead.tenant_id == tid)
            .scalar()
            or 0
        )
        batch_24h = int(
            db.query(func.count(models.EventoAudit.id))
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "inbox_batch_pronto",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .scalar()
            or 0
        )
        fallback_24h = int(
            db.query(func.count(models.EventoAudit.id))
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "node_fallback_acionado",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .scalar()
            or 0
        )
        timing_rows = (
            db.query(models.EventoAudit)
            .join(models.Lead, models.EventoAudit.lead_id == models.Lead.id)
            .filter(
                models.EventoAudit.evento == "node_exec_timing",
                models.EventoAudit.timestamp >= inicio_24h,
                models.Lead.tenant_id == tid,
            )
            .order_by(models.EventoAudit.timestamp.desc())
            .limit(4000)
            .all()
        )
        n_timing = 0
        soma_timing = 0.0
        lentos = 0
        for ev in timing_rows:
            d = ev.dados if isinstance(ev.dados, dict) else {}
            elapsed = float(d.get("elapsed_s") or 0.0)
            if elapsed <= 0:
                continue
            n_timing += 1
            soma_timing += elapsed
            if elapsed > 3.5:
                lentos += 1
        tempo_medio = (soma_timing / n_timing) if n_timing else 0.0

        custo_json = _load_report_json("custo_ia_por_lead_report.json")
        custo_medio = float(custo_json.get("avg_cost_per_lead_brl") or 0.0)
        usage_pct = float(custo_json.get("avg_budget_usage_pct") or 0.0)
        meta_json = _load_report_json("meta_ads_snapshot.json")
        camp = int(meta_json.get("campaigns_total") or 0)
        adset = int(meta_json.get("adsets_total") or 0)
        ads = int(meta_json.get("ads_total") or 0)

        return jsonify(
            {
                "generated_at": now.isoformat(),
                "departments": {
                    "funil": {
                        "leads_total": leads_total,
                        "convertidos_total": conv_total,
                        "opt_out_total": opt_out_total,
                        "prioridade": "alta" if conv_total == 0 and leads_total > 10 else "normal",
                    },
                    "atendimento": {
                        "mensagens_24h": msgs_24h,
                        "batch_24h": batch_24h,
                        "fallback_24h": fallback_24h,
                        "tempo_node_medio_s_24h": round(tempo_medio, 3),
                        "nodes_lentos_24h": lentos,
                        "urgencia": "alta" if lentos > 20 else "normal",
                    },
                    "custo_ia": {
                        "avg_cost_per_lead_brl": round(custo_medio, 6),
                        "avg_budget_usage_pct": round(usage_pct, 2),
                        "status": "atencao" if usage_pct >= 80 else "ok",
                    },
                    "vendas": {
                        "ticket_base": int(CONFIG_CLIENTE.get("preco_materiais", "65") or 65),
                        "ticket_completo": int(CONFIG_CLIENTE.get("preco_servico", "65") or 65)
                        + int(CONFIG_CLIENTE.get("preco_materiais", "65") or 65),
                        "recomendacao": (
                            "Acompanhar objecao de preco no node8 e foco em FIRMO."
                        ),
                    },
                    "integracoes": {
                        "cakto_enabled": bool((CONFIG_CLIENTE.get("cakto") or {}).get("enabled")),
                        "meta_ads_snapshot": bool(meta_json),
                        "campaigns_total": camp,
                        "adsets_total": adset,
                        "ads_total": ads,
                    },
                },
            }
        ), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/executive/overview: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/executive/department/<dep_name>", methods=["GET"])
def api_executive_department(dep_name: str):
    """
    Drill-down rápido por departamento com base no overview.
    """
    try:
        with app.test_request_context("/api/executive/overview"):
            resp, status = api_executive_overview()
        if status != 200:
            return jsonify({"ok": False, "error": "overview indisponível"}), 500
        data = resp.get_json(silent=True) or {}
        deps = (data.get("departments") or {}) if isinstance(data, dict) else {}
        key = str(dep_name or "").strip().lower()
        dep = deps.get(key)
        if dep is None:
            return jsonify({"ok": False, "error": "departamento não encontrado"}), 404
        return jsonify({"ok": True, "department": key, "data": dep}), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/executive/department/%s: %s", dep_name, e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/config/ia-economia", methods=["GET", "POST"])
def api_config_ia_economia():
    ie = CONFIG_CLIENTE.get("ia_economia") or {}
    if request.method == "GET":
        return jsonify(_json_safe_for_api(ie)), 200
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "payload inválido"}), 400
        novo = dict(ie)
        for k in (
            "orcamento_tokens_por_lead",
            "max_tentativas_ia_por_node",
            "max_output_tokens_default",
        ):
            if k in payload:
                novo[k] = max(1, int(payload.get(k)))
        if "modo_economico_ratio" in payload:
            novo["modo_economico_ratio"] = max(0.4, min(float(payload.get("modo_economico_ratio")), 0.98))
        if "max_output_tokens_por_node" in payload and isinstance(payload["max_output_tokens_por_node"], dict):
            m = dict(novo.get("max_output_tokens_por_node") or {})
            for nk, nv in payload["max_output_tokens_por_node"].items():
                try:
                    m[str(nk)] = max(120, int(nv))
                except Exception:
                    continue
            novo["max_output_tokens_por_node"] = m
        CONFIG_CLIENTE["ia_economia"] = novo
        return jsonify({"ok": True, "ia_economia": _json_safe_for_api(novo)}), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/config/ia-economia: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/cost/ia", methods=["GET"])
def api_cost_ia():
    data = _load_report_json("custo_ia_por_lead_report.json")
    if not data:
        return jsonify({"ok": False, "message": "Relatório ainda não gerado"}), 200
    return jsonify({"ok": True, "data": _json_safe_for_api(data)}), 200


@app.route("/api/meta/status", methods=["GET", "POST"])
def api_meta_status():
    """
    Snapshot para Meta Ads/Pixel.
    POST recebe snapshot exportado (campaign/adset/ad) e salva em reports.
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "payload inválido"}), 400
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_report_json("meta_ads_snapshot.json", payload)
        return jsonify({"ok": True}), 200

    snap = _load_report_json("meta_ads_snapshot.json")
    pixel_id = os.getenv("META_PIXEL_ID", "").strip()
    dataset_id = os.getenv("META_DATASET_ID", "").strip()
    recommendations = []
    spend = float(snap.get("spend_total") or 0.0) if snap else 0.0
    revenue = float(snap.get("revenue_total") or 0.0) if snap else 0.0
    roas = (revenue / spend) if spend > 0 else 0.0
    if snap:
        if roas < 1.5:
            recommendations.append("Reduzir verba nos anúncios com ROAS < 1.5 e mover para os top 20%.")
        elif roas >= 2.5:
            recommendations.append("Escalar gradualmente campanhas vencedoras (10-20% ao dia).")
    if not pixel_id:
        recommendations.append("Configurar META_PIXEL_ID para rastreio de eventos de checkout/conversão.")
    if not dataset_id:
        recommendations.append("Configurar META_DATASET_ID para CAPI e melhoria de otimização de campanhas.")
    if isinstance(snap, dict) and isinstance(snap.get("recommendations"), list):
        for rec in snap.get("recommendations")[:6]:
            txt = str(rec.get("text") or "").strip() if isinstance(rec, dict) else ""
            if txt:
                recommendations.append(txt)
    urgent_actions = []
    if isinstance(snap, dict):
        for rec in (snap.get("recommendations") or []):
            if not isinstance(rec, dict):
                continue
            if str(rec.get("urgency") or "").lower() not in ("alta", "atencao"):
                continue
            urgent_actions.append(
                {
                    "scope": rec.get("scope"),
                    "entity_id": rec.get("entity_id"),
                    "entity_name": rec.get("entity_name"),
                    "urgency": rec.get("urgency"),
                    "action": rec.get("action"),
                    "text": rec.get("text"),
                    "impact_brl_est": float(rec.get("impact_brl_est") or 0.0),
                }
            )
    urgent_actions = sorted(urgent_actions, key=lambda x: float(x.get("impact_brl_est") or 0.0), reverse=True)[:3]

    history = _load_meta_actions_history()
    recent = []
    for row in reversed(history[-30:]):
        if not isinstance(row, dict):
            continue
        out = dict(row)
        executed = row.get("executed_snapshot") if isinstance(row.get("executed_snapshot"), dict) else {}
        current = _find_entity_in_snapshot(
            snap if isinstance(snap, dict) else {},
            str(row.get("scope") or ""),
            str(row.get("entity_id") or ""),
        ) or {}
        if executed and current:
            spent_before = float(executed.get("spend") or 0.0)
            spent_now = float(current.get("spend") or 0.0)
            sales_before = float(executed.get("purchases") or 0.0)
            sales_now = float(current.get("purchases") or 0.0)
            out["delta_spend"] = round(spent_now - spent_before, 2)
            out["delta_sales"] = round(sales_now - sales_before, 2)
            out["impact_real_brl_est"] = round((sales_now - sales_before) - max(0.0, spent_now - spent_before), 2)
        recent.append(out)
    recent = list(reversed(recent[-12:]))

    return jsonify(
        {
            "ok": True,
            "pixel_configured": bool(pixel_id),
            "dataset_configured": bool(dataset_id),
            "snapshot": _json_safe_for_api(snap),
            "recommendations": recommendations,
            "urgent_actions_top3": urgent_actions,
            "action_history_recent": _json_safe_for_api(recent),
        }
    ), 200


@app.route("/api/meta/actions/execute", methods=["POST"])
def api_meta_action_execute():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "payload inválido"}), 400
    scope = str(payload.get("scope") or "").strip()
    entity_id = str(payload.get("entity_id") or "").strip()
    entity_name = str(payload.get("entity_name") or "").strip()
    action = str(payload.get("action") or "revisar").strip()
    urgency = str(payload.get("urgency") or "normal").strip()
    impact_est = float(payload.get("impact_brl_est") or 0.0)
    if not entity_id or not entity_name:
        return jsonify({"ok": False, "error": "entity_id/entity_name obrigatórios"}), 400

    snap = _load_report_json("meta_ads_snapshot.json")
    baseline = _find_entity_in_snapshot(snap if isinstance(snap, dict) else {}, scope, entity_id) or {}
    row = {
        "id": f"{int(time.time()*1000)}_{entity_id}",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "action": action,
        "urgency": urgency,
        "impact_brl_est": round(float(impact_est), 2),
        "executed_snapshot": {
            "spend": round(float(baseline.get("spend") or 0.0), 2),
            "purchases": round(float(baseline.get("purchases") or 0.0), 2),
            "roas": round(float(baseline.get("roas") or 0.0), 3),
        },
    }
    rows = _load_meta_actions_history()
    rows.append(row)
    _save_meta_actions_history(rows)
    return jsonify({"ok": True, "action_log": row}), 200


@app.route("/api/meta/actions/history", methods=["GET"])
def api_meta_action_history():
    rows = _load_meta_actions_history()
    return jsonify({"ok": True, "rows": _json_safe_for_api(list(reversed(rows[-120:])))}), 200


@app.route("/api/meta/sync", methods=["POST"])
def api_meta_sync():
    """
    Sincroniza dados direto da Meta Ads API e salva snapshot.
    Requer:
      - META_ACCESS_TOKEN
      - META_AD_ACCOUNT_ID (apenas números, sem 'act_')
    """
    ad_account_id = os.getenv("META_AD_ACCOUNT_ID", "").strip().replace("act_", "")
    if not ad_account_id:
        return jsonify({"ok": False, "error": "META_AD_ACCOUNT_ID não configurado"}), 400
    try:
        days = int((request.args.get("days", "7") or "7").strip())
        days = max(1, min(days, 30))
    except Exception:
        days = 7
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        until = datetime.now(timezone.utc).date().isoformat()
        params = {
            "fields": "id,name,status,insights.time_range({'since':'%s','until':'%s'}){spend,impressions,clicks,actions,action_values,purchase_roas}" % (since, until),
            "limit": 100,
        }
        out = _meta_graph_get(f"act_{ad_account_id}/campaigns", params)
        items = out.get("data") if isinstance(out, dict) else []
        campaigns = []
        spend_total = 0.0
        purchases_total = 0.0
        for c in (items or []):
            if not isinstance(c, dict):
                continue
            insights = (c.get("insights") or {}).get("data") or []
            ins = insights[0] if insights else {}
            spend = float(ins.get("spend") or 0.0)
            impressions = int(float(ins.get("impressions") or 0))
            clicks = int(float(ins.get("clicks") or 0))
            purchases = _parse_purchase_from_actions(ins.get("actions"))
            roas = (purchases / spend) if spend > 0 else 0.0
            spend_total += spend
            purchases_total += purchases
            campaigns.append(
                {
                    "id": str(c.get("id") or ""),
                    "name": str(c.get("name") or ""),
                    "status": str(c.get("status") or ""),
                    "spend": round(spend, 2),
                    "impressions": impressions,
                    "clicks": clicks,
                    "purchases": round(purchases, 2),
                    "roas": round(roas, 3),
                }
            )
        campaigns_sorted_spend = sorted(campaigns, key=lambda x: float(x.get("spend") or 0.0), reverse=True)
        campaigns_sorted_sales = sorted(campaigns, key=lambda x: float(x.get("purchases") or 0.0), reverse=True)

        adsets_json = _meta_graph_get(
            f"act_{ad_account_id}/insights",
            {
                "level": "adset",
                "time_range": json.dumps({"since": since, "until": until}),
                "fields": "adset_id,adset_name,campaign_id,campaign_name,spend,impressions,clicks,actions",
                "limit": 100,
            },
        )
        ads_json = _meta_graph_get(
            f"act_{ad_account_id}/insights",
            {
                "level": "ad",
                "time_range": json.dumps({"since": since, "until": until}),
                "fields": "ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,spend,impressions,clicks,actions",
                "limit": 100,
            },
        )
        adsets = []
        for row in (adsets_json.get("data") or []):
            spend_i = float(row.get("spend") or 0.0)
            purchases_i = _parse_purchase_from_actions(row.get("actions"))
            roas_i = (purchases_i / spend_i) if spend_i > 0 else 0.0
            obj = {
                "id": str(row.get("adset_id") or ""),
                "name": str(row.get("adset_name") or ""),
                "campaign_name": str(row.get("campaign_name") or ""),
                "spend": round(spend_i, 2),
                "purchases": round(purchases_i, 2),
                "roas": round(roas_i, 3),
                "impressions": int(float(row.get("impressions") or 0)),
                "clicks": int(float(row.get("clicks") or 0)),
                "status": "active",
            }
            obj["recommendation"] = _entity_meta_recommendation(obj)
            adsets.append(obj)

        ads = []
        for row in (ads_json.get("data") or []):
            spend_i = float(row.get("spend") or 0.0)
            purchases_i = _parse_purchase_from_actions(row.get("actions"))
            roas_i = (purchases_i / spend_i) if spend_i > 0 else 0.0
            obj = {
                "id": str(row.get("ad_id") or ""),
                "name": str(row.get("ad_name") or ""),
                "campaign_name": str(row.get("campaign_name") or ""),
                "adset_name": str(row.get("adset_name") or ""),
                "spend": round(spend_i, 2),
                "purchases": round(purchases_i, 2),
                "roas": round(roas_i, 3),
                "impressions": int(float(row.get("impressions") or 0)),
                "clicks": int(float(row.get("clicks") or 0)),
                "status": "active",
            }
            obj["recommendation"] = _entity_meta_recommendation(obj)
            ads.append(obj)

        top_adsets_spend = sorted(adsets, key=lambda x: float(x.get("spend") or 0.0), reverse=True)[:15]
        top_ads_spend = sorted(ads, key=lambda x: float(x.get("spend") or 0.0), reverse=True)[:20]
        top_ads_sales = sorted(ads, key=lambda x: float(x.get("purchases") or 0.0), reverse=True)[:20]

        auto_recommendations = []
        for rank_name, collection in (
            ("campanhas", campaigns_sorted_spend[:8]),
            ("conjuntos", top_adsets_spend[:8]),
            ("anuncios", top_ads_spend[:8]),
        ):
            for item in collection:
                rec = _entity_meta_recommendation(item)
                if rec["urgency"] in ("alta", "atencao"):
                    auto_recommendations.append(
                        {
                            "scope": rank_name,
                            "entity_id": item.get("id"),
                            "entity_name": item.get("name"),
                            "urgency": rec["urgency"],
                            "action": rec["action"],
                            "text": f"{item.get('name')}: {rec['reason']}",
                            "impact_brl_est": _estimate_impact_brl(item, rec["action"]),
                        }
                    )
        auto_recommendations = auto_recommendations[:24]
        snapshot = {
            "source": "meta_api",
            "window_days": days,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "campaigns_total": len(campaigns),
            "adsets_total": len(adsets),
            "ads_total": len(ads),
            "spend_total": round(spend_total, 2),
            "revenue_total": round(purchases_total, 2),
            "top_campaign_by_spend": campaigns_sorted_spend[0] if campaigns_sorted_spend else None,
            "top_campaign_by_sales": campaigns_sorted_sales[0] if campaigns_sorted_sales else None,
            "campaigns": campaigns_sorted_spend[:30],
            "top_adsets_by_spend": top_adsets_spend,
            "top_ads_by_spend": top_ads_spend,
            "top_ads_by_sales": top_ads_sales,
            "recommendations": auto_recommendations,
        }
        _save_report_json("meta_ads_snapshot.json", snapshot)
        return jsonify({"ok": True, "snapshot": snapshot}), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/meta/sync: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/diagnostics/redundancia", methods=["GET"])
def api_diagnostics_redundancia():
    """
    Diagnóstico de balões redundantes filtrados no engine.
    Query params:
      - hours: janela (1..168), default 24
      - limit: máximo de eventos retornados (1..500), default 120
      - node: filtra por node (opcional, ex: 3_coleta_profunda)
      - motivo: filtra por motivo (opcional, ex: foto_ja_recebida)
    """
    db = SessionLocal()
    try:
        hours = request.args.get("hours", default=24, type=int) or 24
        hours = max(1, min(hours, 168))
        limit = request.args.get("limit", default=120, type=int) or 120
        limit = max(1, min(limit, 500))
        node_filter = (request.args.get("node", default="", type=str) or "").strip().lower()
        motivo_filter = (request.args.get("motivo", default="", type=str) or "").strip().lower()

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = (
            db.query(models.EventoAudit)
            .filter(
                models.EventoAudit.evento == "engine_redundancia_filtrada",
                models.EventoAudit.timestamp >= since,
            )
            .order_by(models.EventoAudit.timestamp.desc())
        )
        rows = q.limit(max(limit * 3, 250)).all()

        por_motivo: dict[str, int] = {}
        por_node: dict[str, int] = {}
        serie_hora: dict[str, int] = {}
        eventos = []
        for ev in rows:
            d = ev.dados if isinstance(ev.dados, dict) else {}
            motivo = str(d.get("motivo") or "na")
            node = str(d.get("node") or "na")
            qtd = int(d.get("qtd") or 1)
            if node_filter and node.lower() != node_filter:
                continue
            if motivo_filter and motivo.lower() != motivo_filter:
                continue
            por_motivo[motivo] = int(por_motivo.get(motivo, 0) or 0) + qtd
            por_node[node] = int(por_node.get(node, 0) or 0) + qtd
            ts = ev.timestamp
            if ts:
                bucket = ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:00")
                serie_hora[bucket] = int(serie_hora.get(bucket, 0) or 0) + qtd
            eventos.append(
                {
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                    "lead_id": ev.lead_id,
                    "motivo": motivo,
                    "node": node,
                    "qtd": qtd,
                }
            )
        eventos = eventos[:limit]
        serie_ordenada = [{"bucket_utc": k, "qtd": serie_hora[k]} for k in sorted(serie_hora.keys())]

        return jsonify(
            {
                "window_hours": hours,
                "returned_events": len(eventos),
                "applied_filters": {"node": node_filter or None, "motivo": motivo_filter or None},
                "totais_por_motivo": por_motivo,
                "totais_por_node": por_node,
                "serie_por_hora": serie_ordenada,
                "eventos": eventos,
            }
        ), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/diagnostics/redundancia: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/diagnostics/robustez", methods=["GET"])
def api_diagnostics_robustez():
    """
    Diagnóstico de robustez operacional:
    - busy detectado/requeue/descarte
    - fallback por node crítico
    """
    db = SessionLocal()
    try:
        hours = request.args.get("hours", default=24, type=int) or 24
        hours = max(1, min(hours, 168))
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        eventos = (
            db.query(models.EventoAudit)
            .filter(
                models.EventoAudit.timestamp >= since,
                models.EventoAudit.evento.in_(
                    (
                        "engine_busy_detectado",
                        "engine_busy_requeued",
                        "engine_busy_discarded",
                        "inbox_backpressure_merged_oldest",
                        "node_fallback_acionado",
                        "inbox_batch_pronto",
                    )
                ),
            )
            .order_by(models.EventoAudit.timestamp.desc())
            .limit(2000)
            .all()
        )
        totals = {
            "engine_busy_detectado": 0,
            "engine_busy_requeued": 0,
            "engine_busy_discarded": 0,
            "inbox_backpressure_merged_oldest": 0,
            "node_fallback_acionado": 0,
            "inbox_batch_pronto": 0,
        }
        fallback_por_node: dict[str, int] = {}
        serie_hora: dict[str, int] = {}
        for ev in eventos:
            totals[ev.evento] = int(totals.get(ev.evento, 0) or 0) + 1
            if ev.evento == "node_fallback_acionado":
                d = ev.dados if isinstance(ev.dados, dict) else {}
                node = str(d.get("node") or "na")
                fallback_por_node[node] = int(fallback_por_node.get(node, 0) or 0) + 1
            ts = ev.timestamp
            if ts:
                bucket = ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:00")
                serie_hora[bucket] = int(serie_hora.get(bucket, 0) or 0) + 1
        return jsonify(
            {
                "window_hours": hours,
                "totais": totals,
                "fallback_por_node": fallback_por_node,
                "serie_por_hora": [{"bucket_utc": k, "qtd": serie_hora[k]} for k in sorted(serie_hora.keys())],
            }
        ), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/diagnostics/robustez: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/diagnostics/personalizacao", methods=["GET"])
def api_diagnostics_personalizacao():
    """
    Diagnóstico da personalização de copy/contexto.
    Query params:
      - hours: janela em horas (1..720), default 24
      - limit: máximo de leads analisados (5..400), default 100
      - min_msgs: mínimo de mensagens para avaliar lead (2..50), default 6
      - min_node: prefixo numérico mínimo do node (0..99), opcional; ex. 6 = só pós-node-5
    """
    db = SessionLocal()
    try:
        hours = request.args.get("hours", default=24, type=int)
        limit = request.args.get("limit", default=100, type=int)
        min_msgs = request.args.get("min_msgs", default=6, type=int)
        min_node_raw = request.args.get("min_node", default=None, type=int)
        min_node_prefix = (
            max(0, min(int(min_node_raw), 99)) if min_node_raw is not None else None
        )
        payload = auditar_personalizacao(
            db,
            hours=max(1, min(int(hours or 24), 720)),
            limit=max(5, min(int(limit or 100), 400)),
            min_msgs=max(2, min(int(min_msgs or 6), 50)),
            min_node_prefix=min_node_prefix,
        )
        return jsonify(payload), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/diagnostics/personalizacao: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/leads", methods=["GET"])
def get_leads():
    """Retorna lista de leads para chat/dashboard com filtros."""
    db = SessionLocal()
    try:
        limit = request.args.get("limit", default=120, type=int) or 120
        limit = max(10, min(limit, 500))
        status = (request.args.get("status", default="all", type=str) or "all").strip().lower()
        q = (request.args.get("q", default="", type=str) or "").strip().lower()
        sort = (request.args.get("sort", default="priority", type=str) or "priority").strip().lower()
        my_queue = (request.args.get("my_queue", default="0", type=str) or "0").strip().lower() in ("1", "true", "sim", "yes")
        operator = (request.args.get("operator", default="", type=str) or "").strip()

        tid = get_request_tenant_id()
        leads_q = db.query(models.Lead).filter(models.Lead.tenant_id == tid)

        if q:
            like = f"%{q}%"
            leads_q = leads_q.filter((models.Lead.nome.ilike(like)) | (models.Lead.telefone.ilike(like)))

        if sort == "recent":
            leads_q = leads_q.order_by(models.Lead.atualizado_em.desc())
        else:
            leads_q = leads_q.order_by(models.Lead.bot_pausado.desc(), models.Lead.atualizado_em.desc())
        leads = leads_q.limit(limit).all()

        out = []
        for l in leads:
            md = _lead_metadata_as_dict(getattr(l, "metadata_json", None))
            last_msg = (
                db.query(models.Mensagem)
                .filter(models.Mensagem.lead_id == l.id)
                .order_by(models.Mensagem.timestamp.desc())
                .first()
            )
            last_user = (
                db.query(models.Mensagem)
                .filter(models.Mensagem.lead_id == l.id, models.Mensagem.remetente == "user")
                .order_by(models.Mensagem.timestamp.desc())
                .first()
            )
            last_bot = (
                db.query(models.Mensagem)
                .filter(models.Mensagem.lead_id == l.id, models.Mensagem.remetente == "bot")
                .order_by(models.Mensagem.timestamp.desc())
                .first()
            )
            waiting_human = False
            unread_human = False
            sla_wait_minutes = 0
            resolved = False
            resolved_at = str(md.get("chat_resolvido_em") or "").strip()
            if last_user and (not last_bot or (last_user.timestamp and last_bot.timestamp and last_user.timestamp > last_bot.timestamp)):
                waiting_human = bool(l.bot_pausado or str(getattr(l, "ultimo_sentimento", "") or "").lower() in ("frustrado", "resistente"))
                unread_human = True
                if last_user.timestamp:
                    tsu = last_user.timestamp
                    if tsu.tzinfo is None:
                        tsu = tsu.replace(tzinfo=timezone.utc)
                    sla_wait_minutes = int(max(0, (datetime.now(timezone.utc) - tsu).total_seconds() // 60))
                if resolved_at and last_user.timestamp:
                    try:
                        rts = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                        if rts.tzinfo is None:
                            rts = rts.replace(tzinfo=timezone.utc)
                        if last_user.timestamp <= rts:
                            waiting_human = False
                            unread_human = False
                            sla_wait_minutes = 0
                            resolved = True
                    except Exception:
                        pass
            elif resolved_at:
                try:
                    _ = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                    resolved = True
                except Exception:
                    resolved = False

            manual_open = bool(getattr(l, "bot_pausado", False)) and (not bool(getattr(l, "convertido", False))) and (not resolved)
            new_message = bool(unread_human) and (not manual_open) and (not bool(getattr(l, "convertido", False))) and (not resolved)
            closed_chat = bool(getattr(l, "convertido", False)) or resolved
            open_in_progress = (not closed_chat) and (not new_message)

            fechamento_score = 0.0
            try:
                eng = float(l.score_engajamento or 0.0)
            except Exception:
                eng = 0.0
            if waiting_human:
                fechamento_score += 50.0
            if unread_human:
                fechamento_score += 25.0
            fechamento_score += min(25.0, eng * 20.0)
            if sla_wait_minutes >= 5:
                fechamento_score += min(20.0, sla_wait_minutes * 0.8)
            out.append(
                {
                    "id": l.id,
                    "nome": l.nome or l.telefone,
                    "telefone": l.telefone,
                    "node_atual": l.node_atual,
                    "bot_pausado": bool(getattr(l, "bot_pausado", False)),
                    "convertido": bool(getattr(l, "convertido", False)),
                    "sentimento": getattr(l, "ultimo_sentimento", "padrao"),
                    "score": round(l.score_engajamento, 3) if getattr(l, "score_engajamento", None) is not None else 0.5,
                    "atualizado_em": l.atualizado_em.isoformat() if l.atualizado_em else None,
                    "last_message_preview": (str(last_msg.texto or "").strip()[:90] if last_msg else ""),
                    "last_message_from": (str(last_msg.remetente or "") if last_msg else ""),
                    "waiting_human": waiting_human,
                    "unread_human": unread_human,
                    "is_resolved": resolved,
                    "is_manual_open": manual_open,
                    "is_new_message": new_message,
                    "is_closed_chat": closed_chat,
                    "is_open_in_progress": open_in_progress,
                    "sla_wait_minutes": int(sla_wait_minutes),
                    "closing_priority_score": round(float(fechamento_score), 2),
                    "owner_operator": str(md.get("chat_owner_operator") or ""),
                }
            )
        if status == "new":
            out = [x for x in out if bool(x.get("is_new_message"))]
        elif status == "open":
            out = [x for x in out if bool(x.get("is_open_in_progress"))]
        elif status == "closed":
            out = [x for x in out if bool(x.get("is_closed_chat"))]
        if sort == "priority":
            out = sorted(
                out,
                key=lambda x: (
                    bool(x.get("waiting_human")),
                    bool(x.get("unread_human")),
                    float(x.get("closing_priority_score") or 0.0),
                    str(x.get("atualizado_em") or ""),
                ),
                reverse=True,
            )
        if my_queue and operator:
            out = [x for x in out if str(x.get("owner_operator") or "").strip().lower() == operator.lower()]
        return jsonify(out), 200
    except Exception as e:
        logger.error(f"🚨 [API] Erro ao listar leads: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/leads/<int:lead_id>/resolve", methods=["POST"])
def resolve_lead_chat(lead_id: int):
    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"ok": False, "error": "not_found"}), 404
        md = _lead_metadata_as_dict(getattr(lead, "metadata_json", None))
        md["chat_resolvido_em"] = datetime.now(timezone.utc).isoformat()
        lead.metadata_json = md
        lead.bot_pausado = False
        db.commit()
        return jsonify({"ok": True, "resolved_at": md["chat_resolvido_em"]}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/chat/operators", methods=["GET", "POST"])
def api_chat_operators():
    state = _load_chat_ops_state()
    if request.method == "GET":
        return jsonify(
            {
                "ok": True,
                "operators": state.get("operators", []),
                "max_active_per_operator": int(state.get("max_active_per_operator", 10) or 10),
            }
        ), 200
    payload = request.get_json(silent=True) or {}
    ops = payload.get("operators") if isinstance(payload, dict) else None
    if not isinstance(ops, list):
        return jsonify({"ok": False, "error": "operators deve ser lista"}), 400
    clean = []
    for op in ops:
        s = str(op or "").strip()
        if s and s not in clean:
            clean.append(s)
    state["operators"] = clean[:20]
    try:
        max_active = int(payload.get("max_active_per_operator", state.get("max_active_per_operator", 10)))
    except Exception:
        max_active = int(state.get("max_active_per_operator", 10) or 10)
    state["max_active_per_operator"] = max(1, min(max_active, 200))
    state["rr_index"] = int(state.get("rr_index", 0) or 0)
    _save_chat_ops_state(state)
    return jsonify({"ok": True, "operators": state["operators"], "max_active_per_operator": state["max_active_per_operator"]}), 200


@app.route("/api/chat/assign", methods=["POST"])
def api_chat_assign():
    payload = request.get_json(silent=True) or {}
    lead_id = int(payload.get("lead_id") or 0) if isinstance(payload, dict) else 0
    if lead_id <= 0:
        return jsonify({"ok": False, "error": "lead_id inválido"}), 400
    state = _load_chat_ops_state()
    ops = state.get("operators") or []
    if not ops:
        return jsonify({"ok": False, "error": "sem operadores configurados"}), 400
    db = SessionLocal()
    try:
        # distribuição por menor carga (com fallback round-robin)
        carga = {str(op): 0 for op in ops}
        tid = get_request_tenant_id()
        leads_open = (
            db.query(models.Lead)
            .filter(models.Lead.convertido.is_(False), models.Lead.tenant_id == tid)
            .all()
        )
        for ld in leads_open:
            mdx = _lead_metadata_as_dict(getattr(ld, "metadata_json", None))
            ow = str(mdx.get("chat_owner_operator") or "")
            if ow in carga:
                carga[ow] += 1
        max_active = int(state.get("max_active_per_operator", 10) or 10)
        candidatos = [op for op in ops if carga.get(str(op), 0) < max_active] or list(ops)
        owner = str(sorted(candidatos, key=lambda o: (carga.get(str(o), 0), ops.index(o)))[0])
        # mantém ponteiro rr para desempates futuros
        idx = ops.index(owner) if owner in ops else int(state.get("rr_index", 0) or 0) % len(ops)
        state["rr_index"] = (idx + 1) % len(ops)
        _save_chat_ops_state(state)

        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"ok": False, "error": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"ok": False, "error": "not_found"}), 404
        md = _lead_metadata_as_dict(getattr(lead, "metadata_json", None))
        md["chat_owner_operator"] = owner
        md["chat_owner_assigned_em"] = datetime.now(timezone.utc).isoformat()
        lead.metadata_json = md
        db.commit()
        return jsonify({"ok": True, "owner_operator": owner}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/chat/rebalance", methods=["POST"])
def api_chat_rebalance():
    state = _load_chat_ops_state()
    ops = state.get("operators") or []
    if not ops:
        return jsonify({"ok": False, "error": "sem operadores configurados"}), 400
    payload = request.get_json(silent=True) or {}
    try:
        sla_threshold = int(payload.get("sla_threshold_minutes", 10)) if isinstance(payload, dict) else 10
    except Exception:
        sla_threshold = 10
    sla_threshold = max(1, min(sla_threshold, 180))
    max_active = int(state.get("max_active_per_operator", 10) or 10)

    db = SessionLocal()
    try:
        tid = get_request_tenant_id()
        leads = (
            db.query(models.Lead)
            .filter(models.Lead.convertido.is_(False), models.Lead.tenant_id == tid)
            .all()
        )
        carga = {str(op): 0 for op in ops}
        pendentes = []
        now = datetime.now(timezone.utc)
        for ld in leads:
            md = _lead_metadata_as_dict(getattr(ld, "metadata_json", None))
            owner = str(md.get("chat_owner_operator") or "")
            if owner in carga:
                carga[owner] += 1
            if not bool(getattr(ld, "bot_pausado", False)):
                continue
            last_user = (
                db.query(models.Mensagem)
                .filter(models.Mensagem.lead_id == ld.id, models.Mensagem.remetente == "user")
                .order_by(models.Mensagem.timestamp.desc())
                .first()
            )
            if not last_user or not last_user.timestamp:
                continue
            tsu = last_user.timestamp
            if tsu.tzinfo is None:
                tsu = tsu.replace(tzinfo=timezone.utc)
            wait_min = int(max(0, (now - tsu).total_seconds() // 60))
            if wait_min >= sla_threshold:
                pendentes.append((ld, md, wait_min))

        moved = []
        for ld, md, wait_min in pendentes:
            owner_now = str(md.get("chat_owner_operator") or "")
            candidates = [op for op in ops if carga.get(str(op), 0) < max_active] or list(ops)
            best = str(sorted(candidates, key=lambda o: (carga.get(str(o), 0), ops.index(o)))[0])
            if owner_now == best:
                continue
            md["chat_owner_operator"] = best
            md["chat_owner_assigned_em"] = now.isoformat()
            ld.metadata_json = md
            if owner_now in carga:
                carga[owner_now] = max(0, int(carga[owner_now]) - 1)
            carga[best] = int(carga.get(best, 0)) + 1
            moved.append({"lead_id": ld.id, "from": owner_now, "to": best, "sla_wait_minutes": wait_min})
        db.commit()
        return jsonify({"ok": True, "moved": moved, "moved_count": len(moved), "sla_threshold_minutes": sla_threshold}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/leads/<int:lead_id>/messages", methods=["GET"])
def get_messages(lead_id):
    """Retorna histórico e metadados minerados para o Radar Místico.

    Query: limit — últimas N mensagens (1–5000, default 2000) para conversas muito longas.
    """
    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"error": "Lead não encontrado", "code": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "Lead não encontrado", "code": "not_found"}), 404

        lim = request.args.get("limit", default=2000, type=int)
        if lim is None or lim < 1:
            lim = 2000
        lim = min(lim, 5000)

        q = db.query(models.Mensagem).filter_by(lead_id=lead_id)
        rows = (
            q.order_by(models.Mensagem.timestamp.desc())
            .limit(lim)
            .all()
        )
        rows = list(reversed(rows))
        include_total = (request.args.get("include_total", default="0", type=str) or "0").strip().lower() in ("1", "true", "yes", "sim")
        if include_total:
            total = q.count()
        else:
            total = len(rows)
        meta_raw = _lead_metadata_as_dict(lead.metadata_json)
        meta = _json_safe_for_api(meta_raw)
        wa_win = _whatsapp_care_window_info(db, lead_id)
        bot_state = _bot_state_snapshot_for_lead(db, lead)

        return jsonify({
            "messages": [{
                "id": m.id,
                "remetente": m.remetente,
                "texto": m.texto,
                "tipo": m.tipo,
                "media_url": getattr(m, "media_url", None),
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            } for m in rows],
            "metadata": meta,
            "lead_score": lead.score_engajamento or 0.5,
            "sentiment": lead.ultimo_sentimento or "padrao",
            "messages_total": total,
            "messages_returned": len(rows),
            "truncated": (total > len(rows)) if include_total else False,
            "whatsapp_meta": _json_safe_for_api(wa_win),
            "bot_state": bot_state,
            "whatsapp_policy_hint": (
                "Regra usual Meta: dentro de ~24h após a última mensagem do lead, mensagens de sessão para continuar "
                "o atendimento costumam ser aceitas. Fora disso, contatos proativos costumam exigir templates (HSM) "
                "pré-aprovados na categoria correta. Políticas e limites podem mudar; confira a documentação oficial "
                "Meta for Business / WhatsApp."
            ),
        }), 200
    except Exception as e:
        logger.error(f"🚨 [API] Erro ao carregar mensagens: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/leads/<int:lead_id>/funnel-snapshot", methods=["GET"])
def get_lead_funnel_snapshot(lead_id):
    """
    Snapshot da fase 1 (checklist / burst) para suporte e debug — mesma lógica que `flows.funnel_gates`.
    Query: texto_turno — texto da última mensagem do user neste turno (opcional; default vazio).
    """
    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"error": "Lead não encontrado", "code": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "Lead não encontrado", "code": "not_found"}), 404

        meta_raw = _lead_metadata_as_dict(lead.metadata_json)
        meta = dict(meta_raw or {})
        nome = (getattr(lead, "nome", None) or meta.get("nome_lead") or "").strip()
        texto_turno = (request.args.get("texto_turno", default="", type=str) or "").strip()

        from flows.funnel_gates import pendencias_fase1, snapshot_fase1_coleta

        snap = snapshot_fase1_coleta(meta, nome, texto_turno)
        pend = pendencias_fase1(meta, nome, texto_turno)

        return jsonify(
            _json_safe_for_api(
                {
                    "lead_id": lead_id,
                    "telefone": getattr(lead, "telefone", None),
                    "node_atual": getattr(lead, "node_atual", None),
                    "nome_lead_engine": nome,
                    "texto_turno_usado": texto_turno,
                    "snapshot": snap,
                    "pendencias": pend,
                }
            )
        ), 200
    except Exception as e:
        logger.error("🚨 [API] Erro /api/leads/%s/funnel-snapshot: %s", lead_id, e)
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/leads/<int:lead_id>/pause", methods=["POST"])
def toggle_pause(lead_id):
    """Ativa ou desativa o atendimento manual (Handoff)."""
    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead: return jsonify({"error": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "not_found"}), 404
        lead.bot_pausado = not getattr(lead, "bot_pausado", False)
        db.commit()
        logger.info(f"⏯️ [DASHBOARD] Bot {'PAUSADO' if lead.bot_pausado else 'ATIVADO'} para {lead.telefone}.")
        return jsonify({"bot_pausado": lead.bot_pausado}), 200
    finally:
        db.close()


@app.route("/api/leads/<int:lead_id>/resume-last-user", methods=["POST"])
def resume_last_user_turn(lead_id: int):
    """
    Reprocessa a última mensagem do usuário para retomada manual do atendimento.
    Não envia texto novo: apenas reaplica o último turno recebido.
    """
    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"error": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "not_found"}), 404
        last_user = (
            db.query(models.Mensagem)
            .filter(models.Mensagem.lead_id == lead.id, models.Mensagem.remetente == "user")
            .order_by(models.Mensagem.id.desc())
            .first()
        )
        if not last_user:
            return jsonify({"error": "no_user_message"}), 400
        texto = str(getattr(last_user, "texto", "") or "").strip()
        if not texto:
            return jsonify({"error": "empty_user_message"}), 400

        lead.bot_pausado = False
        db.commit()

        out = motor.processar_mensagem(
            str(getattr(lead, "telefone", "") or ""),
            texto,
            tipo_mensagem=str(getattr(last_user, "tipo", "text") or "text"),
        )
        return jsonify({"ok": True, "result": out or {"status": "ok"}}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/leads/<int:lead_id>/resend-current-block", methods=["POST"])
def resend_current_block(lead_id: int):
    """
    Reenvia o bloco atual do funil estático, limpando flags de dispatch/fase do bloco.
    """
    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"error": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "not_found"}), 404
        node = str(getattr(lead, "node_atual", "") or "").strip()
        if not node.startswith("static_meumisterio_"):
            return jsonify({"error": "not_static_node"}), 400

        md = _lead_metadata_as_dict(getattr(lead, "metadata_json", None))
        reset_map = {
            "static_meumisterio_b1": ["static_mm_b1_phase", "static_mm_b1_entregue"],
            "static_meumisterio_b2": ["static_mm_b2_phase", "static_mm_b2_seq_dispatched", "static_mm_b2_entregue"],
            "static_meumisterio_b3": ["static_mm_b3_phase", "static_mm_b3_seq_dispatched", "static_mm_b3_entregue"],
            "static_meumisterio_b4": ["static_mm_b4_phase", "static_mm_b4_seq_dispatched", "static_mm_b4_entregue"],
            "static_meumisterio_b5": ["static_mm_b5_phase", "static_mm_b5_seq_dispatched", "static_mm_b5_entregue"],
            "static_meumisterio_b6": ["static_mm_b6_seq_dispatched"],
        }
        for k in reset_map.get(node, []):
            md.pop(k, None)
        lead.metadata_json = md
        lead.bot_pausado = False
        db.commit()

        default_text = "quero minha consulta" if node == "static_meumisterio_b1" else "ok"
        out = motor.processar_mensagem(str(getattr(lead, "telefone", "") or ""), default_text, tipo_mensagem="text")
        return jsonify({"ok": True, "node": node, "result": out or {"status": "ok"}}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/leads/<int:lead_id>/advance-node", methods=["POST"])
def advance_lead_node(lead_id: int):
    """
    Avança manualmente o nó atual do funil estático para um nó alvo.
    """
    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"error": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "not_found"}), 404
        body = request.get_json(silent=True) or {}
        target_node = _normalizar_static_target_node(str(body.get("target_node") or "").strip())
        allowed = {
            "static_meumisterio_b1",
            "static_meumisterio_b2",
            "static_meumisterio_b3",
            "static_meumisterio_b4",
            "static_meumisterio_b5",
            "static_meumisterio_b6",
        }
        if target_node not in allowed:
            return jsonify({"error": "invalid_target_node"}), 400
        prev = str(getattr(lead, "node_atual", "") or "")
        if target_node == prev:
            maybe_next = _next_static_node(prev)
            if bool(body.get("auto_next")) and maybe_next:
                target_node = maybe_next
            else:
                return jsonify({"error": "same_target_node", "node": prev}), 400
        md = _lead_metadata_as_dict(getattr(lead, "metadata_json", None))
        reset_map = {
            "static_meumisterio_b1": ["static_mm_b1_phase", "static_mm_b1_entregue"],
            "static_meumisterio_b2": ["static_mm_b2_phase", "static_mm_b2_seq_dispatched", "static_mm_b2_entregue"],
            "static_meumisterio_b3": ["static_mm_b3_phase", "static_mm_b3_seq_dispatched", "static_mm_b3_entregue"],
            "static_meumisterio_b4": ["static_mm_b4_phase", "static_mm_b4_seq_dispatched", "static_mm_b4_entregue"],
            "static_meumisterio_b5": ["static_mm_b5_phase", "static_mm_b5_seq_dispatched", "static_mm_b5_entregue"],
            "static_meumisterio_b6": ["static_mm_b6_seq_dispatched"],
        }
        for k in reset_map.get(target_node, []):
            md.pop(k, None)
        lead.metadata_json = md
        lead.node_atual = target_node
        lead.bot_pausado = False
        db.add(
            models.EventoAudit(
                lead_id=lead.id,
                evento="manual_node_advance",
                dados={"from": prev, "to": target_node},
            )
        )
        db.commit()
        default_text = "quero minha consulta" if target_node == "static_meumisterio_b1" else "ok"
        out = motor.processar_mensagem(str(getattr(lead, "telefone", "") or ""), default_text, tipo_mensagem="text")
        return jsonify({"ok": True, "from": prev, "to": target_node, "result": out or {"status": "ok"}}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/leads/<int:lead_id>/send", methods=["POST"])
def send_manual(lead_id):
    """Envia mensagem manual do atendente via Meta API."""
    data = request.get_json()
    texto = data.get("texto", "").strip()
    if not texto: return jsonify({"error": "Mensagem vazia"}), 400

    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead: return jsonify({"error": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "not_found"}), 404

        wa_before = _whatsapp_care_window_info(db, lead.id)
        if not wa_before.get("within_24h_session"):
            return jsonify({
                "error": "Janela de atendimento (~24h) inativa. Aguarde uma mensagem do lead ou envie um template aprovado.",
                "code": "outside_24h_window",
                "whatsapp_meta": _json_safe_for_api(wa_before),
            }), 403

        # Envio Real via Engine utilizando o método privado de envio com retry
        if motor._enviar_com_retry(lead.telefone, "text", texto):
            # Salva no histórico como atendente
            m = models.Mensagem(
                lead_id=lead.id, 
                remetente="bot", 
                texto=f"👩‍💻 [ATENDENTE] {texto}",
                timestamp=datetime.now(timezone.utc)
            )
            db.add(m)
            # Ao intervir manualmente, pausamos o bot por segurança
            lead.bot_pausado = True 
            db.commit()
            return jsonify({"status": "ok", "whatsapp_meta": _json_safe_for_api(wa_before)}), 200
        return jsonify({"error": "Falha no envio via Meta"}), 500
    except Exception as e:
        db.rollback()
        logger.error(f"🚨 [API] Erro no envio manual: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/whatsapp/templates", methods=["GET"])
def list_whatsapp_templates():
    """Lista templates da WABA via Graph API (normalmente status APPROVED)."""
    if not WABA_ID or not WEBAPP_TOKEN:
        return jsonify({
            "templates": [],
            "warning": "Configure WABA_ID e WEBAPP_TOKEN no ambiente para listar templates.",
        }), 200
    try:
        url = f"https://graph.facebook.com/v21.0/{WABA_ID}/message_templates"
        r = requests.get(
            url,
            params={"fields": "name,status,language,category", "limit": 200},
            headers={"Authorization": f"Bearer {WEBAPP_TOKEN}"},
            timeout=25,
        )
        if r.status_code != 200:
            logger.warning("templates_list http=%s body=%s", r.status_code, (r.text or "")[:500])
            return jsonify({"templates": [], "error": (r.text or "")[:800]}), 200
        payload = r.json()
        rows = payload.get("data") or []
        out = []
        for t in rows:
            st = (t.get("status") or "").upper()
            if st and st != "APPROVED":
                continue
            lang = t.get("language")
            if isinstance(lang, dict):
                lc = (lang.get("code") or lang.get("locale") or "pt_BR") or "pt_BR"
            else:
                lc = (lang or "pt_BR") if isinstance(lang, str) else "pt_BR"
            out.append({
                "name": t.get("name"),
                "language": lc,
                "category": t.get("category"),
                "status": t.get("status"),
            })
        return jsonify({"templates": [x for x in out if x.get("name")]}), 200
    except Exception as e:
        logger.error("templates_list_exc %s", e, exc_info=True)
        return jsonify({"templates": [], "error": str(e)}), 200


@app.route("/api/leads/<int:lead_id>/send-template", methods=["POST"])
def send_whatsapp_template(lead_id):
    """Envia template (HSM) aprovado — permitido fora da janela de 24h."""
    data = request.get_json() or {}
    name = (data.get("template_name") or data.get("name") or "").strip()
    lang = (data.get("language") or "pt_BR").strip() or "pt_BR"
    body_texts = data.get("body_texts") or data.get("body_parameters")
    if isinstance(body_texts, str):
        body_texts = [ln.strip() for ln in body_texts.splitlines() if ln.strip()]
    elif isinstance(body_texts, list):
        body_texts = [str(x).strip() for x in body_texts if str(x).strip()]
    else:
        body_texts = []
    if not name:
        return jsonify({"error": "template_name obrigatório"}), 400

    db = SessionLocal()
    try:
        lead = db.get(models.Lead, lead_id)
        if not lead:
            return jsonify({"error": "not_found"}), 404
        if str(getattr(lead, "tenant_id", "default") or "default") != get_request_tenant_id():
            return jsonify({"error": "not_found"}), 404

        if not motor.enviar_template_hsm(lead.telefone, name, lang, body_texts):
            return jsonify({"error": "Falha ao enviar template via Meta (ver logs / permissões)."}), 500

        db.add(
            models.Mensagem(
                lead_id=lead.id,
                remetente="bot",
                texto=f"📋 [TEMPLATE Meta] {name} ({lang})",
                tipo="text",
                timestamp=datetime.now(timezone.utc),
            )
        )
        lead.bot_pausado = True
        db.commit()
        wa = _whatsapp_care_window_info(db, lead.id)
        return jsonify({"status": "ok", "whatsapp_meta": _json_safe_for_api(wa)}), 200
    except Exception as e:
        db.rollback()
        logger.error(f"🚨 [API] send-template: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/integrations/summary", methods=["GET"])
def integrations_summary():
    """URLs públicas e estado de configuração para o painel Integrações (sem expor segredos)."""
    base = (request.url_root or "").rstrip("/")
    redis_inbound = {"configured": False, "ready": False, "queue_key": None, "depth": None}
    if (os.getenv("REDIS_URL") or "").strip():
        redis_inbound["configured"] = True
        try:
            from reliability.redis_inbound import QUEUE_KEY, queue_depth, redis_inbound_ready

            redis_inbound["queue_key"] = QUEUE_KEY
            redis_inbound["ready"] = redis_inbound_ready()
            redis_inbound["depth"] = queue_depth()
        except Exception:
            pass
    return jsonify({
        "base_url": base,
        "webhooks": [
            {
                "id": "whatsapp",
                "label": "WhatsApp Cloud API",
                "path": "/webhook",
                "hint": "GET: verificação Meta (hub.verify_token). POST: mensagens e status.",
            },
            {
                "id": "cakto",
                "label": "Cakto (vendas / pedidos)",
                "path": "/webhook/cakto",
                "hint": "POST: notificações de pagamento e eventos configurados na Cakto.",
            },
        ],
        "meta": {
            "waba_configured": bool(WABA_ID),
            "phone_number_configured": bool(PHONE_NUMBER_ID),
            "token_configured": bool(WEBAPP_TOKEN),
            "verify_token_configured": bool(VERIFY_TOKEN),
        },
        "redis_inbound": redis_inbound,
        "docs": {
            "whatsapp_cloud": "https://developers.facebook.com/docs/whatsapp/cloud-api",
            "webhooks_graph": "https://developers.facebook.com/docs/graph-api/webhooks/getting-started",
        },
    }), 200


# ─────────────────────────────────────────────────────────────────────
# WEBHOOKS (META WHATSAPP)
# ─────────────────────────────────────────────────────────────────────

@app.route("/webhook", methods=["GET", "POST"])
def webhook_meta():
    """Ponto de entrada oficial para mensagens do WhatsApp."""
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("✅ [WEBHOOK] Token Meta validado.")
            return challenge, 200
        return "Forbidden", 403

    # Verificação HMAC SHA256 (Segurança Magno)
    if APP_SECRET:
        corpo_raw = request.get_data()
        assinatura = request.headers.get("X-Hub-Signature-256", "")
        mac = hmac.new(APP_SECRET.encode(), corpo_raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(f"sha256={mac}", assinatura):
            logger.warning("🚫 [SECURITY] Assinatura inválida detectada.")
            return "Invalid Signature", 403

    data = request.get_json(silent=True)
    if not data: return "NO_DATA", 400

    # Com REDIS_URL: fila durável (LPUSH) + worker BRPOP → mesma _triagem_meta. Senão: thread in-process.
    enqueued = False
    try:
        from reliability.redis_inbound import enqueue_inbound_webhook, redis_inbound_ready

        if redis_inbound_ready():
            enqueued = enqueue_inbound_webhook(data)
    except Exception as e:
        logger.warning("⚠️ [REDIS] Enfileiramento falhou — fallback thread: %s", e)
    if not enqueued:
        threading.Thread(target=_triagem_meta, args=(data,), daemon=True).start()
    return "EVENT_RECEIVED", 200

def _triagem_meta(data):
    """Extrai informações do JSON da Meta e gerencia Idempotência."""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        if "messages" not in value: return

        msg = value["messages"][0]
        msg_id = msg.get("id")

        # IDEMPOTÊNCIA (memória + SQLite): Meta pode reentregar o mesmo wamid após restart
        with LOCK_IDEMPOTENCIA:
            if msg_id and msg_id in CACHE_MENSAGENS:
                logger.debug("♻️ [TRAVA] Ignorando duplicata em memória: %s", msg_id)
                return
        if msg_id and not _try_claim_wamid_db(msg_id):
            with LOCK_IDEMPOTENCIA:
                if msg_id not in CACHE_MENSAGENS:
                    CACHE_MENSAGENS.append(msg_id)
            logger.info("♻️ [WEBHOOK] Duplicata durável ignorada (wamid já processado): %s", msg_id)
            return
        with LOCK_IDEMPOTENCIA:
            if msg_id:
                CACHE_MENSAGENS.append(msg_id)

        telefone = msg.get("from")
        tipo = msg.get("type")
        texto_recebido = ""
        img_url = ""
        media_url = ""
        media_id = ""
        nome_perfil_whatsapp = ""

        # Nome de perfil enviado pela Meta (quando disponível em contacts[*].profile.name)
        contatos = value.get("contacts") or []
        if isinstance(contatos, list) and contatos:
            c0 = contatos[0] or {}
            prof = c0.get("profile") if isinstance(c0, dict) else None
            if isinstance(prof, dict):
                nome_perfil_whatsapp = str(prof.get("name") or "").strip()
        
        # ── PROCESSAMENTO POR TIPO ──
        if tipo == "text":
            texto_recebido = msg.get("text", {}).get("body", "").strip()

        elif tipo == "interactive":
            # Captura resposta de botões interativos
            texto_recebido = msg.get("interactive", {}).get("button_reply", {}).get("title", "")

        elif tipo == "image":
            media_id = msg.get("image", {}).get("id")
            caption = msg.get("image", {}).get("caption", "")
            logger.info(f"🖼️ [MÍDIA] Imagem de {telefone}. Media ID: {media_id}")
            fp, _ = _baixar_midia(media_id)
            if fp:
                # Mesmo host do dashboard + absoluto via PUBLIC_URL no motor
                bn = os.path.basename(fp)
                img_url = f"/media/{bn}"
                media_url = img_url
            texto_recebido = caption

        elif tipo == "audio":
            media_id = msg.get("audio", {}).get("id")
            mime = msg.get("audio", {}).get("mime_type", "audio/ogg")
            logger.info(f"🎙️ [MÍDIA] Áudio de {telefone}. Transcrevendo...")
            fp, mime_real = _baixar_midia(media_id)
            if fp:
                media_url = f"/media/{os.path.basename(fp)}"
                texto_recebido = _transcrever_audio(fp, mime_real or mime)

        # LGPD opt-out detection (Frente 8.17): se lead pediu STOP, marca opt-out
        # automaticamente (sem entrar na fila do bot, evitando resposta automática).
        if tipo == "text" and texto_recebido:
            try:
                from api.saas.privacy import detect_opt_out
                if detect_opt_out(texto_recebido):
                    from db.database import SessionLocal
                    from db import models as _models
                    from datetime import datetime as _dt, timezone as _tz
                    from tenant_context import get_request_tenant_id
                    _db = SessionLocal()
                    try:
                        try:
                            _tid = get_request_tenant_id()
                        except Exception:
                            _tid = "default"
                        lead = _db.query(_models.Lead).filter_by(
                            tenant_id=_tid, telefone=telefone,
                        ).first()
                        if lead:
                            tags = list(lead.tags or [])
                            if "opted_out" not in tags:
                                tags.append("opted_out")
                            lead.tags = tags
                            meta = dict(lead.metadata_json or {})
                            meta["opted_out"] = True
                            meta["opted_out_at"] = _dt.now(_tz.utc).isoformat()
                            meta["opted_out_reason"] = "auto_detected_keyword"
                            lead.metadata_json = meta
                            _db.commit()
                            logger.warning(
                                "[privacy.opt_out.auto] tenant=%s telefone=%s keyword detected",
                                _tid, telefone,
                            )
                            return  # NÃO entra na fila — não responde automaticamente
                    finally:
                        _db.close()
            except Exception as exc:
                logger.warning("[privacy.opt_out.detect] falha (fail open): %s", exc)

        # Envia para a Fila do Lead via Manager
        payload = {
            "telefone": telefone,
            "texto_recebido": texto_recebido,
            "tipo_mensagem": tipo,
            "imagem_url": img_url,
            "media_url": media_url,
            "meta_msg_id": msg_id,
            "meta_media_id": media_id,
            "nome_perfil_whatsapp": nome_perfil_whatsapp,
        }
        inbox_manager.enqueue(telefone, payload)

    except Exception as e:
        logger.error(f"🚨 [TRIAGEM] Erro crítico na extração: {e}", exc_info=True)


def _bootstrap_redis_inbound_consumer():
    try:
        from reliability.redis_inbound import start_consumer_if_configured

        start_consumer_if_configured(_triagem_meta)
    except Exception as e:
        logger.warning("⚠️ [REDIS] Worker inbound não iniciado: %s", e)


_bootstrap_redis_inbound_consumer()

# ─────────────────────────────────────────────────────────────────────
# WEBHOOK (CAKTO) - GESTÃO DE VENDAS
# ─────────────────────────────────────────────────────────────────────

@app.route("/webhook/cakto", methods=["POST"])
def webhook_cakto():
    """Recebe notificações de pagamento e abandono do Cakto."""
    data = request.get_json(silent=True)
    if not data:
        return "NO_DATA", 400

    def _digitos(v: str) -> str:
        return "".join(ch for ch in str(v or "") if ch.isdigit())

    # Estruturas possíveis do webhook (status em raiz, em order, em data/object)
    status = str(
        data.get("status")
        or (data.get("order") or {}).get("status")
        or (data.get("data") or {}).get("status")
        or (data.get("object") or {}).get("status")
        or ""
    ).lower()
    evento = str(data.get("event") or data.get("type") or "").lower()

    # Busca telefone em múltiplos caminhos comuns
    telefone = _digitos(
        (data.get("customer") or {}).get("phone")
        or (data.get("order") or {}).get("customer_phone")
        or ((data.get("order") or {}).get("customer") or {}).get("phone")
        or ((data.get("data") or {}).get("customer") or {}).get("phone")
        or ((data.get("object") or {}).get("customer") or {}).get("phone")
        or data.get("phone")
    )
    if not telefone:
        return "NO_PHONE", 400

    # Alguns webhooks usam event sem status explícito
    if not status:
        if "abandon" in evento:
            status = "abandoned"
        elif any(x in evento for x in ("paid", "approved", "completed", "order.paid", "payment.approved")):
            status = "paid"

    # Auditoria básica + atualização de estado do lead (escopo do tenant do motor)
    db = SessionLocal()
    _tid = get_engine_tenant_id()
    lead = db.query(models.Lead).filter_by(telefone=telefone, tenant_id=_tid).first()
    if not lead and telefone.startswith("55"):
        lead = db.query(models.Lead).filter_by(telefone=f"+{telefone}", tenant_id=_tid).first()
    if not lead and not telefone.startswith("55"):
        lead = db.query(models.Lead).filter_by(telefone=f"55{telefone}", tenant_id=_tid).first()
    if not lead:
        lead = db.query(models.Lead).filter_by(telefone=f"+55{telefone}", tenant_id=_tid).first()

    node_para_gate = None
    if lead:
        pedido_ref = (
            str(data.get("id") or "")
            or str((data.get("order") or {}).get("id") or "")
            or str((data.get("data") or {}).get("id") or "")
        )
        produto = (
            str((data.get("order") or {}).get("product_name") or "")
            or str((data.get("order") or {}).get("offer_name") or "")
            or str((data.get("data") or {}).get("product_name") or "")
        )
        amount = _to_float(
            (data.get("order") or {}).get("amount")
            or (data.get("order") or {}).get("total")
            or (data.get("data") or {}).get("amount")
            or data.get("amount")
            or 0.0,
            0.0,
        )
        db.add(
            models.EventoAudit(
                lead_id=lead.id,
                evento="cakto_webhook",
                dados={"status": status, "event": evento, "pedido_ref": pedido_ref, "produto": produto, "amount": round(amount, 2)},
            )
        )
        if status in ["paid", "approved", "completed"]:
            lead.convertido = True
            if produto:
                lead.produto_comprado = produto[:200]
        node_para_gate = str(lead.node_atual or "")
        db.commit()
    db.close()

    # ── CENÁRIO A: Venda Aprovada ──────────
    if status in ["paid", "approved", "completed"]:
        logger.info(f"💰 [CAKTO] Venda aprovada para {telefone}.")
        _emit_meta_event("Purchase", telefone, value=float((data.get("order") or {}).get("amount") or 0.0))
        _cakto = CONFIG_CLIENTE.get("cakto") or {}
        if cakto_webhook_deve_iniciar_pos_venda(node_para_gate, _cakto):
            logger.info("💰 [CAKTO] Disparando pós-venda (motor) para %s node_atual=%s", telefone, node_para_gate)
            threading.Thread(target=motor.iniciar_fluxo_post_venda, args=(telefone,)).start()
        else:
            logger.info(
                "event=cakto_pos_venda_motor_skipped telefone=%s node_atual=%s "
                "webhook_dispara_pos_venda_ia=%s webhook_dispara_pos_venda_funil_estatico=%s",
                telefone,
                node_para_gate,
                _cakto.get("webhook_dispara_pos_venda_ia"),
                _cakto.get("webhook_dispara_pos_venda_funil_estatico"),
            )

    # ── CENÁRIO B: Abandono de Checkout ──────────
    elif status in ["abandoned", "checkout_abandoned"]:
        logger.info(f"🚪 [CAKTO] Abandono detectado: {telefone}. Recuperação pendente.")
        _emit_meta_event("InitiateCheckout", telefone, value=float((data.get("order") or {}).get("amount") or 0.0))
        # O motor de recuperação assumirá o lead no próximo ciclo
        threading.Thread(target=motor.iniciar_fluxo_recuperacao_abandono, args=(telefone, "abandonou")).start()

    return "OK", 200

# ─────────────────────────────────────────────────────────────────────
# UTILITÁRIOS: DOWNLOAD, STT E MANUTENÇÃO
# ─────────────────────────────────────────────────────────────────────

def _is_simulator_graph_media_id(media_id) -> bool:
    """True para IDs do `simulador_fantasmas.py` — não existem na Graph API."""
    if media_id is None:
        return False
    s = str(media_id).strip()
    return s in ("ID_IMAGEM_TESTE", "ID_AUDIO_TESTE") or (
        s.startswith("ID_") and "TESTE" in s.upper()
    )


def _baixar_midia(media_id):
    """Descarrega mídia da Meta via Graph API."""
    try:
        if _is_simulator_graph_media_id(media_id):
            logger.info(
                "🧪 [DOWNLOAD] Ignorado (media_id de simulador local, sem objeto na Meta): %s",
                media_id,
            )
            return None, None
        headers = {"Authorization": f"Bearer {WEBAPP_TOKEN}"}
        # 1. Obtém URL temporária de download
        r1 = requests.get(f"https://graph.facebook.com/v19.0/{media_id}", headers=headers, timeout=12)
        if r1.status_code != 200: 
            logger.error(f"❌ [DOWNLOAD] Erro Meta URL: {r1.text}")
            return None, None
            
        url = r1.json().get("url")
        mime = r1.json().get("mime_type", "")
        
        # 2. Descarrega o conteúdo binário real
        r2 = requests.get(url, headers=headers, timeout=30)
        if r2.status_code != 200: return None, None
        
        # Define extensão baseada no MIME
        ext = mime.split("/")[-1].split(";")[0] or "bin"
        filename = f"{media_id}.{ext}"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(r2.content)
            
        return filepath, mime
    except Exception as e:
        logger.error(f"❌ [DOWNLOAD] Falha fatal: {e}")
        return None, None

def _transcrever_audio(filepath, mime):
    """Usa o Gemini Pro como motor de Speech-to-Text de alta precisão."""
    if not os.path.exists(filepath): return "[Áudio ausente]"
    try:
        with open(filepath, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Endpoint de geração de conteúdo do Gemini (Flash ou Pro)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{STT_MODEL}:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime.split(";")[0], "data": audio_b64}},
                    {"text": "Transcreva o áudio literalmente em português, sem adicionar comentários ou introduções."}
                ]
            }],
            "generationConfig": {
                "temperature": 0.0, # Zero para máxima fidelidade
                "max_output_tokens": 1024
            }
        }
        
        resp = requests.post(url, json=payload, timeout=40)
        if resp.status_code == 200:
            res_json = resp.json()
            text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return text.strip() or "[Áudio inaudível]"
            
        logger.error(f"❌ [STT] Erro Gemini API: {resp.text}")
        return "[Áudio recebido]"
    except Exception as e:
        logger.error(f"❌ [STT] Erro na transcrição: {e}")
        return "[Falha no processamento de voz]"

def _limpeza_automatica():
    """Tarefa de background para manter o disco limpo de mídias temporárias."""
    while True:
        try:
            # Limite de 2 horas para mídias (tempo suficiente para a IA processar e o dashboard exibir)
            limite = time.time() - 7200 
            for f in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
                if os.path.getmtime(f) < limite:
                    os.remove(f)
            logger.debug("🧹 [CLEANUP] Ciclo de limpeza concluído.")
        except Exception: pass
        # Executa a limpeza a cada 1 hora
        time.sleep(3600)

# ─────────────────────────────────────────────────────────────────────
# BOOT DO SERVIDOR (PRODUCTION READY)
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Inicia tarefa de limpeza de mídias em thread separada
    threading.Thread(target=_limpeza_automatica, daemon=True, name="CleanupThread").start()

    logger.info(
        "🚀 [SYSTEM] AcassIA v8.7 — plataforma de funil (ex.: fluxo Cigana Esmeralda no motor de nós)."
    )
    logger.info("🔗 [DASHBOARD] Acesse em: http://localhost:5000/dashboard")
    
    # Execução com suporte a multithreading nativo do Flask para melhor performance
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
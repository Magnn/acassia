"""
engine.py — Versão SUPREME FINAL (A MÁQUINA TOTAL) — REVISADO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Circuit Breaker: .total_seconds() fixado.
✓ ModuleCache: Double-check locking (Zero travamentos).
✓ Config Injection: Injeta config_cliente em cada interação.
✓ DB Safety: Rollback isolado em falhas de gravação.
✓ VCard SUPREME: wa_id purificado + Formatação E164.
✓ Oráculo Libertado: _quebrar_baloes sem limite de fatiamento.
✓ Fila Anti-Zombie: Desbloqueio seguro e lock no .pop().

🔥 ATUALIZAÇÃO CRÍTICA (PROTOCOLO MAGNO): 
  - O Monitor de Recuperação agora arranca com intervalo de 2 minutos 
    para garantir o disparo exato do Ghosting Localizado aos 5 minutos.
"""

import os
import sys
import importlib
import logging
import time
import random
import threading
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional, List, Set

import requests

from db.database import SessionLocal
from db.models import (
    ABTestExposure,
    EventoAudit,
    FlowBlueprint,
    FlowPublish,
    Lead,
    LeadBehaviorEvent,
    Mensagem,
)
from ai.intent_classifier import IntentClassifier
from ai.context_compressor import ContextCompressor
from ai.sentiment_analyzer import SentimentAnalyzer
from ai.response_validator import ResponseValidator
from ai.recovery_engine import RecoveryEngine
from ai.stage_intelligence import enriquecer_contexto_stage
from analytics.funnel_audit import registrar_node_transition, registrar_silent_ack
from tts.audio_engine import AudioEngine
from config_cliente import CONFIG_CLIENTE
from flows.fase_1_preflight import (
    concat_texto_usuario,
    enriquecer_dados_node3_precoce,
    promover_burst_fase1_meta,
    resolver_avanco_node_fase1,
    sniffer_nome_confirmado_meta,
    sniffer_instagram_meta,
)
from flows.funnel_gates import (
    nome_eh_placeholder,
    sanear_lead_contato_sem_evento_sniffer,
    snapshot_fase1_coleta,
    sniffer_aplicar_fase1_flags,
    VOCATIVO_SEM_NOME,
)

# 🚨 IMPORTAÇÃO DAS DATACLASSES CENTRALIZADAS (Resolve o ImportError)
from schema import Acao, ContextoConversa
from copy_sanitizer import (
    BALAO_IA_REGEX_CORTE_FINAL,
    MOBILE_CHARS_POR_LINHA,
    MOBILE_MAX_LINHAS_BALO,
    preparar_texto_envio,
    delay_entre_baloes,
    delay_escuta_pos_audio,
    fatiar_texto_ritmo_celular,
    quebrar_por_linhas_max,
    aplicar_gancho_na_lista_acoes,
    normalizar_enxerto_dor_sem_contexto,
    tentar_salvar_balao_ia_cortado,
    extrair_evidencias_conversa,
    motivo_redundancia_texto,
    nome_lead_para_exibicao,
    preview_url_flag_para_whatsapp,
)
from flows.funil_estatico_meu_misterio.static_funnel_state import (
    apply_delivered,
    apply_dispatch_started,
    collect_static_sources_from_acoes,
    merge_metadata_for_persist,
)
from reliability.lead_metadata_atomic import atomic_patch_metadata_json, atomic_update_lead_columns
from reliability.distributed_lock import DistributedLock
from conversation_policy import (
    acoes_reparo_entrega_padrao,
    lead_reportou_problema_entrega,
)

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger(__name__)


def _abs_media_url_for_fetch(url: str) -> str:
    """URL absoluta para requests (IA baixa mídia); paths relativos usam PUBLIC_URL."""
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("/"):
        base = os.getenv("PUBLIC_URL", "http://127.0.0.1:5000").rstrip("/")
        return base + u
    return u

MAX_RETRY          = 3
CIRCUIT_THRESHOLD  = 5
CIRCUIT_RESET_TIME = 60    # segundos
ZOMBIE_TIMEOUT_SEG = 90    # 1,5 minuto (evita bloquear turnos reais por tempo excessivo)
# Pré-nó fase 1 (Instagram, burst, avanço): flows/fase_1_preflight.py

# ══════════════════════════════════════════════════════════════════════
# DISJUNTOR DE CIRCUITO (CIRCUIT BREAKER)
# ══════════════════════════════════════════════════════════════════════

class CircuitState(Enum):
    FECHADO = "fechado"
    ABERTO  = "aberto"

class CircuitBreaker:
    def __init__(self):
        self.falhas       = 0
        self.estado       = CircuitState.FECHADO
        self.ultima_falha = None
        self._lock        = threading.Lock()

    def pode_tentar(self) -> bool:
        with self._lock:
            if self.estado == CircuitState.ABERTO:
                segundos_desde_falha = (datetime.now() - self.ultima_falha).total_seconds()
                if segundos_desde_falha > CIRCUIT_RESET_TIME:
                    self.estado = CircuitState.FECHADO
                    self.falhas = 0
                    logger.info("⚡ [CIRCUIT] Reset após %.0fs. A retomar os envios.", segundos_desde_falha)
                    return True
                return False
            return True

    def registrar_falha(self):
        with self._lock:
            self.falhas      += 1
            self.ultima_falha = datetime.now()
            if self.falhas >= CIRCUIT_THRESHOLD:
                self.estado = CircuitState.ABERTO
                logger.error(f"🔴 [CIRCUIT] Aberto após {self.falhas} falhas consecutivas.")

    def registrar_sucesso(self):
        with self._lock:
            if self.falhas > 0:
                logger.info("🟢 [CIRCUIT] Normalizado.")
            self.falhas = 0
            self.estado = CircuitState.FECHADO


# ══════════════════════════════════════════════════════════════════════
# CACHE DE MÓDULOS (DOUBLE-CHECK LOCKING)
# ══════════════════════════════════════════════════════════════════════

class ModuleCache:
    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock  = threading.Lock()
        self._pastas = [
            "funil_estatico_meu_misterio",
            "fase_1_saudacao",
            "fase_2_leitura",
            "fase_3_oferta",
            "fase_3_recuperacao",
            "fase_4_entrega",
        ]

    def get(self, node_id: str) -> Optional[Any]:
        for pasta in self._pastas:
            mod_name = f"flows.{pasta}.node_{node_id}"
            filepath = os.path.join(_ROOT, "flows", pasta, f"node_{node_id}.py")

            if not os.path.exists(filepath):
                continue

            try:
                mtime_atual = os.path.getmtime(filepath)
            except OSError:
                continue

            with self._lock:
                entrada = self._cache.get(mod_name)

            if entrada:
                modulo, mtime_cache = entrada
                if mtime_atual == mtime_cache:
                    return modulo  # Cache hit (lock mínimo)

            # Importação pesada fora do lock principal
            try:
                if mod_name in sys.modules:
                    modulo = importlib.reload(sys.modules[mod_name])
                else:
                    modulo = importlib.import_module(mod_name)

                with self._lock:
                    self._cache[mod_name] = (modulo, mtime_atual)

                logger.debug(f"📦 [CACHE] Módulo '{mod_name}' carregado.")
                return modulo
            except Exception as e:
                logger.error(f"🚨 [CACHE] Falha ao carregar '{mod_name}': {e}")
                return None
        return None


# ══════════════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL (ENGINE)
# ══════════════════════════════════════════════════════════════════════

class Engine:
    def __init__(self, whatsapp_token: str, whatsapp_phone_id: str, personalizer=None, **kwargs):
        self.whatsapp_token    = whatsapp_token
        self.whatsapp_phone_id = whatsapp_phone_id
        self.personalizer      = personalizer
        self.tts_ativo         = kwargs.get("tts_ativo", False) or CONFIG_CLIENTE.get("tts_ativo", False)

        _gk = kwargs.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        self.wa_url = f"https://graph.facebook.com/v19.0/{whatsapp_phone_id}/messages"

        self.intent_classifier  = IntentClassifier(_gk)
        self.sentiment_analyzer = SentimentAnalyzer(_gk)
        self.response_validator = ResponseValidator(_gk)
        self.context_compressor = ContextCompressor(_gk)
        self.audio_engine       = AudioEngine() if self.tts_ativo else None

        self.recovery_engine = RecoveryEngine(whatsapp_token, whatsapp_phone_id, gemini_api_key=_gk)
        
        # 🚨 CORREÇÃO CRÍTICA PARA PROTOCOLO 5 MINUTOS:
        # Reduzido de 20 para 2 minutos para garantir que o sistema deteta a pausa atempadamente.
        # Guard: apenas UM worker Gunicorn inicia o monitor (distributed lock com TTL).
        # Se o worker morrer, o TTL expira e outro worker assume.
        self._recovery_monitor_started = False
        try:
            _monitor_lock = DistributedLock(
                "engine:recovery_monitor",
                ttl_ms=180_000,  # 3 min TTL — monitor roda a cada 2 min
            )
            if _monitor_lock.acquire(timeout=0.5):
                self.recovery_engine.iniciar_monitor(intervalo_minutos=2)
                self._recovery_monitor_started = True
                logger.info("[ENGINE] Recovery monitor iniciado (este worker ganhou o lock)")
            else:
                logger.info("[ENGINE] Recovery monitor já ativo em outro worker — skip")
        except Exception as exc:
            # Fallback: inicia localmente (melhor que não ter monitor)
            logger.warning("[ENGINE] Fallback: iniciando recovery monitor local: %s", exc)
            self.recovery_engine.iniciar_monitor(intervalo_minutos=2)
            self._recovery_monitor_started = True

        self._circuit   = CircuitBreaker()
        self._mod_cache = ModuleCache()
        # Pool reutilizável para NLU paralelo (intent + sentiment) — evita
        # criar/destruir threads a cada mensagem em alta carga.
        self._nlu_pool  = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="nlu",
        )
        
        self._leads_em_processamento: dict[int, float] = {}
        self._lock_proc = threading.Lock()
        self._envio_locks_guard = threading.Lock()
        self._envio_locks: dict[int, threading.Lock] = {}
        self._envio_locks_ts: dict[int, float] = {}  # lead_id → last_used timestamp
        # Distributed locks per-lead (Redis se disponível, fallback local)
        self._dist_locks: dict[int, DistributedLock] = {}
        self._dist_locks_guard = threading.Lock()
        self._lock_gc_interval_s = 600  # GC a cada 10 min
        self._lock_max_idle_s = 600     # locks não usados há 10 min são removidos
        try:
            from tenant_context import get_engine_tenant_id

            self._tenant_id_static = str(kwargs.get("tenant_id") or get_engine_tenant_id())
        except Exception:
            self._tenant_id_static = "default"
        self._monitor_retomada_estatica_ativo = False
        self._iniciar_monitor_retomada_estatica()

    @property
    def tenant_id(self) -> str:
        """
        Tenant corrente para esta chamada do engine. Lê:
            1. ContextVar override (multi-tenant webhook usa
               ``tenant_override_ctx(...)`` antes de chamar processar_mensagem)
            2. Tenant estático da construção (single-tenant legado / cron)
        """
        try:
            from tenant_context import _ENGINE_TENANT_OVERRIDE

            override = _ENGINE_TENANT_OVERRIDE.get()
            if override:
                return override
        except Exception:
            pass
        return self._tenant_id_static

    @tenant_id.setter
    def tenant_id(self, value: str) -> None:
        # Compat: codigos antigos que faziam motor.tenant_id = "x" continuam funcionando.
        self._tenant_id_static = str(value or "default")

    def _should_use_fallback_reply(self, node_atual: str) -> bool:
        """
        Decide se este tenant deve receber auto-reply de fallback em vez
        de cair no funil estatico legado.

        Regras:
            - Se ENV MEU_MISTERIO_TENANT_ID setada e bate com tenant atual -> usa
              funil legado (single-tenant deploy).
            - Senao, se tenant tem FlowPublish ou StudioPublish ativo ->
              segue normal (engine consome blueprint publicado).
            - Senao, se lead ja esta em node static_meumisterio -> deixa
              continuar pra nao quebrar conversas em andamento.
            - Senao, retorna True (fallback).
        """
        import os
        legacy_tenant = (os.getenv("MEU_MISTERIO_TENANT_ID") or "").strip()
        cur_tenant = self.tenant_id or "default"

        if legacy_tenant and legacy_tenant == cur_tenant:
            return False
        if node_atual.startswith("static_meumisterio_"):
            return False
        try:
            from flow_executor import tenant_has_published_content
            if tenant_has_published_content(cur_tenant):
                return False
        except Exception:
            pass
        return True

    def _enviar_fallback_reply(self, db, lead, telefone: str) -> dict:
        """
        Envia mensagem-padrao quando tenant nao tem flow publicado ainda.
        Texto pode ser customizado via TenantFlowVariable
        ``whatsapp.fallback_message`` (ate 1000 chars).

        Idempotencia: marca flag em metadata_json pra nao spammar — re-envia
        ate 1x por dia por lead.
        """
        from datetime import datetime, timezone, timedelta

        cur_tenant = self.tenant_id or "default"

        # 1) Resolve mensagem custom ou default
        custom_msg = None
        try:
            from api.tenant_config import get_tenant_config
            cfg = get_tenant_config(cur_tenant)
            wa_cfg = cfg.get("whatsapp") if isinstance(cfg, dict) else None
            if isinstance(wa_cfg, dict):
                custom_msg = wa_cfg.get("fallback_message")
        except Exception:
            pass

        msg = (custom_msg or
               "Olá! Recebi sua mensagem. Em breve responderei pessoalmente — "
               "estamos finalizando a configuração do atendimento. Obrigada pela "
               "paciência. ✦")
        msg = str(msg)[:1000]

        # 2) Idempotencia: nao mandar mesma mensagem mais de 1x/dia pro lead
        try:
            meta = dict(getattr(lead, "metadata_json", None) or {})
            last_sent_iso = meta.get("meumisterio_fallback_last_sent")
            if last_sent_iso:
                try:
                    last_sent = datetime.fromisoformat(last_sent_iso)
                    if last_sent.tzinfo is None:
                        last_sent = last_sent.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - last_sent < timedelta(hours=20):
                        logger.info(
                            "[engine.fallback] tenant=%s lead=%s ja recebeu fallback recente — skip",
                            cur_tenant, lead.id,
                        )
                        with self._lock_proc:
                            self._leads_em_processamento.pop(lead.id, None)
                        return {"status": "fallback_skipped"}
                except Exception:
                    pass
        except Exception:
            pass

        # 3) Envio
        try:
            ok = self.whatsapp_client.enviar_mensagem(telefone, msg, formato="texto") \
                if hasattr(self, "whatsapp_client") and self.whatsapp_client else False
            if not ok:
                # Fallback adicional: usar provider direto
                try:
                    from api.whatsapp_api import whatsapp_client as _wc
                    ok = _wc.enviar_mensagem(telefone, msg, formato="texto")
                except Exception:
                    ok = False
        except Exception as exc:
            logger.warning("[engine.fallback] envio falhou tenant=%s lead=%s: %s",
                           cur_tenant, lead.id, exc)
            ok = False

        # 4) Persist no historico de mensagens (mesmo se envio falhou — debug)
        try:
            self._salvar_mensagem(
                db, lead.id, "bot", msg, "text", auto_commit=False,
            )
        except Exception:
            pass

        # 5) Marca metadata + audit
        try:
            meta = dict(getattr(lead, "metadata_json", None) or {})
            meta["meumisterio_fallback_last_sent"] = datetime.now(timezone.utc).isoformat()
            lead.metadata_json = meta
            db.add(EventoAudit(
                lead_id=lead.id,
                evento="engine_fallback_no_flow_published",
                dados={"tenant_id": cur_tenant, "sent_ok": ok},
            ))
            db.commit()
        except Exception:
            db.rollback()

        with self._lock_proc:
            self._leads_em_processamento.pop(lead.id, None)
        return {"status": "fallback_sent", "ok": ok}

    def _iniciar_monitor_retomada_estatica(self) -> None:
        """
        Monitor de auto-retomada do funil estático:
        quando um lead respondeu e ficou sem resposta do bot após queda/restart,
        reenfileira o último turno do usuário automaticamente.

        Guard: usa DistributedLock para evitar múltiplos monitors em multi-worker.
        """
        try:
            enabled = bool(CONFIG_CLIENTE.get("funil_estatico_auto_retoma_ativo", True))
        except Exception:
            enabled = True
        if not enabled:
            return
        if self._monitor_retomada_estatica_ativo:
            return

        # Lock distribuído: apenas 1 worker roda o monitor
        try:
            _static_lock = DistributedLock(
                "engine:static_retomada_monitor",
                ttl_ms=120_000,  # 2 min TTL — monitor roda a cada 45s
            )
            if not _static_lock.acquire(timeout=0.5):
                logger.info("[ENGINE] Monitor retomada estática já ativo em outro worker — skip")
                return
        except Exception as exc:
            logger.debug("[ENGINE] Fallback: iniciando monitor retomada local: %s", exc)

        self._monitor_retomada_estatica_ativo = True
        th = threading.Thread(
            target=self._loop_monitor_retomada_estatica,
            daemon=True,
            name="static-mm-auto-retoma",
        )
        th.start()

    @staticmethod
    def _meta_as_dict(raw: Any) -> dict:
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str):
            try:
                obj = json.loads(raw)
                return dict(obj) if isinstance(obj, dict) else {}
            except Exception:
                return {}
        return {}

    @staticmethod
    def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _loop_monitor_retomada_estatica(self) -> None:
        interval_s = int(CONFIG_CLIENTE.get("funil_estatico_auto_retoma_intervalo_s", 45) or 45)
        grace_s = int(CONFIG_CLIENTE.get("funil_estatico_auto_retoma_grace_s", 360) or 360)
        cooldown_s = int(CONFIG_CLIENTE.get("funil_estatico_auto_retoma_cooldown_s", 600) or 600)
        interval_s = max(20, min(interval_s, 600))
        grace_s = max(120, min(grace_s, 3600))
        cooldown_s = max(120, min(cooldown_s, 7200))

        _gc_counter = 0
        _gc_every = max(1, int(self._lock_gc_interval_s / max(20, interval_s)))
        while True:
            try:
                self._executar_ciclo_retomada_estatica(grace_s=grace_s, cooldown_s=cooldown_s)
            except Exception as e:
                logger.warning("⚠️ [STATIC-RECOVER] ciclo falhou: %s", e)
            # GC periódico de lock dicts (a cada ~10 min)
            _gc_counter += 1
            if _gc_counter >= _gc_every:
                try:
                    self._gc_lock_dicts()
                except Exception:
                    pass
                _gc_counter = 0
            time.sleep(interval_s)

    def _executar_ciclo_retomada_estatica(self, *, grace_s: int, cooldown_s: int) -> None:
        db = SessionLocal()
        try:
            candidatos = (
                db.query(Lead)
                .filter(
                    Lead.tenant_id == (self.tenant_id or "default"),
                    Lead.node_atual.in_(
                        (
                            "static_meumisterio_b1",
                            "static_meumisterio_b2",
                            "static_meumisterio_b3",
                            "static_meumisterio_b4",
                            "static_meumisterio_b5",
                        )
                    ),
                )
                .all()
            )
            now = datetime.now(timezone.utc)
            for lead in candidatos:
                # Evita corrida com turnos em execução.
                with self._lock_proc:
                    if lead.id in self._leads_em_processamento:
                        continue

                last_user = (
                    db.query(Mensagem)
                    .filter(Mensagem.lead_id == lead.id, Mensagem.remetente == "user")
                    .order_by(Mensagem.id.desc())
                    .first()
                )
                if not last_user:
                    continue
                last_bot = (
                    db.query(Mensagem)
                    .filter(Mensagem.lead_id == lead.id, Mensagem.remetente == "bot")
                    .order_by(Mensagem.id.desc())
                    .first()
                )
                last_user_ts = self._as_utc(getattr(last_user, "timestamp", None))
                last_bot_ts = self._as_utc(getattr(last_bot, "timestamp", None)) if last_bot else None
                if last_bot_ts and last_user_ts and last_bot_ts >= last_user_ts:
                    continue
                if not last_user_ts:
                    continue
                age_s = (now - last_user_ts).total_seconds()
                if age_s < float(grace_s):
                    continue

                meta = self._meta_as_dict(getattr(lead, "metadata_json", None))
                last_msg_id = int(meta.get("static_mm_retomada_ultimo_user_msg_id", 0) or 0)
                last_try_iso = str(meta.get("static_mm_retomada_ultimo_attempt_at", "") or "").strip()
                last_try_at = None
                if last_try_iso:
                    try:
                        last_try_at = self._as_utc(datetime.fromisoformat(last_try_iso.replace("Z", "+00:00")))
                    except Exception:
                        last_try_at = None
                if last_msg_id == int(last_user.id) and last_try_at is not None:
                    if (now - last_try_at).total_seconds() < float(cooldown_s):
                        continue

                meta["static_mm_retomada_ultimo_user_msg_id"] = int(last_user.id)
                meta["static_mm_retomada_ultimo_attempt_at"] = now.isoformat()
                lead.metadata_json = meta
                db.commit()

                txt = str(getattr(last_user, "texto", "") or "").strip()
                if not txt:
                    continue
                logger.info(
                    "event=static_mm_auto_retomada lead_id=%s node=%s user_msg_id=%s age_s=%.1f",
                    lead.id,
                    str(getattr(lead, "node_atual", "") or ""),
                    int(last_user.id),
                    float(age_s),
                )
                try:
                    self.processar_mensagem(
                        str(getattr(lead, "telefone", "") or ""),
                        txt,
                        tipo_mensagem=str(getattr(last_user, "tipo", "text") or "text"),
                    )
                except Exception as e:
                    logger.warning(
                        "⚠️ [STATIC-RECOVER] falha ao retomar lead_id=%s: %s",
                        lead.id,
                        e,
                    )
        finally:
            db.close()

    def _lock_envio_lead(self, lead_id: int) -> threading.Lock:
        """Evita intercalar no WhatsApp balões de dois processamentos do mesmo lead."""
        with self._envio_locks_guard:
            lk = self._envio_locks.get(lead_id)
            if lk is None:
                lk = threading.Lock()
                self._envio_locks[lead_id] = lk
            self._envio_locks_ts[lead_id] = time.time()
            return lk

    def _gc_lock_dicts(self) -> None:
        """
        Garbage-collect de lock dicts para evitar memory leak.
        Remove locks não usados há mais de _lock_max_idle_s.
        Chamado periodicamente pelo monitor de retomada estática.
        """
        cutoff = time.time() - self._lock_max_idle_s
        evicted = 0

        # 1. _envio_locks — remove locks idle
        with self._envio_locks_guard:
            stale = [lid for lid, ts in self._envio_locks_ts.items() if ts < cutoff]
            for lid in stale:
                lk = self._envio_locks.get(lid)
                # Só remove se o lock NÃO está adquirido
                if lk is not None and not lk.locked():
                    self._envio_locks.pop(lid, None)
                    self._envio_locks_ts.pop(lid, None)
                    evicted += 1

        # 2. _leads_em_processamento — remove leads com timestamp stale
        with self._lock_proc:
            stale_proc = [lid for lid, ts in self._leads_em_processamento.items() if ts < cutoff]
            for lid in stale_proc:
                self._leads_em_processamento.pop(lid, None)
                evicted += 1

        if evicted > 0:
            logger.info(
                "[ENGINE_GC] Evicted %d stale locks (envio=%d, proc=%d, dist remaining=%d)",
                evicted, len(self._envio_locks), len(self._leads_em_processamento),
                len(self._dist_locks),
            )

    def acquire_lead_distributed_lock(self, lead_id: int, timeout: float = 8.0) -> bool:
        """
        Adquire lock distribuído para processamento do lead (cross-worker).
        Usa Redis SET NX se disponível, fallback para threading.Lock local.
        TTL de 90s evita deadlock se o worker crashar.
        """
        with self._dist_locks_guard:
            dl = self._dist_locks.get(lead_id)
            if dl is None:
                dl = DistributedLock(
                    f"engine:lead:{self.tenant_id}:{lead_id}",
                    ttl_ms=90_000,
                )
                self._dist_locks[lead_id] = dl
        return dl.acquire(timeout=timeout)

    def release_lead_distributed_lock(self, lead_id: int) -> None:
        """Libera lock distribuído do lead."""
        with self._dist_locks_guard:
            dl = self._dist_locks.pop(lead_id, None)
        if dl is not None:
            dl.release()

    def _pular_nlu_ia(self, texto: str, tipo_msg: str) -> bool:
        """
        Curto-circuito para alto volume:
        evita chamar intent/sentiment em ruído curto e confirmações triviais.
        """
        if (tipo_msg or "").lower() in {"image", "video", "audio"}:
            return True
        t = (texto or "").strip().lower()
        if not t:
            return True
        if len(t) <= 3:
            return True
        if len(t.split()) <= 2 and re.search(r"\b(ok|sim|pronto|beleza|blz|ta|tá|show|fechado)\b", t, re.I):
            return True
        # Cooldown de quota: evita insistir na API quando intent/sentiment já sinalizaram 429.
        try:
            if hasattr(self.intent_classifier, "em_cooldown_quota") and self.intent_classifier.em_cooldown_quota():
                return True
            if hasattr(self.sentiment_analyzer, "em_cooldown_quota") and self.sentiment_analyzer.em_cooldown_quota():
                return True
        except Exception:
            pass
        return False

    # ══════════════════════════════════════════════════════════════════
    # ROTA PRINCIPAL DE PROCESSAMENTO
    # ══════════════════════════════════════════════════════════════════

    def processar_mensagem(self, telefone: str, texto_recebido: str, **kwargs) -> dict:
        db = SessionLocal()
        try:
            lead     = self._obter_ou_criar_lead(db, telefone)
            tipo_msg = kwargs.get("tipo_mensagem", "text")
            nome_perfil = str(kwargs.get("nome_perfil_whatsapp") or "").strip()

            # Primeira ancoragem de nome via perfil WhatsApp (quando o lead ainda está sem nome útil).
            # Evita node 1 perguntar "como você se chama?" quando a Meta já trouxe um nome válido.
            if nome_perfil and nome_eh_placeholder(str(getattr(lead, "nome", "") or "")):
                toks = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,24}", nome_perfil)
                lixo = {
                    "oi", "ola", "olá", "sim", "ok", "pronto", "meumisterio", "esmeralda",
                    "meu", "bem", "anjo", "contato", "whatsapp",
                }
                if toks:
                    cand = toks[0].strip()
                    if cand and cand.lower() not in lixo:
                        lead.nome = cand.capitalize()
            # Há URL de imagem neste request → tratar como mídia (fila fundida ou payload legado)
            if (kwargs.get("imagem_url") or kwargs.get("media_url")) and tipo_msg not in ("image", "video", "audio"):
                tipo_msg = "image"

            # Bloqueio Anti-Zombie
            with self._lock_proc:
                agora = time.time()
                if lead.id in self._leads_em_processamento:
                    inicio = self._leads_em_processamento[lead.id]
                    if agora - inicio < ZOMBIE_TIMEOUT_SEG:
                        logger.info(
                            "event=engine_busy_drop_prevented lead=%s waited_s=%.1f timeout_s=%s",
                            lead.id,
                            (agora - inicio),
                            ZOMBIE_TIMEOUT_SEG,
                        )
                        db.add(
                            EventoAudit(
                                lead_id=lead.id,
                                evento="engine_busy_detectado",
                                dados={
                                    "waited_s": round(float(agora - inicio), 3),
                                    "timeout_s": int(ZOMBIE_TIMEOUT_SEG),
                                    "node": str(getattr(lead, "node_atual", "") or ""),
                                },
                            )
                        )
                        db.commit()
                        return {"status": "busy"}
                    logger.warning(f"⚡ [ENGINE] Lead {telefone} zombie libertado à força.")
                self._leads_em_processamento[lead.id] = agora

            try:
                media_url = kwargs.get("media_url") or kwargs.get("imagem_url") or None
                self._salvar_mensagem(
                    db,
                    lead.id,
                    "user",
                    texto_recebido,
                    tipo_msg,
                    media_url=media_url,
                    auto_commit=False,
                )

                ctx = ContextoConversa(
                    lead_id=lead.id,
                    telefone=telefone,
                    node_atual=lead.node_atual or "1_apresentacao",
                    historico=self._buscar_historico(db, lead.id, 20),
                    texto_recebido=texto_recebido,
                    tipo_mensagem=tipo_msg,
                    interactive_reply_id=kwargs.get("interactive_reply_id"),
                    nome_lead=lead.nome or "",
                    personalizer=self.personalizer,
                )

                # Injeta multimédia nos metadados (vision precisa de URL absoluta)
                imagem_url = _abs_media_url_for_fetch(
                    kwargs.get("imagem_url", "") or kwargs.get("media_url", "")
                )
                caption    = kwargs.get("caption", "")
                if imagem_url: ctx.metadata["imagem_url"] = imagem_url
                if caption: ctx.metadata["caption"] = caption

                # ── MULTI-TENANT FALLBACK ──
                # Tenant sem flow/studio publicado nao deve cair no funil estatico
                # legado (que e do tenant default). Manda auto-reply gentil.
                _node_atual_handoff = str(getattr(lead, "node_atual", "") or "")
                if self._should_use_fallback_reply(_node_atual_handoff):
                    return self._enviar_fallback_reply(db, lead, telefone)

                # ── HANDOFF: Verifica se o bot está pausado para atendimento humano ──
                _em_estatico_mm = _node_atual_handoff.startswith("static_meumisterio_")
                # Guardrail: no funil estático ativo, não manter pause legado/indevido.
                if _em_estatico_mm and bool(getattr(lead, "bot_pausado", False)) and not bool(getattr(lead, "convertido", False)):
                    lead.bot_pausado = False
                    try:
                        db.add(
                            EventoAudit(
                                lead_id=lead.id,
                                evento="handoff_guardrail_unpause_static",
                                dados={"node_atual": _node_atual_handoff},
                            )
                        )
                        db.commit()
                    except Exception:
                        db.rollback()
                    logger.info(
                        "event=handoff_guardrail_unpause_static lead=%s node=%s",
                        lead.id,
                        _node_atual_handoff,
                    )
                if getattr(lead, "bot_pausado", False):
                    logger.info(f"⏸️ [HANDOFF] Bot pausado para {telefone}. Apenas a registar mensagem.")
                    db.commit()
                    with self._lock_proc:
                        self._leads_em_processamento.pop(lead.id, None)
                    return {"status": "paused"}
                if self._lead_ja_passou_funil_ou_comprou(lead):
                    # Cliente já convertido/pós-funil não reentra no funil automático.
                    if not bool(getattr(lead, "bot_pausado", False)):
                        lead.bot_pausado = True
                    try:
                        db.add(
                            EventoAudit(
                                lead_id=lead.id,
                                evento="handoff_silencioso_pos_funil",
                                dados={
                                    "node_atual": str(getattr(lead, "node_atual", "") or ""),
                                    "convertido": bool(getattr(lead, "convertido", False)),
                                    "produto_comprado": str(getattr(lead, "produto_comprado", "") or "")[:120],
                                },
                            )
                        )
                    except Exception as e:
                        db.rollback()
                        logger.warning("⚠️ [AUDIT] handoff_pos_funil audit: %s", e)
                    logger.info(
                        "⏸️ [HANDOFF] Lead pós-funil/comprador (%s) desviado para atendimento silencioso.",
                        telefone,
                    )
                    logger.info(
                        "event=entrada_handoff_pos_funil lead=%s node=%s convertido=%s produto=%s",
                        lead.id,
                        str(getattr(lead, "node_atual", "") or ""),
                        bool(getattr(lead, "convertido", False)),
                        str(getattr(lead, "produto_comprado", "") or "")[:80],
                    )
                    db.commit()
                    with self._lock_proc:
                        self._leads_em_processamento.pop(lead.id, None)
                    return {"status": "paused_pos_funil"}

                # INJEÇÃO DA CONFIGURAÇÃO CENTRALIZADA
                ctx.metadata["__config__"] = self._config_para_ctx()
                ctx.metadata["tts_ativo"]  = self.tts_ativo
                # Funil estático: nunca NLU/Gemini nem stage_intel — mesmo se FUNIL_ESTATICO_ATIVO=0 no .env.
                _node_static_mm = str(getattr(lead, "node_atual", "") or "").startswith("static_meumisterio_")
                if CONFIG_CLIENTE.get("ia_motor_desligada") or _node_static_mm:
                    ctx.personalizer = None
                    ctx.metadata["ia_motor_desligada"] = True

                self._restaurar_memoria(lead, ctx)
                _node_inject = str(getattr(lead, "node_atual", "") or "")
                if not _node_inject.startswith("static_meumisterio_"):
                    try:
                        from studio_runtime import inject_published_studio_into_metadata

                        inject_published_studio_into_metadata(ctx.metadata, tenant_id=self.tenant_id)
                    except ImportError:
                        pass
                    except Exception as e:
                        logger.warning("⚠️ [ENGINE] studio_runtime inject falhou: %s", e)
                    try:
                        from flow_executor import inject_published_flow_metadata

                        inject_published_flow_metadata(ctx.metadata, tenant_id=self.tenant_id)
                    except ImportError:
                        pass
                    except Exception as e:
                        logger.warning("⚠️ [ENGINE] flow_executor inject falhou: %s", e)

                # Nome do lead: coluna `lead.nome` é fonte de verdade quando preenchida;
                # evita nodes usarem a primeira palavra da mensagem atual ("mandei", "foto") quando o JSON não tem nome_lead.
                nm_db = (getattr(lead, "nome", None) or "").strip()
                nm_meta = (ctx.metadata.get("nome_lead") or "").strip()

                def _nome_ok(n: str) -> bool:
                    return not nome_eh_placeholder(n)

                if _nome_ok(nm_db):
                    ctx.metadata["nome_lead"] = nm_db
                    ctx.nome_lead = nm_db
                elif _nome_ok(nm_meta):
                    ctx.nome_lead = nm_meta

                # ── GLOBAL SNIFFER (OUVIDO OMNISCIENTE) ──
                # Interceta mídias e desabafos antes do Node 3 — escritas em flows.funnel_gates.
                meta = ctx.metadata
                texto_sniff = (texto_recebido or "").strip()
                if not texto_sniff and meta.get("caption"):
                    texto_sniff = str(meta.get("caption") or "").strip()

                # ── BIRTH DATE SNIFFER (Frente 4.25) ──
                # Detecta data de nascimento em mensagem natural quando lead nao
                # tem birth_date ainda. So persiste em alta confianca + hint
                # textual de data — zero false-positive em conversas normais.
                if texto_sniff and not getattr(lead, "birth_date", None):
                    try:
                        import birthdate_extractor as _bde
                        _bd_result = _bde.sniff_and_persist(texto_sniff, lead)
                        if _bd_result is not None and _bd_result.date is not None:
                            ctx.metadata["lead_birth_date_capturado"] = _bd_result.date.isoformat()
                            _signo_bd = getattr(lead, "signo", None)
                            ctx.metadata["lead_signo_capturado"] = _signo_bd
                            if _signo_bd and not ctx.metadata.get("signo"):
                                ctx.metadata["signo"] = _signo_bd
                            try:
                                db.add(EventoAudit(
                                    lead_id=lead.id,
                                    evento="birth_date_auto_capturado",
                                    dados={
                                        "date": _bd_result.date.isoformat(),
                                        "confidence": _bd_result.confidence,
                                        "source": _bd_result.source,
                                        "signo": getattr(lead, "signo", None),
                                    },
                                ))
                            except Exception:
                                pass
                            logger.info(
                                "🎂 [SNIFFER] Birth date auto-capturado lead=%s date=%s signo=%s",
                                lead.id, _bd_result.date.isoformat(),
                                getattr(lead, "signo", "?"),
                            )
                    except Exception as _bd_exc:
                        logger.warning("[SNIFFER] birthdate falhou (fail-open): %s", _bd_exc)

                _tinha_contato_decl = bool(meta.get("lead_contato_salvo_declarado"))
                _ev_sniffer = sniffer_aplicar_fase1_flags(
                    meta,
                    tipo_mensagem=tipo_msg,
                    texto_sniff=texto_sniff,
                    historico=ctx.historico,
                )
                for ev in _ev_sniffer:
                    if ev == "foto_atual":
                        logger.info("👁️ [SNIFFER] Foto interceptada antecipadamente para o lead %s.", lead.id)
                    elif ev == "foto_historico":
                        logger.info(
                            "👁️ [SNIFFER] Foto já presente no histórico (lead=%s) — evita pedir de novo.",
                            lead.id,
                        )
                    elif ev == "contato_atual":
                        logger.info("📇 [SNIFFER] Lead declarou contato salvo (atual) lead=%s.", lead.id)
                    elif ev == "contato_historico":
                        logger.info("📇 [SNIFFER] Contato salvo declarado no histórico lead=%s.", lead.id)
                    elif ev == "desabafo":
                        logger.info("👂 [SNIFFER] Desabafo interceptado antecipadamente para o lead %s.", lead.id)

                if sanear_lead_contato_sem_evento_sniffer(
                    meta,
                    tinha_antes=_tinha_contato_decl,
                    eventos_sniffer=_ev_sniffer,
                ):
                    logger.warning(
                        "event=funnel_guardrail_contato_revertido lead=%s "
                        "(lead_contato_salvo_declarado sem evento contato_* do sniffer)",
                        lead.id,
                    )

                ctx.metadata = meta

                _tf_fase1 = concat_texto_usuario(ctx, texto_sniff)
                sniffer_nome_confirmado_meta(meta, _tf_fase1, lead.id)
                if not bool(meta.get("nome_confirmado_chat")):
                    logger.info(
                        "event=entrada_nome_pendente lead=%s node=%s",
                        lead.id,
                        str(getattr(lead, "node_atual", "") or ""),
                    )
                sniffer_instagram_meta(meta, _tf_fase1, lead.id)
                enriquecer_dados_node3_precoce(meta, _tf_fase1, lead.id)
                promover_burst_fase1_meta(meta, _tf_fase1, lead.id, lead)
                resolver_avanco_node_fase1(lead, ctx, meta)
                ctx.metadata = meta

                _snap = {}
                try:
                    _nm_snap = (
                        (getattr(ctx, "nome_lead", None) or meta.get("nome_lead") or "")
                    ).strip()
                    _snap = snapshot_fase1_coleta(meta, _nm_snap, texto_sniff or "")
                    logger.info(
                        "event=funnel_snapshot_fase1 lead=%s node=%s snap=%s",
                        lead.id,
                        getattr(ctx, "node_atual", ""),
                        _snap,
                    )
                except Exception as e:
                    logger.warning("⚠️ [ENGINE] snapshot_fase1_coleta falhou lead=%s: %s", lead.id, e)

                # Enriquecimento IA (com curto-circuito para alta escala)
                if CONFIG_CLIENTE.get("ia_motor_desligada") or _node_static_mm:
                    ctx.intencao = "padrao"
                    ctx.sentimento = "padrao"
                    ctx.score_engajamento = 0.5
                elif self._pular_nlu_ia(ctx.texto_recebido, tipo_msg):
                    ctx.intencao = "confirmacao" if re.search(
                        r"\b(ok|sim|pronto|beleza|blz|ta|tá|show|fechado)\b",
                        str(ctx.texto_recebido or "").lower(),
                        re.I,
                    ) else "padrao"
                    ctx.sentimento = "padrao"
                    ctx.score_engajamento = 0.5
                else:
                    try:
                        fut_i = self._nlu_pool.submit(
                            self.intent_classifier.classificar,
                            ctx.texto_recebido,
                            ctx.historico,
                            ctx.node_atual,
                            lead.id,
                        )
                        fut_s = self._nlu_pool.submit(
                            self.sentiment_analyzer.analisar,
                            ctx.texto_recebido,
                            ctx.historico,
                        )
                        ctx.intencao = fut_i.result()
                        sent = fut_s.result()
                    except Exception as exc:
                        logger.warning(
                            "⚠️ [ENGINE] NLU paralelo falhou (%s); a cair para sequencial.",
                            exc,
                        )
                        ctx.intencao = self.intent_classifier.classificar(
                            ctx.texto_recebido,
                            ctx.historico,
                            ctx.node_atual,
                            lead_id=lead.id,
                        )
                        sent = self.sentiment_analyzer.analisar(ctx.texto_recebido, ctx.historico)
                    ctx.sentimento = sent.get("sentimento", "padrao")
                    ctx.score_engajamento = sent.get("score", 0.5)

                # ── SENTIMENT ROUTING (Roteamento de Emergência) ──
                # Avalia urgência APÓS qualquer caminho (NLU ou skip).
                # Fast-path keywords de crise rodam SEMPRE, mesmo sem IA.
                try:
                    from ai.sentiment_router import evaluate_urgency, clear_urgency_if_resolved
                    _sent_for_routing = {
                        "sentimento": ctx.sentimento,
                        "score": ctx.score_engajamento,
                        "sinais": sent.get("sinais", []) if isinstance(sent, dict) else [],
                    } if 'sent' in dir() else {"sentimento": ctx.sentimento, "score": ctx.score_engajamento, "sinais": []}
                    _urgency = evaluate_urgency(_sent_for_routing, texto_recebido)
                    if _urgency.is_urgent and not getattr(lead, "is_urgent", False):
                        lead.is_urgent = True
                        lead.urgent_reason = (_urgency.reason or "")[:200]
                        lead.urgent_at = datetime.now(timezone.utc)
                        lead.ultimo_sentimento = ctx.sentimento
                        logger.warning(
                            "🚨 [SENTIMENT ROUTING] Lead %s marcado URGENTE: %s (severity=%s)",
                            lead.id, _urgency.reason, _urgency.severity,
                        )
                        db.add(EventoAudit(
                            lead_id=lead.id,
                            evento="sentiment_urgent_flagged",
                            dados={
                                "reason": _urgency.reason[:180],
                                "severity": _urgency.severity,
                                "sentimento": ctx.sentimento,
                                "score": round(ctx.score_engajamento, 3),
                            },
                        ))
                        # SSE push — operador vê lead pulando no topo do CRM em tempo real
                        try:
                            from api.saas.realtime_hooks import notify_lead_updated
                            notify_lead_updated(self.tenant_id, lead.id, changes={
                                "is_urgent": True,
                                "urgent_reason": _urgency.reason[:120],
                                "severity": _urgency.severity,
                            })
                        except Exception:
                            pass
                    elif getattr(lead, "is_urgent", False) and not _urgency.is_urgent:
                        # Auto-clear: sentimento melhorou
                        if clear_urgency_if_resolved(_sent_for_routing):
                            lead.is_urgent = False
                            lead.urgent_reason = None
                            lead.urgent_at = None
                            lead.ultimo_sentimento = ctx.sentimento
                            logger.info(
                                "✅ [SENTIMENT ROUTING] Lead %s urgência resolvida (sentimento=%s score=%.2f)",
                                lead.id, ctx.sentimento, ctx.score_engajamento,
                            )
                            db.add(EventoAudit(
                                lead_id=lead.id,
                                evento="sentiment_urgent_cleared",
                                dados={"sentimento": ctx.sentimento, "score": round(ctx.score_engajamento, 3)},
                            ))
                            try:
                                from api.saas.realtime_hooks import notify_lead_updated
                                notify_lead_updated(self.tenant_id, lead.id, changes={"is_urgent": False})
                            except Exception:
                                pass
                    else:
                        # Apenas persiste sentimento atual
                        lead.ultimo_sentimento = ctx.sentimento
                except Exception as _sr_exc:
                    logger.debug("[SENTIMENT ROUTING] Falhou (fail-open): %s", _sr_exc)

                # se qualquer submódulo IA entrou em cooldown, evita novas chamadas caras dos nodes.
                _ia_cooldown = False
                try:
                    _ia_cooldown = bool(
                        (hasattr(self.intent_classifier, "em_cooldown_quota") and self.intent_classifier.em_cooldown_quota())
                        or (hasattr(self.sentiment_analyzer, "em_cooldown_quota") and self.sentiment_analyzer.em_cooldown_quota())
                        or (hasattr(ctx.personalizer, "em_cooldown_quota") and ctx.personalizer.em_cooldown_quota())
                    )
                except Exception:
                    _ia_cooldown = False
                if _ia_cooldown:
                    ctx.metadata["_ia_quota_cooldown_ativo"] = True
                    ctx.personalizer = None
                    logger.info("event=ia_quota_cooldown_ativo lead=%s node=%s", lead.id, ctx.node_atual)

                # Inteligência por etapa (copy / funil — não altera FSM)
                if not _node_static_mm:
                    enriquecer_contexto_stage(
                        ctx,
                        lead,
                        texto_recebido=texto_recebido or "",
                        intencao=ctx.intencao,
                        sentimento=ctx.sentimento,
                    )

                # Fluxo publicado do builder tem prioridade no WhatsApp. Se o
                # gatilho não casar, o funil legado continua normalmente.
                flow_handled, flow_actions = self._try_published_flow_turn(db, lead, ctx)
                acoes = flow_actions if flow_handled else self._rotear_state_machine(db, lead, ctx)
                acoes, motivos_redundancia = self._filtrar_acoes_redundantes_por_contexto(ctx, acoes)
                resumo_turno = self._resumo_acoes_turno(acoes or [])
                self._registrar_evento_comportamental(
                    db,
                    lead,
                    event_type="turn_observed",
                    ctx=ctx,
                    payload={
                        "tipo_mensagem": str(tipo_msg or "text"),
                        "texto_chars": len(str(texto_recebido or "")),
                        "foto_atual": bool(tipo_msg in ("image", "video")),
                        "sniffer_eventos": list(_ev_sniffer or []),
                        "snapshot_fase1": dict(_snap) if isinstance(_snap, dict) else {},
                        "acoes": resumo_turno,
                        "intencao": str(getattr(ctx, "intencao", "") or "")[:50],
                        "sentimento": str(getattr(ctx, "sentimento", "") or "")[:50],
                    },
                )
                if motivos_redundancia:
                    for motivo, qtd in motivos_redundancia.items():
                        db.add(
                            EventoAudit(
                                lead_id=lead.id,
                                evento="engine_redundancia_filtrada",
                                dados={
                                    "motivo": str(motivo),
                                    "qtd": int(qtd),
                                    "node": str(getattr(ctx, "node_atual", "") or ""),
                                },
                            )
                        )
                # Auditoria de fallback de nodes críticos (6/7/8)
                for node_key in ("node6", "node7", "node8"):
                    k_flag = f"{node_key}_fallback_acionado_turno"
                    if ctx.metadata.pop(k_flag, False):
                        k_motivo = f"{node_key}_fallback_motivo"
                        motivo_fb = str(ctx.metadata.pop(k_motivo, "") or "")
                        db.add(
                            EventoAudit(
                                lead_id=lead.id,
                                evento="node_fallback_acionado",
                                dados={
                                    "node": node_key,
                                    "motivo": motivo_fb[:180],
                                    "node_atual": str(getattr(ctx, "node_atual", "") or ""),
                                },
                            )
                        )

                # Persiste progresso
                self._persistir_memoria(db, lead, ctx)

                # Disparo assíncrono para a Fila
                threading.Thread(
                    target=self._processar_fila,
                    args=(lead.id, ctx, acoes),
                    daemon=True,
                    name=f"fila-{telefone[-4:]}"
                ).start()
                # Libera processamento do lead imediatamente após despachar a fila de envio.
                # Evita exigir "reenvio" quando o usuário responde enquanto ainda há balões/delays sendo enviados.
                with self._lock_proc:
                    self._leads_em_processamento.pop(lead.id, None)

                return {"status": "ok"}

            except Exception as e:
                logger.error(f"🚨 [ENGINE] Erro interno {telefone}: {e}", exc_info=True)
                with self._lock_proc:
                    self._leads_em_processamento.pop(lead.id, None)
                return {"status": "error"}

        finally:
            db.close()

    # ══════════════════════════════════════════════════════════════════
    # ANTI-REDUNDÂNCIA GLOBAL (todos os nodes)
    # ══════════════════════════════════════════════════════════════════
    def _filtrar_acoes_redundantes_por_contexto(self, ctx: ContextoConversa, acoes: list[Acao]) -> tuple[list[Acao], dict[str, int]]:
        """
        Remove balões que pedem dados já enviados pelo lead (nome, foto, confirmação).
        Evita repetir perguntas em cadeia entre nodes.
        """
        if not acoes:
            return acoes, {}

        _na = str(getattr(ctx, "node_atual", "") or "")
        if _na.startswith("static_meumisterio_"):
            return acoes, {}

        evid = extrair_evidencias_conversa(
            texto_atual=getattr(ctx, "texto_recebido", "") or "",
            tipo_mensagem_atual=getattr(ctx, "tipo_mensagem", "") or "",
            historico=getattr(ctx, "historico", []) or [],
            metadata=getattr(ctx, "metadata", {}) or {},
            nome_lead=getattr(ctx, "nome_lead", "") or "",
        )

        def _texto_redundante(t: str) -> bool:
            return bool(motivo_redundancia_texto(t, evid))

        filtradas: list[Acao] = []
        removidas = 0
        motivos: dict[str, int] = {}
        for acao in acoes:
            if getattr(acao, "tipo", "") == "text" and _texto_redundante(getattr(acao, "conteudo", "") or ""):
                motivo = motivo_redundancia_texto(getattr(acao, "conteudo", "") or "", evid)
                removidas += 1
                if motivo:
                    motivos[motivo] = int(motivos.get(motivo, 0) or 0) + 1
                # remove delay imediatamente anterior para não deixar pausa "fantasma"
                if filtradas and getattr(filtradas[-1], "tipo", "") == "delay":
                    filtradas.pop()
                logger.info(
                    "event=engine_balao_suprimido_redundancia lead=%s node=%s motivo=%s trecho=%s",
                    getattr(ctx, "lead_id", None),
                    getattr(ctx, "node_atual", ""),
                    motivo or "na",
                    (getattr(acao, "conteudo", "") or "")[:90].replace("\n", " "),
                )
                continue
            filtradas.append(acao)

        if removidas:
            logger.info(
                "event=engine_acoes_redundantes_filtradas lead=%s node=%s removidas=%s",
                getattr(ctx, "lead_id", None),
                getattr(ctx, "node_atual", ""),
                removidas,
            )
        return filtradas, motivos

    # ══════════════════════════════════════════════════════════════════
    # FLUXOS CAKTO (WEBHOOKS)
    # ══════════════════════════════════════════════════════════════════

    def iniciar_fluxo_post_venda(self, telefone: str):
        db = SessionLocal()
        try:
            lead = self._obter_ou_criar_lead(db, telefone)
            node_antes = lead.node_atual
            lead.convertido = True
            _na_prev = str(node_antes or "")
            target_entrega = (
                "static_meumisterio_b7"
                if _na_prev.startswith("static_meumisterio_")
                else "14_confirmacao_entrega"
            )
            lead.node_atual = target_entrega
            try:
                registrar_node_transition(
                    db,
                    lead.id,
                    node_antes,
                    target_entrega,
                    intencao=None,
                    sentimento=None,
                    tipo_mensagem="system",
                    texto_recebido="",
                    origem="webhook_pos_venda",
                )
            except Exception as e:
                logger.warning("⚠️ [AUDIT] pos_venda: %s", e)
            db.commit()

            ctx = ContextoConversa(
                lead_id=lead.id, telefone=telefone, node_atual=target_entrega,
                historico=[], texto_recebido="SISTEMA_WEBHOOK", tipo_mensagem="system", 
                interactive_reply_id=None, nome_lead=(getattr(lead, "nome", "") or ""), personalizer=self.personalizer
            )
            ctx.metadata["__config__"] = self._config_para_ctx()
            try:
                from studio_runtime import inject_published_studio_into_metadata

                inject_published_studio_into_metadata(ctx.metadata, tenant_id=self.tenant_id)
            except ImportError:
                pass
            except Exception as e:
                logger.warning("⚠️ [ENGINE] studio_runtime inject falhou (pos_venda): %s", e)
            try:
                from flow_executor import inject_published_flow_metadata

                inject_published_flow_metadata(ctx.metadata, tenant_id=self.tenant_id)
            except ImportError:
                pass
            except Exception as e:
                logger.warning("⚠️ [ENGINE] flow_executor inject falhou (pos_venda): %s", e)
            self._restaurar_memoria(lead, ctx)
            # Tenta blueprint customizado do tenant (ADR_006); se ausente/falha,
            # cai no caminho legado _executar_node. Mantém retrocompat.
            acoes = self._compile_post_payment_blueprint(db, ctx, lead) \
                or self._executar_node(target_entrega, ctx, db, lead)
            self._processar_fila(lead.id, ctx, acoes)
        finally:
            db.close()

    def _config_para_ctx(self) -> dict:
        """
        Devolve config consolidada do tenant (deep-copy mutável) pra injetar em
        ``ctx.metadata["__config__"]``. Usa ``api.tenant_config.get_tenant_config``
        com fallback automático ao CONFIG_CLIENTE legado quando tenant não tem
        overrides em DB. Ver docs/MIGRACAO_CONFIG_CLIENTE.md.
        """
        import copy as _copy
        from api.tenant_config import get_tenant_config
        return _copy.deepcopy(dict(get_tenant_config(self.tenant_id)))

    def _compile_post_payment_blueprint(self, db, ctx, lead) -> Optional[List[Acao]]:
        """
        Compila o blueprint slug='post_payment' do tenant numa lista de Acao.

        Retorna None se:
          - tenant não tem blueprint slug='post_payment' (fallback ao caminho legado)
          - compilação levanta exceção (logged via logger.exception, fallback)

        Caller deve usar fluxo legado (_executar_node) quando retornar None.
        Ver ADR_006 (post-payment híbrido).
        """
        try:
            bp = db.query(FlowBlueprint).filter_by(
                tenant_id=self.tenant_id, slug="post_payment"
            ).first()
            if not bp:
                return None
            from flow_executor import document_to_acoes
            ctx_dict: dict = {
                "lead_id": lead.id,
                "telefone": getattr(lead, "telefone", "") or "",
                "nome": getattr(lead, "nome", "") or "",
                "node_atual": ctx.node_atual,
            }
            ctx_dict.update(ctx.metadata or {})
            acoes = document_to_acoes(
                bp.body_json or {},
                context=ctx_dict,
                tenant_id=self.tenant_id,
                blueprint_id=bp.id,
            )
            logger.info(
                "[engine] post_venda usando blueprint customizado: tenant=%s blueprint=%s acoes=%d",
                self.tenant_id, bp.id, len(acoes) if acoes else 0,
            )
            return acoes
        except Exception:
            logger.exception(
                "[engine] _compile_post_payment_blueprint falhou — fallback ao _executar_node"
            )
            return None

    def iniciar_fluxo_recuperacao_abandono(self, telefone: str, motivo: str = "abandonou"):
        db = SessionLocal()
        try:
            lead = self._obter_ou_criar_lead(db, telefone)
            if getattr(lead, "convertido", False):
                return

            acoes = self._montar_mensagens_recuperacao(motivo, lead)
            _nl_rec = (getattr(lead, "nome", None) or "").strip()
            _nome_lead_rec = _nl_rec if _nl_rec and not nome_eh_placeholder(_nl_rec) else VOCATIVO_SEM_NOME
            ctx = ContextoConversa(
                lead_id=lead.id, telefone=telefone, node_atual=lead.node_atual or "8_oferta_principal",
                historico=self._buscar_historico(db, lead.id, 5), texto_recebido=f"SISTEMA_ABANDONO_{motivo.upper()}",
                tipo_mensagem="system",
                interactive_reply_id=None,
                nome_lead=_nome_lead_rec,
                personalizer=self.personalizer
            )
            ctx.metadata["__config__"] = self._config_para_ctx()
            try:
                from studio_runtime import inject_published_studio_into_metadata

                inject_published_studio_into_metadata(ctx.metadata, tenant_id=self.tenant_id)
            except ImportError:
                pass
            except Exception as e:
                logger.warning("⚠️ [ENGINE] studio_runtime inject falhou (recuperacao): %s", e)
            try:
                from flow_executor import inject_published_flow_metadata

                inject_published_flow_metadata(ctx.metadata, tenant_id=self.tenant_id)
            except ImportError:
                pass
            except Exception as e:
                logger.warning("⚠️ [ENGINE] flow_executor inject falhou (recuperacao): %s", e)
            self._restaurar_memoria(lead, ctx)
            self._processar_fila(lead.id, ctx, acoes)
        except Exception as e:
            logger.error(f"🚨 [RECUPERAÇÃO] {telefone}: {e}", exc_info=True)
        finally:
            db.close()

    def _montar_mensagens_recuperacao(self, motivo: str, lead) -> list[Acao]:
        # Formatação do nome focada no tratamento correto
        nome = nome_lead_para_exibicao((getattr(lead, "nome", "") or "").strip()).capitalize()

        if motivo in ["pix_pendente", "pending", "waiting_payment", "pix_generated"]:
            return [
                Acao(tipo="delay", segundos=random.randint(8, 15)),
                Acao(tipo="text", conteudo=f"{nome}, vi que você iniciou a sua troca no altar... 🕯"),
                Acao(tipo="delay", segundos=random.randint(10, 18)),
                Acao(tipo="text", conteudo="A fenda ainda está aberta — o caminho foi preparado, mas o movimento ainda não foi concluído."),
                Acao(tipo="delay", segundos=random.randint(12, 20)),
                Acao(tipo="text", conteudo="Às vezes o PIX trava, ou a vida interrompe no momento errado. Se precisar de ajuda para finalizar, é só me falar. 🔮"),
            ]
        else:
            return [
                Acao(tipo="delay", segundos=random.randint(5, 12)),
                Acao(tipo="text", conteudo=f"{nome}... os guias me disseram que você chegou até a porta e recuou. 🔮"),
                Acao(tipo="delay", segundos=random.randint(12, 20)),
                Acao(tipo="text", conteudo="Isso não é coincidência — às vezes o próprio medo de mudar faz a gente hesitar no momento mais importante."),
                Acao(tipo="delay", segundos=random.randint(10, 16)),
                Acao(tipo="text", conteudo="Mas a situação que você me contou ainda está lá. Ainda pesa. Posso te ajudar a entender o que travou? 🙏"),
            ]

    # ══════════════════════════════════════════════════════════════════
    # FILA DE ENVIO
    # ══════════════════════════════════════════════════════════════════

    def _processar_fila(self, lead_id: int, ctx: ContextoConversa, acoes: list[Acao]):
        with self._lock_envio_lead(lead_id):
            self._processar_fila_corpo(lead_id, ctx, acoes)

    def _processar_fila_corpo(self, lead_id: int, ctx: ContextoConversa, acoes: list[Acao]):
        db       = SessionLocal()
        enviados = 0
        falhas   = 0
        pendentes_db = 0
        batch_commit = 5
        ultimo_tipo_enviado = ""
        delivered_static_sources: Set[str] = set()

        def _registrar_source_entregue(acao_obj: Acao) -> None:
            meta_acao = getattr(acao_obj, "metadata", None) or {}
            src = str(meta_acao.get("source") or "").strip().lower()
            if src.startswith("static_meumisterio_b"):
                delivered_static_sources.add(src)

        try:
            if acoes:
                aplicar_gancho_na_lista_acoes(acoes)
            planned_static_sources = collect_static_sources_from_acoes(acoes)
            if planned_static_sources:
                try:
                    ok_dispatch = atomic_patch_metadata_json(
                        db,
                        lead_id,
                        lambda old: apply_dispatch_started(old, planned_static_sources),
                        max_retries=6,
                    )
                    if not ok_dispatch:
                        lead_obj = db.query(Lead).filter(Lead.id == lead_id).first()
                        if lead_obj:
                            meta = apply_dispatch_started(
                                dict(getattr(lead_obj, "metadata_json", None) or {}),
                                planned_static_sources,
                            )
                            lead_obj.metadata_json = meta
                            db.commit()
                except Exception as e:
                    db.rollback()
                    logger.warning("⚠️ [FILA] dispatch_started patch falhou lead=%s: %s", lead_id, e)
            # Só neste disparo: evita repetir o mesmo balão fatiado duas vezes na mesma lista de ações.
            dedup_texto_neste_lote: Set[str] = set()
            is_fast_channel = str(ctx.telefone or "").startswith(("web_", "tg_"))
            for acao in acoes:
                if acao.tipo == "delay":
                    if is_fast_channel:
                        time.sleep(0.05)
                    else:
                        fator = 0.10 if acao.segundos < 5 else 0.20
                        jitter = acao.segundos * fator
                        time.sleep(max(0.5, acao.segundos + random.uniform(-jitter, jitter)))

                elif acao.tipo == "typing":
                    if not is_fast_channel:
                        _meta_ty = getattr(acao, "metadata", None) or {}
                        _kind = str(_meta_ty.get("whatsapp_typing") or "text").strip().lower()
                        if _kind not in ("text", "audio"):
                            _kind = "text"
                        self._enviar_typing_indicator(ctx.telefone, _kind)
                        time.sleep(random.uniform(0.35, 1.05))

                elif acao.tipo == "text":
                    _meta_ac = getattr(acao, "metadata", None) or {}
                    # Flow Builder (GPT/Agente): placeholder `runtime=llm` não envia o prompt (A1).
                    # Texto já gerado pelo Gemini em `flow_executor` usa `runtime=llm_gemini` (C2).
                    if (
                        str(_meta_ac.get("source") or "").strip().lower() == "flow_builder"
                        and str(_meta_ac.get("runtime") or "").strip().lower() == "llm"
                    ):
                        logger.warning(
                            "event=flow_builder_llm_skip lead=%s node=%s — prompt do bloco IA não enviado ao WhatsApp",
                            lead_id,
                            getattr(ctx, "node_atual", ""),
                        )
                        continue
                    # Flow Builder — anotação interna (B4): não enviar ao lead (ver docs/roadmap-canvas-orbita.md).
                    if (
                        str(_meta_ac.get("source") or "").strip().lower() == "flow_builder"
                        and str(_meta_ac.get("kind") or "").strip().lower() == "note"
                    ):
                        logger.info(
                            "event=flow_builder_note_skip lead=%s node=%s — anotação de fluxo não enviada ao WhatsApp",
                            lead_id,
                            getattr(ctx, "node_atual", ""),
                        )
                        continue
                    # Flow Builder — notificação de atendente (notificar/notificar_atendente): não enviar ao lead.
                    if (
                        str(_meta_ac.get("source") or "").strip().lower() == "flow_builder"
                        and _meta_ac.get("notify")
                    ):
                        logger.info(
                            "event=flow_builder_notify_atendente lead=%s node=%s msg=%s",
                            lead_id,
                            getattr(ctx, "node_atual", ""),
                            str(acao.conteudo or "")[:200],
                        )
                        continue
                    # Flow Builder — motor_ref sem execução ou com erro (C3): não enviar texto técnico ao lead.
                    _rt_m = str(_meta_ac.get("runtime") or "").strip().lower()
                    if str(_meta_ac.get("source") or "").strip().lower() == "flow_builder" and _rt_m in (
                        "motor_ref_pending",
                        "motor_ref_error",
                    ):
                        logger.info(
                            "event=flow_builder_motor_ref_skip lead=%s node=%s runtime=%s",
                            lead_id,
                            getattr(ctx, "node_atual", ""),
                            _rt_m,
                        )
                        continue
                    # Roteiro estático: um único balão, sem fatiar nem pipeline que colapsa espaços.
                    if _meta_ac.get("engine_texto_unico"):
                        fatiados = [str(acao.conteudo or "").rstrip()]
                    else:
                        _mb = int(_meta_ac.get("engine_max_baloes") or 0)
                        if _mb < 1:
                            _na_txt = str(getattr(ctx, "node_atual", "") or "")
                            # Funis estáticos: textos longos viram >6 pedaços; o cap global cortava o fim.
                            _mb = 24 if _na_txt.startswith("static_meumisterio_") else 6
                        _mb = max(1, min(_mb, 40))
                        fatiados = self._fatiar_texto_envio_seguro(acao.conteudo, max_baloes=_mb)
                    for balao in fatiados:
                        if _meta_ac.get("engine_copy_estatica"):
                            balao_limpo = (
                                (balao or "")
                                .replace("\u200b", "")
                                .replace("\u200c", "")
                                .replace("\u200d", "")
                                .replace("\ufeff", "")
                            )
                        else:
                            balao_limpo = self._blindar_texto_final_anti_corte(balao)
                            if not balao_limpo:
                                logger.warning(
                                    "⚠️ [ENGINE] Balão suprimido por truncamento irreparável. lead=%s node=%s",
                                    lead_id,
                                    getattr(ctx, "node_atual", ""),
                                )
                                continue
                        if not _meta_ac.get("engine_copy_estatica"):
                            balao_limpo = preparar_texto_envio(balao_limpo, "engine_fila_text")
                        # Smart greeting (Frente 4.26): {{smart_greeting}} -> texto dinamico
                        if balao_limpo and "{{" in balao_limpo:
                            try:
                                from smart_greeting import render_smart_greeting_in_text
                                # Carrega lead lazy — so quando {{...}} esta presente.
                                _lead_for_greeting = db.query(Lead).filter_by(id=lead_id).first()
                                if _lead_for_greeting is not None:
                                    balao_limpo = render_smart_greeting_in_text(
                                        balao_limpo, _lead_for_greeting,
                                        tenant_id=self.tenant_id,
                                    )
                            except Exception as _sg_exc:
                                logger.warning("[engine.smart_greeting] falha: %s", _sg_exc)
                        chave_dedup = self._normalizar_para_dedup(balao_limpo)
                        if chave_dedup and chave_dedup in dedup_texto_neste_lote:
                            logger.info(
                                "event=engine_suprime_balao_duplicado_mesmo_lote lead=%s node=%s trecho=%s",
                                lead_id,
                                getattr(ctx, "node_atual", ""),
                                (balao_limpo or "")[:90].replace("\n", " "),
                            )
                            continue
                        if (
                            not self._dedup_db_desligado_para_node(getattr(ctx, "node_atual", "") or "")
                            and self._deve_suprimir_balao_repetido(db, lead_id, balao_limpo)
                        ):
                            logger.info(
                                "event=engine_suprime_balao_duplicado lead=%s node=%s trecho=%s",
                                lead_id,
                                getattr(ctx, "node_atual", ""),
                                (balao_limpo or "")[:90].replace("\n", " "),
                            )
                            continue
                        if self._enviar_com_retry(ctx.telefone, "text", balao_limpo):
                            _registrar_source_entregue(acao)
                            if chave_dedup:
                                dedup_texto_neste_lote.add(chave_dedup)
                            self._salvar_mensagem(db, lead_id, "bot", balao_limpo, "text", auto_commit=False)
                            enviados += 1
                            pendentes_db += 1
                            if is_fast_channel or pendentes_db >= batch_commit:
                                db.commit()
                                pendentes_db = 0
                        else:
                            falhas += 1
                        if not is_fast_channel:
                            time.sleep(delay_entre_baloes())
                        ultimo_tipo_enviado = "text"

                elif acao.tipo == "vcard":
                    if ultimo_tipo_enviado == "text":
                        time.sleep(random.uniform(2.2, 3.4))
                    if self._enviar_com_retry(ctx.telefone, "vcard", acao.conteudo):
                        _registrar_source_entregue(acao)
                        self._salvar_mensagem(db, lead_id, "bot", "[vcard]", "vcard", auto_commit=False)
                        enviados += 1
                        pendentes_db += 1
                        ultimo_tipo_enviado = "vcard"
                        if pendentes_db >= batch_commit:
                            db.commit()
                            pendentes_db = 0
                    else:
                        falhas += 1

                elif acao.tipo == "tts":
                    if self.audio_engine and acao.tts_template:
                        try:
                            roteiro = preparar_texto_envio(acao.tts_template, "engine_tts")
                            tts_meta = getattr(acao, "metadata", None) or {}
                            try:
                                voice_style = float(tts_meta.get("voice_style") or 0.5)
                            except (TypeError, ValueError):
                                voice_style = 0.5
                            try:
                                voice_speed = float(tts_meta.get("voice_speed") or 1.0)
                            except (TypeError, ValueError):
                                voice_speed = 1.0
                            audio_url = self.audio_engine.gerar(
                                roteiro,
                                voice_name=str(tts_meta.get("voice_profile") or "").strip() or None,
                                style=max(0.0, min(1.0, voice_style)),
                                speed=max(0.5, min(2.0, voice_speed)),
                            )
                            sent_audio = bool(audio_url) and self._enviar_com_retry(
                                ctx.telefone,
                                "audio",
                                audio_url,
                                audio_voice=bool(tts_meta.get("whatsapp_voice", True)),
                            )
                            if sent_audio:
                                _registrar_source_entregue(acao)
                                self._salvar_mensagem(db, lead_id, "bot", "[tts]", "audio", auto_commit=False)
                                enviados += 1
                                pendentes_db += 1
                                if pendentes_db >= batch_commit:
                                    db.commit()
                                    pendentes_db = 0
                                time.sleep(delay_escuta_pos_audio())
                            else:
                                logger.warning("[TTS] Áudio indisponível. Fallback para texto.")
                                fb = preparar_texto_envio(acao.tts_template, "engine_tts_fallback")
                                if self._enviar_com_retry(ctx.telefone, "text", fb):
                                    _registrar_source_entregue(acao)
                                    self._salvar_mensagem(db, lead_id, "bot", fb, "text", auto_commit=False)
                                    enviados += 1
                                    pendentes_db += 1
                                    if pendentes_db >= batch_commit:
                                        db.commit()
                                        pendentes_db = 0
                                else:
                                    falhas += 1
                        except Exception as e:
                            logger.warning(f"⚠️ [TTS] Falha: {e}. Fallback para texto.")
                            fb = preparar_texto_envio(acao.tts_template, "engine_tts_fallback")
                            if self._enviar_com_retry(ctx.telefone, "text", fb):
                                _registrar_source_entregue(acao)
                                self._salvar_mensagem(db, lead_id, "bot", fb, "text", auto_commit=False)
                                enviados += 1
                                pendentes_db += 1
                                if pendentes_db >= batch_commit:
                                    db.commit()
                                    pendentes_db = 0
                            else:
                                falhas += 1
                    elif acao.tts_template:
                        fb = preparar_texto_envio(acao.tts_template, "engine_tts_disabled_fallback")
                        if self._enviar_com_retry(ctx.telefone, "text", fb):
                            _registrar_source_entregue(acao)
                            self._salvar_mensagem(db, lead_id, "bot", fb, "text", auto_commit=False)
                            enviados += 1
                            pendentes_db += 1
                            if pendentes_db >= batch_commit:
                                db.commit()
                                pendentes_db = 0
                        else:
                            falhas += 1

                elif acao.tipo == "audio":
                    payload_url = acao.url or acao.conteudo
                    _voice = bool((getattr(acao, "metadata", None) or {}).get("whatsapp_voice"))

                    # Frente 4.16 ext — auto-TTS via default voice quando
                    # conteudo nao parece ser URL e tenant tem voice padrao.
                    payload_str = str(payload_url or "").strip()
                    looks_like_url = payload_str.startswith(("http://", "https://", "/"))
                    if payload_str and not looks_like_url:
                        try:
                            import voice_provider as _vp
                            audio_bytes, info = _vp.synthesize_for_tenant(
                                self.tenant_id, payload_str,
                            )
                            if audio_bytes:
                                # Persist local + monta URL absoluta
                                import secrets as _secrets
                                import os as _os
                                _audio_dir = _os.path.join(
                                    _os.path.dirname(__file__), "media", "voice",
                                )
                                _os.makedirs(_audio_dir, exist_ok=True)
                                _file_id = _secrets.token_hex(8)
                                _filename = f"{self.tenant_id}_flow_{_file_id}.mp3"
                                _filepath = _os.path.join(_audio_dir, _filename)
                                with open(_filepath, "wb") as _f:
                                    _f.write(audio_bytes)
                                _public_base = (_os.getenv("PUBLIC_URL") or "").rstrip("/")
                                if _public_base:
                                    payload_url = f"{_public_base}/saas/voice/audio/{_file_id}"
                                    # Registra AudioGeneration
                                    try:
                                        from db import models as _ag_models
                                        db.add(_ag_models.AudioGeneration(
                                            tenant_id=self.tenant_id,
                                            voice_clone_id=info.get("voice_clone_id"),
                                            text=payload_str[:2000],
                                            chars_count=len(payload_str),
                                            audio_url=f"/saas/voice/audio/{_file_id}",
                                            provider="elevenlabs",
                                            status="done",
                                        ))
                                    except Exception:
                                        pass
                                    logger.info(
                                        "[engine.audio] auto-TTS tenant=%s voice=%s chars=%s",
                                        self.tenant_id, info.get("voice_clone_id"),
                                        info.get("chars_count"),
                                    )
                                else:
                                    logger.warning(
                                        "[engine.audio] PUBLIC_URL nao configurada — fallback texto",
                                    )
                                    # Fallback: envia como texto
                                    if self._enviar_com_retry(ctx.telefone, "text", payload_str):
                                        _registrar_source_entregue(acao)
                                        self._salvar_mensagem(db, lead_id, "bot", payload_str, "text", auto_commit=False)
                                        enviados += 1
                                        pendentes_db += 1
                                        if pendentes_db >= batch_commit:
                                            db.commit()
                                            pendentes_db = 0
                                    else:
                                        falhas += 1
                                    continue
                            else:
                                # Sem default voice ou falhou — fallback pra texto
                                reason = info.get("error_reason", "unknown")
                                logger.info(
                                    "[engine.audio] auto-TTS skip tenant=%s reason=%s — fallback texto",
                                    self.tenant_id, reason,
                                )
                                if self._enviar_com_retry(ctx.telefone, "text", payload_str):
                                    _registrar_source_entregue(acao)
                                    self._salvar_mensagem(db, lead_id, "bot", payload_str, "text", auto_commit=False)
                                    enviados += 1
                                    pendentes_db += 1
                                    if pendentes_db >= batch_commit:
                                        db.commit()
                                        pendentes_db = 0
                                else:
                                    falhas += 1
                                continue
                        except Exception as _tts_exc:
                            logger.warning("[engine.audio] auto-TTS erro: %s", _tts_exc)
                            # cai pro envio como URL (que pode ser invalida — mas mantém compat)

                    if payload_url and self._enviar_com_retry(
                        ctx.telefone, "audio", payload_url, audio_voice=_voice
                    ):
                        _registrar_source_entregue(acao)
                        self._salvar_mensagem(db, lead_id, "bot", "[audio]", "audio", auto_commit=False)
                        enviados += 1
                        pendentes_db += 1
                        if pendentes_db >= batch_commit:
                            db.commit()
                            pendentes_db = 0
                        time.sleep(delay_escuta_pos_audio())
                        ultimo_tipo_enviado = "audio"
                    else:
                        falhas += 1

                elif acao.tipo == "pix":
                    # Frente 7.1 — gera Pix QR + envia QR + texto copia-e-cola
                    try:
                        meta = getattr(acao, "metadata", None) or {}
                        amount = float(meta.get("amount_brl") or 0)
                        description = str(meta.get("description") or acao.conteudo or "Pagamento")
                        expires_min = int(meta.get("expires_min") or 30)
                        if amount <= 0:
                            logger.warning("[engine.pix] amount inválido — pulando")
                            continue
                        from api.payments.pix_provider import create_pix_mercadopago, PixProviderError
                        try:
                            result = create_pix_mercadopago(
                                tenant_id=getattr(self, "tenant_id", None) or "default",
                                amount_brl=amount,
                                description=description,
                                expires_min=expires_min,
                                external_reference=f"lead_{lead_id}",
                            )
                            # Persiste PixPayment
                            from db import models as _models
                            pix_row = _models.PixPayment(
                                tenant_id=getattr(self, "tenant_id", None) or "default",
                                lead_id=lead_id,
                                provider="mercadopago",
                                provider_payment_id=result.provider_payment_id,
                                amount_brl_cents=result.amount_brl_cents,
                                description=description,
                                qr_code_image_url=result.qr_code_image_url,
                                qr_code_text=result.qr_code_text,
                                expires_at=result.expires_at,
                                status="pending",
                                raw_response=result.raw,
                            )
                            db.add(pix_row)
                            db.commit()

                            # Envia mensagem com QR + copia-e-cola
                            msg_text = (
                                f"💜 Pagamento de R${amount:.2f} — {description}\n\n"
                                f"📱 Copia e cola:\n{result.qr_code_text}\n\n"
                                f"⏱ Vence em {expires_min} minutos."
                            )
                            if self._enviar_com_retry(ctx.telefone, "text", msg_text):
                                _registrar_source_entregue(acao)
                                self._salvar_mensagem(db, lead_id, "bot", msg_text, "text", auto_commit=False)
                                enviados += 1
                                pendentes_db += 1
                                if pendentes_db >= batch_commit:
                                    db.commit()
                                    pendentes_db = 0
                            else:
                                falhas += 1
                        except PixProviderError as exc:
                            logger.warning(f"⚠️ [PIX] Falha provider: {exc}")
                            falhas += 1
                    except Exception as e:
                        logger.warning(f"⚠️ [PIX] erro inesperado: {e}")
                        falhas += 1

                elif acao.tipo == "voice_clone":
                    # Frente 4.16 — gera TTS na voz clonada e manda como audio
                    try:
                        meta = getattr(acao, "metadata", None) or {}
                        text = (acao.conteudo or meta.get("text") or "").strip()
                        clone_id = meta.get("voice_clone_id")
                        if not text or not clone_id:
                            logger.warning("[engine.voice_clone] missing text/clone_id")
                            continue
                        from db import models as _models
                        clone = db.query(_models.VoiceClone).filter_by(id=int(clone_id)).first()
                        if not clone or clone.deleted_at:
                            logger.warning("[engine.voice_clone] clone %s não disponível", clone_id)
                            continue
                        import voice_provider as vp
                        try:
                            audio_bytes = vp.synthesize_elevenlabs(
                                tenant_id=clone.tenant_id,
                                voice_id=clone.provider_voice_id,
                                text=text,
                            )
                            # Salva em /media/voice/
                            import os, secrets
                            audio_dir = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)),
                                "media", "voice",
                            )
                            os.makedirs(audio_dir, exist_ok=True)
                            file_id = secrets.token_hex(8)
                            filename = f"{clone.tenant_id}_engine_{file_id}.mp3"
                            filepath = os.path.join(audio_dir, filename)
                            with open(filepath, "wb") as f:
                                f.write(audio_bytes)

                            # Audio URL pública (servidor próprio)
                            audio_url = f"/media/voice/{filename}"

                            # Send via WA com tag voice
                            if self._enviar_com_retry(
                                ctx.telefone, "audio", audio_url, audio_voice=True,
                            ):
                                _registrar_source_entregue(acao)
                                self._salvar_mensagem(db, lead_id, "bot", "[voice_clone]", "audio", auto_commit=False)
                                # Track AudioGeneration
                                db.add(_models.AudioGeneration(
                                    tenant_id=clone.tenant_id,
                                    voice_clone_id=clone.id,
                                    text=text[:2000],
                                    chars_count=len(text),
                                    audio_url=audio_url,
                                    provider="elevenlabs",
                                    status="done",
                                ))
                                enviados += 1
                                pendentes_db += 1
                                if pendentes_db >= batch_commit:
                                    db.commit()
                                    pendentes_db = 0
                                time.sleep(delay_escuta_pos_audio())
                                ultimo_tipo_enviado = "audio"
                            else:
                                falhas += 1
                        except vp.VoiceProviderError as exc:
                            logger.warning(f"⚠️ [VOICE] {exc}")
                            falhas += 1
                    except Exception as e:
                        logger.warning(f"⚠️ [VOICE] erro inesperado: {e}")
                        falhas += 1

                else:
                    payload_url = acao.url or acao.conteudo
                    if acao.tipo in ("image", "video") and ultimo_tipo_enviado == "text":
                        time.sleep(random.uniform(1.4, 2.4))
                    if payload_url and self._enviar_com_retry(ctx.telefone, acao.tipo, payload_url):
                        _registrar_source_entregue(acao)
                        self._salvar_mensagem(db, lead_id, "bot", f"[{acao.tipo}]", acao.tipo, auto_commit=False)
                        enviados += 1
                        pendentes_db += 1
                        ultimo_tipo_enviado = acao.tipo
                        if pendentes_db >= batch_commit:
                            db.commit()
                            pendentes_db = 0
                    else:
                        falhas += 1

        except Exception as e:
            logger.error(f"🚨 [FILA] Erro no lead {lead_id}: {e}", exc_info=True)

        finally:
            if pendentes_db > 0:
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.warning("⚠️ [FILA] commit final falhou lead=%s: %s", lead_id, e)
            if delivered_static_sources:
                try:
                    ok_del = atomic_patch_metadata_json(
                        db,
                        lead_id,
                        lambda old: apply_delivered(old, delivered_static_sources),
                        max_retries=6,
                    )
                    if not ok_del:
                        lead_obj = db.query(Lead).filter(Lead.id == lead_id).first()
                        if lead_obj:
                            meta = apply_delivered(
                                dict(getattr(lead_obj, "metadata_json", None) or {}),
                                delivered_static_sources,
                            )
                            lead_obj.metadata_json = meta
                            db.commit()
                except Exception as e:
                    db.rollback()
                    logger.warning("⚠️ [FILA] apply_delivered patch falhou lead=%s: %s", lead_id, e)
            db.close()
            with self._lock_proc:
                self._leads_em_processamento.pop(lead_id, None)

    def _quebrar_baloes(self, texto: str) -> list[str]:
        if "[BALAO]" in texto:
            return [b.strip() for b in texto.split("[BALAO]") if b.strip()]
        return [p.strip() for p in texto.split("\n\n") if p.strip()]

    _RE_URL_NO_TEXTO = re.compile(r"(https?://\S+)", re.I)

    @staticmethod
    def _limpar_pontuacao_apos_url(u: str) -> str:
        """Remove vírgula/ponto final colado ao link (não quebra o path com /)."""
        s = (u or "").strip()
        while len(s) > 12 and s[-1] in ".,;:!?）":
            s = s[:-1]
        return s

    def _fatiar_texto_envio_seguro(self, texto: str, *, max_baloes: int = 6) -> list[str]:
        """
        Fatiamento resiliente para WhatsApp:
        preserva sentenças, corta excesso e evita explosão de balões.
        Qualquer URL http(s) permanece em balão único (nunca fatiada no meio).
        `max_baloes`: teto de sub-mensagens por um único Acao tipo text (antes truncava em 6).
        """
        def _emoji_ou_pontuacao_somente(s: str) -> bool:
            t = str(s or "").strip()
            if not t:
                return False
            # Somente símbolos/emoji/pontuação (sem letras/dígitos) -> não enviar como balão isolado.
            return re.fullmatch(r"[\W_]+", t, flags=re.UNICODE) is not None

        bruto = str(texto or "").strip()
        # URL pura deve ir em balão único (evita quebrar "https://www.instagram.com/...").
        if re.match(r"^https?://\S+$", bruto, re.I):
            return [self._limpar_pontuacao_apos_url(bruto)]

        out: list[str] = []
        # Segmenta texto vs URLs: URLs nunca passam por fatiar_texto_ritmo_celular.
        for trecho in self._RE_URL_NO_TEXTO.split(bruto):
            t = (trecho or "").strip()
            if not t:
                continue
            if re.match(r"^https?://\S+", t, re.I):
                out.append(self._limpar_pontuacao_apos_url(t))
                continue
            base = self._quebrar_baloes(t)
            for parte in base:
                chunks = fatiar_texto_ritmo_celular(
                    parte,
                    max_linhas_visuais=MOBILE_MAX_LINHAS_BALO,
                    chars_por_linha=MOBILE_CHARS_POR_LINHA,
                )
                for ch in chunks:
                    out.extend(quebrar_por_linhas_max(ch, MOBILE_MAX_LINHAS_BALO))
        limpos = [str(x or "").strip() for x in out if str(x or "").strip()]

        # Regra UX: emoji isolado deve ficar junto do balão anterior.
        merged: list[str] = []
        for p in limpos:
            if _emoji_ou_pontuacao_somente(p) and merged:
                merged[-1] = f"{merged[-1]} {p}".strip()
            else:
                merged.append(p)

        return merged[:max_baloes]

    @staticmethod
    def _normalizar_para_dedup(txt: str) -> str:
        s = (txt or "").strip().lower()
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"[.!?…]+$", "", s).strip()
        return s

    @staticmethod
    def _lead_reportou_problema_entrega(texto: str) -> bool:
        return lead_reportou_problema_entrega(texto)

    @staticmethod
    def _acoes_reparo_entrega(nome_vocativo: str) -> list[Acao]:
        return acoes_reparo_entrega_padrao(nome_vocativo)

    @staticmethod
    def _ultima_fala_do_bot_e_pergunta(acoes: list[Acao]) -> bool:
        """
        Detecta se a última fala textual/áudio do bloco termina em pergunta.
        Regra prática: se terminou com '?', deve pausar e esperar o lead.
        """
        for acao in reversed(acoes or []):
            if acao.tipo == "text":
                t = (acao.conteudo or "").strip()
                if t:
                    return t.endswith("?")
            if acao.tipo == "tts":
                t = (acao.tts_template or "").strip()
                if t:
                    return t.endswith("?")
        return False

    @staticmethod
    def _resumo_acoes_turno(acoes: list[Acao]) -> dict:
        resumo = {
            "total": 0,
            "textos": 0,
            "delays": 0,
            "midias": 0,
            "audios_tts": 0,
            "vcards": 0,
            "delay_total_s": 0,
        }
        for acao in acoes or []:
            tipo = str(getattr(acao, "tipo", "") or "").strip().lower()
            if not tipo:
                continue
            resumo["total"] += 1
            if tipo == "text":
                resumo["textos"] += 1
            elif tipo == "delay":
                resumo["delays"] += 1
                resumo["delay_total_s"] += int(getattr(acao, "segundos", 0) or 0)
            elif tipo in {"image", "video"}:
                resumo["midias"] += 1
            elif tipo in {"audio", "tts"}:
                resumo["audios_tts"] += 1
            elif tipo == "vcard":
                resumo["vcards"] += 1
        return resumo

    def _registrar_evento_comportamental(
        self,
        db,
        lead: Lead,
        *,
        event_type: str,
        ctx: ContextoConversa,
        payload: Optional[dict] = None,
    ) -> None:
        """
        Captura passiva para treino offline da IA de atendimento.
        Não faz commit isolado para não interferir no fluxo estático.
        """
        try:
            db.add(
                LeadBehaviorEvent(
                    lead_id=int(getattr(lead, "id", 0) or 0),
                    tenant_id=str(getattr(lead, "tenant_id", None) or getattr(self, "tenant_id", "default")),
                    event_type=str(event_type or "unknown")[:64],
                    node_atual=str(getattr(ctx, "node_atual", "") or "")[:100],
                    payload=dict(payload or {}),
                )
            )
        except Exception as e:
            logger.warning("⚠️ [BEHAVIOR] Falha ao registrar evento comportamental: %s", e)

    @staticmethod
    def _dedup_db_desligado_para_node(node: str) -> bool:
        """
        Estados silenciosos costumam reutilizar o mesmo ack fixo; dedup curto (90s) suprimia
        a resposta quando o lead mandava outra mensagem logo em seguida (ex.: link errado).
        """
        n = (node or "").strip().lower()
        return n in Engine._ESTADOS_SILENCIOSOS

    def _deve_suprimir_balao_repetido(self, db, lead_id: int, texto: str) -> bool:
        """
        Anti-echo **curto**: suprime balão idêntico ao que o bot já mandou há poucos segundos
        (retry, webhook duplicado, mesma execução reentrando).

        Janela longa (ex.: 25 min) quebrava nodes como a coleta: o modelo reutiliza aberturas
        (“Eu li o que você mandou…”) em turnos diferentes; o lead precisa ver a resposta
        do turno atual, não um silêncio por “eco” de minutos atrás.
        """
        alvo = self._normalizar_para_dedup(texto)
        if not alvo or len(alvo) < 10:
            return False
        janela = datetime.now(timezone.utc) - timedelta(seconds=45)
        recentes = (
            db.query(Mensagem)
            .filter(
                Mensagem.lead_id == lead_id,
                Mensagem.remetente == "bot",
                Mensagem.tipo == "text",
                Mensagem.timestamp >= janela,
            )
            .order_by(Mensagem.timestamp.desc())
            .limit(10)
            .all()
        )
        for m in recentes:
            atual = self._normalizar_para_dedup(getattr(m, "texto", "") or "")
            if atual == alvo:
                return True
        return False

    def _blindar_texto_final_anti_corte(self, texto: str) -> str:
        """
        Última barreira global contra mensagem cortada.
        1) tenta recuperar final truncado;
        2) se ainda parecer "aberto" ou começar em fragmento, não envia.
        """
        t = (texto or "").strip()
        if not t:
            return ""
        if re.match(r"^https?://\S+$", t, re.I):
            return t
        t2 = tentar_salvar_balao_ia_cortado(t, BALAO_IA_REGEX_CORTE_FINAL).strip()
        t2 = normalizar_enxerto_dor_sem_contexto(t2)
        # Se ainda termina em conectivo/pontuação aberta, suprime.
        if re.search(BALAO_IA_REGEX_CORTE_FINAL, t2.lower()):
            return ""
        # Suprime fragmento curto / início claramente truncado (ex.: "za sua;…" sobrou após corte).
        if len(t2) < 10:
            return ""
        primeiro_tok = t2.split()[0] if t2.split() else ""
        if primeiro_tok and len(primeiro_tok) <= 3 and primeiro_tok[0].islower() and primeiro_tok.isalpha():
            return ""
        return t2

    # ══════════════════════════════════════════════════════════════════
    # ROTEAMENTO E WHATSAPP API
    # ══════════════════════════════════════════════════════════════════

    _ESTADOS_SILENCIOSOS = frozenset(
        {
            "aguardando_pagamento",
            "aguardando_pagamento_servico",
            "aguardando_pagamento_downsell",
            "aguardando_dados_altar",
            "fluxo_encerrado",
            "14_confirmacao_entrega",
            "static_meumisterio_b7",
        }
    )
    _META_KEYS_EXCLUIR_PERSISTENCIA = frozenset(
        {
            "__config__",
            "__meumisterio_studio__",
            "node_atual_exec",
            "node5_ignorar_ruido_um_turno",
            "node6_fallback_acionado_turno",
            "node7_fallback_acionado_turno",
            "node8_fallback_acionado_turno",
        }
    )

    def _ack_estado_silencioso(self, node: str) -> str:
        n = (node or "").strip().lower()
        if n == "aguardando_pagamento":
            return (
                "Recebi aqui, meu bem. Se for sobre o pagamento, o link ou qualquer dúvida nessa hora, "
                "me fala em uma frase que eu te ajudo. ✨"
            )
        if n in ("aguardando_pagamento_servico", "aguardando_pagamento_downsell"):
            return (
                "Recebi aqui. Se for comprovante, dúvida no link ou a segunda parte da troca, "
                "me escreve em uma frase que eu alinho contigo. ✨"
            )
        if n == "aguardando_dados_altar":
            return (
                "Recebi sua mensagem. Se for nome completo, data ou outro dado para o altar, "
                "pode mandar com calma que eu registro tudo por aqui. 🔮"
            )
        if n == "14_confirmacao_entrega":
            return (
                "Recebi sua mensagem. Se for sobre a entrega ou o material, me conta com calma que eu alinho por aqui. 🔮"
            )
        if n == "static_meumisterio_b7":
            return (
                "Recebi sua mensagem. Se forem nomes, fotos ou dúvidas sobre o trabalho, pode mandar com calma que eu vejo por aqui. 🔮"
            )
        # fluxo_encerrado
        return (
            "Teu contato chegou aqui. Se precisar retomar depois, manda um oi quando quiser. 🌙"
        )

    @staticmethod
    def _vocativo_curto_lead(lead, ctx: ContextoConversa) -> str:
        for src in ((getattr(lead, "nome", None) or ""), (getattr(ctx, "nome_lead", None) or "")):
            s = (src or "").strip()
            if s and not nome_eh_placeholder(s):
                return s.split()[0].strip().capitalize()
        return VOCATIVO_SEM_NOME

    @classmethod
    def _metadata_persistivel(cls, meta: dict) -> dict:
        out: dict = {}
        for k, v in (meta or {}).items():
            ks = str(k or "")
            if not ks:
                continue
            if ks in cls._META_KEYS_EXCLUIR_PERSISTENCIA:
                continue
            if ks.endswith("_turno") or ks.endswith("_temp"):
                continue
            out[ks] = v
        return out

    @staticmethod
    def _lead_ja_passou_funil_ou_comprou(lead) -> bool:
        if bool(getattr(lead, "convertido", False)):
            return True
        if str(getattr(lead, "produto_comprado", "") or "").strip():
            return True
        meta = getattr(lead, "metadata_json", None) or {}
        if not isinstance(meta, dict):
            return False
        return bool(
            meta.get("ja_passou_funil")
            or meta.get("cliente_existente")
            or meta.get("atendimento_pos_funil")
            or meta.get("ja_recebeu_atendimento")
            or meta.get("departamento_humano_ativo")
        )

    def _apply_published_flow_effects(
        self,
        db,
        lead: Lead,
        ctx: ContextoConversa,
        effects: list[dict],
    ) -> None:
        """Aplica no lead as ações internas configuradas no bloco Ação."""
        for effect in effects or []:
            if not isinstance(effect, dict):
                continue
            kind = str(effect.get("kind") or "").strip().lower()
            payload = str(effect.get("payload") or "").strip()
            if kind == "ab_exposure":
                try:
                    blueprint_id = int(effect.get("blueprint_id"))
                except (TypeError, ValueError):
                    blueprint_id = 0
                node_id = str(effect.get("node_id") or "").strip()[:200]
                variant = str(effect.get("variant") or "").strip().upper()[:1]
                if blueprint_id and node_id and variant:
                    exposure = (
                        db.query(ABTestExposure)
                        .filter_by(
                            tenant_id=str(getattr(lead, "tenant_id", None) or self.tenant_id or "default"),
                            blueprint_id=blueprint_id,
                            node_id=node_id,
                            lead_id=lead.id,
                        )
                        .first()
                    )
                    if exposure is None:
                        db.add(
                            ABTestExposure(
                                tenant_id=str(getattr(lead, "tenant_id", None) or self.tenant_id or "default"),
                                blueprint_id=blueprint_id,
                                node_id=node_id,
                                lead_id=lead.id,
                                variant=variant,
                                weight_a=int(effect.get("weight_a") or 0),
                                weight_b=int(effect.get("weight_b") or 0),
                            )
                        )
            elif kind in ("tag_add", "tag_remove"):
                tags = [str(tag) for tag in (getattr(lead, "tags", None) or []) if str(tag).strip()]
                if kind == "tag_add" and payload and payload not in tags:
                    tags.append(payload[:120])
                elif kind == "tag_remove" and payload:
                    tags = [tag for tag in tags if tag.casefold() != payload.casefold()]
                lead.tags = tags
            elif kind == "assign_user":
                ctx.metadata["assigned_user_id"] = payload or None
            elif kind == "unassign_user":
                ctx.metadata["assigned_user_id"] = None
            elif kind == "open_chat":
                lead.bot_pausado = False
                ctx.metadata["flow_chat_status"] = "open"
            elif kind == "close_chat":
                lead.bot_pausado = True
                ctx.metadata["flow_chat_status"] = "closed"
            elif kind == "update_contact":
                field_name = str(effect.get("target_field") or "").strip().lower()
                if field_name in ("name", "nome") and payload:
                    lead.nome = payload[:200]
                    ctx.nome_lead = lead.nome
                elif field_name in ("email", "e-mail") and payload:
                    lead.email = payload[:200]
                elif field_name in ("phone", "telefone", "whatsapp") and payload:
                    phone = re.sub(r"\D+", "", payload)[:20]
                    if len(phone) >= 7:
                        lead.telefone = phone
                        ctx.telefone = phone
                elif field_name and payload:
                    custom = dict(getattr(lead, "custom_fields", None) or {})
                    custom[field_name[:120]] = payload[:4000]
                    lead.custom_fields = custom
            elif kind == "start_flow":
                # O alvo fica registrado para o próximo despacho. A troca não
                # altera a publicação global do tenant.
                ctx.metadata["flow_requested_start"] = payload[:128]
            elif kind == "end_flow":
                ctx.metadata["flow_forced_end"] = True
            elif kind == "notify_attendant":
                lead.bot_pausado = True
                ctx.metadata["flow_chat_status"] = "waiting_attendant"
                attendant_id = str(effect.get("attendant_id") or "").strip()
                if attendant_id:
                    ctx.metadata["assigned_user_id"] = attendant_id

            if kind:
                db.add(
                    EventoAudit(
                        lead_id=lead.id,
                        evento="flow_builder_side_effect",
                        dados={
                            "kind": kind[:80],
                            "payload": payload[:240],
                            "blueprint_id": (ctx.metadata.get("flow_builder_runtime") or {}).get("blueprint_id"),
                        },
                    )
                )

    def _try_published_flow_turn(
        self,
        db,
        lead: Lead,
        ctx: ContextoConversa,
        *,
        event_type: str = "message",
        event_data: Optional[dict] = None,
    ) -> tuple[bool, list[Acao]]:
        """Tenta consumir a mensagem no blueprint publicado deste tenant."""
        if (
            event_type == "message"
            and str(getattr(lead, "node_atual", "") or "").startswith("static_meumisterio_")
        ):
            return False, []
        try:
            from flow_executor import flow_context_from_lead
            from published_flow_runtime import RUNTIME_STATE_KEY, execute_published_flow_turn

            tenant_id = str(getattr(lead, "tenant_id", None) or self.tenant_id or "default")
            published = db.query(FlowPublish).filter_by(tenant_id=tenant_id).first()
            if not published or not published.published_blueprint_id:
                return False, []
            blueprint = (
                db.query(FlowBlueprint)
                .filter_by(id=published.published_blueprint_id, tenant_id=tenant_id)
                .first()
            )
            if not blueprint or not isinstance(blueprint.body_json, dict):
                return False, []

            existing_state = ctx.metadata.get(RUNTIME_STATE_KEY)
            if not isinstance(existing_state, dict):
                existing_state = (getattr(lead, "metadata_json", None) or {}).get(RUNTIME_STATE_KEY)
            runtime_context = flow_context_from_lead(lead, tenant_id=tenant_id)
            runtime_context.update(ctx.metadata or {})
            runtime_context["chat.message"] = ctx.texto_recebido or ""
            runtime_context["texto_recebido"] = ctx.texto_recebido or ""
            if isinstance(event_data, dict):
                runtime_context["event"] = dict(event_data)
                runtime_context["event.platform"] = str(event_data.get("platform") or "")
                runtime_context["platform"] = str(event_data.get("platform") or "")
                for key, value in event_data.items():
                    runtime_context[f"event.{key}"] = value

            turn = execute_published_flow_turn(
                blueprint.body_json,
                blueprint_id=int(blueprint.id),
                tenant_id=tenant_id,
                lead_id=int(lead.id),
                message=ctx.texto_recebido or "",
                interactive_reply_id=ctx.interactive_reply_id,
                event_type=event_type,
                existing_state=(
                    existing_state
                    if event_type == "message" and isinstance(existing_state, dict)
                    else None
                ),
                context=runtime_context,
            )
            if not turn.handled:
                return False, []

            ctx.metadata[RUNTIME_STATE_KEY] = turn.state
            flow_vars = turn.state.get("vars") if isinstance(turn.state, dict) else {}
            if isinstance(flow_vars, dict):
                ctx.metadata.update(flow_vars)
            self._apply_published_flow_effects(db, lead, ctx, turn.side_effects)
            combined_actions = list(turn.actions)
            requested_flow = str(ctx.metadata.get("flow_requested_start") or "").strip()
            ctx.metadata["flow_requested_start"] = None
            started_blueprint_id = None
            if requested_flow:
                target_blueprint = None
                if requested_flow.isdigit():
                    target_blueprint = (
                        db.query(FlowBlueprint)
                        .filter_by(id=int(requested_flow), tenant_id=tenant_id)
                        .first()
                    )
                if target_blueprint is None:
                    target_blueprint = (
                        db.query(FlowBlueprint)
                        .filter_by(slug=requested_flow.lower(), tenant_id=tenant_id)
                        .first()
                    )
                if target_blueprint is not None and isinstance(target_blueprint.body_json, dict):
                    target_nodes = (
                        (target_blueprint.body_json.get("graph") or {}).get("nodes")
                        if isinstance(target_blueprint.body_json.get("graph"), dict)
                        else []
                    )
                    target_trigger = next(
                        (
                            str(node.get("id") or "").strip()
                            for node in (target_nodes or [])
                            if isinstance(node, dict)
                            and str(node.get("type") or "").lower() in ("trigger", "webhook")
                        ),
                        "",
                    )
                    if target_trigger:
                        forced_state = {
                            "version": 1,
                            "blueprint_id": int(target_blueprint.id),
                            "status": "running",
                            "current_node_id": target_trigger,
                            "waiting": None,
                            "vars": dict(flow_vars or {}),
                        }
                        next_turn = execute_published_flow_turn(
                            target_blueprint.body_json,
                            blueprint_id=int(target_blueprint.id),
                            tenant_id=tenant_id,
                            lead_id=int(lead.id),
                            message=ctx.texto_recebido or "",
                            interactive_reply_id=ctx.interactive_reply_id,
                            event_type="message",
                            existing_state=forced_state,
                            context=runtime_context,
                        )
                        if next_turn.handled:
                            started_blueprint_id = int(target_blueprint.id)
                            turn = next_turn
                            combined_actions.extend(next_turn.actions)
                            ctx.metadata[RUNTIME_STATE_KEY] = next_turn.state
                            next_vars = next_turn.state.get("vars") or {}
                            if isinstance(next_vars, dict):
                                ctx.metadata.update(next_vars)
                            self._apply_published_flow_effects(db, lead, ctx, next_turn.side_effects)
            db.add(
                EventoAudit(
                    lead_id=lead.id,
                    evento="flow_builder_turn",
                    dados={
                        "blueprint_id": int(blueprint.id),
                        "started_blueprint_id": started_blueprint_id,
                        "status": str(turn.state.get("status") or ""),
                        "actions": len(turn.actions),
                        "trace": turn.trace[:80],
                    },
                )
            )
            return True, combined_actions
        except Exception as exc:
            logger.exception("event=flow_builder_turn_error lead=%s err=%s", getattr(lead, "id", None), exc)
            try:
                db.add(
                    EventoAudit(
                        lead_id=lead.id,
                        evento="flow_builder_turn_error",
                        dados={"error": str(exc)[:500]},
                    )
                )
            except Exception:
                pass
            return False, []

    def processar_evento_fluxo(
        self,
        lead_id: int,
        event_type: str,
        event_data: Optional[dict] = None,
        tenant_id: Optional[str] = None,
    ) -> dict:
        """Dispara o blueprint publicado a partir de compra/abandono do checkout."""
        db = SessionLocal()
        try:
            resolved_tenant_id = str(tenant_id or self.tenant_id or "default")
            lead = db.query(Lead).filter_by(id=int(lead_id), tenant_id=resolved_tenant_id).first()
            if not lead:
                return {"status": "lead_not_found"}
            ctx = ContextoConversa(
                lead_id=lead.id,
                telefone=lead.telefone,
                node_atual=lead.node_atual or "1_apresentacao",
                texto_recebido="",
                tipo_mensagem="event",
                historico=self._buscar_historico(db, lead.id, 20),
                nome_lead=lead.nome or "",
                personalizer=self.personalizer,
            )
            self._restaurar_memoria(lead, ctx)
            handled, actions = self._try_published_flow_turn(
                db,
                lead,
                ctx,
                event_type=str(event_type or ""),
                event_data=event_data or {},
            )
            if not handled:
                db.commit()
                return {"status": "ignored"}
            self._persistir_memoria(db, lead, ctx)
            threading.Thread(
                target=self._processar_fila,
                args=(lead.id, ctx, actions),
                daemon=True,
                name=f"flow-event-{str(event_type)[:24]}-{lead.id}",
            ).start()
            return {"status": "queued", "actions": len(actions)}
        except Exception as exc:
            db.rollback()
            logger.exception(
                "event=flow_builder_external_event_error lead=%s type=%s err=%s",
                lead_id,
                event_type,
                exc,
            )
            return {"status": "error", "error": str(exc)}
        finally:
            db.close()

    def _rotear_state_machine(self, db, lead, ctx: ContextoConversa) -> list[Acao]:
        if self._lead_reportou_problema_entrega(ctx.texto_recebido or ""):
            try:
                db.add(
                    EventoAudit(
                        lead_id=lead.id,
                        evento="lead_reportou_problema_entrega",
                        dados={
                            "node": str(getattr(ctx, "node_atual", "") or ""),
                            "texto_preview": str(ctx.texto_recebido or "")[:220],
                        },
                    )
                )
                db.commit()
            except Exception as e:
                db.rollback()
                logger.warning("⚠️ [AUDIT] problema_entrega audit: %s", e)
            return self._acoes_reparo_entrega(self._vocativo_curto_lead(lead, ctx))

        if ctx.node_atual in self._ESTADOS_SILENCIOSOS:
            if (ctx.texto_recebido or "").strip():
                try:
                    registrar_silent_ack(
                        db,
                        lead.id,
                        ctx.node_atual,
                        intencao=getattr(ctx, "intencao", None),
                        sentimento=getattr(ctx, "sentimento", None),
                        texto_recebido=ctx.texto_recebido or "",
                    )
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.warning("⚠️ [AUDIT] silent_ack: %s", e)

                from flows.fase_3_oferta.suporte_pagamento_silencioso import (
                    link_efetivo_para_node,
                    montar_acoes_suporte_checkout,
                    node_e_checkout_silencioso,
                    texto_pedido_ajuda_checkout,
                )

                if node_e_checkout_silencioso(ctx.node_atual) and texto_pedido_ajuda_checkout(
                    ctx.texto_recebido or ""
                ):
                    cfg = ctx.metadata.get("__config__") or CONFIG_CLIENTE
                    lk = link_efetivo_para_node(
                        ctx.node_atual, cfg, getattr(ctx, "metadata", None) or {}
                    )
                    logger.info(
                        "event=suporte_checkout_silencioso lead_id=%s node=%s",
                        lead.id,
                        ctx.node_atual,
                    )
                    return montar_acoes_suporte_checkout(
                        nome_vocativo=self._vocativo_curto_lead(lead, ctx),
                        link=lk,
                        node_atual=ctx.node_atual,
                    )

                return [Acao(tipo="text", conteudo=self._ack_estado_silencioso(ctx.node_atual))]
            return []
        return self._executar_node(ctx.node_atual, ctx, db, lead)

    def _executar_node(self, node_id: str, ctx: ContextoConversa, db, lead) -> list[Acao]:
        """
        Executa o módulo do node. Encadeia na mesma requisição para `4_instagram` e `6_atencao_dinamica`
        (regras distintas dentro do loop), para o lead não ficar sem mensagens até o próximo envio.
        """
        acum: list[Acao] = []
        current_id = node_id
        for depth in range(6):
            modulo = self._mod_cache.get(current_id)
            if not modulo:
                logger.error(f"🚨 [ENGINE] Módulo não encontrado: node_{current_id}")
                return acum or [Acao(tipo="text", conteudo="🔮 Senti uma oscilação... manda um 'Oi' novamente.")]

            try:
                t0_node = time.time()
                if not getattr(ctx, "metadata", None):
                    ctx.metadata = {}
                ctx.metadata["node_atual_exec"] = current_id
                res, prox = modulo.executar_v2(ctx)
                elapsed_node = time.time() - t0_node
                cfg = (ctx.metadata.get("__config__", {}) or {})
                sla_warn_s = float(cfg.get("node_exec_sla_warn_seconds", 3.5) or 3.5)
                # Nodes narrativos (leitura/oferta) são naturalmente mais longos; evita falso alerta.
                sla_warn_por_node = {
                    "6_atencao_dinamica": float(cfg.get("node6_exec_sla_warn_seconds", 18) or 18),
                    "7_interesse_desejo": float(cfg.get("node7_exec_sla_warn_seconds", 18) or 18),
                    "8_oferta_principal": float(cfg.get("node8_exec_sla_warn_seconds", 15) or 15),
                }
                sla_warn_s = float(sla_warn_por_node.get(current_id, sla_warn_s))
                cap_por_node = {
                    "6_atencao_dinamica": int(cfg.get("node6_max_acoes", 44) or 44),
                    "7_interesse_desejo": int(cfg.get("node7_max_acoes", 30) or 30),
                    "8_oferta_principal": int(cfg.get("node8_max_acoes", 36) or 36),
                }
                cap_raw = int(cap_por_node.get(current_id, 0) or 0)
                cap = max(1, cap_raw) if cap_raw > 0 else 0
                if cap > 0 and len(res or []) > cap:
                    res = list((res or [])[:cap])
                    while res and getattr(res[-1], "tipo", "") == "delay":
                        res.pop()
                    logger.warning(
                        "event=node_action_cap_applied lead_id=%s node=%s cap=%s",
                        lead.id,
                        current_id,
                        cap,
                    )
                logger.info(
                    "event=node_exec_timing lead_id=%s node=%s elapsed_s=%.3f acoes=%s prox=%s",
                    lead.id,
                    current_id,
                    elapsed_node,
                    len(res or []),
                    prox,
                )
                resumo_turno = self._resumo_acoes_turno(list(res or []))
                logger.info(
                    "event=node_turn_telemetry lead_id=%s node=%s total=%s textos=%s delays=%s delay_total_s=%s midias=%s audios_tts=%s vcards=%s pergunta_final=%s",
                    lead.id,
                    current_id,
                    resumo_turno["total"],
                    resumo_turno["textos"],
                    resumo_turno["delays"],
                    resumo_turno["delay_total_s"],
                    resumo_turno["midias"],
                    resumo_turno["audios_tts"],
                    resumo_turno["vcards"],
                    self._ultima_fala_do_bot_e_pergunta(list(res or [])),
                )
                if elapsed_node > sla_warn_s:
                    logger.warning(
                        "⏱️ [ENGINE] Node lento: node=%s lead_id=%s elapsed_s=%.3f (sla_warn=%.2f)",
                        current_id,
                        lead.id,
                        elapsed_node,
                        sla_warn_s,
                    )
                acum.extend(res or [])
            except Exception as e:
                logger.error(f"🚨 [ENGINE] Erro ao executar node_{current_id}: {e}", exc_info=True)
                db.rollback()
                return acum

            if not prox:
                break

            node_antes = lead.node_atual
            lead.node_atual = prox
            ctx.node_atual = prox
            # Funnel analytics (Frente 3.26)
            try:
                import funnel_analytics
                funnel_analytics.record_node_entry(
                    lead_id=lead.id,
                    tenant_id=lead.tenant_id or "default",
                    node_id=prox,
                    flow_slug=getattr(ctx, "flow_slug", None),
                    db_session=db,
                )
            except Exception as exc:
                logger.debug("[funnel] record_entry falhou: %s", exc)
            try:
                registrar_node_transition(
                    db,
                    lead.id,
                    node_antes,
                    prox,
                    intencao=getattr(ctx, "intencao", None),
                    sentimento=getattr(ctx, "sentimento", None),
                    tipo_mensagem=getattr(ctx, "tipo_mensagem", None) or "text",
                    texto_recebido=getattr(ctx, "texto_recebido", None) or "",
                    origem="engine",
                )
            except Exception as e:
                logger.warning("⚠️ [AUDIT] node_transition: %s", e)
            db.commit()

            # Encadeamento no mesmo webhook (senão o lead muda de nó na DB mas não recebe mensagens até o próximo envio dele).
            # - 3_coleta_profunda: ao sair do Node 2 (novo padrão sem pergunta de confirmação no Node 2).
            # - 4_instagram: só ao sair do Node 3 (o próprio Node 4 também devolve prox=4_instagram — não repetir).
            # - 6_atencao_dinamica: só se a última fala não for pergunta (pausa natural antes da leitura longa).
            if prox == "3_coleta_profunda" and current_id == "2_salvar_contato":
                logger.info(
                    "🔗 [ENGINE] Encadeando 3_coleta_profunda na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            if prox == "4_instagram" and current_id == "3_coleta_profunda":
                logger.info(
                    "🔗 [ENGINE] Encadeando 4_instagram na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            if prox == "5_processa_leitura" and current_id == "4_instagram":
                logger.info(
                    "🔗 [ENGINE] Encadeando 5_processa_leitura na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            # Funil estático Meu Mistério: resposta ao bloco 1 → bloco 2 na mesma requisição
            if prox == "static_meumisterio_b2" and current_id == "static_meumisterio_b1":
                logger.info(
                    "🔗 [ENGINE] Encadeando static_meumisterio_b2 na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            if prox == "static_meumisterio_b3" and current_id == "static_meumisterio_b2":
                logger.info(
                    "🔗 [ENGINE] Encadeando static_meumisterio_b3 na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            if prox == "static_meumisterio_b4" and current_id == "static_meumisterio_b3":
                logger.info(
                    "🔗 [ENGINE] Encadeando static_meumisterio_b4 na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            if prox == "static_meumisterio_b5" and current_id == "static_meumisterio_b4":
                logger.info(
                    "🔗 [ENGINE] Encadeando static_meumisterio_b5 na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            if prox == "static_meumisterio_b6" and current_id == "static_meumisterio_b5":
                logger.info(
                    "🔗 [ENGINE] Encadeando static_meumisterio_b6 na mesma requisição (depth=%s) lead_id=%s",
                    depth,
                    lead.id,
                )
                current_id = prox
                continue
            if prox != "6_atencao_dinamica":
                break
            if self._ultima_fala_do_bot_e_pergunta(res or []):
                logger.info(
                    "⏸️ [ENGINE] Pausa de interação: última fala é pergunta. lead_id=%s node=%s",
                    lead.id,
                    current_id,
                )
                break
            logger.info(
                "🔗 [ENGINE] Encadeando Node 6 na mesma requisição (depth=%s) lead_id=%s",
                depth,
                lead.id,
            )
            current_id = prox

        return acum

    def _enviar_typing_indicator(self, telefone: str, kind: str) -> bool:
        """Indicador 'digitando' ou 'gravando áudio' (Cloud API `typing`)."""
        if str(telefone or "").startswith(("web_", "tg_")):
            return True
        if not self._circuit.pode_tentar():
            return False
        k = (kind or "text").strip().lower()
        if k not in ("text", "audio"):
            k = "text"
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": telefone,
                "type": "typing",
                "typing": {"type": k},
            }
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json",
            }
            r = requests.post(self.wa_url, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                self._circuit.registrar_sucesso()
                return True
            if k == "audio" and r.status_code in (400, 403, 404):
                payload["typing"] = {"type": "text"}
                r2 = requests.post(self.wa_url, json=payload, headers=headers, timeout=15)
                if r2.status_code == 200:
                    self._circuit.registrar_sucesso()
                    logger.info("event=wa_typing_audio_fallback_text ok")
                    return True
            logger.warning(
                "event=wa_typing_fail status=%s kind=%s body=%s",
                r.status_code,
                k,
                (r.text or "")[:220],
            )
            self._circuit.registrar_falha()
        except Exception as e:
            logger.warning("event=wa_typing_exception kind=%s err=%s", k, e)
        return False

    def _enviar_com_retry(
        self,
        telefone: str,
        tipo: str,
        conteudo: str,
        *,
        audio_voice: bool = False,
    ) -> bool:
        if str(telefone or "").startswith(("web_", "tg_")):
            return True
        if not self._circuit.pode_tentar():
            return False

        for tentativa in range(MAX_RETRY):
            try:
                payload = {"messaging_product": "whatsapp", "to": telefone}

                if tipo == "text":
                    payload.update({
                        "type": "text",
                        "text": {
                            "body": conteudo,
                            "preview_url": preview_url_flag_para_whatsapp(conteudo),
                        },
                    })

                elif tipo == "vcard":
                    num_limpo = "".join(filter(str.isdigit, conteudo.strip()))
                    num_e164  = f"+{num_limpo}" if num_limpo and not conteudo.startswith("+") else conteudo.strip()

                    contato = {
                        "name": {"first_name": "Esmeralda", "formatted_name": "Meu Mistério Esmeralda"},
                        "phones": [{"phone": num_e164, "wa_id": num_limpo, "type": "WORK"}] if num_limpo else []
                    }
                    payload.update({"type": "contacts", "contacts": [contato]})

                elif tipo == "audio":
                    media_link = str(conteudo or "").strip()
                    if media_link.startswith("/"):
                        public_base = str(os.getenv("PUBLIC_URL") or "").rstrip("/")
                        if not public_base:
                            logger.error("[WA] PUBLIC_URL ausente para mídia local: %s", media_link[:160])
                            return False
                        media_link = f"{public_base}{media_link}"
                    audio_obj: dict = {"link": media_link}
                    if audio_voice:
                        audio_obj["voice"] = True
                    payload.update({"type": "audio", "audio": audio_obj})
                else:
                    media_link = str(conteudo or "").strip()
                    if media_link.startswith("/"):
                        public_base = str(os.getenv("PUBLIC_URL") or "").rstrip("/")
                        if not public_base:
                            logger.error("[WA] PUBLIC_URL ausente para mídia local: %s", media_link[:160])
                            return False
                        media_link = f"{public_base}{media_link}"
                    payload.update({"type": tipo, tipo: {"link": media_link}})

                headers = {
                    "Authorization": f"Bearer {self.whatsapp_token}",
                    "Content-Type":  "application/json",
                }

                r = requests.post(self.wa_url, json=payload, headers=headers, timeout=15)

                if r.status_code == 200:
                    self._circuit.registrar_sucesso()
                    return True

                self._circuit.registrar_falha()
                time.sleep(2 ** tentativa)

            except Exception as e:
                logger.warning("⚠️ [WA] Exceção ao enviar %s para %s (tentativa %s): %s", tipo, telefone, tentativa + 1, e)
                self._circuit.registrar_falha()

        return False

    def enviar_template_hsm(
        self,
        telefone: str,
        template_name: str,
        language_code: str = "pt_BR",
        body_parameters: Optional[List[str]] = None,
    ) -> bool:
        """Envia template (HSM) aprovado pela Meta — típico fora da janela de 24h."""
        if not self._circuit.pode_tentar():
            return False
        body_parameters = body_parameters or []
        name = (template_name or "").strip()
        if not name:
            return False
        lang = (language_code or "pt_BR").strip() or "pt_BR"
        tpl: dict = {
            "name": name,
            "language": {"code": lang},
        }
        if body_parameters:
            tpl["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)[:4000]}
                        for p in body_parameters
                    ],
                }
            ]
        payload = {
            "messaging_product": "whatsapp",
            "to": telefone,
            "type": "template",
            "template": tpl,
        }
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json",
        }
        for tentativa in range(MAX_RETRY):
            try:
                r = requests.post(self.wa_url, json=payload, headers=headers, timeout=25)
                if r.status_code == 200:
                    self._circuit.registrar_sucesso()
                    return True
                logger.warning(
                    "event=wa_template_fail status=%s body=%s template=%s",
                    r.status_code,
                    (r.text or "")[:800],
                    name,
                )
                self._circuit.registrar_falha()
                time.sleep(2 ** tentativa)
            except Exception as e:
                logger.error("event=wa_template_exc err=%s", e)
                self._circuit.registrar_falha()
        return False

    # ══════════════════════════════════════════════════════════════════
    # MEMÓRIA PERSISTENTE E DB UTILS
    # ══════════════════════════════════════════════════════════════════

    def _restaurar_memoria(self, lead, ctx: ContextoConversa):
        meta_json = getattr(lead, "metadata_json", None)
        if meta_json:
            try:
                if isinstance(meta_json, dict):
                    lead_meta = dict(meta_json)
                else:
                    lead_meta = json.loads(meta_json)
                ctx.estado_coleta = lead_meta.pop("estado_coleta", ctx.estado_coleta or "inicial")
                for k, v in lead_meta.items():
                    if k not in ctx.metadata and k not in ("__config__", "__meumisterio_studio__"):
                        ctx.metadata[k] = v
            except (json.JSONDecodeError, TypeError):
                ctx.estado_coleta = getattr(lead, "estado_coleta", None) or "inicial"
        else:
            ctx.estado_coleta = getattr(lead, "estado_coleta", None) or "inicial"
        # Seed signo from DB column when metadata_json doesn't have it (birthdate extractor path)
        if not ctx.metadata.get("signo"):
            _signo_col = getattr(lead, "signo", None)
            if _signo_col:
                ctx.metadata["signo"] = str(_signo_col)[:20]

    def _persistir_memoria(self, db, lead, ctx: ContextoConversa):
        lead_id = int(getattr(lead, "id", 0) or 0)
        if lead_id <= 0:
            return

        def _build_patch(lead_row: Lead):
            patch: dict = {}
            if hasattr(ctx, "estado_coleta"):
                patch[Lead.estado_coleta] = ctx.estado_coleta
                ctx.metadata["estado_coleta"] = ctx.estado_coleta

            if ctx.nome_lead and getattr(lead_row, "nome", "") != ctx.nome_lead:
                patch[Lead.nome] = ctx.nome_lead

            m = ctx.metadata or {}
            if m.get("resumo_dor"):
                patch[Lead.resumo_dor] = str(m["resumo_dor"])[:8000]
            if m.get("objecao_silenciosa"):
                patch[Lead.objecao_silenciosa] = str(m["objecao_silenciosa"])[:4000]
            if m.get("nome_mecanismo"):
                patch[Lead.nome_mecanismo] = str(m["nome_mecanismo"])[:200]
            if m.get("genero_lead"):
                patch[Lead.genero] = str(m["genero_lead"])[:24]
            if m.get("signo") and not getattr(lead_row, "signo", None):
                patch[Lead.signo] = str(m["signo"])[:20]

            if ctx.metadata:
                existente = self._meta_as_dict(getattr(lead_row, "metadata_json", None))
                combinado = merge_metadata_for_persist(existente, dict(ctx.metadata))
                patch[Lead.metadata_json] = self._metadata_persistivel(combinado)

            if getattr(ctx, "intencao", None):
                patch[Lead.ultima_intencao] = str(ctx.intencao)[:50]
            if getattr(ctx, "sentimento", None):
                patch[Lead.ultimo_sentimento] = str(ctx.sentimento)[:50]

            return patch if patch else None

        ok = atomic_update_lead_columns(db, lead_id, _build_patch, max_retries=6)
        if ok:
            return

        logger.warning("event=persistir_memoria_fallback_atomic lead_id=%s", lead_id)
        try:
            db.add(
                EventoAudit(
                    lead_id=lead_id,
                    evento="lead_metadata_atomic_fallback",
                    dados={"where": "persistir_memoria"},
                )
            )
        except Exception:
            pass

        if hasattr(ctx, "estado_coleta"):
            lead.estado_coleta = ctx.estado_coleta
            ctx.metadata["estado_coleta"] = ctx.estado_coleta
        if ctx.nome_lead and getattr(lead, "nome", "") != ctx.nome_lead:
            lead.nome = ctx.nome_lead
        if ctx.metadata:
            m = ctx.metadata
            if m.get("resumo_dor"):
                lead.resumo_dor = str(m["resumo_dor"])[:8000]
            if m.get("objecao_silenciosa"):
                lead.objecao_silenciosa = str(m["objecao_silenciosa"])[:4000]
            if m.get("nome_mecanismo"):
                lead.nome_mecanismo = str(m["nome_mecanismo"])[:200]
            if m.get("genero_lead"):
                lead.genero = str(m["genero_lead"])[:24]
            if m.get("signo") and not getattr(lead, "signo", None):
                lead.signo = str(m["signo"])[:20]
            existente = self._meta_as_dict(getattr(lead, "metadata_json", None))
            combinado = merge_metadata_for_persist(existente, dict(ctx.metadata))
            lead.metadata_json = self._metadata_persistivel(combinado)
        if getattr(ctx, "intencao", None):
            lead.ultima_intencao = str(ctx.intencao)[:50]
        if getattr(ctx, "sentimento", None):
            lead.ultimo_sentimento = str(ctx.sentimento)[:50]
        db.commit()

    def _obter_ou_criar_lead(self, db, telefone: str) -> Lead:
        tid = getattr(self, "tenant_id", None) or "default"
        lead = db.query(Lead).filter_by(telefone=telefone, tenant_id=tid).first()
        if not lead:
            # Quota check: leads_month (Frente 2.4)
            # Política: NÃO bloquear (perde venda). Consome quota e marca
            # quota_exceeded=True em metadata se passou. UI avisa user.
            try:
                import quota
                allowed, current, limit = quota.consume_quota(tid, "leads_month", 1, db_session=db)
                if not allowed:
                    logger.warning(
                        "[quota.leads.exceeded] tenant=%s current=%s limit=%s — capturando lead com flag",
                        tid, current, limit,
                    )
                    # Não bloqueia; lead é capturado mas marcado pra possível
                    # processamento diferido (quando user fizer upgrade).
            except Exception as exc:
                logger.warning("[quota.leads] check falhou (fail open): %s", exc)
            _validos = frozenset({"1_apresentacao", "static_meumisterio_b1"})
            _ini = ""
            try:
                from api.tenant_config import get_tenant_config
                _t_cfg = get_tenant_config(tid)
                _ini = (_t_cfg.get("funil_entrada_inicial") or "").strip()
            except Exception:
                pass
            if not _ini:
                _ini = (CONFIG_CLIENTE.get("funil_entrada_inicial") or "").strip()
            _node0 = _ini if _ini in _validos else "1_apresentacao"
            lead = Lead(
                telefone=telefone,
                tenant_id=tid,
                node_atual=_node0,
                estado_coleta="inicial",
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
        return lead

    def _salvar_mensagem(
        self,
        db,
        lead_id: int,
        remetente: str,
        texto: str,
        tipo: str = "text",
        *,
        media_url: Optional[str] = None,
        auto_commit: bool = True,
    ):
        try:
            # Captura wamid + status sent pra delivery tracking (Frente 4 ext)
            wamid = None
            delivery_status = None
            if remetente == "bot":
                try:
                    from api.whatsapp_providers.meta_cloud import pop_last_wamid
                    wamid = pop_last_wamid()
                    if wamid:
                        delivery_status = "sent"
                except Exception:
                    pass

            m = Mensagem(
                lead_id=lead_id,
                remetente=remetente,
                texto=texto,
                tipo=tipo,
                media_url=media_url,
                wamid=wamid,
                delivery_status=delivery_status,
                delivery_status_at=datetime.now(timezone.utc) if delivery_status else None,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(m)
            if auto_commit:
                db.commit()
                # Recalcula score do lead a cada msg salva (Frente 3.24)
                # Skip async: cron daily faz batch refresh.
                # Aqui só recalcula em msg inbound (user) — sinal forte.
                if remetente == "user":
                    try:
                        import lead_scoring
                        lead_scoring.update_lead_score(lead_id, db_session=db)
                    except Exception as exc:
                        logger.debug("[lead_scoring] update inline falhou: %s", exc)
        except Exception as e:
            db.rollback()
            logger.error(f"🚨 [DB] Falha ao salvar mensagem: {e}")

    def _buscar_historico(self, db, lead_id: int, limite: int) -> list:
        msgs = (
            db.query(Mensagem)
            .filter_by(lead_id=lead_id)
            .order_by(Mensagem.timestamp.desc())
            .limit(limite)
            .all()
        )
        return msgs[::-1]

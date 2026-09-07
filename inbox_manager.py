"""
inbox_manager.py — v2.0 Redis-Backed LeadInboxManager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fix F: Filas per-lead durável via Redis (RPUSH/LPOP) + DistributedLock.
Sobrevive a restarts, deploys e crashes. Escala horizontal com N workers.

Quando Redis não está disponível, faz fallback transparente para o modo
in-memory original (queue.Queue) — zero downtime.

Fluxo Redis:
  1. enqueue() → RPUSH meumisterio:inbox:{telefone} (durável)
  2. _spawn_drainer() → tenta DistributedLock(inbox:drain:{telefone})
     - Se NÃO conseguir → outro worker já drena, retorna (msg segura no Redis)
     - Se conseguir → entra no loop drainer
  3. drainer loop: LPOP → merge → silence poll → resolve_media → motor
  4. Quando a fila esvazia → release lock, thread morre
"""

import json as _json
import logging
import threading
import time
import queue
import re
import hashlib
import random
from collections import deque
from datetime import datetime, timezone

from config_cliente import CONFIG_CLIENTE
from db import models
from db.database import SessionLocal
from tenant_context import get_engine_tenant_id, tenant_override_ctx
from reliability.distributed_lock import DistributedLock, DistributedSemaphore

logger = logging.getLogger(__name__)

# ── Redis helpers ────────────────────────────────────────────────────
_INBOX_PREFIX = "meumisterio:inbox:"
_INBOX_TTL = 3600  # 1h — segurança: expira filas abandonadas


def _redis_client():
    """Retorna cliente Redis ou None."""
    try:
        from reliability.distributed_lock import _get_redis
        return _get_redis()
    except Exception:
        return None


def _lead_metadata_as_dict(metadata_json):
    if not metadata_json:
        return {}
    if isinstance(metadata_json, dict):
        return metadata_json
    if isinstance(metadata_json, str):
        try:
            return _json.loads(metadata_json)
        except Exception:
            return {}
    return {}


class LeadInboxManager:
    """
    Ordem cronológica + fusão de texto com filas Redis duráveis.
    Fallback transparente para in-memory se Redis indisponível.
    """
    def __init__(self, process_callback):
        # Fallback in-memory (quando Redis está off)
        self._mem_inboxes = {}
        self._mem_lock = threading.Lock()

        self._dedup_lock = threading.Lock()
        self._recent_fp_by_phone = {}
        # Tracks active drainer threads (prevents duplicate spawns per-process)
        self._active_drainers = set()
        self._drainer_guard = threading.Lock()

        # Config
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
        _max_conc = max(4, int(CONFIG_CLIENTE.get("inbox_max_concorrencia_processamento", 24) or 24))
        self._sem_processamento = DistributedSemaphore(
            "inbox:processing", max_concurrent=_max_conc,
        )
        self._re_confirmacao_curta = re.compile(
            r"\b(ok|sim|pronto|salvo|beleza|blz|show|feito|entendi|combinado)\b", re.I,
        )
        self._re_feedback_entrega = re.compile(
            r"\b(cortad[ao]|incomplet[ao]|atropel|card|cart[aã]o\s+de\s+contato|"
            r"n[aã]o\s+deu\s+tempo|n[aã]o\s+deu\s+pra\s+ver)\b", re.I,
        )
        self._re_intencao_midia = re.compile(
            r"\b(foto|imagem|palma|m[aã]o|mao|print|selfie|enviei\s+foto|mandei\s+foto)\b", re.I,
        )
        self.process_callback = process_callback

    # ── Helpers (unchanged) ──────────────────────────────────────────

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
                    telefone, "inbox_static_cooldown_skip",
                    {"node_atual": node, "delta_s": round(float(delta), 2),
                     "cooldown_s": round(float(self.static_block_cooldown_s), 2)},
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
                p["texto_recebido"] = f"{pt}. {et}".strip(" .") if pt else et
        if extra.get("imagem_url"):
            p["imagem_url"] = extra["imagem_url"]
            p["tipo_mensagem"] = "image"
        if extra.get("media_url"):
            p["media_url"] = extra["media_url"]
        if p.get("imagem_url") and p.get("tipo_mensagem") == "text":
            p["tipo_mensagem"] = "image"
        # Preservar flags de mídia pendente (Fix B) durante fusão
        for _mflag in ("_media_pending", "_media_caption", "_media_mime"):
            if extra.get(_mflag) is not None:
                p[_mflag] = extra[_mflag]
        return p

    def _deve_grace_midia_pos_texto(self, payload: dict) -> bool:
        if self.after_text_grace_s <= 0:
            return False
        if payload.get("imagem_url") or payload.get("media_url"):
            return False
        tipo = str(payload.get("tipo_mensagem") or "text").lower()
        if tipo in ("image", "video", "audio"):
            return False
        tx = str(payload.get("texto_recebido") or "").strip()
        if self._re_feedback_entrega.search(tx):
            return False
        palavras = tx.split()
        if len(palavras) <= 8 and self._re_confirmacao_curta.search(tx):
            return False
        if len(tx) < self.after_text_grace_min_chars:
            return False
        if not self._re_intencao_midia.search(tx):
            return False
        return True

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
            db.add(models.EventoAudit(lead_id=lead.id, evento=evento, dados=payload_audit))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def _auditar_batch_pronto(self, telefone: str, payload: dict) -> None:
        tx = str(payload.get("texto_recebido") or "").strip()
        partes = max(1, len([s for s in re.split(r"[.!?]\s+", tx) if s.strip()])) if tx else 1
        self._auditar_busy_por_telefone(
            telefone, "inbox_batch_pronto",
            {"silence_s": round(float(self.silence_s), 2),
             "after_text_grace_s": round(float(self.after_text_grace_s), 2)
             if payload.get("_inbox_after_text_grace") else 0.0,
             "chars": len(tx),
             "tipo_mensagem": str(payload.get("tipo_mensagem") or "text"),
             "partes_fundidas": partes},
        )

    # ── Redis Queue Operations ───────────────────────────────────────

    def _redis_enqueue(self, telefone: str, payload: dict) -> bool:
        """RPUSH payload serializado. Retorna True se gravou no Redis."""
        r = _redis_client()
        if not r:
            return False
        try:
            key = f"{_INBOX_PREFIX}{telefone}"
            data = _json.dumps(payload, ensure_ascii=False)
            pipe = r.pipeline(transaction=False)
            pipe.rpush(key, data)
            pipe.expire(key, _INBOX_TTL)
            pipe.execute()
            return True
        except Exception as exc:
            logger.warning("[FILA-REDIS] RPUSH falhou para %s: %s", telefone, exc)
            return False

    def _redis_lpop(self, telefone: str) -> dict | None:
        """LPOP e deserializa. None se vazia."""
        r = _redis_client()
        if not r:
            return None
        try:
            key = f"{_INBOX_PREFIX}{telefone}"
            raw = r.lpop(key)
            if raw is None:
                return None
            return _json.loads(raw)
        except Exception as exc:
            logger.warning("[FILA-REDIS] LPOP falhou para %s: %s", telefone, exc)
            return None

    def _redis_queue_len(self, telefone: str) -> int:
        r = _redis_client()
        if not r:
            return 0
        try:
            return int(r.llen(f"{_INBOX_PREFIX}{telefone}"))
        except Exception:
            return 0

    def _redis_drain_all(self, telefone: str) -> list[dict]:
        """Drena tudo da fila Redis de uma vez (LRANGE + DEL atômico via Lua)."""
        r = _redis_client()
        if not r:
            return []
        key = f"{_INBOX_PREFIX}{telefone}"
        lua = """
        local items = redis.call("LRANGE", KEYS[1], 0, -1)
        redis.call("DEL", KEYS[1])
        return items
        """
        try:
            raws = r.eval(lua, 1, key)
            if not raws:
                return []
            results = []
            for raw in raws:
                try:
                    results.append(_json.loads(raw))
                except Exception:
                    pass
            return results
        except Exception as exc:
            logger.warning("[FILA-REDIS] drain_all falhou para %s: %s", telefone, exc)
            return []

    # ── Enqueue (entry point) ────────────────────────────────────────

    def enqueue(self, telefone, payload):
        if self._is_recent_duplicate(telefone, payload):
            logger.info("♻️ [FILA] Duplicata recente suprimida para %s.", telefone)
            self._auditar_busy_por_telefone(
                telefone, "inbox_dedupe_suppressed",
                {"window_s": round(float(self.dedupe_window_s), 2)},
            )
            return

        # Tenta Redis primeiro (durável, cross-worker)
        if self._redis_enqueue(telefone, payload):
            logger.info("📥 [FILA-REDIS] Mensagem enfileirada para %s.", telefone)
            self._spawn_drainer(telefone)
            return

        # Fallback: in-memory (single-process)
        self._enqueue_memory(telefone, payload)

    def _enqueue_memory(self, telefone: str, payload: dict):
        """Fallback in-memory quando Redis não está disponível."""
        with self._mem_lock:
            if telefone not in self._mem_inboxes:
                self._mem_inboxes[telefone] = queue.Queue()
                threading.Thread(
                    target=self._worker_memory, args=(telefone,),
                    daemon=True, name=f"Worker-mem-{telefone[-4:]}",
                ).start()
        q = self._mem_inboxes[telefone]
        merged = dict(payload)
        if q.qsize() >= self.max_fila_por_lead:
            try:
                old = q.get_nowait()
                q.task_done()
                merged = self._merge_payload(old, merged)
            except Exception:
                pass
        q.put(merged)
        logger.info("📥 [FILA-MEM] Mensagem enfileirada para %s (fallback).", telefone)

    # ── Redis Drainer ────────────────────────────────────────────────

    def _spawn_drainer(self, telefone: str):
        """Spawna thread drainer se não há uma ativa neste processo."""
        with self._drainer_guard:
            if telefone in self._active_drainers:
                return  # Já tem um drainer ativo — a msg no Redis será puxada
            self._active_drainers.add(telefone)

        threading.Thread(
            target=self._drainer_redis, args=(telefone,),
            daemon=True, name=f"Drain-{telefone[-4:]}",
        ).start()

    def _drainer_redis(self, telefone: str):
        """
        Drainer Redis: adquire lock exclusivo per-lead, consome a fila,
        funde mensagens, espera silêncio, e despacha para o motor.
        """
        lock = DistributedLock(
            f"inbox:drain:{telefone}",
            ttl_ms=180_000,  # 3 min TTL (extend durante processamento)
        )
        try:
            acquired = lock.acquire(timeout=2.0)
            if not acquired:
                # Outro worker/processo já está drenando este lead.
                # A mensagem está segura no Redis e será processada.
                logger.debug("[DRAIN] Lock não adquirido para %s (outro drainer ativo).", telefone)
                return

            self._drain_loop(telefone, lock)
        except Exception as exc:
            logger.error("[DRAIN] Erro fatal para %s: %s", telefone, exc, exc_info=True)
        finally:
            lock.release()
            with self._drainer_guard:
                self._active_drainers.discard(telefone)

    def _drain_loop(self, telefone: str, lock: DistributedLock):
        """Loop principal do drainer: consome fila Redis até esvaziar."""
        while True:
            # 1. Drenar tudo disponível agora (rajada)
            items = self._redis_drain_all(telefone)
            if not items:
                # Fila vazia — missão cumprida
                return

            # Backpressure: se muitos itens, fundir os mais antigos
            while len(items) > self.max_fila_por_lead:
                old = items.pop(0)
                items[0] = self._merge_payload(old, items[0])

            # 2. Fundir todos os itens em um payload único
            payload = items[0]
            for extra in items[1:]:
                payload = self._merge_payload(payload, extra)

            # 3. Espera de silêncio (polling Redis por novas mensagens)
            payload = self._wait_silence_redis(telefone, payload)

            # 4. Grace mídia pós-texto
            if self._deve_grace_midia_pos_texto(payload):
                logger.info(
                    "⏳ [DRAIN] Grace pós-texto para %s: %.1fs", telefone, self.after_text_grace_s,
                )
                extra = self._wait_silence_redis(telefone, payload, timeout=self.after_text_grace_s)
                if extra is not payload:
                    payload = extra
                    payload["_inbox_after_text_grace"] = True

            # 5. Extend lock antes do processamento pesado
            lock.extend(extra_ms=120_000)

            # 6. Log batch
            tx = str(payload.get("texto_recebido") or "").strip()
            logger.info(
                "📦 [DRAIN] Batch pronto para %s (chars=%d, tipo=%s)",
                telefone, len(tx), payload.get("tipo_mensagem", "text"),
            )

            # 7. Processar
            if self._should_skip_static_cooldown(telefone, payload):
                continue

            self._process_payload(telefone, payload, lock)

            # 8. Checar se chegou mais durante o processamento
            remaining = self._redis_queue_len(telefone)
            if remaining == 0:
                return
            # Loop continua para drenar o restante

    def _wait_silence_redis(self, telefone: str, payload: dict, timeout: float | None = None) -> dict:
        """Espera silêncio (sem novas msgs) por N segundos, fundindo o que chegar."""
        wait = timeout if timeout is not None else self.silence_s
        if wait <= 0:
            return payload
        merged = dict(payload)
        deadline = time.time() + wait
        while time.time() < deadline:
            time.sleep(min(1.0, max(0.2, deadline - time.time())))
            items = self._redis_drain_all(telefone)
            if not items:
                continue
            # Novas mensagens chegaram — fundir e resetar deadline
            for extra in items:
                merged = self._merge_payload(merged, extra)
            deadline = time.time() + wait  # Reset silence timer
        return merged

    # ── Process Payload (shared between Redis and memory modes) ──────

    def _process_payload(self, telefone: str, payload: dict, lock: DistributedLock | None = None):
        """Adquire semáforo, resolve mídia, chama motor."""
        acquired = False
        try:
            acquired = self._sem_processamento.acquire(timeout=8)
            if not acquired:
                # Re-enqueue para retry
                retries = int(payload.get("_busy_retries", 0) or 0) + 1
                payload["_busy_retries"] = retries
                self._redis_enqueue(telefone, payload)
                self._auditar_busy_por_telefone(
                    telefone, "engine_capacity_requeued", {"tentativa": retries},
                )
                return

            motor_payload = dict(payload)
            motor_payload.pop("_inbox_after_text_grace", None)

            # Fix B: resolver mídia pendente no worker
            if motor_payload.get("_media_pending"):
                try:
                    from webhooks.media_resolver import resolve_pending_media
                    motor_payload = resolve_pending_media(motor_payload)
                except Exception as _media_exc:
                    logger.error("🚨 [MEDIA-RESOLVE] Falha para %s: %s", telefone, _media_exc, exc_info=True)
                    motor_payload.pop("_media_pending", None)

            # Extend lock durante processamento do motor
            if lock:
                lock.extend(extra_ms=120_000)

            _override_tenant = motor_payload.get("tenant_id")

            with tenant_override_ctx(_override_tenant):
                result = self.process_callback(**motor_payload) or {}

            if result.get("status") != "busy":
                self._auditar_batch_pronto(telefone, payload)
            if result.get("status") == "busy":
                retries = int(payload.get("_busy_retries", 0) or 0) + 1
                if retries <= self.max_busy_retries:
                    retry_payload = dict(payload)
                    retry_payload["_busy_retries"] = retries
                    wait_s = min(5.0, 1.5 * retries + random.uniform(0.2, 1.0))
                    logger.info(
                        "⏳ [FILA] Motor busy para %s; requeue tentativa=%s em %.1fs.",
                        telefone, retries, wait_s,
                    )
                    self._auditar_busy_por_telefone(
                        telefone, "engine_busy_requeued",
                        {"tentativa": retries, "espera_s": round(float(wait_s), 3)},
                    )
                    time.sleep(wait_s)
                    self._redis_enqueue(telefone, retry_payload)
                else:
                    logger.warning(
                        "⚠️ [FILA] Motor busy persistente para %s; descartando após %s tentativas.",
                        telefone, retries - 1,
                    )
                    self._auditar_busy_por_telefone(
                        telefone, "engine_busy_discarded",
                        {"tentativas": retries - 1,
                         "_texto_recebido_preview": payload.get("texto_recebido")},
                    )
        except Exception as e:
            logger.error("🚨 [ENGINE ERROR] Falha no processamento de %s: %s", telefone, e, exc_info=True)
        finally:
            if acquired:
                try:
                    self._sem_processamento.release()
                except Exception:
                    pass

    # ── Fallback: In-Memory Worker (identical to v1) ─────────────────

    def _worker_memory(self, telefone):
        """Worker in-memory para quando Redis não está disponível."""
        q = self._mem_inboxes[telefone]
        while True:
            try:
                payload = q.get(timeout=300)
                q.task_done()

                # Drenar rajada
                while True:
                    try:
                        extra = q.get_nowait()
                        payload = self._merge_payload(payload, extra)
                        q.task_done()
                    except queue.Empty:
                        break

                # Espera silêncio
                payload = self._wait_silence_memory(q, payload)

                # Grace mídia
                if self._deve_grace_midia_pos_texto(payload):
                    payload = self._wait_silence_memory(q, payload, timeout=self.after_text_grace_s)
                    payload["_inbox_after_text_grace"] = True

                if self._should_skip_static_cooldown(telefone, payload):
                    continue

                self._process_payload(telefone, payload)
            except queue.Empty:
                with self._mem_lock:
                    self._mem_inboxes.pop(telefone, None)
                logger.debug("💤 [FILA-MEM] Worker para %s encerrado por inatividade.", telefone)
                break

    def _wait_silence_memory(self, q: queue.Queue, payload: dict, timeout: float | None = None) -> dict:
        """Espera silêncio em modo in-memory."""
        wait = timeout if timeout is not None else self.silence_s
        if wait <= 0:
            return payload
        merged = dict(payload)
        while True:
            try:
                extra = q.get(timeout=wait)
                merged = self._merge_payload(merged, extra)
                q.task_done()
                # Drenar rajada imediata
                while True:
                    try:
                        extra2 = q.get_nowait()
                        merged = self._merge_payload(merged, extra2)
                        q.task_done()
                    except queue.Empty:
                        break
            except queue.Empty:
                break
        return merged

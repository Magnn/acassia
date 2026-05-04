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
from reliability.distributed_lock import DistributedSemaphore

logger = logging.getLogger(__name__)

def _lead_metadata_as_dict(metadata_json):
    if not metadata_json:
        return {}
    if isinstance(metadata_json, dict):
        return metadata_json
    import json
    if isinstance(metadata_json, str):
        try:
            return json.loads(metadata_json)
        except Exception:
            return {}
    return {}

class LeadInboxManager:
    """
    Ordem cronológica + fusão de texto.
    Fluxo: (1) funde rajada imediata na fila; (2) espera silêncio (sem novas mensagens) por
    inbox_silence_seconds; (3) só então processa um único batch — a IA vê o contexto completo antes de responder.
    """
    def __init__(self, process_callback):
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
        # Semáforo distribuído (Redis se disponível, fallback local).
        # Limita concurrência GLOBAL (cross-worker) de processamento.
        _max_conc = max(4, int(CONFIG_CLIENTE.get("inbox_max_concorrencia_processamento", 24) or 24))
        self._sem_processamento = DistributedSemaphore(
            "inbox:processing",
            max_concurrent=_max_conc,
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
        self.process_callback = process_callback

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
            return False
        palavras = tx.split()
        if len(palavras) <= 8 and self._re_confirmacao_curta.search(tx):
            return False
        if len(tx) < self.after_text_grace_min_chars:
            return False
        if not self._re_intencao_midia.search(tx):
            return False
        return True

    def _esperar_grace_midia_pos_texto(self, q, payload: dict, telefone: str) -> dict:
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
                payload = q.get(timeout=300)
                q.task_done()

                payload = self._drenar_rajada_imediata(q, payload)
                payload = self._esperar_silencio_do_lead(q, payload)
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

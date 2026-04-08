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
from db.models import Lead, Mensagem, EventoAudit
from ai.intent_classifier import IntentClassifier
from ai.context_compressor import ContextCompressor
from ai.sentiment_analyzer import SentimentAnalyzer
from ai.response_validator import ResponseValidator
from ai.recovery_engine import RecoveryEngine
from ai.stage_intelligence import enriquecer_contexto_stage
from analytics.funnel_audit import registrar_node_transition, registrar_silent_ack
from tts.audio_engine import AudioEngine
from config_cliente import CONFIG_CLIENTE
from flows.fase_1_saudacao.sniffer_fase1 import (
    concat_texto_usuario,
    promover_burst_fase1_meta,
    resolver_avanco_node_fase1,
    sniffer_instagram_meta,
)
from flows.funnel_gates import nome_eh_placeholder

# 🚨 IMPORTAÇÃO DAS DATACLASSES CENTRALIZADAS (Resolve o ImportError)
from schema import Acao, ContextoConversa
from copy_sanitizer import (
    BALAO_IA_REGEX_CORTE_FINAL,
    preparar_texto_envio,
    delay_entre_baloes,
    delay_escuta_pos_audio,
    quebrar_por_linhas_max,
    aplicar_gancho_na_lista_acoes,
    normalizar_enxerto_dor_sem_contexto,
    tentar_salvar_balao_ia_cortado,
    extrair_evidencias_conversa,
    motivo_redundancia_texto,
    preview_url_flag_para_whatsapp,
)
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
# Pré-nó fase 1 (Instagram, burst, avanço de nó): flows/fase_1_saudacao/sniffer_fase1.py

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
        self.recovery_engine.iniciar_monitor(intervalo_minutos=2)

        self._circuit   = CircuitBreaker()
        self._mod_cache = ModuleCache()
        
        self._leads_em_processamento: dict[int, float] = {}
        self._lock_proc = threading.Lock()
        self._envio_locks_guard = threading.Lock()
        self._envio_locks: dict[int, threading.Lock] = {}
        try:
            from tenant_context import get_engine_tenant_id

            self.tenant_id = str(kwargs.get("tenant_id") or get_engine_tenant_id())
        except Exception:
            self.tenant_id = "default"

    def _lock_envio_lead(self, lead_id: int) -> threading.Lock:
        """Evita intercalar no WhatsApp balões de dois processamentos do mesmo lead."""
        with self._envio_locks_guard:
            lk = self._envio_locks.get(lead_id)
            if lk is None:
                lk = threading.Lock()
                self._envio_locks[lead_id] = lk
            return lk

    @staticmethod
    def _pular_nlu_ia(texto: str, tipo_msg: str) -> bool:
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
        return False

    # ══════════════════════════════════════════════════════════════════
    # ROTA PRINCIPAL DE PROCESSAMENTO
    # ══════════════════════════════════════════════════════════════════

    def processar_mensagem(self, telefone: str, texto_recebido: str, **kwargs) -> dict:
        db = SessionLocal()
        try:
            lead     = self._obter_ou_criar_lead(db, telefone)
            tipo_msg = kwargs.get("tipo_mensagem", "text")
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

                # ── HANDOFF: Verifica se o bot está pausado para atendimento humano ──
                if getattr(lead, "bot_pausado", False):
                    logger.info(f"⏸️ [HANDOFF] Bot pausado para {telefone}. Apenas a registar mensagem.")
                    db.commit()
                    with self._lock_proc:
                        self._leads_em_processamento.pop(lead.id, None)
                    return {"status": "paused"}

                # INJEÇÃO DA CONFIGURAÇÃO CENTRALIZADA
                ctx.metadata["__config__"] = CONFIG_CLIENTE
                ctx.metadata["tts_ativo"]  = self.tts_ativo

                self._restaurar_memoria(lead, ctx)
                try:
                    from studio_runtime import inject_published_studio_into_metadata

                    inject_published_studio_into_metadata(ctx.metadata, tenant_id=self.tenant_id)
                except Exception:
                    pass

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
                # Interceta mídias e desabafos antes do Node 3 para não pedir de novo o que já chegou.
                meta = ctx.metadata
                texto_sniff = (texto_recebido or "").strip()
                if not texto_sniff and meta.get("caption"):
                    texto_sniff = str(meta.get("caption") or "").strip()
                msg_lower = texto_sniff.lower()
                palavras_msg = msg_lower.split()

                if tipo_msg in ("image", "video") and not meta.get("foto_recebida"):
                    meta["foto_recebida"] = True
                    logger.info("👁️ [SNIFFER] Foto interceptada antecipadamente para o lead %s.", lead.id)

                if not meta.get("foto_recebida"):
                    for hm in ctx.historico or []:
                        if getattr(hm, "remetente", "") != "user":
                            continue
                        t_hist = str(getattr(hm, "tipo", "") or "").lower()
                        if t_hist in ("image", "video"):
                            meta["foto_recebida"] = True
                            logger.info(
                                "👁️ [SNIFFER] Foto já presente no histórico (lead=%s) — evita pedir de novo.",
                                lead.id,
                            )
                            break

                _RE_CONTATO_JA_SALVO = re.compile(
                    r"(?i)\b(já|ja)\s+(salvei|salbei|guardei|adicionei|botei)\b|"
                    r"\b(salvei|salbei|guardei)\s+(o\s+)?(seu\s+)?(contato|número|numero|telefone)\b|"
                    r"\b(contato|número|numero)\s+(salvo|guardado|já\s+está|ja\s+esta)\b|"
                    r"\b(salvei|salbei)\s+ddu\b|"
                    r"\bpronto[,]?\s*(já|ja)\s+salvei\b|"
                    r"\bjá\s+deixei\s+seu\s+número\b|"
                    r"\b(salvei|salbei)\s+(teu|seu|o)\s+contato\b"
                )
                if not meta.get("lead_contato_salvo_declarado"):
                    if _RE_CONTATO_JA_SALVO.search(texto_sniff):
                        meta["lead_contato_salvo_declarado"] = True
                        logger.info("📇 [SNIFFER] Lead declarou contato salvo (atual) lead=%s.", lead.id)
                    else:
                        for hm in ctx.historico or []:
                            if getattr(hm, "remetente", "") != "user":
                                continue
                            txh = str(getattr(hm, "texto", "") or "")
                            if _RE_CONTATO_JA_SALVO.search(txh):
                                meta["lead_contato_salvo_declarado"] = True
                                logger.info("📇 [SNIFFER] Contato salvo declarado no histórico lead=%s.", lead.id)
                                break

                _RE_INTENCAO_CONSULTA_CURTA = re.compile(
                    r"(?i)\b(quero\s+saber|gostaria\s+de\s+saber|preciso\s+saber|"
                    r"será\s+que|sera\s+que|vai\s+voltar|volta\s+comigo|volta\s+pra\s+mim|"
                    r"minha\s+ex|meu\s+ex|ela\s+volta|ele\s+volta|me\s+ama|"
                    r"namora|namorad|casamento|casar\s+com)\b"
                )
                if not meta.get("desabafo_recebido"):
                    gatilhos_sniffer = (
                        "traição", "traicao", "marido", "esposa", "ex", "dor", "sofre", "ajuda",
                        "dinheiro", "urgente", "desespero", "choro", "angústia", "angustia", "medo",
                        "traiu", "separou", "voltar",
                    )
                    marcou = len(palavras_msg) > 8 and any(g in msg_lower for g in gatilhos_sniffer)
                    if not marcou and len(palavras_msg) >= 4 and _RE_INTENCAO_CONSULTA_CURTA.search(msg_lower):
                        marcou = True
                    if marcou:
                        meta["desabafo_recebido"] = True
                        blob = texto_sniff[:1500]
                        prev = (meta.get("desabafo_original") or "").strip()
                        meta["desabafo_original"] = f"{prev} {blob}".strip() if prev else blob
                        logger.info("👂 [SNIFFER] Desabafo interceptado antecipadamente para o lead %s.", lead.id)

                ctx.metadata = meta

                _tf_fase1 = concat_texto_usuario(ctx, texto_sniff)
                sniffer_instagram_meta(meta, _tf_fase1, lead.id)
                promover_burst_fase1_meta(meta, _tf_fase1, lead.id, lead)
                resolver_avanco_node_fase1(lead, ctx, meta)
                ctx.metadata = meta

                try:
                    from flows.funnel_gates import snapshot_fase1_coleta

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
                except Exception:
                    pass

                # Enriquecimento IA (com curto-circuito para alta escala)
                if self._pular_nlu_ia(ctx.texto_recebido, tipo_msg):
                    ctx.intencao = "confirmacao" if re.search(
                        r"\b(ok|sim|pronto|beleza|blz|ta|tá|show|fechado)\b",
                        str(ctx.texto_recebido or "").lower(),
                        re.I,
                    ) else "padrao"
                    ctx.sentimento = "padrao"
                    ctx.score_engajamento = 0.5
                else:
                    try:
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            fut_i = pool.submit(
                                self.intent_classifier.classificar,
                                ctx.texto_recebido,
                                ctx.historico,
                                ctx.node_atual,
                                lead.id,
                            )
                            fut_s = pool.submit(
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

                # Inteligência por etapa (copy / funil — não altera FSM)
                enriquecer_contexto_stage(
                    ctx,
                    lead,
                    texto_recebido=texto_recebido or "",
                    intencao=ctx.intencao,
                    sentimento=ctx.sentimento,
                )

                # Máquina de estados
                acoes = self._rotear_state_machine(db, lead, ctx)
                acoes, motivos_redundancia = self._filtrar_acoes_redundantes_por_contexto(ctx, acoes)
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
            lead.node_atual = "14_confirmacao_entrega"
            try:
                registrar_node_transition(
                    db,
                    lead.id,
                    node_antes,
                    "14_confirmacao_entrega",
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
                lead_id=lead.id, telefone=telefone, node_atual="14_confirmacao_entrega",
                historico=[], texto_recebido="SISTEMA_WEBHOOK", tipo_mensagem="system", 
                interactive_reply_id=None, personalizer=self.personalizer
            )
            ctx.metadata["__config__"] = CONFIG_CLIENTE
            try:
                from studio_runtime import inject_published_studio_into_metadata

                inject_published_studio_into_metadata(ctx.metadata, tenant_id=self.tenant_id)
            except Exception:
                pass
            acoes = self._executar_node("14_confirmacao_entrega", ctx, db, lead)
            self._processar_fila(lead.id, ctx, acoes)
        finally:
            db.close()

    def iniciar_fluxo_recuperacao_abandono(self, telefone: str, motivo: str = "abandonou"):
        db = SessionLocal()
        try:
            lead = self._obter_ou_criar_lead(db, telefone)
            if getattr(lead, "convertido", False):
                return

            acoes = self._montar_mensagens_recuperacao(motivo, lead)
            ctx   = ContextoConversa(
                lead_id=lead.id, telefone=telefone, node_atual=lead.node_atual or "8_oferta_principal",
                historico=self._buscar_historico(db, lead.id, 5), texto_recebido=f"SISTEMA_ABANDONO_{motivo.upper()}",
                tipo_mensagem="system", interactive_reply_id=None, nome_lead=lead.nome or "meu anjo", 
                personalizer=self.personalizer
            )
            ctx.metadata["__config__"] = CONFIG_CLIENTE
            try:
                from studio_runtime import inject_published_studio_into_metadata

                inject_published_studio_into_metadata(ctx.metadata, tenant_id=self.tenant_id)
            except Exception:
                pass
            self._processar_fila(lead.id, ctx, acoes)
        except Exception as e:
            logger.error(f"🚨 [RECUPERAÇÃO] {telefone}: {e}", exc_info=True)
        finally:
            db.close()

    def _montar_mensagens_recuperacao(self, motivo: str, lead) -> list[Acao]:
        # Formatação do nome focada no tratamento correto
        nome_raw = getattr(lead, "nome", "") or "meu anjo"
        nome = nome_raw.capitalize()

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

        try:
            if acoes:
                aplicar_gancho_na_lista_acoes(acoes)
            # Só neste disparo: evita repetir o mesmo balão fatiado duas vezes na mesma lista de ações.
            dedup_texto_neste_lote: Set[str] = set()
            for acao in acoes:
                if acao.tipo == "delay":
                    fator = 0.10 if acao.segundos < 5 else 0.20
                    jitter = acao.segundos * fator
                    time.sleep(max(0.5, acao.segundos + random.uniform(-jitter, jitter)))

                elif acao.tipo == "text":
                    fatiados: list[str] = []
                    for parte in self._quebrar_baloes(acao.conteudo):
                        fatiados.extend(quebrar_por_linhas_max(parte, 4))
                    for balao in fatiados:
                        balao_limpo = self._blindar_texto_final_anti_corte(balao)
                        if not balao_limpo:
                            logger.warning(
                                "⚠️ [ENGINE] Balão suprimido por truncamento irreparável. lead=%s node=%s",
                                lead_id,
                                getattr(ctx, "node_atual", ""),
                            )
                            continue
                        balao_limpo = preparar_texto_envio(balao_limpo, "engine_fila_text")
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
                            if chave_dedup:
                                dedup_texto_neste_lote.add(chave_dedup)
                            self._salvar_mensagem(db, lead_id, "bot", balao_limpo, "text", auto_commit=False)
                            enviados += 1
                            pendentes_db += 1
                            if pendentes_db >= batch_commit:
                                db.commit()
                                pendentes_db = 0
                        else:
                            falhas += 1
                        time.sleep(delay_entre_baloes())
                        ultimo_tipo_enviado = "text"

                elif acao.tipo == "vcard":
                    if ultimo_tipo_enviado == "text":
                        time.sleep(random.uniform(2.2, 3.4))
                    if self._enviar_com_retry(ctx.telefone, "vcard", acao.conteudo):
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
                            audio_url = self.audio_engine.gerar(roteiro)
                            if audio_url and self._enviar_com_retry(ctx.telefone, "audio", audio_url):
                                self._salvar_mensagem(db, lead_id, "bot", "[tts]", "audio", auto_commit=False)
                                enviados += 1
                                pendentes_db += 1
                                if pendentes_db >= batch_commit:
                                    db.commit()
                                    pendentes_db = 0
                                time.sleep(delay_escuta_pos_audio())
                        except Exception as e:
                            logger.warning(f"⚠️ [TTS] Falha: {e}. Fallback para texto.")
                            fb = preparar_texto_envio(acao.tts_template, "engine_tts_fallback")
                            if self._enviar_com_retry(ctx.telefone, "text", fb):
                                self._salvar_mensagem(db, lead_id, "bot", fb, "text", auto_commit=False)
                                enviados += 1
                                pendentes_db += 1
                                if pendentes_db >= batch_commit:
                                    db.commit()
                                    pendentes_db = 0

                elif acao.tipo == "audio":
                    payload_url = acao.url or acao.conteudo
                    if payload_url and self._enviar_com_retry(ctx.telefone, "audio", payload_url):
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

                else:
                    payload_url = acao.url or acao.conteudo
                    if acao.tipo in ("image", "video") and ultimo_tipo_enviado == "text":
                        time.sleep(random.uniform(1.4, 2.4))
                    if payload_url and self._enviar_com_retry(ctx.telefone, acao.tipo, payload_url):
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
                except Exception:
                    db.rollback()
            db.close()
            with self._lock_proc:
                self._leads_em_processamento.pop(lead_id, None)

    def _quebrar_baloes(self, texto: str) -> list[str]:
        if "[BALAO]" in texto:
            return [b.strip() for b in texto.split("[BALAO]") if b.strip()]
        return [p.strip() for p in texto.split("\n\n") if p.strip()]

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
        janela = datetime.now(timezone.utc) - timedelta(seconds=90)
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
        2) se ainda parecer "aberto", não envia.
        """
        t = (texto or "").strip()
        if not t:
            return ""
        t2 = tentar_salvar_balao_ia_cortado(t, BALAO_IA_REGEX_CORTE_FINAL).strip()
        t2 = normalizar_enxerto_dor_sem_contexto(t2)
        # Se ainda termina em conectivo/pontuação aberta, suprime.
        if re.search(BALAO_IA_REGEX_CORTE_FINAL, t2.lower()):
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
        # fluxo_encerrado
        return (
            "Teu contato chegou aqui. Se precisar retomar depois, manda um oi quando quiser. 🌙"
        )

    @staticmethod
    def _vocativo_curto_lead(lead, ctx: ContextoConversa) -> str:
        nm = (getattr(lead, "nome", None) or "").strip()
        if nm:
            return nm.split()[0].strip().capitalize()
        n2 = (getattr(ctx, "nome_lead", None) or "").strip()
        if n2:
            return n2.split()[0].strip().capitalize()
        return "meu bem"

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
            except Exception:
                db.rollback()
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
                    lk = link_efetivo_para_node(ctx.node_atual, cfg)
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
        Executa o módulo do node. Se o próximo passo for `6_atencao_dinamica` (Hive Mind → leitura),
        encadeia na mesma requisição — senão o lead ficava só com o delay do Node 5 até a próxima mensagem.
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
                sla_warn_s = float(
                    (ctx.metadata.get("__config__", {}) or {}).get("node_exec_sla_warn_seconds", 3.5)
                    or 3.5
                )
                logger.info(
                    "event=node_exec_timing lead_id=%s node=%s elapsed_s=%.3f acoes=%s prox=%s",
                    lead.id,
                    current_id,
                    elapsed_node,
                    len(res or []),
                    prox,
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

            # Só encadeia o Node 6 (leitura) no mesmo webhook quando o bloco atual
            # NÃO termina em pergunta. Pergunta precisa pausa real de conversa.
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

    def _enviar_com_retry(self, telefone: str, tipo: str, conteudo: str) -> bool:
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
                        "name": {"first_name": "Esmeralda", "formatted_name": "Cigana Esmeralda"},
                        "phones": [{"phone": num_e164, "wa_id": num_limpo, "type": "WORK"}] if num_limpo else []
                    }
                    payload.update({"type": "contacts", "contacts": [contato]})

                else:
                    payload.update({"type": tipo, tipo: {"link": conteudo}})

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
                    if k not in ctx.metadata and k not in ("__config__", "__acassia_studio__"):
                        ctx.metadata[k] = v
            except (json.JSONDecodeError, TypeError):
                ctx.estado_coleta = getattr(lead, "estado_coleta", None) or "inicial"
        else:
            ctx.estado_coleta = getattr(lead, "estado_coleta", None) or "inicial"

    def _persistir_memoria(self, db, lead, ctx: ContextoConversa):
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

            meta_para_salvar = {
                k: v
                for k, v in ctx.metadata.items()
                if k not in ("__config__", "__acassia_studio__")
            }
            lead.metadata_json = meta_para_salvar

        if getattr(ctx, "intencao", None):
            lead.ultima_intencao = str(ctx.intencao)[:50]
        if getattr(ctx, "sentimento", None):
            lead.ultimo_sentimento = str(ctx.sentimento)[:50]

        db.commit()

    def _obter_ou_criar_lead(self, db, telefone: str) -> Lead:
        tid = getattr(self, "tenant_id", None) or "default"
        lead = db.query(Lead).filter_by(telefone=telefone, tenant_id=tid).first()
        if not lead:
            lead = Lead(
                telefone=telefone,
                tenant_id=tid,
                node_atual="1_apresentacao",
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
            m = Mensagem(
                lead_id=lead_id,
                remetente=remetente,
                texto=texto,
                tipo=tipo,
                media_url=media_url,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(m)
            if auto_commit:
                db.commit()
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
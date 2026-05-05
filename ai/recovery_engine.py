"""
ai/recovery_engine.py — Motor de Recuperação Estratégico SUPREME v4.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Módulo de reengajamento automático com tempos agressivos (Protocolo Magno).

ATUALIZAÇÕES DESTA VERSÃO:
🔥 FIX MODEL SYNC (v4.3): Ajuste do atributo 'objecoes_detectadas' para 
   'objecao_silenciosa' para sincronizar com o db/models.py v4.0.
🔥 TIMING MAGNO: R1 (5min), R2 (60min), R3 (180min).
🔥 CICLO ULTRA-RÁPIDO: Monitoramento a cada 2 minutos para precisão cirúrgica.
🔥 CONTEXTO DE NÓ: IA agora gera copy específico para o ponto exato da parada.
🔥 RECUPERAÇÃO MULTIMODAL: Suporte a áudio na primeira tentativa (R1).
🔥 CONCURRENCY LOCKS: Prevenção de corrida na recuperação simultânea.
"""

import json
import logging
import time
import random
import threading
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple, Any
from sqlalchemy import func, and_

from db.database import SessionLocal
from db.models import Lead, Mensagem, EventoAudit
from reliability.distributed_lock import DistributedLock
from utils.datetime_helpers import aware as _ts_utc_helper
from ai.template_registry import TemplateRegistry
from tts.audio_engine import AudioEngine
from schema import ContextoConversa
from copy_sanitizer import (
    preparar_texto_envio,
    delay_entre_baloes,
    quebrar_por_linhas_max,
    resolver_gatilho_emocional,
    aplicar_gancho_na_lista_acoes,
    preview_url_flag_para_whatsapp,
    nome_lead_para_exibicao,
)
from config_cliente import CONFIG_CLIENTE
from analytics.funnel_audit import registrar_node_transition

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA SEQUÊNCIA (5min, 1h, 3h)
# ─────────────────────────────────────────────
SEQUENCIA_RECOVERY = [
    {
        "etapa": 1,
        "categoria": "recuperacao_1",
        "silencio_minutos": 5,  # R1: 5 minutos (Vibração)
        "label": "Check-in de Vibração",
    },
    {
        "etapa": 2,
        "categoria": "recuperacao_2",
        "silencio_minutos": 60,  # R2: 1 hora (O Altar)
        "label": "Comprometimento Altar",
    },
    {
        "etapa": 3,
        "categoria": "recuperacao_3",
        "silencio_minutos": 180,  # R3: 3 horas (Ultimato)
        "label": "Fechamento de Portal",
    },
]

# Nós onde o bot NÃO deve atuar (conversão concluída ou saída solicitada)
NODES_EXCLUIDOS = frozenset(["99_opt_out", "99_convertido", "fluxo_encerrado", "aguardando_dados_altar"])

# Delay anti-spam entre disparos para leads diferentes
DELAY_ENTRE_LEADS = (15, 40)

# Hardening anti-colisão (evita recovery "em cima" de interação real)
SILENCIO_MIN_POR_NODE = {
    "3_coleta_profunda": 10,
    "4_instagram": 9,
    # Pós-oferta / FIRMO: não cutucar em poucos minutos; soa robótico no celular.
    "8_oferta_principal": 30,
    "aguardando_pagamento": 30,
}
SILENCIO_MIN_DESDE_ULTIMO_USER = 8
# Ligeiramente < 15 para não perder ciclo do monitor (2min) quando dá ~14.94min desde a mídia.
COOLDOWN_MIDIA_USER_MIN = 14.9
JANELA_SENSIVEL_NODE3_MIN = 12
MAX_LEADS_POR_CICLO = int(CONFIG_CLIENTE.get("recovery_max_leads_por_ciclo", 120) or 120)


class _NoopCtx:
    """No-op context manager — usado quando tenant_override_ctx nao esta disponivel."""
    def __enter__(self):
        return None
    def __exit__(self, *args):
        return False


class RecoveryEngine:
    def __init__(
        self,
        whatsapp_token: str,
        whatsapp_phone_id: str,
        gemini_api_key: str | None = None,
        *,
        tts_ativo: bool = False,
    ):
        self.wa_token = whatsapp_token
        self.wa_phone_id = whatsapp_phone_id
        self.wa_url = f"https://graph.facebook.com/v19.0/{whatsapp_phone_id}/messages"
        self.tts_ativo = tts_ativo
        self._rodando = False
        self.template_registry = TemplateRegistry(gemini_api_key)
        self.audio_engine = AudioEngine() if tts_ativo else None
        # Distributed locks per-lead (cross-worker safe via Redis, fallback local)
        self._locks: Dict[int, DistributedLock] = {}
        self._locks_guard = threading.Lock()  # protege acesso ao dict
        self._locks_ts: Dict[int, float] = {}  # lead_id → last_used timestamp

    def iniciar_monitor(self, intervalo_minutos: int = 2):
        """Inicia o monitor de alta frequência para suportar recuperação de 5min."""
        self._rodando = True
        t = threading.Thread(target=self._loop_monitoramento, args=(intervalo_minutos,), daemon=True, name="RecoveryMonitor")
        t.start()
        logger.info("🔄 [RECOVERY] Monitor v4.3 Ativo (Check: %dmin).", intervalo_minutos)

    def _loop_monitoramento(self, intervalo_minutos: int):
        _gc_counter = 0
        while self._rodando:
            try:
                self._executar_ciclo()
            except Exception as e:
                logger.error("🚨 [RECOVERY] Erro crítico no ciclo: %s", e, exc_info=True)
            # GC a cada ~10 ciclos (20 min)
            _gc_counter += 1
            if _gc_counter >= 10:
                try:
                    self._gc_locks()
                except Exception:
                    pass
                _gc_counter = 0
            time.sleep(intervalo_minutos * 60)

    def _executar_ciclo(self):
        agora = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            # Multi-tenant (Frente 1):
            # - Se ENV MEU_MISTERIO_TENANT_ID estiver setada -> single-tenant (legacy).
            # - Senao, processa todos os tenants com binding ativo + tenants
            #   que tem leads ativos no DB.
            try:
                from tenant_context import get_engine_tenant_id, tenant_override_ctx
            except Exception:
                tenant_override_ctx = None
                get_engine_tenant_id = lambda: "default"

            import os as _os
            single_tenant_legacy = bool(_os.getenv("MEU_MISTERIO_TENANT_ID"))

            base_query = db.query(Lead).filter(
                Lead.node_atual.notin_(NODES_EXCLUIDOS),
                Lead.recovery_bloqueado == False,
                Lead.convertido == False,
            )

            if single_tenant_legacy:
                _tid = get_engine_tenant_id()
                leads = (
                    base_query.filter(Lead.tenant_id == _tid)
                    .order_by(Lead.atualizado_em.asc())
                    .limit(MAX_LEADS_POR_CICLO)
                    .all()
                )
            else:
                # Multi-tenant: leads de qualquer tenant ate o limite
                leads = (
                    base_query.order_by(Lead.atualizado_em.asc())
                    .limit(MAX_LEADS_POR_CICLO)
                    .all()
                )

            if not leads:
                return

            sinais = self._precarregar_sinais_leads(db, [l.id for l in leads])
            disparados = 0
            resets_pendentes = 0
            for lead in leads:
                try:
                    lock = self._obter_lock(lead.id)
                    if lock.acquire(blocking=False):
                        try:
                            # Sempre opera no tenant do lead (multi-tenant safe)
                            lead_tenant = lead.tenant_id or "default"
                            ctx_mgr = (
                                tenant_override_ctx(lead_tenant)
                                if tenant_override_ctx is not None
                                else _NoopCtx()
                            )
                            with ctx_mgr:
                                acao = self._avaliar_lead(db, lead, agora, sinais.get(lead.id, {}))
                                if getattr(lead, "_recovery_reset_pendente", False):
                                    resets_pendentes += 1
                                    setattr(lead, "_recovery_reset_pendente", False)
                                if acao:
                                    self._disparar_recovery(db, lead, acao, agora)
                                    disparados += 1
                                    time.sleep(random.randint(*DELAY_ENTRE_LEADS))
                        finally:
                            lock.release()
                    else:
                        logger.debug(f"🔒 [RECOVERY] Lead {lead.id} já está a ser processado. Ignorando.")
                except Exception as e:
                    db.rollback()
                    logger.error(f"🚨 [RECOVERY] Erro no lead {lead.id}: %s", e, exc_info=True)

            if resets_pendentes > 0:
                try:
                    db.commit()
                    logger.info("🔄 [RECOVERY] Resets em lote aplicados: %s", resets_pendentes)
                except Exception:
                    db.rollback()

            if disparados > 0:
                logger.info("✅ [RECOVERY] Ciclo concluído. %d disparos realizados.", disparados)
        finally:
            db.close()

    def _obter_lock(self, lead_id: int) -> DistributedLock:
        """Retorna um lock distribuído específico para o lead (cross-worker safe)."""
        with self._locks_guard:
            lk = self._locks.get(lead_id)
            if lk is None:
                lk = DistributedLock(
                    f"recovery:lead:{lead_id}",
                    ttl_ms=120_000,  # 2 min TTL — suficiente para um ciclo de recovery
                )
                self._locks[lead_id] = lk
            self._locks_ts[lead_id] = time.time()
            return lk

    def _gc_locks(self, max_idle_s: int = 600) -> None:
        """Remove locks não usados há mais de max_idle_s para evitar memory leak."""
        cutoff = time.time() - max_idle_s
        with self._locks_guard:
            stale = [lid for lid, ts in self._locks_ts.items() if ts < cutoff]
            for lid in stale:
                self._locks.pop(lid, None)
                self._locks_ts.pop(lid, None)
            if stale:
                logger.debug("[RECOVERY_GC] Evicted %d stale locks", len(stale))

    @staticmethod
    def _ts_utc(ts: Optional[datetime]) -> Optional[datetime]:
        return _ts_utc_helper(ts)

    def _precarregar_sinais_leads(self, db, lead_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Pré-carrega sinais de atividade em lote para reduzir N+1 no ciclo de recovery.
        """
        if not lead_ids:
            return {}
        out: Dict[int, Dict[str, Any]] = {lid: {} for lid in lead_ids}

        sq_ult_ts = (
            db.query(
                Mensagem.lead_id.label("lead_id"),
                func.max(Mensagem.timestamp).label("ts"),
            )
            .filter(Mensagem.lead_id.in_(lead_ids))
            .group_by(Mensagem.lead_id)
            .subquery()
        )
        ult_rows = (
            db.query(Mensagem.lead_id, Mensagem.remetente, Mensagem.timestamp)
            .join(
                sq_ult_ts,
                and_(
                    Mensagem.lead_id == sq_ult_ts.c.lead_id,
                    Mensagem.timestamp == sq_ult_ts.c.ts,
                ),
            )
            .all()
        )
        for lead_id, remetente, ts in ult_rows:
            if out.get(lead_id, {}).get("ultima_msg_ts") is None:
                out[lead_id]["ultima_msg_ts"] = ts
                out[lead_id]["ultima_msg_remetente"] = remetente

        user_rows = (
            db.query(
                Mensagem.lead_id,
                func.max(Mensagem.timestamp),
            )
            .filter(
                Mensagem.lead_id.in_(lead_ids),
                Mensagem.remetente == "user",
            )
            .group_by(Mensagem.lead_id)
            .all()
        )
        for lead_id, ts in user_rows:
            out[lead_id]["ultima_user_ts"] = ts

        media_rows = (
            db.query(
                Mensagem.lead_id,
                func.max(Mensagem.timestamp),
            )
            .filter(
                Mensagem.lead_id.in_(lead_ids),
                Mensagem.remetente == "user",
                Mensagem.tipo.in_(("image", "audio", "video")),
            )
            .group_by(Mensagem.lead_id)
            .all()
        )
        for lead_id, ts in media_rows:
            out[lead_id]["ultima_midia_user_ts"] = ts

        return out

    def _avaliar_lead(self, db, lead: Lead, agora: datetime, sinais: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Avalia se o lead está elegível para uma nova recuperação."""
        sinais = sinais or {}
        if (lead.node_atual or "").startswith("static_meumisterio_"):
            return None
        etapa_atual = lead.recovery_stage or 0
        if etapa_atual >= len(SEQUENCIA_RECOVERY):
            return None

        config_etapa = SEQUENCIA_RECOVERY[etapa_atual]
        silencio_min = int(config_etapa["silencio_minutos"])
        silencio_min = max(silencio_min, int(SILENCIO_MIN_POR_NODE.get(lead.node_atual or "", 0)))

        ts_ultima_msg = self._ts_utc(sinais.get("ultima_msg_ts"))
        remetente_ultima_msg = str(sinais.get("ultima_msg_remetente") or "")
        if not ts_ultima_msg:
            return None

        # RESET: última mensagem do usuário = não está em ghosting. Só limpa recovery se havia estado pendente
        # (evita commit/log a cada ciclo quando stage já é 0 — última mensagem costuma ser do user).
        if remetente_ultima_msg == "user":
            if (lead.recovery_stage or 0) > 0 or lead.ultimo_recovery_em is not None:
                self._reset_recovery(db, lead, auto_commit=False)
                setattr(lead, "_recovery_reset_pendente", True)
            return None

        # Verifica se o tempo de silêncio já passou
        if (agora - ts_ultima_msg) < timedelta(minutes=silencio_min):
            return None

        # Guardrail 1: exige silêncio mínimo também desde a última mensagem do USER
        ts_user = self._ts_utc(sinais.get("ultima_user_ts"))
        if ts_user and (agora - ts_user) < timedelta(minutes=max(silencio_min, SILENCIO_MIN_DESDE_ULTIMO_USER)):
            logger.info(
                "event=recovery_skip_user_recent lead=%s node=%s etapa=%s min_desde_user=%.2f req_min=%s",
                lead.id,
                lead.node_atual,
                config_etapa.get("etapa"),
                (agora - ts_user).total_seconds() / 60.0,
                max(silencio_min, SILENCIO_MIN_DESDE_ULTIMO_USER),
            )
            return None

        # Guardrail 2: cooldown após mídia do usuário (foto/áudio/vídeo), especialmente no começo do funil
        ts_media = self._ts_utc(sinais.get("ultima_midia_user_ts"))
        if ts_media and (agora - ts_media) < timedelta(minutes=COOLDOWN_MIDIA_USER_MIN):
            logger.info(
                "event=recovery_skip_media_cooldown lead=%s node=%s etapa=%s min_desde_media=%.2f cooldown_min=%s",
                lead.id,
                lead.node_atual,
                config_etapa.get("etapa"),
                (agora - ts_media).total_seconds() / 60.0,
                COOLDOWN_MIDIA_USER_MIN,
            )
            return None

        # Guardrail 3: Node3 sensível — evitar recuperação quando o lead está responsivo (confirmação/frustração)
        if (lead.node_atual or "") == "3_coleta_profunda":
            i = str(getattr(lead, "ultima_intencao", "") or "").lower().strip()
            s = str(getattr(lead, "ultimo_sentimento", "") or "").lower().strip()
            if i in {"confirmacao", "engajado"} and s in {"frustrado", "interessado"} and ts_user:
                if (agora - ts_user) < timedelta(minutes=JANELA_SENSIVEL_NODE3_MIN):
                    logger.info(
                        "event=recovery_skip_node3_contextual lead=%s intencao=%s sentimento=%s min_desde_user=%.2f janela_min=%s",
                        lead.id,
                        i,
                        s,
                        (agora - ts_user).total_seconds() / 60.0,
                        JANELA_SENSIVEL_NODE3_MIN,
                    )
                    return None

        # Trava de segurança: Nunca enviar dois recoveries em menos de 4 minutos
        ultimo_recovery = lead.ultimo_recovery_em
        if ultimo_recovery:
            ultimo_recovery = self._ts_utc(ultimo_recovery)
            if (agora - ultimo_recovery) < timedelta(minutes=4):
                return None

        return config_etapa

    def _split_baloes(self, texto: str) -> List[str]:
        if not texto or not texto.strip():
            return []
        if "[BALAO]" in texto:
            return [b.strip() for b in texto.split("[BALAO]") if b.strip()]
        parts = [p.strip() for p in texto.split("\n\n") if p.strip()]
        return parts if parts else [texto.strip()]

    def _enviar_whatsapp_texto_com_retry(self, telefone: str, mensagem: str, max_tentativas: int = 3) -> bool:
        """Repete envio com backoff leve (API/WhatsApp instável)."""
        for t in range(max_tentativas):
            if self._enviar_whatsapp_texto(telefone, mensagem):
                return True
            if t < max_tentativas - 1:
                espera = min(12.0, 1.2 * (2**t)) + random.uniform(0, 2.0)
                logger.warning(
                    "⚠️ [RECOVERY] Retry texto %s/%s para %s após %.1fs",
                    t + 1,
                    max_tentativas,
                    telefone[-6:],
                    espera,
                )
                time.sleep(espera)
        return False

    def _metadata_lead_como_dict(self, lead: Lead) -> Dict[str, Any]:
        m = lead.metadata_json
        if isinstance(m, dict):
            return dict(m)
        if isinstance(m, str) and m.strip():
            try:
                return dict(json.loads(m))
            except json.JSONDecodeError:
                return {}
        return {}

    def _registrar_falha_recovery_node9(
        self,
        db: SessionLocal,
        lead: Lead,
        agora: datetime,
        tentativa: int,
        blocos_ok: int,
    ) -> None:
        """
        Não incrementa recovery_stage. Atualiza ultimo_recovery_em para respeitar o anti-spam de 4 min
        e grava diagnóstico para o dashboard / próximo ciclo.
        """
        lead.ultimo_recovery_em = agora
        meta = self._metadata_lead_como_dict(lead)
        meta["recovery_node9_falhou_em"] = agora.isoformat()
        meta["recovery_node9_tentativa_sem_sucesso"] = tentativa
        meta["recovery_node9_blocos_enviados_antes_falha"] = blocos_ok
        lead.metadata_json = meta
        db.add(
            EventoAudit(
                lead_id=lead.id,
                evento="recovery_node9_falha_envio",
                dados={"tentativa": tentativa, "blocos_ok": blocos_ok},
            )
        )
        db.commit()
        logger.warning(
            "🔴 [RECOVERY] Node9 incompleto lead_id=%s tentativa=%s blocos_ok=%s (stage NÃO incrementado)",
            lead.id,
            tentativa,
            blocos_ok,
        )

    def _enviar_sequencia_node9(self, db: SessionLocal, lead: Lead, acoes: list, agora: datetime) -> Tuple[bool, int]:
        """Envia Acao (text/delay). Retorna (sucesso_total, quantidade_de_textos_entregues)."""
        textos_entregues = 0
        if acoes:
            aplicar_gancho_na_lista_acoes(acoes)
        for acao in acoes:
            if acao.tipo == "delay":
                j = max(0.5, acao.segundos * 0.15)
                time.sleep(max(0.5, acao.segundos + random.uniform(-j, j)))
            elif acao.tipo == "text":
                for balao in self._split_baloes(acao.conteudo):
                    for parte in quebrar_por_linhas_max(balao, 4):
                        body = preparar_texto_envio(parte, "recovery_node9")
                        if not body:
                            continue
                        ok = self._enviar_whatsapp_texto_com_retry(lead.telefone, body)
                        if ok:
                            textos_entregues += 1
                            db.add(
                                Mensagem(
                                    lead_id=lead.id,
                                    remetente="bot",
                                    texto=body,
                                    tipo="recovery",
                                    timestamp=agora,
                                )
                            )
                            # Batch commit: persistimos em lote no final da tentativa
                            # para reduzir contenção de escrita.
                        else:
                            return False, textos_entregues
                        time.sleep(delay_entre_baloes())
            else:
                logger.debug("[RECOVERY] Ação omitida na sequência node9: %s", getattr(acao, "tipo", ""))
        return True, textos_entregues

    def _disparar_recovery(self, db: SessionLocal, lead: Lead, config: Dict[str, Any], agora: datetime):
        """Dispara a mensagem de recuperação para o lead."""
        try:
            nome = (lead.nome or "").strip()
            nome_fmt = nome_lead_para_exibicao(nome).capitalize()

            # Pós-oferta: usar copy do node_9 (3 toques) alinhada ao recovery_stage
            if lead.node_atual == "aguardando_pagamento":
                try:
                    from flows.fase_3_oferta import node_9_recuperacao as n9

                    lead_meta = self._metadata_lead_como_dict(lead)
                    # Migrado pra tenant_config (façade com fallback ao CONFIG_CLIENTE).
                    # deepcopy: lead_meta pode ser mutado downstream; tenant_config retorna proxy.
                    import copy as _copy
                    from api.tenant_config import get_tenant_config
                    _tid = getattr(lead, "tenant_id", None) or "default"
                    lead_meta["__config__"] = _copy.deepcopy(dict(get_tenant_config(_tid)))
                    if getattr(lead, "resumo_dor", None):
                        lead_meta.setdefault("resumo_dor", lead.resumo_dor)
                    if getattr(lead, "objecao_silenciosa", None):
                        lead_meta.setdefault("objecao_silenciosa", lead.objecao_silenciosa)
                    if not (lead_meta.get("gatilho_emocional") or "").strip():
                        lead_meta["gatilho_emocional"] = resolver_gatilho_emocional(
                            lead_meta,
                            resumo_dor_coluna=getattr(lead, "resumo_dor", None) or "",
                            objecao_coluna=getattr(lead, "objecao_silenciosa", None) or "",
                        )

                    ctx = ContextoConversa(
                        lead_id=lead.id,
                        telefone=lead.telefone,
                        node_atual=lead.node_atual,
                        texto_recebido="__SISTEMA_RECOVERY__",
                        historico=[],
                        nome_lead=lead.nome or "",
                        metadata=lead_meta,
                    )
                    tentativa = (lead.recovery_stage or 0) + 1
                    acoes, proximo = n9.executar_v2(ctx, tentativa=tentativa)

                    audit = " | ".join(a.conteudo[:80] for a in acoes if a.tipo == "text")[:480]
                    ok, n_textos = self._enviar_sequencia_node9(db, lead, acoes, agora)

                    if ok:
                        clean_meta = {k: v for k, v in (ctx.metadata or {}).items() if k != "__config__"}
                        clean_meta["recovery_node9_ultima_tentativa"] = tentativa
                        clean_meta.pop("recovery_node9_falhou_em", None)
                        clean_meta.pop("recovery_node9_tentativa_sem_sucesso", None)
                        clean_meta.pop("recovery_node9_blocos_enviados_antes_falha", None)
                        lead.metadata_json = clean_meta
                        if getattr(ctx, "estado_coleta", None):
                            lead.estado_coleta = ctx.estado_coleta
                        if proximo and proximo != lead.node_atual:
                            node_antes = lead.node_atual
                            lead.node_atual = proximo
                            try:
                                registrar_node_transition(
                                    db,
                                    lead.id,
                                    node_antes,
                                    proximo,
                                    intencao=getattr(lead, "ultima_intencao", None),
                                    sentimento=getattr(lead, "ultimo_sentimento", None),
                                    tipo_mensagem="recovery",
                                    texto_recebido="",
                                    origem="recovery_node9",
                                )
                            except Exception as e:
                                logger.warning("⚠️ [AUDIT] recovery transition: %s", e)

                        self._atualizar_lead_apos_recovery(
                            db, lead, config, agora, audit or "[NODE9]", False, gravar_linha_historico=False
                        )
                        logger.info(
                            "💌 [RECOVERY] Node9 T%s para %s (node=%s) textos=%s.",
                            tentativa,
                            lead.telefone,
                            lead.node_atual,
                            n_textos,
                        )
                    else:
                        self._registrar_falha_recovery_node9(db, lead, agora, tentativa, n_textos)
                    return
                except Exception as e:
                    logger.error("🚨 [RECOVERY] Falha Node9, fallback template: %s", e, exc_info=True)
                    db.rollback()

            variaveis = {"nome": nome_fmt}

            contexto_geracao = {
                "sentimento": lead.ultimo_sentimento or "padrao",
                "historico": self._buscar_historico_resumido(db, lead.id),
                "objecoes": lead.objecao_silenciosa or "nenhuma",
            }

            texto = self.template_registry.obter_ou_gerar(
                categoria=config["categoria"],
                node=lead.node_atual,
                contexto_geracao=contexto_geracao,
                variaveis=variaveis,
            )

            if not texto:
                logger.warning("⚠️ [RECOVERY] Sem texto para enviar ao lead %s.", lead.id)
                return

            texto_limpo = preparar_texto_envio(texto, "recovery_template")
            ok_texto = self._enviar_whatsapp_texto_com_retry(lead.telefone, texto_limpo)

            ok_audio = False
            if ok_texto and self.tts_ativo and self.audio_engine and config["etapa"] == 1:
                audio_url = self.audio_engine.gerar(f"{nome_fmt}, senti um silêncio agora. Estou aguardando por você no altar.")
                if audio_url:
                    time.sleep(random.randint(4, 8))
                    ok_audio = self._enviar_whatsapp_audio(lead.telefone, audio_url)

            if ok_texto:
                self._atualizar_lead_apos_recovery(db, lead, config, agora, texto_limpo, ok_audio, gravar_linha_historico=True)
                logger.info("💌 [RECOVERY] %s enviada para %s (Node: %s).", config["label"], lead.telefone, lead.node_atual)

        except Exception as e:
            logger.error("🚨 [RECOVERY] Falha ao disparar recuperação para %s: %s", lead.telefone, e, exc_info=True)
            db.rollback()

    def _atualizar_lead_apos_recovery(
        self,
        db: SessionLocal,
        lead: Lead,
        config: Dict[str, Any],
        agora: datetime,
        texto: str,
        ok_audio: bool,
        *,
        gravar_linha_historico: bool = True,
    ):
        """Atualiza o lead após o disparo da recuperação."""
        lead.recovery_stage += 1
        lead.ultimo_recovery_em = agora

        if gravar_linha_historico:
            db.add(
                Mensagem(
                    lead_id=lead.id,
                    remetente="bot",
                    texto=f"[RECOVERY-{lead.recovery_stage}] {texto}",
                    tipo="recovery",
                    timestamp=agora,
                )
            )

        db.add(
            EventoAudit(
                lead_id=lead.id,
                evento="recovery_disparado",
                dados={
                    "etapa": lead.recovery_stage,
                    "node": lead.node_atual,
                    "audio": ok_audio,
                    "trecho": (texto or "")[:200],
                },
            )
        )
        db.commit()

    def _reset_recovery(self, db: SessionLocal, lead: Lead, *, auto_commit: bool = True):
        """Reseta o contador se o lead voltou a interagir (só grava/loga se havia estado de recovery)."""
        if (lead.recovery_stage or 0) == 0 and lead.ultimo_recovery_em is None:
            return
        lead.recovery_stage = 0
        lead.ultimo_recovery_em = None
        if auto_commit:
            db.commit()
        logger.info("🔄 [RECOVERY] Reset automático para o lead %s.", lead.id)

    def _buscar_historico_resumido(self, db: SessionLocal, lead_id: int) -> str:
        """Busca o histórico resumido das mensagens."""
        msgs = db.query(Mensagem).filter(Mensagem.lead_id == lead_id).order_by(Mensagem.timestamp.desc()).limit(3).all()
        return " | ".join([f"{'U' if m.remetente=='user' else 'B'}: {m.texto[:50]}" for m in reversed(msgs)])

    def _enviar_whatsapp_texto(self, telefone: str, mensagem: str) -> bool:
        """Envia mensagem de texto via WhatsApp."""
        headers = {"Authorization": f"Bearer {self.wa_token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": telefone,
            "type": "text",
            "text": {"body": mensagem, "preview_url": preview_url_flag_para_whatsapp(mensagem)},
        }
        try:
            r = requests.post(self.wa_url, json=payload, headers=headers, timeout=12)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"❌ Falha ao enviar texto para {telefone}: {e}")
            return False

    def _enviar_whatsapp_audio(self, telefone: str, url: str) -> bool:
        """Envia mensagem de áudio via WhatsApp."""
        headers = {"Authorization": f"Bearer {self.wa_token}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": telefone, "type": "audio", "audio": {"link": url}}
        try:
            r = requests.post(self.wa_url, json=payload, headers=headers, timeout=15)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"❌ Falha ao enviar áudio para {telefone}: {e}")
            return False
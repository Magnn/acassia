"""
db/models.py — SUPREME v4.0 (A MEMÓRIA DO ORÁCULO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Multi-tenant (tenant_id), Studio AcassIA, mensagens com media_url.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float,
    DateTime, ForeignKey, Boolean, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def _agora_utc():
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("tenant_id", "telefone", name="uq_lead_tenant_phone"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, default="default", index=True)
    telefone = Column(String(20), nullable=False, index=True)

    node_atual = Column(String(100), default="1_apresentacao", index=True)
    node_historico = Column(JSON, default=list)

    estado_coleta = Column(String, default="inicial")
    metadata_json = Column(JSON, default=dict)

    nome = Column(String(200), nullable=True)
    genero = Column(String(20), nullable=True)
    arquetipo = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    tags = Column(JSON, default=list)

    tempo_sofrimento = Column(String(100), nullable=True)
    resumo_dor = Column(Text, nullable=True)
    desejo_oculto = Column(Text, nullable=True)
    nome_mecanismo = Column(String(200), nullable=True)
    objecao_silenciosa = Column(Text, nullable=True)

    nivel_energia = Column(String(50), nullable=True)
    tom_sugerido = Column(String(50), nullable=True)
    score_engajamento = Column(Float, default=0.5)
    ultima_intencao = Column(String(50), nullable=True)
    ultimo_sentimento = Column(String(50), nullable=True)

    recovery_stage = Column(Integer, default=0)
    recovery_bloqueado = Column(Boolean, default=False, index=True)
    ultimo_recovery_em = Column(DateTime(timezone=True), nullable=True)

    opt_out = Column(Boolean, default=False)
    convertido = Column(Boolean, default=False, index=True)
    produto_comprado = Column(String(200), nullable=True)
    bot_pausado = Column(Boolean, default=False, index=True)

    criado_em = Column(DateTime(timezone=True), default=_agora_utc)
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)
    # Controle de concorrência (motor vs thread de envio): merge otimista em metadata_json
    metadata_version = Column(Integer, nullable=False, default=0)

    mensagens = relationship("Mensagem", back_populates="lead", lazy="dynamic", cascade="all, delete-orphan")
    eventos = relationship("EventoAudit", back_populates="lead", lazy="dynamic", cascade="all, delete-orphan")
    behavior_events = relationship(
        "LeadBehaviorEvent",
        back_populates="lead",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Lead id={self.id} tel={self.telefone} node={self.node_atual} genero={self.genero}>"


class Mensagem(Base):
    __tablename__ = "mensagens"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    remetente = Column(String(10), nullable=False)
    texto = Column(Text, nullable=False)
    tipo = Column(String(20), default="text")
    media_url = Column(Text, nullable=True)

    intencao = Column(String(50), nullable=True)
    sentimento = Column(String(50), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_agora_utc, index=True)

    lead = relationship("Lead", back_populates="mensagens")


class TemplateMsg(Base):
    __tablename__ = "templates_msg"

    id = Column(Integer, primary_key=True, index=True)
    chave_base = Column(String(100), nullable=False, index=True)
    categoria = Column(String(50), nullable=False)
    node_origem = Column(String(100), nullable=True)
    corpo = Column(Text, nullable=False)

    score_conversao = Column(Float, default=0.5)
    total_usos = Column(Integer, default=0)
    total_conversoes = Column(Integer, default=0)

    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)


class AudioCache(Base):
    __tablename__ = "audio_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), unique=True, nullable=False, index=True)
    url_publica = Column(Text, nullable=False)
    texto_original = Column(Text, nullable=True)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)


class EventoAudit(Base):
    __tablename__ = "eventos_audit"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=_agora_utc, index=True)
    evento = Column(String(100), nullable=False)
    dados = Column(JSON, default=dict)

    lead = relationship("Lead", back_populates="eventos")


class WhatsAppInboundReceipt(Base):
    """
    Idempotência durável de webhooks Meta (at-least-once delivery).
    Mesmo wamid não reentra na fila após restart do processo.
    """

    __tablename__ = "whatsapp_inbound_receipts"
    __table_args__ = (UniqueConstraint("tenant_id", "wamid", name="uq_wa_receipt_tenant_wamid"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, default="default", index=True)
    wamid = Column(String(128), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc, index=True)


class LeadBehaviorEvent(Base):
    """
    Telemetria passiva para dataset de treino da IA de atendimento.
    Não altera o fluxo do motor; apenas registra sinais observados do turno.
    """

    __tablename__ = "lead_behavior_events"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, default="default", index=True)
    timestamp = Column(DateTime(timezone=True), default=_agora_utc, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    node_atual = Column(String(100), nullable=True, index=True)
    payload = Column(JSON, default=dict)

    lead = relationship("Lead", back_populates="behavior_events")


class StudioAgent(Base):
    __tablename__ = "studio_agents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), default="default", nullable=False, index=True)
    name = Column(String(200), nullable=False)
    avatar = Column(String(32), default="#7c3aed", nullable=False)
    draft_json = Column(JSON, default=dict)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)

    versoes = relationship(
        "StudioAgentVersion",
        back_populates="agent",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class StudioAgentVersion(Base):
    __tablename__ = "studio_agent_versions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("studio_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    body_json = Column(JSON, default=dict)
    note = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)

    agent = relationship("StudioAgent", back_populates="versoes")


class StudioPublish(Base):
    __tablename__ = "studio_publish"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, unique=True, index=True, default="default")
    published_version_id = Column(
        Integer,
        ForeignKey("studio_agent_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class FlowBlueprint(Base):
    """
    Fluxo desenhado no Flow Builder (documento acassia-flow v1).
    Persistência servidor por tenant + slug estável.
    """

    __tablename__ = "flow_blueprints"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_flow_blueprint_tenant_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, default="default", index=True)
    slug = Column(String(128), nullable=False, index=True)
    title = Column(String(300), nullable=False, default="")
    body_json = Column(JSON, default=dict)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)


class FlowPublish(Base):
    """Blueprint publicado por tenant (referência para executor / metadados no motor)."""

    __tablename__ = "flow_publish"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, unique=True, index=True, default="default")
    published_blueprint_id = Column(
        Integer,
        ForeignKey("flow_blueprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class FlowBlueprintVersion(Base):
    """Snapshot imutável do documento acassia-flow (histórico / restore)."""

    __tablename__ = "flow_blueprint_versions"
    __table_args__ = (UniqueConstraint("blueprint_id", "version_number", name="uq_flow_bp_version_num"),)

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    body_json = Column(JSON, default=dict)
    note = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)


class FlowBlueprintLock(Base):
    """Lock cooperativo por blueprint (colaboração)."""

    __tablename__ = "flow_blueprint_locks"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lock_holder = Column(String(200), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)


class FlowBlueprintComment(Base):
    """Comentário opcionalmente ancorado a um nó (node_ref)."""

    __tablename__ = "flow_blueprint_comments"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    node_ref = Column(String(200), nullable=True)
    body = Column(Text, nullable=False)
    author_label = Column(String(200), nullable=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)


class FlowRun(Base):
    """Execução observável de um blueprint (manual ou futuro agendado)."""

    __tablename__ = "flow_runs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="queued")
    meta_json = Column(JSON, default=dict)
    started_at = Column(DateTime(timezone=True), default=_agora_utc)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class FlowRunEvent(Base):
    __tablename__ = "flow_run_events"
    __table_args__ = (UniqueConstraint("run_id", "seq", name="uq_flow_run_event_seq"),)

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("flow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)
    payload_json = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=_agora_utc)


class TenantFlowSecret(Base):
    """Segredos por tenant (valor ofuscado em repouso; use cofre em produção)."""

    __tablename__ = "tenant_flow_secrets"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_tenant_flow_secret_key"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    key = Column(String(128), nullable=False)
    value_cipher = Column(Text, nullable=False)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)


class TenantFlowVariable(Base):
    """Variáveis não sensíveis (JSON) por tenant."""

    __tablename__ = "tenant_flow_variables"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_tenant_flow_var_key"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    key = Column(String(128), nullable=False)
    value_json = Column(JSON, nullable=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)


class FlowBlueprintAclEntry(Base):
    __tablename__ = "flow_blueprint_acl"
    __table_args__ = (UniqueConstraint("blueprint_id", "principal", name="uq_flow_bp_acl_principal"),)

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    principal = Column(String(200), nullable=False)
    role = Column(String(32), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)


class FlowSchedule(Base):
    """Agendamento (cron) — persistência; worker de disparo é etapa futura."""

    __tablename__ = "flow_schedules"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    cron_expr = Column(String(120), nullable=False)
    timezone = Column(String(64), nullable=False, default="America/Sao_Paulo")
    active = Column(Boolean, default=True)
    meta_json = Column(JSON, default=dict)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)
    atualizado_em = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)


class User(Base):
    """
    Usuário do SaaS (tarólogo). 1 user = 1 tenant_id (relação 1:1 inicial).
    Pode evoluir pra many-to-one (multi-team) numa fase futura.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(200), nullable=True)
    role = Column(String(20), nullable=False, default="user", index=True) # 'admin' | 'user'
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), default=_agora_utc)

    # ── 2FA TOTP (Frente 8.1, 1.1) ─────────────────────────────────
    totp_secret = Column(String(64), nullable=True)
    totp_enabled_at = Column(DateTime(timezone=True), nullable=True)
    totp_recovery_codes = Column(JSON, nullable=True)  # 10 one-time codes (hashed)

    # ── Verification + lifecycle (Frente 8.11, 1.8, 1.9) ───────────
    is_verified = Column(Boolean, default=False, nullable=False)
    phone = Column(String(30), nullable=True)
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_password_change_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    suspended_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    suspension_reason = Column(Text, nullable=True)

    # ── Admin sub-roles (Frente 1.24) ──────────────────────────────
    # null pra users; "founder|support|billing" pra admins
    admin_subrole = Column(String(20), nullable=True)

    # ── UX prefs (Frente 5) ────────────────────────────────────────
    timezone = Column(String(40), default="America/Sao_Paulo", nullable=False)
    theme_preset = Column(String(40), nullable=True)
    dashboard_layout = Column(JSON, nullable=True)
    tours_completed = Column(JSON, default=list)
    last_changelog_seen_at = Column(DateTime(timezone=True), nullable=True)

    # ── Trial + dunning (Frente 2.19, 2.20) ────────────────────────
    trial_started_at = Column(DateTime(timezone=True), nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    trial_extended_count = Column(Integer, default=0, nullable=False)
    dunning_status = Column(String(20), nullable=True)  # null|past_due|cancelled
    dunning_attempts = Column(Integer, default=0, nullable=False)


# ─── Frente 1: Admin tables ──────────────────────────────────────────


class ImpersonationSession(Base):
    """
    Sessões de admin impersonando user. Toda ação durante a sessão é
    auditada com link pro impersonator real (Frente 1.2).
    """
    __tablename__ = "impersonation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_tenant_id = Column(String(64), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    end_reason = Column(String(20), nullable=True)  # manual|expired|forced|crash
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    actions_count = Column(Integer, default=0, nullable=False)


class TenantAdminNote(Base):
    """Notas internas do admin sobre um tenant (Frente 1.4 / 1.21)."""
    __tablename__ = "tenant_admin_notes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    author_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class TenantPlanOverride(Base):
    """Override admin do plano comercial de um tenant (Frente 1.5)."""
    __tablename__ = "tenant_plan_overrides"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    plan = Column(String(32), nullable=False)
    granted_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    starts_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # null = permanente
    pauses_stripe = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    revoked_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TenantQuotaGrant(Base):
    """Cota extra concedida pelo admin (Frente 1.6)."""
    __tablename__ = "tenant_quota_grants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(40), nullable=False)  # gemini_tokens|wa_msgs|leads
    amount = Column(Integer, nullable=False)
    used_amount = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TenantUsageCounter(Base):
    """
    Counter atômico de uso por (tenant, period_yyyymm, kind) (Frente 2.2).
    UPSERT com CAS pra atomicidade.
    """
    __tablename__ = "tenant_usage_counters"

    tenant_id = Column(String(64), primary_key=True)
    period_yyyymm = Column(Integer, primary_key=True)  # 202604
    kind = Column(String(40), primary_key=True)        # leads|wa_msgs|gemini_tokens
    count = Column(Integer, default=0, nullable=False)
    cost_brl_cents = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class PlanGlobalOverride(Base):
    """
    Override admin de campos globais de um plano (Frente 2.1) — ex.:
    aumentar limite de leads do Pro de 5k pra 7k sem deploy.
    """
    __tablename__ = "plan_global_overrides"

    id = Column(Integer, primary_key=True, index=True)
    plan_key = Column(String(32), nullable=False, index=True)
    field_path = Column(String(100), nullable=False)  # ex: "limits.leads_month"
    field_value = Column(JSON, nullable=False)
    set_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TenantHealth(Base):
    """Health score composto por tenant (Frente 1.15)."""
    __tablename__ = "tenant_health"

    tenant_id = Column(String(64), primary_key=True)
    score = Column(Integer, nullable=False)  # 0-100
    band = Column(String(10), nullable=False)  # healthy|at_risk|critical
    components = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class FeatureFlag(Base):
    """Definição global de feature flags (Frente 1.10)."""
    __tablename__ = "feature_flags"

    key = Column(String(64), primary_key=True)
    description = Column(Text, nullable=True)
    default_value = Column(Boolean, default=False, nullable=False)
    rollout_pct = Column(Integer, default=0, nullable=False)  # 0-100
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TenantFeatureFlag(Base):
    """Override por tenant de feature flag (Frente 1.10)."""
    __tablename__ = "tenant_feature_flags"

    tenant_id = Column(String(64), primary_key=True)
    flag_key = Column(String(64), ForeignKey("feature_flags.key"), primary_key=True)
    enabled = Column(Boolean, nullable=False)
    set_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    set_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class AuditEvent(Base):
    """
    Audit log estruturado v2 pra ações administrativas e do user (Frente 1.12, 8.5).
    Distingue de `eventos_audit` legado (que é específico de eventos de lead).
    """
    __tablename__ = "eventos_audit_v2"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=_agora_utc, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)  # null pra eventos não-tenant
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    impersonator_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    impersonation_id = Column(Integer, ForeignKey("impersonation_sessions.id"), nullable=True)
    event_type = Column(String(80), nullable=False, index=True)
    target_type = Column(String(40), nullable=True)
    target_id = Column(String(120), nullable=True)
    payload = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)


class TenantUsageQuotaWarning(Base):
    """Tracking de quais warnings de quota já foram enviados (Frente 2.11)."""
    __tablename__ = "tenant_quota_warnings"

    tenant_id = Column(String(64), primary_key=True)
    period_yyyymm = Column(Integer, primary_key=True)
    kind = Column(String(40), primary_key=True)
    threshold_pct = Column(Integer, primary_key=True)  # 80 / 95 / 100
    sent_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class PaymentEventReceipt(Base):
    """
    Idempotência durável de webhooks de pagamento (at-least-once delivery).
    Mesmo (provider, event_id, tenant) não reentra após restart do processo —
    análogo ao WhatsAppInboundReceipt mas pra Stripe / Cakto. Ver ADR_006 (G4).
    """

    __tablename__ = "payment_event_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "event_id", name="uq_payment_event_receipt"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, default="default", index=True)
    provider = Column(String(32), nullable=False, index=True)   # 'stripe' | 'cakto'
    event_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(64), nullable=True)              # ex 'payment_intent.succeeded'
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    raw_payload = Column(JSON, default=dict)
    processed_at = Column(DateTime(timezone=True), default=_agora_utc, index=True)

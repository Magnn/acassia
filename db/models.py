"""
db/models.py — SUPREME v4.0 (A MEMÓRIA DO ORÁCULO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Multi-tenant (tenant_id), Studio AcassIA, mensagens com media_url.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float,
    DateTime, Date, ForeignKey, Boolean, JSON, UniqueConstraint,
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

    # Lead scoring (Frente 3.24) — distinto de score_engajamento legado
    # score_value: 0-100 composto (engagement + sentiment + funnel + commercial)
    # score_band: hot|warm|cold
    # score_components: dict com pontuações individuais pra debug
    score_value = Column(Integer, default=0, nullable=False, index=True)
    score_band = Column(String(10), default="cold", nullable=False, index=True)
    score_components = Column(JSON, nullable=True)
    score_updated_at = Column(DateTime(timezone=True), nullable=True)
    ultimo_sentimento = Column(String(50), nullable=True)

    recovery_stage = Column(Integer, default=0)
    recovery_bloqueado = Column(Boolean, default=False, index=True)
    ultimo_recovery_em = Column(DateTime(timezone=True), nullable=True)

    opt_out = Column(Boolean, default=False)
    convertido = Column(Boolean, default=False, index=True)
    produto_comprado = Column(String(200), nullable=True)
    bot_pausado = Column(Boolean, default=False, index=True)

    # Astrologia (Frente 4.3 / 4.13)
    birth_date = Column(Date, nullable=True)
    signo = Column(String(20), nullable=True, index=True)
    timezone = Column(String(60), nullable=True)  # IANA tz; default tenant-level
    # consents: {daily_horoscope: bool, marketing: bool, ...} — LGPD
    consents = Column(JSON, default=dict, nullable=False)

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


class PasswordResetToken(Base):
    """
    Token one-time pra reset de senha (Frente 8.9).
    Token armazena bcrypt hash; URL expira em 1h.
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    requested_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class EmailVerificationToken(Base):
    """Token pra verificar email após signup (Frente 8.11)."""
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class ConsentRecord(Base):
    """Registro de consents do user pra LGPD (Frente 8.16)."""
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    visitor_id = Column(String(64), nullable=True, index=True)
    consents = Column(JSON, nullable=False)  # {analytics: true, marketing: false, ...}
    policy_version = Column(String(20), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class OnboardingMilestone(Base):
    """
    Marcos de ativação do user (Frente 5.1).
    Auto-detectados em hot paths (signup, wa_connect, first_flow_published, etc).
    """
    __tablename__ = "onboarding_milestones"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    milestone_key = Column(String(40), primary_key=True)
    completed_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    metadata_json = Column(JSON, nullable=True)


class FlowTemplate(Base):
    """
    Templates pré-construídos de fluxo pra acelerar onboarding (Frente 5.3).
    Marketplace V2 (Frente 7.14) reutiliza essa table com seller_tenant_id.
    """
    __tablename__ = "flow_templates"

    id = Column(String(40), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(40), nullable=True)
    preview_image_url = Column(String(500), nullable=True)
    ticket_brl_avg = Column(Integer, default=0, nullable=False)
    blueprint_json = Column(JSON, nullable=False)
    agent_json = Column(JSON, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    is_official = Column(Boolean, default=True, nullable=False)
    seller_tenant_id = Column(String(64), nullable=True)
    price_brl_cents = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TarotDeck(Base):
    """Decks de tarot (Marselha, Rider-Waite, custom). Frente 4.7."""
    __tablename__ = "tarot_decks"

    id = Column(String(40), primary_key=True)
    name = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    tenant_id = Column(String(64), nullable=True)  # null = global/shared
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TarotCard(Base):
    """Cartas individuais (78 por deck). Frente 4.7."""
    __tablename__ = "tarot_cards"

    id = Column(String(40), primary_key=True)
    deck_id = Column(String(40), ForeignKey("tarot_decks.id"), primary_key=True)
    name = Column(String(100), nullable=False)
    arcana = Column(String(10), nullable=False)  # major|minor
    suit = Column(String(20), nullable=True)  # copas|ouros|espadas|paus
    number = Column(Integer, nullable=True)
    image_url = Column(String(500), nullable=True)
    meaning_upright = Column(Text, nullable=True)
    meaning_reversed = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)


class MarketplaceListing(Base):
    """Listing público de template no marketplace (Frente 7.14)."""
    __tablename__ = "marketplace_listings"

    id = Column(Integer, primary_key=True, index=True)
    seller_tenant_id = Column(String(64), nullable=False, index=True)
    seller_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    flow_template_id = Column(String(40), ForeignKey("flow_templates.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(40), nullable=True)
    price_brl_cents = Column(Integer, nullable=False)
    blueprint_json = Column(JSON, nullable=False)
    agent_json = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    preview_image_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending_review", nullable=False)
    approved_by_admin = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    total_sales = Column(Integer, default=0, nullable=False)
    total_revenue_brl_cents = Column(Integer, default=0, nullable=False)
    rating_avg = Column(Float, nullable=True)
    rating_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class MarketplacePurchase(Base):
    """Compra de listing no marketplace."""
    __tablename__ = "marketplace_purchases"

    id = Column(Integer, primary_key=True, index=True)
    buyer_tenant_id = Column(String(64), nullable=False, index=True)
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=False, index=True)
    amount_brl_cents = Column(Integer, nullable=False)
    acassia_fee_cents = Column(Integer, nullable=False)
    seller_payout_cents = Column(Integer, nullable=False)
    stripe_payment_id = Column(String(120), nullable=True)
    pix_payment_id = Column(String(120), nullable=True)
    payment_provider = Column(String(40), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    purchased_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    applied_blueprint_id = Column(Integer, nullable=True)


class MarketplaceReview(Base):
    """Reviews de listings."""
    __tablename__ = "marketplace_reviews"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=False, index=True)
    purchase_id = Column(Integer, ForeignKey("marketplace_purchases.id"), nullable=False, unique=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class LunarTrigger(Base):
    """Gatilho lunar pra disparar fluxos automáticos (Frente 4.2)."""
    __tablename__ = "lunar_triggers"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    flow_id = Column(Integer, nullable=True)
    flow_slug = Column(String(120), nullable=True)
    trigger_phase = Column(String(20), nullable=False)  # nova|crescente|cheia|minguante
    window_hours_before = Column(Integer, default=0, nullable=False)
    segment_filter = Column(JSON, nullable=True)  # {tags: [...], score_band: 'hot', etc}
    active = Column(Boolean, default=True, nullable=False)
    last_fired_at = Column(DateTime(timezone=True), nullable=True)
    fire_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class LunarPhase(Base):
    """Cache de fases lunares pré-calculadas (Frente 4.1)."""
    __tablename__ = "lunar_phases"

    date = Column(DateTime(timezone=True), primary_key=True)  # always 00:00 UTC do dia
    phase_name = Column(String(20), nullable=False)  # nova|crescente|cheia|minguante
    illumination_pct = Column(Float, nullable=False)
    zodiac_sign = Column(String(20), nullable=True)  # se computado
    is_special = Column(Boolean, default=False, nullable=False)
    special_label = Column(String(60), nullable=True)


class Affiliate(Base):
    """Programa de afiliados (Frente 7.15) — referência → comissão recorrente."""
    __tablename__ = "affiliates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    ref_code = Column(String(40), nullable=False, unique=True, index=True)
    pix_key = Column(String(120), nullable=True)
    pix_key_type = Column(String(20), nullable=True)  # cpf|email|phone|random
    total_referrals = Column(Integer, default=0, nullable=False)
    active_referrals = Column(Integer, default=0, nullable=False)
    total_earned_brl_cents = Column(Integer, default=0, nullable=False)
    total_paid_out_brl_cents = Column(Integer, default=0, nullable=False)
    commission_pct = Column(Integer, default=30, nullable=False)  # 30% padrão
    tier = Column(String(20), default="standard", nullable=False)  # standard|silver|gold
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class Referral(Base):
    """Referral entry: lead que veio via afiliado."""
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    affiliate_id = Column(Integer, ForeignKey("affiliates.id"), nullable=False, index=True)
    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    referred_email = Column(String(200), nullable=True)
    signed_up_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    first_payment_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="signup", nullable=False)  # signup|trial|paid|churned
    total_commission_earned_cents = Column(Integer, default=0, nullable=False)
    last_recurrence_at = Column(DateTime(timezone=True), nullable=True)
    cookie_ip = Column(String(45), nullable=True)


class AffiliatePayout(Base):
    """Pagamento de comissão ao afiliado (mensal)."""
    __tablename__ = "affiliate_payouts"

    id = Column(Integer, primary_key=True, index=True)
    affiliate_id = Column(Integer, ForeignKey("affiliates.id"), nullable=False, index=True)
    period_yyyymm = Column(Integer, nullable=False, index=True)
    amount_brl_cents = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending|paid|failed
    paid_at = Column(DateTime(timezone=True), nullable=True)
    pix_receipt_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class VoiceClone(Base):
    """
    Voz clonada por user para TTS (Frente 4.14).
    Provider primário: ElevenLabs. Outros TBD (Coqui, OpenAI TTS).
    """
    __tablename__ = "voice_clones"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=True)
    provider = Column(String(40), nullable=False)  # elevenlabs|coqui|openai
    provider_voice_id = Column(String(120), nullable=False)
    enrollment_audio_url = Column(Text, nullable=True)
    sample_audio_url = Column(Text, nullable=True)  # áudio de teste gerado
    status = Column(String(20), default="pending", nullable=False)  # pending|active|failed
    consented_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class AudioGeneration(Base):
    """Histórico de TTS gerados (Frente 4.16). Conta tokens consumidos."""
    __tablename__ = "audio_generations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    voice_clone_id = Column(Integer, ForeignKey("voice_clones.id"), nullable=True)
    text = Column(Text, nullable=False)
    chars_count = Column(Integer, nullable=False)
    audio_url = Column(Text, nullable=True)
    duration_s = Column(Float, nullable=True)
    provider = Column(String(40), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending|done|failed
    error_message = Column(Text, nullable=True)
    cost_usd_cents = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class PixPayment(Base):
    """
    Pix QR dinâmico (Frente 7.1).
    Gerado via Mercado Pago / Asaas / Pagar.me.
    """
    __tablename__ = "pix_payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    flow_run_id = Column(Integer, nullable=True)
    provider = Column(String(40), nullable=False)  # mercadopago|asaas|pagarme
    provider_payment_id = Column(String(120), nullable=False, unique=True, index=True)
    amount_brl_cents = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    qr_code_image_url = Column(Text, nullable=True)  # base64 data URL ou URL imagem
    qr_code_text = Column(Text, nullable=True)  # copia-e-cola
    expires_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending|approved|expired|cancelled
    paid_at = Column(DateTime(timezone=True), nullable=True)
    raw_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TarotReading(Base):
    """Tiragens feitas pra leads (Frente 4.10)."""
    __tablename__ = "tarot_readings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    attended_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    spread_type = Column(String(40), nullable=False)  # 1card|3card|cross5|celtic10
    deck_id = Column(String(40), nullable=False)
    cards = Column(JSON, nullable=False)  # [{card_id, position, reversed}]
    question = Column(Text, nullable=True)
    interpretation = Column(Text, nullable=True)
    sent_to_lead = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class FlowNodeVisit(Base):
    """
    Visita de lead em um nó específico do fluxo (Frente 3.26).
    Persistido cada vez que lead entra/sai de um nó pra calcular funnel.
    """
    __tablename__ = "flow_node_visits"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    flow_id = Column(Integer, nullable=True, index=True)  # FlowBlueprint.id (null se motor estático)
    flow_slug = Column(String(120), nullable=True, index=True)
    node_id = Column(String(120), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    entered_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    exited_at = Column(DateTime(timezone=True), nullable=True)
    exit_reason = Column(String(40), nullable=True)  # response|timeout|exit|next|error


class TenantBilling(Base):
    """
    Estado canônico de assinatura Stripe por tenant (Frente 2.16).
    Atualizado via webhook handlers. Fonte de verdade pro effective_plan.
    """
    __tablename__ = "tenant_billing"

    tenant_id = Column(String(64), primary_key=True)
    plan = Column(String(32), nullable=True)  # starter|pro|enterprise
    billing_period = Column(String(10), nullable=True)  # monthly|annual
    status = Column(String(20), nullable=True)
    # Stripe IDs
    customer_id = Column(String(120), nullable=True, index=True)
    subscription_id = Column(String(120), nullable=True)
    price_id = Column(String(120), nullable=True)
    # Datas críticas
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    # Pending downgrade (Frente 2.18) — aplicar no próximo period_end
    pending_plan = Column(String(32), nullable=True)
    pending_billing_period = Column(String(10), nullable=True)
    pending_effective_at = Column(DateTime(timezone=True), nullable=True)
    # MRR
    mrr_brl_cents = Column(Integer, default=0, nullable=False)
    # Update tracking
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class CancellationSurvey(Base):
    """Survey ao cancelar assinatura (Frente 2.21)."""
    __tablename__ = "cancellation_surveys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason_category = Column(String(40), nullable=True)
    reason_text = Column(Text, nullable=True)
    win_back_offered = Column(String(40), nullable=True)
    win_back_accepted = Column(Boolean, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    reactivated_at = Column(DateTime(timezone=True), nullable=True)


class UserSession(Base):
    """
    Sessão de login persistida pra session mgmt (Frente 8.4-8.6).
    Gravada em parallelo com flask-login session cookie.
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    geo_country = Column(String(2), nullable=True)
    geo_city = Column(String(100), nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(40), nullable=True)


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


class DailyHoroscope(Base):
    """
    Cache de horoscopo diario por signo (Frente 4.13).

    PK composto (date, signo, lang) — uma geracao por signo/idioma/dia.
    Compartilhado entre tenants (idempotencia global por dia) — assim economiza
    tokens Gemini quando 100 tenants pedem o mesmo signo no mesmo dia.
    """
    __tablename__ = "daily_horoscopes"
    __table_args__ = (
        UniqueConstraint("date", "signo", "lang", name="uq_daily_horoscope_date_sign_lang"),
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    signo = Column(String(20), nullable=False, index=True)
    lang = Column(String(8), default="pt-BR", nullable=False)
    text = Column(Text, nullable=False)
    source = Column(String(40), nullable=False)         # gemini|manual|external_api
    generated_by = Column(String(80), nullable=True)    # model_id ou autor
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class HoroscopeAutomation(Base):
    """
    Configuracao por tenant da automacao de horoscopo diario (Frente 4.13).
    """
    __tablename__ = "horoscope_automations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    send_hour_local = Column(Integer, default=7, nullable=False)   # 0-23
    timezone = Column(String(60), default="America/Sao_Paulo", nullable=False)
    source = Column(String(20), default="gemini", nullable=False)  # gemini|manual
    # segment: 'all' | 'hot' | 'warm' | 'hot_warm'
    segment_filter = Column(String(20), default="all", nullable=False)
    custom_prefix = Column(Text, nullable=True)   # texto fixo antes do horoscopo
    last_run_date = Column(Date, nullable=True)   # ultima data UTC processada
    total_sent = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc, nullable=False)


class HoroscopeDelivery(Base):
    """
    Log de envios diarios de horoscopo (idempotencia + analytics).
    Garante que mesmo (tenant, lead, date) nao envia duas vezes.
    """
    __tablename__ = "horoscope_deliveries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "lead_id", "date", name="uq_horoscope_delivery_tenant_lead_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    signo = Column(String(20), nullable=False)
    status = Column(String(20), default="sent", nullable=False)  # sent|failed|opted_out|skipped
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

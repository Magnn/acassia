"""
db/models.py — SUPREME v4.0 (A MEMÓRIA DO ORÁCULO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Multi-tenant (tenant_id), Studio AcassIA, mensagens com media_url.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float,
    DateTime, Date, ForeignKey, Boolean, JSON, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from .database import Base


def _agora_utc():
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "telefone", name="uq_lead_tenant_phone"),
        Index("ix_lead_tenant_node", "tenant_id", "node_atual"),
        Index("ix_lead_tenant_pipeline", "tenant_id", "pipeline_stage"),
        Index("ix_lead_tenant_score", "tenant_id", "score_band"),
        Index("ix_lead_tenant_updated", "tenant_id", "atualizado_em"),
    )

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

    # Pipeline stage (ActiveCampaign-style Kanban)
    # novo → em_conversa → interessado → proposta → agendado → convertido → perdido
    pipeline_stage = Column(String(30), default="novo", nullable=False, index=True)

    # Deal value (AC CRM: valor monetário esperado)
    deal_value = Column(Float, default=0.0, nullable=False)
    deal_currency = Column(String(3), default="BRL", nullable=False)

    # Win Probability (AC predictive: 0-100%)
    win_probability = Column(Integer, default=0, nullable=False)

    # Conversion Attribution (último flow/recipe que converteu)
    conversion_source = Column(String(200), nullable=True)
    conversion_at = Column(DateTime(timezone=True), nullable=True)

    # Engagement temporal patterns (AC engagement tagging)
    avg_response_time_min = Column(Float, nullable=True)  # tempo médio de resposta em minutos
    preferred_hour = Column(Integer, nullable=True)  # hora preferida (0-23) — predictive sending
    last_response_at = Column(DateTime(timezone=True), nullable=True)
    engagement_level = Column(String(20), default="unknown", nullable=False)  # superfan, engaged, idle, inactive

    # Astrologia (Frente 4.3 / 4.13)
    birth_date = Column(Date, nullable=True)
    signo = Column(String(20), nullable=True, index=True)
    timezone = Column(String(60), nullable=True)  # IANA tz; default tenant-level
    # consents: {daily_horoscope: bool, marketing: bool, ...} — LGPD
    consents = Column(JSON, default=dict, nullable=False)

    # Cadastro extendido (Frente 3.18)
    idade = Column(Integer, nullable=True)
    cidade = Column(String(120), nullable=True)
    custom_fields = Column(JSON, default=dict, nullable=False)

    # Frente 4.19: aggregate intent espiritual (top category + urgency)
    spiritual_category = Column(String(40), nullable=True, index=True)
    spiritual_intent = Column(JSON, nullable=True)
    spiritual_intent_at = Column(DateTime(timezone=True), nullable=True)

    # Sentiment Routing: urgência detectada pela IA → CRM prioriza no topo
    is_urgent = Column(Boolean, default=False, nullable=False, index=True)
    urgent_reason = Column(String(200), nullable=True)
    urgent_at = Column(DateTime(timezone=True), nullable=True)

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
    __table_args__ = (
        Index("ix_msg_lead_ts", "lead_id", "timestamp"),
        Index("ix_msg_lead_remetente_ts", "lead_id", "remetente", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    remetente = Column(String(10), nullable=False)
    texto = Column(Text, nullable=False)
    tipo = Column(String(20), default="text")
    media_url = Column(Text, nullable=True)
    # Frente 4 ext — tracking de entrega Meta (wamid + status)
    wamid = Column(String(128), nullable=True, index=True)
    delivery_status = Column(String(20), nullable=True)  # sent|delivered|read|failed
    delivery_status_at = Column(DateTime(timezone=True), nullable=True)

    intencao = Column(String(50), nullable=True)
    sentimento = Column(String(50), nullable=True)
    # Frente 4.19: classificacao de intent espiritual
    # {categories: ["amor","decisao"], urgency: "high|med|low", emotion: "ansiedade"}
    spiritual_intent = Column(JSON, nullable=True)
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
    __table_args__ = (
        Index("ix_evento_lead_ts", "lead_id", "timestamp"),
    )

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
    __table_args__ = (
        Index("ix_behavior_tenant_type_ts", "tenant_id", "event_type", "timestamp"),
        Index("ix_behavior_lead_ts", "lead_id", "timestamp"),
    )

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
    Fluxo desenhado no Flow Builder (documento meumisterio-flow v1).
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
    """Snapshot imutável do documento meumisterio-flow (histórico / restore)."""

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
    status = Column(String(32), nullable=False, default="queued", index=True)
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
    tenant_id = Column(String(64), nullable=False, index=True) # Removido unique=True (Agora 1 User pode ter N Workspaces)
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



class Workspace(Base):
    """
    O Espaço de Trabalho (Clínica/Agência).
    O ID deste modelo é o `tenant_id` usado em todo o sistema.
    """
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True) # Equivale ao tenant_id
    name = Column(String(128), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

class WorkspaceMember(Base):
    """
    Tabela de relacionamento Usuário <-> Workspace.
    """
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(32), default="admin", nullable=False) # admin, operator
    joined_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

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
    __table_args__ = (
        Index("ix_audit_v2_tenant_type", "tenant_id", "event_type"),
        Index("ix_audit_v2_tenant_ts", "tenant_id", "timestamp"),
    )

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


# ═══════════════════════════════════════════════════════════════════════
# DREAM INTERPRETER — Interpretador de Sonhos IA
# ═══════════════════════════════════════════════════════════════════════

class DreamEntry(Base):
    """
    Registro de sonho com interpretação IA.
    Análise simbólica junguiana + espiritual + padrões recorrentes.
    """
    __tablename__ = "dream_entries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)

    content = Column(Text, nullable=False)  # relato do sonho
    title = Column(String(200), nullable=True)  # título auto-gerado
    dream_date = Column(Date, nullable=True)  # noite do sonho

    # Análise IA
    symbols = Column(JSON, default=list)  # ["água", "cobra", "casa"]
    interpretation = Column(Text, nullable=True)  # interpretação junguiana/espiritual
    emotional_tone = Column(String(32), nullable=True)  # medo, alegria, confusão
    archetype = Column(String(64), nullable=True)  # sombra, anima, self, trickster
    recurring_themes = Column(JSON, default=list)  # temas que se repetem entre sonhos
    lucidity_level = Column(Integer, nullable=True)  # 1-5

    # Contexto astral
    moon_phase = Column(String(32), nullable=True)
    sign = Column(String(32), nullable=True)

    # Tarot conexão (carta que representa o sonho)
    # Nota: TarotCard tem PK composta (id, deck_id), FK parcial não é válida.
    # Armazena card_id como soft-reference (string).
    tarot_card_id = Column(String(40), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# VISION BOARD — Manifestação Visual com IA
# ═══════════════════════════════════════════════════════════════════════

class VisionBoardItem(Base):
    """
    Item do quadro de visão/manifestação.
    IA gera imagens, usuário trackeia manifestações realizadas.
    """
    __tablename__ = "vision_board_items"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)

    category = Column(String(32), nullable=False)  # amor, prosperidade, saude, carreira, espiritual
    affirmation = Column(Text, nullable=False)  # "Eu atraio abundância ilimitada"
    image_url = Column(Text, nullable=True)  # URL da imagem (IA-gerada ou upload)
    description = Column(Text, nullable=True)
    target_date = Column(Date, nullable=True)  # data-alvo p/ manifestação

    is_manifested = Column(Boolean, default=False, nullable=False)
    manifested_at = Column(DateTime(timezone=True), nullable=True)
    manifestation_notes = Column(Text, nullable=True)

    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# COMMUNITY — Fórum/Comunidade com IA Oráculo
# ═══════════════════════════════════════════════════════════════════════

class CommunityGroup(Base):
    """
    Grupo/comunidade. Pode ser por signo, prática, tema.
    Suporta IA Oracle que responde perguntas dentro do grupo.
    """
    __tablename__ = "community_groups"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(32), nullable=False, default="general")  # signo, pratica, tema, livre
    icon = Column(String(8), nullable=True)  # emoji
    cover_image_url = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True, nullable=False)
    oracle_enabled = Column(Boolean, default=True, nullable=False)  # IA Oracle ativa
    oracle_persona = Column(Text, nullable=True)  # persona customizada da IA

    member_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False, nullable=False)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

    members = relationship("CommunityMember", backref="group", lazy="dynamic")
    posts = relationship("CommunityPost", backref="group", lazy="dynamic")


class CommunityMember(Base):
    """Membro de um grupo. Controla permissões e notificações."""
    __tablename__ = "community_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("community_groups.id"), nullable=False, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # se for terapeuta
    tenant_id = Column(String(64), nullable=True, index=True)

    role = Column(String(16), default="member")  # admin, moderator, member
    notifications_on = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class CommunityPost(Base):
    """
    Post/mensagem em um grupo. Suporta:
    - Posts normais (texto, imagem)
    - Perguntas para IA Oracle
    - Respostas da IA
    - Threads (reply_to_id)
    """
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("community_groups.id"), nullable=False, index=True)
    author_consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # terapeuta
    tenant_id = Column(String(64), nullable=True, index=True)

    content = Column(Text, nullable=False)
    post_type = Column(String(16), default="post")  # post, question, oracle_response, event, poll
    media_url = Column(Text, nullable=True)
    media_type = Column(String(16), nullable=True)  # image, video, audio

    # Thread
    reply_to_id = Column(Integer, ForeignKey("community_posts.id"), nullable=True)
    reply_count = Column(Integer, default=0)

    # Oracle IA
    is_oracle_response = Column(Boolean, default=False)
    oracle_context = Column(JSON, default=dict)  # contexto usado na geração

    # Engajamento
    reaction_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

    reactions = relationship("CommunityReaction", backref="post", lazy="dynamic")


class CommunityReaction(Base):
    """Reação a um post (like, love, fire, etc)."""
    __tablename__ = "community_reactions"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    reaction_type = Column(String(16), default="like")  # like, love, fire, pray, insight
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
    tenant_id = Column(String(64), nullable=True, index=True)  # null = global/shared
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
    meumisterio_fee_cents = Column(Integer, nullable=False)
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
    # Voice default do tenant (Frente 4.16) — bot usa essa pra audios outbound.
    # Apenas 1 voice_clone por tenant pode estar marcada como default por vez.
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    consented_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class AudioLibraryItem(Base):
    """
    Biblioteca de audios pre-gravados/curados (Frente 4.17).

    Tarologos sobem uploads de "saudacao manha", "oracao protecao", etc.
    Reutilizaveis em conversas inbound e em flow nodes (audio prontos).
    Cada audio sofre soft delete via deleted_at.
    """
    __tablename__ = "audio_library"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(40), nullable=True, index=True)
    tags = Column(JSON, default=list, nullable=False)
    audio_url = Column(String(500), nullable=False)  # /saas/voice/audio/<file_id>
    file_path = Column(String(500), nullable=True)   # caminho absoluto local (debug)
    duration_s = Column(Integer, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
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
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class FlowNodeVisit(Base):
    """
    Visita de lead em um nó específico do fluxo (Frente 3.26).
    Persistido cada vez que lead entra/sai de um nó pra calcular funnel.
    """
    __tablename__ = "flow_node_visits"
    __table_args__ = (
        Index("ix_fnv_tenant_node_entered", "tenant_id", "node_id", "entered_at"),
        Index("ix_fnv_lead_entered", "lead_id", "entered_at"),
    )

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


class LeadNatalChart(Base):
    """Mapa astral lite por lead (Frente 4.5/4.6)."""
    __tablename__ = "lead_natal_charts"

    lead_id = Column(Integer, ForeignKey("leads.id"), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    birth_date = Column(Date, nullable=True)
    birth_time = Column(String(8), nullable=True)   # "HH:MM" local
    birth_place = Column(String(200), nullable=True)
    birth_lat = Column(Float, nullable=True)
    birth_lon = Column(Float, nullable=True)
    timezone_offset = Column(Float, default=-3.0, nullable=False)  # horas vs UTC
    chart_json = Column(JSON, nullable=True)        # output natal_chart_lite()
    interpretation_text = Column(Text, nullable=True)
    interpretation_focus = Column(String(40), nullable=True)
    computed_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    interpreted_at = Column(DateTime(timezone=True), nullable=True)


class LeadNumerology(Base):
    """Numerologia por lead (Frente 4.11/4.12)."""
    __tablename__ = "lead_numerology"

    lead_id = Column(Integer, ForeignKey("leads.id"), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    full_name = Column(String(300), nullable=True)
    birth_date = Column(Date, nullable=True)
    life_path = Column(Integer, nullable=True)
    expression = Column(Integer, nullable=True)
    soul = Column(Integer, nullable=True)
    components = Column(JSON, nullable=True)  # meanings + qualquer extra
    interpretation_text = Column(Text, nullable=True)
    computed_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    interpreted_at = Column(DateTime(timezone=True), nullable=True)


class LeadNote(Base):
    """Notas livres do atendente sobre um lead (Frente 3.23)."""
    __tablename__ = "lead_notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc, nullable=False)


class QuickReply(Base):
    """
    Templates de mensagem rapida para uso na inbox (Frente 3.12).
    Diferente de TemplateMsg (que serve copy do motor) — esta tabela e
    de atendentes humanos compose box.
    """
    __tablename__ = "quick_replies"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "shortcut_number",
            name="uq_quick_reply_tenant_shortcut",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    body = Column(Text, nullable=False)               # pode ter {{nome}}, {{signo}}
    category = Column(String(40), nullable=True)     # saudacao|oferta|fechamento|recuperacao
    shortcut_number = Column(Integer, nullable=True) # 1-9 (atalho teclado)
    usage_count = Column(Integer, default=0, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc, nullable=False)


class WaPhoneTenantBinding(Base):
    """
    Liga um phone_number_id da Meta WhatsApp Cloud API ao tenant dono dele
    (Frente 1: multi-tenant onboarding).

    O webhook /webhook é unico, mas a Meta envia phone_number_id no payload
    (entry[].changes[].value.metadata.phone_number_id). Esse mapeamento e
    usado para resolver o tenant correto antes do _triagem_meta enfileirar.

    Tambem suporta verify_token e app_secret por tenant — o token global
    do .env continua funcionando como fallback (single-tenant mode).
    """
    __tablename__ = "wa_phone_tenant_bindings"

    phone_number_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    waba_id = Column(String(64), nullable=True)
    display_phone_number = Column(String(40), nullable=True)
    verify_token = Column(String(120), nullable=True)
    app_secret = Column(String(200), nullable=True)
    # Per-tenant webhook path (defesa em profundidade). Formato wh_<32_chars_url_safe>.
    # Cada tenant tem URL unica /webhook/<webhook_path> alem do /webhook global.
    webhook_path = Column(String(64), nullable=True, unique=True, index=True)
    status = Column(String(20), default="pending", nullable=False)  # pending|active|failed
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    # Subscribe automatico ao webhook field "messages" via Graph API
    subscribed_at = Column(DateTime(timezone=True), nullable=True)
    subscribe_error = Column(Text, nullable=True)
    # Telemetria de inbound: 1ª msg + acumulado
    first_inbound_at = Column(DateTime(timezone=True), nullable=True)
    last_inbound_at = Column(DateTime(timezone=True), nullable=True)
    inbound_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc, nullable=False,
    )


class WaInboundLog(Base):
    """
    Log lightweight de eventos do webhook inbound (Frente 1 — observabilidade).

    Persistido apenas em casos relevantes:
        - rate_limited     (msg dropada por excesso de inbound)
        - tenant_resolve_miss (phone_id desconhecido)
        - hmac_invalid     (assinatura rejeitada)
        - error            (excecao no _triagem_meta)
        - first_inbound    (1a msg de um phone_id)

    Nao logamos every-msg por questoes de espaco. Sucessos sao contados
    em WaPhoneTenantBinding.inbound_count.
    """
    __tablename__ = "wa_inbound_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    phone_number_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(40), nullable=False, index=True)
    message = Column(Text, nullable=True)
    payload_excerpt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False, index=True)


class FlowNodeExperiment(Base):
    """
    A/B test em no de mensagem (Frente 3.28-3.29).

    Cada experimento tem variantes A (original) e B (alternativa).
    Assignment deterministico via hash(experiment_id + lead_id) % 100.

    winning_event:
        responded — lead respondeu apos receber a msg
        clicked   — lead clicou em link/oferta
        paid      — lead converteu (PaymentEventReceipt)
        custom    — definido por callback

    status:
        running              — coletando dados
        completed_winner_a   — A venceu por significancia
        completed_winner_b   — B venceu por significancia
        completed_no_diff    — sem diferenca apos N>=500
        stopped_manual       — admin parou
    """
    __tablename__ = "flow_node_experiments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    flow_id = Column(Integer, nullable=True, index=True)
    flow_slug = Column(String(120), nullable=True, index=True)
    node_id = Column(String(120), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    variant_a_text = Column(Text, nullable=False)
    variant_b_text = Column(Text, nullable=False)
    split_pct = Column(Integer, default=50, nullable=False)  # % do A
    winning_event = Column(String(40), default="responded", nullable=False)
    min_sample_size = Column(Integer, default=50, nullable=False)
    confidence_threshold = Column(Float, default=0.95, nullable=False)
    started_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    winner_picked_at = Column(DateTime(timezone=True), nullable=True)
    winner = Column(String(1), nullable=True)  # 'A' or 'B'
    p_value = Column(Float, nullable=True)
    lift_pct = Column(Float, nullable=True)
    status = Column(String(30), default="running", nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class FlowNodeExperimentAssignment(Base):
    """
    Lead foi assignado a uma variante (Frente 3.28).
    Conversao detectada via WaPhoneTenantBinding ou Mensagem subsequente.
    """
    __tablename__ = "flow_node_experiment_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "lead_id", name="uq_exp_lead"),
    )

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer, ForeignKey("flow_node_experiments.id"), nullable=False, index=True,
    )
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    variant = Column(String(1), nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    converted = Column(Boolean, default=False, nullable=False, index=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)


class SpiritualGlossaryTerm(Base):
    """
    Glossario espiritual injetado no system prompt do GPT (Frente 4.21).

    Reduz alucinacao de termos: "egum" != "agua", "Pomba-gira" != generico.
    Tabela suporta termos globais (tenant_id null) + custom por tenant.
    """
    __tablename__ = "spiritual_glossary"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)  # null = global
    term = Column(String(100), nullable=False, index=True)
    definition = Column(Text, nullable=False)
    category = Column(String(40), nullable=True)  # afro|crista|astrologia|tarot|geral
    usage_examples = Column(JSON, nullable=True)  # [{example, context}]
    importance = Column(Integer, default=5, nullable=False)  # 1-10, ordena no prompt
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class SpiritualDate(Base):
    """
    Datas espirituais/ritos (Frente 4.22).

    Recurring rule:
        annual_fixed   — mesmo dia/mes todo ano (ex: 2/2 Iemanja)
        annual_movable — varia por ano (Pascoa, Samhain por equinocio)
        lunar          — atrelado a fase lunar (calculado em tempo real)
    """
    __tablename__ = "spiritual_dates"

    id = Column(Integer, primary_key=True, index=True)
    tradition = Column(String(40), nullable=False, index=True)  # crista|afro|paga|astronomica|pessoal
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    recurring = Column(String(20), default="annual_fixed", nullable=False)
    month = Column(Integer, nullable=True)  # 1-12 para annual_fixed
    day = Column(Integer, nullable=True)    # 1-31 para annual_fixed
    fixed_date = Column(Date, nullable=True)  # caso especifico (ex: eclipse 2026)
    tenant_id = Column(String(64), nullable=True, index=True)  # null = global; senao custom do tenant
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class LeadAuraImage(Base):
    """Aura semanal gerada via Stable Diffusion (Frente 4.18)."""
    __tablename__ = "lead_aura_images"
    __table_args__ = (
        UniqueConstraint("lead_id", "week_id", name="uq_aura_lead_week"),
    )

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    signo = Column(String(20), nullable=False)
    week_id = Column(String(10), nullable=False, index=True)  # YYYY-Www
    image_url = Column(String(800), nullable=False)
    prompt = Column(Text, nullable=True)
    provider = Column(String(40), nullable=False)
    sent_to_lead = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class ScheduledReading(Base):
    """
    Tiragem agendada (Frente 4.28).

    Lead pede "quero tiragem na proxima lua cheia" → cria registro com
    scheduled_for absoluto. Cron horario verifica vencidos:
        - 1h antes: envia "preparando sua tiragem..."
        - Hora certa: roda tiragem automatica + envia leitura

    trigger_type:
        lunar_full     — proxima lua cheia
        lunar_new      — proxima lua nova
        date_specific  — data/hora exata
        sign_transit   — V2 (Sol entrando em signo)

    status:
        pending           — aguardando hora
        warning_sent      — msg "preparando" ja enviou (1h antes)
        completed         — tiragem rodou + entregue
        cancelled         — lead pediu cancelar
        failed            — erro processando
    """
    __tablename__ = "scheduled_readings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    trigger_type = Column(String(40), nullable=False)
    spread_type = Column(String(40), default="3card", nullable=False)
    deck_id = Column(String(40), default="marselha", nullable=False)
    question = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    warning_sent_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    reading_id = Column(Integer, ForeignKey("tarot_readings.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc, nullable=False,
    )


class DailyPersonalMessage(Base):
    """
    Mensagem do dia personalizada por lead (Frente 4.27).

    Diferente de DailyHoroscope (per-signo, compartilhada), esta e unica
    por lead e gera uma vez por dia via Gemini com contexto rico
    (signo + lua + intencao + nome).

    Idempotente: (tenant_id, lead_id, date) e unique.
    """
    __tablename__ = "daily_personal_messages"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "lead_id", "date",
            name="uq_dpm_tenant_lead_date",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    text = Column(Text, nullable=False)
    source = Column(String(40), nullable=False)  # gemini|fallback|manual
    status = Column(String(20), default="generated", nullable=False)  # generated|sent|failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    chars_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


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

# ─── MÓDULO B2C MARKETPLACE (FRENTE 10.0 - O IFOOD DA ESPIRITUALIDADE) ───────

class ExpertService(Base):
    """
    Catálogo: Serviços e produtos que o Expert (Tenant) oferece na vitrine.
    Usado no perfil público, marketplace B2C e agendamentos.
    """
    __tablename__ = "expert_services"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(300), nullable=True)  # resumo p/ cards
    service_type = Column(String(32), default="live_reading", nullable=False)
    # live_reading, digital_product, therapy, coaching, reiki, ceremony, tarot, consultation

    # Preço e duração
    price_cents = Column(Integer, default=0, nullable=False)  # em centavos
    original_price_cents = Column(Integer, nullable=True)  # preço original (para promoção)
    duration_minutes = Column(Integer, nullable=True)

    # Classificação
    category = Column(String(32), nullable=True)
    # tarot, terapia, coaching, astrologia, reiki, ritual, meditacao, constelacao
    modality = Column(String(16), default="online")  # online, in_person, both

    # Visual
    cover_image_url = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)  # ordenação na vitrine

    # Disponibilidade
    is_active = Column(Boolean, default=True, nullable=False)
    max_per_day = Column(Integer, nullable=True)  # limite de atendimentos/dia

    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

class ConsumerProfile(Base):
    """
    Consumidor Final (B2C): Identidade global para acessar o App/Área de Membros.
    Pode estar vinculado a vários Leads de diferentes Experts.
    """
    __tablename__ = "consumer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(32), nullable=False, unique=True)
    email = Column(String(128), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=True)
    name = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

class ConsumerPurchase(Base):
    """
    Compra do consumidor no Marketplace B2C.
    """
    __tablename__ = "consumer_purchases"

    id = Column(Integer, primary_key=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("expert_services.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True) # Expert que vendeu
    amount_paid_cents = Column(Integer, nullable=False)
    status = Column(String(32), default="pending", nullable=False) # pending, approved, refunded
    purchased_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

class ExpertScheduleSlot(Base):
    """
    Motor de Calendário: Slots de disponibilidade do Expert.
    O terapeuta define seus horários disponíveis; o lead/consumidor reserva.
    """
    __tablename__ = "expert_schedule_slots"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    slot_date = Column(Date, nullable=False, index=True)  # data do slot
    slot_time = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)  # bloqueio manual

    # Quem reservou
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    purchase_id = Column(Integer, ForeignKey("consumer_purchases.id"), nullable=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)

    # Recorrência (semanal)
    recurrence_rule = Column(String(32), nullable=True)  # weekly, biweekly, none
    recurrence_group_id = Column(String(64), nullable=True)  # agrupa slots recorrentes

    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class Appointment(Base):
    """
    Agendamento: reserva confirmada de uma consulta/sessão.
    Ligada a um slot, lead, serviço e pagamento.
    """
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    slot_id = Column(Integer, ForeignKey("expert_schedule_slots.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("expert_services.id"), nullable=True)

    # Dados do cliente
    client_name = Column(String(128), nullable=True)
    client_phone = Column(String(32), nullable=True)
    client_email = Column(String(128), nullable=True)

    # Horário
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=60)
    timezone_str = Column(String(48), default="America/Sao_Paulo")

    # Tipo
    appointment_type = Column(String(32), default="consultation", nullable=False)
    # consultation, tarot_reading, therapy, coaching, reiki, ceremony
    modality = Column(String(16), default="online", nullable=False)  # online, in_person
    meeting_url = Column(Text, nullable=True)  # link do Google Meet/Zoom

    # Status
    status = Column(String(24), default="pending", nullable=False)
    # pending → confirmed → in_progress → completed → cancelled → no_show
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)

    # Pagamento
    amount_cents = Column(Integer, default=0)
    payment_method = Column(String(16), nullable=True)
    payment_id = Column(String(128), nullable=True)
    payment_status = Column(String(16), default="pending")  # pending, paid, refunded

    # Notas
    notes_before = Column(Text, nullable=True)  # notas do cliente antes da sessão
    notes_after = Column(Text, nullable=True)   # notas do terapeuta pós-sessão

    # Lembrete
    reminder_sent = Column(Boolean, default=False)
    reminder_24h_sent = Column(Boolean, default=False)

    # Recorrência
    subscription_id = Column(Integer, ForeignKey("client_subscriptions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class ClientSubscription(Base):
    """
    Assinatura do cliente final com o terapeuta.
    Ex: "Pacote mensal de 4 sessões de terapia" ou "Acompanhamento semanal".
    """
    __tablename__ = "client_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("expert_services.id"), nullable=True)

    # Dados do assinante
    client_name = Column(String(128), nullable=True)
    client_phone = Column(String(32), nullable=True)

    # Plano
    plan_name = Column(String(128), nullable=False)  # "Pacote Mensal 4 Sessões"
    frequency = Column(String(16), default="monthly", nullable=False)
    # weekly, biweekly, monthly, quarterly
    sessions_per_period = Column(Integer, default=4, nullable=False)  # sessões por período
    sessions_used = Column(Integer, default=0, nullable=False)

    # Preço
    price_cents = Column(Integer, default=0, nullable=False)
    currency = Column(String(3), default="BRL")

    # Status
    status = Column(String(16), default="active", nullable=False)
    # active, paused, cancelled, expired
    starts_at = Column(DateTime(timezone=True), nullable=False)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Pagamento recorrente
    payment_method = Column(String(16), nullable=True)
    stripe_subscription_id = Column(String(128), nullable=True)

    # Preferências
    preferred_day = Column(String(16), nullable=True)  # monday, tuesday...
    preferred_time = Column(String(8), nullable=True)   # "14:00"

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

class MemberAreaAsset(Base):
    """
    O Cofre de Entregáveis B2C: Áudios, PDFs, e vídeos comprados/gerados.
    """
    __tablename__ = "member_area_assets"

    id = Column(Integer, primary_key=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True) # Expert que gerou
    asset_type = Column(String(32), nullable=False) # reading_audio, therapy_video, ebook
    title = Column(String(128), nullable=False)
    content_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class PublicApiKey(Base):
    """
    API keys para acesso público à infraestrutura de astrologia/numerologia/tarot.
    Vertical 2: "Vender picaretas" — AaaS (Astrology as a Service).

    Tiers: free (100/dia), pro (10K/dia), scale (1M/dia).
    """
    __tablename__ = "public_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    label = Column(String(128), nullable=False)  # "Meu App de Horóscopo"
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    key_prefix = Column(String(12), nullable=False)  # "mm_pk_a3b2" (para identificação visual)
    tier = Column(String(16), nullable=False, default="free")  # free, pro, scale
    is_active = Column(Boolean, default=True, nullable=False)
    daily_usage = Column(JSON, default=dict)  # {"2027-01-15": 42}
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class RitualLog(Base):
    """
    Log de rituais diários completados — Vertical 5: Curador de Rituais.
    Trackeia streak, engajamento e preferências do usuário B2C.
    """
    __tablename__ = "ritual_logs"

    id = Column(Integer, primary_key=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    ritual_type = Column(String(32), nullable=False)  # breathing, mantra, meditation, intention
    duration_seconds = Column(Integer, nullable=True)
    mood_before = Column(String(32), nullable=True)  # ansioso, triste, grato, motivado
    mood_after = Column(String(32), nullable=True)
    moon_phase = Column(String(32), nullable=True)
    sign = Column(String(32), nullable=True)
    ritual_data = Column(JSON, default=dict)  # detalhes do ritual gerado
    completed_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# BROADCAST & SEGMENTAÇÃO — Grupos de Lançamento
# ═══════════════════════════════════════════════════════════════════════

class BroadcastCampaign(Base):
    """
    Campanha de broadcast: envio segmentado em massa via WhatsApp.
    Resolve: lançamentos, divulgação de retiros, promoções, nurturing.
    """
    __tablename__ = "broadcast_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message_text = Column(Text, nullable=False)
    message_media_url = Column(Text, nullable=True)  # imagem/vídeo anexado
    message_media_type = Column(String(16), nullable=True)  # image, video, document

    # Segmentação (filtros JSON)
    segment_filters = Column(JSON, default=dict)
    # Exemplos de filtros:
    #   {"tags": ["vip", "retiro"], "score_band": ["hot", "warm"],
    #    "signo": ["leao", "touro"], "bot_ativo": false}

    status = Column(String(24), default="draft", nullable=False, index=True)
    # draft → scheduled → sending → completed → cancelled
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # agendar envio

    # Métricas
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)  # quantos responderam

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class BroadcastRecipient(Base):
    """Log de cada destinatário de uma campanha broadcast."""
    __tablename__ = "broadcast_recipients"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("broadcast_campaigns.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    status = Column(String(16), default="pending", nullable=False)
    # pending → sent → delivered → failed → replied
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_reason = Column(String(200), nullable=True)


# ═══════════════════════════════════════════════════════════════════════
# EVENTOS & RETIROS — Vagas limitadas, inscrição, lista de espera
# ═══════════════════════════════════════════════════════════════════════

class Event(Base):
    """
    Evento do profissional: retiro, workshop, vivência, curso presencial.
    Suporta vagas limitadas, lista de espera e parcelamento.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(32), default="retreat", nullable=False)
    # retreat, workshop, ceremony, webinar, course

    # Localização
    location_name = Column(String(200), nullable=True)  # "Casa de Retiros Sol Nascente"
    location_address = Column(Text, nullable=True)
    is_online = Column(Boolean, default=False, nullable=False)
    online_url = Column(Text, nullable=True)  # link do meet/zoom

    # Datas
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)

    # Vagas
    max_spots = Column(Integer, nullable=True)  # null = ilimitado
    spots_taken = Column(Integer, default=0, nullable=False)
    waitlist_enabled = Column(Boolean, default=True, nullable=False)

    # Preço
    price_cents = Column(Integer, default=0, nullable=False)
    currency = Column(String(3), default="BRL", nullable=False)
    installments_max = Column(Integer, default=1, nullable=False)  # parcelas
    early_bird_price_cents = Column(Integer, nullable=True)
    early_bird_deadline = Column(DateTime(timezone=True), nullable=True)

    # Visual
    cover_image_url = Column(Text, nullable=True)

    # Status
    status = Column(String(24), default="draft", nullable=False)
    # draft → published → sold_out → in_progress → completed → cancelled
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Metadados extras
    metadata_json = Column(JSON, default=dict)
    # Ex: {"includes": ["alimentação", "hospedagem"], "requirements": ["levar almofada"]}

    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class EventRegistration(Base):
    """Inscrição de um lead/consumidor em um evento."""
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)

    # Dados do inscrito
    name = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)

    status = Column(String(24), default="pending", nullable=False)
    # pending → confirmed → waitlisted → cancelled → attended → no_show
    is_waitlist = Column(Boolean, default=False, nullable=False)

    # Pagamento
    amount_paid_cents = Column(Integer, default=0)
    payment_method = Column(String(16), nullable=True)  # pix, stripe, cash
    payment_id = Column(String(128), nullable=True)  # external ref

    notes = Column(Text, nullable=True)  # observações do profissional
    registered_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# CUPONS DE DESCONTO
# ═══════════════════════════════════════════════════════════════════════

class Coupon(Base):
    """
    Cupom de desconto aplicável a serviços, eventos ou infoprodutos.
    """
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    code = Column(String(32), nullable=False, index=True)  # "RETIRO10"
    discount_type = Column(String(12), nullable=False, default="percent")  # percent, fixed
    discount_value = Column(Integer, nullable=False)  # 10 = 10% ou R$10
    applies_to = Column(String(24), nullable=True)  # event, service, content, all
    target_id = Column(Integer, nullable=True)  # ID específico do evento/serviço
    max_uses = Column(Integer, nullable=True)  # null = ilimitado
    used_count = Column(Integer, default=0, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# CONTEÚDO DIGITAL — Infoprodutos
# ═══════════════════════════════════════════════════════════════════════

class ContentAsset(Base):
    """
    Infoproduto: e-book, meditação gravada, curso em vídeo, etc.
    Produto digital vendável com entrega automática.
    """
    __tablename__ = "content_assets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(String(32), nullable=False, default="ebook")
    # ebook, meditation_audio, video_course, worksheet, oracle_deck

    # Preço
    price_cents = Column(Integer, default=0, nullable=False)
    is_free = Column(Boolean, default=False, nullable=False)

    # Arquivos
    file_url = Column(Text, nullable=True)  # URL do arquivo principal
    cover_image_url = Column(Text, nullable=True)
    preview_url = Column(Text, nullable=True)  # preview gratuito

    # Entrega
    delivery_method = Column(String(24), default="download", nullable=False)
    # download, streaming, whatsapp_send, email
    delivery_message = Column(Text, nullable=True)  # mensagem pós-compra

    # Status
    status = Column(String(16), default="draft", nullable=False, index=True)  # draft, published, archived
    total_sales = Column(Integer, default=0, nullable=False)
    total_revenue_cents = Column(Integer, default=0, nullable=False)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False, index=True)


class ContentPurchase(Base):
    """Compra de um infoproduto — link de acesso gerado."""
    __tablename__ = "content_purchases"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_assets.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    amount_paid_cents = Column(Integer, default=0)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=True)
    payment_method = Column(String(16), nullable=True)
    payment_id = Column(String(128), nullable=True)
    status = Column(String(16), default="pending", nullable=False)  # pending, paid, refunded
    access_token = Column(String(64), nullable=True, unique=True)  # token de acesso único
    delivered = Column(Boolean, default=False, nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    purchased_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# PERFIL PÚBLICO DO PROFISSIONAL — Landing Page
# ═══════════════════════════════════════════════════════════════════════

class ExpertProfile(Base):
    """
    Página pública do terapeuta/oraculista.
    Acessível sem login: /p/<slug>
    """
    __tablename__ = "expert_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slug = Column(String(64), nullable=False, unique=True, index=True)  # "ana-tarologa"

    # Bio
    display_name = Column(String(128), nullable=False)
    headline = Column(String(200), nullable=True)  # "Taróloga & Terapeuta Holística"
    bio = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)

    # Especialidades (JSON array)
    specialties = Column(JSON, default=list)
    # ["tarot", "reiki", "terapia_floral", "astrologia", "coaching"]

    # Contato (visível na página)
    city = Column(String(64), nullable=True)
    state = Column(String(2), nullable=True)
    instagram = Column(String(64), nullable=True)
    whatsapp_display = Column(String(20), nullable=True)

    # Configurações
    show_services = Column(Boolean, default=True)
    show_testimonials = Column(Boolean, default=True)
    show_calendar = Column(Boolean, default=True)
    accept_online = Column(Boolean, default=True)
    accept_in_person = Column(Boolean, default=False)

    # SEO
    meta_title = Column(String(120), nullable=True)
    meta_description = Column(String(300), nullable=True)

    # Métricas
    total_views = Column(Integer, default=0)
    total_bookings = Column(Integer, default=0)

    # Estilo visual
    theme_color = Column(String(7), default="#7C3AED")  # cor primária
    custom_css = Column(Text, nullable=True)

    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class ExpertTestimonial(Base):
    """Depoimento de cliente na página pública."""
    __tablename__ = "expert_testimonials"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("expert_profiles.id"), nullable=False, index=True)
    client_name = Column(String(128), nullable=False)
    client_avatar_url = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    rating = Column(Integer, default=5)  # 1-5
    service_type = Column(String(32), nullable=True)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# DIÁRIO ESPIRITUAL — Journaling
# ═══════════════════════════════════════════════════════════════════════

class JournalEntry(Base):
    """
    Entrada do diário espiritual do consumidor/lead.
    Journaling guiado com IA + tracking de humor + rituais.
    """
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True, index=True)

    # Conteúdo
    entry_type = Column(String(24), default="free", nullable=False)
    # free, gratitude, intention, reflection, dream, affirmation, moon_ritual
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)

    # Contexto espiritual
    mood = Column(String(32), nullable=True)  # ansioso, grato, motivado, triste, esperançoso
    energy_level = Column(Integer, nullable=True)  # 1-10
    moon_phase = Column(String(32), nullable=True)
    tarot_card = Column(String(64), nullable=True)  # carta do dia se fez tiragem
    sign = Column(String(32), nullable=True)

    # IA
    ai_prompt = Column(Text, nullable=True)    # prompt guiado que gerou a entrada
    ai_insight = Column(Text, nullable=True)   # reflexão da IA sobre a entrada

    # Tags
    tags = Column(JSON, default=list)  # ["sonhos", "relacionamento", "cura"]

    # Privacidade
    is_private = Column(Boolean, default=True)

    # Streaks
    streak_day = Column(Integer, default=1)  # dia consecutivo

    entry_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# TRILHAS DE APRENDIZADO — Learning Paths + Gamificação
# ═══════════════════════════════════════════════════════════════════════

class LearningTrail(Base):
    """
    Trilha de aprendizado: 7 dias de meditação, 21 dias de autoconhecimento, etc.
    Criada pelo terapeuta ou pela plataforma.
    """
    __tablename__ = "learning_trails"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)  # null = global
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)

    category = Column(String(32), default="spiritual", nullable=False)
    # spiritual, meditation, tarot, astrology, healing, mindfulness
    difficulty = Column(String(16), default="beginner")  # beginner, intermediate, advanced
    duration_days = Column(Integer, default=7, nullable=False)

    # Gamificação
    xp_reward = Column(Integer, default=100)  # XP ao completar
    badge_name = Column(String(64), nullable=True)  # "Mestre da Lua"
    badge_icon = Column(String(32), nullable=True)  # emoji ou icon name

    # Status
    is_published = Column(Boolean, default=False)
    total_enrollments = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)

    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


class TrailStep(Base):
    """Passo individual dentro de uma trilha."""
    __tablename__ = "trail_steps"

    id = Column(Integer, primary_key=True, index=True)
    trail_id = Column(Integer, ForeignKey("learning_trails.id"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)  # dia 1, 2, 3...
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)  # texto/markdown do conteúdo
    content_type = Column(String(24), default="text", nullable=False)
    # text, meditation, exercise, journal_prompt, tarot_draw, reflection, quiz

    # Mídia
    media_url = Column(Text, nullable=True)  # áudio/vídeo do passo
    media_type = Column(String(16), nullable=True)

    # Ação requerida
    action_type = Column(String(24), nullable=True)
    # journal_write, meditate_minutes, draw_card, answer_quiz, reflect
    action_config = Column(JSON, default=dict)
    # Ex: {"min_words": 50} ou {"meditate_minutes": 10} ou {"question": "..."}

    xp_reward = Column(Integer, default=10)
    sort_order = Column(Integer, default=0)


class TrailEnrollment(Base):
    """Matrícula de um usuário numa trilha."""
    __tablename__ = "trail_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    trail_id = Column(Integer, ForeignKey("learning_trails.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    tenant_id = Column(String(64), nullable=True, index=True)

    current_day = Column(Integer, default=1)
    completed_steps = Column(JSON, default=list)  # [1, 2, 3] - step IDs concluídos
    total_xp = Column(Integer, default=0)
    streak_count = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)

    status = Column(String(16), default="active")  # active, completed, abandoned
    started_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), default=_agora_utc)


class UserBadge(Base):
    """Badge/conquista desbloqueada pelo usuário."""
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumer_profiles.id"), nullable=True)
    tenant_id = Column(String(64), nullable=True, index=True)

    badge_name = Column(String(64), nullable=False)  # "Mestre da Lua"
    badge_icon = Column(String(32), nullable=True)
    badge_type = Column(String(24), nullable=False)
    # trail_completion, streak_7, streak_21, streak_40, journal_50, first_tarot
    description = Column(String(200), nullable=True)
    xp_earned = Column(Integer, default=0)
    trail_id = Column(Integer, ForeignKey("learning_trails.id"), nullable=True)

    earned_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# LAUNCH MANAGER — Gerenciamento de Lançamentos com Grupos WhatsApp
# ═══════════════════════════════════════════════════════════════════════

class LaunchCampaign(Base):
    """Lançamento completo com fases agendadas."""
    __tablename__ = "launch_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    group_jid = Column(String(100), nullable=True)  # ID do grupo WhatsApp
    device_id = Column(Integer, ForeignKey("wa_devices.id"), nullable=True, index=True)  # Qual dispositivo WA usar
    product_name = Column(String(200), nullable=True)
    link_vendas = Column(String(500), nullable=True)
    preco_lancamento = Column(String(20), nullable=True)
    preco_normal = Column(String(20), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="draft")  # draft, active, paused, completed
    variables = Column(JSON, default=dict)  # variáveis customizadas
    created_at = Column(DateTime(timezone=True), default=_agora_utc, nullable=False)

    phases = relationship("LaunchPhase", back_populates="launch", cascade="all, delete-orphan")
    device = relationship("WADevice", foreign_keys=[device_id])


class LaunchPhase(Base):
    """Fase individual de um lançamento (aquecimento, abertura, escassez, etc)."""
    __tablename__ = "launch_phases"

    id = Column(Integer, primary_key=True, index=True)
    launch_id = Column(Integer, ForeignKey("launch_campaigns.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    phase_type = Column(String(30), nullable=False)  # warmup, cart_open, reminder, scarcity, cart_close, custom
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    group_name_template = Column(String(300), nullable=True)  # nome do grupo nesta fase
    message_template = Column(Text, nullable=True)  # mensagem a enviar
    media_url = Column(String(500), nullable=True)  # URL de imagem/vídeo para enviar
    status = Column(String(20), default="pending")  # pending, executed, failed, skipped
    sort_order = Column(Integer, default=0)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    launch = relationship("LaunchCampaign", back_populates="phases")


# ═══════════════════════════════════════════════════════════════════════════
# ACTIVECAMPAIGN-INSPIRED MODELS
# ═══════════════════════════════════════════════════════════════════════════


class LeadTask(Base):
    """Tarefas vinculadas a leads (AC Task Management)."""
    __tablename__ = "lead_tasks"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(30), default="follow_up")  # follow_up, call, meeting, proposal, custom
    due_at = Column(DateTime(timezone=True), nullable=True)
    completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String(10), default="medium")  # low, medium, high, urgent
    created_at = Column(DateTime(timezone=True), default=_agora_utc)

    lead = relationship("Lead", backref="tasks")



class FlowGoal(Base):
    """Meta de conversão por flow (AC Automation Goals).
    
    Quando lead atinge o goal, sai do flow automaticamente.
    Permite medir % de conversão por automação.
    """
    __tablename__ = "flow_goals"
    __table_args__ = (UniqueConstraint("blueprint_id", "goal_key", name="uq_flow_goal_bp_key"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_key = Column(String(100), nullable=False)  # ex: "agendou", "pagou", "respondeu"
    goal_type = Column(String(30), nullable=False)  # tag_added, pipeline_stage, converted, custom
    goal_condition = Column(JSON, default=dict)  # {"tag": "intent:preco"} or {"stage": "convertido"}
    description = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


class FlowGoalHit(Base):
    """Registro de quando um lead atingiu um goal."""
    __tablename__ = "flow_goal_hits"
    __table_args__ = (UniqueConstraint("goal_id", "lead_id", name="uq_flow_goal_hit_unique"),)

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("flow_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    hit_at = Column(DateTime(timezone=True), default=_agora_utc)


class ABTestExposure(Base):
    """Registro de exposição A/B: qual variante cada lead viu num nó ab_split.

    Usado para atribuição de conversão (lookback de 48h):
    - Quando o lead converte, consultamos: "por qual variante ele passou?"
    - Permite calcular: impressões, conversões, taxa, receita por variante.
    """
    __tablename__ = "ab_test_exposures"
    __table_args__ = (
        UniqueConstraint("tenant_id", "blueprint_id", "node_id", "lead_id", name="uq_ab_exposure_lead_node"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    blueprint_id = Column(Integer, ForeignKey("flow_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(String(200), nullable=False)  # ID do nó ab_split no canvas
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    variant = Column(String(1), nullable=False)  # "A" ou "B"
    weight_a = Column(Integer, default=50)
    weight_b = Column(Integer, default=50)
    exposed_at = Column(DateTime(timezone=True), default=_agora_utc)

    # Atribuição de conversão (preenchido no lookback)
    converted = Column(Boolean, default=False, nullable=False)
    conversion_value = Column(Float, default=0.0)
    converted_at = Column(DateTime(timezone=True), nullable=True)


class ConversionEvent(Base):
    """Registro de conversão com atribuição (AC Conversion Attribution).
    
    Rastreia qual automação/mensagem/recipe levou à conversão.
    """
    __tablename__ = "conversion_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(30), nullable=False)  # flow, recipe, broadcast, manual, launch
    source_id = Column(String(100), nullable=True)  # ID do flow/recipe/broadcast
    source_name = Column(String(300), nullable=True)  # nome legível
    value = Column(Float, default=0.0)  # valor da conversão em R$
    currency = Column(String(3), default="BRL")
    notes = Column(Text, nullable=True)
    converted_at = Column(DateTime(timezone=True), default=_agora_utc)

    lead = relationship("Lead", backref="conversions")


class CaptureWidget(Base):
    """Widget de captura embeddable (AC Forms Builder).
    
    Gera snippet JS que terapeuta coloca no site.
    Lead preenche nome + WhatsApp → entra no Meu Mistério.
    """
    __tablename__ = "capture_widgets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    widget_type = Column(String(30), default="popup")  # popup, inline, floating_bar, floating_button
    config = Column(JSON, default=dict)  # {title, subtitle, cta_text, color, position, delay_seconds}
    welcome_flow_id = Column(Integer, nullable=True)  # flow a executar quando lead entra
    active = Column(Boolean, default=True)
    leads_captured = Column(Integer, default=0)
    embed_token = Column(String(64), nullable=False, unique=True, index=True)  # token público pra embed
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


class SubscriptionPreference(Base):
    """Preferências de comunicação por lead (AC Subscription Management)."""
    __tablename__ = "subscription_preferences"
    __table_args__ = (UniqueConstraint("tenant_id", "lead_id", name="uq_sub_pref_tenant_lead"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    daily_tarot = Column(Boolean, default=True)
    promotions = Column(Boolean, default=True)
    lunar_alerts = Column(Boolean, default=True)
    rituals = Column(Boolean, default=True)
    horoscope = Column(Boolean, default=True)
    events = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)

    lead = relationship("Lead", backref="subscription_prefs")


# ═══════════════════════════════════════════════════════════════════════════
# DEVZAPP-INSPIRED MODELS
# ═══════════════════════════════════════════════════════════════════════════


class CheckoutWebhookEvent(Base):
    """Eventos de checkout recebidos via webhook (Hotmart/Kiwify/Asaas).

    Rastreia compra aprovada, boleto gerado, carrinho abandonado, PIX, reembolso.
    """
    __tablename__ = "checkout_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(30), nullable=False)  # hotmart, kiwify, asaas, stripe, manual
    event_type = Column(String(50), nullable=False)  # purchase_approved, billet_printed, cart_abandoned, pix_generated, refunded, subscription_canceled
    payload = Column(JSON, default=dict)  # raw webhook payload
    buyer_name = Column(String(200), nullable=True)
    buyer_email = Column(String(200), nullable=True)
    buyer_phone = Column(String(30), nullable=True, index=True)
    product_name = Column(String(300), nullable=True)
    product_id = Column(String(100), nullable=True)
    value = Column(Float, default=0.0)
    currency = Column(String(3), default="BRL")
    payment_method = Column(String(30), nullable=True)  # credit_card, billet, pix
    payment_url = Column(String(500), nullable=True)  # link do boleto/pix
    status = Column(String(30), default="received")  # received, processed, failed
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    automation_sent = Column(Boolean, default=False)  # se já disparou automação
    received_at = Column(DateTime(timezone=True), default=_agora_utc)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class WADevice(Base):
    """Dispositivo WhatsApp conectado (suporta N dispositivos por tenant)."""
    __tablename__ = "wa_devices"
    __table_args__ = (UniqueConstraint("tenant_id", "nickname", name="uq_wadevice_tenant_nick"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    nickname = Column(String(100), nullable=False)  # "Spanda Principal", "Suporte"
    provider = Column(String(30), nullable=False, default="evolution")  # meta_cloud, evolution, coex
    phone_display = Column(String(30), nullable=True)  # "+55 11 99999-0000"

    # Evolution credentials
    evolution_server_url = Column(String(500), nullable=True)
    evolution_instance = Column(String(100), nullable=True)
    evolution_api_key = Column(String(500), nullable=True)

    # Meta Cloud credentials
    meta_phone_number_id = Column(String(100), nullable=True)
    meta_waba_id = Column(String(100), nullable=True)
    meta_access_token = Column(String(1000), nullable=True)

    # State
    connected = Column(Boolean, default=False)
    connection_state = Column(String(30), nullable=True)  # open, close, connecting
    is_primary = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=_agora_utc)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    groups = relationship("WAGroup", backref="device", foreign_keys="WAGroup.device_id")


class WAGroup(Base):
    """Grupo de WhatsApp gerenciado (DevGrupos)."""
    __tablename__ = "wa_groups"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("wa_devices.id"), nullable=True, index=True)
    group_jid = Column(String(100), nullable=True, index=True)  # JID do grupo no WA
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    purpose = Column(String(30), default="launch")  # launch, community, vip, support
    launch_id = Column(Integer, nullable=True, index=True)  # link com LaunchCampaign
    max_members = Column(Integer, default=256)
    current_members = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    invite_link = Column(String(500), nullable=True)
    welcome_message = Column(Text, nullable=True)  # Msg automática quando entra no grupo
    exit_message = Column(Text, nullable=True)  # Msg automática quando sai (PV)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)

    messages = relationship("WAGroupMessage", backref="group", cascade="all, delete-orphan")


class WAGroupMessage(Base):
    """Mensagem agendada para grupo de WhatsApp."""
    __tablename__ = "wa_group_messages"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("wa_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    media_type = Column(String(20), nullable=True)  # text, image, video, audio, document
    media_url = Column(String(500), nullable=True)
    mention_all = Column(Boolean, default=False)  # @mencionar todos
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


class Department(Base):
    """Departamento para roteamento de atendimento (DevChat)."""
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_dept_tenant_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False)  # consultas, cursos, suporte, financeiro
    emoji = Column(String(10), nullable=True)
    description = Column(String(500), nullable=True)
    auto_reply = Column(Text, nullable=True)  # mensagem automática quando roteado
    active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


class ConversationTransfer(Base):
    """Registro de transferência de conversa entre atendentes/departamentos."""
    __tablename__ = "conversation_transfers"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    from_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    to_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    reason = Column(String(300), nullable=True)
    transferred_at = Column(DateTime(timezone=True), default=_agora_utc)


class ServiceRating(Base):
    """Avaliação pós-atendimento (NPS / 1-5 estrelas)."""
    __tablename__ = "service_ratings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    feedback = Column(Text, nullable=True)
    context = Column(String(50), nullable=True)  # consulta, atendimento, produto
    created_at = Column(DateTime(timezone=True), default=_agora_utc)

    lead = relationship("Lead", backref="ratings")


class BusinessHours(Base):
    """Horário de atendimento por tenant (DevChat)."""
    __tablename__ = "business_hours"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_bh_tenant"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    timezone = Column(String(60), default="America/Sao_Paulo")
    schedule = Column(JSON, default=dict)  # {"mon": {"start": "09:00", "end": "18:00"}, ...}
    away_message = Column(Text, nullable=True)  # mensagem fora do horário
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


class QueueEntry(Base):
    """Fila de espera de atendimento."""
    __tablename__ = "queue_entries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    position = Column(Integer, nullable=False)
    status = Column(String(20), default="waiting")  # waiting, serving, completed, abandoned
    entered_at = Column(DateTime(timezone=True), default=_agora_utc)
    served_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class TrackedLink(Base):
    """Links rastreáveis para medir cliques (DevFunil)."""
    __tablename__ = "tracked_links"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    slug = Column(String(100), nullable=False, index=True)
    destination_url = Column(String(1000), nullable=False)
    label = Column(String(200), nullable=True)
    clicks = Column(Integer, default=0)
    unique_clicks = Column(Integer, default=0)
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


class AudioTemplate(Base):
    """Templates de áudio PTT humanizado (DevVoice)."""
    __tablename__ = "audio_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)  # welcome, follow_up, offer, faq
    audio_url = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    send_as_ptt = Column(Boolean, default=True)  # Push-to-Talk (parece gravado na hora)
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


class SendingSafetyConfig(Base):
    """Configuração anti-bloqueio (delay, aquecimento) por tenant."""
    __tablename__ = "sending_safety_config"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_safety_tenant"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    min_delay_sec = Column(Integer, default=3)  # delay mínimo entre mensagens
    max_delay_sec = Column(Integer, default=15)  # delay máximo (randomizado)
    max_msgs_per_hour = Column(Integer, default=60)  # limite por hora
    max_msgs_per_day = Column(Integer, default=500)  # limite diário
    warmup_enabled = Column(Boolean, default=True)  # aquecimento gradual
    warmup_days = Column(Integer, default=7)  # dias de aquecimento
    warmup_start_pct = Column(Integer, default=20)  # % do limite no dia 1
    fake_typing_enabled = Column(Boolean, default=True)  # simular "digitando..."
    fake_typing_sec = Column(Integer, default=3)  # segundos de "digitando"
    active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), default=_agora_utc, onupdate=_agora_utc)


class GroupPoll(Base):
    """Enquete/votação em grupo WA."""
    __tablename__ = "group_polls"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("wa_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(String(500), nullable=False)
    options = Column(JSON, default=list)  # ["Opção A", "Opção B", "Opção C"]
    votes = Column(JSON, default=dict)  # {"Opção A": 12, "Opção B": 5}
    multi_select = Column(Boolean, default=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending")  # pending, sent, closed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)


# ═══════════════════════════════════════════════════════════════════════════
# JOINZAP-INSPIRED MODELS
# ═══════════════════════════════════════════════════════════════════════════


class SmartGroupLink(Base):
    """Link inteligente que distribui leads entre grupos (JoinZap)."""
    __tablename__ = "smart_group_links"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    launch_id = Column(Integer, nullable=True, index=True)
    max_per_group = Column(Integer, default=200)  # redireciona antes de lotar
    active = Column(Boolean, default=True)
    # Página de vagas encerradas
    closed_title = Column(String(300), default="Vagas Encerradas! 😢")
    closed_message = Column(Text, default="Infelizmente todas as vagas foram preenchidas. Deixe seu contato para ser avisado(a) da próxima turma!")
    closed_cta = Column(String(100), default="Quero ser avisado(a)!")
    # Tracking pixels
    fb_pixel_id = Column(String(100), nullable=True)
    ga_tracking_id = Column(String(50), nullable=True)
    # Stats
    total_clicks = Column(Integer, default=0)
    total_redirects = Column(Integer, default=0)
    total_waitlist = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_agora_utc)

    visits = relationship("GroupLinkVisit", backref="smart_link", cascade="all, delete-orphan")


class GroupLinkVisit(Base):
    """Rastreia visitas ao smart link (anti-duplicidade)."""
    __tablename__ = "group_link_visits"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    smart_link_id = Column(Integer, ForeignKey("smart_group_links.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint = Column(String(200), nullable=False, index=True)  # cookie/IP hash
    group_id = Column(Integer, ForeignKey("wa_groups.id", ondelete="SET NULL"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    visited_at = Column(DateTime(timezone=True), default=_agora_utc)

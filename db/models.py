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

    mensagens = relationship("Mensagem", back_populates="lead", lazy="dynamic", cascade="all, delete-orphan")
    eventos = relationship("EventoAudit", back_populates="lead", lazy="dynamic", cascade="all, delete-orphan")

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

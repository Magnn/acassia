import logging
import os
from functools import wraps
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

from db.database import SessionLocal
from db.models import (
    ExpertService,
    ConsumerProfile,
    ConsumerPurchase,
    MemberAreaAsset,
    ExpertScheduleSlot,
    Appointment,
    User  # Used for finding expert profiles
)
from extensions import limiter

logger = logging.getLogger(__name__)

b2c_bp = Blueprint("b2c_marketplace", __name__, url_prefix="/api/b2c")

def _agora_utc():
    return datetime.now(timezone.utc)


def _consumer_serializer():
    secret = os.getenv("B2C_TOKEN_SECRET") or os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("B2C_TOKEN_SECRET não configurado")
    return URLSafeTimedSerializer(secret, salt="meu-misterio-b2c-v1")


def _consumer_token(consumer_id: int) -> str:
    return _consumer_serializer().dumps({"consumer_id": consumer_id})


def consumer_required(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Bearer ") else ""
        if not token:
            return jsonify({"error": "consumer_auth_required"}), 401
        try:
            payload = _consumer_serializer().loads(token, max_age=60 * 60 * 24 * 30)
            g.consumer_id = int(payload["consumer_id"])
        except SignatureExpired:
            return jsonify({"error": "consumer_token_expired"}), 401
        except (BadSignature, KeyError, TypeError, ValueError):
            return jsonify({"error": "consumer_token_invalid"}), 401
        requested_id = kwargs.get("consumer_id")
        if requested_id is not None and int(requested_id) != g.consumer_id:
            return jsonify({"error": "forbidden"}), 403
        return function(*args, **kwargs)
    return decorated

# ─── CONSUMER AUTHENTICATION (B2C) ──────────────────────────────────────────

@b2c_bp.route("/auth/signup", methods=["POST"])
@limiter.limit("10/hour")
def consumer_signup():
    """Cria a identidade global do Consumidor no Super App."""
    data = request.json or {}
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "")

    if not phone or not password:
        return jsonify({"error": "Telefone e senha são obrigatórios"}), 400
    if len(password) < 8:
        return jsonify({"error": "A senha deve ter pelo menos 8 caracteres"}), 422

    db = SessionLocal()
    try:
        exists = db.query(ConsumerProfile).filter_by(phone=phone).first()
        if exists:
            return jsonify({"error": "Telefone já cadastrado"}), 409

        consumer = ConsumerProfile(
            phone=phone,
            email=email if email else None,
            password_hash=generate_password_hash(password),
            name=name
        )
        db.add(consumer)
        db.commit()
        db.refresh(consumer)

        return jsonify({
            "message": "Conta B2C criada com sucesso",
            "consumer": {"id": consumer.id, "name": consumer.name, "phone": consumer.phone},
            "access_token": _consumer_token(consumer.id),
        }), 201
    finally:
        db.close()


@b2c_bp.route("/auth/login", methods=["POST"])
@limiter.limit("10/minute")
def consumer_login():
    """Autentica o consumidor para acessar o Cofre e o Marketplace."""
    data = request.json or {}
    phone = data.get("phone", "").strip()
    password = data.get("password", "")

    db = SessionLocal()
    try:
        consumer = db.query(ConsumerProfile).filter_by(phone=phone).first()
        if not consumer or not check_password_hash(consumer.password_hash, password):
            return jsonify({"error": "Credenciais inválidas"}), 401

        return jsonify({
            "message": "Login B2C efetuado",
            "consumer": {"id": consumer.id, "name": consumer.name, "phone": consumer.phone},
            "access_token": _consumer_token(consumer.id),
        })
    finally:
        db.close()


@b2c_bp.route("/auth/me", methods=["GET"])
@consumer_required
def get_current_consumer():
    """Retorna o perfil do consumidor autenticado via Bearer Token."""
    db = SessionLocal()
    try:
        consumer = db.query(ConsumerProfile).filter_by(id=g.consumer_id).first()
        if not consumer:
            return jsonify({"error": "consumer_not_found"}), 404
        return jsonify({
            "ok": True,
            "consumer": {
                "id": consumer.id,
                "name": consumer.name,
                "phone": consumer.phone,
                "email": consumer.email,
                "created_at": consumer.created_at.isoformat() if consumer.created_at else None,
            }
        })
    finally:
        db.close()


# ─── MARKETPLACE DISCOVERY (O "iFOOD") ──────────────────────────────────────

@b2c_bp.route("/experts", methods=["GET"])
def list_experts():
    """Lista todos os Terapeutas/Especialistas disponíveis na vitrine global."""
    db = SessionLocal()
    try:
        # Puxa usuários que são experts e têm serviços ativos
        services = db.query(ExpertService.tenant_id).filter_by(is_active=True).distinct().all()
        active_tenant_ids = [s[0] for s in services]

        experts = db.query(User).filter(
            User.tenant_id.in_(active_tenant_ids),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.suspended_at.is_(None),
        ).all()
        
        result = []
        seen = set()
        for exp in experts:
            if exp.tenant_id not in seen:
                seen.add(exp.tenant_id)
                result.append({
                    "tenant_id": exp.tenant_id,
                    "name": exp.name or "Especialista",
                    # A especialidade exige um campo de perfil verificável.
                    # Não inventamos uma credencial comercial para o cliente.
                    "specialty": None,
                })

        return jsonify({"experts": result})
    finally:
        db.close()


@b2c_bp.route("/experts/<tenant_id>/services", methods=["GET"])
def list_expert_services(tenant_id):
    """Retorna a prateleira de serviços de um Expert específico."""
    db = SessionLocal()
    try:
        services = db.query(ExpertService).filter_by(tenant_id=tenant_id, is_active=True).all()
        return jsonify({"services": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "type": s.service_type,
                "price_brl": s.price_cents / 100,
                "duration_min": s.duration_minutes
            } for s in services
        ]})
    finally:
        db.close()


# ─── CONSUMER MEMBER AREA (O COFRE / ÁREA DE MEMBROS) ────────────────────────

@b2c_bp.route("/me/<int:consumer_id>/vault", methods=["GET"])
@consumer_required
def get_member_vault(consumer_id):
    """
    Retorna os conteúdos comprados (Leituras Gravadas, Terapias, PDFs)
    para o consumidor consumir estilo Netflix.
    """
    db = SessionLocal()
    try:
        assets = db.query(MemberAreaAsset).filter_by(consumer_id=consumer_id).order_by(MemberAreaAsset.created_at.desc()).all()
        return jsonify({"vault": [
            {
                "id": a.id,
                "expert_tenant_id": a.tenant_id,
                "type": a.asset_type,
                "title": a.title,
                "content_url": a.content_url,
                "unlocked_at": a.created_at.isoformat()
            } for a in assets
        ]})
    finally:
        db.close()


@b2c_bp.route("/me/<int:consumer_id>/appointments", methods=["GET"])
@consumer_required
def get_consumer_appointments(consumer_id):
    """
    Retorna a agenda do consumidor (Sessões ao vivo marcadas).
    Unifica agendamentos diretos e slots vinculados a compras sem duplicatas.
    """
    db = SessionLocal()
    try:
        consumer = db.query(ConsumerProfile).filter_by(id=consumer_id).first()
        if not consumer:
            return jsonify({"error": "consumer_not_found"}), 404

        now_utc = _agora_utc()

        # 1. Agendamentos diretos associados ao consumer_id ou telefone
        appt_filters = [Appointment.consumer_id == consumer_id]
        if consumer.phone:
            appt_filters.append(Appointment.client_phone == consumer.phone)
        
        appts = (
            db.query(Appointment)
            .filter(or_(*appt_filters))
            .filter(Appointment.status.notin_(["cancelled"]))
            .order_by(Appointment.scheduled_at.asc())
            .all()
        )

        # 2. Slots comprados via marketplace
        purchases = db.query(ConsumerPurchase.id).filter_by(consumer_id=consumer_id).all()
        purchase_ids = [p[0] for p in purchases]
        slot_filters = [ExpertScheduleSlot.consumer_id == consumer_id]
        if purchase_ids:
            slot_filters.append(ExpertScheduleSlot.purchase_id.in_(purchase_ids))

        slots = (
            db.query(ExpertScheduleSlot)
            .filter(or_(*slot_filters))
            .order_by(ExpertScheduleSlot.slot_time.asc())
            .all()
        )

        # Prepara nomes de especialistas e serviços
        tenant_ids = {a.tenant_id for a in appts} | {s.tenant_id for s in slots}
        expert_users = db.query(User).filter(User.tenant_id.in_(tenant_ids)).all() if tenant_ids else []
        expert_name_map = {u.tenant_id: (u.name or "Especialista") for u in expert_users}

        service_ids = {a.service_id for a in appts if a.service_id}
        services = db.query(ExpertService).filter(ExpertService.id.in_(service_ids)).all() if service_ids else []
        service_title_map = {s.id: s.title for s in services}

        results = []
        seen_slot_ids = set()
        seen_appt_ids = set()

        for a in appts:
            seen_appt_ids.add(a.id)
            if a.slot_id:
                seen_slot_ids.add(a.slot_id)
            expert_name = expert_name_map.get(a.tenant_id, "Especialista")
            service_title = service_title_map.get(a.service_id, a.appointment_type or "Consulta Online")
            sched_dt = a.scheduled_at
            if sched_dt and sched_dt.tzinfo is None:
                sched_dt = sched_dt.replace(tzinfo=timezone.utc)
            results.append({
                "id": a.id,
                "slot_id": a.slot_id,
                "expert_tenant_id": a.tenant_id,
                "expert_name": expert_name,
                "title": service_title,
                "datetime": a.scheduled_at.isoformat() if a.scheduled_at else None,
                "duration_minutes": a.duration_minutes or 60,
                "status": "scheduled" if (sched_dt and sched_dt > now_utc) else "completed",
                "meeting_url": a.meeting_url,
            })

        for s in slots:
            if s.id in seen_slot_ids:
                continue
            if s.appointment_id and s.appointment_id in seen_appt_ids:
                continue
            expert_name = expert_name_map.get(s.tenant_id, "Especialista")
            slot_dt = s.slot_time
            if slot_dt and slot_dt.tzinfo is None:
                slot_dt = slot_dt.replace(tzinfo=timezone.utc)
            results.append({
                "id": None,
                "slot_id": s.id,
                "expert_tenant_id": s.tenant_id,
                "expert_name": expert_name,
                "title": "Sessão com Especialista",
                "datetime": s.slot_time.isoformat() if s.slot_time else None,
                "duration_minutes": s.duration_minutes or 60,
                "status": "scheduled" if (slot_dt and slot_dt > now_utc) else "completed",
                "meeting_url": None,
            })

        results.sort(key=lambda x: x["datetime"] or "")

        return jsonify({"appointments": results})
    finally:
        db.close()


# ─── EXPERT CATALOG MANAGEMENT (B2B) ────────────────────────────────────────

from flask_login import login_required, current_user

@b2c_bp.route("/expert/services", methods=["POST"])
@login_required
def create_expert_service():
    """O Terapeuta/Tarólogo cria um novo serviço para vender no App B2C."""
    data = request.json or {}
    title = data.get("title", "").strip()
    price_cents = data.get("price_cents", 0)
    service_type = data.get("service_type", "live_reading")

    if not title:
        return jsonify({"error": "Título é obrigatório"}), 400

    db = SessionLocal()
    try:
        service = ExpertService(
            tenant_id=current_user.tenant_id,
            title=title,
            description=data.get("description", ""),
            service_type=service_type,
            price_cents=price_cents,
            duration_minutes=data.get("duration_minutes")
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        return jsonify({"message": "Serviço criado e disponível no marketplace", "service_id": service.id}), 201
    finally:
        db.close()

@b2c_bp.route("/expert/services", methods=["GET"])
@login_required
def get_expert_services():
    """Lista todos os serviços que o Expert atual tem no catálogo."""
    db = SessionLocal()
    try:
        services = db.query(ExpertService).filter_by(tenant_id=current_user.tenant_id).all()
        return jsonify({"services": [
            {
                "id": s.id,
                "title": s.title,
                "type": s.service_type,
                "price_brl": s.price_cents / 100,
                "is_active": s.is_active
            } for s in services
        ]})
    finally:
        db.close()

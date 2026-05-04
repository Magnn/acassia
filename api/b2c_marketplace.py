import logging
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash

from db.database import SessionLocal
from db.models import (
    ExpertService,
    ConsumerProfile,
    ConsumerPurchase,
    MemberAreaAsset,
    ExpertScheduleSlot,
    User  # Used for finding expert profiles
)

logger = logging.getLogger(__name__)

b2c_bp = Blueprint("b2c_marketplace", __name__, url_prefix="/api/b2c")

def _agora_utc():
    return datetime.now(timezone.utc)

# ─── CONSUMER AUTHENTICATION (B2C) ──────────────────────────────────────────

@b2c_bp.route("/auth/signup", methods=["POST"])
def consumer_signup():
    """Cria a identidade global do Consumidor no Super App."""
    data = request.json or {}
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "")

    if not phone or not password:
        return jsonify({"error": "Telefone e senha são obrigatórios"}), 400

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

        # Em um cenário real, aqui emitiríamos um JWT.
        # Por simplicidade de arquitetura, retornamos o ID seguro para a sessão do cliente.
        return jsonify({
            "message": "Conta B2C criada com sucesso",
            "consumer": {"id": consumer.id, "name": consumer.name, "phone": consumer.phone}
        }), 201
    finally:
        db.close()


@b2c_bp.route("/auth/login", methods=["POST"])
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
            "consumer": {"id": consumer.id, "name": consumer.name, "phone": consumer.phone}
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
        # Aqui simplificamos puxando Tenants que tenham ExpertServices ativos
        services = db.query(ExpertService.tenant_id).filter_by(is_active=True).distinct().all()
        active_tenant_ids = [s[0] for s in services]

        # Em produção, enriqueceríamos isso com foto de perfil, rating e categorias
        experts = db.query(User).filter(User.tenant_id.in_(active_tenant_ids)).all()
        
        result = []
        # Evitar duplicações de tenant
        seen = set()
        for exp in experts:
            if exp.tenant_id not in seen:
                seen.add(exp.tenant_id)
                result.append({
                    "tenant_id": exp.tenant_id,
                    "name": exp.name or "Especialista Premium",
                    "specialty": "Terapia Holística e Tarot" # Mockado, viria do profile
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
def get_consumer_appointments(consumer_id):
    """
    Retorna a agenda do consumidor (Sessões ao vivo marcadas).
    """
    db = SessionLocal()
    try:
        # Busca compras do consumidor
        purchases = db.query(ConsumerPurchase.id).filter_by(consumer_id=consumer_id).all()
        purchase_ids = [p[0] for p in purchases]

        if not purchase_ids:
            return jsonify({"appointments": []})

        slots = db.query(ExpertScheduleSlot).filter(ExpertScheduleSlot.purchase_id.in_(purchase_ids)).all()
        
        return jsonify({"appointments": [
            {
                "slot_id": s.id,
                "expert_tenant_id": s.tenant_id,
                "datetime": s.slot_time.isoformat(),
                "status": "scheduled" if s.slot_time > _agora_utc() else "completed"
            } for s in slots
        ]})
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

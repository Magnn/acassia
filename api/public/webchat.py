"""
api/public/webchat.py — Webchat Widget API (Omnichannel ManyChat / ChatbotX style)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Permite incorporar um widget de chat em qualquer site/landing page de clientes SaaS:
- Cria/recupera sessão do visitante via session_id persistido no browser.
- Conecta diretamente ao motor conversacional (engine) ou suporte humano.
- Notifica o Inbox da plataforma em tempo real via SSE.
- CORS habilitado para carregamento em qualquer domínio.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, make_response
from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
webchat_bp = Blueprint("public_webchat", __name__, url_prefix="/api/public/webchat")


def _cors_response(data, status=200):
    resp = make_response(jsonify(data), status)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


@webchat_bp.route("/<path:subpath>", methods=["OPTIONS"])
@webchat_bp.route("/", methods=["OPTIONS"])
def handle_options(subpath=None):
    return _cors_response({}, 204)


@webchat_bp.route("/init", methods=["POST"])
def init_session():
    """
    Inicializa ou recupera a sessão do visitante no widget.
    Gera session_id único se não fornecido e sincroniza histórico recente.
    """
    body = request.get_json(silent=True) or {}
    tenant_id = (body.get("tenant_id") or "default").strip()
    session_id = (body.get("session_id") or "").strip()
    if not session_id:
        session_id = f"web_{uuid.uuid4().hex[:12]}"

    visitor_name = (body.get("name") or "").strip() or None
    visitor_phone = (body.get("phone") or "").strip() or None

    tel_id = visitor_phone or session_id

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            tenant_id=tenant_id, telefone=tel_id
        ).first()

        if not lead:
            tags = ["webchat"]
            custom_fields = {"channel": "webchat", "session_id": session_id}
            lead = models.Lead(
                tenant_id=tenant_id,
                telefone=tel_id,
                nome=visitor_name or "Visitante Web",
                tags=tags,
                custom_fields=custom_fields,
                metadata_json={"origem": "webchat", "session_id": session_id},
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
        else:
            tags = list(lead.tags) if isinstance(lead.tags, list) else []
            if "webchat" not in tags:
                tags.append("webchat")
                lead.tags = tags
                db.commit()

        # Carregar mensagens existentes
        msgs = db.query(models.Mensagem).filter_by(lead_id=lead.id).order_by(
            models.Mensagem.timestamp.asc()
        ).limit(50).all()

        messages_data = [{
            "id": m.id,
            "text": m.texto,
            "sender": "user" if m.remetente == "user" else "assistant",
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        } for m in msgs]

        return _cors_response({
            "ok": True,
            "session_id": session_id,
            "lead_id": lead.id,
            "bot_pausado": bool(lead.bot_pausado),
            "messages": messages_data,
        })
    except Exception as exc:
        logger.exception("[webchat] Erro em /init: %s", exc)
        return _cors_response({"error": "init_failed", "message": str(exc)}, 500)
    finally:
        db.close()


@webchat_bp.route("/message", methods=["POST"])
def send_message():
    """
    Recebe mensagem do visitante na web.
    - Se bot_pausado == False: processa pelo motor e devolve resposta.
    - Se bot_pausado == True: armazena e aguarda operador responder pelo Inbox.
    """
    body = request.get_json(silent=True) or {}
    tenant_id = (body.get("tenant_id") or "default").strip()
    session_id = (body.get("session_id") or "").strip()
    text = (body.get("text") or "").strip()

    if not session_id or not text:
        return _cors_response({"error": "missing_params", "message": "session_id e text são obrigatórios"}, 400)

    db = SessionLocal()
    try:
        # Busca lead pelo session_id ou telefone
        lead = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            (models.Lead.telefone == session_id) | (models.Lead.telefone.like(f"%{session_id}%")),
        ).first()

        if not lead:
            lead = models.Lead(
                tenant_id=tenant_id,
                telefone=session_id,
                nome="Visitante Web",
                tags=["webchat"],
                custom_fields={"channel": "webchat", "session_id": session_id},
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)

        now = datetime.now(timezone.utc)

        # 1. Salvar mensagem do visitante
        user_msg = models.Mensagem(
            lead_id=lead.id,
            remetente="user",
            texto=text,
            tipo="texto",
            timestamp=now,
        )
        db.add(user_msg)
        lead.atualizado_em = now
        db.commit()
        db.refresh(user_msg)

        # Notificar Inbox via SSE
        try:
            from api.saas.realtime_hooks import notify_message_created
            notify_message_created(tenant_id, lead.id, {
                "id": user_msg.id,
                "texto": text,
                "remetente": "user",
                "timestamp": now.isoformat(),
            })
        except Exception:
            pass

        # 2. Se o bot estiver pausado pelo operador (atendimento humano)
        if lead.bot_pausado:
            return _cors_response({
                "ok": True,
                "bot_pausado": True,
                "replies": [],
                "user_message_id": user_msg.id,
            })

        # 3. Processar mensagem via motor
        replies = []
        try:
            from flask import current_app
            motor = current_app.extensions.get("flow_engine")
            if motor:
                with SessionLocal() as engine_db:
                    result = motor.processar_mensagem(
                        telefone=lead.telefone,
                        texto_recebido=text,
                        db=engine_db,
                    )
                    # Aguarda a thread da fila persistir os balões
                    import time
                    time.sleep(0.35)

                    # Busca mensagens geradas pelo motor e salvas no banco
                    new_bot_msgs = engine_db.query(models.Mensagem).filter(
                        models.Mensagem.lead_id == lead.id,
                        models.Mensagem.id > user_msg.id,
                        models.Mensagem.remetente != "user",
                    ).order_by(models.Mensagem.timestamp.asc()).all()

                    for bm in new_bot_msgs:
                        if bm.texto and bm.texto.strip():
                            replies.append(bm.texto.strip())

                    if not replies and isinstance(result, dict):
                        reply_text = result.get("mensagem") or result.get("texto") or result.get("resposta")
                        if reply_text:
                            replies.append(reply_text)
            else:
                replies.append("Olá! Recebemos sua mensagem e entraremos em contato em breve.")
        except Exception as exc:
            logger.exception("[webchat] Erro ao processar mensagem no motor: %s", exc)
            replies.append("Olá! Recebemos sua mensagem e já estamos processando. Como posso ajudar mais?")

        # Retorna respostas para exibição imediata no widget
        return _cors_response({
            "ok": True,
            "bot_pausado": False,
            "replies": replies,
            "user_message_id": user_msg.id,
        })
    except Exception as exc:
        logger.exception("[webchat] Erro em /message: %s", exc)
        return _cors_response({"error": "message_failed", "message": str(exc)}, 500)
    finally:
        db.close()


@webchat_bp.route("/poll", methods=["GET"])
def poll_messages():
    """
    Retorna mensagens novas (útil para quando o operador responde pelo Inbox).
    Query: ?tenant_id=...&session_id=...&after_id=123
    """
    tenant_id = (request.args.get("tenant_id") or "default").strip()
    session_id = (request.args.get("session_id") or "").strip()
    after_id = int(request.args.get("after_id") or 0)

    if not session_id:
        return _cors_response({"error": "missing_session_id"}, 400)

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter(
            models.Lead.tenant_id == tenant_id,
            (models.Lead.telefone == session_id) | (models.Lead.telefone.like(f"%{session_id}%")),
        ).first()

        if not lead:
            return _cors_response({"messages": []})

        q = db.query(models.Mensagem).filter_by(lead_id=lead.id)
        if after_id > 0:
            q = q.filter(models.Mensagem.id > after_id)

        msgs = q.order_by(models.Mensagem.timestamp.asc()).limit(30).all()

        return _cors_response({
            "messages": [{
                "id": m.id,
                "text": m.texto,
                "sender": "user" if m.remetente == "user" else "assistant",
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            } for m in msgs]
        })
    finally:
        db.close()

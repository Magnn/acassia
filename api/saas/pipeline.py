"""
api/saas/pipeline.py — Pipeline Kanban + Auto-Tagging + Automation Recipes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Inspirado no ActiveCampaign:
  - Visual pipeline (Kanban) com estágios configuráveis
  - Auto-tagging baseado em IA (conteúdo das mensagens)
  - Automation recipes prontas (boas-vindas, reengajamento, upsell)
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, case

from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/saas/pipeline")

# ── PIPELINE STAGES ──────────────────────────────────────────────────────

PIPELINE_STAGES = [
    {"key": "novo",         "label": "Novo Lead",         "emoji": "🆕", "color": "#6366f1"},
    {"key": "em_conversa",  "label": "Em Conversa",       "emoji": "💬", "color": "#8b5cf6"},
    {"key": "interessado",  "label": "Interesse Mostrado", "emoji": "👀", "color": "#a855f7"},
    {"key": "proposta",     "label": "Proposta Enviada",  "emoji": "📋", "color": "#f59e0b"},
    {"key": "agendado",     "label": "Consulta Agendada", "emoji": "📅", "color": "#10b981"},
    {"key": "convertido",   "label": "Convertido",        "emoji": "💰", "color": "#22c55e"},
    {"key": "perdido",      "label": "Perdido",           "emoji": "❌", "color": "#ef4444"},
]

STAGE_KEYS = [s["key"] for s in PIPELINE_STAGES]


# ── AUTO-TAG RULES ───────────────────────────────────────────────────────

AUTO_TAG_RULES = [
    # (patterns in message, tag to apply)
    (["quanto custa", "qual o valor", "preço", "investimento", "qual valor"],
     "intent:preco"),
    (["agendar", "marcar horário", "marcar consulta", "tem horário", "agenda"],
     "intent:agendamento"),
    (["não tenho dinheiro", "caro", "tá caro", "muito caro", "sem condição"],
     "objecao:preco"),
    (["funciona mesmo", "será que funciona", "é verdade", "confiável"],
     "objecao:confianca"),
    (["obrigado", "obrigada", "gratidão", "amei", "maravilhoso", "incrível"],
     "sentimento:positivo"),
    (["ansiedade", "angústia", "angustia", "depressão", "sofrendo"],
     "sentimento:dor"),
    (["tarot", "cartas", "tiragem", "arcano"],
     "interesse:tarot"),
    (["mapa astral", "mapa natal", "astrologia", "signo"],
     "interesse:astrologia"),
    (["cristal", "cristais", "pedra", "quartzo", "ametista"],
     "interesse:cristais"),
    (["meditação", "meditar", "mantra"],
     "interesse:meditacao"),
    (["retiro", "imersão", "presencial"],
     "interesse:retiro"),
    (["urgente", "preciso agora", "socorro", "por favor me ajude"],
     "urgencia:alta"),
]


# ── AUTOMATION RECIPES ───────────────────────────────────────────────────

AUTOMATION_RECIPES = [
    {
        "id": "boas_vindas",
        "name": "Boas-Vindas Espiritual",
        "emoji": "🌟",
        "description": "Lead novo recebe tirada de tarot grátis + convite pra consulta",
        "trigger": "lead_created",
        "steps": [
            {"delay": "0m",  "action": "send_message", "text": "Olá {nome}! ✨ Sou {terapeuta}, terapeuta holística. Seja bem-vinda(o) a esta jornada!"},
            {"delay": "2m",  "action": "send_message", "text": "Preparei uma leitura especial pra você... 🔮"},
            {"delay": "5m",  "action": "tarot_reading", "spread": "carta_do_dia"},
            {"delay": "1h",  "action": "send_message", "text": "O que achou da sua leitura? Se quiser aprofundar, posso te mostrar como funciona uma consulta completa 💜"},
            {"delay": "24h", "action": "check_response", "if_no_response": "send_followup"},
        ],
        "category": "onboarding",
    },
    {
        "id": "reengajamento_lunar",
        "name": "Reengajamento Lunar",
        "emoji": "🌑",
        "description": "Lead que sumiu há 14+ dias recebe mensagem alinhada com a fase lunar",
        "trigger": "inactive_14d",
        "steps": [
            {"delay": "0m", "action": "send_message", "text": "Olá {nome}! 🌙 A {fase_lunar} está pedindo sua atenção. Senti que era hora de reconectar..."},
            {"delay": "1h", "action": "send_message", "text": "Preparei um ritual especial pra esse momento. Quer receber? 🕯️"},
        ],
        "category": "reengajamento",
    },
    {
        "id": "upsell_pos_consulta",
        "name": "Upsell Pós-Consulta",
        "emoji": "⬆️",
        "description": "3 dias após a consulta, oferecer pacote VIP ou acompanhamento",
        "trigger": "post_appointment_3d",
        "steps": [
            {"delay": "0m",  "action": "send_message", "text": "Oi {nome}! 💜 Como você está se sentindo depois da nossa sessão?"},
            {"delay": "4h",  "action": "send_message", "text": "Muitas clientes relatam que um acompanhamento semanal potencializa demais os resultados. Tenho um pacote especial de 4 sessões..."},
        ],
        "category": "upsell",
    },
    {
        "id": "aniversario_astral",
        "name": "Aniversário Astral",
        "emoji": "🎂",
        "description": "No aniversário do lead, enviar tiragem especial + oferta de mapa astral",
        "trigger": "birthday",
        "steps": [
            {"delay": "0m", "action": "send_message", "text": "Feliz aniversário, {nome}! 🎂✨ Preparei um presente especial pra você..."},
            {"delay": "1m", "action": "tarot_reading", "spread": "ano_pessoal"},
            {"delay": "2h", "action": "send_message", "text": "Quer ir mais fundo? Um Mapa Astral completo revela tudo que 2025 reserva pra você 🌟"},
        ],
        "category": "engajamento",
    },
    {
        "id": "cart_recovery",
        "name": "Recovery de Carrinho",
        "emoji": "🛒",
        "description": "Lead perguntou preço mas não comprou → follow-up com urgência",
        "trigger": "tag:intent:preco_no_purchase_4h",
        "steps": [
            {"delay": "0m",  "action": "send_message", "text": "{nome}, vi que você demonstrou interesse 💜 Posso tirar alguma dúvida?"},
            {"delay": "4h",  "action": "send_message", "text": "Tenho uma condição especial disponível até hoje. Quer saber mais? ✨"},
        ],
        "category": "conversao",
    },
    {
        "id": "pos_tarot",
        "name": "Follow-up Pós-Tarot",
        "emoji": "🃏",
        "description": "Após tiragem grátis, convida pra sessão completa",
        "trigger": "after_free_reading",
        "steps": [
            {"delay": "30m", "action": "send_message", "text": "E aí {nome}, o que achou da leitura? As cartas falam muito quando ouvimos com o coração 💜"},
            {"delay": "24h", "action": "send_message", "text": "Sabe, numa sessão completa eu consigo aprofundar muito mais e te dar orientações práticas. Quer conhecer?"},
        ],
        "category": "conversao",
    },
    {
        "id": "ritual_lua_cheia",
        "name": "Ritual de Lua Cheia",
        "emoji": "🌕",
        "description": "Todo mês na lua cheia, enviar ritual + oferta de grupo",
        "trigger": "lunar_full_moon",
        "steps": [
            {"delay": "0m",  "action": "send_message", "text": "🌕 {nome}, a Lua Cheia chegou! Momento perfeito pra liberar o que não serve mais."},
            {"delay": "5m",  "action": "send_message", "text": "Preparei um ritual de 10 minutos pra fazer hoje à noite. Quer receber? 🕯️"},
            {"delay": "1h",  "action": "send_message", "text": "Se quiser vivenciar esse ritual em grupo com minha guiança, temos um encontro especial amanhã 💜"},
        ],
        "category": "engajamento",
    },
    {
        "id": "welcome_back",
        "name": "Bem-Vindo de Volta",
        "emoji": "🔄",
        "description": "Lead que voltou a mandar mensagem após 30+ dias",
        "trigger": "reactivation",
        "steps": [
            {"delay": "0m",  "action": "send_message", "text": "Que bom ter você de volta, {nome}! ✨ Muita coisa aconteceu no universo desde nossa última conversa..."},
            {"delay": "2m",  "action": "tarot_reading", "spread": "carta_do_dia"},
        ],
        "category": "reengajamento",
    },
    {
        "id": "depoimento_request",
        "name": "Pedir Depoimento",
        "emoji": "⭐",
        "description": "7 dias após a consulta, pedir depoimento + indicação",
        "trigger": "post_appointment_7d",
        "steps": [
            {"delay": "0m", "action": "send_message", "text": "Oi {nome}! 💜 Espero que esteja sentindo os efeitos da nossa sessão."},
            {"delay": "5m", "action": "send_message", "text": "Seu feedback é muito importante pra mim. Poderia me contar em poucas palavras como foi a experiência? Isso ajuda outras pessoas que estão passando pelo mesmo 🙏"},
        ],
        "category": "fidelizacao",
    },
    {
        "id": "indicacao",
        "name": "Programa de Indicação",
        "emoji": "🤝",
        "description": "Após depoimento positivo, oferece desconto por indicação",
        "trigger": "tag:sentimento:positivo",
        "steps": [
            {"delay": "24h", "action": "send_message", "text": "{nome}, você faz parte de um grupo especial de clientes ✨ Criei uma condição exclusiva pra você: indique uma amiga e ambas ganham 20% na próxima sessão!"},
        ],
        "category": "fidelizacao",
    },
]


# ── ENDPOINTS ────────────────────────────────────────────────────────────


@pipeline_bp.route("/stages", methods=["GET"])
@login_required
def get_stages():
    """Retorna os estágios do pipeline."""
    return jsonify({"stages": PIPELINE_STAGES})


@pipeline_bp.route("/board", methods=["GET"])
@login_required
def get_board():
    """Retorna leads agrupados por estágio do pipeline (Kanban board)."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        leads = (
            db.query(models.Lead)
            .filter_by(tenant_id=tid, opt_out=False)
            .order_by(models.Lead.score_value.desc())
            .all()
        )

        board = {}
        for stage in PIPELINE_STAGES:
            board[stage["key"]] = []

        for lead in leads:
            stage = getattr(lead, 'pipeline_stage', 'novo') or 'novo'
            if stage not in board:
                stage = 'novo'

            # Count messages
            msg_count = db.query(func.count(models.Mensagem.id)).filter_by(lead_id=lead.id).scalar() or 0

            # Last message
            last_msg = (
                db.query(models.Mensagem)
                .filter_by(lead_id=lead.id)
                .order_by(models.Mensagem.timestamp.desc())
                .first()
            )

            board[stage].append({
                "id": lead.id,
                "nome": lead.nome or lead.telefone,
                "telefone": lead.telefone,
                "signo": lead.signo,
                "score_value": lead.score_value or 0,
                "score_band": lead.score_band or "cold",
                "tags": lead.tags or [],
                "spiritual_category": lead.spiritual_category,
                "pipeline_stage": stage,
                "convertido": lead.convertido,
                "bot_pausado": lead.bot_pausado,
                "msg_count": msg_count,
                "deal_value": lead.deal_value or 0,
                "win_probability": lead.win_probability or 0,
                "engagement_level": getattr(lead, 'engagement_level', 'unknown') or 'unknown',
                "preferred_hour": getattr(lead, 'preferred_hour', None),
                "last_msg": last_msg.texto[:80] if last_msg and last_msg.texto else None,
                "last_msg_at": last_msg.timestamp.isoformat() if last_msg and last_msg.timestamp else None,
                "created_at": lead.criado_em.isoformat() if lead.criado_em else None,
            })

        # Counts per stage
        stage_counts = {s["key"]: len(board[s["key"]]) for s in PIPELINE_STAGES}

        return jsonify({
            "board": board,
            "stages": PIPELINE_STAGES,
            "counts": stage_counts,
            "total": sum(stage_counts.values()),
        })
    finally:
        db.close()


@pipeline_bp.route("/move", methods=["POST"])
@login_required
def move_lead():
    """Move um lead para outro estágio do pipeline."""
    data = request.json or {}
    lead_id = data.get("lead_id")
    new_stage = data.get("stage", "").strip()

    if not lead_id or new_stage not in STAGE_KEYS:
        return jsonify({"error": "lead_id e stage válido são obrigatórios"}), 400

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id
        ).first()
        if not lead:
            return jsonify({"error": "Lead não encontrado"}), 404

        old_stage = lead.pipeline_stage or "novo"
        lead.pipeline_stage = new_stage

        # Auto-update convertido flag
        if new_stage == "convertido":
            lead.convertido = True
        elif new_stage == "perdido":
            lead.convertido = False

        db.commit()

        logger.info(
            "[pipeline] Lead %d movido: %s → %s (tenant=%s)",
            lead_id, old_stage, new_stage, current_user.tenant_id,
        )

        return jsonify({
            "ok": True,
            "lead_id": lead_id,
            "old_stage": old_stage,
            "new_stage": new_stage,
        })
    finally:
        db.close()


@pipeline_bp.route("/stats", methods=["GET"])
@login_required
def pipeline_stats():
    """Métricas do pipeline: conversão por estágio, tempo médio, etc."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Count per stage
        stage_counts = (
            db.query(
                models.Lead.pipeline_stage,
                func.count(models.Lead.id),
            )
            .filter_by(tenant_id=tid, opt_out=False)
            .group_by(models.Lead.pipeline_stage)
            .all()
        )
        counts = {row[0] or "novo": row[1] for row in stage_counts}

        # Conversion rates
        total = sum(counts.values())
        converted = counts.get("convertido", 0)
        lost = counts.get("perdido", 0)

        # Leads created last 30d
        new_30d = (
            db.query(func.count(models.Lead.id))
            .filter(
                models.Lead.tenant_id == tid,
                models.Lead.criado_em >= thirty_days_ago,
            )
            .scalar() or 0
        )

        # Avg score by stage
        avg_scores = (
            db.query(
                models.Lead.pipeline_stage,
                func.avg(models.Lead.score_value),
            )
            .filter_by(tenant_id=tid, opt_out=False)
            .group_by(models.Lead.pipeline_stage)
            .all()
        )
        scores = {row[0] or "novo": round(row[1] or 0, 1) for row in avg_scores}

        return jsonify({
            "counts": counts,
            "total": total,
            "converted": converted,
            "lost": lost,
            "conversion_rate": round(converted / max(total, 1) * 100, 1),
            "new_last_30d": new_30d,
            "avg_score_by_stage": scores,
        })
    finally:
        db.close()


# ── AUTO-TAGGING ─────────────────────────────────────────────────────────


@pipeline_bp.route("/auto-tag", methods=["POST"])
@login_required
def run_auto_tag():
    """Executa auto-tagging em todos os leads ou em um lead específico."""
    data = request.json or {}
    lead_id = data.get("lead_id")

    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        if lead_id:
            leads = [db.query(models.Lead).filter_by(id=lead_id, tenant_id=tid).first()]
            leads = [l for l in leads if l]
        else:
            leads = db.query(models.Lead).filter_by(tenant_id=tid, opt_out=False).all()

        tagged_count = 0
        for lead in leads:
            # Get last 20 messages from lead
            messages = (
                db.query(models.Mensagem)
                .filter_by(lead_id=lead.id, origem="lead")
                .order_by(models.Mensagem.timestamp.desc())
                .limit(20)
                .all()
            )

            all_text = " ".join([m.texto or "" for m in messages]).lower()
            current_tags = list(lead.tags or [])
            new_tags = []

            for patterns, tag in AUTO_TAG_RULES:
                if tag not in current_tags:
                    for pattern in patterns:
                        if pattern in all_text:
                            new_tags.append(tag)
                            break

            if new_tags:
                lead.tags = current_tags + new_tags
                tagged_count += 1

                # Auto-advance pipeline based on tags
                stage = lead.pipeline_stage or "novo"
                if stage == "novo" and any(t.startswith("intent:") for t in new_tags):
                    lead.pipeline_stage = "interessado"
                elif stage == "novo" and len(messages) >= 3:
                    lead.pipeline_stage = "em_conversa"

        db.commit()
        return jsonify({"ok": True, "leads_tagged": tagged_count, "total_checked": len(leads)})
    finally:
        db.close()


def auto_tag_lead_message(lead_id: int, message_text: str):
    """Called inline after receiving a message — tags lead in real-time."""
    if not message_text:
        return

    text_lower = message_text.lower()
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        if not lead:
            return

        current_tags = list(lead.tags or [])
        new_tags = []

        for patterns, tag in AUTO_TAG_RULES:
            if tag not in current_tags:
                for pattern in patterns:
                    if pattern in text_lower:
                        new_tags.append(tag)
                        break

        if new_tags:
            lead.tags = current_tags + new_tags

            # Auto-advance pipeline
            stage = lead.pipeline_stage or "novo"
            if stage == "novo" and any(t.startswith("intent:") for t in new_tags):
                lead.pipeline_stage = "interessado"

            db.commit()
            logger.info("[auto_tag] Lead %d: +%s", lead_id, new_tags)
    except Exception as e:
        logger.warning("[auto_tag] Error: %s", e)
    finally:
        db.close()


# ── AUTOMATION RECIPES ───────────────────────────────────────────────────


@pipeline_bp.route("/recipes", methods=["GET"])
@login_required
def list_recipes():
    """Lista todos os automation recipes disponíveis."""
    category = request.args.get("category")
    recipes = AUTOMATION_RECIPES
    if category:
        recipes = [r for r in recipes if r["category"] == category]

    categories = sorted(set(r["category"] for r in AUTOMATION_RECIPES))
    return jsonify({"recipes": recipes, "categories": categories})


@pipeline_bp.route("/recipes/<recipe_id>/preview", methods=["GET"])
@login_required
def preview_recipe(recipe_id: str):
    """Preview de um recipe com variáveis preenchidas."""
    recipe = next((r for r in AUTOMATION_RECIPES if r["id"] == recipe_id), None)
    if not recipe:
        return jsonify({"error": "Recipe não encontrado"}), 404

    # Get tenant name for {terapeuta} variable
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=current_user.id).first()
        terapeuta_name = user.name or user.email.split("@")[0] if user else "Terapeuta"

        # Preview with sample data
        sample_vars = {
            "nome": "Maria",
            "terapeuta": terapeuta_name,
            "fase_lunar": "Lua Nova",
            "signo": "Áries",
        }

        preview_steps = []
        for step in recipe["steps"]:
            s = dict(step)
            if "text" in s:
                text = s["text"]
                for k, v in sample_vars.items():
                    text = text.replace("{" + k + "}", v)
                s["text"] = text
            preview_steps.append(s)

        return jsonify({
            "recipe": recipe,
            "preview_steps": preview_steps,
            "variables": sample_vars,
        })
    finally:
        db.close()

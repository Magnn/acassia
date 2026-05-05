"""
api/saas/bot_commands.py — Interceptador de Comandos "Estilo Bot" (ex: .cartadodia, .convocar)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Inspirado em bots de gestão (como Knightbot), este módulo intercepta
mensagens que começam com "." ANTES de irem para a fila do RAG/LLM.
Isso permite funções de grupo, gamificação mística e gestão instantânea.
"""

import logging
import random
import re
import urllib.request
import json
import os
from datetime import datetime, timezone
from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)

# Arcanos Maiores para o comando .cartadodia
ARCANOS_MAIORES = [
    ("O Louco", "Novos começos, saltos de fé, espontaneidade."),
    ("O Mago", "Manifestação, criatividade, poder pessoal."),
    ("A Sacerdotisa", "Intuição, mistérios ocultos, sabedoria interior."),
    ("A Imperatriz", "Abundância, fertilidade, nutrição."),
    ("O Imperador", "Estrutura, estabilidade, autoridade."),
    ("O Hierofante", "Tradição, conhecimento espiritual, crenças."),
    ("Os Enamorados", "Escolhas, alinhamento, uniões."),
    ("O Carro", "Ação, determinação, vitória."),
    ("A Força", "Coragem, resiliência, domínio interior."),
    ("O Eremita", "Introspecção, busca por respostas, solitude."),
    ("A Roda da Fortuna", "Ciclos, mudanças, destino."),
    ("A Justiça", "Equilíbrio, verdade, causa e efeito."),
    ("O Enforcado", "Pausa, novas perspectivas, sacrifício."),
    ("A Morte", "Transformação, fim de um ciclo, renovação."),
    ("A Temperança", "Equilíbrio, moderação, paciência."),
    ("O Diabo", "Amarras, sombras, materialismo."),
    ("A Torre", "Revelações repentinas, quebra de ilusões."),
    ("A Estrela", "Esperança, fé, inspiração."),
    ("A Lua", "Ilusões, intuição profunda, medos ocultos."),
    ("O Sol", "Alegria, sucesso, vitalidade."),
    ("O Julgamento", "Renascimento, chamado interior, absolvição."),
    ("O Mundo", "Conclusão, integração, completude.")
]

def _send_wa_message(tenant_id, phone_number_id, to_number, text):
    """Envia mensagem simples via Cloud API (usado para respostas de bot)."""
    db = SessionLocal()
    try:
        sec = db.query(models.TenantFlowSecret).filter_by(
            tenant_id=tenant_id, key="whatsapp.access_token"
        ).first()
        if not sec:
            return False
            
        token = sec.value_cipher
        ver = os.getenv("META_GRAPH_API_VERSION", "v21.0")
        url = f"https://graph.facebook.com/{ver}/{phone_number_id}/messages"
        
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": text}
        }).encode()

        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error("[bot_commands] falha ao enviar: %s", e)
        return False
    finally:
        db.close()


def intercept_bot_command(texto: str, telefone: str, tenant_id: str, phone_number_id: str, raw_value: dict) -> bool:
    """
    Avalia se o texto é um comando e o executa.
    Retorna True se interceptou (a mensagem não deve ir para a IA).
    Retorna False caso contrário.
    """
    cmd = texto.strip().split()[0].lower()
    args = texto[len(cmd):].strip()
    
    if cmd == ".cartadodia":
        # Comando: Sorteia uma carta e envia no chat (pessoal ou grupo)
        carta, significado = random.choice(ARCANOS_MAIORES)
        resposta = (
            f"🃏 *A sua Carta do Dia é: {carta}*\n\n"
            f"✨ *Mensagem:* {significado}\n\n"
            f"Que esta energia guie seus passos hoje."
        )
        logger.info("[bot_commands] Comando .cartadodia acionado por %s", telefone)
        _send_wa_message(tenant_id, phone_number_id, telefone, resposta)
        return True

    elif cmd in (".convocar", ".tagall"):
        # Comando: Marca todo mundo no grupo (se suportado via Meta)
        # Por segurança, só quem envia deve ser admin, mas Cloud API não diz se é admin.
        if not args:
            args = "Atenção a este aviso importante!"
            
        resposta = f"@todos\n\n📢 {args}"
        logger.info("[bot_commands] Comando .convocar acionado por %s no grupo %s", telefone, telefone)
        # Nota: Cloud API lida com '@todos' se o WhatsApp Business Client resolver a menção (EvolutionAPI resolve 100%).
        _send_wa_message(tenant_id, phone_number_id, telefone, resposta)
        return True
        
    elif cmd == ".ping":
        # Simples ping para ver se o bot está vivo
        _send_wa_message(tenant_id, phone_number_id, telefone, "🏓 Pong! O bot está online e operante.")
        return True

    # Se não é nenhum comando conhecido, deixa a engine de IA tentar processar
    return False

"""
Seed dos flow templates pré-prontos (Frente 5.3).

Idempotente — executar várias vezes não duplica.
Run: python -m flow_templates_seed
"""

from __future__ import annotations

import logging

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


TEMPLATES: list[dict] = [
    {
        "id": "tarot-amor-express",
        "name": "Tarô do Amor Express",
        "description": "Funil rápido pra leitura focada em relacionamento. Ticket R$67, conversão alta.",
        "category": "amor",
        "ticket_brl_avg": 67,
        "blueprint_json": {
            "title": "Tarô do Amor Express",
            "version": 1,
            "nodes": [
                {"id": "1_saudacao", "type": "message", "text": "Olá querida 💜 Que ótimo te ver aqui. Sou {persona} — vou te ajudar a entender o que o universo está dizendo sobre seu amor agora. Posso?", "next": "2_pergunta"},
                {"id": "2_pergunta", "type": "input", "text": "Me conta seu nome, e em uma frase: o que você quer descobrir sobre amor agora?", "save_as": "pergunta_amor", "next": "3_validacao"},
                {"id": "3_validacao", "type": "message", "text": "Entendi, {nome}. Sinto que tem energia forte aqui — preciso fazer uma tiragem completa pra te dar uma resposta clara. Vou abrir as cartas pra você.", "next": "4_oferta"},
                {"id": "4_oferta", "type": "offer", "text": "A tiragem completa do Amor é R$67 e você recebe a leitura em áudio em até 1h. Te interessa?", "value_brl": 67, "next": "5_pix"},
                {"id": "5_pix", "type": "pix", "amount_brl": 67, "description": "Tarô do Amor Express", "next": "6_entrega"},
                {"id": "6_entrega", "type": "audio_delivery", "text": "Estou abrindo as cartas... volto em 15min com sua leitura completa em áudio."}
            ]
        },
        "agent_json": {
            "persona": {"identidade": "Tarot reader empática focada em relacionamentos", "tom": "acolhedora, mística"},
            "instrucoes": {"gerais": "Use linguagem sensível ao tema amor, evite julgamentos.", "proibicoes": "Nunca prometer reconciliação garantida. Nunca falar mal de outras pessoas."},
        },
    },
    {
        "id": "misterio-reservado",
        "name": "Mistério Reservado",
        "description": "Funil premium pra clientes recorrentes. 7 nós com qualificação profunda. Ticket R$197.",
        "category": "premium",
        "ticket_brl_avg": 197,
        "blueprint_json": {
            "title": "Mistério Reservado",
            "version": 1,
            "nodes": [
                {"id": "1_apresentacao", "type": "message", "text": "Olá. Você chegou aqui guiada — sou {persona}, e nem todo mundo é aceito no Mistério Reservado. Antes de qualquer coisa, me conta seu nome e signo, por favor.", "next": "2_qualificacao"},
                {"id": "2_qualificacao", "type": "input", "text": "Perfeito {nome}. Agora me conta: você já fez tarot antes? Foi uma experiência marcante ou superficial?", "save_as": "experiencia_anterior", "next": "3_dor"},
                {"id": "3_dor", "type": "input", "text": "Entendi. E pra ser direta: qual situação tá te tirando o sono ultimamente? Pode falar comigo, isso é sigiloso.", "save_as": "dor_atual", "next": "4_engajamento"},
                {"id": "4_engajamento", "type": "message", "text": "Sinto sua energia, {nome}. Há algo aqui que precisa ser dito profundamente. O Mistério Reservado é uma sessão completa — 30min de leitura aprofundada com mapa astral, três tiragens diferentes, e uma resposta gravada que você guarda pra sempre.", "next": "5_oferta"},
                {"id": "5_oferta", "type": "offer", "text": "O investimento é R$197. Vale o que você sente. Quer entrar?", "value_brl": 197, "next": "6_pix"},
                {"id": "6_pix", "type": "pix", "amount_brl": 197, "description": "Mistério Reservado — sessão completa"},
            ]
        },
        "agent_json": {
            "persona": {"identidade": "Tarot reader veterana, premium tier", "tom": "misteriosa, autoridade calma"},
            "instrucoes": {"gerais": "Crie sensação de exclusividade. Não responda perguntas rápidas — sempre conduz pra qualificação."},
        },
    },
    {
        "id": "mapa-astral-completo",
        "name": "Mapa Astral Completo",
        "description": "Captura nascimento (data/hora/local) e oferece análise. Ticket R$97.",
        "category": "astrologia",
        "ticket_brl_avg": 97,
        "blueprint_json": {
            "title": "Mapa Astral Completo",
            "version": 1,
            "nodes": [
                {"id": "1_saudacao", "type": "message", "text": "Olá! Sou {persona}, astróloga. Vou te oferecer hoje a leitura do seu mapa astral completo. Pra começar, preciso saber 3 coisas:", "next": "2_data"},
                {"id": "2_data", "type": "input", "text": "1️⃣ Que dia você nasceu? (DD/MM/AAAA)", "save_as": "data_nascimento", "next": "3_hora"},
                {"id": "3_hora", "type": "input", "text": "2️⃣ A que horas você nasceu? (Se não souber, mande 'manhã/tarde/noite' — eu me viro)", "save_as": "hora_nascimento", "next": "4_local"},
                {"id": "4_local", "type": "input", "text": "3️⃣ Em qual cidade você nasceu?", "save_as": "local_nascimento", "next": "5_preview"},
                {"id": "5_preview", "type": "message", "text": "Perfeito. Já vi parte do seu mapa — você tem {ascendente} no ascendente, e isso já me diz muita coisa. Quer a análise completa? Vai ter PDF + áudio explicando.", "next": "6_oferta"},
                {"id": "6_oferta", "type": "offer", "text": "O Mapa Astral Completo é R$97 e fica pronto em 24h. Topa?", "value_brl": 97, "next": "7_pix"},
                {"id": "7_pix", "type": "pix", "amount_brl": 97, "description": "Mapa Astral Completo"},
            ]
        },
        "agent_json": {
            "persona": {"identidade": "Astróloga moderna", "tom": "intuitiva + precisa"},
        },
    },
    {
        "id": "sessao-online",
        "name": "Sessão Online 1:1",
        "description": "Triagem + agendamento Cal.com + pagamento upfront. Ticket R$300.",
        "category": "premium",
        "ticket_brl_avg": 300,
        "blueprint_json": {
            "title": "Sessão Online 1:1",
            "version": 1,
            "nodes": [
                {"id": "1_saudacao", "type": "message", "text": "Olá. Você está procurando uma sessão online 1:1, certo? Sou {persona}. Antes de te oferecer um horário, preciso entender se faz sentido pra você.", "next": "2_triagem"},
                {"id": "2_triagem", "type": "input", "text": "Me fala em uma frase: o que tá te incomodando atualmente?", "save_as": "tema", "next": "3_qualificacao"},
                {"id": "3_qualificacao", "type": "input", "text": "Você já fez algum tipo de consulta antes (tarot, terapia, espiritualidade)?", "save_as": "experiencia", "next": "4_oferta"},
                {"id": "4_oferta", "type": "offer", "text": "Acho que faz total sentido. A sessão é 50min via Google Meet, R$300, eu mando o link de agendamento depois do pagamento.", "value_brl": 300, "next": "5_pix"},
                {"id": "5_pix", "type": "pix", "amount_brl": 300, "description": "Sessão Online 1:1", "next": "6_agendamento"},
                {"id": "6_agendamento", "type": "scheduling", "provider": "cal_com", "duration_min": 50}
            ]
        },
        "agent_json": {
            "persona": {"identidade": "Tarot reader sénior pra sessão 1:1", "tom": "profissional, acolhedor"},
        },
    },
    {
        "id": "recuperacao",
        "name": "Recuperação de leads inativos",
        "description": "Mensagem de win-back pra leads que sumiram. Sem oferta direta.",
        "category": "recuperacao",
        "ticket_brl_avg": 0,
        "blueprint_json": {
            "title": "Recuperação suave",
            "version": 1,
            "nodes": [
                {"id": "1_lembranca", "type": "message", "text": "{nome}, lembrei de você... 🌙 Sentei pra fazer minha tiragem hoje e sua energia voltou pra mim. Tudo bem por aí?", "next": "2_aguarda"},
                {"id": "2_aguarda", "type": "wait_response", "timeout_hours": 24, "next_no_response": "3_sem_resposta"},
                {"id": "3_sem_resposta", "type": "message", "text": "Sem pressa, querida. Quando precisar, sabe onde me achar 💜", "terminal": True}
            ]
        },
        "agent_json": {
            "persona": {"identidade": "Recuperação suave", "tom": "amigável, sem pressão"},
        },
    },
]


def seed():
    db = SessionLocal()
    inserted = 0
    updated = 0
    try:
        for tpl in TEMPLATES:
            existing = db.query(models.FlowTemplate).filter_by(id=tpl["id"]).first()
            if existing:
                # Atualiza campos pra refletir mudanças no seed
                existing.name = tpl["name"]
                existing.description = tpl["description"]
                existing.category = tpl["category"]
                existing.ticket_brl_avg = tpl["ticket_brl_avg"]
                existing.blueprint_json = tpl["blueprint_json"]
                existing.agent_json = tpl.get("agent_json")
                updated += 1
            else:
                db.add(models.FlowTemplate(
                    id=tpl["id"],
                    name=tpl["name"],
                    description=tpl["description"],
                    category=tpl["category"],
                    ticket_brl_avg=tpl["ticket_brl_avg"],
                    blueprint_json=tpl["blueprint_json"],
                    agent_json=tpl.get("agent_json"),
                    is_official=True,
                ))
                inserted += 1
        db.commit()
        logger.info(
            "[flow_templates_seed] inserted=%d updated=%d total=%d",
            inserted, updated, inserted + updated,
        )
        return inserted, updated
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    inserted, updated = seed()
    print(f"Inserted: {inserted}, Updated: {updated}")

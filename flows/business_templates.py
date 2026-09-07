"""Modelos independentes do nicho. Cada chamada produz um documento editável."""


def sales_starter(offer_name: str, description: str) -> dict:
    nodes = [
        {"id": "start", "type": "trigger", "label": "Nova conversa", "config": {}},
        {"id": "welcome", "type": "conteudo", "label": "Boas-vindas", "config": {
            "content_text": "Olá! Sou o assistente virtual. Vou ajudar você a conhecer nosso atendimento.",
            "step_name": "Apresentar o atendimento",
        }},
        {"id": "need", "type": "pergunta", "label": "Entender a necessidade", "config": {
            "question": "O que você procura e como podemos ajudar?",
            "save_to_flow_field": "necessidade", "reply_mode": "text",
        }},
        {"id": "offer", "type": "conteudo", "label": "Apresentar a oferta", "config": {
            "content_text": f"Conheça {offer_name}.\n{description}".strip(),
            "step_name": "Apresentar informações cadastradas do produto",
        }},
        {"id": "interest", "type": "pergunta", "label": "Ouvir dúvidas", "config": {
            "question": "Qual dúvida você gostaria de esclarecer antes de continuar?",
            "save_to_flow_field": "duvida_comercial", "reply_mode": "text",
        }},
        {"id": "recorded", "type": "conteudo", "label": "Confirmar registro", "config": {
            "content_text": "Obrigado! Sua dúvida ficou registrada. Nossa equipe pode continuar o atendimento por aqui.",
        }},
        {"id": "handoff", "type": "notificar_atendente", "label": "Encaminhar para a equipe", "config": {
            "message": "Atendimento comercial: {{necessidade}}. Dúvida: {{duvida_comercial}}",
            "step_name": "Pausar automação e deixar conversa aguardando atendente",
        }},
        {"id": "end", "type": "end", "label": "Encerrar etapa", "config": {}},
    ]
    for index, node in enumerate(nodes):
        node["x"] = 160 + index * 320
        node["y"] = 180
    edges = []
    for source, target in zip(nodes, nodes[1:]):
        edge = {"id": f"{source['id']}-{target['id']}", "from": source["id"], "to": target["id"]}
        if source["type"] == "pergunta":
            edge["sourceHandle"] = "resposta"
        edges.append(edge)
    for question in ("need", "interest"):
        edges.append({"id": f"{question}-timeout", "from": question, "to": "end", "sourceHandle": "timeout"})
    return {"format": "meumisterio-flow", "version": 1, "title": "Atendimento comercial inicial",
            "graph": {"nodes": nodes, "edges": edges}}

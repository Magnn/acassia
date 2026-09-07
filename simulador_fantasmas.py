"""
simulador_fantasmas.py — Versão SUPREME v5.0 (Chaos Engine)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ferramenta de testes de estresse para o Império do Meu Mistério Esmeralda.
Focado em simular o CAOS do mundo real: leads apressados, céticos,
erros gramaticais e perguntas fora de hora.

PERFIS DE TESTE AVANÇADOS:
- 'Ansioso': Pergunta o preço antes da hora. Testa o redirecionamento.
- 'Cético': Pergunta como funciona e exige provas.
- 'Ouro (Caos)': Texto longo, erros de português, cita nomes (testa Leitura Fria).
- 'Ruído': Manda apenas monossílabos para testar a barreira do Node 5.
"""

import requests
import json
import uuid
import time
import sys
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração do Destino (Servidor Flask Local)
URL_WEBHOOK = "http://127.0.0.1:5000/webhook"
URL_CAKTO = "http://127.0.0.1:5000/webhook/cakto"
APP_SECRET = os.getenv("APP_SECRET", "")

# ── ROTEIROS DE CONVERSA (CAOS SIMULADO) ────────────────────────────
FANTASMAS = {
    "1": {
        "nome": "Carlos (O Apressado)",
        "telefone": "559284979401",
        "perfil": "Pergunta o preço logo no início. Testa a capacidade da IA de não vender antes da hora e puxar para o funil.",
        "script": [
            ("text", "Oi, vi o anúncio."),
            ("text", "Meu nome é Carlos"),
            ("text", "Mas me diz logo, quanto custa o trabalho? Não quero perder tempo."),
            ("text", "Tá bom, já salvei o contato."),
            ("image", "Aqui a foto da minha mão"),
            ("text", "Eu quero saber se vou arrumar um emprego logo, me fala logo o valor de tudo.")
        ]
    },
    "2": {
        "nome": "Juliana (A Ouro/Caos Gramatical)",
        "telefone": "559284979402",
        "perfil": "Manda um texto gigante, com erros e cita terceiros (Roberto e Maria). Perfeito para forçar uma Leitura Fria profunda (Node 6).",
        "script": [
            ("text", "Oie meumisterio presiso de ajuda urgente"),
            ("text", "Juliana"),
            ("text", "ja salvei sim"),
            ("image", "ta ai a foto"),
            ("text", "Meu Mistério meu ex marido roberto saiu de casa fas 3 meses. a familia dele fez macumba pra jente, eu achei terra na porta. to sem durmir, sem comer, ele me bloqueou e ta com uma tal de maria. me ajuda a faser ele voltar manso por favor")
        ]
    },
    "3": {
        "nome": "Fernando (O Cético)",
        "telefone": "559284979403",
        "perfil": "Questiona o processo. Testa como a IA lida com objeções e explicações antes da oferta.",
        "script": [
            ("text", "Olá"),
            ("text", "Fernando"),
            ("text", "Já salvei. Mas como funciona isso? É grátis mesmo ou depois vão me cobrar?"),
            ("image", "minha mão"),
            ("text", "Sinto que nada dá certo na minha vida. Mas tenho medo de ser enganado, já caí em golpes antes. Isso funciona de verdade?")
        ]
    },
    "4": {
        "nome": "Nilson (A Parede)",
        "telefone": "559284979404",
        "perfil": "Manda o mínimo possível. Força a IA a fazer perguntas investigativas e travar o avanço.",
        "script": [
            ("text", "oi"),
            ("text", "nilson"),
            ("text", "ok"),
            ("image", "foto"),
            ("text", "ta ruim as coisas")
        ]
    },
    "5": {
        "nome": "Magno (Jornada Limpa VIP)",
        "telefone": "559284979419",
        "perfil": "Simula a jornada perfeita + Pagamento Cakto.",
        "script": [
            ("text", "Olá, quero uma consulta"),
            ("text", "Magno"),
            ("text", "Sim, já salvei"),
            ("image", "foto_mao.jpg"),
            ("text", "Sinto que meus caminhos financeiros estão amarrados. Trabalho muito, mas o dinheiro some por causa de inveja na família e não consigo prosperar.")
        ]
    }
}

# ── MOTORES DE PAYLOAD ──────────────────────────────────────────────

def gerar_payload_whatsapp(telefone, texto="", tipo="text", media_id=None):
    msg_id = f"wamid.{uuid.uuid4().hex}"
    
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1443823057400060",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "559284979419", "phone_number_id": "1126244453895124"},
                    "contacts": [{"profile": {"name": "Lead Fantasma"}, "wa_id": telefone}],
                    "messages": [{
                        "from": telefone,
                        "id": msg_id,
                        "timestamp": str(int(time.time())),
                        "type": tipo
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    msg_obj = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    
    if tipo == "text":
        msg_obj["text"] = {"body": texto}
    elif tipo == "image":
        msg_obj["image"] = {"id": media_id or "ID_IMAGEM_TESTE", "caption": texto, "mime_type": "image/jpeg"}
    elif tipo == "audio":
        msg_obj["audio"] = {"id": media_id or "ID_AUDIO_TESTE", "mime_type": "audio/ogg; codecs=opus"}

    return payload

def disparar_webhook(payload, label="WH"):
    try:
        data_json = json.dumps(payload)
        headers = {'Content-Type': 'application/json'}
        
        if APP_SECRET:
            signature = hmac.new(
                APP_SECRET.encode('utf-8'), 
                data_json.encode('utf-8'), 
                hashlib.sha256
            ).hexdigest()
            headers['X-Hub-Signature-256'] = f"sha256={signature}"

        r = requests.post(URL_WEBHOOK, data=data_json, headers=headers, timeout=10)
        status = "✅" if r.status_code == 200 else "❌"
        print(f"{status} [{label}] Status: {r.status_code} | Resposta: {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"🚨 Erro de conexão: {e}")
        return False

def simular_venda_cakto(telefone):
    print(f"\n💰 [CAKTO] Gerando notificação de venda aprovada para {telefone}...")
    payload = {
        "status": "paid",
        "customer": {"phone": telefone},
        "payment_method": "pix",
        "amount": 6000
    }
    try:
        r = requests.post(URL_CAKTO, json=payload, timeout=10)
        print(f"✅ [CAKTO] Resposta do servidor: {r.status_code}")
    except Exception as e:
        print(f"🚨 [CAKTO] Erro: {e}")

# ── LOGICA DE JORNADA VARIÁVEL ─────────────────────────────────────

def jornada_caos(persona_key):
    p = FANTASMAS[persona_key]
    tel = p['telefone']
    script = p['script']
    
    print(f"\n🚀 Iniciando Jornada CAOS para: {p['nome']}")
    print(f"Objetivo: {p['perfil']}\n")
    
    for i, (tipo, msg) in enumerate(script):
        passo_label = f"Passo {i+1} ({tipo})"
        print(f"--- 💬 O lead está a enviar: '{msg}' ---")
        
        if tipo == "image":
            disparar_webhook(gerar_payload_whatsapp(tel, msg, "image"), passo_label)
        else:
            disparar_webhook(gerar_payload_whatsapp(tel, msg), passo_label)
        
        # Pausa de 12 segundos entre as mensagens para o bot poder "pensar" e responder,
        # e para você acompanhar a resposta no Painel Dashboard
        print("⏳ Aguardando a reação do Meu Mistério (12s)... Verifique o Dashboard.")
        time.sleep(12)

    if persona_key == "5":
        print("\n--- [MAGNO ADMIN] Forçando Venda em 5 segundos ---")
        time.sleep(5)
        simular_venda_cakto(tel)

# ── INTERFACE DO USUÁRIO ───────────────────────────────────────────

def main_menu():
    while True:
        print("\n" + "═"*70)
        print("🔮 SIMULADOR DE FANTASMAS v5.0 - CHAOS ENGINE")
        print("═"*70)
        for k, v in FANTASMAS.items():
            print(f"[{k}] {v['nome']} -> {v['perfil']}")
        print("[A] Simular TODAS as personas de uma vez")
        print("[0] Sair")
        
        op = input("\nEscolha uma opção: ").upper()
        
        if op == "0": break
        
        if op == "A":
            for k in ["1", "2", "3", "4", "5"]:
                jornada_caos(k)
                print("\n" + "-"*40 + "\nPróxima persona em 3s...")
                time.sleep(3)
            continue

        if op in FANTASMAS:
            p = FANTASMAS[op]
            print(f"\n👻 Modo Interativo ou Automático: {p['nome']}")
            print("Comandos: 'auto' (rodar o script da persona), 'venda' (Cakto), 'foto', 'audio', 'voltar'")
            print("Ou digite livremente para testar a IA manualmente.")
            
            while True:
                txt = input(f"\n[{p['nome']}]: ").strip()
                
                if txt.lower() == 'voltar': break
                elif txt.lower() == 'auto': jornada_caos(op); break
                elif txt.lower() == 'venda': simular_venda_cakto(p['telefone'])
                elif txt.lower() == 'foto': disparar_webhook(gerar_payload_whatsapp(p['telefone'], "minha palma", "image"), "Foto")
                elif txt.lower() == 'audio': disparar_webhook(gerar_payload_whatsapp(p['telefone'], "", "audio"), "Audio")
                else: disparar_webhook(gerar_payload_whatsapp(p['telefone'], txt), "Msg")
        else:
            print("❌ Opção Inválida.")

if __name__ == "__main__":
    try:
        requests.get("http://127.0.0.1:5000/dashboard", timeout=2)
    except:
        print("⚠️ ALERTA: O servidor 'app.py' não está rodando na porta 5000!")
        sys.exit()
        
    main_menu()
import sqlite3
import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

conn = sqlite3.connect("meumisterio.db")
c = conn.cursor()

# Find Magnus lead ID dynamically by phone number
c.execute("SELECT id FROM leads WHERE telefone = '559284979419'")
row = c.fetchone()
if not row:
    print("🚨 Lead Magnus (559284979419) not found in the database!")
    conn.close()
    sys.exit(1)

lead_id = row[0]
print(f"Found Lead Magnus with ID: {lead_id}")

print("=== MAGNUS MESSAGES BEFORE RESET ===")
c.execute("SELECT id, remetente, texto, tipo, timestamp FROM mensagens WHERE lead_id = ? ORDER BY id", (lead_id,))
messages = c.fetchall()
for m in messages:
    print(f"ID: {m[0]} | Remetente: {m[1]} | Tipo: {m[3]} | Text: {repr(m[2])} | Time: {m[4]}")

# We want to keep the onboarding messages:
# Typically, the first few messages where the lead says "Oi", "sim", "Magnus", saves the contact.
# Let's see: we should delete any image messages (hand photo) and any text messages sent during/after Node 3.
# Looking at the message history:
# The first messages are:
# - User: "Oi" or greeting
# - Bot: Introduction
# - User: name "Magnus"
# - Bot: Vcard / contact
# - User: "sim" (contact saved)
# - Bot: Start of Node 3 (asking for photo and desabafo)
#
# Any message from ID >= 19 (where user sent the first photo/desabafo) should be deleted!
# Let's delete all messages with ID >= 18 (which is around when the hand photo was sent).
# Let's do it safely: we delete messages where remetente='user' and tipo='image' or message text contains the hand/desabafo,
# or simply delete all messages after the "sim" confirmation of saving the contact.
# Let's find the message ID of the bot's presentation or the user's "sim" to save contact.
# In Magnus's history, the message "sim" is ID 17. The first hand photo is ID 19.
# So we can safely delete all messages with ID >= 18! This deletes the hand photos and all subsequent conversation.

print("\n=== RESETTING DATABASE FOR MAGNUS ===")

# 1. Delete messages from Node 3 onwards (ID >= 18)
c.execute("DELETE FROM mensagens WHERE lead_id = ? AND id >= 18", (lead_id,))
print(f"Deleted {c.rowcount} messages from Node 3 onwards.")

# 2. Reset Lead table fields
c.execute("""
    UPDATE leads 
    SET node_atual = '3_coleta_profunda',
        estado_coleta = 'inicial',
        arquetipo = NULL,
        tempo_sofrimento = NULL,
        resumo_dor = 'Quero saber se vou ficar rico in 2026',
        desejo_oculto = NULL,
        nome_mecanismo = 'Trabalho de Firmação e Resgate nas Linhas',
        objecao_silenciosa = 'Nenhuma',
        nivel_energia = NULL,
        tom_sugerido = NULL,
        score_engajamento = 0.5,
        convertido = 0,
        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ?
""", (lead_id,))
print("Updated leads table fields.")

# 3. Clean up and reset metadata_json
c.execute("SELECT metadata_json FROM leads WHERE id = ?", (lead_id,))
meta_raw = c.fetchone()[0]
meta = json.loads(meta_raw) if meta_raw else {}

# Retain onboarding and basic info
clean_meta = {
    "nome_lead": meta.get("nome_lead", "Magnus"),
    "nome_confirmado_chat": True,
    "genero_lead": "indefinido",
    "tts_ativo": False,
    "meumisterio_fallback_last_sent": None,
    # Node 1 onboarding completed
    "node1_baloes_enviados": meta.get("node1_baloes_enviados", 4),
    "node1_modo_abertura_usado": meta.get("node1_modo_abertura_usado", "safe_contract"),
    "node1_contrato_enviado": True,
    # Node 2 contact completed
    "node2_contrato_enviado": True,
    "node2_vcard_despachado": True,
    "node2_contexto_card_enviado": True,
    "lead_contato_salvo_declarado": True,
    "node2_contato_ja_reconhecido": True,
    # Reset Node 3 state completely
    "node3_estado": "inicial",
    "node3_contrato_enviado": False,
    "foto_recebida": False,
    "desabafo_recebido": False,
    "node3_tentativas_c1": 0,
    "node3_tentativas_c2": 0,
    "node3_tentativas_c3": 0,
    "desabafo_original": "",
    "desejo_declarado": "",
    "aproprofundamento_texto": "",
    "node3_aprofundamento_acumulado": "",
    "universo_desejo": "",
    "desejo_tipo": "",
    "node3_extracao_feita": False,
    "estado_coleta": "inicial"
}

c.execute("UPDATE leads SET metadata_json = ? WHERE id = ?", (json.dumps(clean_meta), lead_id))
print("Reset metadata_json cleanly.")

conn.commit()
conn.close()
print("✅ Magnus reset to Node 3 (Coleta Profunda) successfully!")


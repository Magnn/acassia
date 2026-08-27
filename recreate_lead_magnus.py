import json
import sys
from db.database import session_scope
from db.models import Lead, Mensagem

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

phone = "559284979419"

with session_scope() as db:
    # 1. Delete any existing lead with this phone
    existing_leads = db.query(Lead).filter(Lead.telefone == phone).all()
    for el in existing_leads:
        # Delete related messages first
        db.query(Mensagem).filter(Mensagem.lead_id == el.id).delete()
        db.delete(el)
    db.commit() # Commit deletions first to free up the unique constraint!
    print(f"Deleted existing leads/messages with phone {phone} and committed.")

    # 2. Create the clean metadata_json for Magnus at Node 3 starting state
    clean_meta = {
        "nome_lead": "Magnus",
        "nome_confirmado_chat": True,
        "genero_lead": "indefinido",
        "tts_ativo": False,
        "meumisterio_fallback_last_sent": None,
        # Node 1 onboarding completed
        "node1_baloes_enviados": 4,
        "node1_modo_abertura_usado": "safe_contract",
        "node1_contrato_enviado": True,
        # Node 2 contact completed
        "node2_contrato_enviado": True,
        "node2_vcard_despachado": True,
        "node2_contexto_card_enviado": True,
        "lead_contato_salvo_declarado": True,
        "node2_contato_ja_reconhecido": True,
        # Node 3 state - starting clean!
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

    # 3. Insert the new lead using SQLAlchemy model (so all defaults are populated!)
    novo_lead = Lead(
        tenant_id="default",
        telefone=phone,
        node_atual="3_coleta_profunda",
        estado_coleta="inicial",
        metadata_json=clean_meta,
        nome="Magnus",
        score_engajamento=0.5,
        convertido=False
    )
    db.add(novo_lead)
    db.flush() # Flush to get the ID generated
    
    print(f"Successfully inserted Magnus lead! New ID in database: {novo_lead.id}")

print("✅ Database ready for testing Magnus fresh from Node 3 starting state!")

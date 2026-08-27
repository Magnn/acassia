import os
import sys
from sqlalchemy import create_engine, text

# Database setup
db_url = os.getenv("DATABASE_URL", "postgresql://admin:magno_local_123@localhost:5432/meumisterio")
engine = create_engine(db_url)

# Force utf-8 stdout for emojis on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def query_db():
    with engine.connect() as conn:
        # Find messages related to "rico"
        print("--- MESSAGES CONTAINING 'rico' ---")
        result = conn.execute(text(
            "SELECT id, lead_id, remetente, texto, timestamp, tipo FROM mensagem "
            "WHERE texto LIKE :pat ORDER BY id DESC LIMIT 20"
        ), {"pat": "%rico%"})
        
        rows = result.fetchall()
        if not rows:
            print("No messages found containing 'rico'. Searching last 20 messages instead:")
            result = conn.execute(text(
                "SELECT id, lead_id, remetente, texto, timestamp, tipo FROM mensagem "
                "ORDER BY id DESC LIMIT 20"
            ))
            rows = result.fetchall()
            
        for r in rows:
            print(f"Msg ID: {r[0]} | Lead ID: {r[1]} | Remetente: {r[2]} | Time: {r[4]}")
            print(f"Content: {repr(r[3])}\n")
            
        if rows:
            lead_id = rows[0][1]
            print(f"\n--- ALL MESSAGES FOR LEAD {lead_id} ---")
            result = conn.execute(text(
                "SELECT id, remetente, texto, timestamp, tipo FROM mensagem "
                "WHERE lead_id = :lid ORDER BY id ASC"
            ), {"lid": lead_id})
            for r in result.fetchall():
                print(f"[{r[1].upper()}] ({r[3]}): {repr(r[2])}")
                
            print(f"\n--- AUDIT EVENTS FOR LEAD {lead_id} ---")
            result = conn.execute(text(
                "SELECT id, evento, dados, criado_at FROM evento_audit "
                "WHERE lead_id = :lid ORDER BY id ASC"
            ), {"lid": lead_id})
            for r in result.fetchall():
                print(f"Event: {r[1]} | Created: {r[3]}")
                print(f"Data: {r[2]}\n")

if __name__ == "__main__":
    query_db()

import sqlite3
import sys

# Force utf-8 stdout for emojis on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_messages():
    conn = sqlite3.connect("meumisterio.db")
    c = conn.cursor()
    
    lead_id = 2
    print(f"=== ALL MESSAGES FOR LEAD {lead_id} (Magnus) ===")
    c.execute(
        "SELECT id, remetente, texto, timestamp, tipo FROM mensagens "
        "WHERE lead_id = ? ORDER BY id ASC", (lead_id,)
    )
    rows = c.fetchall()
    for r in rows:
        print(f"\n[{r[1].upper()}] (ID: {r[0]} | Time: {r[3]}):")
        print(f"  {repr(r[2])}")
        
    print(f"\n=== AUDIT EVENTS FOR LEAD {lead_id} (Magnus) ===")
    c.execute(
        "SELECT id, evento, dados, criado_at FROM eventos_audit "
        "WHERE lead_id = ? ORDER BY id ASC", (lead_id,)
    )
    for r in c.fetchall():
        print(f"\nEvent: {r[1]} | Created: {r[3]}")
        print(f"  {r[2]}")
        
    conn.close()

if __name__ == "__main__":
    get_messages()

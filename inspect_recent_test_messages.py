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

print("=== MAGNUS DATABASE LEAD STATE ===")
c.execute("SELECT id, node_atual, estado_coleta, metadata_json FROM leads WHERE id = 3")
lead = c.fetchone()
if lead:
    print(f"ID: {lead[0]} | Node Atual: {lead[1]} | Estado: {lead[2]}")
    try:
        meta = json.loads(lead[3])
        print("Metadata Keys:")
        for k, v in meta.items():
            if not isinstance(v, (dict, list)) or len(str(v)) < 100:
                print(f"  {k}: {repr(v)}")
    except Exception as e:
        print("  Error parsing metadata_json:", e)

print("\n=== MESSAGE LOGS FOR MAGNUS (LEAD 3) ===")
c.execute("SELECT id, remetente, texto, tipo, timestamp FROM mensagens WHERE lead_id = 3 ORDER BY id")
for m in c.fetchall():
    print(f"ID: {m[0]} | Remetente: {m[1]} | Tipo: {m[3]} | Text: {repr(m[2])} | Time: {m[4]}")

conn.close()

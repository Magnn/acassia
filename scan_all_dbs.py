import os
import sqlite3

def scan():
    print("=== SCANNING FOR SQLITE DB FILES ===")
    for root, dirs, files in os.walk("."):
        # Skip virtual env and git dirs
        if any(p in root for p in (".git", "venv", "node_modules", "__pycache__", ".pytest_cache")):
            continue
        for f in files:
            if f.endswith((".db", ".sqlite", ".sqlite3")):
                path = os.path.join(root, f)
                print(f"\nFound SQLite File: {path} ({os.path.getsize(path)} bytes)")
                try:
                    conn = sqlite3.connect(path)
                    c = conn.cursor()
                    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [r[0] for r in c.fetchall()]
                    print("  Tables:", tables)
                    for t in tables:
                        c.execute(f"SELECT COUNT(*) FROM {t};")
                        cnt = c.fetchone()[0]
                        if cnt > 0:
                            print(f"    * {t}: {cnt} rows")
                            if t in ("mensagem", "mensagens", "lead", "leads"):
                                c.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 2")
                                print(f"      Sample rows: {c.fetchall()}")
                    conn.close()
                except Exception as e:
                    print(f"  Error reading {path}: {e}")

if __name__ == "__main__":
    scan()

import os
import sys
import psycopg2
import sqlite3

# Force utf-8 stdout for emojis on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def try_sqlite(path):
    print(f"\n--- Checking SQLite: {path} ---")
    try:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in c.fetchall()]
        print(f"  Tables found: {tables}")
        for t in tables:
            c.execute(f"SELECT COUNT(*) FROM {t};")
            cnt = c.fetchone()[0]
            if cnt > 0:
                print(f"  * Table {t}: {cnt} rows")
                if t in ("mensagem", "mensagens"):
                    c.execute(f"SELECT id, lead_id, remetente, texto FROM {t} ORDER BY id DESC LIMIT 5")
                    print(f"    Latest messages: {c.fetchall()}")
        conn.close()
    except Exception as e:
        print(f"  Error: {e}")

def try_postgres(host, port, user, password, dbname):
    print(f"\n--- Checking PG: {user}@{host}:{port}/{dbname} ---")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            connect_timeout=3
        )
        c = conn.cursor()
        c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = [r[0] for r in c.fetchall()]
        print(f"  Tables found: {tables}")
        for t in tables:
            try:
                c.execute(f"SELECT COUNT(*) FROM {t};")
                cnt = c.fetchone()[0]
                if cnt > 0:
                    print(f"  * Table {t}: {cnt} rows")
                    if t in ("mensagem", "mensagens"):
                        c.execute(f"SELECT id, lead_id, remetente, texto FROM {t} ORDER BY id DESC LIMIT 5")
                        print(f"    Latest messages: {c.fetchall()}")
            except Exception as e:
                conn.rollback()
                print(f"    Error querying table {t}: {e}")
        conn.close()
    except Exception as e:
        print(f"  Connection error: {e}")

if __name__ == "__main__":
    # Check sqlite
    try_sqlite("meumisterio.db")
    try_sqlite("db/meumisterio.db")
    try_sqlite("cigana.db")
    
    # Try various PG options
    # Port 5432
    try_postgres("localhost", 5432, "postgres", "postgres", "postgres")
    try_postgres("localhost", 5432, "postgres", "postgres", "meumisterio")
    try_postgres("localhost", 5432, "meumisterio", "meumisterio_2026_secure", "meumisterio")
    try_postgres("localhost", 5432, "admin", "magno_local_123", "meumisterio")
    
    # Port 5433 (zap-sales-postgres)
    try_postgres("localhost", 5433, "postgres", "postgres", "postgres")
    try_postgres("localhost", 5433, "postgres", "postgres", "meumisterio")
    try_postgres("localhost", 5433, "admin", "magno_local_123", "meumisterio")
    try_postgres("localhost", 5433, "admin", "magno_local_123", "postgres")
    try_postgres("localhost", 5433, "meumisterio", "meumisterio_2026_secure", "meumisterio")
    
    # Port 54322 (supabase_db_app)
    try_postgres("localhost", 54322, "postgres", "postgres", "postgres")
    try_postgres("localhost", 54322, "postgres", "postgres", "meumisterio")

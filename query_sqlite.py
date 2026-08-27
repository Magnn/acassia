import sqlite3

def list_tables(db_name):
    print(f"\n=== TABLES IN {db_name} ===")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        print("Tables:", tables)
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {t};")
            cnt = cursor.fetchone()[0]
            print(f"  - Table {t}: {cnt} rows")
    except Exception as e:
        print(f"Error querying {db_name}:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    list_tables("meumisterio.db")
    list_tables("cigana.db")

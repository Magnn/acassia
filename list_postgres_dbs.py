import psycopg2

def list_dbs(port, user, password):
    print(f"\n=== DATABASES ON PORT {port} ({user}) ===")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=port,
            user=user,
            password=password,
            database="postgres",
            connect_timeout=3
        )
        c = conn.cursor()
        c.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        dbs = [r[0] for r in c.fetchall()]
        print("Databases:", dbs)
        
        for db in dbs:
            print(f"\n  --- Exploring DB: {db} ---")
            try:
                conn_db = psycopg2.connect(
                    host="localhost",
                    port=port,
                    user=user,
                    password=password,
                    database=db,
                    connect_timeout=3
                )
                c_db = conn_db.cursor()
                c_db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                tables = [r[0] for r in c_db.fetchall()]
                print(f"  Tables in {db}: {tables}")
                for t in tables:
                    try:
                        c_db.execute(f"SELECT COUNT(*) FROM {t};")
                        cnt = c_db.fetchone()[0]
                        if cnt > 0:
                            print(f"    * Table {t}: {cnt} rows")
                            if t in ("mensagem", "mensagens"):
                                c_db.execute(f"SELECT id, lead_id, remetente, texto FROM {t} ORDER BY id DESC LIMIT 3")
                                print(f"      Latest messages: {c_db.fetchall()}")
                    except Exception as e:
                        conn_db.rollback()
                        print(f"      Error counting {t}: {e}")
                conn_db.close()
            except Exception as e:
                print(f"  Error connecting to {db}: {e}")
                
        conn.close()
    except Exception as e:
        print(f"Error connecting to postgres: {e}")

if __name__ == "__main__":
    list_dbs(5433, "postgres", "postgres")
    list_dbs(54322, "postgres", "postgres")

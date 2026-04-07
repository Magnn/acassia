import sqlite3
import os

# Caminho do banco de dados na raiz do projeto
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cigana.db")

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Adiciona a coluna para sabermos quando o humano assumiu o comando
    c.execute("ALTER TABLE leads ADD COLUMN bot_pausado BOOLEAN DEFAULT 0;")
    conn.commit()
    print("✅ Coluna 'bot_pausado' adicionada com sucesso ao banco de dados!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("⚠️ A coluna 'bot_pausado' já existe no banco de dados. Tudo pronto!")
    else:
        print(f"🚨 Erro ao alterar o banco: {e}")
finally:
    conn.close()
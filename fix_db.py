import sqlite3
import os

# Ajuste o caminho se o seu banco tiver outro nome (ex: meumisterio.db, sqlite.db)
DB_PATH = os.path.join("db", "database.db") 

def fix():
    print(f"🛠️ Iniciando manutenção direta em {DB_PATH}...")

    # Garante que a pasta db existe
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Limpeza Radical (Apaga as tabelas antigas para evitar conflitos)
    cursor.execute("DROP TABLE IF EXISTS leads")
    cursor.execute("DROP TABLE IF EXISTS mensagens")

    # 2. Criação da Tabela Leads (ATUALIZADA V6.1 - Com Memória Persistente)
    print("📝 Criando tabela 'leads' atualizada...")
    cursor.execute("""
        CREATE TABLE leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefone TEXT UNIQUE NOT NULL,
            node_atual TEXT DEFAULT '1_apresentacao',
            node_historico TEXT,
            estado_coleta TEXT DEFAULT 'inicial',
            metadata_json TEXT,
            nome TEXT,
            email TEXT,
            tags TEXT,
            score_engajamento FLOAT DEFAULT 0.5,
            ultima_intencao TEXT,
            ultimo_sentimento TEXT,
            objecoes_detectadas TEXT,
            recovery_stage INTEGER DEFAULT 0,
            recovery_bloqueado BOOLEAN DEFAULT 0,
            ultimo_recovery_em DATETIME,
            opt_out BOOLEAN DEFAULT 0,
            convertido BOOLEAN DEFAULT 0,
            produto_comprado TEXT,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Criação da Tabela Mensagens (ATUALIZADA V6.1 - Com tipos de mídia)
    print("📝 Criando tabela 'mensagens' atualizada...")
    cursor.execute("""
        CREATE TABLE mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            remetente TEXT NOT NULL,
            texto TEXT NOT NULL,
            tipo TEXT DEFAULT 'text',
            intencao TEXT,
            sentimento TEXT,
            score_engajamento FLOAT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Tudo pronto! As tabelas foram recriadas com a Arquitetura Sênior v6.1.")

if __name__ == "__main__":
    fix()
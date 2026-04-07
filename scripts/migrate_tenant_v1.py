"""
Migração v1: isolamento por conta (tenant_id).

Execute na raiz do projeto:
  python scripts/migrate_tenant_v1.py

- leads: adiciona tenant_id (default) e índice único (tenant_id, telefone)
- studio_publish: adiciona tenant_id único por linha (migra linha id=1 -> tenant default)

Após rodar, reinicie o servidor. Em instalações novas, create_all já cria o schema correto.
"""
from __future__ import annotations

import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DB_PATH = os.path.join(_ROOT, "cigana.db")


def _colunas(conn, tabela: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({tabela})")
    return {r[1] for r in cur.fetchall()}


def _indices(conn, tabela: str) -> list[tuple]:
    cur = conn.execute(f"PRAGMA index_list({tabela})")
    return cur.fetchall()


def migrate():
    if not os.path.isfile(DB_PATH):
        print(f"DB não encontrado: {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    try:
        # ── leads ─────────────────────────────────────────────────────
        cols = _colunas(conn, "leads")
        if "tenant_id" not in cols:
            print("Adicionando leads.tenant_id …")
            conn.execute(
                "ALTER TABLE leads ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'default'"
            )
            conn.commit()

        # Remove índice único antigo só em telefone (nome varia)
        for row in _indices(conn, "leads"):
            idx_name = row[1] if isinstance(row, (list, tuple)) and len(row) > 1 else row[0]
            if not idx_name or "sqlite_autoindex" in str(idx_name):
                continue
            info = conn.execute(f"PRAGMA index_info({idx_name})").fetchall()
            if len(info) == 1 and info[0][2] == "telefone":
                try:
                    conn.execute(f"DROP INDEX {idx_name}")
                    print(f"Removido índice antigo: {idx_name}")
                except sqlite3.OperationalError as e:
                    print(f"Aviso ao dropar {idx_name}: {e}")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_lead_tenant_phone ON leads(tenant_id, telefone)"
        )
        conn.commit()

        # ── studio_publish ────────────────────────────────────────────
        if "studio_publish" in [
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]:
            sp_cols = _colunas(conn, "studio_publish")
            if "tenant_id" not in sp_cols:
                print("Adicionando studio_publish.tenant_id …")
                conn.execute(
                    "ALTER TABLE studio_publish ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'default'"
                )
                conn.execute("UPDATE studio_publish SET tenant_id = 'default' WHERE tenant_id IS NULL OR tenant_id = ''")
                conn.commit()
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_studio_publish_tenant ON studio_publish(tenant_id)"
            )
            conn.commit()

        # ── studio_agents ────────────────────────────────────────────
        if "studio_agents" in [
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]:
            sa_cols = _colunas(conn, "studio_agents")
            if "tenant_id" not in sa_cols:
                print("Adicionando studio_agents.tenant_id …")
                conn.execute(
                    "ALTER TABLE studio_agents ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'default'"
                )
                conn.execute("UPDATE studio_agents SET tenant_id = 'default' WHERE tenant_id IS NULL OR tenant_id = ''")
                conn.commit()

        print("OK — migração tenant v1 concluída.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(migrate())

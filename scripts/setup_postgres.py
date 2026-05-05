"""
scripts/setup_postgres.py — Setup completo: Docker → Schema → Migração → .env
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Script interativo que:
  1. Sobe PostgreSQL via Docker (se disponível)
  2. Configura DATABASE_URL no .env
  3. Cria schema via create_all
  4. Migra dados do SQLite
  5. Valida contagem de linhas
  6. Configura REDIS_URL (se Docker)

Uso:
  python scripts/setup_postgres.py                    # Docker local
  python scripts/setup_postgres.py --url "postgresql://..."  # URL externa (Neon, Supabase, etc.)
"""

import os
import sys
import time
import subprocess
import argparse
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def _run(cmd: str, timeout: int = 60) -> tuple:
    """Roda comando e retorna (return_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            cwd=_ROOT,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def _update_env(key: str, value: str):
    """Adiciona ou atualiza variável no .env."""
    env_path = os.path.join(_ROOT, ".env")
    lines = []
    found = False

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"  ✅ .env: {key}={value[:40]}{'...' if len(value) > 40 else ''}")


def _wait_for_pg(url: str, max_wait: int = 30) -> bool:
    """Espera PostgreSQL aceitar conexões."""
    from sqlalchemy import create_engine, text
    print(f"  ⏳ Aguardando PostgreSQL aceitar conexões (max {max_wait}s)...")
    for i in range(max_wait):
        try:
            eng = create_engine(url, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"  ✅ PostgreSQL respondendo após {i+1}s")
            eng.dispose()
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    parser = argparse.ArgumentParser(description="Setup PostgreSQL para Acássia")
    parser.add_argument("--url", type=str, help="DATABASE_URL externa (Neon, Supabase, etc.)")
    parser.add_argument("--skip-docker", action="store_true", help="Pular Docker")
    parser.add_argument("--skip-migrate", action="store_true", help="Pular migração de dados")
    args = parser.parse_args()

    print("=" * 60)
    print("🐘 Setup PostgreSQL — Acássia / Meu Mistério")
    print("=" * 60)
    print()

    # ── Determinar DATABASE_URL ──
    if args.url:
        pg_url = args.url.strip()
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://", 1)
        print(f"📌 Usando URL fornecida: ...@{pg_url.split('@')[-1] if '@' in pg_url else 'local'}")
    else:
        # Tentar Docker
        if not args.skip_docker:
            print("🐳 Tentando subir PostgreSQL via Docker...")
            rc, out, err = _run("docker compose up -d db redis", timeout=120)
            if rc == 0:
                print("  ✅ Docker compose: db + redis subindo")
                pg_url = "postgresql://meumisterio:meumisterio_2026_secure@localhost:5432/meumisterio"
            else:
                print(f"  ❌ Docker falhou: {err[:100]}")
                print()
                print("  💡 Alternativas:")
                print("     1. Inicie o Docker Desktop e re-execute este script")
                print("     2. Use Neon (free): python scripts/setup_postgres.py --url 'postgresql://...'")
                print("     3. Use Supabase (free): python scripts/setup_postgres.py --url 'postgresql://...'")
                return 1
        else:
            pg_url = "postgresql://meumisterio:meumisterio_2026_secure@localhost:5432/meumisterio"

    # ── Esperar PostgreSQL ──
    if not _wait_for_pg(pg_url):
        print("  ❌ PostgreSQL não respondeu em 30s")
        print("     Verifique se o serviço está rodando e a URL está correta")
        return 1

    # ── Salvar no .env ──
    print()
    print("📝 Configurando .env...")
    _update_env("DATABASE_URL", pg_url)
    if "localhost" in pg_url:
        _update_env("REDIS_URL", "redis://localhost:6379/0")

    # ── Criar schema ──
    print()
    print("📦 Criando schema no PostgreSQL...")
    os.environ["DATABASE_URL"] = pg_url

    # Reimportar database.py com a nova URL
    if "db.database" in sys.modules:
        del sys.modules["db.database"]
    if "db.models" in sys.modules:
        del sys.modules["db.models"]

    from db.database import engine as pg_engine, DB_DRIVER
    from db.models import Base

    print(f"  Driver detectado: {DB_DRIVER}")
    Base.metadata.create_all(bind=pg_engine)
    print("  ✅ Schema criado/verificado")

    # ── Contar tabelas ──
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(pg_engine)
    tables = inspector.get_table_names()
    print(f"  📋 {len(tables)} tabelas no PostgreSQL")

    # ── Migrar dados ──
    if not args.skip_migrate:
        sqlite_path = os.path.join(_ROOT, "meumisterio.db")
        if os.path.exists(sqlite_path):
            print()
            print("📥 Migrando dados do SQLite → PostgreSQL...")
            rc, out, err = _run(
                f'python scripts/migrate_sqlite_to_postgres.py',
                timeout=300,
            )
            if rc == 0:
                print("  ✅ Migração concluída")
                # Mostrar últimas linhas do output
                for line in out.split("\n")[-10:]:
                    if line.strip():
                        print(f"  {line}")
            else:
                print(f"  ⚠️ Migração retornou código {rc}")
                if err:
                    print(f"  {err[:200]}")
        else:
            print(f"  ℹ️  SQLite não encontrado ({sqlite_path}) — skip migração")
    else:
        print("  ⏩ Migração de dados pulada (--skip-migrate)")

    # ── Health check final ──
    print()
    print("🏥 Health check final...")
    from db.database import check_db_health
    health = check_db_health()
    if health.get("status") == "ok":
        print(f"  ✅ {health['driver']} OK!")
    else:
        print(f"  ❌ Health check falhou: {health}")
        return 1

    print()
    print("=" * 60)
    print("🎉 SETUP COMPLETO!")
    print("=" * 60)
    print()
    print("Próximos passos:")
    print("  1. Reinicie o servidor: python app.py")
    print("  2. Verifique o log: '🐘 [DATABASE] PostgreSQL conectado'")
    print("  3. Teste: http://localhost:5000/api/health")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

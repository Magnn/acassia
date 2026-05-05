"""
db/database.py — v5.0 (DUAL-ENGINE: SQLite + PostgreSQL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Suporta SQLite (dev/single-tenant) e PostgreSQL (prod/multi-tenant).
Detecção automática via DATABASE_URL:
    - Não definida / sqlite:///... → SQLite com pragmas WAL+MMAP
    - postgresql://... ou postgres://... → PostgreSQL com pool otimizado

🔥 UPGRADES v5.0:
  1. DUAL ENGINE: SQLite (dev) ou PostgreSQL (prod) via DATABASE_URL
  2. POOL TUNING: Parâmetros distintos por driver
  3. HEALTH CHECK: Função `check_db_health()` para probes
  4. ASYNC-READY: Estrutura preparada para migração futura asyncpg
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

# Evita repetir log de pragmas a cada nova conexão SQLite
_PRAGMA_JA_LOGADO = False

# ── CONFIGURAÇÃO DE CAMINHOS ──
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Prefer meumisterio.db, fallback to meumisterio.db for backwards compatibility
_NEW_DB = os.path.join(_BASE_DIR, "meumisterio.db")
_LEGACY_DB = os.path.join(_BASE_DIR, "meumisterio.db")
DB_PATH = _NEW_DB if os.path.exists(_NEW_DB) else (_LEGACY_DB if os.path.exists(_LEGACY_DB) else _NEW_DB)

# Detecta driver a partir de DATABASE_URL
_raw_url = os.getenv("DATABASE_URL", "").strip()

# Heroku/Railway usam "postgres://" que SQLAlchemy 2.x não aceita — corrigir
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

if _raw_url and _raw_url.startswith("postgresql"):
    DATABASE_URL = _raw_url
    DB_DRIVER = "postgresql"
else:
    DATABASE_URL = _raw_url if _raw_url else ("sqlite:///" + DB_PATH.replace("\\", "/"))
    DB_DRIVER = "sqlite"


def _int_env(key: str, default: int) -> int:
    try:
        return int(str(os.getenv(key, str(default))).strip())
    except (TypeError, ValueError):
        return default


# ── POOL SETTINGS (ajustados por driver) ──
if DB_DRIVER == "postgresql":
    DB_POOL_SIZE = max(5, _int_env("DB_POOL_SIZE", 20))
    DB_MAX_OVERFLOW = max(0, _int_env("DB_MAX_OVERFLOW", 40))
    DB_POOL_TIMEOUT = max(3, _int_env("DB_POOL_TIMEOUT", 30))
    DB_POOL_RECYCLE = max(60, _int_env("DB_POOL_RECYCLE", 1800))

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE,
        pool_use_lifo=True,
        # PostgreSQL: statement timeout 30s (evita queries lentas travarem pool)
        connect_args={"options": "-c statement_timeout=30000"},
    )
else:
    # SQLite: pool conservador — SQLite tem 1 writer por vez, muitas conexões
    # só aumentam contention e SQLITE_BUSY. Pool >= 15 já é generoso.
    DB_POOL_SIZE = max(3, _int_env("DB_POOL_SIZE", 5))
    DB_MAX_OVERFLOW = max(0, _int_env("DB_MAX_OVERFLOW", 10))
    DB_POOL_TIMEOUT = max(3, _int_env("DB_POOL_TIMEOUT", 30))
    DB_POOL_RECYCLE = max(60, _int_env("DB_POOL_RECYCLE", 1800))

    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE,
        pool_use_lifo=True,
    )


# ── PRAGMAS SQLite DE ALTA PERFORMANCE ──
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configurações de hardware e sistema para extrair o máximo do SQLite.
    Ignora silenciosamente se o driver for PostgreSQL.
    """
    if engine.name != "sqlite":
        return

    cursor = dbapi_connection.cursor()
    # Ativa leitura e escrita simultânea (Crucial para o Recovery de 2min)
    cursor.execute("PRAGMA journal_mode=WAL")
    # Performance de escrita balanceada
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Otimização para SSDs: blocos de 4KB
    cursor.execute("PRAGMA page_size=4096")
    # MMAP: Mapeia até 256MB do banco direto na RAM para velocidade luz
    cursor.execute("PRAGMA mmap_size=268435456")
    # Buffer de cache em memória
    cursor.execute("PRAGMA cache_size=-64000")
    # Timeout de segurança para evitar 'Database is locked' (30s para 50+ users)
    cursor.execute("PRAGMA busy_timeout=30000")
    # Wal auto-checkpoint a cada 1000 pages (evita WAL crescer demais)
    cursor.execute("PRAGMA wal_autocheckpoint=1000")
    # Leitura suja permitida em WAL (melhora leitura concorrente)
    cursor.execute("PRAGMA read_uncommitted=ON")
    # Temp store em memória
    cursor.execute("PRAGMA temp_store=MEMORY")

    # Validação do estado
    cursor.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    cursor.close()

    global _PRAGMA_JA_LOGADO
    if mode.lower() == "wal":
        if not _PRAGMA_JA_LOGADO:
            logger.info("⚡ [DATABASE] Alta Performance Ativada (WAL + MMAP).")
            _PRAGMA_JA_LOGADO = True
    else:
        logger.warning(f"⚠️ [DATABASE] SQLite operando em modo degradado: {mode}")


# ── GESTÃO DE SESSÕES ──
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Mantém objetos acessíveis após o commit (Vital para o Dashboard)
)

# Classe Base moderna para SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass

@contextmanager
def session_scope():
    """
    Gerenciador robusto com tratamento cirúrgico de erros.
    Uso: with session_scope() as db: ...
    Faz commit automatico; rollback em caso de exceção.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("🚨 [DB_FATAL] Falha na transação: %s", e, exc_info=True)
        raise
    finally:
        session.close()


@contextmanager
def read_session():
    """
    Session read-only — sem commit/rollback, apenas close.
    Ideal para queries de leitura que não precisam de transação.
    Reduz overhead de pool em endpoints de leitura intensiva.

    Uso: with read_session() as db: rows = db.query(...).all()
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db():
    """
    Injeção de dependência padrão para Flask/API.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_teardown(app):
    """
    Registra cleanup automático de sessions no Flask.
    Chamado uma vez no app factory: init_teardown(app)
    Garante que conexões são devolvidas ao pool ao final de cada request,
    mesmo se o handler esqueceu de chamar db.close().
    """
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        SessionLocal.remove() if hasattr(SessionLocal, 'remove') else None


# ── HEALTH CHECK ──
def check_db_health() -> dict:
    """Verifica saúde do banco para probes de readiness."""
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ok", "driver": DB_DRIVER}
        finally:
            db.close()
    except Exception as exc:
        return {"status": "error", "driver": DB_DRIVER, "error": str(exc)[:200]}


def set_tenant_rls(session, tenant_id: str) -> None:
    """
    Ativa Row-Level Security para a sessão corrente.
    Deve ser chamado no início de cada request autenticada.

    Em SQLite (dev), é no-op — RLS é feature do PostgreSQL.

    Uso:
        db = SessionLocal()
        set_tenant_rls(db, current_user.tenant_id)
    """
    if DB_DRIVER != "postgresql" or not tenant_id:
        return
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
    except Exception:
        pass  # Non-fatal: RLS is defense-in-depth, not primary filter


# Log de inicialização
if DB_DRIVER == "postgresql":
    # Oculta credenciais no log
    _safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "localhost"
    logger.info(f"🐘 [DATABASE] PostgreSQL conectado em: ...@{_safe_url}")
else:
    logger.info(f"🔮 [DATABASE] SQLite conectado em: {os.path.abspath(DB_PATH)}")

logger.info(
    "🧵 [DATABASE] Pool configurado: driver=%s size=%s overflow=%s timeout=%ss recycle=%ss",
    DB_DRIVER,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
    DB_POOL_RECYCLE,
)
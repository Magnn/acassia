"""
db/database.py — SUPREME v4.2 (HIGH-SPEED ENGINE & ALCHEMY 2.0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conexão SQLAlchemy otimizada para o tráfego pesado do Magno.

🔥 UPGRADES DESTA VERSÃO (v4.2):
  1. MMAP PERFORMANCE: Ativa o Memory-Mapped I/O para leitura ultra-rápida.
  2. SQLALCHEMY 2.0 READY: Atualização da 'Base' para evitar LegacyWarnings.
  3. SESSION PERSISTENCE: expire_on_commit=False para manter dados vivos no Dashboard.
  4. PAGE_SIZE OPTIMIZATION: Ajuste de 4KB para melhor performance em SSDs modernos.
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

# Evita repetir a mesma linha a cada nova conexão SQLite (worker / threads)
_PRAGMA_JA_LOGADO = False

# ── CONFIGURAÇÃO DE CAMINHOS ──
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_BASE_DIR, "cigana.db")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + DB_PATH.replace("\\", "/"))


def _int_env(key: str, default: int) -> int:
    try:
        return int(str(os.getenv(key, str(default))).strip())
    except (TypeError, ValueError):
        return default


DB_POOL_SIZE = max(5, _int_env("DB_POOL_SIZE", 24))
DB_MAX_OVERFLOW = max(0, _int_env("DB_MAX_OVERFLOW", 48))
DB_POOL_TIMEOUT = max(3, _int_env("DB_POOL_TIMEOUT", 20))
DB_POOL_RECYCLE = max(60, _int_env("DB_POOL_RECYCLE", 1800))

# ── MOTOR DE EXECUÇÃO ──
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,  # Verifica saúde da conexão antes de cada query
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_use_lifo=True,
)

# ── PRAGMAS DE ALTA PERFORMANCE (O SEGREDO DA VELOCIDADE) ──
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configurações de hardware e sistema para extrair o máximo do SQLite.
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
    # Timeout de segurança para evitar 'Database is locked'
    cursor.execute("PRAGMA busy_timeout=10000")
    
    # Validação mística do estado
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

# ── GERENCIADORES DE CONTEXTO IMPERIAIS ──

@contextmanager
def session_scope():
    """
    Gerenciador robusto com tratamento cirúrgico de erros.
    Uso: with session_scope() as db: ...
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"🚨 [DB_FATAL] Falha na transação: {e}", exc_info=True)
        raise
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

# Log de inicialização com path absoluto para segurança operacional
logger.info(f"🔮 [DATABASE] Oráculo conectado em: {os.path.abspath(DB_PATH)}")
logger.info(
    "🧵 [DATABASE] Pool configurado: size=%s overflow=%s timeout=%ss recycle=%ss",
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
    DB_POOL_RECYCLE,
)
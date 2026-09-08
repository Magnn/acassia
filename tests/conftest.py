"""
Configuração global de testes.

Define BCRYPT_ROUNDS=4 antes de qualquer import — bcrypt em cost=12 (default
de prod) toma ~250ms por hash; com 4 fica em ms. Crítico pra suite rodar
em <5s.
"""

import os
import sys
import pytest

# Purge cached modules to prevent cross-project import contamination
for m in list(sys.modules.keys()):
    if any(m.startswith(prefix) for prefix in ["db", "api", "engine", "extensions", "app", "config", "helpers", "analytics_telemetry"]):
        del sys.modules[m]

# Garante prioridade absoluta de importação para a pasta meu_misterio
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if "projeto_cigana" not in p and p != "c:\\projetos_magno" and p != "C:\\projetos_magno"]
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Força o uso de um banco de teste SQLite isolado para todos os testes
os.environ["DATABASE_URL"] = "sqlite:///c:/projetos_magno/meu_misterio/meumisterio_test.db"
os.environ.setdefault("BCRYPT_ROUNDS", "4")

# Desativa o rate limiter globalmente para evitar 429 nos testes paralelos/concorrentes
try:
    from extensions import limiter
    limiter.enabled = False
except Exception:
    pass


@pytest.fixture(autouse=True)
def clean_global_state():
    # 1. Reset lockout counters
    try:
        from api.saas.security import reset_lockout_counters_for_test
        reset_lockout_counters_for_test()
    except Exception:
        pass

    # 2. Clear database tables in correct dependency order
    try:
        from db.database import SessionLocal, Base, engine as db_engine
        from db import models
        from db.sync import sync_database
        Base.metadata.create_all(bind=db_engine)
        sync_database()
        db = SessionLocal()
        for model in [
            models.EmailVerificationToken,
            models.PasswordResetToken,
            models.ImpersonationSession,
            models.UserSession,
            models.AuditEvent,
            models.TenantBilling,
            models.WaPhoneTenantBinding,
            models.TenantFlowSecret,
            models.TenantFlowVariable,
            models.Mensagem,
            models.Lead,
            models.User,
        ]:
            try:
                db.query(model).delete()
            except Exception:
                db.rollback()
        db.commit()
        db.close()
    except Exception:
        pass

    # 3. Clear tenant config cache
    try:
        from api import tenant_config
        tenant_config.clear_cache()
    except Exception:
        pass

    yield


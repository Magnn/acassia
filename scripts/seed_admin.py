"""
scripts/seed_admin.py — Garante a existência da conta Super-Admin no banco.
Executado a cada inicialização para garantir persistência mesmo em containers efêmeros.
"""

import os
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import logging
from datetime import datetime, timezone
import bcrypt
from db.database import SessionLocal
from db import models

logger = logging.getLogger("seed_admin")

DEFAULT_ADMIN_EMAIL = "mgnhnrq31@gmail.com"
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "Magno@Admin2026")
DEFAULT_ADMIN_NAME = "Magno (Super Admin)"
DEFAULT_ADMIN_TENANT = "admin_master"


def seed_admin_user(
    email: str = DEFAULT_ADMIN_EMAIL,
    password: str = DEFAULT_ADMIN_PASSWORD,
    name: str = DEFAULT_ADMIN_NAME,
):
    email = email.strip().lower()
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        if not user:
            user = models.User(
                email=email,
                name=name,
                password_hash=pw_hash,
                role="admin",
                tenant_id=DEFAULT_ADMIN_TENANT,
                is_active=True,
                is_verified=True,
                criado_em=datetime.now(timezone.utc),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("👑 [ADMIN] Conta Super-Admin criada: %s (id=%s, role=admin)", email, user.id)
            print(f"[seed_admin] Conta Super-Admin criada: {email} (id={user.id})")
        else:
            changed = False
            if user.role != "admin":
                user.role = "admin"
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if not user.is_verified:
                user.is_verified = True
                changed = True
            # Se a senha informada for diferente, atualiza
            if password and not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
                user.password_hash = pw_hash
                changed = True
                print(f"[seed_admin] Senha atualizada para {email}")
            if changed:
                db.commit()
                logger.info("👑 [ADMIN] Conta %s atualizada para role=admin", email)
                print(f"[seed_admin] Conta {email} sincronizada com sucesso")
            else:
                logger.info("👑 [ADMIN] Conta Super-Admin %s já ativa", email)
                print(f"[seed_admin] Conta Super-Admin {email} já ativa")
        return user
    except Exception as exc:
        db.rollback()
        logger.error("🚨 [ADMIN] Falha ao semear admin %s: %s", email, exc)
        print(f"[seed_admin] Erro ao semear admin: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_user()

from app import app
from db.database import SessionLocal
from db.models import TenantConfig

with app.app_context():
    db = SessionLocal()
    print("Configs:")
    for c in db.query(TenantConfig).all():
        print(f"- {c.key}: {c.value}")
    db.close()

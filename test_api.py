from app import app
from db.database import SessionLocal
from db.models import WADevice

with app.app_context():
    db = SessionLocal()
    devs = db.query(WADevice).all()
    print("ALL DEVICES IN DB:")
    for d in devs:
        print(f"ID={d.id} Tenant={d.tenant_id} Phone={d.phone_display}")
    db.close()

from app import app
from db.database import SessionLocal
from db.models import User, WADevice

with app.app_context():
    db = SessionLocal()
    users = db.query(User).all()
    print("Users:")
    for u in users:
        print(f"- ID: {u.id}, Email: {u.email}, Tenant: {u.tenant_id}")
        
    devs = db.query(WADevice).all()
    print("\nDevices:")
    for d in devs:
        print(f"- ID: {d.id}, Tenant: {d.tenant_id}, Phone: {d.phone_display}")
    db.close()

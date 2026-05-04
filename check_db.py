from app import app
from db.database import SessionLocal
from db.models import WaPhoneTenantBinding, TenantFlowSecret, WADevice
import os

with app.app_context():
    db = SessionLocal()
    print("Bindings: ", db.query(WaPhoneTenantBinding).count())
    print("TenantFlowSecrets WA:", db.query(TenantFlowSecret).filter_by(key="wa_access_token").count())
    
    # Try migrating secrets directly if they don't have bindings?
    secrets = db.query(TenantFlowSecret).filter_by(key="wa_access_token").all()
    count = 0
    for s in secrets:
        existing = db.query(WADevice).filter_by(tenant_id=s.tenant_id).first()
        if existing:
            continue
        token = s.value_cipher
        try:
            from core.crypto import decrypt_secret
            if token and token.startswith("enc_"):
                token = decrypt_secret(token)
        except:
            pass
            
        # Try to get phone display from tenant config if possible
        # We don't have TenantConfig imported but let's just make a WADevice
        dev = WADevice(
            tenant_id=s.tenant_id,
            nickname=f"WhatsApp {s.tenant_id}",
            provider="meta_cloud",
            connected=True,
            meta_access_token=token,
            is_primary=True
        )
        db.add(dev)
        count += 1
    
    db.commit()
    print(f"Migrated {count} devices from secrets.")
    db.close()

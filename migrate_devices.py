from app import app
from db.database import SessionLocal
from db.models import WaPhoneTenantBinding, TenantFlowSecret, WADevice
import os

with app.app_context():
    db = SessionLocal()
    try:
        bindings = db.query(WaPhoneTenantBinding).all()
        count = 0
        for b in bindings:
            existing = db.query(WADevice).filter_by(meta_phone_number_id=b.phone_number_id).first()
            if existing:
                continue
                
            secret = db.query(TenantFlowSecret).filter_by(tenant_id=b.tenant_id, key="wa_access_token").first()
            token = secret.value_cipher if secret else ""
            
            try:
                from core.crypto import decrypt_secret
                if token and token.startswith("enc_"):
                    token = decrypt_secret(token)
            except Exception:
                pass

            dev = WADevice(
                tenant_id=b.tenant_id,
                nickname=b.display_phone_number or b.phone_number_id or "WhatsApp Principal",
                provider="meta_cloud",
                connected=True,
                phone_display=b.display_phone_number,
                meta_phone_number_id=b.phone_number_id,
                meta_waba_id=b.waba_id,
                meta_access_token=token,
                is_primary=True
            )
            db.add(dev)
            count += 1
            
        db.commit()
        print(f"Migrados {count} dispositivos com sucesso!")
    finally:
        db.close()

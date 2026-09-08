import pytest
from flask import Flask
from unittest.mock import patch
from db.database import SessionLocal, Base, engine as db_engine
from db import models
from api.saas.wa_devices import devices_bp
from api.saas.auth import login_manager
from engine import Engine
from schema import ContextoConversa

@pytest.fixture
def app():
    flask_app = Flask('test_app')
    flask_app.config.update(SECRET_KEY='test-key', TESTING=True, SERVER_NAME='localhost')
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(devices_bp)
    return flask_app

def test_device_flow_mode_toggle_and_engine(app):
    db = SessionLocal()
    tenant_id = 'tenant_test_flow_mode'
    
    # Cleanup
    db.query(models.Lead).filter_by(tenant_id=tenant_id).delete()
    db.query(models.WADevice).filter_by(tenant_id=tenant_id).delete()
    db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id).delete()
    db.query(models.User).filter_by(tenant_id=tenant_id).delete()
    db.commit()
    
    # Create test user
    user = models.User(
        tenant_id=tenant_id,
        email='test_flow_mode@example.com',
        password_hash='$2b$12$fakehashedpasswordforflowmodetesting00',
        name='Test User',
        role='admin',
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create device
    dev = models.WADevice(
        tenant_id=tenant_id,
        nickname='Test Device',
        provider='meta_cloud',
        phone_display='+55 69 8105-1492',
        connected=True,
        flow_mode='static_funnel',
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    dev_id = dev.id
    db.close()
    
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
            
        # 1. Invalid mode returns 400
        res = c.post(f'/saas/devices/{dev_id}/flow-mode', json={'flow_mode': 'invalid_xyz'})
        assert res.status_code == 400
        
        # 2. Switch to ai_agent
        res = c.post(f'/saas/devices/{dev_id}/flow-mode', json={'flow_mode': 'ai_agent'})
        assert res.status_code == 200
        data = res.get_json()
        assert data['ok'] is True
        assert data['flow_mode'] == 'ai_agent'
        assert data['funil_entrada_inicial'] == '1_apresentacao'
        
        # Verify in DB
        db = SessionLocal()
        dev_db = db.query(models.WADevice).filter_by(id=dev_id).first()
        assert dev_db.flow_mode == 'ai_agent'
        var = db.query(models.TenantFlowVariable).filter_by(tenant_id=tenant_id, key='funil_entrada_inicial').first()
        assert var.value_json == '1_apresentacao'
        
        # Engine should create lead with 1_apresentacao
        eng = object.__new__(Engine)
        eng.tenant_id = tenant_id
        lead_ai = eng._obter_ou_criar_lead(db, '556999990001')
        assert lead_ai.node_atual == '1_apresentacao'
        
        # 3. Switch back to static_funnel
        res2 = c.post(f'/saas/devices/{dev_id}/flow-mode', json={'flow_mode': 'static_funnel'})
        assert res2.status_code == 200
        data2 = res2.get_json()
        assert data2['flow_mode'] == 'static_funnel'
        assert data2['funil_entrada_inicial'] == 'static_meumisterio_b1'
        
        # Verify in DB and Engine
        db.refresh(dev_db)
        assert dev_db.flow_mode == 'static_funnel'
        
        lead_static = eng._obter_ou_criar_lead(db, '556999990002')
        assert lead_static.node_atual == 'static_meumisterio_b1'
        
        db.close()
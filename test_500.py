import traceback
from app import app
from db.database import SessionLocal
from db.models import User
import json

db = SessionLocal()
user = db.query(User).first()
if not user:
    # mock a user
    user = User(email="test@test.com", password_hash="hash", tenant_id="test", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
client = app.test_client()

with client:
    # Fake login by setting session directly
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    try:
        resp = client.post('/saas/workspaces', json={"name": "test_script2"})
        print("POST /workspaces =>", resp.status_code)
        if resp.status_code == 500:
            print(resp.data.decode('utf-8'))
        
        data = json.loads(resp.data)
        if "id" in data:
            ws_id = data["id"]
            resp2 = client.post('/saas/workspaces/switch', json={"workspace_id": ws_id})
            print("POST /workspaces/switch =>", resp2.status_code)
            if resp2.status_code == 500:
                print(resp2.data.decode('utf-8'))
    except Exception as e:
        traceback.print_exc()

db.close()

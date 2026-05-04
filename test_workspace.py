from app import app
from db.database import SessionLocal
from db.models import User
from flask_login import login_user
from api.saas.auth import AuthenticatedUser

with app.test_request_context():
    db = SessionLocal()
    user = db.query(User).first()
    if user:
        print(f"Testing with user: {user.email}")
        
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_id'] = "fake_sess_id"
    
    try:
        resp = c.post('/saas/workspaces', json={"name": "test_script"})
        print("Status:", resp.status_code)
        print("Data:", resp.data)
    except Exception as e:
        import traceback
        traceback.print_exc()

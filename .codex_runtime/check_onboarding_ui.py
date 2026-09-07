import os
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(tempfile.mkdtemp(prefix='meumisterio-ui-')) / 'test.db').as_posix()
from flask import Flask, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin
from db.database import Base, engine
from db import models
from api.saas.onboarding import onboarding_bp
import api.saas.integrations_whatsapp as wa
import meta_graph_admin

Base.metadata.create_all(engine)
wa._validate_token_and_phone = lambda *args: (True, {'display_phone_number': 'Numero ficticio'})
meta_graph_admin.subscribe_apps_to_waba = lambda *args: (True, {'success': True})
app = Flask(__name__)
app.secret_key = 'local-ui-fixture'
login = LoginManager(app)
class FixtureUser(UserMixin):
    id = '999'
    tenant_id = 'ui-fixture'
@login.request_loader
def fixture_user(request):
    return FixtureUser()
app.register_blueprint(onboarding_bp)

@app.get('/builder/')
@app.get('/builder/<path:path>')
def frontend(path=''):
    dist = root / 'frontend' / 'dist'
    return send_from_directory(dist, path if path and (dist / path).is_file() else 'index.html')

@app.get('/saas/templates/data')
def templates():
    return jsonify(templates=[])

@app.get('/saas/metrics/data')
def metrics():
    return jsonify(total_leads=0, leads_7d=0, leads_30d=0, convertidos=0, ativas=0, pausadas=0, opt_out=0, conversion_rate=0, node_distribution=[])

@app.get('/api/dashboard/kpis')
def kpis():
    return jsonify(ok=True, series=[])

app.run(host='127.0.0.1', port=5187, debug=False)

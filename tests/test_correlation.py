"""tests/test_correlation.py — Testes do middleware de correlation ID."""
import uuid
from flask import Flask, g
from api.utils.correlation import init_correlation_id, get_correlation_id


def test_correlation_id_generated():
    """Deve gerar correlation ID automaticamente se não fornecido."""
    app = Flask(__name__)
    init_correlation_id(app)

    @app.route("/test")
    def _test_route():
        return {"cid": g.correlation_id}

    with app.test_client() as client:
        resp = client.get("/test")
        assert resp.status_code == 200
        cid = resp.headers.get("X-Correlation-ID")
        assert cid is not None
        assert len(cid) == 16


def test_correlation_id_preserved():
    """Deve preservar correlation ID se fornecido no header."""
    app = Flask(__name__)
    init_correlation_id(app)

    @app.route("/test")
    def _test_route():
        return {"cid": g.correlation_id}

    with app.test_client() as client:
        my_cid = "test-correlation-123"
        resp = client.get("/test", headers={"X-Correlation-ID": my_cid})
        assert resp.headers.get("X-Correlation-ID") == my_cid

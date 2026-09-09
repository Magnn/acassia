from types import SimpleNamespace

from flask import Flask

from api.saas import platform_health


def test_feature_usage_never_reads_another_tenant(monkeypatch):
    app = Flask("telemetry-scope")
    monkeypatch.setattr(
        platform_health,
        "current_user",
        SimpleNamespace(is_authenticated=True, tenant_id="telemetry-tenant-a"),
    )
    platform_health._feature_events[:] = [
        {"tenant_id": "telemetry-tenant-a", "event": "own"},
        {"tenant_id": "telemetry-tenant-b", "event": "foreign"},
    ]
    try:
        with app.test_request_context("/api/telemetry/feature-usage?tenant_id=telemetry-tenant-b"):
            response = app.make_response(platform_health.feature_usage())
            assert response.status_code == 200
            assert response.get_json() == {
                "total_events": 1,
                "features": [{"event": "own", "count": 1}],
            }
    finally:
        platform_health._feature_events.clear()

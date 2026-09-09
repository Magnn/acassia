from api.saas.wa_embedded_signup import _get_meta_app_credentials


def test_embedded_signup_has_no_hardcoded_app_id(monkeypatch):
    for key in ("META_APP_ID", "APP_ID", "META_APP_SECRET", "APP_SECRET", "META_CONFIG_ID"):
        monkeypatch.delenv(key, raising=False)
    assert _get_meta_app_credentials() == ("", "", "")


def test_embedded_signup_reads_complete_meta_configuration(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "app-123")
    monkeypatch.setenv("META_APP_SECRET", "secret-456")
    monkeypatch.setenv("META_CONFIG_ID", "config-789")
    assert _get_meta_app_credentials() == ("app-123", "secret-456", "config-789")

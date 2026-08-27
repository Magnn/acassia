from api.saas.integration_runners import execute_integration


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_activecampaign_reads_flat_builder_context_and_adds_tag(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs["json"]))
        if url.endswith("/contact/sync"):
            return _Response({"contact": {"id": "42"}})
        return _Response({})

    monkeypatch.setattr("api.saas.integration_runners.requests.post", fake_post)

    result = execute_integration(
        "activecampaign",
        "add_tag",
        {"tag_id": "7"},
        {"base_url": "https://tenant.api-us1.com", "api_key": "secret"},
        {"lead.email": "bia@example.com", "lead.telefone": "5592999999999", "lead.nome": "Bia"},
    )

    assert result == "Tag 7 adicionada ao contato 42 no ActiveCampaign."
    assert calls == [
        (
            "https://tenant.api-us1.com/api/3/contact/sync",
            {"contact": {"email": "bia@example.com", "firstName": "Bia", "phone": "5592999999999"}},
        ),
        (
            "https://tenant.api-us1.com/api/3/contactTags",
            {"contactTag": {"contact": "42", "tag": "7"}},
        ),
    ]


def test_activecampaign_requires_email_before_request(monkeypatch):
    def unexpected_post(*args, **kwargs):
        raise AssertionError("não deveria chamar a API")

    monkeypatch.setattr("api.saas.integration_runners.requests.post", unexpected_post)

    try:
        execute_integration(
            "activecampaign",
            "create_contact",
            {},
            {"base_url": "https://tenant.api-us1.com", "api_key": "secret"},
            {"lead.nome": "Sem Email"},
        )
    except ValueError as exc:
        assert "e-mail" in str(exc)
    else:
        raise AssertionError("era esperado erro de validação")

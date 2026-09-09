import json
from unittest.mock import patch

from mcp_server import handle
from sdk import MeuMisterioClient


class _Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()


def test_sdk_sends_bearer_and_json_body():
    with patch("sdk.client.urlopen", return_value=_Response({"ok": True})) as opened:
        result = MeuMisterioClient("https://example.test/", "secret").send_message("5511", "Oi")
    assert result == {"ok": True}
    request = opened.call_args.args[0]
    assert request.full_url == "https://example.test/api/v1/messages/send"
    assert request.get_header("Authorization") == "Bearer secret"
    assert json.loads(request.data)["recipient"] == "5511"


def test_mcp_lists_expected_tools():
    response = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {"get_contact", "upsert_contact", "send_message", "enroll_sequence"}

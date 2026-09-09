"""SDK Python sem dependências externas para a API v1."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class MeuMisterioError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


class MeuMisterioClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 20):
        if not base_url or not api_key:
            raise ValueError("base_url e api_key são obrigatórios")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            self.base_url + path, data=data, method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {"message": raw}
            raise MeuMisterioError(payload.get("error") or payload.get("message") or str(exc), exc.code, payload) from exc
        except URLError as exc:
            raise MeuMisterioError(f"Falha de conexão: {exc.reason}") from exc

    def ping(self) -> dict:
        return self._request("GET", "/api/v1/ping")

    def get_contact(self, phone_or_id: str | int) -> dict:
        return self._request("GET", f"/api/v1/contacts/{phone_or_id}")

    def upsert_contact(self, phone: str, name: str = "", tags=None, custom_fields=None) -> dict:
        return self._request("POST", "/api/v1/contacts", {
            "phone": phone, "name": name, "tags": tags or [], "custom_fields": custom_fields or {},
        })

    def add_tags(self, phone_or_id: str | int, tags: list[str]) -> dict:
        return self._request("POST", f"/api/v1/contacts/{phone_or_id}/tags", {"tags": tags})

    def send_message(self, recipient: str, text: str, channel: str = "whatsapp", **options) -> dict:
        return self._request("POST", "/api/v1/messages/send", {
            "recipient": recipient, "text": text, "channel": channel, **options,
        })

    def enroll_sequence(self, sequence_id: int, *, contact_id: int | None = None, phone: str | None = None) -> dict:
        return self._request("POST", "/api/v1/sequences/enroll", {
            "sequence_id": sequence_id, "contact_id": contact_id, "phone": phone,
        })

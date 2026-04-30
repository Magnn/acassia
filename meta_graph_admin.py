"""
Wrappers para Graph API administrativa da Meta WhatsApp Cloud API.

Foco: o que precisa rodar a partir do tenant pra deixar o webhook real:
    - subscribe_apps_to_waba(waba_id, access_token)  → subscreve a app no WABA
    - get_subscribed_apps(waba_id, access_token)
    - send_text(phone_number_id, access_token, to, body)  → envia texto direto
    - get_phone_number_info(phone_number_id, access_token)

Retornam (ok: bool, body: dict). Em erro, body inclui {error: {message, code}}.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode


logger = logging.getLogger(__name__)


GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")


def _request(method: str, path: str, access_token: str, *, params: dict | None = None,
             body: dict | None = None, timeout: int = 12) -> tuple[bool, dict[str, Any]]:
    qs = dict(params or {})
    qs["access_token"] = access_token
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{path.lstrip('/')}?{urlencode(qs)}"
    data = None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            return True, json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            payload = {"error": {"message": e.reason, "code": e.code}}
        return False, payload
    except Exception as exc:
        return False, {"error": {"message": str(exc), "code": 0}}


def subscribe_apps_to_waba(waba_id: str, access_token: str) -> tuple[bool, dict]:
    """
    Subscreve a App configurada (token system user) ao WABA na Meta.
    Endpoint: POST /<WABA_ID>/subscribed_apps

    Equivalente ao "Webhook Fields" no painel do app, mas no nivel do
    Business Account. Sem isso, mensagens nao chegam mesmo com webhook
    URL configurada.
    """
    if not waba_id or not access_token:
        return False, {"error": {"message": "missing_args"}}
    return _request("POST", f"{waba_id}/subscribed_apps", access_token)


def get_subscribed_apps(waba_id: str, access_token: str) -> tuple[bool, dict]:
    if not waba_id or not access_token:
        return False, {"error": {"message": "missing_args"}}
    return _request("GET", f"{waba_id}/subscribed_apps", access_token)


def get_phone_number_info(phone_number_id: str, access_token: str) -> tuple[bool, dict]:
    if not phone_number_id or not access_token:
        return False, {"error": {"message": "missing_args"}}
    return _request("GET", phone_number_id, access_token)


def send_text(phone_number_id: str, access_token: str, *, to: str, body: str) -> tuple[bool, dict]:
    """
    Envia mensagem de texto pelo provider Meta direto, sem passar pelo
    motor — usado pra teste end-to-end de credenciais antes do fluxo
    estar publicado.
    """
    if not phone_number_id or not access_token or not to or not body:
        return False, {"error": {"message": "missing_args"}}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:4096], "preview_url": False},
    }
    return _request(
        "POST", f"{phone_number_id}/messages", access_token, body=payload,
    )

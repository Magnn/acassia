"""
utils/meta_capi.py — Meta Conversions API (CAPI) para WhatsApp e Web
Envia eventos de conversão (Purchase, Lead, InitiateCheckout, CompleteRegistration)
direto dos servidores da Acássia para o Meta Pixel / Conversions API.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

META_GRAPH_VERSION = "v21.0"
META_CAPI_URL = f"https://graph.facebook.com/{META_GRAPH_VERSION}"


def hash_sha256(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    clean = str(val).strip().lower()
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def send_meta_capi_event(
    pixel_id: str,
    access_token: str,
    event_name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    value: Optional[float] = None,
    currency: str = "BRL",
    event_source_url: Optional[str] = None,
    action_source: str = "business_messaging",
    custom_data: Optional[Dict[str, Any]] = None,
    test_event_code: Optional[str] = None,
) -> Dict[str, Any]:
    if not pixel_id or not access_token:
        logger.warning("[META_CAPI] Pixel ID ou Access Token ausente. Ignorando envio.")
        return {"ok": False, "error": "missing_credentials"}

    user_data = {}
    if phone:
        clean_phone = "".join(filter(str.isdigit, phone))
        if clean_phone:
            user_data["ph"] = [hash_sha256(clean_phone)]
    if email:
        user_data["em"] = [hash_sha256(email)]
    if name:
        parts = name.strip().split()
        if parts:
            user_data["fn"] = [hash_sha256(parts[0])]
            if len(parts) > 1:
                user_data["ln"] = [hash_sha256(parts[-1])]

    data_payload: Dict[str, Any] = {}
    if value is not None:
        data_payload["value"] = float(value)
        data_payload["currency"] = currency
    if custom_data:
        data_payload.update(custom_data)

    event_payload = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "action_source": action_source,
        "user_data": user_data,
        "custom_data": data_payload,
    }
    if event_source_url:
        event_payload["event_source_url"] = event_source_url

    body: Dict[str, Any] = {
        "data": [event_payload]
    }
    if test_event_code:
        body["test_event_code"] = test_event_code

    url = f"{META_CAPI_URL}/{pixel_id}/events"
    params = {"access_token": access_token}

    try:
        resp = requests.post(url, params=params, json=body, timeout=10)
        res_json = resp.json()
        if resp.status_code == 200 and not res_json.get("error"):
            logger.info(
                "[META_CAPI] Evento '%s' enviado com sucesso para pixel %s (events_received=%s)",
                event_name,
                pixel_id,
                res_json.get("events_received"),
            )
            return {"ok": True, "data": res_json}
        else:
            logger.error("[META_CAPI] Erro ao enviar evento: %s", res_json)
            return {"ok": False, "error": res_json.get("error", "capi_error")}
    except Exception as exc:
        logger.exception("[META_CAPI] Excecao na requisicao CAPI: %s", exc)
        return {"ok": False, "error": str(exc)}

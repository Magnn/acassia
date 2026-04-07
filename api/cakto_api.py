from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import requests

from copy_sanitizer import normalizar_link_para_envio

logger = logging.getLogger(__name__)


class CaktoAPIClient:
    """Cliente leve da Cakto API com cache de token OAuth2."""

    def __init__(self, *, base_url: str, client_id: str, client_secret: str, timeout: int = 15):
        self.base_url = (base_url or "https://api.cakto.com.br").rstrip("/")
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.timeout = timeout
        self._access_token: str = ""
        self._token_exp_at: float = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _token_valido(self) -> bool:
        return bool(self._access_token and time.time() < (self._token_exp_at - 30))

    def get_access_token(self, force_refresh: bool = False) -> str:
        if not self.enabled:
            return ""
        if not force_refresh and self._token_valido():
            return self._access_token

        url = f"{self.base_url}/public_api/token/"
        data = {"client_id": self.client_id, "client_secret": self.client_secret}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post(url, data=data, headers=headers, timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"cakto_token_http_{r.status_code}")
        payload = r.json() if r.content else {}
        tok = str(payload.get("access_token") or "").strip()
        if not tok:
            raise RuntimeError("cakto_token_missing")
        expires_in = int(payload.get("expires_in") or 3600)
        self._access_token = tok
        self._token_exp_at = time.time() + max(60, expires_in)
        return tok

    def _request(self, method: str, path: str, *, params: Optional[dict] = None, json_body: Optional[dict] = None) -> dict:
        if not self.enabled:
            raise RuntimeError("cakto_disabled")
        token = self.get_access_token()
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=json_body,
            timeout=self.timeout,
        )
        if r.status_code == 401:
            token = self.get_access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            r = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        if r.status_code not in (200, 201):
            raise RuntimeError(f"cakto_http_{r.status_code}:{r.text[:180]}")
        return r.json() if r.content else {}

    def list_offers(self, *, search: str = "", page: int = 1, limit: int = 50) -> dict:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        return self._request("GET", "/public_api/offers/", params=params)

    def retrieve_offer(self, offer_id: str) -> dict:
        return self._request("GET", f"/public_api/offers/{offer_id}/")

    def list_orders(self, *, search: str = "", page: int = 1, limit: int = 50) -> dict:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        return self._request("GET", "/public_api/orders/", params=params)

    def create_webhook(self, payload: dict) -> dict:
        return self._request("POST", "/public_api/webhooks/", json_body=payload)

    @staticmethod
    def extract_checkout_url(offer_data: dict) -> str:
        """Tenta localizar URL de checkout em diferentes formatos de resposta."""
        if not isinstance(offer_data, dict):
            return ""
        candidates = []
        for key in (
            "checkout_url",
            "payment_link",
            "url",
            "checkoutLink",
            "checkoutUrl",
            "link",
        ):
            val = offer_data.get(key)
            if isinstance(val, str) and val.strip():
                candidates.append(val.strip())
        for nested_key in ("checkout", "links"):
            nested = offer_data.get(nested_key)
            if isinstance(nested, dict):
                for key in ("url", "checkout_url", "payment_link", "checkoutUrl"):
                    val = nested.get(key)
                    if isinstance(val, str) and val.strip():
                        candidates.append(val.strip())
        for raw in candidates:
            norm = normalizar_link_para_envio(raw, instagram_mode=False)
            if norm:
                return norm
        return ""

    def resolve_checkout_url(self, *, offer_id: str = "", offer_slug: str = "") -> str:
        """
        Resolve URL de checkout por offer_id (preferencial) ou por slug/search.
        """
        if offer_id:
            offer = self.retrieve_offer(str(offer_id).strip())
            return self.extract_checkout_url(offer)

        if offer_slug:
            search = str(offer_slug).strip()
            data = self.list_offers(search=search, page=1, limit=20)
            items = data.get("results") if isinstance(data, dict) else None
            if isinstance(items, list):
                slug_low = search.lower()
                for it in items:
                    s = str((it or {}).get("slug") or "").lower()
                    if s == slug_low:
                        url = self.extract_checkout_url(it)
                        if url:
                            return url
                for it in items:
                    url = self.extract_checkout_url(it)
                    if url:
                        return url
        return ""


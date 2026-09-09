"""
Factory que escolhe o provider WhatsApp correto pra um tenant.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import ProviderMode, WhatsAppProvider
from .coex import CoexProvider
from .evolution import EvolutionProvider
from .meta_cloud import MetaCloudProvider
from .openwa import OpenWAProvider

logger = logging.getLogger(__name__)


def get_provider_for_tenant(tenant_id: str) -> WhatsAppProvider:
    """
    Retorna o provider configurado pro tenant. Lê:

      - whatsapp.provider     (variable)  meta_cloud | coex | evolution | openwa
        Default: meta_cloud (retro com env).

    Cada provider lê as próprias chaves do tenant_config.
    """
    from api.tenant_config import get_tenant_config

    tid = tenant_id or "default"
    cfg = get_tenant_config(tid)
    wa = cfg.get("whatsapp") if isinstance(cfg, dict) else None
    wa = wa if isinstance(wa, dict) else {}

    mode = str(wa.get("provider") or "meta_cloud").strip().lower()

    # Achata config pra estilo "{prefix}_{key}" pra ser consumido pelos providers.
    flat: dict[str, Any] = {
        "phone_number_id": wa.get("phone_number_id"),
        "waba_id": wa.get("waba_id"),
        "access_token": wa.get("access_token"),
    }
    coex_cfg = wa.get("coex") if isinstance(wa.get("coex"), dict) else {}
    flat.update({
        "coex_api_url": coex_cfg.get("api_url"),
        "coex_instance": coex_cfg.get("instance"),
        "coex_api_key": coex_cfg.get("api_key"),
    })
    evo_cfg = wa.get("evolution") if isinstance(wa.get("evolution"), dict) else {}
    flat.update({
        "evolution_server_url": evo_cfg.get("server_url"),
        "evolution_instance": evo_cfg.get("instance"),
        "evolution_api_key": evo_cfg.get("api_key"),
    })
    openwa_cfg = wa.get("openwa") if isinstance(wa.get("openwa"), dict) else {}
    flat.update({
        "openwa_server_url": openwa_cfg.get("server_url"),
        "openwa_session_id": openwa_cfg.get("session_id"),
        "openwa_api_key": openwa_cfg.get("api_key"),
    })

    if mode == ProviderMode.COEX.value:
        return CoexProvider(tid, flat)
    if mode == ProviderMode.EVOLUTION.value:
        return EvolutionProvider(tid, flat)
    if mode == ProviderMode.OPENWA.value:
        return OpenWAProvider(tid, flat)
    return MetaCloudProvider(tid, flat)

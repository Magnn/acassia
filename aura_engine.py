"""
Aura imagery via Stable Diffusion (Frente 4.18).

Provider abstraction:
    - REPLICATE_API_TOKEN -> Replicate (SDXL ou Flux)
    - TOGETHER_API_KEY    -> Together.ai
    - Sem chave           -> retorna disabled=True (UI exibe orientacao)

Sign -> cores + elemento dominante.
Prompt template determinístico.
Fallback NSFW: regenera 1x.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


# ─── Sign metadata ────────────────────────────────────────────────────


SIGN_META = {
    "Aries":      {"colors": ["crimson red", "molten gold"],   "element": "fire"},
    "Touro":      {"colors": ["emerald green", "rose pink"],    "element": "earth"},
    "Gemeos":     {"colors": ["sky yellow", "iridescent silver"], "element": "air"},
    "Cancer":     {"colors": ["pearl white", "moonlight silver"], "element": "water"},
    "Leao":       {"colors": ["solar gold", "amber orange"],   "element": "fire"},
    "Virgem":     {"colors": ["sage green", "soft beige"],     "element": "earth"},
    "Libra":      {"colors": ["pastel pink", "soft lavender"], "element": "air"},
    "Escorpiao":  {"colors": ["deep crimson", "obsidian black"], "element": "water"},
    "Sagitario":  {"colors": ["royal purple", "gold"],         "element": "fire"},
    "Capricornio":{"colors": ["graphite gray", "deep brown"],  "element": "earth"},
    "Aquario":    {"colors": ["electric blue", "aqua cyan"],   "element": "air"},
    "Peixes":     {"colors": ["sea-foam green", "soft violet"], "element": "water"},
}


def build_aura_prompt(signo: str, mood: str | None = None) -> str:
    """Constroi prompt SDXL determinístico."""
    meta = SIGN_META.get(signo) or {"colors": ["violet", "gold"], "element": "ether"}
    c1, c2 = meta["colors"]
    el = meta["element"]
    base = (
        f"ethereal aura portrait, swirling {c1} and {c2} energies, "
        f"{el} elemental glow, mystical sacred geometry background, "
        f"art nouveau influence, soft luminous glow, dreamy cinematic, "
        f"highly detailed, no text, no faces, abstract spiritual art"
    )
    if mood:
        base += f", mood: {mood.strip()[:40]}"
    return base


# ─── Provider clients ─────────────────────────────────────────────────


class AuraProviderError(Exception):
    pass


def _provider_active() -> str | None:
    """Detecta qual provider está configurado por variavel de ambiente."""
    if os.environ.get("REPLICATE_API_TOKEN"):
        return "replicate"
    if os.environ.get("TOGETHER_API_KEY"):
        return "together"
    return None


def is_available() -> bool:
    return _provider_active() is not None


def _http_post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body.decode("utf-8"))


def _http_get_json(url: str, headers: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body.decode("utf-8"))


# Replicate: SDXL


_REPLICATE_MODEL = (
    "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
)


def generate_via_replicate(prompt: str, *, max_wait_sec: int = 90) -> str:
    """Cria predicao no Replicate, faz polling. Retorna URL da imagem."""
    token = os.environ["REPLICATE_API_TOKEN"]
    headers = {"Authorization": f"Token {token}"}

    create = _http_post_json(
        "https://api.replicate.com/v1/predictions",
        headers,
        {
            "version": _REPLICATE_MODEL.split(":", 1)[1],
            "input": {
                "prompt": prompt,
                "negative_prompt": "nsfw, nude, text, watermark, blurry, deformed",
                "width": 768, "height": 768,
                "num_inference_steps": 28,
                "guidance_scale": 7.5,
                "num_outputs": 1,
            },
        },
        timeout=30,
    )
    pred_url = create.get("urls", {}).get("get") or \
               f"https://api.replicate.com/v1/predictions/{create['id']}"

    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        time.sleep(2)
        status = _http_get_json(pred_url, headers, timeout=15)
        st = status.get("status")
        if st == "succeeded":
            outputs = status.get("output") or []
            if isinstance(outputs, list) and outputs:
                return outputs[0]
            if isinstance(outputs, str):
                return outputs
            raise AuraProviderError("replicate_no_output")
        if st in ("failed", "canceled"):
            raise AuraProviderError(f"replicate_{st}: {status.get('error')}")
    raise AuraProviderError("replicate_timeout")


# Together.ai: Flux Schnell


def generate_via_together(prompt: str) -> str:
    token = os.environ["TOGETHER_API_KEY"]
    headers = {"Authorization": f"Bearer {token}"}
    res = _http_post_json(
        "https://api.together.xyz/v1/images/generations",
        headers,
        {
            "model": "black-forest-labs/FLUX.1-schnell-Free",
            "prompt": prompt,
            "width": 768, "height": 768,
            "steps": 4, "n": 1,
        },
        timeout=60,
    )
    data = res.get("data") or []
    if not data:
        raise AuraProviderError("together_no_output")
    item = data[0]
    return item.get("url") or item.get("b64_json") or ""


# ─── Public entrypoint ────────────────────────────────────────────────


def generate_aura_image(signo: str, *, mood: str | None = None) -> dict:
    """
    Retorna {url, prompt, provider, generated_at}.
    Levanta AuraProviderError se nenhum provider configurado ou falha.
    """
    provider = _provider_active()
    if provider is None:
        raise AuraProviderError("no_provider_configured")

    prompt = build_aura_prompt(signo, mood)
    if provider == "replicate":
        url = generate_via_replicate(prompt)
    elif provider == "together":
        url = generate_via_together(prompt)
    else:
        raise AuraProviderError(f"unknown_provider_{provider}")

    if not url:
        raise AuraProviderError("empty_url")

    return {
        "url": url,
        "prompt": prompt,
        "provider": provider,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def week_id_for(date: datetime | None = None) -> str:
    """ID da semana ISO (YYYY-Www). Usado pra agrupar uma aura por semana."""
    date = date or datetime.now(timezone.utc)
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"

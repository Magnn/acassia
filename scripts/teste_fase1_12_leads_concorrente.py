"""
Stress concorrente da Fase 1 com 12 leads fantasmas.

Dispara mensagens intercaladas (ordem embaralhada por rodada) para simular
entrada real de leads com comportamentos diferentes na fase inicial.

Uso:
  py scripts/teste_fase1_12_leads_concorrente.py --base-url http://127.0.0.1:5000
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List

import requests


@dataclass
class LeadCase:
    phone: str
    roteiro: List[str]
    tags: List[str]


def _mk_phone(i: int) -> str:
    return f"5592{980000000 + i:09d}"


def _payload_text(phone: str, text: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": f"f1-{phone}-{int(time.time() * 1000)}-{random.randint(100, 999)}",
                                    "from": phone,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def _carregar_app_secret() -> str:
    env_secret = (os.getenv("APP_SECRET") or "").strip()
    if env_secret:
        return env_secret
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for linha in f:
                txt = linha.strip()
                if not txt or txt.startswith("#") or "=" not in txt:
                    continue
                k, v = txt.split("=", 1)
                if k.strip() == "APP_SECRET":
                    return v.strip()
    except OSError:
        return ""
    return ""


def _roteiros_12() -> List[LeadCase]:
    rows = [
        (["oi", "me chamo Ana", "já salvei", "mandei a foto", "dói há 2 anos"], ["nome_claro", "fluxo_direto"]),
        (["boa noite", "sou Lucas", "sim", "já salvei seu contato", "quero voltar com minha ex"], ["amor", "contato_ok"]),
        (["olá", "sim", "ok", "já mandei", "estou confusa"], ["placeholder_risco"]),
        (["bom dia", "meu nome é Paula", "não achei seu contato", "agora achei", "sinto ansiedade"], ["vcard_retry"]),
        (["oi cigana", "sou Magno", "já salvei", "foto enviada", "faz meses que sofro"], ["burst_possivel"]),
        (["oi", "quanto custa", "quero ajuda no amor", "sim salvei", "medo de perder ele"], ["preco_precoce"]),
        (["boa tarde", "sou Renata", "ok", "não chegou completo", "agora foi"], ["feedback_entrega"]),
        (["olá", "me chamo Bia", "já salvei", "palma enviada", "não durmo direito"], ["dor_forte"]),
        (["oi", "sou Bruno", "sim", "já salvei", "problema financeiro"], ["financeiro"]),
        (["eae", "nome Carlos", "ok", "já salvei aqui", "traição e bloqueio"], ["giria_curta"]),
        (["boa noite", "me chamo Nina", "salvei", "mandei foto", "quero paz"], ["texto_curto"]),
        (["oi", "meu nome é Joana", "sim", "já fiz tudo", "mensagem cortada antes"], ["historico_ruido"]),
    ]
    leads: List[LeadCase] = []
    for i, (roteiro, tags) in enumerate(rows, start=1):
        leads.append(LeadCase(phone=_mk_phone(i), roteiro=roteiro, tags=tags))
    return leads


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:5000")
    ap.add_argument("--min-gap-ms", type=int, default=80)
    ap.add_argument("--max-gap-ms", type=int, default=260)
    ap.add_argument("--seed", type=int, default=77)
    ap.add_argument("--app-secret", default=_carregar_app_secret())
    args = ap.parse_args()

    random.seed(args.seed)
    leads = _roteiros_12()
    max_steps = max(len(ld.roteiro) for ld in leads)
    ok = 0
    fail = 0
    by_status: Dict[str, int] = {}

    start = time.time()
    for step in range(max_steps):
        rodada = list(leads)
        random.shuffle(rodada)
        for ld in rodada:
            if step >= len(ld.roteiro):
                continue
            txt = ld.roteiro[step]
            try:
                payload = _payload_text(ld.phone, txt)
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                headers = {"Content-Type": "application/json"}
                if (args.app_secret or "").strip():
                    sig = hmac.new(args.app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
                    headers["X-Hub-Signature-256"] = f"sha256={sig}"
                r = requests.post(
                    f"{args.base_url.rstrip('/')}/webhook",
                    data=body,
                    headers=headers,
                    timeout=8,
                )
                if 200 <= r.status_code < 300:
                    ok += 1
                else:
                    fail += 1
                    k = str(r.status_code)
                    by_status[k] = by_status.get(k, 0) + 1
            except Exception:
                fail += 1
                by_status["exception"] = by_status.get("exception", 0) + 1
            time.sleep(random.randint(args.min_gap_ms, args.max_gap_ms) / 1000.0)

    elapsed = round(time.time() - start, 2)
    print(
        json.dumps(
            {
                "ok": fail == 0,
                "leads": len(leads),
                "messages_ok": ok,
                "messages_fail": fail,
                "fail_by_status": by_status,
                "elapsed_s": elapsed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())


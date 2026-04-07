"""
Simulador simples de carga conversacional (1000 leads/dia-like).

Uso:
  py scripts/simular_carga_leads.py --base-url http://127.0.0.1:5000 --leads 120 --seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import random
import time
import json
from dataclasses import dataclass
from typing import Dict, List

import requests


@dataclass
class FakeLead:
    phone: str
    roteiro: List[str]


def _mk_phone(i: int) -> str:
    return f"5592{900000000 + i:09d}"


def _payload(phone: str, text: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": f"sim-{phone}-{int(time.time() * 1000)}-{random.randint(100, 999)}",
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


def _roteiros() -> List[List[str]]:
    return [
        ["Boa tarde", "Me chamo Ana", "sim", "já salvei", "o que mais dói é solidão faz 2 anos"],
        ["Oi", "quanto custa essa consulta?", "sim", "já mandei foto", "quero saber se volto com meu ex"],
        ["boa noite", "me chamo Renato", "vamos", "sim", "já faz 1 ano e tentei de tudo"],
        ["olá", "como funciona?", "ok", "salvei", "quero prosperidade, estou travado financeiramente"],
        ["bom dia", "sou Magno", "beleza", "já sim", "medo de repetir o mesmo padrão no amor"],
        ["Oi cigana", "sou Carla", "sim", "já salvei aqui", "desde que terminei meu namoro não durmo direito"],
        ["Boa noite", "me chamo Lucas", "ok", "salvei o contato", "é ansiedade no trabalho e medo de demissão"],
        ["Oi", "pode me ajudar no amor?", "sim", "já fiz", "ele sumiu tem 3 meses e não sei se volta"],
        ["Olá", "quanto tempo demora?", "sim", "já salvei", "quero destravar vendas, estou estagnado"],
        ["Bom dia", "sou Renata", "vamos", "já salvei sim", "sinto inveja e peso no meu caminho afetivo"],
    ]


def _carregar_app_secret_padrao() -> str:
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


def gerar_leads(n: int) -> List[FakeLead]:
    bases = _roteiros()
    leads: List[FakeLead] = []
    for i in range(n):
        roteiro = random.choice(bases)
        leads.append(FakeLead(phone=_mk_phone(i + 1), roteiro=list(roteiro)))
    return leads


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:5000")
    ap.add_argument("--leads", type=int, default=100)
    ap.add_argument("--min-gap-ms", type=int, default=120)
    ap.add_argument("--max-gap-ms", type=int, default=450)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--app-secret", default=_carregar_app_secret_padrao())
    args = ap.parse_args()

    random.seed(args.seed)
    leads = gerar_leads(max(1, args.leads))
    ok = 0
    fail = 0

    falhas_por_status: Dict[str, int] = {}
    max_steps = max(len(ld.roteiro) for ld in leads)

    # Intercala mensagens entre leads para simular tráfego humano real.
    for step in range(max_steps):
        rodada = list(leads)
        random.shuffle(rodada)
        for ld in rodada:
            if step >= len(ld.roteiro):
                continue
            txt = ld.roteiro[step]
            try:
                payload = _payload(ld.phone, txt)
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                headers = {"Content-Type": "application/json"}
                if (args.app_secret or "").strip():
                    sig = hmac.new(
                        (args.app_secret or "").encode("utf-8"),
                        body,
                        hashlib.sha256,
                    ).hexdigest()
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
                    chave = str(r.status_code)
                    falhas_por_status[chave] = falhas_por_status.get(chave, 0) + 1
            except Exception:
                fail += 1
                falhas_por_status["exception"] = falhas_por_status.get("exception", 0) + 1
            time.sleep(random.randint(args.min_gap_ms, args.max_gap_ms) / 1000.0)

    print(f"Envios OK: {ok} | Falhas: {fail} | Leads simulados: {len(leads)}")
    if falhas_por_status:
        print(f"Falhas por status: {falhas_por_status}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

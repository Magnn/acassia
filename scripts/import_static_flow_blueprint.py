#!/usr/bin/env python3
"""
Importa o template JSON do funil estático via POST /api/flows/blueprints/import.

Uso (app rodando em localhost:5000):
  python scripts/import_static_flow_blueprint.py
  python scripts/import_static_flow_blueprint.py http://127.0.0.1:5000 default

Imprime o blueprint id para usar em /api/flows/blueprints/<id>/execute.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
    tenant = sys.argv[2] if len(sys.argv) > 2 else "default"
    path = ROOT / "docs" / "templates" / "funil_estatico_meu_misterio_bloco1.acassia-flow.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    payload = {
        "title": doc.get("title") or "Funil estático Meu Mistério",
        "slug": "meu_misterio_estatico_v1",
        "body": doc,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/flows/blueprints/import",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Acassia-Tenant": tenant,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    if not out.get("ok"):
        print(out, file=sys.stderr)
        return 1
    bid = out.get("blueprint", {}).get("id")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nExecute no Zap (troque LEAD_ID):\n  POST {base}/api/flows/blueprints/{bid}/execute")
    print(f'  Body: {{"lead_id": LEAD_ID}}')
    print(f'  Header: X-Acassia-Tenant: {tenant}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Simula o template de funil estático (dry-run) e lista as Acao geradas.

Uso:
  python scripts/simulate_static_flow_template.py
  python scripts/simulate_static_flow_template.py path/para/fluxo.acassia-flow.json

Não envia WhatsApp. Para teste ao vivo, importe o JSON no Flow Builder e use
POST /api/flows/blueprints/<id>/execute com lead_id (app em execução).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flow_builder_runtime import simulate_flow, validate_flow_document  # noqa: E402
from flow_executor import document_to_acoes  # noqa: E402


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    default = ROOT / "docs" / "templates" / "funil_estatico_meu_misterio_bloco1.acassia-flow.json"
    path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default
    if not path.is_file():
        print(f"Arquivo não encontrado: {path}", file=sys.stderr)
        return 1
    doc = json.loads(path.read_text(encoding="utf-8"))
    rep = validate_flow_document(doc)
    print("=== validate_flow_document ===")
    print("ok:", rep.get("ok"), "errors:", len(rep.get("errors") or []))

    sim = simulate_flow(rep.get("normalized") or doc, max_steps=80)
    print("\n=== simulate_flow (trace) ===")
    for row in (sim.get("trace") or [])[:40]:
        print(f"  - {row.get('description', row)}")

    try:
        acoes = document_to_acoes(rep.get("normalized") or doc)
    except ValueError as e:
        print("\n=== document_to_acoes ===")
        print("ERRO:", e)
        return 1

    print(f"\n=== document_to_acoes ({len(acoes)} ações) ===")
    for i, a in enumerate(acoes, 1):
        meta = getattr(a, "metadata", None) or {}
        tipo = getattr(a, "tipo", "")
        prev = (getattr(a, "conteudo", None) or getattr(a, "url", None) or "")[:120]
        print(f"  {i:2}. {tipo:8} {prev!s} {meta.get('node_type', '')}")

    print(
        "\nNota: esperas interativas (wait_until) não geram balão no executor atual; "
        "o motor de conversa precisa pausar o fluxo ao receber esses metadados no produto."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

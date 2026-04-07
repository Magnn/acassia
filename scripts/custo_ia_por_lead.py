"""
Relatorio de custo estimado de IA por lead.

Fonte:
- metadata_json do lead, campo `_ia_tokens_gastos_aprox`

Uso:
  py scripts/custo_ia_por_lead.py
  py scripts/custo_ia_por_lead.py --dias 30 --top 30
  py scripts/custo_ia_por_lead.py --preco-milhão-brl 1.8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sqlalchemy import desc
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import Lead
from config_cliente import CONFIG_CLIENTE


def _to_int(v, default=0) -> int:
    try:
        return int(v or default)
    except Exception:
        return default


def _to_float(v, default=0.0) -> float:
    try:
        return float(v or default)
    except Exception:
        return default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=30, help="Janela em dias (padrao 30)")
    ap.add_argument("--top", type=int, default=20, help="Top leads por custo (padrao 20)")
    ap.add_argument(
        "--preco-milhao-brl",
        type=float,
        default=1.8,
        help="Custo estimado em BRL por 1M tokens (padrao 1.8)",
    )
    args = ap.parse_args()

    desde = datetime.now(timezone.utc) - timedelta(days=max(1, args.dias))
    preco_milhao = max(0.01, float(args.preco_milhao_brl))
    preco_por_token = preco_milhao / 1_000_000.0

    cfg_ie = (CONFIG_CLIENTE.get("ia_economia") or {}) if isinstance(CONFIG_CLIENTE, dict) else {}
    budget_tokens = _to_int(cfg_ie.get("orcamento_tokens_por_lead"), 12000)
    t1 = _to_int(CONFIG_CLIENTE.get("preco_materiais"), 65)
    t2 = _to_int(CONFIG_CLIENTE.get("preco_servico"), 65)
    ticket_padrao = max(1, t1 + t2)

    db: Session = SessionLocal()
    try:
        leads = (
            db.query(Lead)
            .filter(Lead.atualizado_em >= desde)
            .order_by(desc(Lead.atualizado_em))
            .all()
        )
    finally:
        db.close()

    rows = []
    total_tokens = 0
    total_cost = 0.0
    count_with_tokens = 0
    for ld in leads:
        meta = getattr(ld, "metadata_json", None) or {}
        if not isinstance(meta, dict):
            continue
        toks = _to_int(meta.get("_ia_tokens_gastos_aprox"), 0)
        if toks <= 0:
            continue
        count_with_tokens += 1
        cost = toks * preco_por_token
        total_tokens += toks
        total_cost += cost
        ticket = 130
        try:
            ini = _to_int(meta.get("node8_ticket_inicial"), 0)
            if ini in (65, 100, 130):
                ticket = ini
            else:
                ticket = ticket_padrao
        except Exception:
            ticket = ticket_padrao
        pct_ticket = (cost / max(1.0, float(ticket))) * 100.0
        rows.append(
            {
                "lead_id": ld.id,
                "telefone": ld.telefone,
                "node_atual": ld.node_atual,
                "tokens_aprox": toks,
                "custo_brl_aprox": round(cost, 4),
                "ticket_ref": ticket,
                "pct_ticket": round(pct_ticket, 3),
            }
        )

    rows.sort(key=lambda x: x["custo_brl_aprox"], reverse=True)

    media_tokens = (total_tokens / count_with_tokens) if count_with_tokens else 0.0
    media_cost = (total_cost / count_with_tokens) if count_with_tokens else 0.0
    budget_cost = budget_tokens * preco_por_token
    pct_budget = (media_tokens / max(1, budget_tokens)) * 100.0 if budget_tokens else 0.0

    print("=== Custo IA por Lead (estimado) ===")
    print(f"Janela: {args.dias} dias | leads com tokens: {count_with_tokens}")
    print(f"Preço usado: R$ {preco_milhao:.4f} / 1M tokens")
    print(f"Budget config: {budget_tokens} tokens (~R$ {budget_cost:.4f})")
    print(
        f"Média por lead: {media_tokens:.1f} tokens | R$ {media_cost:.4f} "
        f"| uso do budget: {pct_budget:.1f}%"
    )
    print("")
    print(f"Top {max(1, args.top)} leads por custo:")
    for r in rows[: max(1, args.top)]:
        print(
            f"- lead={r['lead_id']} tel={r['telefone']} node={r['node_atual']} "
            f"tokens={r['tokens_aprox']} custo=R$ {r['custo_brl_aprox']:.4f} "
            f"ticket={r['ticket_ref']} ({r['pct_ticket']:.3f}% do ticket)"
        )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.dias,
        "price_per_million_brl": preco_milhao,
        "budget_tokens_per_lead": budget_tokens,
        "budget_cost_brl": round(budget_cost, 6),
        "leads_with_tokens": count_with_tokens,
        "avg_tokens_per_lead": round(media_tokens, 2),
        "avg_cost_per_lead_brl": round(media_cost, 6),
        "avg_budget_usage_pct": round(pct_budget, 2),
        "top": rows[: max(1, args.top)],
    }
    out_dir = os.path.join(_ROOT, "scripts", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "custo_ia_por_lead_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("")
    print(f"Relatório JSON: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


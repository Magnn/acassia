"""
Auditoria avançada de copy/contexto por lead.

Uso:
  python scripts/auditoria_personalizacao.py
  python scripts/auditoria_personalizacao.py --hours 48 --limit 120
  python scripts/auditoria_personalizacao.py --min-node 6
"""

from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analytics.personalizacao_audit import auditar_personalizacao
from db.database import SessionLocal


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24, help="Janela em horas (padrão: 24)")
    ap.add_argument("--limit", type=int, default=100, help="Máx. leads analisados (padrão: 100)")
    ap.add_argument("--min-msgs", type=int, default=6, help="Mínimo de mensagens para avaliar (padrão: 6)")
    ap.add_argument(
        "--min-node",
        type=int,
        default=None,
        metavar="N",
        help="Só leads com prefixo numérico do node >= N (ex.: 6 = leitura em diante)",
    )
    args = ap.parse_args()

    db = SessionLocal()
    try:
        r = auditar_personalizacao(
            db,
            hours=args.hours,
            limit=args.limit,
            min_msgs=args.min_msgs,
            min_node_prefix=args.min_node,
        )
    finally:
        db.close()

    print("=== Auditoria de Personalização (Copy + Contexto) ===")
    filt = r.get("filtros") or {}
    mn = filt.get("min_node_prefix")
    print(
        f"Janela: {r.get('window_hours')}h | Amostra: {r.get('sample_size')} leads"
        + (f" | min_node>={mn}" if mn is not None else "")
    )
    por_st = r.get("kpis_por_estagio") or {}
    if por_st:
        partes = [f"{k}: n={v.get('count')} média={v.get('score_medio')}" for k, v in sorted(por_st.items())]
        print("Por estágio (auditoria): " + " | ".join(partes))
    k = r.get("kpis", {}) or {}
    if not k:
        print("Sem dados suficientes na janela.")
        return

    print(
        f"Score médio: {k.get('score_medio')} | "
        f"Baixo(<55): {k.get('pct_baixo_lt55')}% | "
        f"Médio(55-74): {k.get('pct_medio_55_74')}% | "
        f"Alto(>=75): {k.get('pct_alto_ge75')}%"
    )
    print("\nTop diagnósticos:")
    for d, n in (k.get("diagnosticos_top", {}) or {}).items():
        print(f"  - {d}: {n}")

    print("\nLeads com maior risco (menor score):")
    for item in (r.get("top_risco", []) or [])[:10]:
        diags = ", ".join(item.get("diagnosticos", [])[:3]) or "-"
        print(
            f"  lead={item.get('lead_id')} tel={item.get('telefone')} "
            f"node={item.get('node_atual')} score={item.get('score_personalizacao')} "
            f"diag={diags}"
        )


if __name__ == "__main__":
    main()

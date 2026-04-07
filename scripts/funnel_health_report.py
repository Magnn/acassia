"""
Relatório ampliado de saúde do funil: matriz from→to, taxas aproximadas, export JSON.

Uso:
  python scripts/funnel_health_report.py
  python scripts/funnel_health_report.py --dias 30 --json relatorio.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import EventoAudit, Lead
from analytics.funnel_audit import EVENTO_NODE_TRANSITION, EVENTO_SILENT_ACK
from experiments.registry import listar_experimentos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=14, help="Janela para eventos (padrão 14)")
    ap.add_argument("--json", type=str, default="", help="Gravar saída estruturada em arquivo JSON")
    args = ap.parse_args()

    desde = datetime.now(timezone.utc) - timedelta(days=args.dias)

    db: Session = SessionLocal()
    report: dict = {"periodo_dias": args.dias, "desde_utc": desde.isoformat(), "snapshot": {}, "eventos_janela": {}}

    try:
        total = db.query(func.count(Lead.id)).scalar() or 0
        por_node = dict(
            db.query(Lead.node_atual, func.count(Lead.id))
            .group_by(Lead.node_atual)
            .all()
        )
        opt = db.query(func.count(Lead.id)).filter(Lead.opt_out.is_(True)).scalar() or 0
        conv = db.query(func.count(Lead.id)).filter(Lead.convertido.is_(True)).scalar() or 0

        report["snapshot"] = {
            "leads_total": total,
            "por_node_atual": por_node,
            "opt_out": opt,
            "convertidos_flag": conv,
        }

        q_tr = (
            db.query(EventoAudit)
            .filter(
                EventoAudit.timestamp >= desde,
                EventoAudit.evento == EVENTO_NODE_TRANSITION,
            )
            .all()
        )
        matriz: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        destinos = Counter()
        origens = Counter()
        for ev in q_tr:
            d = ev.dados or {}
            fr = str(d.get("from") or "")
            to = str(d.get("to") or "")
            if fr and to:
                matriz[fr][to] += 1
            destinos[to] += 1
            origens[fr] += 1

        silent = (
            db.query(func.count(EventoAudit.id))
            .filter(
                EventoAudit.timestamp >= desde,
                EventoAudit.evento == EVENTO_SILENT_ACK,
            )
            .scalar()
            or 0
        )
        recovery = (
            db.query(func.count(EventoAudit.id))
            .filter(
                EventoAudit.timestamp >= desde,
                EventoAudit.evento == "recovery_disparado",
            )
            .scalar()
            or 0
        )

        report["eventos_janela"] = {
            "transicoes": len(q_tr),
            "silent_ack": silent,
            "recovery_disparado": recovery,
            "top_origens": dict(origens.most_common(15)),
            "top_destinos": dict(destinos.most_common(15)),
            "matriz_from_to": {k: dict(v) for k, v in matriz.items()},
        }
        report["experimentos_registrados"] = listar_experimentos()

    finally:
        db.close()

    # stdout
    print("=== Funnel health report ===\n")
    print(f"Janela: últimos {args.dias} dias (desde {desde.date()} UTC)\n")
    s = report["snapshot"]
    print(f"Leads no banco: {s['leads_total']} | opt-out: {s['opt_out']} | convertidos: {s['convertidos_flag']}\n")
    ej = report["eventos_janela"]
    print(f"Transições auditadas: {ej['transicoes']} | silent_ack: {ej['silent_ack']} | recovery: {ej['recovery_disparado']}\n")
    if ej["top_destinos"]:
        print("Top destinos (to) na janela:")
        for n, c in list(ej["top_destinos"].items())[:10]:
            print(f"  {c:4d}  -> {n}")
        print()
    if ej["matriz_from_to"]:
        print("Amostra de fluxos from->to (contagem):")
        shown = 0
        for fr, dests in ej["matriz_from_to"].items():
            for to, c in sorted(dests.items(), key=lambda x: -x[1])[:3]:
                print(f"  {c:4d}  {fr} -> {to}")
                shown += 1
                if shown >= 15:
                    break
            if shown >= 15:
                break
        print()
    print(f"Experimentos no registro: {len(report['experimentos_registrados'])}\n")

    if args.json:
        out_path = os.path.abspath(args.json)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"JSON gravado em: {out_path}")


if __name__ == "__main__":
    main()

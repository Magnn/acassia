"""
Relatório rápido de funil (últimos 7 dias) — SQLite de produção local.
Sem PII: agrega por nó, eventos de auditoria e conversão.

Uso (na raiz do projeto):
  python scripts/metricas_semanais.py
  python scripts/metricas_semanais.py --dias 14
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import EventoAudit, Lead
from analytics.funnel_audit import EVENTO_NODE_TRANSITION, EVENTO_SILENT_ACK


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=7, help="Janela em dias (padrão 7)")
    args = ap.parse_args()

    desde = datetime.now(timezone.utc) - timedelta(days=args.dias)

    db: Session = SessionLocal()
    try:
        print(f"=== Métricas do funil (desde {desde.date()} UTC) ===\n")

        # Snapshot atual de leads (estado do funil)
        total_leads = db.query(func.count(Lead.id)).scalar() or 0
        por_node = (
            db.query(Lead.node_atual, func.count(Lead.id))
            .group_by(Lead.node_atual)
            .order_by(func.count(Lead.id).desc())
            .all()
        )
        print(f"Leads no banco (total): {total_leads}")
        print("Distribuição por node_atual (snapshot):")
        for node, n in por_node:
            print(f"  {n:4d}  {node or '(vazio)'}")
        print()

        opt = db.query(func.count(Lead.id)).filter(Lead.opt_out.is_(True)).scalar() or 0
        conv = db.query(func.count(Lead.id)).filter(Lead.convertido.is_(True)).scalar() or 0
        print(f"Opt-out (total): {opt} | Convertidos (flag): {conv}\n")

        # Eventos de transição (janela)
        q_tr = (
            db.query(EventoAudit)
            .filter(
                EventoAudit.timestamp >= desde,
                EventoAudit.evento == EVENTO_NODE_TRANSITION,
            )
            .all()
        )
        destinos = Counter()
        origens = Counter()
        for ev in q_tr:
            d = ev.dados or {}
            destinos[str(d.get("to") or "")] += 1
            origens[str(d.get("from") or "")] += 1

        print(f"Transições registradas ({EVENTO_NODE_TRANSITION}): {len(q_tr)}")
        if destinos:
            print("  Top destinos (to):")
            for node, n in destinos.most_common(12):
                if node:
                    print(f"    {n:4d}  -> {node}")
        print()

        q_sa = (
            db.query(func.count(EventoAudit.id))
            .filter(
                EventoAudit.timestamp >= desde,
                EventoAudit.evento == EVENTO_SILENT_ACK,
            )
            .scalar()
            or 0
        )
        print(f"Mensagens em estado silencioso ({EVENTO_SILENT_ACK}): {q_sa}\n")

        rec = (
            db.query(func.count(EventoAudit.id))
            .filter(
                EventoAudit.timestamp >= desde,
                EventoAudit.evento == "recovery_disparado",
            )
            .scalar()
            or 0
        )
        print(f"Recovery disparado (evento legado): {rec}\n")

    finally:
        db.close()

    print("Dica: exporte CSV do dashboard ou rode queries em `eventos_audit` para análises custom.")


if __name__ == "__main__":
    main()

"""
Linha do tempo de auditoria por lead (sem texto de mensagens — só eventos e nós).

Uso:
  python scripts/lead_journey.py 42
  python scripts/lead_journey.py 42 --limite 50
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from db.database import SessionLocal
from db.models import EventoAudit, Lead


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lead_id", type=int, help="ID do lead no banco")
    ap.add_argument("--limite", type=int, default=40, help="Máx. eventos (padrão 40)")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=args.lead_id).first()
        if not lead:
            print(f"Lead {args.lead_id} não encontrado.")
            sys.exit(1)

        print(f"Lead {lead.id} | node_atual: {lead.node_atual} | opt_out: {lead.opt_out} | convertido: {lead.convertido}\n")

        evs = (
            db.query(EventoAudit)
            .filter(EventoAudit.lead_id == args.lead_id)
            .order_by(EventoAudit.timestamp.desc())
            .limit(args.limite)
            .all()
        )
        if not evs:
            print("Nenhum evento em eventos_audit para este lead.")
            return

        for ev in reversed(evs):
            ts = ev.timestamp
            if isinstance(ts, datetime):
                ts_s = ts.isoformat()
            else:
                ts_s = str(ts)
            dados = ev.dados or {}
            extra = ""
            if ev.evento == "funnel.node_transition":
                extra = f" {dados.get('from')} -> {dados.get('to')} intent={dados.get('intencao')!r}"
            elif ev.evento == "funnel.silent_ack_user_text":
                extra = f" node={dados.get('node')!r}"
            print(f"{ts_s}  {ev.evento}{extra}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

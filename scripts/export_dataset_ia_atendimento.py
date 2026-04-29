"""
Exporta dataset passivo de comportamento dos leads para treino offline.

Uso:
  py scripts/export_dataset_ia_atendimento.py --out scripts/reports/dataset_ia_atendimento.jsonl
  py scripts/export_dataset_ia_atendimento.py --format csv --out scripts/reports/dataset_ia_atendimento.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from db.database import SessionLocal
from db.models import LeadBehaviorEvent


def _iter_rows(limit: int, tenant_id: str | None) -> Iterable[LeadBehaviorEvent]:
    db = SessionLocal()
    try:
        q = db.query(LeadBehaviorEvent).order_by(LeadBehaviorEvent.id.asc())
        if tenant_id:
            q = q.filter(LeadBehaviorEvent.tenant_id == tenant_id)
        if limit > 0:
            q = q.limit(limit)
        for row in q.all():
            yield row
    finally:
        db.close()


def _flatten(row: LeadBehaviorEvent) -> Dict[str, Any]:
    payload = row.payload if isinstance(row.payload, dict) else {}
    snap = payload.get("snapshot_fase1") if isinstance(payload.get("snapshot_fase1"), dict) else {}
    acoes = payload.get("acoes") if isinstance(payload.get("acoes"), dict) else {}
    return {
        "id": int(row.id),
        "timestamp": str(row.timestamp.isoformat() if row.timestamp else ""),
        "tenant_id": str(row.tenant_id or "default"),
        "lead_id": int(row.lead_id),
        "event_type": str(row.event_type or ""),
        "node_atual": str(row.node_atual or ""),
        "tipo_mensagem": str(payload.get("tipo_mensagem") or ""),
        "texto_chars": int(payload.get("texto_chars") or 0),
        "foto_atual": bool(payload.get("foto_atual")),
        "sniffer_eventos": list(payload.get("sniffer_eventos") or []),
        "intencao": str(payload.get("intencao") or ""),
        "sentimento": str(payload.get("sentimento") or ""),
        "snapshot_nome_ok": bool(snap.get("nome_util_ok")),
        "snapshot_contato_ok": bool(snap.get("contato_ok")),
        "snapshot_foto_ok": bool(snap.get("foto_ok")),
        "snapshot_desabafo_ok": bool(snap.get("desabafo_ok")),
        "snapshot_burst_elegivel": bool(snap.get("burst_elegivel")),
        "snapshot_pendencias": list(snap.get("pendencias") or []),
        "acoes_total": int(acoes.get("total") or 0),
        "acoes_textos": int(acoes.get("textos") or 0),
        "acoes_delays": int(acoes.get("delays") or 0),
        "acoes_midias": int(acoes.get("midias") or 0),
        "acoes_audios_tts": int(acoes.get("audios_tts") or 0),
        "acoes_vcards": int(acoes.get("vcards") or 0),
        "acoes_delay_total_s": int(acoes.get("delay_total_s") or 0),
    }


def _write_jsonl(rows: List[Dict[str, Any]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _write_csv(rows: List[Dict[str, Any]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys()) if rows else []
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            item = dict(r)
            item["sniffer_eventos"] = json.dumps(item.get("sniffer_eventos", []), ensure_ascii=False)
            item["snapshot_pendencias"] = json.dumps(item.get("snapshot_pendencias", []), ensure_ascii=False)
            w.writerow(item)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Caminho de saída (.jsonl ou .csv)")
    ap.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    ap.add_argument("--limit", type=int, default=0, help="0 = sem limite")
    ap.add_argument("--tenant-id", default="", help="Filtra por tenant_id (opcional)")
    args = ap.parse_args()

    rows = [_flatten(r) for r in _iter_rows(limit=max(0, int(args.limit or 0)), tenant_id=(args.tenant_id or "").strip() or None)]
    out = Path(args.out)
    if args.format == "csv":
        _write_csv(rows, out)
    else:
        _write_jsonl(rows, out)

    print(json.dumps({"ok": True, "rows": len(rows), "format": args.format, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

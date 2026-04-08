"""
Ranking rápido de nós por lentidão e verbosidade via logs do engine.

Uso:
  python scripts/ranking_nodes_telemetria.py --log app.log
  python scripts/ranking_nodes_telemetria.py --log logs/app.log --top 8
"""

from __future__ import annotations

import argparse
import math
import os
import re
from collections import defaultdict


_RE_KV = re.compile(r"(\w+)=([^\s]+)")


def _parse_kv(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in _RE_KV.findall(line or ""):
        out[k] = v.strip()
    return out


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    if len(arr) == 1:
        return arr[0]
    k = (len(arr) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return arr[int(k)]
    return arr[f] * (c - k) + arr[c] * (k - f)


def _safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: str, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=str, default="app.log", help="Arquivo de log para leitura")
    ap.add_argument("--top", type=int, default=10, help="Quantidade de nós no ranking")
    args = ap.parse_args()

    log_path = os.path.abspath(args.log)
    if not os.path.exists(log_path):
        raise SystemExit(f"Arquivo não encontrado: {log_path}")

    by_node: dict[str, dict[str, list[float] | int]] = defaultdict(
        lambda: {
            "elapsed_s": [],
            "acoes": [],
            "textos": [],
            "delay_total_s": [],
            "pergunta_final_true": 0,
            "pergunta_final_total": 0,
        }
    )

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if "event=node_exec_timing" in line:
                kv = _parse_kv(line)
                node = kv.get("node", "").strip()
                if not node:
                    continue
                by_node[node]["elapsed_s"].append(_safe_float(kv.get("elapsed_s", "0")))
                by_node[node]["acoes"].append(_safe_float(kv.get("acoes", "0")))
            elif "event=node_turn_telemetry" in line:
                kv = _parse_kv(line)
                node = kv.get("node", "").strip()
                if not node:
                    continue
                by_node[node]["textos"].append(_safe_float(kv.get("textos", "0")))
                by_node[node]["delay_total_s"].append(_safe_float(kv.get("delay_total_s", "0")))
                by_node[node]["pergunta_final_total"] += 1
                if str(kv.get("pergunta_final", "")).lower() in {"true", "1", "yes"}:
                    by_node[node]["pergunta_final_true"] += 1

    ranking: list[dict[str, float | int | str]] = []
    for node, d in by_node.items():
        elapsed = d["elapsed_s"]
        acoes = d["acoes"]
        textos = d["textos"]
        delays = d["delay_total_s"]
        q_total = int(d["pergunta_final_total"])
        q_true = int(d["pergunta_final_true"])
        ranking.append(
            {
                "node": node,
                "amostras_exec": len(elapsed),
                "p50_elapsed_s": _pct(elapsed, 0.50),
                "p90_elapsed_s": _pct(elapsed, 0.90),
                "avg_acoes": (sum(acoes) / len(acoes)) if acoes else 0.0,
                "avg_textos": (sum(textos) / len(textos)) if textos else 0.0,
                "avg_delay_total_s": (sum(delays) / len(delays)) if delays else 0.0,
                "pergunta_final_rate": (q_true / q_total) if q_total > 0 else 0.0,
            }
        )

    # Score único simples: mais peso para latência p90, depois volume e delay total.
    ranking.sort(
        key=lambda r: (
            float(r["p90_elapsed_s"]) * 0.6
            + float(r["avg_acoes"]) * 0.25
            + float(r["avg_delay_total_s"]) * 0.15
        ),
        reverse=True,
    )

    top = max(1, int(args.top))
    print("=== Ranking de Nós (lentidão + verbosidade) ===")
    print(f"Log: {log_path}\n")
    print(
        "node | amostras | p50_s | p90_s | avg_acoes | avg_textos | avg_delay_s | pergunta_final_rate"
    )
    for r in ranking[:top]:
        print(
            f"{r['node']} | {int(r['amostras_exec'])} | "
            f"{float(r['p50_elapsed_s']):.2f} | {float(r['p90_elapsed_s']):.2f} | "
            f"{float(r['avg_acoes']):.1f} | {float(r['avg_textos']):.1f} | "
            f"{float(r['avg_delay_total_s']):.1f} | {float(r['pergunta_final_rate']) * 100:.0f}%"
        )

    if not ranking:
        print("Nenhum evento de telemetria encontrado (node_exec_timing/node_turn_telemetry).")


if __name__ == "__main__":
    main()


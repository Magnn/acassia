from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "scripts" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)


def _run_py(script_rel: str, *args: str) -> Tuple[int, str]:
    cmd = [sys.executable, str(ROOT / script_rel), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    return p.returncode, out.strip()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _build_markdown(report: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Release Gate Funil")
    lines.append("")
    lines.append(f"- Gerado em: `{report.get('generated_at', '-')}`")
    lines.append(f"- Status final: `{report.get('status', '-')}`")
    lines.append("")

    g = report.get("guardrails", {})
    e = report.get("e2e", {})
    q = report.get("qa_copy", {})
    lines.append("## Resultado dos Gates")
    lines.append(f"- Guardrails: `{g.get('status', '-')}`")
    lines.append(f"- Simulacao E2E: `{e.get('status', '-')}` | score `{e.get('score', '-')}`")
    if q:
        lines.append(f"- QA copy: `{q.get('status', '-')}`")
    else:
        lines.append("- QA copy: `nao executado`")
    lines.append("")

    if e.get("score_by_stage"):
        lines.append("## Score por Estagio (E2E)")
        for stage, st in e["score_by_stage"].items():
            lines.append(
                f"- `{stage}`: score `{st.get('score')}` ({st.get('passed')}/{st.get('total')})"
            )
        lines.append("")

    if report.get("baseline_comparison"):
        b = report["baseline_comparison"]
        lines.append("## Comparativo com Baseline")
        lines.append(f"- Baseline score: `{b.get('baseline_score', '-')}`")
        lines.append(f"- Atual score: `{b.get('current_score', '-')}`")
        lines.append(f"- Delta: `{b.get('delta', '-')}`")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--qa-score-json",
        type=str,
        default="",
        help="Caminho do JSON de score QA copy (opcional)",
    )
    ap.add_argument(
        "--baseline-e2e",
        type=str,
        default="",
        help="Caminho para report JSON E2E baseline (opcional)",
    )
    args = ap.parse_args()

    rc_g, out_g = _run_py("scripts/verificar_guardrails_funil.py")
    rc_e, out_e = _run_py("scripts/simular_funil_e2e.py")

    e2e_report_path = REPORTS / "simular_funil_e2e_report.json"
    e2e_json = _load_json(e2e_report_path)

    qa_obj: Dict[str, Any] = {}
    if args.qa_score_json:
        rc_q, out_q = _run_py("scripts/calcular_score_qa_copy.py", args.qa_score_json)
        qa_obj = {
            "status": "ok" if rc_q == 0 else "fail",
            "exit_code": rc_q,
            "output_excerpt": out_q[-1400:],
        }

    comp: Dict[str, Any] = {}
    if args.baseline_e2e:
        base = _load_json(Path(args.baseline_e2e))
        if base:
            bs = float(base.get("score", 0.0) or 0.0)
            cs = float(e2e_json.get("score", 0.0) or 0.0)
            comp = {
                "baseline_path": str(Path(args.baseline_e2e)),
                "baseline_score": bs,
                "current_score": cs,
                "delta": round(cs - bs, 2),
            }

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if (rc_g == 0 and rc_e == 0) else "fail",
        "guardrails": {
            "status": "ok" if rc_g == 0 else "fail",
            "exit_code": rc_g,
            "output_excerpt": out_g[-1000:],
        },
        "e2e": {
            "status": "ok" if rc_e == 0 else "fail",
            "exit_code": rc_e,
            "score": e2e_json.get("score"),
            "score_by_stage": e2e_json.get("score_by_stage", {}),
            "results": e2e_json.get("results", []),
            "output_excerpt": out_e[-1000:],
        },
    }
    if qa_obj:
        report["qa_copy"] = qa_obj
    if comp:
        report["baseline_comparison"] = comp

    out_json = REPORTS / "release_gate_report.json"
    out_md = REPORTS / "release_gate_report.md"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_build_markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())


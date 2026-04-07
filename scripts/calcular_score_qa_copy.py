from __future__ import annotations

import json
import sys
from pathlib import Path


GATE_KEYS = {
    "coleta_pergunta_com_pausa",
    "node7_reage_ultimo_input",
    "node7_mecanismo_nome_especifico",
    "node7_urgencia_real",
    "node8_negociacao_escada_correta",
    "conv_sem_atropelo",
}


def _score_items(items: dict) -> tuple[int, int, list[str], list[str]]:
    points = 0
    max_points = 0
    critical_fails: list[str] = []
    gate_fails: list[str] = []

    for key, cfg in items.items():
        critical = bool(cfg.get("critical", False))
        passed = bool(cfg.get("pass", False))
        weight = 4 if critical else 2
        max_points += weight
        if passed:
            points += weight
        elif critical:
            critical_fails.append(key)
            if key in GATE_KEYS:
                gate_fails.append(key)

    return points, max_points, critical_fails, gate_fails


def _decision(score: float, critical_fails: list[str], gate_fails: list[str]) -> str:
    if gate_fails:
        return "REPROVADO (gate de seguranca)"
    if critical_fails:
        return "REPROVADO (falha em item critico)"
    if score >= 90:
        return "ESCALAR TRAFEGO"
    if score >= 80:
        return "AJUSTAR FINO E RETESTAR"
    if score >= 70:
        return "FRACO PARA LEAD MORNO"
    return "REPROVADO"


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: py scripts/calcular_score_qa_copy.py scripts/qa_copy_score_template.json")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Arquivo nao encontrado: {path}")
        return 1

    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios", {})
    if not scenarios:
        print("JSON invalido: sem 'scenarios'.")
        return 1

    print(f"=== QA COPY SCORE :: {payload.get('version_label', '-') } ===")
    print(f"Data: {payload.get('date', '-')}")
    print()

    all_scores = []
    for sid in ("A", "B", "C"):
        sc = scenarios.get(sid, {})
        name = sc.get("name", sid)
        items = sc.get("items", {}) or {}
        if not items:
            print(f"[{sid}] {name}: sem itens preenchidos.")
            print()
            continue
        pts, max_pts, crit_fails, gate_fails = _score_items(items)
        score = round((pts / max_pts) * 100, 2) if max_pts else 0.0
        all_scores.append(score)
        dec = _decision(score, crit_fails, gate_fails)

        print(f"[{sid}] {name}")
        print(f"- Score: {score} ({pts}/{max_pts})")
        print(f"- Criticos com FAIL: {len(crit_fails)}")
        if crit_fails:
            print(f"- Lista criticos FAIL: {', '.join(crit_fails)}")
        if gate_fails:
            print(f"- Gate FAIL: {', '.join(gate_fails)}")
        print(f"- Decisao: {dec}")
        print()

    if all_scores:
        avg = round(sum(all_scores) / len(all_scores), 2)
        print(f"Media geral: {avg}")
    else:
        print("Media geral: sem dados suficientes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


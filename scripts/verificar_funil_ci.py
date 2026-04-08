#!/usr/bin/env python3
"""
Smoke CI do funil: unittest (tests/), guardrails de strings, sequências agregadas, simular_funil_e2e.

Uso: python scripts/verificar_funil_ci.py
Saída: 0 se tudo OK; caso contrário propaga o primeiro código de saída != 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> int:
    return subprocess.call(args, cwd=str(ROOT))


def main() -> int:
    steps = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"],
        [sys.executable, str(ROOT / "scripts" / "verificar_guardrails_funil.py")],
        [sys.executable, str(ROOT / "scripts" / "teste_funnel_sequencias.py")],
        [sys.executable, str(ROOT / "scripts" / "simular_funil_e2e.py")],
    ]
    for cmd in steps:
        code = _run(cmd)
        if code != 0:
            return code
    print("FUNIL CI OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

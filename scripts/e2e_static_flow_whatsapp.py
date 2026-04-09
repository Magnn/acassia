#!/usr/bin/env python3
"""
E2E: sobe o Flask (subprocess), importa o template do funil estático, cria lead se precisar,
chama POST /api/flows/blueprints/<id>/execute.

Uso:
  python scripts/e2e_static_flow_whatsapp.py
  python scripts/e2e_static_flow_whatsapp.py 5511999887766
  FLOW_TEST_LEAD_PHONE=5511... python scripts/e2e_static_flow_whatsapp.py

Sem número: usa placeholder 5511999999999 (a Meta pode não entregar; troque pelo seu DDI+DDD+número).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.error import URLError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _http_json(method: str, url: str, body: dict | None = None, tenant: str = "default") -> tuple[int, dict]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"X-Acassia-Tenant": tenant}
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except URLError:
        return 0, {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"error": raw}


def _wait_app(base: str, tenant: str, seconds: float = 45.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        code, _ = _http_json("GET", f"{base}/api/stats", None, tenant)
        if code == 200:
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    os.chdir(ROOT)
    base = os.getenv("E2E_APP_URL", "http://127.0.0.1:5000").rstrip("/")
    tenant = os.getenv("ACASSIA_TENANT_ID", "default").strip() or "default"
    phone = (
        (sys.argv[1].strip() if len(sys.argv) > 1 else "")
        or os.getenv("FLOW_TEST_LEAD_PHONE", "").strip()
        or "5511999999999"
    )
    public_url = os.getenv("PUBLIC_URL", base).rstrip("/")

    env = os.environ.copy()
    env.setdefault("ACASSIA_TENANT_ID", tenant)
    env["PUBLIC_URL"] = public_url

    proc: subprocess.Popen | None = None
    code0, _ = _http_json("GET", f"{base}/api/stats", None, tenant)
    if code0 == 200:
        print("=== 1) App já estava no ar (pulando subprocess) ===")
    else:
        print("=== 1) Subindo app.py (subprocess) ===")
        kw: dict = {
            "cwd": str(ROOT),
            "env": env,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        proc = subprocess.Popen([sys.executable, "app.py"], **kw)
        if not _wait_app(base, tenant):
            print("ERRO: app não respondeu em /api/stats a tempo.", file=sys.stderr)
            if proc:
                proc.terminate()
            return 1

    try:
        print("=== 2) Lead no SQLite ===")
        sys.path.insert(0, str(ROOT))
        from db.database import SessionLocal
        from db import models

        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter_by(tenant_id=tenant, telefone=phone).first()
            if not lead:
                lead = models.Lead(tenant_id=tenant, telefone=phone, nome="Teste funil estático")
                db.add(lead)
                db.commit()
                db.refresh(lead)
                print(f"Criado lead id={lead.id} telefone={phone}")
            else:
                print(f"Usando lead id={lead.id} telefone={phone}")
            lead_id = lead.id
        finally:
            db.close()

        tpl = ROOT / "docs" / "templates" / "funil_estatico_meu_misterio_bloco1.acassia-flow.json"
        doc = json.loads(tpl.read_text(encoding="utf-8"))
        slug = f"meu_misterio_est_{int(time.time())}"
        payload = {
            "title": doc.get("title") or "Funil estático Meu Mistério",
            "slug": slug,
            "body": doc,
        }

        print("=== 3) Import blueprint ===")
        code, out = _http_json("POST", f"{base}/api/flows/blueprints/import", payload, tenant)
        if code not in (200, 201) or not out.get("ok"):
            print(json.dumps(out, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        bid = out["blueprint"]["id"]
        print(f"blueprint_id={bid} slug={slug}")

        print("=== 4) Execute (fila WhatsApp) ===")
        code, ex = _http_json(
            "POST",
            f"{base}/api/flows/blueprints/{bid}/execute",
            {"lead_id": lead_id},
            tenant,
        )
        print(json.dumps(ex, ensure_ascii=False, indent=2))
        if code != 200 or not ex.get("ok"):
            return 1

        print("\nOK. Verifique o WhatsApp do número:", phone)
        print("Se não chegou nada: confira token Meta, PUBLIC_URL=https (túnel) para mídia, e troque o placeholder pelo seu número.")
        return 0
    finally:
        if proc is not None:
            print("\n=== Encerrando subprocess do app ===")
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())

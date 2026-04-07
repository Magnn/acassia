"""
Valida API de mensagens (media_url) e rota /media/ sem subir servidor manualmente.
Uso: py scripts/validate_chat_media.py
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# PNG 1x1 mínimo
_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500001d0d4e120000000049454e44ae426082"
)


def main() -> int:
    from datetime import datetime, timezone

    from app import app
    from db.database import SessionLocal
    from db import models

    dl = os.path.join(_ROOT, "downloads")
    os.makedirs(dl, exist_ok=True)
    fname = "test_chat_media.png"
    fpath = os.path.join(dl, fname)
    with open(fpath, "wb") as f:
        f.write(_PNG_1X1)

    rel_url = f"/media/{fname}"
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(tenant_id="default").first()
        if not lead:
            lead = models.Lead(telefone="5599999999999", tenant_id="default", node_atual="1_apresentacao")
            db.add(lead)
            db.commit()
            db.refresh(lead)

        db.add(
            models.Mensagem(
                lead_id=lead.id,
                remetente="user",
                texto="legenda teste imagem",
                tipo="image",
                media_url=rel_url,
                timestamp=datetime.now(timezone.utc),
            )
        )
        db.add(
            models.Mensagem(
                lead_id=lead.id,
                remetente="user",
                texto="transcrição teste áudio",
                tipo="audio",
                media_url="/media/test_chat_media.png",
                timestamp=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()

    with app.test_client() as c:
        r = c.get(f"/api/leads/{lead.id}/messages?limit=50")
        assert r.status_code == 200, r.data
        data = r.get_json()
        msgs = data.get("messages") or []
        with_media = [m for m in msgs if m.get("media_url")]
        assert any(m.get("tipo") == "image" and m.get("media_url") == rel_url for m in msgs), msgs
        assert any(m.get("tipo") == "audio" and m.get("media_url") for m in msgs), msgs

        rm = c.get(rel_url)
        assert rm.status_code == 200, rm.status_code
        assert rm.data[:8] == b"\x89PNG\r\n\x1a\n", "bytes PNG"

    print(f"OK: lead_id={lead.id} — API retorna media_url; GET {rel_url} -> 200 ({len(with_media)} msgs com mídia no lote)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
E2E leve: SQLite em memória + modelo Lead + metadata_json após sniffer (sem Engine/WhatsApp).
"""

from __future__ import annotations

import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, Lead
from flows.funnel_gates import sniffer_aplicar_fase1_flags, snapshot_fase1_coleta


class TestSqliteLeadMetadataSnifferE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_persistencia_metadata_apos_sniffer(self):
        db: Session = self.Session()
        try:
            lead = Lead(
                tenant_id="default",
                telefone="+5591999998888",
                node_atual="1_apresentacao",
                nome="Ana",
                metadata_json={},
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)

            meta = dict(lead.metadata_json or {})
            txt = "já salvei " + "x " * 20 + "estou com muita dor e medo na relação"
            sniffer_aplicar_fase1_flags(
                meta,
                tipo_mensagem="text",
                texto_sniff=txt,
                historico=[],
            )
            lead.metadata_json = meta
            db.commit()
            db.refresh(lead)

            raw = json.dumps(lead.metadata_json, ensure_ascii=False)
            roundtrip = json.loads(raw)
            self.assertTrue(roundtrip.get("desabafo_recebido"))
            self.assertTrue(roundtrip.get("lead_contato_salvo_declarado"))

            snap = snapshot_fase1_coleta(roundtrip, "Ana", txt)
            self.assertTrue(snap["nome_util_ok"])
            self.assertTrue(snap["contato_ok"])
            self.assertTrue(snap["desabafo_ok"])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

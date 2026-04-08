"""
E2E do `Engine.processar_mensagem`: DB em memória, NLU mockada, fila e recovery isolados.
Valida que o sniffer + persistência de `metadata_json` funcionam no caminho real do motor.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, Lead
from engine import Engine


class TestEngineProcessarSnifferMetadata(unittest.TestCase):
    def setUp(self) -> None:
        self.mem = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.mem)
        self.Session = sessionmaker(bind=self.mem)

        def sess_factory():
            return self.Session()

        self.sess_factory = sess_factory

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.mem)
        self.mem.dispose()

    def _engine_and_run(self, tel: str, texto: str, **kwargs):
        ic = MagicMock()
        ic.classificar = Mock(return_value="padrao")
        sa = MagicMock()
        sa.analisar = Mock(return_value={"sentimento": "padrao", "score": 0.5})
        rec = MagicMock()
        rec.iniciar_monitor = Mock()
        with patch.multiple(
            "engine",
            RecoveryEngine=Mock(return_value=rec),
            IntentClassifier=Mock(return_value=ic),
            SentimentAnalyzer=Mock(return_value=sa),
            ResponseValidator=Mock(return_value=MagicMock()),
            ContextCompressor=Mock(return_value=MagicMock()),
            SessionLocal=self.sess_factory,
        ):
            eng = Engine(
                "token_teste",
                "phone_id_teste",
                gemini_api_key="dummy",
                tts_ativo=False,
                tenant_id="default",
            )
            with patch("threading.Thread", return_value=MagicMock(start=Mock())):
                with patch.object(eng, "_pular_nlu_ia", return_value=True):
                    with patch.object(eng, "_processar_fila", Mock()):
                        with patch.object(eng, "_rotear_state_machine", Mock(return_value=[])):
                            return eng.processar_mensagem(tel, texto, **kwargs)

    def test_foto_recebida_persiste_via_processar_mensagem(self):
        tel = "+5591887766554"
        out = self._engine_and_run(tel, "", tipo_mensagem="image")
        self.assertEqual(out.get("status"), "ok")

        db = self.Session()
        try:
            lead = db.query(Lead).filter_by(telefone=tel, tenant_id="default").first()
            self.assertIsNotNone(lead)
            meta = dict(lead.metadata_json or {})
            self.assertTrue(meta.get("foto_recebida"), meta)
        finally:
            db.close()

    def test_desabafo_e_contato_no_metadata_apos_texto_longo(self):
        tel = "+5591998877665"
        txt = (
            "já salvei seu contato no celular agora "
            + " ".join(["palavra"] * 25)
            + " estou com muita dor e medo na relação com meu marido"
        )
        out = self._engine_and_run(tel, txt, tipo_mensagem="text")
        self.assertEqual(out.get("status"), "ok")

        db = self.Session()
        try:
            lead = db.query(Lead).filter_by(telefone=tel, tenant_id="default").first()
            self.assertIsNotNone(lead)
            meta = dict(lead.metadata_json or {})
            self.assertTrue(meta.get("lead_contato_salvo_declarado"), meta)
            self.assertTrue(meta.get("desabafo_recebido"), meta)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from types import SimpleNamespace

from engine import Engine


class TestEngineEntryPolicy(unittest.TestCase):
    def test_lead_comprador_ou_pos_funil_desvia(self):
        lead = SimpleNamespace(convertido=True, produto_comprado="", metadata_json={})
        self.assertTrue(Engine._lead_ja_passou_funil_ou_comprou(lead))

        lead = SimpleNamespace(convertido=False, produto_comprado="ritual x", metadata_json={})
        self.assertTrue(Engine._lead_ja_passou_funil_ou_comprou(lead))

    def test_lead_ja_atendido_desvia(self):
        lead = SimpleNamespace(
            convertido=False,
            produto_comprado="",
            metadata_json={"ja_recebeu_atendimento": True},
        )
        self.assertTrue(Engine._lead_ja_passou_funil_ou_comprou(lead))

        lead = SimpleNamespace(
            convertido=False,
            produto_comprado="",
            metadata_json={"departamento_humano_ativo": True},
        )
        self.assertTrue(Engine._lead_ja_passou_funil_ou_comprou(lead))


if __name__ == "__main__":
    unittest.main()

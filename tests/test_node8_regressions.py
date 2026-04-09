from __future__ import annotations

import unittest

from flows.fase_3_oferta import node_8_oferta_principal as n8
from schema import ContextoConversa


class TestNode8Regressoes(unittest.TestCase):
    def test_historico_limpo_remove_pipe_e_ruido_curto(self):
        ctx = ContextoConversa(
            lead_id=1,
            telefone="+5592999999999",
            node_atual="8_oferta_principal",
            texto_recebido="ok",
            historico=[
                {"remetente": "user", "texto": "oi"},
                {"remetente": "user", "texto": "sim"},
                {"remetente": "user", "texto": "quero resolver isso | sem sofrer"},
            ],
        )
        out = n8._historico_limpo_para_ia(ctx)
        joined = " ".join(str(x.get("texto", "")) for x in out).lower()
        self.assertNotIn("|", joined)
        self.assertNotIn(" oi ", f" {joined} ")
        self.assertNotIn(" sim ", f" {joined} ")
        self.assertIn("quero resolver isso", joined)


if __name__ == "__main__":
    unittest.main()

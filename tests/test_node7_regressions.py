"""Regressões de copy do Node 7 (agitação)."""

from __future__ import annotations

import unittest

from flows.fase_2_leitura import node_7_interesse_desejo as n7
from schema import ContextoConversa


class TestNode7Regressoes(unittest.TestCase):
    def test_sanear_citacao_aberta_remove_aspas_soltas(self):
        txt = "Quando você me diz 'Bom dia tudo bem? essa consulta é paga?"
        out = n7._sanear_citacoes_abertas(txt)
        self.assertNotIn("'", out)
        self.assertIn("Bom dia tudo bem?", out)

    def test_historico_limpo_remove_ruido_curto_e_pipe(self):
        ctx = ContextoConversa(
            lead_id=1,
            telefone="+5592999999999",
            node_atual="7_interesse_desejo",
            texto_recebido="ok",
            historico=[
                {"remetente": "user", "texto": "oi"},
                {"remetente": "user", "texto": "sim"},
                {"remetente": "user", "texto": "minha mulher me deixou | quero saber se tem volta"},
            ],
        )
        out = n7._historico_limpo_para_ia(ctx)
        joined = " ".join(str(x.get("texto", "")) for x in out).lower()
        self.assertNotIn("|", joined)
        self.assertNotIn(" oi ", f" {joined} ")
        self.assertNotIn(" sim ", f" {joined} ")
        self.assertIn("minha mulher me deixou", joined)


if __name__ == "__main__":
    unittest.main()

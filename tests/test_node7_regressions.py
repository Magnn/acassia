"""Regressões de copy do Node 7 (agitação)."""

from __future__ import annotations

import unittest

from flows.fase_2_leitura import node_7_interesse_desejo as n7


class TestNode7Regressoes(unittest.TestCase):
    def test_sanear_citacao_aberta_remove_aspas_soltas(self):
        txt = "Quando você me diz 'Bom dia tudo bem? essa consulta é paga?"
        out = n7._sanear_citacoes_abertas(txt)
        self.assertNotIn("'", out)
        self.assertIn("Bom dia tudo bem?", out)


if __name__ == "__main__":
    unittest.main()

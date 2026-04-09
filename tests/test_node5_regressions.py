"""Regressões de higiene de contexto no Node 5."""

from __future__ import annotations

import unittest

from flows.fase_2_leitura import node_5_processa_leitura as n5


class TestNode5Regressoes(unittest.TestCase):
    def test_montagem_contexto_filtra_ruido_operacional(self):
        out = n5._montar_texto_contexto_node5(
            desabafo_pre="Estou há 2 anos sofrendo com esse relacionamento.",
            contexto_extra="Bom dia tudo bem? essa consulta é paga?",
            msg_lead="sim",
        )
        low = out.lower()
        self.assertIn("há 2 anos", low)
        self.assertNotIn("consulta é paga", low)
        self.assertNotIn("bom dia", low)


if __name__ == "__main__":
    unittest.main()

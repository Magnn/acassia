"""Evita duplicar a última mensagem do cliente no bloco HISTÓRICO."""
import unittest

from personalizer import Personalizer


class _M:
    def __init__(self, remetente: str, texto: str):
        self.remetente = remetente
        self.texto = texto


class TestFormatarHistoricoDedupe(unittest.TestCase):
    def test_remove_ultima_se_igual_a_mensagem_lead(self):
        p = Personalizer.__new__(Personalizer)
        hist = [
            _M("user", "oi"),
            _M("bot", "tudo bem"),
            _M("user", "quanto é"),
        ]
        out = Personalizer._formatar_historico(p, hist, mensagem_lead="quanto é")
        self.assertNotIn("quanto é", out)
        self.assertIn("tudo bem", out)

    def test_mantem_se_mensagem_lead_diferente(self):
        p = Personalizer.__new__(Personalizer)
        hist = [_M("user", "oi"), _M("user", "e ai")]
        out = Personalizer._formatar_historico(p, hist, mensagem_lead="novo texto")
        self.assertIn("e ai", out)


if __name__ == "__main__":
    unittest.main()

import unittest

from copy_sanitizer import extrair_evidencias_conversa, sanitizar_anti_ia


class TestSpacing(unittest.TestCase):
    def test_espaco_apos_ponto(self):
        self.assertIn(". Estou", sanitizar_anti_ia("Olá.Estou aqui"))

    def test_virgula(self):
        s = sanitizar_anti_ia("sim,ok")
        self.assertIn(", ok", s)

    def test_extrair_evidencias_nome_ok_respeita_placeholders_funnel(self):
        base = dict(texto_atual="", tipo_mensagem_atual="text", historico=[], metadata={})
        self.assertFalse(
            extrair_evidencias_conversa(**base, nome_lead="minha estrela")["nome_ok"]
        )
        self.assertTrue(extrair_evidencias_conversa(**base, nome_lead="Heloísa")["nome_ok"])


if __name__ == "__main__":
    unittest.main()

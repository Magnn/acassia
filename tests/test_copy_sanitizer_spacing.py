import unittest

from copy_sanitizer import (
    extrair_evidencias_conversa,
    motivo_redundancia_texto,
    sanitizar_anti_ia,
)


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

    def test_extrair_evidencias_sim_nao_e_nome_ok(self):
        ev = extrair_evidencias_conversa(
            texto_atual="",
            tipo_mensagem_atual="text",
            historico=[],
            metadata={},
            nome_lead="sim",
        )
        self.assertFalse(ev["nome_ok"])

    def test_contato_ritual_ok_com_vcard_metadata(self):
        ev = extrair_evidencias_conversa(
            texto_atual="ok",
            tipo_mensagem_atual="text",
            historico=[],
            metadata={"node2_vcard_despachado": True},
            nome_lead="Bia",
        )
        self.assertTrue(ev["contato_ritual_ok"])

    def test_motivo_redundancia_contato_quando_ritual_ok(self):
        ev = {
            "nome_ok": True,
            "contato_ritual_ok": True,
            "tem_foto": False,
            "tem_desabafo": False,
            "tem_desejo": False,
            "tem_aprofundamento": False,
            "confirmou_agora": False,
            "confirmou_comercial_agora": False,
            "node8_fase_esperando_firmo": False,
        }
        m = motivo_redundancia_texto(
            "Quando der, salvar o seu contato aqui no WhatsApp.",
            ev,
        )
        self.assertEqual(m, "contato_ja_tratado")


if __name__ == "__main__":
    unittest.main()

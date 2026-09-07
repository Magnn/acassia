"""Testes do funil estático Meu Mistério — bloco 2."""
import unittest

from schema import ContextoConversa

from flows.funil_estatico_meu_misterio import node_static_meumisterio_b2 as b2
from flows.funil_estatico_meu_misterio import roteiro as R


class TestStaticMeumisterioB2(unittest.TestCase):
    def _ctx(self, **kw):
        defaults = dict(
            lead_id=1,
            telefone="5599999999999",
            node_atual="static_meumisterio_b2",
            texto_recebido="",
            tipo_mensagem="text",
            historico=[],
            metadata={
                "__config__": {
                    "public_url": "https://example.com",
                    "link_prova_social": "https://www.instagram.com/meumisterio_oficial",
                }
            },
        )
        defaults.update(kw)
        return ContextoConversa(**defaults)

    def test_primeira_execucao_tem_delays_texto_audio_pergunta(self):
        ctx = self._ctx(texto_recebido="ok")
        acoes, prox = b2.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b2")
        self.assertTrue(ctx.metadata.get("static_mm_b2_seq_dispatched"))
        self.assertEqual(ctx.metadata.get("static_mm_b2_phase"), "awaiting_nome_amado")
        delays = [a.segundos for a in acoes if a.tipo == "delay"]
        self.assertIn(0, delays)
        self.assertIn(R.B2_DELAY_PRE_AUDIO_S, delays)
        self.assertIn(R.B2_DELAY_POS_AUDIO_S, delays)
        tipos = [a.tipo for a in acoes]
        self.assertIn("text", tipos)
        self.assertGreaterEqual(tipos.count("text"), 2)

    def test_resposta_nome_avanca_b3(self):
        ctx = self._ctx(
            texto_recebido="Maria",
            metadata={
                "__config__": {"public_url": "https://example.com"},
                "static_mm_b2_phase": "awaiting_nome_amado",
                "static_mm_b2_seq_dispatched": True,
                "static_mm_b2_entregue": True,
            },
        )
        acoes, prox = b2.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b3")
        self.assertEqual(acoes, [])
        self.assertIn("Maria", (ctx.metadata.get("nome_pessoa_amada_b2") or ""))


if __name__ == "__main__":
    unittest.main()

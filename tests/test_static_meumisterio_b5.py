"""Testes do funil estático Meu Mistério — bloco 5."""
import unittest

from schema import ContextoConversa

from flows.funil_estatico_meu_misterio import node_static_meumisterio_b5 as b5
from flows.funil_estatico_meu_misterio import roteiro as R


class TestStaticMeumisterioB5(unittest.TestCase):
    def _ctx(self, **kw):
        defaults = dict(
            lead_id=1,
            telefone="5599999999999",
            node_atual="static_meumisterio_b5",
            texto_recebido="",
            tipo_mensagem="text",
            historico=[],
            metadata={
                "__config__": {
                    "public_url": "https://example.com",
                    "link_pagamento_b5": "https://pay.cakto.com.br/teste",
                    "audio_bloco5_url": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco5.ogg",
                }
            },
        )
        defaults.update(kw)
        return ContextoConversa(**defaults)

    def test_primeira_execucao_tem_audio_textos_e_link(self):
        ctx = self._ctx(texto_recebido="ok")
        acoes, prox = b5.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b5")
        self.assertTrue(ctx.metadata.get(R.META_B5_SEQ))
        tipos = [a.tipo for a in acoes]
        self.assertIn("audio", tipos)
        self.assertGreaterEqual(tipos.count("text"), 3)
        textos = [a for a in acoes if a.tipo == "text"]
        kinds = {(a.metadata or {}).get("kind") for a in textos}
        self.assertIn("intro_link_fornecedor", kinds)
        self.assertIn("link_pagamento_cakto", kinds)
        self.assertIn("detalhe_pagamento_desconto", kinds)
        self.assertIn("pergunta_garantia", kinds)

    def test_resposta_avanca_b6_com_delay(self):
        ctx = self._ctx(
            texto_recebido="sim",
            metadata={
                "__config__": {"public_url": "https://example.com"},
                R.META_B5_SEQ: True,
                R.META_B5_PHASE: "awaiting_reply",
                "static_mm_b5_entregue": True,
            },
        )
        acoes, prox = b5.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b6")
        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0].segundos, R.B5_DELAY_ANTES_B6_S)


if __name__ == "__main__":
    unittest.main()

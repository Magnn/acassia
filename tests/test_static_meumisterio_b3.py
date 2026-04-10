"""Testes do funil estático Meu Mistério — bloco 3."""
import unittest

from schema import ContextoConversa

from flows.funil_estatico_meu_misterio import node_static_meumisterio_b3 as b3
from flows.funil_estatico_meu_misterio import roteiro as R


class TestStaticMeumisterioB3(unittest.TestCase):
    def _ctx(self, **kw):
        defaults = dict(
            lead_id=1,
            telefone="5599999999999",
            node_atual="static_meumisterio_b3",
            texto_recebido="",
            tipo_mensagem="text",
            historico=[],
            metadata={
                "__config__": {
                    "public_url": "https://example.com",
                    "audio_bloco3_url": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco3_ptt.ogg",
                }
            },
        )
        defaults.update(kw)
        return ContextoConversa(**defaults)

    def test_primeira_execucao_tem_delays_audio_texto(self):
        ctx = self._ctx(texto_recebido="ok")
        acoes, prox = b3.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b3")
        self.assertTrue(ctx.metadata.get(R.META_B3_SEQ))
        self.assertEqual(ctx.metadata.get(R.META_B3_PHASE), "awaiting_reply")
        tipos = [a.tipo for a in acoes]
        self.assertIn("delay", tipos)
        self.assertIn("audio", tipos)
        self.assertIn("text", tipos)
        self.assertEqual(acoes[0].segundos, R.B3_DELAY_PRE_AUDIO_S)
        perg = next(a for a in acoes if a.tipo == "text" and (a.metadata or {}).get("kind") == "pergunta_hipnose_astral")
        self.assertIn("Hipnose Astral", perg.conteudo or "")

    def test_apos_resposta_avanca_b4_com_delay(self):
        ctx = self._ctx(
            texto_recebido="sim",
            metadata={
                "__config__": {"public_url": "https://example.com"},
                R.META_B3_SEQ: True,
                R.META_B3_PHASE: "awaiting_reply",
            },
        )
        acoes, prox = b3.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b4")
        self.assertEqual(acoes, [])


if __name__ == "__main__":
    unittest.main()

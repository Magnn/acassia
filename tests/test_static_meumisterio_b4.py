"""Testes do funil estático Meu Mistério — bloco 4."""
import unittest

from schema import ContextoConversa

from flows.funil_estatico_meu_misterio import node_static_meumisterio_b4 as b4
from flows.funil_estatico_meu_misterio import roteiro as R


class TestStaticMeumisterioB4(unittest.TestCase):
    def _ctx(self, **kw):
        defaults = dict(
            lead_id=1,
            telefone="5599999999999",
            node_atual="static_meumisterio_b4",
            texto_recebido="",
            tipo_mensagem="text",
            historico=[],
            metadata={
                "__config__": {
                    "public_url": "https://example.com",
                    "audio_bloco4_principal": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco4.ogg",
                    "audio_bloco4_d1": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco4_d1.ogg",
                    "audio_bloco4_d2": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco4_d2.ogg",
                    "audio_bloco4_d3": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco4_d3.ogg",
                }
            },
        )
        defaults.update(kw)
        return ContextoConversa(**defaults)

    def test_primeira_execucao_tem_delays_audios_texto(self):
        ctx = self._ctx(texto_recebido="ok")
        acoes, prox = b4.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b4")
        self.assertTrue(ctx.metadata.get(R.META_B4_SEQ))
        self.assertEqual(ctx.metadata.get(R.META_B4_PHASE), "awaiting_reply")
        tipos = [a.tipo for a in acoes]
        self.assertGreaterEqual(tipos.count("delay"), 5)
        self.assertEqual(tipos.count("audio"), 4)
        self.assertIn("text", tipos)
        voz = [a for a in acoes if a.tipo == "audio"]
        self.assertTrue((voz[0].metadata or {}).get("whatsapp_voice"))
        self.assertFalse((voz[1].metadata or {}).get("whatsapp_voice"))
        pergunta = next(
            a for a in acoes if a.tipo == "text" and (a.metadata or {}).get("kind") == "pergunta_continuidade_leitura"
        )
        self.assertIn("continuidade", (pergunta.conteudo or "").lower())

    def test_resposta_avanca_b5_com_delay(self):
        ctx = self._ctx(
            texto_recebido="sim",
            metadata={
                "__config__": {"public_url": "https://example.com"},
                R.META_B4_SEQ: True,
                R.META_B4_PHASE: "awaiting_reply",
            },
        )
        acoes, prox = b4.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b5")
        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0].tipo, "delay")
        self.assertEqual(acoes[0].segundos, R.B4_DELAY_ANTES_B5_S)


if __name__ == "__main__":
    unittest.main()

"""Testes do funil estático Meu Mistério — bloco 7 (pós-pagamento)."""
import unittest

from schema import ContextoConversa

from flows.funil_estatico_meu_misterio import node_static_meumisterio_b7 as b7
from flows.funil_estatico_meu_misterio import roteiro as R


class TestStaticMeumisterioB7(unittest.TestCase):
    def _ctx(self, **kw):
        defaults = dict(
            lead_id=1,
            telefone="5599999999999",
            node_atual="static_meumisterio_b7",
            texto_recebido="",
            tipo_mensagem="text",
            historico=[],
            metadata={
                "__config__": {
                    "public_url": "https://example.com",
                    "audio_bloco7_01": R.B7_AUDIO_01_DEFAULT,
                    "audio_bloco7_02": R.B7_AUDIO_02_DEFAULT,
                    "audio_bloco7_03": R.B7_AUDIO_03_DEFAULT,
                    "audio_bloco7_04": R.B7_AUDIO_04_DEFAULT,
                    "audio_bloco7_05": R.B7_AUDIO_05_DEFAULT,
                    "audio_bloco7_06": R.B7_AUDIO_06_DEFAULT,
                    "audio_bloco7_07": R.B7_AUDIO_07_DEFAULT,
                    "audio_bloco7_08": R.B7_AUDIO_08_DEFAULT,
                    "audio_bloco7_09": R.B7_AUDIO_09_DEFAULT,
                    "audio_bloco7_10": R.B7_AUDIO_10_DEFAULT,
                }
            },
        )
        defaults.update(kw)
        return ContextoConversa(**defaults)

    def test_primeira_execucao_envia_sequencia(self):
        ctx = self._ctx(texto_recebido="ok")
        acoes, prox = b7.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b7")
        self.assertTrue(ctx.metadata.get(R.META_B7_SEQ))
        tipos = [a.tipo for a in acoes]
        self.assertEqual(tipos.count("audio"), 10)
        self.assertGreaterEqual(tipos.count("text"), 3)
        textos = " ".join((a.conteudo or "") for a in acoes if a.tipo == "text").lower()
        self.assertIn("nomes", textos)
        self.assertIn("materiais", textos)
        self.assertIn("banho", textos)

    def test_segunda_execucao_nao_repete(self):
        ctx = self._ctx(
            texto_recebido="oi",
            metadata={"__config__": {"public_url": "https://example.com"}, R.META_B7_SEQ: True},
        )
        acoes, prox = b7.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b7")
        self.assertEqual(acoes, [])


if __name__ == "__main__":
    unittest.main()

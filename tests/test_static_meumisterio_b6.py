"""Testes do funil estático Meu Mistério — bloco 6 (FIM)."""
import unittest

from schema import ContextoConversa

from flows.funil_estatico_meu_misterio import node_static_meumisterio_b6 as b6
from flows.funil_estatico_meu_misterio import roteiro as R


class TestStaticMeumisterioB6(unittest.TestCase):
    def _ctx(self, **kw):
        defaults = dict(
            lead_id=1,
            telefone="5599999999999",
            node_atual="static_meumisterio_b6",
            texto_recebido="",
            tipo_mensagem="text",
            historico=[],
            metadata={
                "__config__": {
                    "public_url": "https://example.com",
                    "audio_bloco6_a": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco6_a.ogg",
                    "audio_bloco6_b": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco6_b.ogg",
                    "audio_bloco6_c": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco6_c.ogg",
                    "audio_bloco6_d": "https://example.com/assets/funil_estatico_meu_misterio/audio/bloco6_d.ogg",
                }
            },
        )
        defaults.update(kw)
        return ContextoConversa(**defaults)

    def test_primeira_execucao_envia_sequencia_completa(self):
        ctx = self._ctx(texto_recebido="ok")
        acoes, prox = b6.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b6")
        self.assertTrue(ctx.metadata.get(R.META_B6_SEQ))
        tipos = [a.tipo for a in acoes]
        self.assertEqual(tipos.count("audio"), 4)
        self.assertGreaterEqual(tipos.count("text"), 2)
        textos = [a for a in acoes if a.tipo == "text"]
        self.assertTrue(any("garantia" in (t.conteudo or "").lower() for t in textos))
        self.assertTrue(any("vaga" in (t.conteudo or "").lower() for t in textos))

    def test_segunda_execucao_nao_repete(self):
        ctx = self._ctx(
            texto_recebido="sim",
            metadata={"__config__": {"public_url": "https://example.com"}, R.META_B6_SEQ: True},
        )
        acoes, prox = b6.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b6")
        self.assertEqual(acoes, [])


if __name__ == "__main__":
    unittest.main()

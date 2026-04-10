"""Testes do funil estático Meu Mistério — bloco 1."""
import unittest

from schema import ContextoConversa

from flows.funil_estatico_meu_misterio import node_static_meumisterio_b1 as b1
from flows.funil_estatico_meu_misterio import roteiro as R


class TestStaticMeumisterioB1(unittest.TestCase):
    def _ctx(self, **kw):
        defaults = dict(
            lead_id=1,
            telefone="5599999999999",
            node_atual="static_meumisterio_b1",
            texto_recebido="",
            tipo_mensagem="text",
            historico=[],
            metadata={
                "__config__": {
                    "link_prova_social": "https://www.instagram.com/meumisterio_oficial",
                    "public_url": "https://example.com",
                    "imagem_perfil_instagram": "https://example.com/assets/instagram/perfil_meumisterio.png",
                }
            },
        )
        defaults.update(kw)
        return ContextoConversa(**defaults)

    def test_gatilho_dispara_sequencia(self):
        ctx = self._ctx(texto_recebido="Quero minha consulta")
        acoes, prox = b1.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b1")
        self.assertEqual(ctx.metadata.get("static_mm_b1_phase"), "awaiting_reply")
        tipos = [a.tipo for a in acoes]
        self.assertIn("delay", tipos)
        self.assertIn("text", tipos)
        self.assertIn("image", tipos)
        intro = next(a for a in acoes if a.tipo == "text" and (a.metadata or {}).get("kind") == "intro")
        self.assertTrue((intro.metadata or {}).get("engine_texto_unico"))
        self.assertTrue((intro.conteudo or "").strip().startswith("Olá, tudo bem!"))
        self.assertIn("  Esmeralda  ", intro.conteudo or "")

    def test_sem_gatilho_envia_nudge(self):
        ctx = self._ctx(texto_recebido="oi")
        acoes, prox = b1.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b1")
        self.assertTrue(acoes and "quero minha consulta" in (acoes[0].conteudo or "").lower())

    def test_apos_fase_avanca_b2(self):
        ctx = self._ctx(
            texto_recebido="ok",
            metadata={
                "__config__": {"public_url": "https://example.com"},
                "static_mm_b1_phase": "awaiting_reply",
            },
        )
        acoes, prox = b1.executar_v2(ctx)
        self.assertEqual(prox, "static_meumisterio_b2")
        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0].tipo, "delay")
        self.assertEqual(acoes[0].segundos, R.B1_DELAY_ANTES_B2_S)


if __name__ == "__main__":
    unittest.main()

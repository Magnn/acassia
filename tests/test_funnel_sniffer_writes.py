"""Escritas do sniffer fase 1 centralizadas em funnel_gates."""

from __future__ import annotations

import unittest


class TestSnifferFoto(unittest.TestCase):
    def test_marca_foto_no_turno_image(self):
        from flows.funnel_gates import meta_tem_foto, sniffer_aplicar_foto_recebida

        meta: dict = {}
        self.assertEqual(
            sniffer_aplicar_foto_recebida(meta, tipo_mensagem="image", historico=[]),
            "foto_atual",
        )
        self.assertTrue(meta_tem_foto(meta))

    def test_marca_foto_do_historico(self):
        from flows.funnel_gates import sniffer_aplicar_foto_recebida

        meta: dict = {}
        hist = [{"remetente": "user", "tipo": "image", "texto": ""}]
        self.assertEqual(
            sniffer_aplicar_foto_recebida(meta, tipo_mensagem="text", historico=hist),
            "foto_historico",
        )
        self.assertTrue(meta.get("foto_recebida"))


class TestSnifferContato(unittest.TestCase):
    def test_marca_contato_texto_atual(self):
        from flows.funnel_gates import meta_declarou_contato_salvo, sniffer_aplicar_contato_declarado

        meta: dict = {}
        self.assertEqual(
            sniffer_aplicar_contato_declarado(
                meta, texto_sniff="já salvei seu contato aqui", historico=[]
            ),
            "contato_atual",
        )
        self.assertTrue(meta_declarou_contato_salvo(meta))


class TestSnifferDesabafo(unittest.TestCase):
    def test_marca_desabafo_volume_e_gatilho(self):
        from flows.funnel_gates import meta_tem_desabafo, sniffer_aplicar_desabafo_recebido

        meta: dict = {}
        txt = (
            "estou há meses sofrendo com essa traição do meu marido "
            "e não sei mais o que fazer preciso de uma luz na minha vida"
        )
        self.assertEqual(sniffer_aplicar_desabafo_recebido(meta, texto_sniff=txt), "desabafo")
        self.assertTrue(meta_tem_desabafo(meta))
        self.assertIn("traição", (meta.get("desabafo_original") or "").lower())

    def test_marca_desabafo_curto_com_dor_explicita(self):
        """Evita depender de 9+ palavras quando o lead manda 1–2 linhas emotivas."""
        from flows.funnel_gates import meta_tem_desabafo, sniffer_aplicar_desabafo_recebido

        meta: dict = {}
        txt = "estou com muita dor no peito e não aguento mais"
        self.assertEqual(sniffer_aplicar_desabafo_recebido(meta, texto_sniff=txt), "desabafo")
        self.assertTrue(meta_tem_desabafo(meta))


class TestSnifferFase1Flags(unittest.TestCase):
    def test_ordem_e_multiplos_eventos(self):
        from flows.funnel_gates import sniffer_aplicar_fase1_flags

        meta: dict = {}
        txt = "já salvei seu número " + "palavra " * 12 + "com dor no peito e medo"
        evs = sniffer_aplicar_fase1_flags(
            meta,
            tipo_mensagem="image",
            texto_sniff=txt,
            historico=[],
        )
        self.assertIn("foto_atual", evs)
        self.assertIn("contato_atual", evs)
        self.assertIn("desabafo", evs)


class TestNode3CoerceCamada1(unittest.TestCase):
    def test_forca_foto_e_desabafo(self):
        from flows.funnel_gates import meta_node3_forcar_camada1_completa

        meta: dict = {}
        meta_node3_forcar_camada1_completa(
            meta, msg_fallback="só isso", falta_foto=True, falta_desabafo=True
        )
        self.assertTrue(meta.get("foto_recebida"))
        self.assertTrue(meta.get("desabafo_recebido"))
        self.assertTrue((meta.get("desabafo_original") or "").strip())


class TestGuardrailContato(unittest.TestCase):
    def test_sanear_reverte_flip_sem_evento_sniffer(self):
        from flows.funnel_gates import sanear_lead_contato_sem_evento_sniffer

        meta: dict = {"lead_contato_salvo_declarado": True}
        self.assertTrue(
            sanear_lead_contato_sem_evento_sniffer(
                meta, tinha_antes=False, eventos_sniffer=["foto_atual"]
            )
        )
        self.assertFalse(meta.get("lead_contato_salvo_declarado"))

    def test_sanear_nao_mexe_se_sniffer_mandou_contato(self):
        from flows.funnel_gates import sanear_lead_contato_sem_evento_sniffer

        meta: dict = {"lead_contato_salvo_declarado": True}
        self.assertFalse(
            sanear_lead_contato_sem_evento_sniffer(
                meta, tinha_antes=False, eventos_sniffer=["contato_atual"]
            )
        )
        self.assertTrue(meta.get("lead_contato_salvo_declarado"))

    def test_sanear_nao_mexe_se_ja_tinha_antes(self):
        from flows.funnel_gates import sanear_lead_contato_sem_evento_sniffer

        meta: dict = {"lead_contato_salvo_declarado": True}
        self.assertFalse(
            sanear_lead_contato_sem_evento_sniffer(meta, tinha_antes=True, eventos_sniffer=[])
        )


if __name__ == "__main__":
    unittest.main()

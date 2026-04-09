"""Pré-flight fase 1: checklist, burst longo, avanço de nó."""

from __future__ import annotations

import unittest
from types import SimpleNamespace


class TestChecklist(unittest.TestCase):
    def test_sem_nome_fica_no_node1(self):
        from flows.fase_1_preflight import primeiro_node_pendente_fase1

        lead = SimpleNamespace(nome="")
        meta: dict = {}
        self.assertEqual(primeiro_node_pendente_fase1(meta, lead), "1_apresentacao")

    def test_com_nome_sem_contato_vai_node2(self):
        from flows.fase_1_preflight import primeiro_node_pendente_fase1

        lead = SimpleNamespace(nome="Ana")
        meta: dict = {"nome_lead": "Ana"}
        self.assertEqual(primeiro_node_pendente_fase1(meta, lead), "2_salvar_contato")

    def test_vcard_satisfez_contato_para_node3(self):
        from flows.fase_1_preflight import primeiro_node_pendente_fase1

        lead = SimpleNamespace(nome="Ana")
        meta: dict = {
            "nome_lead": "Ana",
            "node2_vcard_despachado": True,
        }
        self.assertEqual(primeiro_node_pendente_fase1(meta, lead), "3_coleta_profunda")


class TestAvanco(unittest.TestCase):
    def test_node1_nao_pula_antes_do_contrato_enviado(self):
        from flows.fase_1_preflight import resolver_avanco_node_fase1

        lead = SimpleNamespace(id=10, node_atual="1_apresentacao", nome="Bia")
        ctx = SimpleNamespace(node_atual="1_apresentacao")
        meta: dict = {"nome_lead": "Bia", "node2_vcard_despachado": True}
        resolver_avanco_node_fase1(lead, ctx, meta)
        self.assertEqual(lead.node_atual, "1_apresentacao")
        self.assertEqual(ctx.node_atual, "1_apresentacao")

    def test_node1_pode_avancar_apos_contrato_enviado(self):
        from flows.fase_1_preflight import resolver_avanco_node_fase1

        lead = SimpleNamespace(id=11, node_atual="1_apresentacao", nome="Bia")
        ctx = SimpleNamespace(node_atual="1_apresentacao")
        meta: dict = {
            "nome_lead": "Bia",
            "node2_vcard_despachado": True,
            "node1_contrato_enviado": True,
        }
        resolver_avanco_node_fase1(lead, ctx, meta)
        self.assertEqual(lead.node_atual, "3_coleta_profunda")
        self.assertEqual(ctx.node_atual, "3_coleta_profunda")

    def test_avanca_para_primeiro_pendente(self):
        from flows.fase_1_preflight import resolver_avanco_node_fase1

        lead = SimpleNamespace(id=7, node_atual="1_apresentacao", nome="Bia")
        ctx = SimpleNamespace(node_atual="1_apresentacao")
        meta: dict = {
            "nome_lead": "Bia",
            "node2_vcard_despachado": True,
            "node1_contrato_enviado": True,
        }
        resolver_avanco_node_fase1(lead, ctx, meta)
        self.assertEqual(lead.node_atual, "3_coleta_profunda")
        self.assertEqual(ctx.node_atual, "3_coleta_profunda")
        self.assertEqual(meta.get("funnel_resolvido_para"), "3_coleta_profunda")

    def test_nao_retrocede_quando_checklist_atras_do_node_atual(self):
        """Metadata inconsistente: não puxa o lead de 4 de volta para 3 (evita loop/repetição)."""
        from flows.fase_1_preflight import resolver_avanco_node_fase1

        lead = SimpleNamespace(id=9, node_atual="4_instagram", nome="Ana")
        ctx = SimpleNamespace(node_atual="4_instagram")
        meta: dict = {
            "nome_lead": "Ana",
            "node2_vcard_despachado": True,
            "node3_estado": "inicial",
        }
        resolver_avanco_node_fase1(lead, ctx, meta)
        self.assertEqual(lead.node_atual, "4_instagram")
        self.assertIsNone(meta.get("funnel_resolvido_para"))


class TestBurstLongo(unittest.TestCase):
    def test_burst_coleta_completa_com_45_palavras(self):
        from flows.fase_1_preflight import promover_burst_fase1_meta

        lead = SimpleNamespace(id=1, nome="Lu")
        meta: dict = {
            "nome_lead": "Lu",
            "foto_recebida": True,
            "desabafo_recebido": True,
            "lead_contato_salvo_declarado": True,
        }
        palavras = ["preciso"] * 50
        palavras.append("ajuda")
        texto = " ".join(palavras)
        promover_burst_fase1_meta(meta, texto, 1, lead)
        self.assertEqual(meta.get("node3_estado"), "coleta_completa")


class TestEnriquecimentoPrecoceNode3(unittest.TestCase):
    def test_preenche_campos_precoce_quando_lead_ja_traz_contexto(self):
        from flows.fase_1_preflight import enriquecer_dados_node3_precoce

        meta: dict = {}
        texto = (
            "Quero encontrar um amor de valor, ja tentei de tudo, "
            "ha 2 anos isso me machuca e desde que ele foi embora eu nao consigo dormir."
        )
        enriquecer_dados_node3_precoce(meta, texto, lead_id=11)

        self.assertTrue((meta.get("desejo_declarado") or "").strip())
        self.assertTrue((meta.get("aprofundamento_texto") or "").strip())
        self.assertIn("2 anos", (meta.get("tempo_exato") or "").lower())
        self.assertIn("desde que", (meta.get("evento_gatilho") or "").lower())

    def test_nao_sobrescreve_campos_ja_preenchidos(self):
        from flows.fase_1_preflight import enriquecer_dados_node3_precoce

        meta: dict = {
            "desejo_declarado": "quero reconciliar",
            "aprofundamento_texto": "ja tentei conversar por meses",
            "tempo_exato": "6 meses",
            "evento_gatilho": "desde que brigamos",
        }
        texto = "quero mudar tudo, ha 1 ano, desde que ela saiu de casa"
        enriquecer_dados_node3_precoce(meta, texto, lead_id=12)

        self.assertEqual(meta.get("desejo_declarado"), "quero reconciliar")
        self.assertEqual(meta.get("aprofundamento_texto"), "ja tentei conversar por meses")
        self.assertEqual(meta.get("tempo_exato"), "6 meses")
        self.assertEqual(meta.get("evento_gatilho"), "desde que brigamos")


if __name__ == "__main__":
    unittest.main()

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
    def test_avanca_para_primeiro_pendente(self):
        from flows.fase_1_preflight import resolver_avanco_node_fase1

        lead = SimpleNamespace(id=7, node_atual="1_apresentacao", nome="Bia")
        ctx = SimpleNamespace(node_atual="1_apresentacao")
        meta: dict = {"nome_lead": "Bia", "node2_vcard_despachado": True}
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


if __name__ == "__main__":
    unittest.main()

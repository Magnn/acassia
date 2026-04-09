"""Matriz global fase 1: cenários combinatórios de atendimento.

Objetivo: garantir evolução incremental sem regressão ao cruzar estados
de nome/contato/coleta/instagram/contratos.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from flows.fase_1_preflight import primeiro_node_pendente_fase1, resolver_avanco_node_fase1


class TestFase1MatrizGlobalChecklist(unittest.TestCase):
    def test_matriz_primeiro_node_pendente(self):
        lead_sem_nome = SimpleNamespace(nome="")
        lead_com_nome = SimpleNamespace(nome="Ana")

        casos = [
            {
                "nome": "sem_nome_sempre_node1",
                "lead": lead_sem_nome,
                "meta": {},
                "esperado": "1_apresentacao",
            },
            {
                "nome": "com_nome_sem_contato_node2",
                "lead": lead_com_nome,
                "meta": {"nome_lead": "Ana", "nome_confirmado_chat": True},
                "esperado": "2_salvar_contato",
            },
            {
                "nome": "contato_ok_sem_contrato_node3",
                "lead": lead_com_nome,
                "meta": {"nome_lead": "Ana", "nome_confirmado_chat": True, "node2_vcard_despachado": True},
                "esperado": "3_coleta_profunda",
            },
            {
                "nome": "node3_contrato_sem_coleta_completa_permanece_node3",
                "lead": lead_com_nome,
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_contrato_enviado": True,
                    "node3_estado": "aguardando_dados",
                },
                "esperado": "3_coleta_profunda",
            },
            {
                "nome": "coleta_completa_sem_contrato_node4",
                "lead": lead_com_nome,
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_estado": "coleta_completa",
                    "node3_contrato_enviado": True,
                },
                "esperado": "4_instagram",
            },
            {
                "nome": "node4_contrato_sem_insta_permanece_node4",
                "lead": lead_com_nome,
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_estado": "coleta_completa",
                    "node3_contrato_enviado": True,
                    "node4_contrato_enviado": True,
                },
                "esperado": "4_instagram",
            },
            {
                "nome": "node4_com_visita_declarada_libera_node5",
                "lead": lead_com_nome,
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_estado": "coleta_completa",
                    "node3_contrato_enviado": True,
                    "node4_contrato_enviado": True,
                    "lead_declarou_visita_insta": True,
                },
                "esperado": "5_processa_leitura",
            },
            {
                "nome": "node4_com_insta_enviado_libera_node5",
                "lead": lead_com_nome,
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_estado": "coleta_completa",
                    "node3_contrato_enviado": True,
                    "node4_contrato_enviado": True,
                    "insta_enviado": True,
                },
                "esperado": "5_processa_leitura",
            },
        ]

        for caso in casos:
            with self.subTest(caso=caso["nome"]):
                got = primeiro_node_pendente_fase1(caso["meta"], caso["lead"])
                self.assertEqual(got, caso["esperado"])


class TestFase1MatrizGlobalAvanco(unittest.TestCase):
    def test_matriz_resolver_avanco(self):
        casos = [
            {
                "nome": "node1_sem_contrato_nao_avanca",
                "node_atual": "1_apresentacao",
                "meta": {"nome_lead": "Ana", "nome_confirmado_chat": True, "node2_vcard_despachado": True},
                "esperado_node": "1_apresentacao",
            },
            {
                "nome": "node1_com_contrato_avanca_para_node3",
                "node_atual": "1_apresentacao",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node1_contrato_enviado": True,
                    "node2_vcard_despachado": True,
                },
                "esperado_node": "3_coleta_profunda",
            },
            {
                "nome": "node2_sem_contrato_nao_avanca",
                "node_atual": "2_salvar_contato",
                "meta": {"nome_lead": "Ana", "nome_confirmado_chat": True, "node2_vcard_despachado": True},
                "esperado_node": "2_salvar_contato",
            },
            {
                "nome": "node2_com_contrato_avanca_para_node3",
                "node_atual": "2_salvar_contato",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node2_contrato_enviado": True,
                },
                "esperado_node": "3_coleta_profunda",
            },
            {
                "nome": "node3_sem_contrato_nao_avanca",
                "node_atual": "3_coleta_profunda",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_estado": "coleta_completa",
                    "lead_declarou_visita_insta": True,
                },
                "esperado_node": "3_coleta_profunda",
            },
            {
                "nome": "node3_com_contrato_avanca_para_node4",
                "node_atual": "3_coleta_profunda",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_contrato_enviado": True,
                    "node3_estado": "coleta_completa",
                    "lead_declarou_visita_insta": True,
                },
                "esperado_node": "4_instagram",
            },
            {
                "nome": "node4_sem_contrato_nao_avanca",
                "node_atual": "4_instagram",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_contrato_enviado": True,
                    "node3_estado": "coleta_completa",
                    "insta_enviado": True,
                },
                "esperado_node": "4_instagram",
            },
            {
                "nome": "node4_contrato_sem_insta_nao_avanca",
                "node_atual": "4_instagram",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_contrato_enviado": True,
                    "node3_estado": "coleta_completa",
                    "node4_contrato_enviado": True,
                },
                "esperado_node": "4_instagram",
            },
            {
                "nome": "node4_contrato_com_insta_avanca_para_node5",
                "node_atual": "4_instagram",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_contrato_enviado": True,
                    "node3_estado": "coleta_completa",
                    "node4_contrato_enviado": True,
                    "insta_enviado": True,
                },
                "esperado_node": "5_processa_leitura",
            },
            {
                "nome": "nao_retrocede_quando_checklist_atras",
                "node_atual": "4_instagram",
                "meta": {
                    "nome_lead": "Ana",
                    "nome_confirmado_chat": True,
                    "node2_vcard_despachado": True,
                    "node3_contrato_enviado": True,
                    "node3_estado": "inicial",
                    "node4_contrato_enviado": True,
                    "insta_enviado": True,
                },
                "esperado_node": "4_instagram",
            },
        ]

        for i, caso in enumerate(casos, start=1000):
            with self.subTest(caso=caso["nome"]):
                lead = SimpleNamespace(id=i, node_atual=caso["node_atual"], nome="Ana")
                ctx = SimpleNamespace(node_atual=caso["node_atual"])
                meta = dict(caso["meta"])
                resolver_avanco_node_fase1(lead, ctx, meta)
                self.assertEqual(lead.node_atual, caso["esperado_node"])
                self.assertEqual(ctx.node_atual, caso["esperado_node"])


if __name__ == "__main__":
    unittest.main()

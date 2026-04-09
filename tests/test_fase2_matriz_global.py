"""Matriz global fase 2: cenários combinatórios do Node 5.

Foco:
- Gatekeeper para mensagem superficial.
- Skip de ruído logo após Instagram.
- Reparo de entrega quando lead reporta corte.
- Handoff para Node 6 quando perfil está suficiente.
"""

from __future__ import annotations

import unittest

from config_cliente import CONFIG_CLIENTE
from flows.fase_2_leitura import node_5_processa_leitura as n5
from schema import ContextoConversa


def _ctx(texto: str, *, meta_extra: dict | None = None) -> ContextoConversa:
    meta = {"__config__": CONFIG_CLIENTE, "nome_lead": "Magno"}
    if meta_extra:
        meta.update(meta_extra)
    return ContextoConversa(
        lead_id=990001,
        telefone="+5592999999999",
        node_atual="5_processa_leitura",
        texto_recebido=texto,
        nome_lead="Magno",
        metadata=meta,
        personalizer=None,
    )


def _textos(acoes) -> list[str]:
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


class TestFase2MatrizGlobalNode5(unittest.TestCase):
    def test_matriz_node5_fluxos(self):
        casos = [
            {
                "nome": "superficial_sem_skip_fica_no_node5_gatekeeper",
                "ctx": _ctx("ok"),
                "prox": "5_processa_leitura",
                "estado": "node5_gatekeeper_fallback",
                "trecho": "o que mais aperta o peito",
            },
            {
                "nome": "superficial_pos_insta_nao_gatekeeper_e_pede_tentativas",
                "ctx": _ctx("ok", meta_extra={"node5_ignorar_ruido_um_turno": True}),
                "prox": "5_processa_leitura",
                "estado": "node5_coleta_tentativas",
                "trecho": "o que você já tentou",
            },
            {
                "nome": "reporta_corte_ativa_reparo_entrega",
                "ctx": _ctx("mensagem cortada, não deu pra ver"),
                "prox": "5_processa_leitura",
                "estado": "node5_reparo_entrega",
                "trecho": "vou seguir em blocos mais curtos",
            },
            {
                "nome": "com_contexto_substancial_handoff_node6",
                "ctx": _ctx(
                    "há 2 anos eu sofro com isso",
                    meta_extra={
                        "desabafo_original": "tenho medo de perder de vez",
                        "aprofundamento_texto": "já tentei conversar e me afastar",
                    },
                ),
                "prox": "6_atencao_dinamica",
                "estado": "node5_perfil_completo",
                "trecho": None,
            },
        ]

        for caso in casos:
            with self.subTest(caso=caso["nome"]):
                acoes, prox = n5.executar_v2(caso["ctx"])
                self.assertEqual(prox, caso["prox"])
                self.assertEqual(caso["ctx"].estado_coleta, caso["estado"])
                if caso["trecho"]:
                    textos = " ".join(t.lower() for t in _textos(acoes))
                    self.assertIn(caso["trecho"], textos)


if __name__ == "__main__":
    unittest.main()

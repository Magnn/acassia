"""Regressões do Node 3: lei por camadas e integração com Node 2."""

from __future__ import annotations

import unittest

from config_cliente import CONFIG_CLIENTE
from flows.fase_1_saudacao import node_3_coleta_profunda
from schema import ContextoConversa


def _ctx(texto: str, *, estado: str = "inicial", meta_extra: dict | None = None) -> ContextoConversa:
    meta = {
        "__config__": CONFIG_CLIENTE,
        "nome_lead": "Magno",
        "node3_estado": estado,
    }
    if meta_extra:
        meta.update(meta_extra)
    return ContextoConversa(
        lead_id=888001,
        telefone="+5592999999999",
        node_atual="3_coleta_profunda",
        texto_recebido=texto,
        nome_lead="Magno",
        metadata=meta,
        personalizer=None,
    )


def _textos(acoes) -> list[str]:
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


class TestNode3Regressoes(unittest.TestCase):
    def test_inicial_com_foto_e_dor_nao_pede_foto_novamente(self):
        ctx = _ctx(
            "quero paz no amor",
            meta_extra={"foto_recebida": True, "desabafo_recebido": True, "desabafo_original": "estou sofrendo muito"},
        )
        acoes, prox = node_3_coleta_profunda.executar_v2(ctx)
        joined = " ".join(t.lower() for t in _textos(acoes))
        self.assertEqual(prox, "3_coleta_profunda")
        self.assertNotIn("manda uma foto", joined)
        self.assertIn("?", joined)

    def test_inicial_so_com_foto_pede_desabafo(self):
        ctx = _ctx("enviei")
        ctx.metadata["foto_recebida"] = True
        acoes, _prox = node_3_coleta_profunda.executar_v2(ctx)
        joined = " ".join(t.lower() for t in _textos(acoes))
        self.assertIn("o que mais aperta", joined)

    def test_inicial_so_com_desabafo_pede_foto(self):
        ctx = _ctx("estou sofrendo muito com isso")
        ctx.metadata["desabafo_recebido"] = True
        acoes, _prox = node_3_coleta_profunda.executar_v2(ctx)
        joined = " ".join(t.lower() for t in _textos(acoes))
        self.assertIn("foto da sua mão", joined)

    def test_abertura_node3_nao_afirma_salvou_quando_so_vcard_despachado(self):
        ctx = _ctx(
            "estou sofrendo muito",
            meta_extra={"foto_recebida": True, "desabafo_recebido": True, "node2_vcard_despachado": True},
        )
        acoes, _prox = node_3_coleta_profunda.executar_v2(ctx)
        textos = _textos(acoes)
        self.assertTrue(textos)
        self.assertIn("deixei meu cartão", textos[0].lower())
        self.assertNotIn("salvou meu contato", textos[0].lower())


if __name__ == "__main__":
    unittest.main()

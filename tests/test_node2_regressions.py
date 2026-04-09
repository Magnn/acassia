"""Regressões do Node 2 (novo padrão sem pergunta de confirmação)."""

from __future__ import annotations

import unittest

from config_cliente import CONFIG_CLIENTE
from flows.fase_1_saudacao import node_2_salvar_contato
from schema import ContextoConversa


def _ctx(texto: str, *, meta_extra: dict | None = None) -> ContextoConversa:
    meta = {"__config__": CONFIG_CLIENTE, "nome_lead": "Magno"}
    if meta_extra:
        meta.update(meta_extra)
    return ContextoConversa(
        lead_id=777001,
        telefone="+5592999999999",
        node_atual="2_salvar_contato",
        texto_recebido=texto,
        nome_lead="Magno",
        metadata=meta,
        personalizer=None,
    )


def _textos(acoes) -> list[str]:
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


class TestNode2Regressoes(unittest.TestCase):
    def test_quando_contato_ja_confirmado_node2_nao_dispara_texto(self):
        ctx = _ctx("ok", meta_extra={"lead_contato_salvo_declarado": True})
        acoes, prox = node_2_salvar_contato.executar_v2(ctx)
        self.assertEqual(prox, "3_coleta_profunda")
        self.assertEqual(len(_textos(acoes)), 0)

    def test_quando_contato_nao_confirmado_envia_vcard_sem_pergunta(self):
        ctx = _ctx("vamos seguir")
        acoes, prox = node_2_salvar_contato.executar_v2(ctx)
        textos = _textos(acoes)
        joined = " ".join(t.lower() for t in textos)
        self.assertEqual(prox, "3_coleta_profunda")
        self.assertTrue(ctx.metadata.get("node2_vcard_despachado"))
        self.assertTrue(any(getattr(a, "tipo", "") == "vcard" for a in acoes))
        self.assertNotIn("?", joined)
        self.assertNotIn("conseguiu salvar", joined)


if __name__ == "__main__":
    unittest.main()

"""Regressões do Node 4 no padrão sem pergunta."""

from __future__ import annotations

import unittest

from config_cliente import CONFIG_CLIENTE
from flows.fase_1_saudacao import node_4_instagram
from schema import ContextoConversa


def _ctx(texto: str, *, meta_extra: dict | None = None) -> ContextoConversa:
    cfg = dict(CONFIG_CLIENTE)
    if not (cfg.get("link_prova_social") or "").strip():
        cfg["link_prova_social"] = "https://www.instagram.com/meumisterio_oficial/"
    meta = {"__config__": cfg, "nome_lead": "Magno"}
    if meta_extra:
        meta.update(meta_extra)
    return ContextoConversa(
        lead_id=999004,
        telefone="+5592999999999",
        node_atual="4_instagram",
        texto_recebido=texto,
        nome_lead="Magno",
        metadata=meta,
        personalizer=None,
    )


def _textos(acoes) -> list[str]:
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


class TestNode4Regressoes(unittest.TestCase):
    def test_quando_insta_ja_confirmado_nao_dispara_e_avanca(self):
        ctx = _ctx("ok", meta_extra={"lead_declarou_visita_insta": True})
        acoes, prox = node_4_instagram.executar_v2(ctx)
        self.assertEqual(prox, "5_processa_leitura")
        self.assertEqual(len(acoes), 0)

    def test_quando_insta_nao_confirmado_envia_link_sem_pergunta_e_avanca(self):
        ctx = _ctx("vamos")
        acoes, prox = node_4_instagram.executar_v2(ctx)
        textos = _textos(acoes)
        joined = " ".join(t.lower() for t in textos)
        self.assertEqual(prox, "5_processa_leitura")
        self.assertTrue(ctx.metadata.get("insta_enviado"))
        self.assertNotIn("?", joined)
        self.assertTrue(any("instagram.com" in t.lower() for t in textos))


if __name__ == "__main__":
    unittest.main()

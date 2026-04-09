"""Regressões críticas do Node 1 (abertura/checklist/roteamento)."""

from __future__ import annotations

import unittest

from config_cliente import CONFIG_CLIENTE
from flows.fase_1_saudacao import node_1_apresentacao
from schema import ContextoConversa


def _ctx(texto: str, *, nome: str = "", meta_extra: dict | None = None) -> ContextoConversa:
    meta = {"__config__": CONFIG_CLIENTE}
    if meta_extra:
        meta.update(meta_extra)
    return ContextoConversa(
        lead_id=555001,
        telefone="+5592999999999",
        node_atual="1_apresentacao",
        texto_recebido=texto,
        nome_lead=nome,
        metadata=meta,
        personalizer=None,
    )


def _textos(acoes) -> list[str]:
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


class TestNode1Regressoes(unittest.TestCase):
    def test_lei_fundamental_sem_nome(self):
        """
        Lei fundamental do Node 1 (sem nome):
        1) saudação
        2) apresentação
        3) vaga/consulta inicial gratuita
        4) pergunta de nome
        """
        ctx = _ctx("oi")
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        txt = _textos(acoes)
        joined = " ".join(t.lower() for t in txt)
        self.assertEqual(prox, "2_salvar_contato")
        self.assertGreaterEqual(len(txt), 4)
        self.assertIn("me chamo esmeralda", joined)
        self.assertTrue("última vaga" in joined or "vaga gratuita" in joined or "consulta inicial" in joined)
        self.assertTrue("como você se chama" in joined or "me diz como você se chama" in joined)

    def test_lei_fundamental_com_nome(self):
        """
        Lei fundamental do Node 1 (com nome):
        mantém saudação + apresentação + vaga/consulta e fecha em convite de início.
        """
        ctx = _ctx("oi", nome="Magno", meta_extra={"nome_confirmado_chat": True})
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        txt = _textos(acoes)
        joined = " ".join(t.lower() for t in txt)
        self.assertEqual(prox, "2_salvar_contato")
        self.assertGreaterEqual(len(txt), 4)
        self.assertIn("me chamo esmeralda", joined)
        self.assertTrue("última vaga" in joined or "vaga gratuita" in joined or "consulta inicial" in joined)
        self.assertFalse("como você se chama" in joined or "me diz como você se chama" in joined)
        self.assertTrue(
            "podemos iniciar" in joined
            or "posso seguir" in joined
            or "proximo passo" in joined
            or "próximo passo" in joined
            or "posso te guiar" in joined
            or "posso continuar" in joined
        )

    def test_duvida_nao_perde_pergunta_de_nome(self):
        ctx = _ctx("como funciona isso?")
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        txt = _textos(acoes)
        joined = " ".join(t.lower() for t in txt)
        self.assertEqual(prox, "2_salvar_contato")
        self.assertLessEqual(len(txt), 4)
        self.assertTrue("como você se chama" in joined or "me diz como você se chama" in joined)

    def test_preco_nao_perde_pergunta_de_nome(self):
        ctx = _ctx("qual o valor?")
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        txt = _textos(acoes)
        joined = " ".join(t.lower() for t in txt)
        self.assertEqual(prox, "2_salvar_contato")
        self.assertLessEqual(len(txt), 4)
        self.assertTrue("vaga gratuita" in joined or "consulta inicial" in joined)
        self.assertTrue("como você se chama" in joined or "me diz como você se chama" in joined)

    def test_dor_preserva_lei_e_contexto_no_balao_de_vaga(self):
        ctx = _ctx("estou com dor no peito e ansiedade")
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        txt = _textos(acoes)
        joined = " ".join(t.lower() for t in txt)
        self.assertEqual(prox, "2_salvar_contato")
        self.assertGreaterEqual(len(txt), 4)
        self.assertIn("me chamo esmeralda", joined)
        self.assertTrue("vaga gratuita" in joined or "consulta inicial" in joined)
        self.assertTrue("como você se chama" in joined or "me diz como você se chama" in joined)

    def test_com_nome_fechamento_tem_convite_e_sem_pedir_nome(self):
        ctx = _ctx("quero entender melhor", nome="Magno", meta_extra={"nome_confirmado_chat": True})
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        txt = _textos(acoes)
        joined = " ".join(t.lower() for t in txt)
        self.assertEqual(prox, "2_salvar_contato")
        self.assertLessEqual(len(txt), 4)
        self.assertFalse("como você se chama" in joined or "me diz como você se chama" in joined)
        self.assertTrue(
            any(
                k in joined
                for k in (
                    "podemos iniciar",
                    "posso seguir",
                    "posso continuar",
                    "próximo passo",
                    "proximo passo",
                )
            )
        )

    def test_burst_completo_pula_para_node3(self):
        ctx = _ctx(
            "me chamo ana, ja salvei seu contato e preciso da sua ajuda",
            meta_extra={
                "foto_recebida": True,
                "desabafo_recebido": True,
                "lead_contato_salvo_declarado": True,
            },
        )
        _acoes, prox = node_1_apresentacao.executar_v2(ctx)
        self.assertEqual(prox, "3_coleta_profunda")
        self.assertTrue(ctx.metadata.get("node1_pulou_para_coleta"))

    def test_saneador_remove_balao_nome_truncado(self):
        baloes = [
            "Ah, Magno, que bom que me permite iniciar.",
            "Seu nome, Mag…",
            "podemos iniciar?",
        ]
        out = node_1_apresentacao._sanear_baloes_saida_node1(baloes)  # noqa: SLF001
        joined = " ".join(t.lower() for t in out)
        self.assertIn("podemos iniciar", joined)
        self.assertNotIn("seu nome, mag", joined)

    def test_nome_de_perfil_sem_confirmacao_no_chat_nao_pode_ser_usado(self):
        ctx = _ctx("oi", nome="Magnus")
        acoes, _prox = node_1_apresentacao.executar_v2(ctx)
        joined = " ".join(t.lower() for t in _textos(acoes))
        self.assertNotIn("magnus", joined)
        self.assertTrue("como você se chama" in joined or "me diz como você se chama" in joined)

    def test_quero_minha_consulta_sem_nome_confirmado_deve_perguntar_nome(self):
        ctx = _ctx("quero minha consulta", nome="Magnus")
        acoes, prox = node_1_apresentacao.executar_v2(ctx)
        joined = " ".join(t.lower() for t in _textos(acoes))
        self.assertEqual(prox, "2_salvar_contato")
        self.assertNotIn("magnus", joined)
        self.assertTrue("como você se chama" in joined or "me diz como você se chama" in joined)


if __name__ == "__main__":
    unittest.main()

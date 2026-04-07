"""Smoke: histórico para IA não pode ser vazio quando há mensagens."""
import unittest

from schema import ContextoConversa, slice_historico_para_ia


class _Msg:
    def __init__(self, remetente: str, texto: str):
        self.remetente = remetente
        self.texto = texto


class TestSliceHistorico(unittest.TestCase):
    def test_slice_vazio(self):
        ctx = ContextoConversa(
            lead_id=1,
            telefone="5599999999999",
            node_atual="1_apresentacao",
            texto_recebido="oi",
            historico=[],
        )
        self.assertEqual(slice_historico_para_ia(ctx), [])

    def test_slice_ultimas(self):
        h = [_Msg("user", f"m{i}") for i in range(25)]
        ctx = ContextoConversa(
            lead_id=1,
            telefone="5599999999999",
            node_atual="2_salvar_contato",
            texto_recebido="x",
            historico=h,
        )
        s = slice_historico_para_ia(ctx, 20)
        self.assertEqual(len(s), 20)
        self.assertEqual(s[-1].texto, "m24")

    def test_slice_menor_que_limite(self):
        h = [_Msg("user", "a"), _Msg("bot", "b")]
        ctx = ContextoConversa(
            lead_id=1,
            telefone="5599999999999",
            node_atual="1_apresentacao",
            texto_recebido="oi",
            historico=h,
        )
        self.assertEqual(len(slice_historico_para_ia(ctx, 20)), 2)


if __name__ == "__main__":
    unittest.main()

import unittest

from flows.funnel_gates import (
    nome_eh_placeholder,
    pendencias_fase1,
    pode_burst_coleta_sem_node2,
    snapshot_fase1_coleta,
    VOCATIVO_SEM_NOME,
)


class TestNomePlaceholder(unittest.TestCase):
    def test_vazio_e_placeholder(self):
        self.assertTrue(nome_eh_placeholder(""))
        self.assertTrue(nome_eh_placeholder("   "))

    def test_meu_bem_e_placeholder(self):
        self.assertTrue(nome_eh_placeholder("meu bem"))
        self.assertTrue(nome_eh_placeholder("Meu Bem"))

    def test_nome_real_nao_e(self):
        self.assertFalse(nome_eh_placeholder("Magno"))
        self.assertFalse(nome_eh_placeholder("Ana"))


class TestBurstColeta(unittest.TestCase):
    def base_meta(self):
        return {
            "foto_recebida": True,
            "desabafo_recebido": True,
            "lead_contato_salvo_declarado": True,
        }

    def test_burst_ok(self):
        self.assertTrue(
            pode_burst_coleta_sem_node2(self.base_meta(), "Magno", "ok")
        )

    def test_burst_falta_nome(self):
        self.assertFalse(
            pode_burst_coleta_sem_node2(self.base_meta(), VOCATIVO_SEM_NOME, "ok")
        )

    def test_burst_falta_foto(self):
        m = dict(self.base_meta())
        m["foto_recebida"] = False
        self.assertFalse(pode_burst_coleta_sem_node2(m, "Magno", "ok"))

    def test_burst_falta_desabafo(self):
        m = dict(self.base_meta())
        m["desabafo_recebido"] = False
        self.assertFalse(pode_burst_coleta_sem_node2(m, "Magno", "ok"))

    def test_burst_falta_contato(self):
        m = dict(self.base_meta())
        m["lead_contato_salvo_declarado"] = False
        m["node2_vcard_despachado"] = False
        self.assertFalse(pode_burst_coleta_sem_node2(m, "Magno", "só oi"))

    def test_burst_ok_so_com_vcard_sem_flag_declarado(self):
        m = dict(self.base_meta())
        m["lead_contato_salvo_declarado"] = False
        m["node2_vcard_despachado"] = True
        self.assertTrue(pode_burst_coleta_sem_node2(m, "Magno", "ok"))


class TestSnapshot(unittest.TestCase):
    def test_pendencias_lista(self):
        p = pendencias_fase1({}, VOCATIVO_SEM_NOME, "")
        self.assertTrue(p["falta_nome"])
        self.assertTrue(p["falta_contato_salvo"])

    def test_pendencias_contato_ok_com_somente_vcard(self):
        p = pendencias_fase1({"node2_vcard_despachado": True}, "Ana", "ok")
        self.assertFalse(p["falta_contato_salvo"])

    def test_snapshot_tem_burst_false_com_tudo_falso(self):
        s = snapshot_fase1_coleta({}, "", "")
        self.assertFalse(s["burst_elegivel"])
        self.assertIn("falta_nome", s["pendencias"])


if __name__ == "__main__":
    unittest.main()

"""Disjuntor do webhook Cakto: pós-venda automático só quando configurado por tipo de funil."""
import unittest

from config_cliente import cakto_webhook_deve_iniciar_pos_venda


class TestCaktoWebhookPosVendaGate(unittest.TestCase):
    def test_padrao_estatico_sim_ia_nao(self):
        cfg = {
            "webhook_dispara_pos_venda_ia": False,
            "webhook_dispara_pos_venda_funil_estatico": True,
        }
        self.assertTrue(cakto_webhook_deve_iniciar_pos_venda("static_meumisterio_b6", cfg))
        self.assertFalse(cakto_webhook_deve_iniciar_pos_venda("8_oferta_principal", cfg))
        self.assertFalse(cakto_webhook_deve_iniciar_pos_venda("aguardando_pagamento", cfg))

    def test_liga_ia_volta_disparar(self):
        cfg = {
            "webhook_dispara_pos_venda_ia": True,
            "webhook_dispara_pos_venda_funil_estatico": True,
        }
        self.assertTrue(cakto_webhook_deve_iniciar_pos_venda("static_meumisterio_b1", cfg))
        self.assertTrue(cakto_webhook_deve_iniciar_pos_venda("14_confirmacao_entrega", cfg))

    def test_desliga_estatico_nao_dispara(self):
        cfg = {
            "webhook_dispara_pos_venda_ia": False,
            "webhook_dispara_pos_venda_funil_estatico": False,
        }
        self.assertFalse(cakto_webhook_deve_iniciar_pos_venda("static_meumisterio_b7", cfg))

    def test_sem_lead_node_trata_como_ia(self):
        cfg = {
            "webhook_dispara_pos_venda_ia": False,
            "webhook_dispara_pos_venda_funil_estatico": True,
        }
        self.assertFalse(cakto_webhook_deve_iniciar_pos_venda(None, cfg))
        self.assertFalse(cakto_webhook_deve_iniciar_pos_venda("", cfg))


if __name__ == "__main__":
    unittest.main()

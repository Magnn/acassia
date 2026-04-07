import unittest

from copy_sanitizer import sanitizar_anti_ia


class TestSpacing(unittest.TestCase):
    def test_espaco_apos_ponto(self):
        self.assertIn(". Estou", sanitizar_anti_ia("Olá.Estou aqui"))

    def test_virgula(self):
        s = sanitizar_anti_ia("sim,ok")
        self.assertIn(", ok", s)


if __name__ == "__main__":
    unittest.main()

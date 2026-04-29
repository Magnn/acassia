"""
Configuração global de testes.

Define BCRYPT_ROUNDS=4 antes de qualquer import — bcrypt em cost=12 (default
de prod) toma ~250ms por hash; com 4 fica em ms. Crítico pra suite rodar
em <5s.
"""

import os

os.environ.setdefault("BCRYPT_ROUNDS", "4")

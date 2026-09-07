"""
Extensions Flask compartilhadas — instanciadas aqui (sem app) e
inicializadas em app.py via ``init_app``. Mover pra cá evita import
circular quando blueprints precisam decorar rotas com extensions
(ex.: ``@limiter.limit(...)`` em api/saas/auth.py).
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Limiter sem app — bind acontece em app.py via limiter.init_app(app).
# Storage URI é configurado via app.config["RATELIMIT_STORAGE_URI"]
# (Redis em prod, memory:// em dev).
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # sem limite global; aplicar por rota
    # Se o storage (Redis) cair ou ficar inalcançável, não derruba a rota —
    # loga e deixa passar sem aplicar o limite (fail-open). Sem isso, um
    # Redis fora do ar (ex.: Upstash indisponível) vira 500 em toda rota
    # limitada, incluindo /saas/login.
    swallow_errors=True,
)

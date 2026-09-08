"""
Testes unitários para resiliência de reconexão ao Redis e HTTP session pooling.
"""

import time
from unittest.mock import patch, MagicMock
import pytest
from requests.adapters import HTTPAdapter

import reliability.redis_inbound as ri
import reliability.distributed_lock as dl
from engine import Engine


def test_redis_inbound_cooldown_and_recovery():
    """Verifica se redis_inbound respeita cooldown e tenta reconectar após expiração."""
    with patch.dict("os.environ", {"REDIS_URL": "redis://fake-redis-test:6379"}):
        ri._redis_client = None
        ri._last_connect_fail_ts = 0.0

        with patch("redis.from_url", side_effect=Exception("Connection refused")):
            client = ri._client()
            assert client is None
            assert ri._last_connect_fail_ts > 0

            # Segunda chamada imediata dentro do cooldown não tenta reconectar
            with patch("redis.from_url") as mock_connect:
                assert ri._client() is None
                mock_connect.assert_not_called()

        # Simula passagem do tempo de cooldown
        ri._last_connect_fail_ts = time.time() - (ri._CONNECT_RETRY_INTERVAL + 1)

        # Agora a conexão é restabelecida
        mock_redis_ok = MagicMock()
        with patch("redis.from_url", return_value=mock_redis_ok):
            client = ri._client()
            assert client is mock_redis_ok
            mock_redis_ok.ping.assert_called_once()

    # Limpeza
    ri._redis_client = None
    ri._last_connect_fail_ts = 0.0


def test_distributed_lock_cooldown_and_fallback():
    """Verifica se DistributedLock cai para local_lock e reseta ao falhar."""
    with patch.dict("os.environ", {"REDIS_URL": "redis://fake-redis-test:6379"}):
        dl._redis_client = None
        dl._last_connect_fail_ts = 0.0

        with patch("redis.from_url", side_effect=Exception("DNS failure")):
            lock = dl.DistributedLock("test_resource", ttl_ms=5000)
            acquired = lock.acquire(timeout=0.1)
            assert acquired is True
            assert lock._local_lock is not None
            lock.release()

    # Limpeza
    dl._redis_client = None
    dl._last_connect_fail_ts = 0.0


def test_engine_http_session_initialized():
    """Verifica se o Engine instancia a sessão HTTP com adapter e connection pool."""
    eng = Engine(
        whatsapp_token="fake-token",
        whatsapp_phone_id="123456",
        gemini_api_key="fake-gk",
    )
    assert hasattr(eng, "_http_session")
    assert eng._http_session is not None

    adapter_https = eng._http_session.get_adapter("https://graph.facebook.com")
    assert isinstance(adapter_https, HTTPAdapter)
    assert adapter_https._pool_connections == 20
    assert adapter_https._pool_maxsize == 50

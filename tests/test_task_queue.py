"""tests/test_task_queue.py — Testes da fila de tarefas durável."""
from unittest.mock import patch, MagicMock


def test_enqueue_broadcast_redis_fallback():
    """Quando Redis indisponível, deve usar threading.Thread como fallback."""
    with patch("api.utils.task_queue._get_redis", return_value=None):
        with patch("api.saas.broadcast._send_campaign_worker") as mock_worker:
            with patch("api.utils.task_queue.threading.Thread") as mock_thread:
                mock_thread.return_value = MagicMock()
                from api.utils.task_queue import enqueue_campaign_send
                result = enqueue_campaign_send(campaign_id=1, tenant_id="test")
                assert result is False
                mock_thread.assert_called_once()


def test_enqueue_broadcast_redis_success():
    """Quando Redis disponível, deve enfileirar via RPUSH."""
    mock_redis = MagicMock()
    mock_redis.rpush.return_value = 1
    with patch("api.utils.task_queue._get_redis", return_value=mock_redis):
        from api.utils.task_queue import enqueue_campaign_send
        result = enqueue_campaign_send(campaign_id=42, tenant_id="tenant_x")
        assert result is True
        mock_redis.rpush.assert_called_once()


def test_enqueue_sequence_redis_fallback():
    """Quando Redis indisponível para sequences, deve executar direto."""
    with patch("api.utils.task_queue._get_redis", return_value=None):
        with patch("api.saas.sequences.process_due_sequence_steps") as mock_process:
            mock_process.return_value = 0
            from api.utils.task_queue import enqueue_sequence_process
            result = enqueue_sequence_process(tenant_id="t1")
            assert result is False

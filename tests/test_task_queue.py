"""Tests for reliable Redis task queue semantics."""
import json
from unittest.mock import MagicMock, patch

from api.utils import task_queue


def test_enqueue_rejects_when_redis_is_unavailable():
    with patch.object(task_queue, "_get_redis", return_value=None):
        assert task_queue.enqueue_campaign_send(1, "tenant") is False


def test_enqueue_persists_payload_before_ready_id():
    redis = MagicMock()
    pipe = redis.pipeline.return_value
    with patch.object(task_queue, "_get_redis", return_value=redis):
        assert task_queue.enqueue_campaign_send(42, "tenant_x") is True
    stored = json.loads(pipe.hset.call_args.args[2])
    assert stored["payload"] == {"campaign_id": 42, "tenant_id": "tenant_x"}
    assert pipe.method_calls[0][0] == "hset"
    assert pipe.method_calls[1][0] == "rpush"
    pipe.execute.assert_called_once()


def test_ack_removes_lease_and_payload_atomically():
    redis = MagicMock()
    pipe = redis.pipeline.return_value
    task_queue._ack(redis, {"kind": "broadcast", "id": "job-1"})
    pipe.zrem.assert_called_once()
    pipe.hdel.assert_called_once()
    pipe.execute.assert_called_once()


def test_failure_is_scheduled_with_backoff():
    redis = MagicMock()
    pipe = redis.pipeline.return_value
    job = {"kind": "sequence", "id": "job-2", "attempts": 0, "payload": {}}
    task_queue._retry(redis, job, RuntimeError("temporary"))
    assert job["attempts"] == 1
    pipe.zadd.assert_called_once()
    pipe.rpush.assert_not_called()


def test_exhausted_job_enters_dead_letter_queue():
    redis = MagicMock()
    pipe = redis.pipeline.return_value
    job = {"kind": "broadcast", "id": "job-3", "attempts": task_queue._MAX_ATTEMPTS - 1, "payload": {}}
    task_queue._retry(redis, job, RuntimeError("permanent"))
    pipe.rpush.assert_called_once()
    pipe.hdel.assert_called_once()
    pipe.zadd.assert_not_called()


def test_embedded_workers_are_opt_in():
    with patch.dict("os.environ", {}, clear=True):
        assert task_queue.start_workers() is False


def test_lease_heartbeat_renews_processing_lease():
    import time
    redis = MagicMock()
    with task_queue._lease_heartbeat(redis, "broadcast", "job-hb", interval=0.05, lease_seconds=100):
        time.sleep(0.12)
    assert redis.zadd.call_count >= 1


def test_get_queue_metrics():
    redis = MagicMock()
    pipe = redis.pipeline.return_value
    pipe.execute.return_value = [2, 1, 0, 0, 3]
    with patch.object(task_queue, "_get_redis", return_value=redis):
        metrics = task_queue.get_queue_metrics()
        assert metrics["available"] is True
        assert "broadcast" in metrics["queues"]
        assert metrics["queues"]["broadcast"]["ready"] == 2
        assert metrics["queues"]["broadcast"]["processing"] == 1
        assert metrics["queues"]["broadcast"]["total_jobs"] == 3


def test_get_queue_metrics_redis_unavailable():
    with patch.object(task_queue, "_get_redis", return_value=None):
        metrics = task_queue.get_queue_metrics()
        assert metrics["available"] is False
        assert metrics["reason"] == "redis_unavailable"


def test_api_health_queues_endpoint():
    from flask import Flask
    import app as flask_module
    client = flask_module.app.test_client()

    with patch.object(task_queue, "get_queue_metrics", return_value={"available": True, "queues": {"broadcast": {"ready": 0}}}):
        resp = client.get("/api/health/queues")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is True
        assert "broadcast" in data["queues"]

    with patch.object(task_queue, "get_queue_metrics", return_value={"available": False, "reason": "redis_unavailable"}):
        resp = client.get("/api/health/queues")
        assert resp.status_code == 503




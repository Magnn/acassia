"""C1: FLOW_BLUEPRINT_ALLOW_HTTP exposto e helper de leitura."""

from flow_executor import flow_blueprint_allow_http


def test_flow_blueprint_allow_http_returns_bool():
    assert isinstance(flow_blueprint_allow_http(), bool)

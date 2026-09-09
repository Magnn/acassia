"""Evita seleção silenciosa de contratos duplicados pela ordem de registro."""
from collections import defaultdict

from app import app


def test_no_duplicate_route_and_method_contracts():
    grouped = defaultdict(list)
    for rule in app.url_map.iter_rules():
        methods = tuple(sorted(set(rule.methods) - {"HEAD", "OPTIONS"}))
        grouped[(rule.rule, methods)].append(rule.endpoint)
    duplicates = {key: endpoints for key, endpoints in grouped.items() if len(endpoints) > 1}
    assert duplicates == {}

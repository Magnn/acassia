"""Estado único do funil estático: merge e chaves."""
from flows.funil_estatico_meu_misterio.static_funnel_state import (
    apply_delivered,
    apply_dispatch_started,
    merge_metadata_for_persist,
    static_mm_base_from_source,
)


def test_static_mm_base_from_source():
    assert static_mm_base_from_source("static_meumisterio_b4") == "static_mm_b4"
    assert static_mm_base_from_source("x") is None


def test_apply_dispatch_started():
    m = apply_dispatch_started({}, {"static_meumisterio_b2"})
    assert m["static_mm_b2_entregue"] is False
    assert "static_mm_b2_dispatch_started_at" in m


def test_apply_delivered():
    m = {"static_mm_b2_dispatch_started_at": "2026-01-01T00:00:00+00:00"}
    out = apply_delivered(m, {"static_meumisterio_b2"})
    assert out["static_mm_b2_entregue"] is True
    assert "static_mm_b2_last_sent_at" in out
    assert "static_mm_b2_dispatch_started_at" not in out


def test_merge_metadata_for_persist_prefere_entregue_true_no_db():
    existente = {"static_mm_b3_entregue": True, "static_mm_b3_dispatch_started_at": "2026-04-10T12:00:00+00:00"}
    ctx = {"static_mm_b3_entregue": False, "nome_lead": "Ana"}
    out = merge_metadata_for_persist(existente, ctx)
    assert out["static_mm_b3_entregue"] is True
    assert out["nome_lead"] == "Ana"

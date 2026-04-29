"""Testes da façade de config por tenant."""

import time
from types import MappingProxyType
from unittest.mock import patch

import pytest

from api import tenant_config
from db import models
from db.database import Base, SessionLocal, engine as db_engine


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.TenantFlowVariable).delete()
    db.query(models.TenantFlowSecret).delete()
    db.commit()
    db.close()
    tenant_config.clear_cache()
    yield
    tenant_config.clear_cache()


def _set_var(tenant_id: str, key: str, value):
    db = SessionLocal()
    try:
        v = models.TenantFlowVariable(tenant_id=tenant_id, key=key, value_json=value)
        db.add(v)
        db.commit()
    finally:
        db.close()


def _set_secret(tenant_id: str, key: str, cipher: str):
    db = SessionLocal()
    try:
        s = models.TenantFlowSecret(tenant_id=tenant_id, key=key, value_cipher=cipher)
        db.add(s)
        db.commit()
    finally:
        db.close()


# ─── Forma do retorno ────────────────────────────────────────────────────────

def test_retorna_proxy_read_only():
    cfg = tenant_config.get_tenant_config("default")
    assert isinstance(cfg, MappingProxyType)
    with pytest.raises(TypeError):
        cfg["nova_chave"] = "x"  # type: ignore


def test_sem_overrides_devolve_estrutura_do_config_cliente():
    """Tenant sem TenantFlowVariable usa CONFIG_CLIENTE puro."""
    cfg = tenant_config.get_tenant_config("default")
    # Chaves canônicas do legado existem
    assert "perfil_negocio" in cfg
    assert "preco_servico" in cfg
    assert "checkout_urls" in cfg


# ─── Override por tenant ─────────────────────────────────────────────────────

def test_tenant_var_sobrescreve_chave_simples():
    _set_var("tenant_x", "preco_servico", "297")
    cfg = tenant_config.get_tenant_config("tenant_x")
    assert cfg["preco_servico"] == "297"


def test_tenant_var_sobrescreve_chave_aninhada_via_dotted():
    _set_var("tenant_x", "perfil_negocio.tom_voz", "direto_pratico")
    cfg = tenant_config.get_tenant_config("tenant_x")
    assert cfg["perfil_negocio"]["tom_voz"] == "direto_pratico"


def test_tenant_var_aninhada_3_niveis():
    _set_var("tenant_x", "ia_economia.max_output_tokens_por_node.1_apresentacao", 1234)
    cfg = tenant_config.get_tenant_config("tenant_x")
    assert cfg["ia_economia"]["max_output_tokens_por_node"]["1_apresentacao"] == 1234


def test_secret_aplicado_via_dotted_key():
    _set_secret("tenant_x", "cakto.client_secret", "super_secret_xyz")
    cfg = tenant_config.get_tenant_config("tenant_x")
    assert cfg["cakto"]["client_secret"] == "super_secret_xyz"


def test_outro_tenant_nao_vaza():
    _set_var("tenant_a", "preco_servico", "111")
    _set_var("tenant_b", "preco_servico", "222")

    cfg_a = tenant_config.get_tenant_config("tenant_a")
    cfg_b = tenant_config.get_tenant_config("tenant_b")
    assert cfg_a["preco_servico"] == "111"
    assert cfg_b["preco_servico"] == "222"


def test_lista_e_dict_em_value_json_funciona():
    _set_var("tenant_x", "depoimentos_urls", ["a", "b", "c"])
    cfg = tenant_config.get_tenant_config("tenant_x")
    assert cfg["depoimentos_urls"] == ["a", "b", "c"]


# ─── Cache ───────────────────────────────────────────────────────────────────

def test_cache_evita_reconsulta_db_dentro_do_ttl():
    _set_var("tenant_y", "preco_servico", "100")
    cfg1 = tenant_config.get_tenant_config("tenant_y")
    assert cfg1["preco_servico"] == "100"

    # Edita DB sem invalidar cache
    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(tenant_id="tenant_y").first()
        v.value_json = "999"
        db.commit()
    finally:
        db.close()

    cfg2 = tenant_config.get_tenant_config("tenant_y")
    assert cfg2["preco_servico"] == "100"  # ainda do cache


def test_clear_cache_individual_invalida():
    _set_var("tenant_y", "preco_servico", "100")
    tenant_config.get_tenant_config("tenant_y")

    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(tenant_id="tenant_y").first()
        v.value_json = "999"
        db.commit()
    finally:
        db.close()

    tenant_config.clear_cache("tenant_y")
    cfg = tenant_config.get_tenant_config("tenant_y")
    assert cfg["preco_servico"] == "999"


def test_clear_cache_global_invalida_todos():
    _set_var("t1", "preco_servico", "1")
    _set_var("t2", "preco_servico", "2")
    tenant_config.get_tenant_config("t1")
    tenant_config.get_tenant_config("t2")

    tenant_config.clear_cache()
    # Após clear, primeiro acesso reconsulta DB. Trocamos valores no DB:
    db = SessionLocal()
    try:
        db.query(models.TenantFlowVariable).filter_by(tenant_id="t1").update({"value_json": "10"})
        db.query(models.TenantFlowVariable).filter_by(tenant_id="t2").update({"value_json": "20"})
        db.commit()
    finally:
        db.close()

    assert tenant_config.get_tenant_config("t1")["preco_servico"] == "10"
    assert tenant_config.get_tenant_config("t2")["preco_servico"] == "20"


# ─── Robustez ────────────────────────────────────────────────────────────────

def test_tenant_id_vazio_vira_default():
    cfg_empty = tenant_config.get_tenant_config("")
    cfg_default = tenant_config.get_tenant_config("default")
    # Mesmo conteúdo (ambos consultam tenant 'default')
    assert dict(cfg_empty) == dict(cfg_default)


def test_db_indisponivel_retorna_legacy_sem_crash():
    """Se o DB cair, devolvemos CONFIG_CLIENTE puro em vez de propagar."""
    tenant_config.clear_cache()
    with patch("api.tenant_config.SessionLocal") as mock_session:
        mock_session.side_effect = RuntimeError("db down")
        cfg = tenant_config.get_tenant_config("tenant_z")
    # Não crashou; tem chaves do legado
    assert "perfil_negocio" in cfg
    assert "preco_servico" in cfg

"""Validação dos blueprints semente de pós-pagamento.

Cada seed JSON precisa passar no validador `validate_post_payment_blueprint`
sem nenhum erro (warnings tolerados). Esses testes funcionam como contrato:
qualquer ajuste num seed que quebre o validador é detectado no CI.
"""

import pytest

from flows.post_payment.seeds import AVAILABLE_SEEDS, load_seed
from flows.post_payment.validator import validate_post_payment_blueprint


# ─── Carga do JSON ───────────────────────────────────────────────────────────

def test_load_seed_express_retorna_dict():
    seed = load_seed("express")
    assert isinstance(seed, dict)
    assert seed.get("format") == "meumisterio-flow"
    assert seed.get("version") == 1


def test_load_seed_premium_retorna_dict():
    seed = load_seed("premium")
    assert isinstance(seed, dict)
    assert seed.get("format") == "meumisterio-flow"


def test_load_seed_inexistente_levanta():
    with pytest.raises(ValueError, match="template inválido"):
        load_seed("nao_existe")


def test_available_seeds_lista_express_e_premium():
    assert "express" in AVAILABLE_SEEDS
    assert "premium" in AVAILABLE_SEEDS


# ─── Validação contra o validador post_payment ───────────────────────────────

@pytest.mark.parametrize("template", ["express", "premium"])
def test_seed_passa_no_validador_post_payment(template):
    seed = load_seed(template)
    res = validate_post_payment_blueprint(seed)
    assert res["ok"] is True, (
        f"seed {template!r} falhou validação:\n"
        f"  errors: {res['errors']}\n"
        f"  pp_issues: {res['post_payment_issues']}"
    )


@pytest.mark.parametrize("template", ["express", "premium"])
def test_seed_tem_trigger_correto(template):
    seed = load_seed(template)
    nodes = seed["graph"]["nodes"]
    triggers = [n for n in nodes if n["type"] == "trigger"]
    assert len(triggers) == 1
    assert triggers[0]["config"]["event"] == "webhook.payment.approved"


@pytest.mark.parametrize("template", ["express", "premium"])
def test_seed_tem_acao_de_conversao(template):
    """Ambos os seeds precisam ter pelo menos 1 nó acao (sem warning)."""
    seed = load_seed(template)
    res = validate_post_payment_blueprint(seed)
    pp_codes = [i["code"] for i in res["post_payment_issues"]]
    assert "pp_no_conversion_tag" not in pp_codes


@pytest.mark.parametrize("template", ["express", "premium"])
def test_seed_tem_mensagem_inicial_imediata(template):
    """Ambos os seeds devem confirmar recebimento na 1ª mensagem (≤60s)."""
    seed = load_seed(template)
    res = validate_post_payment_blueprint(seed)
    pp_codes = [i["code"] for i in res["post_payment_issues"]]
    assert "pp_late_confirmation" not in pp_codes
    assert "pp_no_confirmation_message" not in pp_codes


# ─── Características específicas de cada template ────────────────────────────

def test_seed_express_usa_motor_ref_pra_envio_de_cartas():
    """Express deve invocar a função Python que sorteia + envia 3 cartas."""
    seed = load_seed("express")
    motor_refs = [
        n for n in seed["graph"]["nodes"]
        if n["type"] == "motor_ref"
        and "tarot.envio" in (n.get("config", {}).get("module_hint") or "")
    ]
    assert len(motor_refs) >= 1, "Express deveria chamar flows.tarot.envio:*"


def test_seed_premium_tem_recorrencia_de_dias():
    """Premium tem cadência longa (dias)."""
    seed = load_seed("premium")
    delays = [n for n in seed["graph"]["nodes"] if n["type"] == "delay"]
    assert any(
        n.get("config", {}).get("delay_unit") in ("dia", "dias", "d", "day", "days")
        for n in delays
    ), "Premium deveria ter pelo menos 1 delay em dias"


def test_seed_premium_menciona_link_agendamento_template():
    """Premium usa variável {{link_agendamento}} (resolução do tenant config)."""
    seed = load_seed("premium")
    bodies = [
        n.get("config", {}).get("content_text", "")
        for n in seed["graph"]["nodes"]
    ]
    assert any("{{link_agendamento}}" in b for b in bodies)


def test_seed_express_tag_correta():
    seed = load_seed("express")
    acoes = [n for n in seed["graph"]["nodes"] if n["type"] == "acao"]
    payloads = [n.get("config", {}).get("payload", "") for n in acoes]
    assert any("convertido_express" in p for p in payloads)


def test_seed_premium_tag_correta():
    seed = load_seed("premium")
    acoes = [n for n in seed["graph"]["nodes"] if n["type"] == "acao"]
    payloads = [n.get("config", {}).get("payload", "") for n in acoes]
    assert any("convertido_premium" in p for p in payloads)

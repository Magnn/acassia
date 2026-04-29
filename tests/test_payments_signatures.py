"""Testes de validação de signatures (Cakto e Stripe)."""

import hashlib
import hmac
import time

from api.payments.signatures import verify_cakto_signature, verify_stripe_signature

SECRET = "whsec_test_super_secret_123"


def _cakto_sign(payload: bytes, secret: str = SECRET, prefix: str = "") -> str:
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"{prefix}{sig}"


def _stripe_sign(payload: bytes, secret: str = SECRET, ts: int | None = None) -> tuple[str, int]:
    """Constrói header Stripe-Signature válido."""
    timestamp = ts if ts is not None else int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    header = f"t={timestamp},v1={sig}"
    return header, timestamp


# ─── Cakto ────────────────────────────────────────────────────────────────────

def test_cakto_signature_valida():
    payload = b'{"event":"purchase.approved","id":"evt_1"}'
    assert verify_cakto_signature(payload, _cakto_sign(payload), SECRET) is True


def test_cakto_signature_aceita_prefixo_sha256():
    payload = b'{"event":"x"}'
    assert verify_cakto_signature(payload, _cakto_sign(payload, prefix="sha256="), SECRET) is True


def test_cakto_signature_invalida_secret_errado():
    payload = b'{"event":"x"}'
    assert verify_cakto_signature(payload, _cakto_sign(payload), "outro_secret") is False


def test_cakto_signature_invalida_payload_alterado():
    payload = b'{"event":"x"}'
    sig = _cakto_sign(payload)
    payload_alterado = b'{"event":"y"}'
    assert verify_cakto_signature(payload_alterado, sig, SECRET) is False


def test_cakto_signature_args_vazios_retornam_false():
    assert verify_cakto_signature(b"",  "sig", SECRET) is False
    assert verify_cakto_signature(b"x", "",    SECRET) is False
    assert verify_cakto_signature(b"x", "sig", "")     is False


def test_cakto_signature_lixo_no_header_retorna_false():
    assert verify_cakto_signature(b'{"x":1}', "lixo", SECRET) is False


# ─── Stripe ───────────────────────────────────────────────────────────────────

def test_stripe_signature_valida():
    payload = b'{"id":"evt_1","type":"payment_intent.succeeded"}'
    header, _ = _stripe_sign(payload)
    assert verify_stripe_signature(payload, header, SECRET) is True


def test_stripe_signature_secret_errado():
    payload = b'{"id":"evt_1"}'
    header, _ = _stripe_sign(payload)
    assert verify_stripe_signature(payload, header, "secret_errado") is False


def test_stripe_signature_payload_alterado():
    payload = b'{"id":"evt_1"}'
    header, _ = _stripe_sign(payload)
    assert verify_stripe_signature(b'{"id":"evt_FAKE"}', header, SECRET) is False


def test_stripe_signature_replay_antigo_rejeitado():
    payload = b'{"id":"evt_1"}'
    one_hour_ago = int(time.time()) - 3600
    header, _ = _stripe_sign(payload, ts=one_hour_ago)
    assert verify_stripe_signature(payload, header, SECRET) is False


def test_stripe_signature_dentro_da_tolerancia_aceito():
    payload = b'{"id":"evt_1"}'
    quatro_min_atras = int(time.time()) - 240
    header, _ = _stripe_sign(payload, ts=quatro_min_atras)
    assert verify_stripe_signature(payload, header, SECRET) is True


def test_stripe_signature_aceita_multiplas_v1():
    """Stripe pode rotar secret; v1 múltiplos no header — qualquer válido aceita."""
    payload = b'{"id":"evt_1"}'
    header, ts = _stripe_sign(payload)
    signed_payload = f"{ts}.".encode("utf-8") + payload
    valid_sig = hmac.new(SECRET.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    header_dual = f"t={ts},v1=invalid_sig_blob_no_format,v1={valid_sig}"
    assert verify_stripe_signature(payload, header_dual, SECRET) is True


def test_stripe_signature_header_malformado_retorna_false():
    payload = b'{"id":"evt_1"}'
    assert verify_stripe_signature(payload, "garbage",    SECRET) is False
    assert verify_stripe_signature(payload, "",           SECRET) is False
    assert verify_stripe_signature(payload, "t=,v1=",     SECRET) is False
    assert verify_stripe_signature(payload, "t=abc,v1=x", SECRET) is False  # ts não-int


def test_stripe_signature_args_vazios_retornam_false():
    assert verify_stripe_signature(b"",  "h", SECRET) is False
    assert verify_stripe_signature(b"x", "",  SECRET) is False
    assert verify_stripe_signature(b"x", "h", "")     is False


def test_stripe_signature_now_injetavel_funciona():
    """Permite simular relógio do servidor pra testes determinísticos."""
    payload = b'{"id":"evt_1"}'
    fixed_ts = 1_700_000_000
    header, _ = _stripe_sign(payload, ts=fixed_ts)
    # Server clock 30s à frente — dentro da tolerância
    assert verify_stripe_signature(payload, header, SECRET, _now_unix=fixed_ts + 30) is True
    # Server clock 1 hora à frente — fora
    assert verify_stripe_signature(payload, header, SECRET, _now_unix=fixed_ts + 3600) is False

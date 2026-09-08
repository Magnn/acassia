"""Versioned tenant-secret encryption and legacy migration behavior."""

import base64
import hashlib

import pytest
from cryptography.fernet import Fernet

from api.utils.tenant_secrets import (
    decrypt_tenant_secret,
    encrypt_tenant_secret,
    is_encrypted_tenant_secret,
)


def test_round_trip_uses_versioned_authenticated_encryption(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    cipher = encrypt_tenant_secret("token-super-secreto")
    assert cipher.startswith("fernet:v1:")
    assert "token-super-secreto" not in cipher
    assert is_encrypted_tenant_secret(cipher)
    assert decrypt_tenant_secret(cipher) == "token-super-secreto"


def test_wrong_key_fails_closed(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    cipher = encrypt_tenant_secret("segredo")
    monkeypatch.setenv("CREDENTIAL_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    with pytest.raises(RuntimeError, match="chave incorreta"):
        decrypt_tenant_secret(cipher)


def test_reads_historical_xor_format(monkeypatch):
    master = "old-flow-secret-key"
    monkeypatch.delenv("CREDENTIAL_SECRET_KEY", raising=False)
    monkeypatch.setenv("MEU_MISTERIO_FLOW_SECRETS_KEY", master)
    plain = "legacy-value"
    key = hashlib.sha256(master.encode()).digest()
    raw = bytes(value ^ key[index % len(key)] for index, value in enumerate(plain.encode()))
    legacy_cipher = base64.urlsafe_b64encode(raw).decode("ascii")
    assert decrypt_tenant_secret(legacy_cipher) == plain


def test_plaintext_legacy_requires_explicit_compatibility(monkeypatch):
    monkeypatch.delenv("MEU_MISTERIO_FLOW_SECRETS_KEY", raising=False)
    assert decrypt_tenant_secret("legacy-plain", allow_plaintext_legacy=True) == "legacy-plain"
    with pytest.raises(RuntimeError, match="legado"):
        decrypt_tenant_secret("legacy-plain", allow_plaintext_legacy=False)

"""Versioned encryption for scalar tenant secrets with legacy read support."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


_PREFIX = "fernet:v1:"


def _fernet() -> Fernet:
    configured = (os.getenv("CREDENTIAL_SECRET_KEY") or "").strip()
    if configured:
        try:
            return Fernet(configured.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise RuntimeError("CREDENTIAL_SECRET_KEY inválida") from exc

    master = (
        os.getenv("MEU_MISTERIO_FLOW_SECRETS_KEY")
        or os.getenv("FLASK_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or ""
    ).strip()
    if not master:
        try:
            from flask import current_app
            master = str(current_app.config.get("SECRET_KEY") or "").strip()
        except Exception:
            pass
    if not master and (os.getenv("TESTING") or os.getenv("PYTEST_CURRENT_TEST")):
        master = "meu_misterio_test_key_dev_fallback_2026"
    if not master:
        raise RuntimeError("configure CREDENTIAL_SECRET_KEY")
    derived = base64.urlsafe_b64encode(hashlib.sha256(master.encode("utf-8")).digest())
    return Fernet(derived)


def encrypt_tenant_secret(value: str) -> str:
    if not isinstance(value, str):
        value = str(value)
    return _PREFIX + _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_tenant_secret(value_cipher: str, *, allow_plaintext_legacy: bool = True) -> str:
    value_cipher = value_cipher or ""
    if value_cipher.startswith(_PREFIX):
        try:
            return _fernet().decrypt(value_cipher[len(_PREFIX):].encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("segredo cifrado inválido ou chave incorreta") from exc

    # Formato histórico do flow platform: XOR com SHA-256 + base64, sem prefixo.
    old_master = (os.getenv("MEU_MISTERIO_FLOW_SECRETS_KEY") or "").strip()
    if old_master:
        try:
            raw = base64.urlsafe_b64decode(value_cipher.encode("ascii"))
            key = hashlib.sha256(old_master.encode("utf-8")).digest()
            plain = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw))).decode("utf-8")
            if plain and all(char.isprintable() or char.isspace() for char in plain):
                return plain
        except (ValueError, UnicodeError):
            pass

    if allow_plaintext_legacy:
        return value_cipher
    raise RuntimeError("segredo legado sem criptografia")


def is_encrypted_tenant_secret(value_cipher: str) -> bool:
    return bool(value_cipher and value_cipher.startswith(_PREFIX))

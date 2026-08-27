import os
from cryptography.fernet import Fernet
import json
import base64

def get_cipher():
    # Attempt to load a specific key for credentials, otherwise derive one from FLASK_SECRET_KEY
    # For production, you should have a strong, persistent CREDENTIAL_SECRET_KEY (32 url-safe base64 encoded bytes)
    secret = os.environ.get("CREDENTIAL_SECRET_KEY")
    if not secret:
        # Fallback to FLASK_SECRET_KEY but padded to 32 bytes and base64 encoded for Fernet
        flask_secret = os.environ.get("FLASK_SECRET_KEY", "default_secret_key_meu_misterio")
        padded = flask_secret.ljust(32, '0')[:32].encode('utf-8')
        secret = base64.urlsafe_b64encode(padded)
    return Fernet(secret)

def encrypt_credential(data: dict) -> str:
    """Encrypt a dictionary (e.g. tokens, api keys) into a cipher string."""
    cipher = get_cipher()
    json_bytes = json.dumps(data).encode('utf-8')
    return cipher.encrypt(json_bytes).decode('utf-8')

def decrypt_credential(cipher_text: str) -> dict:
    """Decrypt a cipher string back into a dictionary."""
    cipher = get_cipher()
    json_bytes = cipher.decrypt(cipher_text.encode('utf-8'))
    return json.loads(json_bytes.decode('utf-8'))

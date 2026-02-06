"""
Encryption utilities for sensitive data
"""
from cryptography.fernet import Fernet
import os
import base64
from typing import Optional


def get_or_create_encryption_key() -> bytes:
    """Get or create encryption key for sensitive data."""
    key_file = "./data/encryption.key"
    
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    
    # Generate new key
    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    with open(key_file, "wb") as f:
        f.write(key)
    
    return key


# Initialize Fernet cipher
_cipher = Fernet(get_or_create_encryption_key())


def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    if not value:
        return ""
    encrypted = _cipher.encrypt(value.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_value(encrypted_value: str) -> Optional[str]:
    """Decrypt an encrypted string value."""
    if not encrypted_value:
        return None
    try:
        decoded = base64.b64decode(encrypted_value.encode())
        decrypted = _cipher.decrypt(decoded)
        return decrypted.decode()
    except Exception:
        return None

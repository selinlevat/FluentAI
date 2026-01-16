"""
Encryption utilities for sensitive data (API keys)
"""
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config import settings


def _get_fernet():
    """Get Fernet instance with derived key"""
    # Derive a key from the encryption key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'lingualearn_salt',  # In production, use a random salt stored securely
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.ENCRYPTION_KEY.encode()))
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage"""
    if not api_key:
        return ""
    
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage"""
    if not encrypted_key:
        return ""
    
    try:
        fernet = _get_fernet()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception:
        return ""


def mask_api_key(api_key: str) -> str:
    """Mask API key for display (show only last 4 characters)"""
    if not api_key or len(api_key) < 8:
        return "****"
    return f"****{api_key[-4:]}"

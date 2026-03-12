"""
Fernet encryption utilities for provider API keys.
"""
from cryptography.fernet import Fernet


_fernet_instance = None


def _get_fernet() -> Fernet:
    """Lazy-load Fernet cipher using settings.ENCRYPTION_KEY."""
    global _fernet_instance
    if _fernet_instance is None:
        from app.config.settings import settings
        if not settings.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY is not set in settings")
        _fernet_instance = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet_instance


def encrypt_value(value: str) -> str:
    """
    Encrypt a plaintext value.

    Args:
        value: Plaintext string to encrypt

    Returns:
        Encrypted string (base64-encoded)
    """
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """
    Decrypt an encrypted value.

    Args:
        encrypted: Encrypted string (base64-encoded)

    Returns:
        Decrypted plaintext string
    """
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()

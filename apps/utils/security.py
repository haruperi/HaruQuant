"""Security utilities module."""

from typing import cast

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from apps.logger import logger

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash.

    Returns:
        The hashed password as a string.
    """
    return cast(str, pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password to verify.
        hashed_password: The hashed password to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def get_encryption_key() -> bytes:
    """
    Generate a new encryption key.

    Note: In a production environment, this key should be stored securely
    (e.g., environment variable, secrets manager) and reused.
    """
    return cast(bytes, Fernet.generate_key())


def encrypt_data(data: str, key: bytes) -> str:
    """
    Encrypt string data using Fernet symmetric encryption.

    Args:
        data: The string data to encrypt.
        key: The encryption key (bytes).

    Returns:
        The encrypted data as a string (url-safe base64 encoded).
    """
    try:
        f = Fernet(key)
        encrypted_bytes = f.encrypt(data.encode("utf-8"))
        return cast(str, encrypted_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise


def decrypt_data(token: str, key: bytes) -> str:
    """
    Decrypt an encrypted string token.

    Args:
        token: The encrypted string token.
        key: The encryption key (bytes).

    Returns:
        The decrypted string data.
    """
    try:
        f = Fernet(key)
        decrypted_bytes = f.decrypt(token.encode("utf-8"))
        return cast(str, decrypted_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise

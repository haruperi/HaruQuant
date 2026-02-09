
import pytest
from cryptography.fernet import Fernet
from apps.utils.security import (
    hash_password, verify_password, get_encryption_key, encrypt_data, decrypt_data
)

def test_password_hashing():
    password = "secret_password"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_encryption_key_generation():
    key = get_encryption_key()
    assert isinstance(key, bytes)
    assert len(key) > 0

def test_encryption_decryption():
    key = Fernet.generate_key()
    data = "sensitive_data"
    
    encrypted = encrypt_data(data, key)
    assert encrypted != data
    assert isinstance(encrypted, str)
    
    decrypted = decrypt_data(encrypted, key)
    assert decrypted == data

def test_encryption_failure():
    key = Fernet.generate_key()
    # Invalid key for decryption (different key)
    wrong_key = Fernet.generate_key()
    
    encrypted = encrypt_data("data", key)
    
    with pytest.raises(Exception):
        decrypt_data(encrypted, wrong_key)

"""
Security Utilities Usage Examples

Purpose:
- Demonstrate password hashing and verification with bcrypt
- Show encryption and decryption of sensitive data using Fernet
- Illustrate best practices for secure credential storage
- Examples for API keys, passwords, and configuration encryption

Key Concepts:
- Password hashing with bcrypt (one-way secure hashing)
- Symmetric encryption with Fernet (two-way encryption/decryption)
- Secure key generation and management
- Practical trading platform security scenarios

Usage:
    python tests/usage/utils/usage_security.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.security import (
    hash_password,
    verify_password,
    get_encryption_key,
    encrypt_data,
    decrypt_data,
)
from apps.logger import logger


def example_01_basic_password_hashing():
    """Example 1: Basic password hashing and verification."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Basic Password Hashing")
    logger.info("=" * 70)

    # Hash a password
    password = "MySecurePassword123!"
    hashed = hash_password(password)

    logger.info(f"Original password: {password}")
    logger.info(f"Hashed password: {hashed[:50]}...")
    logger.info(f"Hash length: {len(hashed)} characters")

    # Verify correct password
    is_valid = verify_password(password, hashed)
    logger.info(f"\nCorrect password verification: {is_valid}")

    # Verify incorrect password
    is_valid_wrong = verify_password("WrongPassword", hashed)
    logger.info(f"Wrong password verification: {is_valid_wrong}")


def example_02_user_authentication():
    """Example 2: Simulated user authentication system."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: User Authentication System")
    logger.info("=" * 70)

    # Simulate user registration
    users_db = {}

    username = "trader123"
    password = "SecurePass2024!"

    # Store hashed password
    users_db[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "email": "trader@example.com"
    }

    logger.info(f"User registered: {username}")
    logger.info(f"Stored hash: {users_db[username]['password_hash'][:50]}...")

    # Simulate login attempt
    login_password = "SecurePass2024!"
    stored_hash = users_db[username]["password_hash"]

    if verify_password(login_password, stored_hash):
        logger.info(f"\nLogin successful for user: {username}")
    else:
        logger.info(f"\nLogin failed for user: {username}")


def example_03_password_uniqueness():
    """Example 3: Demonstrate that same password produces different hashes."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Password Hash Uniqueness")
    logger.info("=" * 70)

    password = "SamePassword123"

    # Hash the same password multiple times
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    hash3 = hash_password(password)

    logger.info(f"Password: {password}")
    logger.info(f"\nHash 1: {hash1[:50]}...")
    logger.info(f"Hash 2: {hash2[:50]}...")
    logger.info(f"Hash 3: {hash3[:50]}...")

    logger.info(f"\nHashes are different: {hash1 != hash2 != hash3}")

    # But all verify correctly
    logger.info(f"Hash 1 verifies: {verify_password(password, hash1)}")
    logger.info(f"Hash 2 verifies: {verify_password(password, hash2)}")
    logger.info(f"Hash 3 verifies: {verify_password(password, hash3)}")


def example_04_basic_encryption():
    """Example 4: Basic data encryption and decryption."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Basic Data Encryption")
    logger.info("=" * 70)

    # Generate encryption key
    key = get_encryption_key()
    logger.info(f"Generated encryption key: {key[:20]}...")

    # Encrypt sensitive data
    api_key = "sk_live_1234567890abcdefghijklmnop"
    encrypted = encrypt_data(api_key, key)

    logger.info(f"\nOriginal API key: {api_key}")
    logger.info(f"Encrypted: {encrypted[:50]}...")

    # Decrypt data
    decrypted = decrypt_data(encrypted, key)
    logger.info(f"Decrypted: {decrypted}")

    logger.info(f"\nDecryption successful: {decrypted == api_key}")


def example_05_mt5_credentials_encryption():
    """Example 5: Encrypt MT5 broker credentials."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: MT5 Credentials Encryption")
    logger.info("=" * 70)

    # Generate key (in production, store this securely!)
    encryption_key = get_encryption_key()
    logger.info(f"Encryption key generated: {encryption_key[:30]}...")

    # MT5 credentials to encrypt
    mt5_login = "12345678"
    mt5_password = "MyBrokerPassword!"
    mt5_server = "BrokerName-Server"

    # Encrypt each credential
    encrypted_login = encrypt_data(mt5_login, encryption_key)
    encrypted_password = encrypt_data(mt5_password, encryption_key)
    encrypted_server = encrypt_data(mt5_server, encryption_key)

    logger.info("\nOriginal credentials:")
    logger.info(f"  Login: {mt5_login}")
    logger.info(f"  Password: {mt5_password}")
    logger.info(f"  Server: {mt5_server}")

    logger.info("\nEncrypted credentials:")
    logger.info(f"  Login: {encrypted_login[:40]}...")
    logger.info(f"  Password: {encrypted_password[:40]}...")
    logger.info(f"  Server: {encrypted_server[:40]}...")

    # Decrypt for use
    decrypted_login = decrypt_data(encrypted_login, encryption_key)
    decrypted_password = decrypt_data(encrypted_password, encryption_key)
    decrypted_server = decrypt_data(encrypted_server, encryption_key)

    logger.info("\nDecrypted credentials:")
    logger.info(f"  Login: {decrypted_login}")
    logger.info(f"  Password: {decrypted_password}")
    logger.info(f"  Server: {decrypted_server}")


def example_06_configuration_file_encryption():
    """Example 6: Encrypt sensitive configuration data."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Configuration File Encryption")
    logger.info("=" * 70)

    import json

    # Generate key
    key = get_encryption_key()

    # Sensitive configuration
    config = {
        "database_url": "postgresql://user:password@localhost:5432/trading_db",
        "redis_password": "redis_secret_123",
        "jwt_secret": "super_secret_jwt_key_456",
        "api_keys": {
            "alpha_vantage": "ABCDEF123456",
            "polygon": "XYZ789ABC"
        }
    }

    logger.info("Original configuration:")
    logger.info(json.dumps(config, indent=2))

    # Convert to JSON string and encrypt
    config_json = json.dumps(config)
    encrypted_config = encrypt_data(config_json, key)

    logger.info(f"\nEncrypted configuration: {encrypted_config[:60]}...")
    logger.info(f"Encrypted size: {len(encrypted_config)} bytes")

    # Decrypt and parse
    decrypted_config_json = decrypt_data(encrypted_config, key)
    decrypted_config = json.loads(decrypted_config_json)

    logger.info("\nDecrypted configuration:")
    logger.info(json.dumps(decrypted_config, indent=2))


def example_07_api_key_management():
    """Example 7: Secure API key storage and retrieval."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: API Key Management")
    logger.info("=" * 70)

    # Simulate API key storage system
    key_vault = {}
    encryption_key = get_encryption_key()

    # Store multiple API keys
    api_keys = {
        "binance_api": "binance_abc123xyz",
        "coinbase_api": "coinbase_def456uvw",
        "kraken_api": "kraken_ghi789rst"
    }

    logger.info("Storing API keys securely...")
    for service, api_key in api_keys.items():
        encrypted = encrypt_data(api_key, encryption_key)
        key_vault[service] = encrypted
        logger.info(f"  {service}: {encrypted[:40]}...")

    # Retrieve and use an API key
    logger.info("\nRetrieving API key for Binance...")
    encrypted_binance_key = key_vault["binance_api"]
    decrypted_binance_key = decrypt_data(encrypted_binance_key, encryption_key)
    logger.info(f"Decrypted Binance API key: {decrypted_binance_key}")


def example_08_wrong_key_handling():
    """Example 8: Demonstrate encryption key mismatch handling."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Wrong Encryption Key Handling")
    logger.info("=" * 70)

    # Encrypt with one key
    key1 = get_encryption_key()
    data = "Sensitive Trading Data"
    encrypted = encrypt_data(data, key1)

    logger.info(f"Original data: {data}")
    logger.info(f"Encrypted with key1: {encrypted[:40]}...")

    # Try to decrypt with wrong key
    key2 = get_encryption_key()  # Different key

    logger.info("\nAttempting to decrypt with wrong key...")
    try:
        decrypted = decrypt_data(encrypted, key2)
        logger.info(f"Decrypted: {decrypted}")
    except Exception as e:
        logger.error(f"Decryption failed (expected): {type(e).__name__}")
        logger.error(f"Error message: {str(e)[:50]}")

    # Decrypt with correct key
    logger.info("\nDecrypting with correct key...")
    decrypted_correct = decrypt_data(encrypted, key1)
    logger.info(f"Decrypted successfully: {decrypted_correct}")


def example_09_trading_strategy_parameters():
    """Example 9: Encrypt proprietary trading strategy parameters."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Trading Strategy Parameters Encryption")
    logger.info("=" * 70)

    import json

    key = get_encryption_key()

    # Proprietary strategy parameters
    strategy_params = {
        "name": "ProprietaryMomentumStrategy",
        "entry_threshold": 0.0025,
        "exit_threshold": 0.0015,
        "stop_loss_multiplier": 1.5,
        "take_profit_multiplier": 2.5,
        "position_size": 0.02,
        "max_positions": 3,
        "secret_sauce": "custom_indicator_formula_xyz"
    }

    logger.info("Original strategy parameters:")
    logger.info(json.dumps(strategy_params, indent=2))

    # Encrypt
    params_json = json.dumps(strategy_params)
    encrypted_params = encrypt_data(params_json, key)

    logger.info(f"\nEncrypted parameters: {encrypted_params[:60]}...")

    # Store encryption key securely (not shown here)
    logger.info("\n[In production: Store encryption key in environment variable or key management system]")

    # Decrypt when needed
    decrypted_json = decrypt_data(encrypted_params, key)
    decrypted_params = json.loads(decrypted_json)

    logger.info("\nDecrypted parameters:")
    logger.info(json.dumps(decrypted_params, indent=2))


def example_10_security_best_practices():
    """Example 10: Security best practices summary."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Security Best Practices")
    logger.info("=" * 70)

    best_practices = """
SECURITY BEST PRACTICES FOR TRADING PLATFORMS:

1. PASSWORD HASHING:
   - Always use hash_password() for storing user passwords
   - Never store plain text passwords
   - Use verify_password() for authentication
   - Bcrypt automatically salts passwords (different hash each time)

2. ENCRYPTION KEYS:
   - Store encryption keys in environment variables
   - Never commit keys to version control
   - Use different keys for development/production
   - Rotate keys periodically

3. SENSITIVE DATA:
   - Encrypt: API keys, broker credentials, proprietary algorithms
   - Don't encrypt: Public data, non-sensitive configuration
   - Use encryption for data at rest and in transit

4. MT5 CREDENTIALS:
   - Encrypt login, password, and server information
   - Store encrypted credentials in database
   - Decrypt only when needed for connection

5. API KEYS:
   - Encrypt all third-party API keys
   - Use environment variables or secure vaults
   - Implement key rotation policies

6. ERROR HANDLING:
   - Don't expose decryption errors to users
   - Log security events for auditing
   - Implement rate limiting on authentication

7. KEY MANAGEMENT:
   - Use get_encryption_key() to generate new keys
   - Store keys securely (AWS KMS, Azure Key Vault, etc.)
   - Implement key backup and recovery procedures
    """

    logger.info(best_practices)

    # Demonstrate key storage recommendation
    logger.info("\nExample: Storing encryption key in environment")
    key = get_encryption_key()
    logger.info(f"export ENCRYPTION_KEY='{key.decode()}'")
    logger.info("# Add to .env file (don't commit to git)")


def main():
    """Run all security utility examples."""
    logger.info("\n" + "=" * 80)
    logger.info("SECURITY UTILITIES - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_basic_password_hashing()
    example_02_user_authentication()
    example_03_password_uniqueness()
    example_04_basic_encryption()
    example_05_mt5_credentials_encryption()
    example_06_configuration_file_encryption()
    example_07_api_key_management()
    example_08_wrong_key_handling()
    example_09_trading_strategy_parameters()
    example_10_security_best_practices()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

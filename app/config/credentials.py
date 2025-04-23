"""
Secure credential handling
"""

import os
import logging
from typing import Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
import base64

from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

class Credentials:
    """Secure credential manager."""
    
    def __init__(self):
        """Initialize the credential manager."""
        self._key_file = Path("credentials.key")
        self._credentials_file = Path("credentials.enc")
        self._fernet = None
        self._credentials: Dict[str, Any] = {}
        
    def initialize(self) -> None:
        """Initialize the credential manager."""
        try:
            # Generate or load encryption key
            if not self._key_file.exists():
                key = Fernet.generate_key()
                with open(self._key_file, "wb") as f:
                    f.write(key)
            else:
                with open(self._key_file, "rb") as f:
                    key = f.read()
                    
            self._fernet = Fernet(key)
            
            # Load encrypted credentials if they exist
            if self._credentials_file.exists():
                with open(self._credentials_file, "rb") as f:
                    encrypted_data = f.read()
                    decrypted_data = self._fernet.decrypt(encrypted_data)
                    self._credentials = eval(decrypted_data.decode())
                    
            logger.info("Credential manager initialized successfully")
            
        except Exception as e:
            logger.exception("Error initializing credential manager")
            raise ConfigurationError("Failed to initialize credential manager") from e
            
    def save(self) -> None:
        """Save credentials to encrypted file."""
        try:
            if not self._fernet:
                raise ConfigurationError("Credential manager not initialized")
                
            encrypted_data = self._fernet.encrypt(str(self._credentials).encode())
            with open(self._credentials_file, "wb") as f:
                f.write(encrypted_data)
                
            logger.debug("Credentials saved successfully")
            
        except Exception as e:
            logger.exception("Error saving credentials")
            raise ConfigurationError("Failed to save credentials") from e
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get a credential value.
        
        Args:
            key: The credential key
            default: Default value if not found
            
        Returns:
            The credential value
        """
        return self._credentials.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set a credential value.
        
        Args:
            key: The credential key
            value: The credential value
        """
        self._credentials[key] = value
        self.save()
        
    def delete(self, key: str) -> None:
        """Delete a credential.
        
        Args:
            key: The credential key to delete
        """
        if key in self._credentials:
            del self._credentials[key]
            self.save()
            
    def clear(self) -> None:
        """Clear all credentials."""
        self._credentials.clear()
        self.save()
        
    def get_all(self) -> Dict[str, Any]:
        """Get all credentials.
        
        Returns:
            Dictionary of all credentials
        """
        return self._credentials.copy() 
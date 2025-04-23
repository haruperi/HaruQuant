"""
MetaTrader 5 client for managing connection and authentication.
"""

import MetaTrader5 as mt5
from pathlib import Path
from typing import Optional
from configparser import ConfigParser
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MT5Client:
    """MT5 client for handling connection and data operations."""
    
    def __init__(self):
        """Initialize MT5 client with credentials from config.ini."""
        # Load configuration from config.ini
        config = ConfigParser()
        config.read('config.ini')
        
        # Get MT5 credentials from config
        self.terminal_path = config.get('MT5', 'path').replace('/', '\\')
        self.server = config.get('MT5', 'server')
        self.login = int(config.get('MT5', 'login'))
        self.password = config.get('MT5', 'password')
        self._initialized = False
        self._connected = False
        
        # Verify terminal path exists
        if not Path(self.terminal_path).exists():
            logger.error(f"MT5 terminal not found at: {self.terminal_path}")
            raise FileNotFoundError(f"MT5 terminal not found at: {self.terminal_path}")
        
        logger.info(f"MT5 client initialized with server: {self.server}, login: {self.login}")
    
    def _initialize(self) -> None:
        """Initialize MT5 terminal connection with retry logic."""
        try:
            # First, try to shutdown any existing connection
            try:
                mt5.shutdown()
            except Exception:
                pass
            
            # Initialize MT5 with retries
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    if mt5.initialize(
                        path=self.terminal_path,
                        login=self.login,
                        password=self.password,
                        server=self.server,
                        timeout=60000
                    ):
                        logger.info("MT5 initialized successfully")
                        self._initialized = True
                        self._connected = True
                        
                        # Verify connection by getting terminal info
                        if mt5.terminal_info() is None:
                            raise RuntimeError("Failed to get terminal info after initialization")
                        
                        return
                    else:
                        error = mt5.last_error()
                        logger.warning(f"MT5 initialization attempt {attempt + 1} failed: {error}")
                        
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(retry_delay)
                            continue
                        else:
                            raise RuntimeError(f"Failed to initialize MT5 after {max_retries} attempts: {error}")
                            
                except Exception as e:
                    logger.error(f"Error during MT5 initialization attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay)
                        continue
                    raise
            
            raise RuntimeError("Failed to initialize MT5 after all retry attempts")
            
        except Exception as e:
            logger.error(f"Failed to initialize MT5: {e}")
            self._initialized = False
            self._connected = False
            raise RuntimeError(f"Failed to initialize MT5: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from MT5."""
        try:
            if self._initialized:
                mt5.shutdown()
                self._initialized = False
                self._connected = False
                logger.info("MT5 disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from MT5: {str(e)}") 
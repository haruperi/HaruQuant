"""
Core trading bot implementation with lifecycle management.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

import MetaTrader5 as mt5

from app.config.settings import load_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TradingBot:
    """Core trading bot implementation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, mode: str = "live"):
        """
        Initialize the trading bot.
        
        Args:
            config: Optional configuration dictionary
            mode: Operation mode (live/backtest/optimize)
        """
        self.config = config or load_settings()
        self.mode = mode
        self.is_running = False
        self.mt5_initialized = False
        
        # Create necessary directories
        self._create_directories()
        
        logger.info(f"Trading bot initialized in {mode} mode")
        
    def _create_directories(self) -> None:
        """Create necessary directories for the bot."""
        directories = [
            "logs",
            "data/historical",
            "data/backtest_results",
            "data/optimization_results"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
    def start(self) -> None:
        """Start the trading bot."""
        try:
            logger.info("Starting trading bot...")
            
            # Initialize MT5 connection
            if not self._initialize_mt5():
                raise RuntimeError("Failed to initialize MT5 connection")
                
            self.is_running = True
            
            # Start main loop based on mode
            if self.mode == "live":
                self._run_live_trading()
            elif self.mode == "backtest":
                self._run_backtest()
            elif self.mode == "optimize":
                self._run_optimization()
            else:
                raise ValueError(f"Invalid operation mode: {self.mode}")
                
        except Exception as e:
            logger.exception("Error starting trading bot")
            self.stop()
            raise
            
    def stop(self) -> None:
        """Stop the trading bot."""
        try:
            logger.info("Stopping trading bot...")
            
            # Shutdown MT5 connection
            if self.mt5_initialized:
                mt5.shutdown()
                self.mt5_initialized = False
                
            self.is_running = False
            logger.info("Trading bot stopped successfully")
            
        except Exception as e:
            logger.exception("Error stopping trading bot")
            raise
            
    def _initialize_mt5(self) -> bool:
        """
        Initialize MT5 connection.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Check if terminal path exists
            terminal_path = self.config["mt5"]["terminal_path"]
            if not Path(terminal_path).exists():
                logger.error(f"MT5 terminal not found at: {terminal_path}")
                return False
                
            # Initialize MT5
            if not mt5.initialize(
                path=terminal_path,
                login=self.config["mt5"]["login"],
                password=self.config["mt5"]["password"],
                server=self.config["mt5"]["server"]
            ):
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
                
            self.mt5_initialized = True
            logger.info("MT5 initialized successfully")
            return True
            
        except Exception as e:
            logger.exception("Error initializing MT5")
            return False
            
    def _run_live_trading(self) -> None:
        """Run live trading mode."""
        logger.info("Starting live trading...")
        
        try:
            while self.is_running:
                # TODO: Implement live trading logic
                pass
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping...")
        except Exception as e:
            logger.exception("Error in live trading")
            raise
            
    def _run_backtest(self) -> None:
        """Run backtesting mode."""
        logger.info("Starting backtesting...")
        
        try:
            # TODO: Implement backtesting logic
            pass
            
        except Exception as e:
            logger.exception("Error in backtesting")
            raise
            
    def _run_optimization(self) -> None:
        """Run optimization mode."""
        logger.info("Starting optimization...")
        
        try:
            # TODO: Implement optimization logic
            pass
            
        except Exception as e:
            logger.exception("Error in optimization")
            raise 
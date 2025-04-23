"""
Core trading bot implementation with lifecycle management.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

import MetaTrader5 as mt5

from app.config.settings import load_settings
from app.utils.logger import get_logger
from app.mt5.client import MT5Client
from app.trading.order import OrderManager
from app.strategy.base import StrategyManager
from app.notification.telegram import TelegramNotifier
from app.database.connection import DatabaseConnection
from app.core.crash_recovery import BotState, CrashRecovery

logger = get_logger(__name__)

class TradingBot:
    """Core trading bot implementation with component-based architecture."""
    
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
        
        # Initialize components
        self.mt5_client = None
        self.strategy_manager = None
        self.order_manager = None
        self.db_connection = None
        self.notifier = None
        
        # Initialize crash recovery
        self.bot_state = BotState()
        self.crash_recovery = CrashRecovery(self.bot_state)
        
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
            
    def initialize(self) -> None:
        """Initialize all system components."""
        logger.info("Initializing trading bot components...")
        
        try:
            # Set up signal handlers for graceful shutdown
            self.crash_recovery.setup_signal_handlers()
            
            # Initialize MT5 connection
            if not self._initialize_mt5():
                raise RuntimeError("Failed to initialize MT5 connection")
                
            # Initialize database connection
            if self.config.get('database', {}).get('enabled', False):
                self.db_connection = DatabaseConnection(
                    host=self.config['database']['host'],
                    port=self.config['database']['port'],
                    username=self.config['database']['username'],
                    password=self.config['database']['password'],
                    database=self.config['database']['dbname']
                )
                
            # Initialize notifier
            if self.config.get('notification', {}).get('telegram_enabled', False):
                self.notifier = TelegramNotifier(
                    token=self.config['notification']['telegram_token'],
                    chat_id=self.config['notification']['telegram_chat_id']
                )
                
            # Initialize strategy manager
            self.strategy_manager = StrategyManager(
                mt5_client=self.mt5_client,
                config=self.config.get('strategies', {})
            )
            
            # Initialize order manager
            self.order_manager = OrderManager(
                mt5_client=self.mt5_client,
                risk_config=self.config.get('risk_management', {})
            )
            
            logger.info("Trading bot components initialized successfully")
            
        except Exception as e:
            logger.exception("Error initializing trading bot components")
            self.crash_recovery.handle_crash(e)
            self.stop()
            raise
            
    def start(self) -> None:
        """Start the trading bot."""
        try:
            logger.info("Starting trading bot...")
            
            # Check if we should restart after previous crash
            if not self.crash_recovery.should_restart():
                logger.error("Too many crashes detected, not restarting")
                if self.notifier:
                    self.notifier.send_message(
                        "Bot failed to start due to excessive crashes. "
                        "Please check logs and restart manually."
                    )
                return
                
            # Initialize components
            self.initialize()
            self.is_running = True
            
            # Update state
            self.bot_state.update_state('last_start_time', datetime.now().isoformat())
            
            # Send notification if enabled
            if self.notifier:
                self.notifier.send_message(f"Bot started in {self.mode} mode at {datetime.now()}")
            
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
            self.crash_recovery.handle_crash(e)
            self.stop()
            raise
            
    def stop(self) -> None:
        """Stop the trading bot and clean up resources."""
        try:
            logger.info("Stopping trading bot...")
            
            # Clean up resources
            if self.mt5_initialized:
                mt5.shutdown()
                self.mt5_initialized = False
                
            if self.db_connection:
                self.db_connection.close()
                
            if self.notifier:
                self.notifier.send_message(f"Bot stopped at {datetime.now()}")
                
            self.is_running = False
            
            # Clean up crash recovery
            self.crash_recovery.cleanup()
            
            logger.info("Trading bot stopped successfully")
            
        except Exception as e:
            logger.exception("Error stopping trading bot")
            self.crash_recovery.handle_crash(e)
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
            self.mt5_client = MT5Client(
                server=self.config['mt5']['server'],
                login=self.config['mt5']['login'],
                password=self.config['mt5']['password'],
                path=self.config['mt5']['terminal_path']
            )
            
            logger.info("MT5 initialized successfully")
            return True
            
        except Exception as e:
            logger.exception("Error initializing MT5")
            self.crash_recovery.handle_crash(e)
            return False
            
    def _run_live_trading(self) -> None:
        """Run live trading mode."""
        logger.info("Starting live trading...")
        
        try:
            while self.is_running:
                # Get market data
                market_data = self.mt5_client.get_current_market_data(
                    symbols=self.strategy_manager.get_symbols()
                )
                
                # Generate signals
                signals = self.strategy_manager.generate_signals(market_data)
                
                # Execute trades based on signals
                for signal in signals:
                    self.order_manager.process_signal(signal)
                    
                # Monitor open positions
                self.order_manager.manage_open_positions()
                
                # Sleep to avoid excessive CPU usage
                time.sleep(self.config.get('general', {}).get('update_interval', 1))
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping...")
        except Exception as e:
            logger.exception("Error in live trading")
            self.crash_recovery.handle_crash(e)
            if self.notifier:
                self.notifier.send_message(f"Error in trading loop: {e}")
            raise
            
    def _run_backtest(self) -> None:
        """Run backtesting mode."""
        logger.info("Starting backtesting...")
        
        try:
            # TODO: Implement backtesting logic
            pass
            
        except Exception as e:
            logger.exception("Error in backtesting")
            self.crash_recovery.handle_crash(e)
            raise
            
    def _run_optimization(self) -> None:
        """Run optimization mode."""
        logger.info("Starting optimization...")
        
        try:
            # TODO: Implement optimization logic
            pass
            
        except Exception as e:
            logger.exception("Error in optimization")
            self.crash_recovery.handle_crash(e)
            raise 
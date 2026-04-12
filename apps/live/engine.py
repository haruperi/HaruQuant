"""Multi-Strategy Live Trading Engine.

Runs multiple strategies on different symbols simultaneously with portfolio-level risk management.
Uses a single MT5 connection shared across all strategies.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.live.bar_monitor import BarMonitor
from apps.live.config import load_config_mapping
from apps.live.notification_adapter import LiveTradingNotifier
from apps.live.portfolio_manager import PortfolioManager
from apps.live.position_manager import PositionManager
from apps.live.safety_checks import SafetyChecker
from apps.live.signal_processor import SignalProcessor
from apps.live.state_manager import StateManager
from apps.live.trade_executor import TradeExecutor
from apps.live.mt5_compat import account_balance, account_currency, account_leverage
from backend.common.logger import logger
from apps.mt5 import get_mt5_api
from apps.mt5.client import MT5Client
from apps.strategy import storage
from apps.trading.trade import Trade
from backend.data.strategies.close_breakout import CloseBreakoutStrategy
from backend.data.strategies.mean_reversion import MeanReversionStrategy
from backend.data.strategies.trend_following import TrendFollowingStrategy

mt5 = get_mt5_api()


class StrategyInstance:
    """Container for a single strategy instance."""

    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: str,
        strategy: Any,
        bar_monitor: BarMonitor,
        signal_processor: SignalProcessor,
        trade_executor: TradeExecutor,
        safety_checker: SafetyChecker,
        position_manager: PositionManager,
        config: Dict,
    ):
        """Initialize strategy instance."""
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = strategy
        self.bar_monitor = bar_monitor
        self.signal_processor = signal_processor
        self.trade_executor = trade_executor
        self.safety_checker = safety_checker
        self.position_manager = position_manager
        self.config = config

        # Statistics
        self.signals_detected = 0
        self.trades_executed = 0
        self.trades_failed = 0
        self.last_signal_time: Optional[datetime] = None
        self.last_trade_time: Optional[datetime] = None

    def __repr__(self) -> str:
        """Return string representation of StrategyInstance."""
        return f"StrategyInstance(name={self.name}, symbol={self.symbol}, signals={self.signals_detected}, trades={self.trades_executed})"


class MultiStrategyEngine:
    """Multi-strategy live trading engine with portfolio management."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict] = None,
        client: Optional[MT5Client] = None,
    ):
        """Initialize multi-strategy engine.

        Args:
            config_path: Path to multi-strategy configuration JSON file
            config: Configuration dictionary (alternative to config_path)
            client: Existing MT5Client instance (optional)
        """
        logger.info("=" * 80)
        logger.info("Initializing Multi-Strategy Live Trading Engine")
        logger.info("=" * 80)

        # Load configuration
        if config:
            self.config = config
            logger.info("Configuration loaded directly")
        elif config_path:
            self.config = self._load_config(config_path)
            logger.info(f"Configuration loaded from: {config_path}")
        else:
            raise ValueError("Must provide either config or config_path")

        # Shared components (single MT5 connection)
        self.client: Optional[MT5Client] = client
        self.trade: Optional[Trade] = None
        self.account: Optional[Any] = None

        # Portfolio management
        self.portfolio_manager: Optional[PortfolioManager] = None

        # State and notifications
        self.state_manager: Optional[StateManager] = None
        self.notifier: Optional[LiveTradingNotifier] = None

        # Strategy instances
        self.strategies: List[StrategyInstance] = []

        self._running = False
        self._initialized = False

        # Status export control
        self._last_status_export = 0.0
        self._status_export_interval = 5  # Export every 5 seconds

        # Setup logging
        self._setup_logging()

    def _load_config(self, config_path: str) -> Dict:
        """Load multi-strategy configuration from TOML/JSON + env overlay."""
        try:
            config = load_config_mapping(config_path)
            return self._validate_and_normalize_config(config)

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _validate_and_normalize_config(self, config: Dict) -> Dict:
        """Validate and normalize configuration dictionary."""
        # Validate required sections
        required = [
            # "mt5",  <- MT5 section might be optional if client is injected?
            # actually we might still need it for safety checks if they read params from it?
            # but let's keep it required for now unless we change logic elsewhere
            "portfolio",
            "strategies",
            "logging",
            "state",
        ]

        # If client is injected, mt5 section might be optional in config,
        # but let's see how initialize uses it.
        # initialize() uses self.config["mt5"] to create client if self.client is None.

        for section in required:
            if section not in config:
                raise ValueError(f"Missing required section: {section}")

        # Notifications section is optional if using database (user_id provided)
        if "user_id" not in config and "notifications" not in config:
            raise ValueError(
                "Must provide either 'user_id' (for database notifications) or 'notifications' section"
            )

        if not config["strategies"]:
            raise ValueError("No strategies defined in configuration")

        return dict(config)

    def _setup_logging(self):
        """Configure file logging."""
        log_dir = Path(self.config["logging"]["dir"])
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file
        logger.add(
            log_dir / "multi_strategy.log",
            rotation="1 day",
            retention="30 days",
            level=self.config["logging"].get("level", "INFO"),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} | {message}",
        )

        # Trade-specific log
        logger.add(
            log_dir / "trades.log",
            rotation="1 day",
            retention="90 days",
            filter=lambda record: "TRADE" in record["extra"],
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        )

        logger.info("Multi-strategy logging configured")

    def _get_supported_filling_mode(self, symbol: str) -> int:
        """
        Determine the best filling mode for a symbol.

        MT5 has three filling modes:
        - RETURN: Can be partially filled, remaining is kept as pending
        - IOC: Immediate or Cancel - Fill what you can, cancel the rest
        - FOK: Fill or Kill - All or nothing

        Different symbols support different modes:
        - Forex: Usually RETURN or IOC
        - Metals (XAUUSD): Usually FOK
        - Indices/CFDs: Varies
        """
        try:
            if not self.client:
                return int(mt5.ORDER_FILLING_FOK)
            symbol_info = self.client.symbol_info(symbol)
            if not symbol_info:
                logger.warning(
                    f"Could not get symbol info for {symbol}, defaulting to FOK"
                )
                return int(mt5.ORDER_FILLING_FOK)

            # Check filling_mode flags (bitwise)
            filling_mode = getattr(symbol_info, "filling_mode", 0) or 0

            # Bit flags: 1=RETURN, 2=IOC, 4=FOK
            # For metals/indices, try FOK first
            if filling_mode & 4:  # FOK supported
                logger.info(f"{symbol} supports FOK filling mode")
                return int(mt5.ORDER_FILLING_FOK)
            elif filling_mode & 2:  # IOC supported
                logger.info(f"{symbol} supports IOC filling mode")
                return int(mt5.ORDER_FILLING_IOC)
            elif filling_mode & 1:  # RETURN supported
                logger.info(f"{symbol} supports RETURN filling mode")
                return int(mt5.ORDER_FILLING_RETURN)
            else:
                logger.warning(
                    f"No standard filling mode detected for {symbol}, defaulting to FOK"
                )
                return int(mt5.ORDER_FILLING_FOK)

        except Exception as e:
            logger.error(f"Error detecting filling mode for {symbol}: {e}")
            return int(mt5.ORDER_FILLING_FOK)

    def initialize(self) -> bool:
        """Initialize all strategies and shared components.

        Returns:
            True if initialization successful
        """
        try:
            # 1. Connect to MT5 (single shared connection)
            logger.info("Connecting to MT5...")

            if not self.client:
                mt5_config = self.config["mt5"]

                self.client = MT5Client()
                connected = self.client.connect(
                    path=mt5_config.get("path", ""),
                    login=mt5_config["login"],
                    password=mt5_config["password"],
                    server=mt5_config["server"],
                )

                if not connected:
                    logger.error("Failed to connect to MT5")
                    return False

                logger.info("MT5 connection established (shared across all strategies)")
            else:
                logger.info("Using existing MT5 connection")

            # 2. Setup shared trading objects
            logger.info("Setting up shared trading objects...")
            self.trade = Trade(api=self.client)
            # Note: Filling mode will be set per-symbol in strategy initialization

            self.account = self.client.account_info()

            logger.info(
                f"Account: {account_balance(self.account)} {account_currency(self.account)}, "
                f"Leverage: 1:{account_leverage(self.account)}"
            )

            # 3. Initialize portfolio manager
            logger.info("Initializing portfolio manager...")
            portfolio_config = self.config["portfolio"]
            self.portfolio_manager = PortfolioManager(
                self.client,
                self.account,
                max_total_positions=portfolio_config.get("max_total_positions", 20),
                max_positions_per_symbol=portfolio_config.get(
                    "max_positions_per_symbol", 3
                ),
                max_portfolio_risk_percent=portfolio_config.get(
                    "max_portfolio_risk_percent", 10.0
                ),
                max_correlated_positions=portfolio_config.get(
                    "max_correlated_positions", 5
                ),
            )

            # 4. Initialize state manager
            logger.info("Initializing state manager...")
            self.state_manager = StateManager(self.config["state"]["file"])
            logger.info(f"State: {self.state_manager.get_state_summary()}")

            # 5. Initialize notifier (email and/or Telegram)
            logger.info("Initializing notification system...")

            # Check if user_id is provided (database-based notifications)
            if "user_id" in self.config:
                user_id = self.config["user_id"]
                logger.info(
                    f"Loading notification credentials from database for user {user_id}"
                )
                self.notifier = LiveTradingNotifier.from_database(
                    user_id=user_id,
                    db_path=self.config.get("db_path", "backend/data/database/haruquant.db"),
                )
            else:
                # Fallback to config-based notifications (backward compatibility)
                logger.info("Using config-based notification settings")
                notif_config = self.config["notifications"]
                self.notifier = LiveTradingNotifier(
                    notif_config.get("enable_email", False),
                    notif_config.get("smtp_host", ""),
                    notif_config.get("smtp_port", 587),
                    notif_config.get("smtp_user", ""),
                    notif_config.get("smtp_password", ""),
                    notif_config.get("recipients", []),
                )

            # 6. Initialize each strategy
            logger.info("=" * 80)
            logger.info(f"Initializing {len(self.config['strategies'])} strategies...")
            logger.info("=" * 80)

            for strategy_config in self.config["strategies"]:
                if not self._initialize_strategy(strategy_config):
                    logger.error(
                        f"Failed to initialize strategy: {strategy_config.get('name')}"
                    )
                    return False

            logger.info("=" * 80)
            logger.info(f"Successfully initialized {len(self.strategies)} strategies")
            logger.info("=" * 80)

            # 7. Initial portfolio refresh
            self.portfolio_manager.refresh_all_positions()
            portfolio_summary = self.portfolio_manager.get_portfolio_summary()
            logger.info(
                f"Initial portfolio: {portfolio_summary['total_positions']} positions, "
                f"Profit: {portfolio_summary['profit']:.2f}"
            )

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False

    def _initialize_strategy(self, strategy_config: Dict) -> bool:
        """Initialize a single strategy instance.

        Args:
            strategy_config: Strategy configuration dictionary

        Returns:
            True if successful
        """
        try:
            name = strategy_config.get("name", "UnknownStrategy")
            symbol = strategy_config.get("symbol")
            if not symbol:
                logger.error(f"Strategy config missing 'symbol': {strategy_config}")
                return False
            timeframe = strategy_config["timeframe"]
            strategy_type = strategy_config.get("strategy_type", "TrendFollowing")
            strategy_id = strategy_config.get("strategy_id")
            strategy_version = strategy_config.get("strategy_version")
            strategy_name = strategy_config.get("strategy_name")
            username = strategy_config.get("username") or ""

            logger.info(
                f"Initializing strategy: {name} ({strategy_type} on {symbol} {timeframe})"
            )

            strategy_class = self._load_strategy_class(
                strategy_id, strategy_version, strategy_name, username
            )
            if not strategy_class:
                strategy_class = self._resolve_builtin_strategy_class(
                    strategy_type, strategy_name
                )

            if not strategy_class:
                logger.warning(f"Unknown strategy type: {strategy_type}")
                logger.warning("Unable to load strategy class; skipping instance.")
                return True

            # Create strategy
            strategy_params = strategy_config.get("params", {}).copy()
            strategy_params["symbol"] = symbol
            strategy = strategy_class(params=strategy_params)
            strategy.on_init()

            # Set magic number for this strategy
            magic_number = strategy_config.get(
                "magic_number", 100000 + len(self.strategies)
            )
            if self.trade:
                self.trade.SetExpertMagicNumber(magic_number)

            if not self.client:
                raise RuntimeError("MT5 Client not initialized")

            # Create components
            symbol_info = self.client.symbol_info(symbol)
            if symbol_info is None:
                raise RuntimeError(f"Symbol info unavailable for {symbol}")
            bar_monitor = BarMonitor(self.client, symbol, timeframe)

            # Setup signal processor with historical data
            signal_processor = self._setup_signal_processor(
                strategy, bar_monitor, strategy_config.get("initial_bars", 250)
            )
            if not signal_processor:
                return False

            # Create position manager (per-strategy tracking)
            position_manager = PositionManager(self.client, magic_number)
            position_manager.refresh_positions()

            # Create safety checker and trade executor
            safety_checker = self._create_safety_checker(symbol_info, strategy_config)
            trade_executor = self._create_trade_executor(
                symbol_info, position_manager, symbol, strategy_config
            )

            # Create strategy instance
            instance = StrategyInstance(
                name=name,
                symbol=symbol,
                timeframe=timeframe,
                strategy=strategy,
                bar_monitor=bar_monitor,
                signal_processor=signal_processor,
                trade_executor=trade_executor,
                safety_checker=safety_checker,
                position_manager=position_manager,
                config=strategy_config,
            )

            self.strategies.append(instance)
            logger.info(f"Strategy '{name}' initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing strategy: {e}", exc_info=True)
            return False

    def _load_strategy_class(
        self,
        strategy_id: Optional[int],
        strategy_version: Optional[str],
        strategy_name: Optional[str],
        username: str,
    ) -> Optional[Any]:
        if not strategy_id or not strategy_version or not strategy_name:
            return None

        try:
            return storage.load_strategy_class(
                user_id=self.config.get("user_id", 0),
                strategy_id=int(strategy_id),
                version=strategy_version,
                username=username,
                strategy_name=strategy_name,
            )
        except Exception as exc:
            logger.warning(
                f"Failed to load strategy class for {strategy_name} v{strategy_version}: {exc}"
            )
            return None

    def _resolve_builtin_strategy_class(
        self, strategy_type: str, strategy_name: Optional[str]
    ) -> Optional[Any]:
        normalized_type_key = "".join(
            ch for ch in str(strategy_type).strip().lower() if ch.isalnum()
        )
        strategy_aliases = {
            "trend": "TrendFollowing",
            "trendfollowing": "TrendFollowing",
            "closebreakout": "CloseBreakout",
            "breakout": "CloseBreakout",
            "meanreversion": "MeanReversion",
        }
        normalized_type = strategy_aliases.get(normalized_type_key, strategy_type)
        strategy_classes = {
            "TrendFollowing": TrendFollowingStrategy,
            "CloseBreakout": CloseBreakoutStrategy,
            "MeanReversion": MeanReversionStrategy,
        }

        strategy_class = strategy_classes.get(normalized_type)
        if not strategy_class and strategy_name:
            normalized_name = "".join(
                ch for ch in str(strategy_name).strip().lower() if ch.isalnum()
            )
            mapped_type = strategy_aliases.get(normalized_name)
            if mapped_type:
                strategy_class = strategy_classes.get(mapped_type)

        return strategy_class

    def _setup_signal_processor(
        self, strategy: Any, bar_monitor: BarMonitor, initial_bars: int
    ) -> Optional[SignalProcessor]:
        """Set up and initialize signal processor with historical data."""
        historical_data = bar_monitor.get_historical_data(initial_bars)

        if historical_data is None or historical_data.empty:
            logger.error(f"Failed to fetch historical data for {bar_monitor.symbol}")
            return None

        signal_processor = SignalProcessor(strategy)
        if not signal_processor.initialize(historical_data):
            logger.error(
                f"Failed to initialize signal processor for {bar_monitor.symbol}"
            )
            return None

        return signal_processor

    def _create_safety_checker(
        self, symbol_info: Any, config: Dict
    ) -> SafetyChecker:
        """Create safety checker instance."""
        if not self.client or not self.account:
            raise RuntimeError("Client or Account not initialized")

        return SafetyChecker(
            self.client,
            self.account,
            symbol_info,
            config.get("min_balance", 100.0),
            config.get("min_margin_level", 200.0),
        )

    def _create_trade_executor(
        self,
        symbol_info: Any,
        position_manager: PositionManager,
        symbol: str,
        config: Dict,
    ) -> TradeExecutor:
        """Create trade executor instance."""
        if not self.trade:
            raise RuntimeError("Trade object not initialized")

        filling_mode = self._get_supported_filling_mode(symbol)
        logger.info(f"Detected filling mode for {symbol}: {filling_mode}")

        return TradeExecutor(
            self.trade,
            symbol_info,
            position_manager,
            symbol,
            config.get("volume", 0.01),
            filling_mode=filling_mode,
        )

    def run(self):
        """Run main trading loop."""
        if not self._initialized:
            logger.error("Engine not initialized. Call initialize() first.")
            return

        self._running = True

        # Send startup notification
        # Send email notification (customize for multi-strategy)
        # self.notifier.notify_startup(strategy_list, "", 0)

        try:
            while self._running:
                try:
                    self._run_iteration()

                except KeyboardInterrupt:
                    raise

                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

        finally:
            self._shutdown()

    def _run_iteration(self):
        """Run a single iteration of the trading loop."""
        # 1. Check state (enabled/paused)
        if not self.state_manager:
            return  # Should be initialized

        if not self.state_manager.is_enabled():
            logger.debug("Trading disabled via state file")
            time.sleep(5)
            return

        if self.state_manager.is_paused():
            logger.debug("Trading paused via state file")
            time.sleep(5)
            return

        # 2. Refresh portfolio positions (shared across all strategies)
        if self.portfolio_manager:
            self.portfolio_manager.refresh_all_positions()

        # 3. Check each strategy for new bars and signals
        for instance in self.strategies:
            self._process_strategy(instance)

        # 4. Update state
        if self.state_manager:
            self.state_manager.update_last_run()

        # 5. Export status for dashboard
        self._export_status()

        # 6. Sleep 2 seconds
        time.sleep(2)

    def _process_strategy(self, instance: StrategyInstance):
        """Process a single strategy instance.

        Args:
            instance: StrategyInstance to process
        """
        try:
            # Check for new bar
            if not instance.bar_monitor.check_new_bar():
                return

            # Get last closed bar
            last_bar = instance.bar_monitor.get_last_closed_bar()

            if last_bar is None:
                return

            logger.info(f"[{instance.name}] New bar closed: {last_bar.name}")

            # Process signal
            signal = instance.signal_processor.update_with_new_bar(last_bar)
            if not signal:
                return

            # Handle detected signal
            self._handle_signal(instance, dict(signal))

        except Exception as e:
            logger.error(
                f"[{instance.name}] Error processing strategy: {e}", exc_info=True
            )

    def _handle_signal(self, instance: StrategyInstance, signal: Dict):
        """Handle a detected signal."""
        normalized_signal = self._normalize_signal(signal)

        # Log signal
        self._log_signal(instance, normalized_signal)

        # Refresh positions
        instance.position_manager.refresh_positions()

        # Validate signal
        if not self._validate_signal(instance, normalized_signal):
            return

        # Execute trade
        self._execute_trade(instance, normalized_signal)

    def _normalize_signal(self, signal: Dict) -> Dict:
        """Normalize strategy signal into engine-required schema."""
        normalized = dict(signal)

        if "signal" not in normalized:
            entry_signal = normalized.get("entry_signal")
            exit_signal = normalized.get("exit_signal")
            if entry_signal in (1, -1):
                normalized["signal"] = "buy" if entry_signal == 1 else "sell"
            elif exit_signal in (1, -1):
                normalized["signal"] = "close buy" if exit_signal == 1 else "close sell"
            else:
                normalized["signal"] = "unknown"

        if "entry_price" not in normalized and "price" in normalized:
            normalized["entry_price"] = normalized.get("price")

        return normalized

    def _log_signal(self, instance: StrategyInstance, signal: Dict):
        """Log detected signal details."""
        instance.signals_detected += 1
        instance.last_signal_time = datetime.now()

        logger.info("=" * 60)
        logger.info(f"[{instance.name}] SIGNAL: {str(signal.get('signal')).upper()}")
        logger.info("=" * 60)
        logger.info(f"Symbol: {instance.symbol}")
        logger.info(f"Time: {signal.get('time')}")
        reason = signal.get("reason")
        if reason:
            logger.info(f"Reason: {reason}")
        entry_price = signal.get("entry_price")
        if isinstance(entry_price, (int, float)):
            logger.info(f"Entry Price: {entry_price:.5f}")

    def _validate_signal(self, instance: StrategyInstance, signal: Dict) -> bool:
        """Validate if signal can be executed based on portfolio and safety rules."""
        # 1. Portfolio-level validation (only for new entry signals)
        if signal["signal"] in ["buy", "sell"]:
            if not self.portfolio_manager:
                logger.error("Portfolio manager not initialized")
                return False

            volume = signal.get("volume", instance.config.get("volume", 0.01))
            can_trade, portfolio_reason = self.portfolio_manager.can_open_position(
                symbol=instance.symbol,
                strategy_name=instance.name,
                volume=volume,
                signal_type=str(signal["signal"]),
            )

            if not can_trade:
                logger.warning(
                    f"[{instance.name}] Portfolio check failed: {portfolio_reason}"
                )
                if self.notifier:
                    self.notifier.notify_safety_violation(
                        f"[{instance.name}] {portfolio_reason}"
                    )
                return False

            logger.info(f"[{instance.name}] Portfolio check passed")

        # 2. Strategy-level safety checks
        if not self.state_manager:
            return True  # Should ideally be initialized, but don't block if absent?
            # Actually initialize() ensures it is present.

        passed, reason = instance.safety_checker.check_all(
            volume=signal.get("volume", instance.config.get("volume", 0.01)),
            position_count=instance.position_manager.total_positions(),
            daily_trades=self.state_manager.get_trade_count_today(),
            max_positions=instance.config.get("max_positions", 10),
            max_daily_trades=instance.config.get("max_daily_trades", 50),
        )

        if not passed:
            logger.warning(f"[{instance.name}] Safety check failed: {reason}")
            if self.notifier:
                self.notifier.notify_safety_violation(f"[{instance.name}] {reason}")
            return False

        logger.info(f"[{instance.name}] All safety checks passed")
        return True

    def _execute_trade(self, instance: StrategyInstance, signal: Dict):
        """Execute trade for the signal and update statistics."""
        success, message = instance.trade_executor.execute_signal(signal)

        # Update statistics
        if success:
            instance.trades_executed += 1
            instance.last_trade_time = datetime.now()
            if self.state_manager:
                self.state_manager.increment_trade_count()
                trade_count = self.state_manager.get_trade_count_today()
                logger.info(f"Total trades today: {trade_count}")
        else:
            instance.trades_failed += 1

        # Notify (add symbol and strategy name to signal for notification)
        if self.notifier:
            notification_signal = signal.copy()
            notification_signal["symbol"] = instance.symbol
            notification_signal["strategy_name"] = instance.name
            self.notifier.notify_signal(
                notification_signal,
                executed=success,
                error=message if not success else None,
            )

        logger.info("=" * 60)

    def stop(self):
        """Stop the trading engine."""
        logger.info("Stopping multi-strategy engine...")
        self._running = False

    def _shutdown(self):
        """Clean shutdown."""
        logger.info("=" * 80)
        logger.info("Shutting down Multi-Strategy Engine")
        logger.info("=" * 80)

        # Print final statistics
        logger.info("Final Statistics:")
        for instance in self.strategies:
            logger.info(
                f"  {instance.name}: "
                f"Signals={instance.signals_detected}, "
                f"Trades={instance.trades_executed}, "
                f"Failed={instance.trades_failed}"
            )

        # Portfolio summary
        if self.portfolio_manager:
            portfolio_summary = self.portfolio_manager.get_portfolio_summary()
            logger.info(
                f"Final Portfolio: "
                f"Positions={portfolio_summary.get('total_positions', 0)}, "
                f"Profit={portfolio_summary.get('profit', 0):.2f}"
            )

        # Send shutdown notification
        if self.notifier:
            self.notifier.notify_shutdown()

        # Close MT5 connection
        if self.client:
            try:
                self.client.shutdown()
                logger.info("MT5 connection closed")
            except Exception as e:
                logger.error(f"Error closing MT5 connection: {e}")

        logger.info("Shutdown complete")

    def get_status(self) -> Dict:
        """Get current status of all strategies.

        Returns:
            Dictionary with status information
        """
        strategy_status = []
        for instance in self.strategies:
            strategy_status.append(
                {
                    "name": instance.name,
                    "symbol": instance.symbol,
                    "timeframe": instance.timeframe,
                    "signals_detected": instance.signals_detected,
                    "trades_executed": instance.trades_executed,
                    "trades_failed": instance.trades_failed,
                    "last_signal_time": (
                        instance.last_signal_time.isoformat()
                        if instance.last_signal_time
                        else None
                    ),
                    "last_trade_time": (
                        instance.last_trade_time.isoformat()
                        if instance.last_trade_time
                        else None
                    ),
                }
            )

        portfolio_summary = (
            self.portfolio_manager.get_portfolio_summary()
            if self.portfolio_manager
            else {}
        )

        return {
            "initialized": self._initialized,
            "running": self._running,
            "state": (
                self.state_manager.get_state_summary() if self.state_manager else {}
            ),
            "portfolio": portfolio_summary,
            "strategies": strategy_status,
        }

    def _export_status(self):
        """Export current status to JSON file for dashboard (throttled)."""
        try:
            # Only export if interval has passed
            current_time = time.time()
            if current_time - self._last_status_export < self._status_export_interval:
                return

            self._last_status_export = current_time

            status = self.get_status()

            # Write to status file
            status_file = Path("multi_strategy_status.json")
            with open(status_file, "w") as f:
                json.dump(status, f, indent=2)

            logger.debug("Status exported for dashboard")

        except Exception as e:
            logger.debug(f"Error exporting status: {e}")

    def __repr__(self) -> str:
        """Return string representation of MultiStrategyEngine."""
        return (
            f"MultiStrategyEngine(strategies={len(self.strategies)}, "
            f"initialized={self._initialized}, running={self._running})"
        )



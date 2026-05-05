"""Live Trading Entry Point.

Command-line entry point for the live trading system.

Usage:
    python -m services.execution.live.run --config backend_retiring/config/live_trading_config.json
"""

import argparse
import signal
import sys
from pathlib import Path
from typing import Optional

from services.execution.live.engine import MultiStrategyEngine
from services.utils.logger import logger


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="HaruQuant Live Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single strategy
    python -m services.execution.live.run --config backend_retiring/config/live_trading_config.json

    # Multiple strategies
    python -m services.execution.live.run --config backend_retiring/config/multi_strategy_config.json

The configuration file should define:
    - MT5 connection (single shared connection)
    - Portfolio-level risk management rules
    - One or more strategies with their parameters
    - Notification settings
    - Logging configuration

Benefits:
    - Single MT5 connection (MT5 limitation)
    - Portfolio-level risk management
    - Centralized monitoring
    - Correlation checks across strategies
    - Unified trade execution control
    - Dynamic strategy type loading

For monitoring, run the dashboard in a separate terminal:
    python -m services.execution.live.dashboard

For more information, see the documentation.
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration file (TOML preferred, JSON supported)",
    )

    return parser.parse_args()


def validate_config_path(config_path: str) -> bool:
    """Validate configuration file exists.

    Args:
        config_path: Path to configuration file

    Returns:
        True if file exists
    """
    path = Path(config_path)

    if not path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return False

    if not path.is_file():
        logger.error(f"Configuration path is not a file: {config_path}")
        return False

    if path.suffix.lower() not in {".toml", ".json"}:
        logger.warning(
            f"Configuration file does not have .toml or .json extension: {config_path}"
        )

    return True


def setup_engine(config_path: str) -> Optional[MultiStrategyEngine]:
    """Initialize and setup the trading engine.

    Args:
        config_path: Path to configuration file

    Returns:
        Initialized engine or None if failed
    """
    logger.info("Starting HaruQuant Live Trading System")
    logger.info(f"Config file: {config_path}")

    try:
        engine = MultiStrategyEngine(config_path)
    except Exception as e:
        logger.critical(f"Failed to create engine: {e}", exc_info=True)
        return None

    logger.info("Initializing trading engine...")
    try:
        if not engine.initialize():
            logger.critical("Engine initialization failed")
            return None
    except Exception as e:
        logger.critical(f"Engine initialization error: {e}", exc_info=True)
        return None

    return engine


def register_signal_handlers(engine: MultiStrategyEngine):
    """Register signal handlers for graceful shutdown.

    Args:
        engine: Trading engine instance
    """

    def shutdown_handler(signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name} ({signum}), initiating shutdown...")
        engine.stop()

    signal.signal(signal.SIGINT, shutdown_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_handler)  # Termination signal


def print_startup_info(engine: MultiStrategyEngine):
    """Print engine startup information.

    Args:
        engine: Trading engine instance
    """
    logger.info("=" * 80)
    logger.info("Live Trading Engine Started Successfully")
    logger.info("=" * 80)
    logger.info(f"Strategies: {len(engine.strategies)}")
    for instance in engine.strategies:
        logger.info(f"  - {instance.name} ({instance.symbol} {instance.timeframe})")
    logger.info("=" * 80)
    logger.info("\nTo monitor in real-time, open another terminal and run:")
    logger.info("  python -m services.execution.live.dashboard")
    logger.info("=" * 80)


def main():
    """Execute main entry point logic."""
    # Parse arguments
    args = parse_arguments()

    # Validate config path
    if not validate_config_path(args.config):
        return 1

    # Setup engine
    engine = setup_engine(args.config)
    if not engine:
        return 1

    # Setup signal handlers
    register_signal_handlers(engine)

    # Print startup info
    print_startup_info(engine)

    # Run engine
    logger.info("Starting trading engine...")
    try:
        engine.run()
    except Exception as e:
        logger.critical(f"Fatal error in engine: {e}", exc_info=True)
        return 1

    logger.info("Live trading system stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

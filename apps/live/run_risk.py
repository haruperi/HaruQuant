"""Live Trading with Risk Management Entry Point.

Command-line entry point for the risk-integrated live trading system.

Usage:
    python -m apps.live.run_risk --config backend/config/risk_enabled_multi_strategy.json
"""

import argparse
import signal
import sys
from pathlib import Path
from typing import Optional

from apps.live.risk_engine import RiskIntegratedEngine
from backend.common.logger import logger


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="HaruQuant Risk-Integrated Live Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Risk-enabled multi-strategy trading
    python -m apps.live.run_risk --config backend/config/risk_enabled_multi_strategy.json

Risk Management Features:
    - Dynamic position sizing (fixed_risk, Kelly, volatility, etc.)
    - Regime detection (NORMAL vs STRESS)
    - Risk budget allocation (risk parity)
    - Hard risk constraints (VaR, ES, margin, concentration)
    - Cluster limits per asset class
    - Correlation-aware allocation

The configuration file must include:
    - risk_management section with limits, regime detector, etc.
    - position_sizing method and config
    - symbol_clusters for cluster limits
    - risk_budget per strategy

For monitoring, run the dashboard in a separate terminal:
    python -m apps.live.dashboard

For more information, see apps/risk/README.md
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to risk-enabled configuration file (TOML preferred, JSON supported)",
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


def setup_engine(config_path: str) -> Optional[RiskIntegratedEngine]:
    """Initialize and setup the risk-integrated trading engine.

    Args:
        config_path: Path to configuration file

    Returns:
        Initialized engine or None if failed
    """
    logger.info("=" * 80)
    logger.info("Starting HaruQuant Risk-Integrated Live Trading System")
    logger.info("=" * 80)
    logger.info(f"Config file: {config_path}")

    try:
        engine = RiskIntegratedEngine(config_path)
    except Exception as e:
        logger.critical(f"Failed to create engine: {e}", exc_info=True)
        return None

    logger.info("Initializing trading engine with risk management...")
    try:
        if not engine.initialize():
            logger.critical("Engine initialization failed")
            return None
    except Exception as e:
        logger.critical(f"Engine initialization error: {e}", exc_info=True)
        return None

    return engine


def register_signal_handlers(engine: RiskIntegratedEngine):
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


def print_startup_info(engine: RiskIntegratedEngine):
    """Print engine startup information.

    Args:
        engine: Trading engine instance
    """
    logger.info("=" * 80)
    logger.info("Risk-Integrated Live Trading Engine Started Successfully")
    logger.info("=" * 80)
    logger.info(f"Strategies: {len(engine.strategies)}")
    for instance in engine.strategies:
        risk_budget = instance.config.get("risk_budget", "N/A")
        logger.info(
            f"  - {instance.name} ({instance.symbol} {instance.timeframe}) "
            f"[Risk Budget: {risk_budget}]"
        )
    logger.info("=" * 80)
    logger.info("Risk Management:")
    if engine.risk_enabled:
        logger.info("  Status: ENABLED")
        if engine.position_sizer:
            logger.info(f"  Position Sizing: {engine.position_sizer.method}")
        if engine.current_regime:
            logger.info(f"  Current Regime: {engine.current_regime.name}")
    else:
        logger.info("  Status: DISABLED (using legacy mode)")
    logger.info("=" * 80)
    logger.info("\nTo monitor in real-time, open another terminal and run:")
    logger.info("  python -m apps.live.dashboard")
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
    logger.info("Starting risk-integrated trading engine...")
    try:
        engine.run()
    except Exception as e:
        logger.critical(f"Fatal error in engine: {e}", exc_info=True)
        return 1

    logger.info("Risk-integrated live trading system stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())


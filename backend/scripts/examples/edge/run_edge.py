#!/usr/bin/env python
"""Run Edge CLI helper.

Type: manual demo

This script runs Edge Discovery Strategies (EDS) on real MT5 data
to find and statistically validate trading edges.

Usage:
    # With real MT5 data
    python run_edge.py --symbol EURUSD --timeframe M15 --eds all

    # With demo data (no MT5 required)
    python run_edge.py --symbol EURGBP --timeframe M15 --eds all --demo

    # Multiple symbols
    python run_edge.py --symbols EURUSD,GBPUSD,USDJPY --timeframe H1 --eds mr

    # Specific EDS
    python run_edge.py --symbol EURUSD --timeframe M15 --eds null  # EDS-0: Null baseline
    python run_edge.py --symbol EURUSD --timeframe M15 --eds mr    # EDS-1: Mean reversion
    python run_edge.py --symbol EURUSD --timeframe M15 --eds tp    # EDS-2: Trend persistence
    python run_edge.py --symbol EURUSD --timeframe M15 --eds session  # EDS-3: Session edge

    # Save to database
    python run_edge.py --symbol EURUSD --timeframe M15 --eds all --save-db

    # Skip saving trades (faster, less storage)
    python run_edge.py --symbol EURUSD --timeframe M15 --eds all --save-db --no-trades
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.services.research.config import (  # noqa: E402
    BootstrapConfig,
    DataConfig,
    EdgeLabConfig,
    PermutationConfig,
)
from backend.services.research.datasets import DataSource, load_ohlc, normalize_columns  # noqa: E402
from backend.services.research.eds_mean_reversion import run_eds_mean_reversion  # noqa: E402
from backend.services.research.eds_null_models import run_eds_null_baseline  # noqa: E402
from backend.services.research.eds_session import run_eds_session  # noqa: E402
from backend.services.research.eds_trend_persistence import run_eds_trend_persistence  # noqa: E402
from backend.services.research.reporting import (  # noqa: E402
    generate_multi_symbol_report,
    print_result_summary,
    save_json,
    save_markdown,
)
from backend.services.research.results_schema import EdgeResult  # noqa: E402
from backend.common.logger import logger  # noqa: E402
from backend.data.database.sqlite import SQLiteDatabase  # noqa: E402
from backend.data.database.sqlite.edge_discovery import EdgeDiscoveryManager  # noqa: E402
from backend.data.database.sqlite.users import UserManager  # noqa: E402


class DummyMT5Client:
    """Demo data source for testing without MT5.

    Generates synthetic price data with realistic properties.
    """

    def fetch_data(
        self, symbol: str, timeframe: str, start_pos: int, end_pos: int
    ) -> pd.DataFrame:
        """Generate synthetic OHLC data."""
        n = max(2000, end_pos)
        freq = self._timeframe_to_freq(timeframe)
        idx = pd.date_range("2020-01-01", periods=n, freq=freq)

        # Use symbol hash for reproducible but different data per symbol
        rng = np.random.default_rng(abs(hash(symbol)) % (2**32))

        # Generate realistic price movement
        rets = rng.normal(0, 0.0003, size=n)
        # Add some trending behavior
        trend = np.cumsum(rng.normal(0, 0.00001, size=n))
        rets = rets + trend

        # Generate prices
        base_price = 1.0 if "USD" in symbol else 100.0
        px = base_price * np.exp(np.cumsum(rets))

        # Generate OHLC from close
        spread = np.abs(rng.normal(0, 0.0002, size=n))
        high = px + spread
        low = px - spread
        open_ = np.roll(px, 1)
        open_[0] = px[0]

        # Add some realistic intraday patterns
        hour = idx.hour
        volatility_multiplier = np.where(
            (hour >= 7) & (hour < 16), 1.5, 0.8  # Higher vol during London/NY
        )
        high = px + spread * volatility_multiplier
        low = px - spread * volatility_multiplier

        return pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": px,
                "Volume": rng.integers(100, 1000, size=n),
            },
            index=idx,
        )

    def _timeframe_to_freq(self, tf: str) -> str:
        """Convert MT5 timeframe to pandas frequency."""
        mapping = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "M30": "30min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1D",
            "W1": "1W",
        }
        return mapping.get(tf.upper(), "15min")


def get_mt5_client():
    """Get MT5 client with credentials from database.

    This follows the pattern from tests/usage/backtest for proper MT5 connection.
    """
    from backend.mcp.mt5_mcp.client import MT5Client

    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("Failed to get MT5 credentials from database")
        return None

    try:
        client = MT5Client(
            login=creds["login"],
            password=creds["password"],
            server=creds["server"],
            path=creds["path"],
        )
        if client.is_connected():
            logger.success(f"Connected to MT5 (login: {creds['login']})")
            return client
        else:
            logger.error("MT5 client created but not connected")
            return None
    except Exception as e:
        logger.error(f"Failed to connect to MT5: {e}")
        return None


class MT5DataSource:
    """Real MT5 data source wrapper."""

    def __init__(self):
        """Initialize MT5 client with credentials from database."""
        self.client = get_mt5_client()
        self.connected = self.client is not None and self.client.is_connected()

    def fetch_data(
        self, symbol: str, timeframe: str, start_pos: int, end_pos: int
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLC data from MT5."""
        if not self.connected or self.client is None:
            logger.error("MT5 not connected")
            return None

        count = end_pos - start_pos
        df = self.client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
            start_pos=start_pos,
        )

        if df is None or df.empty:
            logger.error(f"No data returned for {symbol} {timeframe}")
            return None

        # Normalize column names
        df = normalize_columns(df)
        return df


def run_edge_discovery(  # noqa: C901
    symbol: str,
    timeframe: str,
    eds_type: str,
    cfg: EdgeLabConfig,
    source,
    outdir: Path,
    save_to_db: bool = False,
    save_trades: bool = True,
    db_manager: Optional[EdgeDiscoveryManager] = None,
) -> List[EdgeResult]:
    """Run edge discovery for a symbol.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe string
        eds_type: EDS type ("all", "null", "mr", "tp", "session")
        cfg: EdgeLab configuration
        source: Data source (MT5 or dummy)
        outdir: Output directory
        save_to_db: Whether to save results to database
        save_trades: Whether to save individual trades to database
        db_manager: EdgeDiscoveryManager instance for database saving

    Returns:
        List of EdgeResult objects
    """
    logger.info(f"Running edge discovery for {symbol} {timeframe}")

    # Load data
    try:
        df = load_ohlc(
            source=source,
            symbol=cfg.data.symbol,
            timeframe=cfg.data.timeframe,
            start_pos=cfg.data.start_pos,
            end_pos=cfg.data.end_pos,
            exclude_last_bar=cfg.data.exclude_last_bar,
        )
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return []

    results: List[EdgeResult] = []

    def _save_result(res: EdgeResult):
        """Save result to files and optionally database."""
        save_markdown(
            res, outdir / f"{symbol}_{timeframe}_{res.eds_name.replace(' ', '_')}.md"
        )
        save_json(
            res, outdir / f"{symbol}_{timeframe}_{res.eds_name.replace(' ', '_')}.json"
        )
        print_result_summary(res)

        # Save to database if requested
        if save_to_db and db_manager:
            try:
                run_id = db_manager.save_edge_result(
                    result=res.to_dict(),
                    save_trades=save_trades,
                )
                if run_id:
                    logger.info(f"Saved to database: run_id={run_id}")
            except Exception as e:
                logger.error(f"Failed to save to database: {e}")

    # EDS-0: Null Models / Baseline
    if eds_type in ("all", "null"):
        logger.info("Running EDS-0: Null Baseline")
        try:
            res = run_eds_null_baseline(
                df, symbol, timeframe, cfg.null, cfg.bootstrap, cfg.perm
            )
            results.append(res)
            _save_result(res)
        except Exception as e:
            logger.error(f"EDS-0 failed: {e}")

    # EDS-1: Mean Reversion
    if eds_type in ("all", "mr"):
        logger.info("Running EDS-1: Mean Reversion")
        try:
            res = run_eds_mean_reversion(
                df, symbol, timeframe, cfg.mr, cfg.bootstrap, cfg.perm
            )
            results.append(res)
            _save_result(res)
        except Exception as e:
            logger.error(f"EDS-1 failed: {e}")

    # EDS-2: Trend Persistence
    if eds_type in ("all", "tp"):
        logger.info("Running EDS-2: Trend Persistence")
        try:
            res = run_eds_trend_persistence(
                df, symbol, timeframe, cfg.tp, cfg.bootstrap, cfg.perm
            )
            results.append(res)
            _save_result(res)
        except Exception as e:
            logger.error(f"EDS-2 failed: {e}")

    # EDS-3: Session Edge
    if eds_type in ("all", "session"):
        logger.info("Running EDS-3: Session Edge")
        try:
            res = run_eds_session(
                df,
                symbol,
                timeframe,
                cfg.session_edge,
                cfg.sessions,
                cfg.bootstrap,
                cfg.perm,
            )
            results.append(res)
            _save_result(res)
        except Exception as e:
            logger.error(f"EDS-3 failed: {e}")

    return results


def main():
    """Run the main entry point."""
    ap = argparse.ArgumentParser(
        description="Edge Lab: Symbol edge discovery runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Symbol options
    symbol_group = ap.add_mutually_exclusive_group(required=True)
    symbol_group.add_argument(
        "--symbol", type=str, help="Single symbol to analyze (e.g., EURUSD)"
    )
    symbol_group.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated symbols (e.g., EURUSD,GBPUSD,USDJPY)",
    )

    # Other arguments
    ap.add_argument(
        "--timeframe", type=str, default="M15", help="Timeframe (default: M15)"
    )
    ap.add_argument(
        "--eds",
        type=str,
        default="all",
        choices=["all", "null", "mr", "tp", "session"],
        help="EDS type to run (default: all)",
    )
    ap.add_argument(
        "--outdir",
        type=str,
        default="backend/data/edge_lab_outputs",
        help="Output directory (default: backend/data/edge_lab_outputs)",
    )
    ap.add_argument(
        "--end_pos",
        type=int,
        default=5000,
        help="Number of bars to analyze (default: 5000)",
    )
    ap.add_argument("--demo", action="store_true", help="Use demo data instead of MT5")
    ap.add_argument(
        "--n_boot", type=int, default=2000, help="Bootstrap iterations (default: 2000)"
    )
    ap.add_argument(
        "--n_perm",
        type=int,
        default=2000,
        help="Permutation iterations (default: 2000)",
    )
    ap.add_argument("--save-db", action="store_true", help="Save results to database")
    ap.add_argument(
        "--no-trades",
        action="store_true",
        help="Don't save individual trades to database (faster, less storage)",
    )

    args = ap.parse_args()

    # Setup output directory
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Setup database manager if saving to database
    db_manager: Optional[EdgeDiscoveryManager] = None
    if args.save_db:
        try:
            db = SQLiteDatabase()
            db.initialize_database()
            db_manager = db
            logger.info("Database initialized for edge discovery")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("Continuing without database saving")

    # Setup data source
    if args.demo:
        logger.info("Using demo data source")
        source: DataSource = DummyMT5Client()
    else:
        logger.info("Connecting to MT5")
        mt5_source = MT5DataSource()
        if not mt5_source.connected:
            logger.warning("MT5 not connected, falling back to demo data")
            source = DummyMT5Client()
        else:
            source = mt5_source

    # Parse symbols
    if args.symbol:
        symbols = [args.symbol]
    else:
        symbols = [s.strip() for s in args.symbols.split(",")]

    logger.info(f"Analyzing {len(symbols)} symbol(s): {symbols}")

    # Run analysis for each symbol
    all_results: List[EdgeResult] = []

    for symbol in symbols:
        # Create config for this symbol
        cfg = EdgeLabConfig(
            data=DataConfig(
                symbol=symbol,
                timeframe=args.timeframe,
                end_pos=args.end_pos,
            ),
            bootstrap=BootstrapConfig(n_boot=args.n_boot),
            perm=PermutationConfig(n_perm=args.n_perm),
        )

        results = run_edge_discovery(
            symbol=symbol,
            timeframe=args.timeframe,
            eds_type=args.eds,
            cfg=cfg,
            source=source,
            outdir=outdir,
            save_to_db=args.save_db,
            save_trades=not args.no_trades,
            db_manager=db_manager,
        )

        all_results.extend(results)

    # Generate summary report if multiple results
    if len(all_results) > 1:
        generate_multi_symbol_report(all_results, outdir)

    logger.success(f"Done. Wrote {len(all_results)} result(s) to: {outdir.resolve()}")

    # Print final summary
    confirmed = sum(
        1 for r in all_results if r.stats.ci_low > 0 and r.stats.p_value_perm < 0.05
    )
    print(f"\n{'='*60}")
    print("  EDGE LAB SUMMARY")
    print(f"{'='*60}")
    print(f"  Symbols analyzed: {len(symbols)}")
    print(f"  Total results: {len(all_results)}")
    print(f"  Edges confirmed: {confirmed}")
    print(f"  Output: {outdir.resolve()}")
    if args.save_db:
        print("  Database: Results saved to database")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()


#!/usr/bin/env python
"""Edge Discovery Example: Complete workflow with real MT5 data.

Type: live-broker dependent manual demo

This example demonstrates how to use the Edge Lab framework to:
1. Connect to MT5 and fetch real market data
2. Run edge discovery strategies (EDS)
3. Validate findings statistically
4. Generate reports

Prerequisites:
- MT5 terminal running and logged in
- Python packages: numpy, pandas, MetaTrader5

Run from project root:
    python backend/scripts/examples/edge/edge_discovery_example.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from services.research import (  # noqa: E402 # Config; Data; Features; EDS Runners; Reporting
    BootstrapConfig,
    DataConfig,
    EdgeLabConfig,
    MeanReversionConfig,
    PermutationConfig,
    TrendPersistenceConfig,
    atr,
    bb_width,
    generate_multi_symbol_report,
    hurst_exponent,
    load_ohlc,
    print_result_summary,
    rsi,
    run_eds_mean_reversion,
    run_eds_null_baseline,
    run_eds_session,
    run_eds_trend_persistence,
    save_json,
    save_markdown,
    tag_sessions,
    validate_data_quality,
    zscore,
)
from services.utils.logger import logger  # noqa: E402


def create_mt5_source():
    """Create MT5 data source with connection handling."""
    try:
        from backend.mcp.mt5_mcp.client import MT5Client

        client = MT5Client()
        if client.is_connected():
            logger.success("Connected to MT5 terminal")
            return client
        else:
            logger.warning("MT5 client created but not connected")
            return None
    except ImportError:
        logger.error("MT5 module not available")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to MT5: {e}")
        return None


def create_demo_source():
    """Create demo data source for testing."""

    class DemoSource:
        def fetch_data(self, symbol, timeframe, start_pos, end_pos):
            n = end_pos
            freq = {
                "M1": "1min",
                "M5": "5min",
                "M15": "15min",
                "M30": "30min",
                "H1": "1h",
                "H4": "4h",
            }.get(timeframe, "15min")
            idx = pd.date_range("2022-01-01", periods=n, freq=freq)

            rng = np.random.default_rng(abs(hash(symbol)) % 2**32)
            rets = rng.normal(0, 0.0003, n)
            px = 1.0 * np.exp(np.cumsum(rets))
            spread = np.abs(rng.normal(0, 0.0002, n))

            # Add session-based volatility
            hour = idx.hour
            vol_mult = np.where((hour >= 7) & (hour < 16), 1.5, 0.8)

            return pd.DataFrame(
                {
                    "Open": np.roll(px, 1),
                    "High": px + spread * vol_mult,
                    "Low": px - spread * vol_mult,
                    "Close": px,
                    "Volume": rng.integers(100, 1000, n),
                },
                index=idx,
            )

    return DemoSource()


def example_1_basic_edge_discovery():
    """Run example 1: basic edge discovery for a single symbol."""
    print("\n" + "=" * 70)
    print("  EXAMPLE 1: Basic Edge Discovery")
    print("=" * 70 + "\n")

    # Try MT5, fallback to demo
    source = create_mt5_source()
    if source is None:
        logger.info("Using demo data source")
        source = create_demo_source()

    # Configure analysis
    symbol = "EURUSD"
    timeframe = "M15"
    bars = 5000

    cfg = EdgeLabConfig(
        data=DataConfig(symbol=symbol, timeframe=timeframe, end_pos=bars),
        bootstrap=BootstrapConfig(n_boot=1000),  # Faster for demo
        perm=PermutationConfig(n_perm=1000),
    )

    # Load data
    logger.info(f"Loading data for {symbol} {timeframe}")
    df = load_ohlc(source, symbol, timeframe, 0, bars, exclude_last_bar=True)

    # Validate data quality
    quality = validate_data_quality(df)
    logger.info(f"Data quality: {quality['n_rows']} bars, valid={quality['valid']}")

    # Run Mean Reversion EDS
    logger.info("Running EDS-1: Mean Reversion")
    result = run_eds_mean_reversion(
        df, symbol, timeframe, cfg.mr, cfg.bootstrap, cfg.perm
    )

    # Print summary
    print_result_summary(result)

    # Save report
    outdir = ROOT_DIR / "backend" / "data" / "edge_lab_outputs" / "example_1"
    outdir.mkdir(parents=True, exist_ok=True)
    save_markdown(result, outdir / "EURUSD_M15_meanreversion.md", include_trades=True)
    save_json(result, outdir / "EURUSD_M15_meanreversion.json")

    logger.success(f"Report saved to {outdir}")
    return result


def example_2_multi_symbol_screening():
    """Run example 2: screen multiple symbols for edges."""
    print("\n" + "=" * 70)
    print("  EXAMPLE 2: Multi-Symbol Edge Screening")
    print("=" * 70 + "\n")

    source = create_mt5_source()
    if source is None:
        logger.info("Using demo data source")
        source = create_demo_source()

    # FX majors to screen
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
    timeframe = "H1"
    bars = 3000

    cfg = EdgeLabConfig(
        data=DataConfig(symbol="", timeframe=timeframe, end_pos=bars),
        bootstrap=BootstrapConfig(n_boot=500),  # Fast mode
        perm=PermutationConfig(n_perm=500),
    )

    results = []
    for symbol in symbols:
        logger.info(f"Analyzing {symbol}")
        try:
            df = load_ohlc(source, symbol, timeframe, 0, bars, exclude_last_bar=True)

            # Run all EDS
            mr_result = run_eds_mean_reversion(
                df, symbol, timeframe, cfg.mr, cfg.bootstrap, cfg.perm
            )
            tp_result = run_eds_trend_persistence(
                df, symbol, timeframe, cfg.tp, cfg.bootstrap, cfg.perm
            )

            results.append(mr_result)
            results.append(tp_result)

        except Exception as e:
            logger.error(f"Failed to analyze {symbol}: {e}")

    # Generate combined report
    outdir = ROOT_DIR / "backend" / "data" / "edge_lab_outputs" / "example_2_screening"
    generate_multi_symbol_report(results, outdir)

    # Print summary
    confirmed = sum(
        1 for r in results if r.stats.ci_low > 0 and r.stats.p_value_perm < 0.05
    )
    print(f"\nScreening complete: {confirmed}/{len(results)} edges confirmed")
    print(f"Results saved to: {outdir}")

    return results


def example_3_session_analysis():
    """Run example 3: session-based edge analysis."""
    print("\n" + "=" * 70)
    print("  EXAMPLE 3: Session Edge Analysis")
    print("=" * 70 + "\n")

    source = create_mt5_source()
    if source is None:
        logger.info("Using demo data source")
        source = create_demo_source()

    symbol = "GBPUSD"
    timeframe = "M15"
    bars = 10000  # More data for session analysis

    cfg = EdgeLabConfig(
        data=DataConfig(symbol=symbol, timeframe=timeframe, end_pos=bars),
        bootstrap=BootstrapConfig(n_boot=1000),
        perm=PermutationConfig(n_perm=1000),
    )

    # Load and tag sessions
    df = load_ohlc(source, symbol, timeframe, 0, bars, exclude_last_bar=True)
    df = tag_sessions(df)

    # Print session distribution
    session_counts = df["session"].value_counts()
    print("Session Distribution:")
    for sess, count in session_counts.items():
        print(f"  {sess}: {count} bars ({count/len(df)*100:.1f}%)")

    # Run session edge detector
    logger.info("Running EDS-3: Session Edge")
    result = run_eds_session(
        df, symbol, timeframe, cfg.session_edge, cfg.sessions, cfg.bootstrap, cfg.perm
    )

    print_result_summary(result)

    # Print session-specific results
    extras = result.stats.extras or {}
    strategy_results = extras.get("strategy_results", {})
    if strategy_results:
        print("\nSession Strategy Results:")
        for name, stats in strategy_results.items():
            sig = stats.get("significant_after_fdr", False)
            print(
                f"  {name}: expectancy={stats.get('expectancy', 0):.4f}, "
                f"p={stats.get('p_value', 1):.4f}, FDR_sig={sig}"
            )

    # Save
    outdir = ROOT_DIR / "backend" / "data" / "edge_lab_outputs" / "example_3_session"
    outdir.mkdir(parents=True, exist_ok=True)
    save_markdown(result, outdir / f"{symbol}_{timeframe}_session.md")
    save_json(result, outdir / f"{symbol}_{timeframe}_session.json")

    return result


def example_4_custom_parameters():
    """Run example 4: custom EDS parameters for specific market conditions."""
    print("\n" + "=" * 70)
    print("  EXAMPLE 4: Custom EDS Parameters")
    print("=" * 70 + "\n")

    source = create_mt5_source()
    if source is None:
        logger.info("Using demo data source")
        source = create_demo_source()

    symbol = "USDJPY"
    timeframe = "H1"
    bars = 5000

    # Custom mean reversion config for USDJPY
    # JPY pairs often have different volatility characteristics
    custom_mr = MeanReversionConfig(
        sma_n=20,
        z_entry=1.8,  # Lower z threshold
        bbw_n=20,
        bbw_k=2.0,
        compression_window=100,  # Shorter window for H1
        compression_q=0.30,  # Slightly higher threshold
        atr_n=14,
        max_hold_bars=24,  # ~1 day on H1
        k_stop_atr=1.0,  # Tighter stop for JPY
    )

    # Custom trend config
    custom_tp = TrendPersistenceConfig(
        breakout_n=15,  # Shorter breakout period
        atr_n=14,
        atr_regime_window=100,
        atr_q_high=0.75,
        max_hold_bars=36,
        k_stop_atr=1.2,
        k_target_atr=0.8,  # Smaller target for JPY
    )

    cfg = EdgeLabConfig(
        data=DataConfig(symbol=symbol, timeframe=timeframe, end_pos=bars),
        bootstrap=BootstrapConfig(n_boot=1000),
        perm=PermutationConfig(n_perm=1000),
        mr=custom_mr,
        tp=custom_tp,
    )

    df = load_ohlc(source, symbol, timeframe, 0, bars, exclude_last_bar=True)

    # Run with custom configs
    logger.info("Running EDS with custom parameters")
    mr_result = run_eds_mean_reversion(
        df, symbol, timeframe, cfg.mr, cfg.bootstrap, cfg.perm
    )
    tp_result = run_eds_trend_persistence(
        df, symbol, timeframe, cfg.tp, cfg.bootstrap, cfg.perm
    )

    print_result_summary(mr_result)
    print_result_summary(tp_result)

    # Save
    outdir = ROOT_DIR / "backend" / "data" / "edge_lab_outputs" / "example_4_custom"
    outdir.mkdir(parents=True, exist_ok=True)
    save_markdown(mr_result, outdir / f"{symbol}_{timeframe}_mr_custom.md")
    save_markdown(tp_result, outdir / f"{symbol}_{timeframe}_tp_custom.md")

    return mr_result, tp_result


def example_5_null_baseline_comparison():
    """Run example 5: establish null baseline and compare strategy results."""
    print("\n" + "=" * 70)
    print("  EXAMPLE 5: Null Baseline Comparison")
    print("=" * 70 + "\n")

    source = create_mt5_source()
    if source is None:
        logger.info("Using demo data source")
        source = create_demo_source()

    symbol = "EURUSD"
    timeframe = "M15"
    bars = 5000

    cfg = EdgeLabConfig(
        data=DataConfig(symbol=symbol, timeframe=timeframe, end_pos=bars),
        bootstrap=BootstrapConfig(n_boot=1000),
        perm=PermutationConfig(n_perm=1000),
    )

    df = load_ohlc(source, symbol, timeframe, 0, bars, exclude_last_bar=True)

    # Step 1: Establish null baseline
    logger.info("Step 1: Computing null baseline (what random trading produces)")
    null_result = run_eds_null_baseline(
        df, symbol, timeframe, cfg.null, cfg.bootstrap, cfg.perm
    )

    # Extract thresholds from null
    extras = null_result.stats.extras or {}
    thresholds = extras.get("thresholds", {})

    print("\nNull Baseline Results:")
    print(
        f"  R-space null (32 bars, BUY) p95: {thresholds.get('buy_threshold_r32', 'N/A'):.4f}"
    )
    print(
        f"  R-space null (32 bars, BUY) mean: {thresholds.get('buy_null_mean_r32', 'N/A'):.4f}"
    )
    print("\n  Your strategy must beat the p95 threshold to show edge.\n")

    # Step 2: Run actual strategy
    logger.info("Step 2: Running mean reversion strategy")
    mr_result = run_eds_mean_reversion(
        df, symbol, timeframe, cfg.mr, cfg.bootstrap, cfg.perm
    )

    print_result_summary(mr_result)

    # Step 3: Compare to null
    print("\nComparison to Null Baseline:")
    strategy_exp = mr_result.stats.expectancy_r
    null_p95 = thresholds.get("buy_threshold_r32", 0)
    null_mean = thresholds.get("buy_null_mean_r32", 0)

    print(f"  Strategy expectancy: {strategy_exp:.4f} R")
    print(f"  Null p95 threshold:  {null_p95:.4f} R")
    print(f"  Null mean:           {null_mean:.4f} R")

    if strategy_exp > null_p95:
        print("\n  RESULT: Strategy EXCEEDS null p95 - potential edge detected!")
    elif strategy_exp > null_mean:
        print("\n  RESULT: Strategy above null mean but below p95 - weak signal")
    else:
        print("\n  RESULT: Strategy below null mean - no edge detected")

    # Save
    outdir = ROOT_DIR / "backend" / "data" / "edge_lab_outputs" / "example_5_null"
    outdir.mkdir(parents=True, exist_ok=True)
    save_markdown(null_result, outdir / f"{symbol}_{timeframe}_null_baseline.md")
    save_markdown(mr_result, outdir / f"{symbol}_{timeframe}_mr_vs_null.md")

    return null_result, mr_result


def example_6_exploratory_analysis():
    """Run example 6: exploratory data analysis before strategy development."""
    print("\n" + "=" * 70)
    print("  EXAMPLE 6: Exploratory Data Analysis")
    print("=" * 70 + "\n")

    source = create_mt5_source()
    if source is None:
        logger.info("Using demo data source")
        source = create_demo_source()

    symbol = "EURUSD"
    timeframe = "H1"
    bars = 5000

    # Load data
    from services.utils.datasets import compute_session_stats

    df = load_ohlc(source, symbol, timeframe, 0, bars, exclude_last_bar=True)
    df = tag_sessions(df)

    # 1. Basic statistics
    print("1. BASIC STATISTICS")
    print("-" * 40)
    close = df["Close"].astype(float)
    log_rets = np.log(close / close.shift(1)).dropna()

    print(f"  Data range: {df.index[0]} to {df.index[-1]}")
    print(f"  Total bars: {len(df)}")
    print(f"  Mean return: {log_rets.mean():.6f}")
    print(f"  Std return:  {log_rets.std():.6f}")
    print(f"  Skewness:    {log_rets.skew():.4f}")
    print(f"  Kurtosis:    {log_rets.kurtosis():.4f}")

    # 2. Session analysis
    print("\n2. SESSION STATISTICS")
    print("-" * 40)
    session_stats = compute_session_stats(df)
    print(session_stats.to_string())

    # 3. Volatility regime
    print("\n3. VOLATILITY REGIME")
    print("-" * 40)
    df["atr"] = atr(df, 14)
    df["atr_pct"] = (df["atr"] / df["Close"]) * 100

    print(f"  Current ATR: {df['atr'].iloc[-1]:.5f}")
    print(f"  ATR %:       {df['atr_pct'].iloc[-1]:.3f}%")
    print(f"  ATR 20-pctl: {df['atr'].quantile(0.20):.5f}")
    print(f"  ATR 80-pctl: {df['atr'].quantile(0.80):.5f}")

    # 4. Mean reversion characteristics
    print("\n4. MEAN REVERSION ANALYSIS")
    print("-" * 40)
    df["z"] = zscore(close, 20)
    df["bbw"] = bb_width(close, 20, 2)
    df["rsi"] = rsi(close, 14)

    # Estimate Hurst exponent
    H = hurst_exponent(close, lags=20)
    print(f"  Hurst exponent: {H:.4f}")
    if H < 0.45:
        print("    -> Suggests MEAN REVERTING behavior")
    elif H > 0.55:
        print("    -> Suggests TRENDING behavior")
    else:
        print("    -> Suggests RANDOM WALK behavior")

    # Z-score distribution
    z_vals = df["z"].dropna()
    print(
        f"  Z-score > 2:  {(z_vals > 2).sum()} occurrences ({(z_vals > 2).mean()*100:.1f}%)"
    )
    print(
        f"  Z-score < -2: {(z_vals < -2).sum()} occurrences ({(z_vals < -2).mean()*100:.1f}%)"
    )

    # 5. Compression analysis
    print("\n5. COMPRESSION ANALYSIS")
    print("-" * 40)
    bbw_vals = df["bbw"].dropna()
    compression_threshold = bbw_vals.quantile(0.25)
    n_compressed = (bbw_vals <= compression_threshold).sum()
    print(f"  BBW 25th percentile: {compression_threshold:.4f}")
    print(
        f"  Compressed bars:     {n_compressed} ({n_compressed/len(bbw_vals)*100:.1f}%)"
    )

    print("\n" + "=" * 70)
    print("  Exploratory analysis complete. Use findings to tune EDS parameters.")
    print("=" * 70 + "\n")


def main():
    """Run all examples."""
    print("\n" + "#" * 70)
    print("  EDGE LAB EXAMPLES")
    print("  Complete workflow demonstrations with real/demo data")
    print("#" * 70 + "\n")

    # Run examples
    examples = [
        ("Example 1: Basic Edge Discovery", example_1_basic_edge_discovery),
        ("Example 2: Multi-Symbol Screening", example_2_multi_symbol_screening),
        ("Example 3: Session Analysis", example_3_session_analysis),
        ("Example 4: Custom Parameters", example_4_custom_parameters),
        ("Example 5: Null Baseline Comparison", example_5_null_baseline_comparison),
        ("Example 6: Exploratory Analysis", example_6_exploratory_analysis),
    ]

    for name, func in examples:
        try:
            print(f"\nRunning: {name}")
            func()
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            break
        except Exception as e:
            logger.error(f"{name} failed: {e}")

    print("\n" + "#" * 70)
    print("  All examples complete!")
    print("  Check 'backend/data/edge_lab_outputs/' for generated reports")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()


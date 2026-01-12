"""Example demonstrating Plotly conversion functionality.

This script shows how to:
1. Convert existing matplotlib plots to interactive Plotly charts
2. Create native Plotly time series and candlestick charts
3. Save interactive HTML files for web embedding
4. Combine matplotlib and Plotly workflows

Run this file: python examples/backtest/example_plotly_conversion.py

Updated to use real market data.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from apps.plotting import (
    PLOTLY_AVAILABLE,
    convert_and_save,
    create_plotly_candlestick,
    create_plotly_time_series,
    plot_returns,
    save_plotly_html,
    to_plotly,
)
from apps.logger import logger
from apps.utils.data_getters import load_mt5


def get_real_data(symbol="EURUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Get real equity curve and OHLCV data for examples."""
    try:
        ohlcv = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        
        # Simulate equity curve (Buy and Hold)
        returns = ohlcv["close"].pct_change().fillna(0)
        equity = 10000 * (1 + returns).cumprod()
        
        return equity, ohlcv
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.Series(), pd.DataFrame()


def example1_basic_conversion():
    """Demonstrate basic matplotlib to Plotly conversion."""
    logger.info("=" * 60)
    logger.info("Example 1: Basic Matplotlib to Plotly Conversion")
    logger.info("=" * 60)

    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not available - skipping Example 1")
        logger.info("Install with: pip install plotly")
        return

    logger.info("Loading EURUSD data...")
    equity, _ = get_real_data("EURUSD")
    if equity.empty: return

    # Create matplotlib plot
    logger.info("Creating matplotlib plot...")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(equity.index, equity.values, label="Equity Curve", linewidth=2)
    ax.set_title("EURUSD Equity Curve - Matplotlib Version")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Convert to Plotly
    logger.info("Converting to Plotly...")
    plotly_fig = to_plotly(fig)

    # Save as HTML
    output_path = "output/plotting/plotly_basic_conversion.html"
    save_plotly_html(plotly_fig, output_path)

    logger.success(f" Saved interactive plot to {output_path}")
    logger.info("  - Hover over lines to see values")
    logger.info("  - Use toolbar to pan, zoom, reset")
    logger.info("  - Double-click legend to isolate series")

    plt.close(fig)


def example2_wrapper_conversion():
    """Convert wrapper function output to Plotly."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Convert Wrapper Function to Plotly")
    logger.info("=" * 60)

    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not available - skipping Example 2")
        return

    logger.info("Loading GBPUSD data...")
    equity, _ = get_real_data("GBPUSD")
    if equity.empty: return

    # Use plotting wrapper to create matplotlib figure
    logger.info("Creating returns plot with wrapper...")
    fig = plot_returns(
        equity,
        figsize=(12, 6),
        title="GBPUSD Cumulative Returns",
        show=False,  # Don't display matplotlib version
    )

    # Convert to Plotly and save
    logger.info("Converting to interactive Plotly version...")
    output_path = "output/plotting/plotly_returns_conversion.html"
    convert_and_save(
        fig,
        output_path,
        add_rangeslider=True,  # Add interactive range slider
    )

    logger.success(f" Saved interactive returns plot to {output_path}")
    logger.info("  - Range slider at bottom for zooming to specific periods")
    logger.info("  - Hover to see exact return values")

    plt.close(fig)


def example3_native_time_series():
    """Create native Plotly time series."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Native Plotly Time Series")
    logger.info("=" * 60)

    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not available - skipping Example 3")
        return

    logger.info("Loading USDJPY data...")
    equity, _ = get_real_data("USDJPY")
    if equity.empty: return

    # Create DataFrame with multiple series
    returns = equity.pct_change().fillna(0)
    cumulative_returns = (1 + returns).cumprod() - 1

    df = pd.DataFrame(
        {
            "equity": equity,
            "cumulative_returns": cumulative_returns * 100,  # As percentage
        }
    )

    # Create native Plotly time series
    logger.info("Creating native Plotly time series...")
    plotly_fig = create_plotly_time_series(
        df,
        y_columns=["cumulative_returns"],
        title="USDJPY Cumulative Returns (%)",
        rangeslider=True,
    )

    # Customize layout
    plotly_fig.update_layout(
        yaxis_title="Returns (%)",
        xaxis_title="Date",
        hovermode="x unified",  # Unified hover for all series
        height=600,
    )

    # Add horizontal line at 0%
    plotly_fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Save
    output_path = "output/plotting/plotly_native_timeseries.html"
    save_plotly_html(plotly_fig, output_path)

    logger.success(f" Saved native Plotly time series to {output_path}")
    logger.info("  - Created directly with Plotly (no matplotlib conversion)")
    logger.info("  - Fully customizable with Plotly API")


def example4_candlestick_chart():
    """Create interactive candlestick chart."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Interactive Candlestick Chart")
    logger.info("=" * 60)

    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not available - skipping Example 4")
        return

    logger.info("Loading AUDUSD data...")
    _, ohlcv = get_real_data("AUDUSD")
    if ohlcv.empty: return

    # Create candlestick chart with volume
    logger.info("Creating candlestick chart with volume...")
    plotly_fig = create_plotly_candlestick(
        ohlcv,
        title="AUDUSD Price Action with Volume",
        volume_col="volume",
    )

    # Customize layout
    plotly_fig.update_layout(
        height=700,
        showlegend=True,
    )

    # Save
    output_path = "output/plotting/plotly_candlestick.html"
    save_plotly_html(plotly_fig, output_path)

    logger.success(f" Saved candlestick chart to {output_path}")
    logger.info("  - Hover over candles to see OHLC values")
    logger.info("  - Volume bars colored by direction (green/red)")
    logger.info("  - Synchronized x-axis between price and volume")


def example5_multiple_charts():
    """Create multiple charts for comprehensive analysis."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Multiple Interactive Charts")
    logger.info("=" * 60)

    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not available - skipping Example 5")
        return

    logger.info("Loading NZDUSD data...")
    equity, ohlcv = get_real_data("NZDUSD")
    if equity.empty: return

    logger.info("Creating multiple charts...")

    # 1. Equity curve
    equity_fig = create_plotly_time_series(
        pd.DataFrame({"Equity": equity}),
        y_columns="Equity",
        title="NZDUSD Equity Curve",
        rangeslider=False,
    )
    save_plotly_html(equity_fig, "output/plotting/plotly_multi_equity.html")
    logger.success("   Equity curve saved")

    # 2. Drawdown
    running_max = equity.expanding().max()
    drawdown = (equity / running_max - 1) * 100

    dd_fig = create_plotly_time_series(
        pd.DataFrame({"Drawdown (%)": drawdown}),
        y_columns="Drawdown (%)",
        title="NZDUSD Drawdown",
        rangeslider=False,
    )
    dd_fig.update_traces(fill="tozeroy", line_color="red")
    save_plotly_html(dd_fig, "output/plotting/plotly_multi_drawdown.html")
    logger.success("   Drawdown saved")

    # 3. Returns distribution
    returns = equity.pct_change().dropna() * 100

    dist_fig = create_plotly_time_series(
        pd.DataFrame({"Daily Returns (%)": returns}),
        y_columns="Daily Returns (%)",
        title="NZDUSD Daily Returns Distribution",
        rangeslider=False,
    )
    dist_fig.update_traces(mode="markers", marker=dict(size=4, opacity=0.6))
    save_plotly_html(dist_fig, "output/plotting/plotly_multi_returns.html")
    logger.success("   Returns distribution saved")

    logger.success(" Created 3 interactive charts in output/plotting/")
    logger.info("  - Each chart is a standalone HTML file")
    logger.info("  - Can be embedded in web pages or dashboards")


def main():
    """Run all Plotly conversion examples."""
    print("\n" + "=" * 70)
    print(" Plotly Conversion Examples")
    print("=" * 70)

    if not PLOTLY_AVAILABLE:
        logger.error("Plotly is not installed!")
        logger.info("\nTo install Plotly:")
        logger.info("  pip install plotly")
        logger.info("\nPlotly provides:")
        logger.info("  - Interactive charts with zoom, pan, hover")
        logger.info("  - Web-based visualizations (HTML export)")
        logger.info("  - Professional-quality output")
        logger.info("  - No additional JavaScript required (uses CDN)")
        return

    # Create output directory
    output_dir = Path("output/plotting")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"\nOutput directory: {output_dir.absolute()}\n")

    # Run examples
    try:
        example1_basic_conversion()
        example2_wrapper_conversion()
        example3_native_time_series()
        example4_candlestick_chart()
        example5_multiple_charts()

        print("\n" + "=" * 70)
        logger.success("ALL PLOTLY EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 70)

        logger.info("\nGenerated Files:")
        logger.info("  1. plotly_basic_conversion.html - Basic matplotlib to Plotly")
        logger.info("  2. plotly_returns_conversion.html - Wrapper function conversion")
        logger.info("  3. plotly_native_timeseries.html - Native Plotly time series")
        logger.info("  4. plotly_candlestick.html - Candlestick chart with volume")
        logger.info("  5. plotly_multi_equity.html - Equity curve")
        logger.info("  6. plotly_multi_drawdown.html - Drawdown chart")
        logger.info("  7. plotly_multi_returns.html - Returns scatter")

        logger.info("\nNext Steps:")
        logger.info("  - Open HTML files in browser to interact with charts")
        logger.info("  - Embed in web dashboards or reports")
        logger.info("  - Customize with Plotly API for advanced features")
        logger.info("  - Use to_plotly() to convert any matplotlib figure")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

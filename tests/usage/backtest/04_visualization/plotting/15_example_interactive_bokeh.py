"""Example: Interactive Bokeh Charts for Trading Analysis.

This example demonstrates how to use the interactive plotting features including:
1. Linked crosshairs across multiple charts
2. Pan and zoom tools with synchronization
3. Customized hover tooltips for different chart types
4. Interactive legends with click-to-hide functionality
5. Range selector for time-based navigation
6. Complete multi-chart dashboard

Updated to use real market data from MT5.
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

# Import interactive plotting functions
from apps.plotting.interactive import (
    add_equity_hover,
    add_linked_crosshair,
    add_ohlc_hover,
    add_pan_zoom_tools,
    apply_standard_tools,
    configure_interactive_legend,
    create_range_selector_layout,
)
from apps.utils.data_getters import load_mt5

try:
    from bokeh.io import output_file, show
    from bokeh.layouts import column
    from bokeh.models import ColumnDataSource
    from bokeh.plotting import figure

    BOKEH_AVAILABLE = True
except ImportError:
    BOKEH_AVAILABLE = False
    print("Bokeh not available. Please install: pip install bokeh")
    exit(1)


# =============================================================================
# DATA LOADING & PREPARATION
# =============================================================================


def load_real_data(symbol="EURUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Load real OHLC data."""
    try:
        df = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        # Ensure 'date' column exists for Bokeh (reset index if it's DatetimeIndex)
        if "date" not in df.columns:
            df = df.reset_index()
            # Handle various index names
            for col in ["index", "time", "datetime", "timestamp", "Date"]:
                if col in df.columns:
                    df = df.rename(columns={col: "date"})
                    break
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        # Fallback to empty DF or raise
        raise


def generate_indicators(df):
    """Add technical indicators to dataframe."""
    # Simple moving averages
    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    return df


def generate_equity_curve(df):
    """Generate sample equity curve based on simple strategy."""
    # Simple strategy: buy when close > SMA20
    df["signal"] = (df["close"] > df["sma_20"]).astype(int)
    df["returns"] = df["close"].pct_change() * df["signal"].shift(1)
    df["equity"] = 10000 * (1 + df["returns"].fillna(0)).cumprod()
    df["drawdown"] = df["equity"] / df["equity"].expanding().max() - 1

    return df


# =============================================================================
# EXAMPLE 1: BASIC INTERACTIVE CHART
# =============================================================================


def example_1_basic_interactive():
    """Example 1: Basic interactive chart with standard tools."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Interactive Chart")
    print("=" * 70)

    # Load data
    print("Loading EURUSD data...")
    try:
        df = load_real_data("EURUSD", start_date="2023-01-01", end_date="2023-06-01")
    except Exception:
        return

    # Create data source
    source = ColumnDataSource(df)

    # Create figure
    fig = figure(
        title="EURUSD Interactive Price Chart",
        x_axis_type="datetime",
        width=1200,
        height=600,
    )

    # Plot data
    fig.line("date", "close", source=source, line_width=2, color="#3498db")

    # Apply standard interactive tools
    apply_standard_tools(
        fig,
        enable_crosshair=True,
        enable_hover=True,
        hover_type="equity", # Shows date and value (close)
        enable_pan_zoom=True,
    )

    # Save and show
    output_file("output/plotting/example_1_basic_interactive.html")
    
    # Configure legend (must be done after plotting)
    if fig.legend:
        fig.legend.location = "top_left"
        
    show(fig)

    print(" Chart saved to: output/plotting/example_1_basic_interactive.html")
    print("Features:")
    print("  - Pan: Click and drag to move chart")
    print("  - Zoom: Mouse wheel to zoom in/out")
    print("  - Box Zoom: Select area to zoom")
    print("  - Hover: Move mouse over data to see values")
    print("  - Reset: Click reset button to restore original view")


# =============================================================================
# EXAMPLE 2: OHLC CANDLESTICK CHART
# =============================================================================


def example_2_ohlc_candlestick():
    """Create OHLC candlestick chart with custom hover."""
    print("\n" + "=" * 70)
    print("Example 2: OHLC Candlestick Chart")
    print("=" * 70)

    # Load data
    print("Loading GBPUSD data...")
    try:
        data = load_real_data("GBPUSD", start_date="2023-01-01", end_date="2023-04-01")
    except Exception:
        return

    # Create figure
    fig = figure(
        title="GBPUSD OHLC Candlestick Chart",
        x_axis_type="datetime",
        width=1200,
        height=600,
    )

    # Determine up/down candles
    # Note: data is a DataFrame, so we can iterate or use vectorized operations
    # For Bokeh colors list, we need a list of colors matching the dataframe length
    data["color"] = [
        "#2ecc71" if close_val >= open_val else "#e74c3c"
        for close_val, open_val in zip(data["close"], data["open"])
    ]

    # Plot candlesticks
    inc = data["close"] >= data["open"]
    dec = ~inc

    # Up candles
    fig.segment(
        data["date"][inc],
        data["high"][inc],
        data["date"][inc],
        data["low"][inc],
        color="#2ecc71",
    )
    fig.vbar(
        data["date"][inc],
        width=timedelta(hours=16), # Adjust width for daily data
        top=data["close"][inc],
        bottom=data["open"][inc],
        fill_color="#2ecc71",
        line_color="#2ecc71",
    )

    # Down candles
    fig.segment(
        data["date"][dec],
        data["high"][dec],
        data["date"][dec],
        data["low"][dec],
        color="#e74c3c",
    )
    fig.vbar(
        data["date"][dec],
        width=timedelta(hours=16),
        top=data["open"][dec],
        bottom=data["close"][dec],
        fill_color="#e74c3c",
        line_color="#e74c3c",
    )

    # Add OHLC hover tooltip
    add_ohlc_hover(fig)

    # Add pan/zoom tools
    add_pan_zoom_tools(fig)

    # Save and show
    output_file("output/plotting/example_2_ohlc_candlestick.html")
    show(fig)

    print(" Chart saved to: output/plotting/example_2_ohlc_candlestick.html")
    print("Features:")
    print("  - Hover shows OHLC values and volume")
    print("  - Green candles = price up, Red candles = price down")


# =============================================================================
# EXAMPLE 3: MULTI-CHART DASHBOARD WITH LINKED AXES
# =============================================================================


def example_3_linked_dashboard():
    """Example 3: Multi-chart dashboard with linked axes and crosshair."""
    print("\n" + "=" * 70)
    print("Example 3: Linked Multi-Chart Dashboard")
    print("=" * 70)

    # Generate data
    print("Loading USDJPY data...")
    try:
        df = load_real_data("USDJPY", start_date="2023-01-01", end_date="2023-12-31")
    except Exception:
        return

    df = generate_indicators(df)
    df = generate_equity_curve(df)

    # Create data source
    source = ColumnDataSource(df)

    # Create price chart
    price_fig = figure(
        title="USDJPY Price with Moving Averages",
        x_axis_type="datetime",
        width=1200,
        height=400,
        x_range=(df["date"].iloc[0], df["date"].iloc[-1]),
    )
    price_fig.line(
        "date", "close", source=source, legend_label="Close", color="#3498db"
    )
    price_fig.line(
        "date", "sma_20", source=source, legend_label="SMA 20", color="#e67e22"
    )
    price_fig.line(
        "date", "sma_50", source=source, legend_label="SMA 50", color="#9b59b6"
    )

    # Create volume chart
    volume_fig = figure(
        title="Volume",
        x_axis_type="datetime",
        width=1200,
        height=200,
        x_range=price_fig.x_range,  # Link to price chart
    )
    volume_fig.vbar("date", top="volume", source=source, width=timedelta(days=0.8))

    # Create equity chart
    equity_fig = figure(
        title="Equity Curve (Simulated)",
        x_axis_type="datetime",
        width=1200,
        height=300,
        x_range=price_fig.x_range,  # Link to price chart
    )
    equity_fig.line("date", "equity", source=source, color="#2ecc71", line_width=2)

    # Create RSI chart
    rsi_fig = figure(
        title="RSI",
        x_axis_type="datetime",
        width=1200,
        height=200,
        x_range=price_fig.x_range,  # Link to price chart
    )
    rsi_fig.line("date", "rsi", source=source, color="#e74c3c")
    rsi_fig.line(df["date"], [70] * len(df), color="red", line_dash="dashed", alpha=0.5)
    rsi_fig.line(
        df["date"], [30] * len(df), color="green", line_dash="dashed", alpha=0.5
    )

    # Apply tools to all figures
    figures = [price_fig, volume_fig, equity_fig, rsi_fig]

    for fig in figures:
        add_pan_zoom_tools(fig)
        configure_interactive_legend(fig, click_policy="hide")

    # Add linked crosshair
    add_linked_crosshair(figures, dimensions="both")

    # Add hover tooltips
    add_equity_hover(price_fig)
    add_equity_hover(volume_fig)
    add_equity_hover(equity_fig)
    add_equity_hover(rsi_fig)

    # Create layout
    layout = column(price_fig, volume_fig, equity_fig, rsi_fig)

    # Save and show
    output_file("output/plotting/example_3_linked_dashboard.html")
    show(layout)

    print(" Chart saved to: output/plotting/example_3_linked_dashboard.html")
    print("Features:")
    print("  - All charts share synchronized x-axis zoom")
    print("  - Crosshair appears across all charts simultaneously")
    print("  - Click legend items to hide/show series")
    print("  - Pan/zoom on any chart affects all charts")


# =============================================================================
# EXAMPLE 4: RANGE SELECTOR
# =============================================================================


def example_4_range_selector():
    """Example 4: Chart with range selector."""
    print("\n" + "=" * 70)
    print("Example 4: Chart with Range Selector")
    print("=" * 70)

    # Generate data
    print("Loading EURUSD data (2 years)...")
    try:
        df = load_real_data("EURUSD", start_date="2022-01-01", end_date="2023-12-31")
    except Exception:
        return
        
    df = generate_indicators(df)
    df = generate_equity_curve(df)

    # Create data source
    source = ColumnDataSource(df)

    # Create main chart
    main_fig = figure(
        title="EURUSD Equity Curve with Range Selector",
        x_axis_type="datetime",
        width=1200,
        height=600,
    )
    main_fig.line("date", "equity", source=source, color="#2ecc71", line_width=2)

    # Add standard tools
    add_pan_zoom_tools(main_fig)
    add_equity_hover(main_fig)

    # Create layout with range selector
    layout = create_range_selector_layout(
        main_fig, source, selector_height=100, y_column="equity"
    )

    # Save and show
    output_file("output/plotting/example_4_range_selector.html")
    show(layout)

    print(" Chart saved to: output/plotting/example_4_range_selector.html")
    print("Features:")
    print("  - Drag the selection box in the bottom chart to change date range")
    print("  - Main chart updates automatically")
    print("  - Perfect for exploring long time series")


# =============================================================================
# EXAMPLE 5: COMPLETE TRADING DASHBOARD
# =============================================================================


def example_5_complete_dashboard():
    """Example 5: Complete trading dashboard with all features."""
    print("\n" + "=" * 70)
    print("Example 5: Complete Trading Dashboard")
    print("=" * 70)

    # Generate data
    print("Loading AUDUSD data...")
    try:
        df = load_real_data("AUDUSD", start_date="2022-01-01", end_date="2023-12-31")
    except Exception:
        return
        
    df = generate_indicators(df)
    df = generate_equity_curve(df)

    # Create data source
    source = ColumnDataSource(df)

    # 1. Price chart with candlesticks
    price_fig = figure(
        title="AUDUSD Price Chart",
        x_axis_type="datetime",
        width=900,
        height=400,
    )
    price_fig.line(
        "date", "close", source=source, legend_label="Close", color="#3498db"
    )
    price_fig.line(
        "date",
        "sma_20",
        source=source,
        legend_label="SMA 20",
        color="#e67e22",
        alpha=0.7,
    )
    price_fig.line(
        "date",
        "sma_50",
        source=source,
        legend_label="SMA 50",
        color="#9b59b6",
        alpha=0.7,
    )

    # 2. Equity chart
    equity_fig = figure(
        title="Equity Curve",
        x_axis_type="datetime",
        width=900,
        height=300,
        x_range=price_fig.x_range,
    )
    equity_fig.line("date", "equity", source=source, color="#2ecc71", line_width=2)

    # 3. Drawdown chart
    dd_fig = figure(
        title="Drawdown",
        x_axis_type="datetime",
        width=900,
        height=200,
        x_range=price_fig.x_range,
    )
    dd_fig.varea("date", 0, "drawdown", source=source, color="#e74c3c", alpha=0.3)

    # Apply standard tools and configure
    charts = [price_fig, equity_fig, dd_fig]
    for fig in charts:
        add_pan_zoom_tools(fig)
        configure_interactive_legend(fig, click_policy="hide")

    # Add linked crosshair
    add_linked_crosshair(charts)

    # Add specific hover tooltips
    add_equity_hover(price_fig)
    add_equity_hover(equity_fig)
    from apps.plotting.interactive import add_drawdown_hover

    add_drawdown_hover(dd_fig, show_duration=True)

    # Create layout
    main_layout = column(price_fig, equity_fig, dd_fig)

    # Add range selector to price chart
    final_layout = create_range_selector_layout(
        main_layout, source, selector_height=80, y_column="close"
    )

    # Save and show
    output_file("output/plotting/example_5_complete_dashboard.html")
    show(final_layout)

    print(" Chart saved to: output/plotting/example_5_complete_dashboard.html")
    print("Features:")
    print("  - Complete trading dashboard with price, equity, and drawdown")
    print("  - Synchronized zoom and crosshair across all charts")
    print("  - Interactive legend (click to hide/show)")
    print("  - Range selector for quick navigation")
    print("  - Custom hover tooltips for each chart type")


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("INTERACTIVE BOKEH PLOTTING EXAMPLES")
    print("=" * 70)

    # Create output directory
    import os

    os.makedirs("output/plotting", exist_ok=True)

    # Run examples
    try:
        example_1_basic_interactive()
        example_2_ohlc_candlestick()
        example_3_linked_dashboard()
        example_4_range_selector()
        example_5_complete_dashboard()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        print("\nGenerated files:")
        print("  - output/plotting/example_1_basic_interactive.html")
        print("  - output/plotting/example_2_ohlc_candlestick.html")
        print("  - output/plotting/example_3_linked_dashboard.html")
        print("  - output/plotting/example_4_range_selector.html")
        print("  - output/plotting/example_5_complete_dashboard.html")
        print("\nOpen these files in a web browser to interact with the charts!")

    except Exception as e:
        print(f"\n Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

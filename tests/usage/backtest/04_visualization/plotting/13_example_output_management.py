"""Example demonstrating output and export management features.

This script demonstrates:
1. File saving in multiple formats (PNG, PDF, SVG, HTML)
2. Filename sanitization and standardized naming
3. Browser integration for HTML files
4. Jupyter environment detection
5. Return object management for customization
6. Batch export to multiple formats

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

from apps.plotting.output import (  # noqa: E402
    configure_jupyter_display,
    generate_filename,
    get_output_config,
    handle_plot_output,
    is_jupyter_environment,
    open_in_browser,
    print_output_config,
    sanitize_filename,
    save_figure,
    save_multiple_formats,
    should_return_figure,
)
from apps.logger import logger  # noqa: E402
from apps.utils.data_getters import load_mt5

# Create output directory
OUTPUT_DIR = project_root / "output" / "plotting" / "output_management"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_real_data(symbol="EURUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Load real data for examples."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def example_1_basic_save():
    """Demonstrate basic file saving in different formats."""
    print("\n" + "=" * 80)
    print("Example 1: Basic File Saving")
    print("=" * 80)

    # Create a simple plot
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)

    ax.plot(x, y1, label="sin(x)", linewidth=2)
    ax.plot(x, y2, label="cos(x)", linewidth=2)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Trigonometric Functions")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Save in different formats
    print("\n1. Saving as PNG (high resolution)...")
    save_figure(fig, OUTPUT_DIR / "example_1_trig.png", dpi=300)

    print("\n2. Saving as PDF (vector format)...")
    save_figure(fig, OUTPUT_DIR / "example_1_trig.pdf")

    print("\n3. Saving as SVG (web-friendly vector)...")
    save_figure(fig, OUTPUT_DIR / "example_1_trig.svg")

    print("\n4. Saving with auto-detected format from extension...")
    save_figure(fig, OUTPUT_DIR / "example_1_trig_auto.jpg", dpi=150)

    plt.close(fig)
    print("\n All formats saved successfully!")


def example_2_filename_generation():
    """Demonstrate filename sanitization and generation."""
    print("\n" + "=" * 80)
    print("Example 2: Filename Sanitization and Generation")
    print("=" * 80)

    # Test filename sanitization
    print("\nFilename Sanitization Examples:")
    print("-" * 50)

    test_names = [
        "My Strategy: Test #1",
        "BTCUSDT/EURUSD",
        "Strategy with <invalid> chars",
        'File with "quotes" and |pipes|',
        "  Leading and trailing spaces  ",
        "Multiple___underscores___test",
    ]

    for name in test_names:
        sanitized = sanitize_filename(name)
        print(f"  '{name}' -> '{sanitized}'")

    # Test filename generation
    print("\n\nFilename Generation Examples:")
    print("-" * 50)

    strategy_names = [
        "MA Crossover",
        "MACD Strategy",
        "RSI Mean Reversion",
    ]
    metrics = ["equity", "drawdown", "returns"]

    for strategy in strategy_names:
        for metric in metrics:
            # Without timestamp
            filename = generate_filename(strategy, metric, add_timestamp=False)
            print(f"  {strategy} + {metric}: {filename}")

            # With timestamp
            filename_ts = generate_filename(strategy, metric, add_timestamp=True)
            print(f"    (with timestamp): {filename_ts}")

    print("\n Filename operations demonstrated!")


def example_3_multiple_formats():
    """Save figure in multiple formats at once."""
    print("\n" + "=" * 80)
    print("Example 3: Batch Export to Multiple Formats")
    print("=" * 80)

    # Load real data
    print("Loading EURUSD data...")
    data = get_real_data("EURUSD")
    if data.empty: return
    
    # Simulate equity curve
    returns = data["close"].pct_change().fillna(0)
    equity = 10000 * (1 + returns).cumprod()
    dates = equity.index

    # Create equity curve plot
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(dates, equity, linewidth=2, color="#2ecc71")
    ax.fill_between(dates, 10000, equity, alpha=0.2, color="#2ecc71")
    ax.axhline(10000, color="gray", linestyle="--", alpha=0.5, label="Initial Capital")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity ($)")
    ax.set_title("EURUSD Equity Curve - Multi-Format Export")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Format y-axis as currency
    from matplotlib.ticker import FuncFormatter

    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))

    # Save in multiple formats
    print("\nExporting to multiple formats...")
    base_path = OUTPUT_DIR / "example_3_equity"
    formats = ["png", "pdf", "svg"]

    paths = save_multiple_formats(fig, base_path, formats, dpi=300)

    print("\nSaved files:")
    for fmt, path in paths.items():
        print(f"  {fmt.upper()}: {path}")

    plt.close(fig)
    print("\n Multi-format export completed!")


def example_4_return_objects():
    """Return objects for further customization."""
    print("\n" + "=" * 80)
    print("Example 4: Return Objects for Customization")
    print("=" * 80)

    # Create initial plot
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.linspace(0, 2 * np.pi, 100)
    y = np.sin(x)

    ax.plot(x, y, linewidth=2)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Initial Plot")
    ax.grid(True, alpha=0.3)

    # Test should_return_figure logic
    print("\nshould_return_figure() Examples:")
    print("-" * 50)

    test_cases = [
        (True, True, False, "Showing and saving"),
        (True, False, False, "Only showing"),
        (False, True, False, "Only saving"),
        (False, False, False, "Neither showing nor saving"),
        (True, True, True, "Explicit return request"),
    ]

    for show, save, return_fig, description in test_cases:
        result = should_return_figure(show, save, return_fig)
        print(f"  {description}: return={result}")

    # Use handle_plot_output to get figure back
    print("\n\nGetting figure for customization...")
    returned_fig = handle_plot_output(fig, show=False, save=False, return_fig=True)

    if returned_fig is not None:
        print(" Figure returned successfully!")

        # Customize further
        print("\nCustomizing returned figure...")
        ax = returned_fig.axes[0]
        ax.plot(x, np.cos(x), linewidth=2, label="cos(x)", linestyle="--")
        ax.set_title("Customized Plot (added cosine)")
        ax.legend()

        # Now save the customized version
        save_figure(returned_fig, OUTPUT_DIR / "example_4_customized.png", dpi=300)
        print(" Saved customized figure!")

    plt.close(fig)


def example_5_handle_plot_output():
    """Demonstrate comprehensive plot output handling."""
    print("\n" + "=" * 80)
    print("Example 5: Comprehensive Plot Output Handling")
    print("=" * 80)

    # Load real data
    print("Loading GBPUSD data...")
    data = get_real_data("GBPUSD")
    if data.empty: return
    
    returns = data["close"].pct_change().dropna()

    # Create returns distribution plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Histogram
    axes[0].hist(returns, bins=50, alpha=0.7, color="#3498db", edgecolor="black")
    axes[0].axvline(0, color="red", linestyle="--", linewidth=2, label="Zero")
    axes[0].set_xlabel("Returns")
    axes[0].set_ylabel("Frequency")
    axes[0].set_title("GBPUSD Returns Distribution")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Q-Q plot
    from scipy import stats

    stats.probplot(returns, dist="norm", plot=axes[1])
    axes[1].set_title("Q-Q Plot (Normal)")
    axes[1].grid(True, alpha=0.3)

    fig.suptitle("GBPUSD Returns Analysis", fontsize=14, fontweight="bold")

    # Use handle_plot_output for complete control
    print("\n1. Save only (no display, no return)...")
    handle_plot_output(
        fig,
        show=False,
        save=True,
        filepath=OUTPUT_DIR / "example_5_returns_save.png",
        return_fig=False,
        dpi=300,
    )

    print("\n2. Save and get figure back for further use...")
    returned = handle_plot_output(
        fig,
        show=False,
        save=True,
        filepath=OUTPUT_DIR / "example_5_returns_both.pdf",
        return_fig=True,
    )

    if returned is not None:
        print("    Figure returned after saving!")

    # Don't show in example (would block execution)
    # handle_plot_output(fig, show=True, save=False)

    plt.close(fig)
    print("\n Plot output handling demonstrated!")


def example_6_jupyter_detection():
    """Demonstrate Jupyter environment detection and configuration."""
    print("\n" + "=" * 80)
    print("Example 6: Jupyter Environment Detection")
    print("=" * 80)

    # Check environment
    is_jupyter = is_jupyter_environment()
    print(f"\nRunning in Jupyter: {is_jupyter}")

    if is_jupyter:
        print("\nJupyter environment detected!")
        print("Configuring matplotlib for inline display...")
        configure_jupyter_display("matplotlib")

        print("\nConfiguring Bokeh for notebook output...")
        configure_jupyter_display("bokeh")
    else:
        print("\nNot in Jupyter environment (running as script)")
        print("No special configuration needed")

    # Print current configuration
    print("\n")
    print_output_config()

    # Get config as dict
    config = get_output_config()
    print("\nConfiguration dictionary:")
    for key, value in config.items():
        print(f"  {key}: {value}")


def example_7_standardized_naming():
    """Demonstrate standardized naming for strategy outputs."""
    print("\n" + "=" * 80)
    print("Example 7: Standardized Naming Convention")
    print("=" * 80)
    
    # Load real data
    print("Loading USDJPY data...")
    data = get_real_data("USDJPY")
    if data.empty: return
    
    returns = data["close"].pct_change().fillna(0)
    equity = 10000 * (1 + returns).cumprod()
    drawdown = (equity / equity.cummax()) - 1

    # Create sample plots for a strategy
    strategy_name = "USDJPY Strategy"
    metrics = ["equity", "drawdown", "returns", "trades"]

    print(f"\nGenerating outputs for: {strategy_name}")
    print("-" * 50)

    for metric in metrics:
        # Create a simple plot for each metric
        fig, ax = plt.subplots(figsize=(10, 6))

        if metric == "equity":
            ax.plot(equity.index, equity, linewidth=2)
            ax.set_title(f"{strategy_name} - Equity Curve")

        elif metric == "drawdown":
            ax.fill_between(drawdown.index, 0, drawdown, alpha=0.5, color="red")
            ax.set_title(f"{strategy_name} - Drawdown")

        elif metric == "returns":
            ax.hist(returns, bins=30, alpha=0.7, edgecolor="black")
            ax.set_title(f"{strategy_name} - Returns Distribution")

        elif metric == "trades":
            categories = ["Wins", "Losses", "Breakeven"]
            values = [45, 30, 5]
            ax.bar(categories, values)
            ax.set_title(f"{strategy_name} - Trade Outcomes")

        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True, alpha=0.3)

        # Generate standardized filename
        filename = generate_filename(strategy_name, metric, add_timestamp=False)
        filepath = OUTPUT_DIR / filename

        # Save
        save_figure(fig, filepath, dpi=150)
        print(f"  {metric:12s} -> {filename}")

        plt.close(fig)

    print("\n All strategy outputs saved with standardized naming!")


def example_8_browser_integration():
    """Demonstrate browser integration (HTML only)."""
    print("\n" + "=" * 80)
    print("Example 8: Browser Integration")
    print("=" * 80)

    # This example requires Plotly for HTML output
    try:
        from apps.plotting.plotly_convert import to_plotly
        
        # Load real data
        print("Loading AUDUSD data...")
        data = get_real_data("AUDUSD")
        if data.empty: return

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(data.index, data["close"], linewidth=2, label="Price")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.set_title("AUDUSD Interactive Price Chart")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Convert to Plotly for interactivity
        print("\nConverting matplotlib to Plotly...")
        plotly_fig = to_plotly(fig)

        # Save as HTML
        html_path = OUTPUT_DIR / "example_8_interactive.html"
        print(f"\nSaving to {html_path}...")

        # Use plotly's write_html
        plotly_fig.write_html(str(html_path))
        logger.success(f"Saved interactive chart to {html_path}")

        # Open in browser (comment out if running in automation)
        print("\nOpening in browser...")
        print("(Set AUTO_OPEN=True in code to enable)")
        AUTO_OPEN = False  # Set to True to auto-open browser

        if AUTO_OPEN:
            success = open_in_browser(html_path)
            if success:
                print(" Opened in browser!")
        else:
            print(f"Skipped auto-open. Open manually: {html_path}")

        plt.close(fig)
        print("\n Browser integration demonstrated!")

    except ImportError as e:
        print(f"\n Skipping: Plotly not available ({e})")


def main():
    """Run all examples."""
    print("=" * 80)
    print("OUTPUT & EXPORT MANAGEMENT EXAMPLES")
    print("=" * 80)
    print(f"\nOutput directory: {OUTPUT_DIR}")

    # Run examples
    try:
        example_1_basic_save()
        example_2_filename_generation()
        example_3_multiple_formats()
        example_4_return_objects()
        example_5_handle_plot_output()
        example_6_jupyter_detection()
        example_7_standardized_naming()
        example_8_browser_integration()

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\n All examples completed successfully!")
        print(f" Output files saved to: {OUTPUT_DIR}")
        print("\nGenerated files:")

        # List all files
        files = sorted(OUTPUT_DIR.glob("example_*"))
        for file in files:
            size = file.stat().st_size / 1024  # KB
            print(f"  {file.name:50s} ({size:6.1f} KB)")

        print(f"\nTotal files: {len(files)}")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

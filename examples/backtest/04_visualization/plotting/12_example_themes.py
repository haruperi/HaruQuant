"""Example demonstrating theme and styling features.

This script demonstrates:
1. Using built-in themes (light, dark, grayscale, print)
2. Applying themes globally and per-plot
3. Creating custom themes
4. Theme context managers
5. Custom styling (fonts, colors)
6. Watermarks and logos
7. Theme persistence

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

from apps.plotting.themes import (  # noqa: E402
    THEMES,
    ThemeContext,
    add_watermark,
    apply_theme_to_figure,
    create_custom_theme,
    get_current_theme,
    get_line_colors,
    get_theme_colors,
    list_themes,
    load_theme_preference,
    reset_theme,
    save_theme_preference,
    set_color_palette,
    set_custom_font,
    set_theme,
)
from apps.utils.logger import logger  # noqa: E402
from apps.utils.data_getters import load_mt5

# Create output directory
OUTPUT_DIR = project_root / "output" / "plotting" / "themes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_real_data(symbol="EURUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Get real data for examples."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        returns = data["close"].pct_change().fillna(0)
        equity = 10000 * (1 + returns).cumprod()
        return equity, returns
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        # Fallback
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        return pd.Series(10000, index=dates), pd.Series(0, index=dates)


def create_sample_plot(title: str = "Sample Plot"):
    """Create a sample plot for demonstration."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Load real data
    equity, returns = get_real_data("EURUSD")
    
    # Generate some synthetic data for variety
    x = np.linspace(0, 10, 100)
    
    # Plot 1: Line plot (Trig functions)
    ax1 = axes[0, 0]
    ax1.plot(x, np.sin(x), label="sin(x)", linewidth=2)
    ax1.plot(x, np.cos(x), label="cos(x)", linewidth=2)
    ax1.set_xlabel("X")
    ax1.set_ylabel("Y")
    ax1.set_title("Trigonometric Functions")
    ax1.legend()
    ax1.grid(True)

    # Plot 2: Equity curve (Real Data)
    ax2 = axes[0, 1]
    ax2.plot(equity.index, equity, linewidth=2, color="blue")
    ax2.fill_between(equity.index, 10000, equity, alpha=0.3, color="blue")
    ax2.axhline(10000, color="gray", linestyle="--", alpha=0.5)
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Equity ($)")
    ax2.set_title("EURUSD Equity Curve")
    ax2.grid(True)

    # Plot 3: Returns distribution (Real Data)
    ax3 = axes[1, 0]
    ax3.hist(returns, bins=50, alpha=0.7, edgecolor="black")
    ax3.axvline(0, color="red", linestyle="--", linewidth=2)
    ax3.set_xlabel("Returns")
    ax3.set_ylabel("Frequency")
    ax3.set_title("EURUSD Returns Distribution")
    ax3.grid(True, alpha=0.3)

    # Plot 4: Bar chart (Mock Trade Outcomes)
    ax4 = axes[1, 1]
    categories = ["Wins", "Losses", "Breakeven"]
    values = [45, 30, 5]
    colors_theme = get_theme_colors()
    ax4.bar(
        categories,
        values,
        color=[colors_theme["profit"], colors_theme["loss"], colors_theme["neutral"]],
    )
    ax4.set_ylabel("Count")
    ax4.set_title("Trade Outcomes")
    ax4.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    return fig


def example_1_builtin_themes():
    """Demonstrate all built-in themes."""
    print("\n" + "=" * 80)
    print("Example 1: Built-in Themes")
    print("=" * 80)

    # List available themes
    print("\nAvailable themes:")
    themes = list_themes()
    for name, desc in themes.items():
        print(f"  {name:12s} - {desc}")

    # Create plots with each theme
    print("\nCreating plots with each theme...")

    for theme_name in THEMES.keys():
        print(f"\n  Creating plot with '{theme_name}' theme...")

        # Set theme
        set_theme(theme_name)

        # Create plot
        fig = create_sample_plot(f"{theme_name.title()} Theme")

        # Save
        output_path = OUTPUT_DIR / f"example_1_theme_{theme_name}.png"
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.success(f"Saved {theme_name} theme plot")

    print("\n All built-in themes demonstrated!")


def example_2_theme_context():
    """Demonstrate theme context manager."""
    print("\n" + "=" * 80)
    print("Example 2: Theme Context Manager")
    print("=" * 80)

    # Set default theme
    set_theme("light")
    print("\nDefault theme: light")

    # Create plot with default theme
    fig1 = create_sample_plot("Default Theme (Light)")
    fig1.savefig(OUTPUT_DIR / "example_2_default.png", dpi=150, bbox_inches="tight")
    plt.close(fig1)

    # Temporarily use different theme
    print("\nUsing dark theme temporarily...")
    with ThemeContext("dark"):
        fig2 = create_sample_plot("Temporary Theme (Dark)")
        fig2.savefig(
            OUTPUT_DIR / "example_2_temporary.png", dpi=150, bbox_inches="tight"
        )
        plt.close(fig2)

    # Back to default
    print("Back to default theme")
    current = get_current_theme()
    print(f"Current theme: {current['name']}")

    print("\n Theme context demonstrated!")


def example_3_apply_theme_to_existing():
    """Apply theme to existing figure."""
    print("\n" + "=" * 80)
    print("Example 3: Apply Theme to Existing Figure")
    print("=" * 80)

    # Create figure without specific theme
    print("\nCreating figure...")
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.linspace(0, 10, 100)
    ax.plot(x, np.sin(x), label="sin(x)")
    ax.plot(x, np.cos(x), label="cos(x)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Before Theme Application")
    ax.legend()
    ax.grid(True)

    # Save before
    fig.savefig(OUTPUT_DIR / "example_3_before.png", dpi=150, bbox_inches="tight")

    # Apply dark theme
    print("Applying dark theme to existing figure...")
    apply_theme_to_figure(fig, "dark")
    ax.set_title("After Dark Theme Application")

    # Save after
    fig.savefig(OUTPUT_DIR / "example_3_after.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\n Theme application demonstrated!")


def example_4_custom_theme():
    """Create and use custom theme."""
    print("\n" + "=" * 80)
    print("Example 4: Custom Theme Creation")
    print("=" * 80)

    # Create custom theme based on dark
    print("\nCreating custom theme based on dark...")
    custom_theme = create_custom_theme(
        name="cyberpunk",
        base_theme="dark",
        color_overrides={
            "profit": "#00ff9f",  # Neon green
            "loss": "#ff0080",  # Neon pink
            "primary": "#00d4ff",  # Neon cyan
            "accent": "#ffea00",  # Neon yellow
        },
        matplotlib_overrides={
            "grid.alpha": 0.3,
            "grid.linestyle": "--",
            "lines.linewidth": 2.5,
        },
    )

    # Register custom theme
    THEMES["cyberpunk"] = custom_theme
    print(f"Registered custom theme: {custom_theme['name']}")

    # Use custom theme
    set_theme("cyberpunk")

    # Create plot
    fig = create_sample_plot("Custom Cyberpunk Theme")
    fig.savefig(OUTPUT_DIR / "example_4_custom.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\n Custom theme created and used!")


def example_5_custom_colors():
    """Demonstrate custom color palettes."""
    print("\n" + "=" * 80)
    print("Example 5: Custom Color Palettes")
    print("=" * 80)

    set_theme("light")

    # Set custom color palette
    custom_colors = [
        "#e74c3c",  # Red
        "#3498db",  # Blue
        "#2ecc71",  # Green
        "#f39c12",  # Orange
        "#9b59b6",  # Purple
        "#1abc9c",  # Turquoise
    ]

    print("\nSetting custom color palette...")
    set_color_palette(custom_colors)

    # Create plot with multiple lines
    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.linspace(0, 10, 100)
    line_colors = get_line_colors(num_colors=6)

    for i, color in enumerate(line_colors):
        y = np.sin(x + i * 0.5)
        ax.plot(x, y, label=f"Line {i + 1}", linewidth=2, color=color)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Custom Color Palette")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.savefig(OUTPUT_DIR / "example_5_colors.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\n Custom color palette demonstrated!")


def example_6_custom_fonts():
    """Demonstrate custom font settings."""
    print("\n" + "=" * 80)
    print("Example 6: Custom Fonts")
    print("=" * 80)

    set_theme("light")

    # Set custom font
    print("\nSetting custom font...")
    set_custom_font(family="monospace", size=11, weight="bold")

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.linspace(0, 10, 100)
    ax.plot(x, np.sin(x), linewidth=2)
    ax.set_xlabel("X Axis (Custom Font)")
    ax.set_ylabel("Y Axis (Custom Font)")
    ax.set_title("Custom Font Example", fontsize=14)
    ax.grid(True, alpha=0.3)

    fig.savefig(OUTPUT_DIR / "example_6_fonts.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Reset to defaults
    set_custom_font(family="sans-serif", size=10, weight="normal")

    print("\n Custom fonts demonstrated!")


def example_7_watermarks():
    """Demonstrate watermark functionality."""
    print("\n" + "=" * 80)
    print("Example 7: Watermarks")
    print("=" * 80)

    set_theme("light")

    # Create plot
    fig = create_sample_plot("Plot with Watermarks")

    # Add watermarks
    print("\nAdding watermarks...")

    # Center watermark
    add_watermark(
        fig, text="CONFIDENTIAL", position=(0.5, 0.5), alpha=0.08, fontsize=80
    )

    # Corner watermark
    add_watermark(
        fig,
        text="DRAFT",
        position=(0.85, 0.15),
        alpha=0.2,
        fontsize=40,
        rotation=45,
    )

    fig.savefig(OUTPUT_DIR / "example_7_watermark.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\n Watermarks demonstrated!")


def example_8_comparison():
    """Create side-by-side theme comparison."""
    print("\n" + "=" * 80)
    print("Example 8: Theme Comparison")
    print("=" * 80)

    print("\nCreating comparison of all themes...")

    # Only compare built-in themes (not custom)
    builtin_themes = ["light", "dark", "grayscale", "print"]

    # Create figure with subplots for each theme
    fig = plt.figure(figsize=(16, 12))

    # Load real data
    equity, _ = get_real_data("GBPUSD")

    for idx, theme_name in enumerate(builtin_themes, 1):
        # Set theme
        set_theme(theme_name)

        # Create subplot
        ax = fig.add_subplot(2, 2, idx)

        # Plot
        ax.plot(equity.index, equity, linewidth=2)
        ax.fill_between(equity.index, 10000, equity, alpha=0.3)
        ax.axhline(10000, color="gray", linestyle="--", alpha=0.5)
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity ($)")
        ax.set_title(f"{theme_name.title()} Theme")
        ax.grid(True)

        # Apply theme to this specific axis
        theme_config = THEMES[theme_name]
        ax.set_facecolor(theme_config["matplotlib"]["axes.facecolor"])

    fig.suptitle(
        "Theme Comparison (Built-in Themes)", fontsize=18, fontweight="bold", y=0.995
    )
    plt.tight_layout()

    fig.savefig(OUTPUT_DIR / "example_8_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\n Theme comparison created!")


def example_9_persistence():
    """Demonstrate theme persistence."""
    print("\n" + "=" * 80)
    print("Example 9: Theme Persistence")
    print("=" * 80)

    # Save preference
    print("\nSaving 'dark' as default theme...")
    save_theme_preference("dark")

    # Load preference
    print("Loading saved preference...")
    saved = load_theme_preference()
    print(f"Loaded theme preference: {saved}")

    # Apply loaded theme
    if saved:
        set_theme(saved)
        print(f"Applied saved theme: {saved}")

    # Create plot with saved theme
    fig = create_sample_plot("Using Saved Theme Preference")
    fig.savefig(OUTPUT_DIR / "example_9_persistence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Reset to light for other examples
    reset_theme()

    print("\n Theme persistence demonstrated!")


def main():
    """Run all examples."""
    print("=" * 80)
    print("THEME & STYLING EXAMPLES")
    print("=" * 80)
    print(f"\nOutput directory: {OUTPUT_DIR}")

    # Run examples
    try:
        example_1_builtin_themes()
        example_2_theme_context()
        example_3_apply_theme_to_existing()
        example_4_custom_theme()
        example_5_custom_colors()
        example_6_custom_fonts()
        example_7_watermarks()
        example_8_comparison()
        example_9_persistence()

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\n All examples completed successfully!")
        print(f" Output files saved to: {OUTPUT_DIR}")
        print("\nGenerated files:")

        # List all files
        files = sorted(OUTPUT_DIR.glob("example_*.png"))
        for file in files:
            size = file.stat().st_size / 1024  # KB
            print(f"  {file.name:40s} ({size:6.1f} KB)")

        print(f"\nTotal files: {len(files)}")

    except Exception as exc:
        logger.error(f"Example failed: {exc}", exc_info=True)
        raise


if __name__ == "__main__":
    main()


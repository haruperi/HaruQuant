"""Test script for distribution and statistical plotting functions.

This script tests the new distribution plotting functions with various
synthetic and real-world return distributions.

Updated to include real market data tests.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from apps.plotting import (
    _plot_distribution,
    _plot_histogram,
    _plot_qq,
    initialize_plotting,
)
from apps.utils.data_getters import load_mt5

# Initialize plotting
initialize_plotting()

# Create output directory
output_dir = Path("output/plotting/distribution")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Testing Distribution & Statistical Plotting Functions")
print("=" * 80)


def generate_returns(distribution: str, n: int = 1000, **params) -> pd.Series:
    """Generate synthetic returns with specified distribution.

    Args:
        distribution: Type of distribution ('normal', 'skewed', 'heavy_tailed', 'bimodal')
        n: Number of samples
        **params: Distribution parameters

    Returns:
        Returns series
    """
    np.random.seed(42)

    if distribution == "normal":
        # Normal distribution
        mu = params.get("mu", 0.001)
        sigma = params.get("sigma", 0.02)
        returns = np.random.normal(mu, sigma, n)

    elif distribution == "skewed":
        # Skewed distribution (using gamma)
        returns = np.random.gamma(2, 0.01, n) - 0.02

    elif distribution == "heavy_tailed":
        # Heavy-tailed distribution (using t-distribution)
        returns = np.random.standard_t(3, n) * 0.015

    elif distribution == "bimodal":
        # Bimodal distribution
        returns1 = np.random.normal(-0.01, 0.01, n // 2)
        returns2 = np.random.normal(0.015, 0.01, n // 2)
        returns = np.concatenate([returns1, returns2])
        np.random.shuffle(returns)

    else:
        raise ValueError(f"Unknown distribution: {distribution}")

    return pd.Series(returns, name="returns")


def get_real_returns(symbol="EURUSD", start_date="2020-01-01", end_date="2023-12-31"):
    """Get real returns data."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        returns = data["close"].pct_change().dropna()
        return returns
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.Series()


# Test 1: Histogram with Normal Distribution
print("\n1. Testing _plot_histogram() with normal distribution...")
returns_normal = generate_returns("normal", n=1000, mu=0.001, sigma=0.02)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Histogram Tests - Normal Distribution", fontsize=16, fontweight="bold")

# Test different bin methods
_plot_histogram(
    axes[0, 0],
    returns_normal,
    bin_method="auto",
    show_normal=True,
    show_std=True,
    title="Auto Bins (Freedman-Diaconis)",
)

_plot_histogram(
    axes[0, 1],
    returns_normal,
    bin_method="sturges",
    show_normal=True,
    show_std=True,
    title="Sturges' Formula",
)

_plot_histogram(
    axes[1, 0],
    returns_normal,
    bin_method="scott",
    show_normal=True,
    show_std=True,
    title="Scott's Rule",
)

_plot_histogram(
    axes[1, 1],
    returns_normal,
    bins=30,
    show_normal=True,
    show_mean=True,
    show_median=True,
    show_std=True,
    show_stats=True,
    title="Manual Bins (30) - All Features",
)

plt.tight_layout()
output_path = output_dir / "test_histogram_normal.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"    Saved: {output_path}")
plt.close()


# Test 2: Histogram with Different Distributions
print("\n2. Testing _plot_histogram() with various distributions...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Histogram Tests - Various Distributions", fontsize=16, fontweight="bold")

distributions = [
    ("normal", "Normal Distribution"),
    ("skewed", "Skewed Distribution"),
    ("heavy_tailed", "Heavy-Tailed Distribution"),
    ("bimodal", "Bimodal Distribution"),
]

for idx, (dist_type, title) in enumerate(distributions):
    ax = axes[idx // 2, idx % 2]
    returns = generate_returns(dist_type, n=1000)

    _plot_histogram(
        ax,
        returns,
        show_normal=True,
        show_std=True,
        show_stats=True,
        title=title,
    )

plt.tight_layout()
output_path = output_dir / "test_histogram_distributions.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"    Saved: {output_path}")
plt.close()


# Test 3: Q-Q Plots
print("\n3. Testing _plot_qq() with various distributions...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Q-Q Plot Tests - Normality Assessment", fontsize=16, fontweight="bold")

for idx, (dist_type, title) in enumerate(distributions):
    ax = axes[idx // 2, idx % 2]
    returns = generate_returns(dist_type, n=1000)

    _plot_qq(
        ax,
        returns,
        show_fit_line=True,
        show_r2=True,
        highlight_outliers=True,
        title=f"Q-Q Plot: {title}",
    )

plt.tight_layout()
output_path = output_dir / "test_qq_plots.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"    Saved: {output_path}")
plt.close()


# Test 4: Distribution Analysis (KDE + Histogram + Percentiles)
print("\n4. Testing _plot_distribution() with comprehensive features...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Distribution Analysis Tests", fontsize=16, fontweight="bold")

for idx, (dist_type, title) in enumerate(distributions):
    ax = axes[idx // 2, idx % 2]
    returns = generate_returns(dist_type, n=1000)

    _plot_distribution(
        ax,
        returns,
        show_histogram=True,
        show_kde=True,
        show_normal=True,
        show_percentiles=True,
        percentiles=[5, 25, 50, 75, 95],
        show_stats=True,
        show_var=True,
        var_confidence=0.95,
        title=title,
    )

plt.tight_layout()
output_path = output_dir / "test_distribution_analysis.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"    Saved: {output_path}")
plt.close()


# Test 5: Grayscale Mode
print("\n5. Testing grayscale mode...")
returns_normal = generate_returns("normal", n=1000)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Grayscale Mode Tests", fontsize=16, fontweight="bold")

_plot_histogram(
    axes[0],
    returns_normal,
    show_normal=True,
    show_std=True,
    show_stats=True,
    color_mode="grayscale",
    title="Histogram (Grayscale)",
)

_plot_qq(
    axes[1],
    returns_normal,
    show_fit_line=True,
    show_r2=True,
    highlight_outliers=True,
    color_mode="grayscale",
    title="Q-Q Plot (Grayscale)",
)

_plot_distribution(
    axes[2],
    returns_normal,
    show_histogram=True,
    show_kde=True,
    show_normal=True,
    show_percentiles=True,
    show_var=True,
    color_mode="grayscale",
    title="Distribution (Grayscale)",
)

plt.tight_layout()
output_path = output_dir / "test_grayscale_mode.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"    Saved: {output_path}")
plt.close()


# Test 6: Edge Cases
print("\n6. Testing edge cases...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Edge Case Tests", fontsize=16, fontweight="bold")

# All positive returns
returns_positive = pd.Series(np.random.uniform(0.001, 0.05, 500))
_plot_histogram(
    axes[0, 0],
    returns_positive,
    show_normal=True,
    show_stats=True,
    title="All Positive Returns",
)

# All negative returns
returns_negative = pd.Series(np.random.uniform(-0.05, -0.001, 500))
_plot_histogram(
    axes[0, 1],
    returns_negative,
    show_normal=True,
    show_stats=True,
    title="All Negative Returns",
)

# Very small sample
returns_small = pd.Series(np.random.normal(0.001, 0.02, 50))
_plot_qq(
    axes[1, 0],
    returns_small,
    show_fit_line=True,
    show_r2=True,
    title="Small Sample (n=50)",
)

# Large sample
returns_large = pd.Series(np.random.normal(0.001, 0.02, 10000))
_plot_distribution(
    axes[1, 1],
    returns_large,
    show_histogram=True,
    show_kde=True,
    show_percentiles=True,
    title="Large Sample (n=10,000)",
)

plt.tight_layout()
output_path = output_dir / "test_edge_cases.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"    Saved: {output_path}")
plt.close()


# Test 7: Comprehensive Single Plot
print("\n7. Creating comprehensive distribution analysis plot...")
returns_test = generate_returns("heavy_tailed", n=2000)

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

ax1 = fig.add_subplot(gs[0, :])
ax2 = fig.add_subplot(gs[1, 0])
ax3 = fig.add_subplot(gs[1, 1])

fig.suptitle(
    "Comprehensive Distribution Analysis - Heavy-Tailed Returns",
    fontsize=16,
    fontweight="bold",
)

_plot_distribution(
    ax1,
    returns_test,
    show_histogram=True,
    show_kde=True,
    show_normal=True,
    show_percentiles=True,
    percentiles=[1, 5, 25, 50, 75, 95, 99],
    show_stats=True,
    show_var=True,
    var_confidence=0.95,
    title="Distribution with KDE, Histogram, and Percentiles",
)

_plot_histogram(
    ax2,
    returns_test,
    show_normal=True,
    show_mean=True,
    show_median=True,
    show_std=True,
    show_stats=True,
    title="Detailed Histogram",
)

_plot_qq(
    ax3,
    returns_test,
    show_fit_line=True,
    show_r2=True,
    highlight_outliers=True,
    outlier_threshold=2.0,
    title="Q-Q Plot for Normality Check",
)

output_path = output_dir / "test_comprehensive_analysis.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"    Saved: {output_path}")
plt.close()


# Test 8: Real Market Data
print("\n8. Testing with Real Market Data (EURUSD)...")
returns_real = get_real_returns("EURUSD")

if not returns_real.empty:
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, :])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    fig.suptitle(
        "Real Market Data Analysis - EURUSD Daily Returns",
        fontsize=16,
        fontweight="bold",
    )

    _plot_distribution(
        ax1,
        returns_real,
        show_histogram=True,
        show_kde=True,
        show_normal=True,
        show_percentiles=True,
        show_stats=True,
        show_var=True,
        title="EURUSD Return Distribution",
    )

    _plot_histogram(
        ax2,
        returns_real,
        show_normal=True,
        show_stats=True,
        title="EURUSD Histogram",
    )

    _plot_qq(
        ax3,
        returns_real,
        show_fit_line=True,
        show_r2=True,
        highlight_outliers=True,
        title="EURUSD Q-Q Plot",
    )

    output_path = output_dir / "test_real_data_eurusd.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"    Saved: {output_path}")
    plt.close()
else:
    print("   [SKIPPED] Could not load EURUSD data")


# Summary
print("\n" + "=" * 80)
print("Test Summary")
print("=" * 80)
print(" All tests completed successfully!")
print(f" Output directory: {output_dir.absolute()}")
print(f" Generated {len(list(output_dir.glob('*.png')))} test plots")
print("\nGenerated files:")
for file in sorted(output_dir.glob("*.png")):
    print(f"  - {file.name}")
print("=" * 80)

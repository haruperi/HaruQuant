"""Example demonstrating Greek calculations (alpha, beta, R-squared).

This example shows how to calculate and analyze Greek metrics that measure
a strategy's relationship with a benchmark (market).

Greeks include:
- Beta: Systematic risk (how much strategy moves with market)
- Alpha: Excess return beyond what's expected from market exposure
- R-squared: How much variance is explained by the market

Task 7.6.1: Greek Calculations
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from apps.finance import benchmark  # noqa: E402
from apps.logger import logger  # noqa: E402

try:  # Optional dependency
    import matplotlib.pyplot as plt  # noqa: E402
except Exception:  # pragma: no cover - optional
    plt = None


def greeks(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """Calculate alpha, beta, and R-squared."""
    return {
        "alpha": benchmark.alpha(strategy_returns, benchmark_returns, risk_free_rate),
        "beta": benchmark.beta(strategy_returns, benchmark_returns),
        "r_squared": benchmark.r_squared(strategy_returns, benchmark_returns),
    }


def rolling_greeks(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    window: int,
    risk_free_rate: float = 0.0,
) -> pd.DataFrame:
    """Compute rolling alpha, beta, and R-squared."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if aligned.empty:
        return pd.DataFrame(columns=["alpha", "beta", "r_squared"])

    alpha_vals = []
    beta_vals = []
    r2_vals = []
    idx = []

    for i in range(window - 1, len(aligned)):
        slice_data = aligned.iloc[i - window + 1 : i + 1]
        alpha_vals.append(
            benchmark.alpha(
                slice_data["strategy"],
                slice_data["benchmark"],
                risk_free_rate=risk_free_rate,
            )
        )
        beta_vals.append(
            benchmark.beta(slice_data["strategy"], slice_data["benchmark"])
        )
        r2_vals.append(
            benchmark.r_squared(slice_data["strategy"], slice_data["benchmark"])
        )
        idx.append(slice_data.index[-1])

    return pd.DataFrame(
        {"alpha": alpha_vals, "beta": beta_vals, "r_squared": r2_vals}, index=idx
    )


def main() -> None:
    """Demonstrate Greek calculations with synthetic strategy and market data."""
    logger.info("=" * 60)
    logger.info("Greek Calculations Example")
    logger.info("=" * 60)

    logger.info("\n1. Generating synthetic market and strategy data...")

    np.random.seed(42)
    n_days = 252
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")

    daily_mean = 0.10 / 252
    daily_vol = 0.15 / np.sqrt(252)
    market_returns = pd.Series(
        np.random.randn(n_days) * daily_vol + daily_mean,
        index=dates,
        name="Market Returns",
    )

    logger.info("Creating three strategies with different characteristics:")

    logger.info("  - Strategy 1: High Beta (1.5), Positive Alpha")
    strategy1_returns = pd.Series(
        market_returns * 1.5
        + np.random.randn(n_days) * 0.08 / np.sqrt(252)
        + 0.05 / 252,
        index=dates,
        name="Strategy 1",
    )

    logger.info("  - Strategy 2: Low Beta (0.2), High Alpha (market-neutral)")
    strategy2_returns = pd.Series(
        market_returns * 0.2
        + np.random.randn(n_days) * 0.05 / np.sqrt(252)
        + 0.08 / 252,
        index=dates,
        name="Strategy 2",
    )

    logger.info("  - Strategy 3: Beta (1.0), Zero Alpha (index tracker)")
    strategy3_returns = pd.Series(
        market_returns
        + np.random.randn(n_days) * 0.02 / np.sqrt(252),
        index=dates,
        name="Strategy 3",
    )

    logger.info("\n2. Calculating Beta (systematic risk)...")
    logger.info("-" * 60)

    beta1 = benchmark.beta(strategy1_returns, market_returns)
    beta2 = benchmark.beta(strategy2_returns, market_returns)
    beta3 = benchmark.beta(strategy3_returns, market_returns)

    logger.info(f"Strategy 1 Beta: {beta1:.3f} (expected ~1.5)")
    logger.info(f"Strategy 2 Beta: {beta2:.3f} (expected ~0.2)")
    logger.info(f"Strategy 3 Beta: {beta3:.3f} (expected ~1.0)")

    logger.info("\nBeta Interpretation:")
    logger.info("  beta > 1.0: More volatile than market (amplifies moves)")
    logger.info("  beta = 1.0: Moves with market")
    logger.info("  beta < 1.0: Less volatile than market (defensive)")
    logger.info("  beta ~ 0.0: Market-neutral")

    logger.info("\n3. Calculating Alpha (excess return)...")
    logger.info("-" * 60)

    risk_free_rate = 0.02
    alpha1 = benchmark.alpha(strategy1_returns, market_returns, risk_free_rate)
    alpha2 = benchmark.alpha(strategy2_returns, market_returns, risk_free_rate)
    alpha3 = benchmark.alpha(strategy3_returns, market_returns, risk_free_rate)

    logger.info(f"Strategy 1 Alpha: {alpha1:.4f} ({alpha1 * 100:.2f}%)")
    logger.info(f"Strategy 2 Alpha: {alpha2:.4f} ({alpha2 * 100:.2f}%)")
    logger.info(f"Strategy 3 Alpha: {alpha3:.4f} ({alpha3 * 100:.2f}%)")

    logger.info("\nAlpha Interpretation:")
    logger.info("  alpha > 0: Outperforming CAPM expectation (skill)")
    logger.info("  alpha = 0: Performing as expected from market exposure")
    logger.info("  alpha < 0: Underperforming CAPM expectation")

    logger.info("\n4. Calculating all Greeks (alpha, beta, R-squared)...")
    logger.info("-" * 60)

    greeks1 = greeks(strategy1_returns, market_returns, risk_free_rate)
    greeks2 = greeks(strategy2_returns, market_returns, risk_free_rate)
    greeks3 = greeks(strategy3_returns, market_returns, risk_free_rate)

    logger.info("\nStrategy 1 Greeks:")
    for key, value in greeks1.items():
        logger.info(f"  {key}: {value:.4f}")

    logger.info("\nStrategy 2 Greeks:")
    for key, value in greeks2.items():
        logger.info(f"  {key}: {value:.4f}")

    logger.info("\nStrategy 3 Greeks:")
    for key, value in greeks3.items():
        logger.info(f"  {key}: {value:.4f}")

    logger.info("\nR-squared Interpretation:")
    logger.info("  R-squared = 1.0: All variance explained by market")
    logger.info("  R-squared = 0.5: Half variance from market, half from other factors")
    logger.info("  R-squared = 0.0: No relationship with market (pure alpha)")

    logger.info("\n5. Calculating rolling Greeks (time-varying)...")
    logger.info("-" * 60)

    logger.info("Creating strategy with changing beta over time...")
    changing_strategy = pd.concat(
        [
            market_returns.iloc[: n_days // 2] * 0.8
            + np.random.randn(n_days // 2) * 0.05 / np.sqrt(252),
            market_returns.iloc[n_days // 2 :] * 1.5
            + np.random.randn(n_days // 2) * 0.08 / np.sqrt(252),
        ]
    )

    rolling = rolling_greeks(
        changing_strategy,
        market_returns,
        window=63,
        risk_free_rate=risk_free_rate,
    )

    logger.info(f"Calculated rolling Greeks for {len(rolling)} periods")
    if not rolling.empty:
        logger.info(f"First valid beta: {rolling['beta'].iloc[0]:.3f}")
        mid_idx = len(rolling) // 2
        logger.info(f"Mid-point beta: {rolling['beta'].iloc[mid_idx]:.3f}")
        logger.info(f"Final beta: {rolling['beta'].iloc[-1]:.3f}")

        logger.info("\nRolling Greeks Statistics:")
        logger.info(
            "  Beta - Mean: {0:.3f}, Std: {1:.3f}".format(
                rolling["beta"].mean(), rolling["beta"].std()
            )
        )
        logger.info(
            "  Alpha - Mean: {0:.4f}, Std: {1:.4f}".format(
                rolling["alpha"].mean(), rolling["alpha"].std()
            )
        )
        logger.info(
            "  R-squared - Mean: {0:.3f}, Std: {1:.3f}".format(
                rolling["r_squared"].mean(), rolling["r_squared"].std()
            )
        )

    logger.info("\n6. Creating visualizations...")
    if plt is None:
        logger.info("Matplotlib not available; skipping charts.")
    else:
        output_dir = project_root / "output" / "plotting"
        os.makedirs(output_dir, exist_ok=True)
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle("Greek Calculations Analysis", fontsize=16, fontweight="bold")

        ax = axes[0, 0]
        (1 + market_returns).cumprod().plot(ax=ax, label="Market", linewidth=2)
        (1 + strategy1_returns).cumprod().plot(ax=ax, label="Strategy 1", alpha=0.7)
        (1 + strategy2_returns).cumprod().plot(ax=ax, label="Strategy 2", alpha=0.7)
        (1 + strategy3_returns).cumprod().plot(ax=ax, label="Strategy 3", alpha=0.7)
        ax.set_title("Cumulative Returns")
        ax.set_ylabel("Cumulative Return")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[0, 1]
        strategies = [
            "Strategy 1\n(Aggressive)",
            "Strategy 2\n(Market-Neutral)",
            "Strategy 3\n(Index)",
        ]
        betas = [beta1, beta2, beta3]
        colors = ["red" if b > 1 else "blue" if b < 0.5 else "green" for b in betas]
        bars = ax.bar(strategies, betas, color=colors, alpha=0.6)
        ax.axhline(y=1.0, color="black", linestyle="--", label="Market Beta (1.0)")
        ax.set_title("Beta Comparison")
        ax.set_ylabel("Beta")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom",
            )

        ax = axes[1, 0]
        alphas = [alpha1, alpha2, alpha3]
        colors = ["green" if a > 0 else "red" for a in alphas]
        bars = ax.bar(strategies, alphas, color=colors, alpha=0.6)
        ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        ax.set_title("Alpha Comparison (Annualized)")
        ax.set_ylabel("Alpha")
        ax.grid(True, alpha=0.3, axis="y")

        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.4f}",
                ha="center",
                va="bottom" if height > 0 else "top",
            )

        ax = axes[1, 1]
        r_squareds = [greeks1["r_squared"], greeks2["r_squared"], greeks3["r_squared"]]
        bars = ax.bar(strategies, r_squareds, color="gray", alpha=0.6)
        ax.set_title("R-squared (Market Correlation)")
        ax.set_ylabel("R-squared")
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3, axis="y")

        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.3f}",
                ha="center",
                va="bottom",
            )

        ax = axes[2, 0]
        if not rolling.empty:
            rolling["beta"].plot(ax=ax, label="Rolling Beta (63-day)", linewidth=2)
        ax.axhline(y=1.0, color="black", linestyle="--", label="Market Beta", alpha=0.5)
        ax.set_title("Rolling Beta (Changing Strategy)")
        ax.set_ylabel("Beta")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax = axes[2, 1]
        ax2 = ax.twinx()
        if not rolling.empty:
            rolling["alpha"].plot(ax=ax, label="Rolling Alpha", color="green", linewidth=2)
            rolling["r_squared"].plot(
                ax=ax2, label="Rolling R-squared", color="purple", linewidth=2, alpha=0.7
            )
        ax.set_ylabel("Alpha", color="green")
        ax2.set_ylabel("R-squared", color="purple")
        ax.set_title("Rolling Alpha and R-squared")
        ax.tick_params(axis="y", labelcolor="green")
        ax2.tick_params(axis="y", labelcolor="purple")

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        output_path = output_dir / "greeks_analysis.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        logger.info(f"Visualization saved to: {output_path}")

    logger.info("\n7. Summary Comparison Table")
    logger.info("=" * 60)

    summary = pd.DataFrame(
        {
            "Beta": [beta1, beta2, beta3],
            "Alpha": [alpha1, alpha2, alpha3],
            "R-squared": [greeks1["r_squared"], greeks2["r_squared"], greeks3["r_squared"]],
            "Total Return": [
                (1 + strategy1_returns).prod() - 1,
                (1 + strategy2_returns).prod() - 1,
                (1 + strategy3_returns).prod() - 1,
            ],
            "Volatility": [
                strategy1_returns.std() * np.sqrt(252),
                strategy2_returns.std() * np.sqrt(252),
                strategy3_returns.std() * np.sqrt(252),
            ],
        },
        index=["Strategy 1", "Strategy 2", "Strategy 3"],
    )

    print("\n" + summary.to_string())

    logger.info("\n8. Key Insights")
    logger.info("=" * 60)
    logger.info(
        "\n".join(
            [
                "Strategy 1 (Aggressive Growth):",
                "  - High beta (>1.5) amplifies market moves",
                "  - Positive alpha indicates excess return",
                "  - Higher R-squared implies market-driven performance",
                "",
                "Strategy 2 (Market-Neutral):",
                "  - Low beta implies limited market exposure",
                "  - Positive alpha implies return from skill",
                "  - Lower R-squared implies diversification benefit",
                "",
                "Strategy 3 (Index Tracker):",
                "  - Beta near 1.0 tracks market",
                "  - Alpha near 0.0 as expected for passive exposure",
                "  - High R-squared implies tight benchmark tracking",
                "",
                "Rolling Greeks:",
                "  - Detects shifts in market sensitivity over time",
                "  - Useful for allocation and risk controls",
            ]
        )
    )

    logger.info("\nGreek calculations example completed successfully.")


if __name__ == "__main__":
    main()

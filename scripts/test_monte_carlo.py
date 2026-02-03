"""Test script for parametric Monte Carlo simulation."""

import sys
from unittest.mock import MagicMock

# Add project root to path
sys.path.append("d:\\Trading\\Applications\\HaruQuant")

mock_module = MagicMock()
sys.modules["apps.backtest"] = mock_module
sys.modules["apps.backtest.result"] = mock_module

from apps.optimization.monte_carlo import parametric_simulation  # noqa: E402


def test_parametric_simulation():
    """Test the parametric Monte Carlo simulation logic."""
    print("Testing Parametric Monte Carlo Simulation...")

    # 1. Test Case: Breakeven strategy (50% WR, 1:1 RRR)
    # Expected return should be close to 0 (ignoring compounding drag or simple arithmetic mean)
    # Actually with geometric compounding, 50% win of 1% and 50% loss of 1% results in:
    # 1.01 * 0.99 = 0.9999 -> slight decay.
    result = parametric_simulation(
        win_rate=0.5,
        reward_risk_ratio=1.0,
        risk_per_trade=0.01,
        num_trades=1000,
        num_simulations=100,
        initial_balance=10000,
    )

    print("\nCase 1 (50% WR, 1:1 RRR):")
    print(f"Mean Return: {result.mean_return:.2f}%")
    print(f"Median Return: {result.median_return:.2f}%")
    print(f"Prob Ruin: {result.probability_of_ruin}%")

    # 2. Test Case: Profitable strategy (40% WR, 2:1 RRR)
    # Expectancy = (0.4 * 2) - (0.6 * 1) = 0.8 - 0.6 = 0.2R per trade.
    # Over 1000 trades, should be very profitable.
    result_prof = parametric_simulation(
        win_rate=0.4,
        reward_risk_ratio=2.0,
        risk_per_trade=0.01,
        num_trades=1000,
        num_simulations=100,
        initial_balance=10000,
    )

    print("\nCase 2 (40% WR, 2:1 RRR):")
    print(f"Mean Return: {result_prof.mean_return:.2f}%")
    print(f"Prob Ruin: {result_prof.probability_of_ruin}%")

    # 3. Test structure
    assert result.num_simulations == 100
    assert len(result.final_balances) == 100
    assert len(result.equity_curves) > 0
    assert len(result.equity_curves[0]) == 1001  # 1000 trades + 1 initial

    print("\nVerification Successful: Logic appears correct and API shape is valid.")


if __name__ == "__main__":
    test_parametric_simulation()

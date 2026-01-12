# Strategy Examples

This folder contains runner scripts for the "Edge" collection of strategies found in `data/strategies/edge`. These examples demonstrate how to load, configure, and backtest different types of trading strategies using the HaruQuant system.

## Overview

Each script in this directory:
1.  **Dynamically imports** a specific strategy class from `data/strategies/edge`.
2.  **Loads** historical data (defaulting to EURUSD D1).
3.  **Configures** the strategy with default parameters.
4.  **Runs** the backtest using the `EventDrivenEngine`.
5.  **Displays** detailed performance metrics using the shared `metrics_utils.py`.

## Available Strategies

The following 11 strategies are available for testing:

### Breakout & Momentum
*   **[01_breakout_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/01_breakout_runner.py)** - Basic breakout strategy.
*   **[02_extended_breakout_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/02_extended_breakout_runner.py)** - Extended version with additional filters or logic.
*   **[06_rsi_breakout_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/06_rsi_breakout_runner.py)** - Breakout logic combined with RSI confirmation.
*   **[08_close_breakout_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/08_close_breakout_runner.py)** - Breakout based specifically on close prices.

### Mean Reversion
*   **[03_mean_reversion_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/03_mean_reversion_runner.py)** - Classic mean reversion strategy.
*   **[04_extended_mean_reversion_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/04_extended_mean_reversion_runner.py)** - Mean reversion with extended parameters/filters.
*   **[05_rsi_mean_reversion_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/05_rsi_mean_reversion_runner.py)** - Mean reversion using RSI levels (e.g., 30/70).
*   **[07_close_mean_reversion_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/07_close_mean_reversion_runner.py)** - Mean reversion based on close price deviations.
*   **[11_bollinger_mean_reversion_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/11_bollinger_mean_reversion_runner.py)** - Mean reversion using Bollinger Bands (buying lower band, selling upper).

### Trend Following
*   **[09_trend_following_ma_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/09_trend_following_ma_runner.py)** - Moving Average based trend following.
*   **[10_bollinger_trend_following_runner.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/10_bollinger_trend_following_runner.py)** - Trend following using Bollinger Band breakouts.

## Common Architecture

### Dynamic Import Pattern
All runners use a dynamic import block to load strategies from `data/strategies/edge`. This allows the test runners to be decoupled from the exact file structure of the strategy repository if needed, though they currently point to specific files.

```python
module_name = "01_breakout"
file_path = project_root / "data/strategies/edge/01_breakout.py"
# ... importlib magic ...
```

### Shared Metrics
The **[metrics_utils.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/01_strategies/metrics_utils.py)** file provides a unified way to display results across all runners, ensuring consistent reporting of:
- Returns (Total, CAGR)
- Risk (Sharpe, Sortino, Drawdown)
- Trade Stats (Win Rate, Profit Factor)

## How to Run

Run any script directly from the project root or the file's directory:

```bash
# Example: Run the Bollinger Mean Reversion strategy
python tests/usage/backtest/01_strategies/11_bollinger_mean_reversion_runner.py
```

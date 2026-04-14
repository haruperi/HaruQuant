Great — let’s start this in the structured format.

## Module 1 — Building a Workflow for AI Trading

### Lesson 1 — Introduction to AI Workflows in Trading

This lesson is about the **end-to-end workflow** of using AI in trading.
Before using supervised learning, unsupervised learning, or reinforcement learning, you need a solid pipeline for turning raw market data into something a model or strategy can use safely.

---

## 1. What is an AI workflow in trading?

An AI trading workflow is the sequence:

1. **Collect market data**
2. **Clean and prepare the data**
3. **Create features**
4. **Define a strategy or model**
5. **Generate signals**
6. **Backtest the strategy**
7. **Evaluate performance**
8. **Refine and repeat**

In real trading systems, this loop becomes continuous:

**Data → Features → Signal → Execution → Evaluation → Improvement**

This is the backbone of both:

* rule-based strategies like RSI
* ML strategies like classification/regression
* RL agents that learn actions from rewards

---

## 2. Why this lesson matters

Many people jump directly into machine learning, but the real edge starts earlier:

* bad data gives bad models
* data leakage gives fake results
* poor backtesting gives false confidence
* weak feature engineering makes ML useless

So this lesson teaches the foundation:

* preparing price data
* backtesting properly
* building a simple baseline trading algorithm

That baseline is important because later ML models must beat it.

---

## 3. Core concepts in this lesson

### A. Price data preparation

Market data usually contains:

* timestamp
* open
* high
* low
* close
* volume

Before using it, you normally:

* sort by time
* remove duplicates
* handle missing values
* ensure correct data types
* resample if needed
* create returns and indicators

Example derived columns:

* percentage return
* log return
* rolling mean
* rolling volatility
* RSI
* moving averages

---

### B. Backtesting

A backtest simulates how a trading strategy would have performed on historical data.

A valid backtest should answer:

* when do we enter?
* when do we exit?
* what is the return?
* what are the costs?
* what is the drawdown?
* is it realistic?

Basic backtesting components:

* capital
* position logic
* signal generation
* transaction cost/slippage
* equity curve
* metrics

---

### C. Simple RSI strategy

The Relative Strength Index is a momentum oscillator.

Common interpretation:

* **RSI < 30** → oversold → possible buy
* **RSI > 70** → overbought → possible sell

This is not “AI” by itself, but it is a perfect baseline workflow:

* prepare data
* calculate indicator
* create signals
* backtest
* evaluate

Later, ML models can replace or enhance the signal-generation step.

---

## 4. AI workflow structure in trading

Here is the practical structure you should remember:

### Step 1 — Get the data

Examples:

* OHLCV price data
* tick data
* fundamentals
* macro data
* sentiment/news

### Step 2 — Clean the data

Examples:

* missing candles
* timezone issues
* duplicate rows
* irregular intervals

### Step 3 — Engineer features

Examples:

* RSI
* moving averages
* rolling volatility
* momentum
* market regime labels

### Step 4 — Define target or decision rule

Examples:

* buy/sell labels
* future return prediction
* regime classification
* action space for RL

### Step 5 — Simulate strategy

This is backtesting.

### Step 6 — Measure performance

Examples:

* cumulative return
* Sharpe ratio
* max drawdown
* win rate
* profit factor

### Step 7 — Improve

Examples:

* better features
* better risk rules
* better validation split
* more realistic costs

---

## 5. Lesson takeaway in trading terms

This lesson is teaching you that **AI trading is not just about the model**.
It is a workflow problem.

Even a simple RSI strategy teaches the same structure used later for:

* ML classifiers predicting next-day direction
* clustering regimes
* RL agents choosing actions
* portfolio optimization models

---

## 6. Practical example in Python

Below is a clean beginner-to-intermediate example that:

* loads price data
* computes RSI
* creates a simple trading signal
* backtests it
* evaluates returns

### File: `lesson_1_rsi_workflow.py`

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute RSI using the classic rolling average gain/loss method.
    """
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def load_price_data(filepath: str) -> pd.DataFrame:
    """
    Load CSV data and standardize columns.
    Expected columns: Date, Open, High, Low, Close, Volume
    """
    df = pd.read_csv(filepath)

    # Normalize column names
    df.columns = [col.strip().lower() for col in df.columns]

    required = {"date", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates(subset="date")
    df = df.set_index("date")

    # Handle missing values conservatively
    df = df.ffill().dropna()

    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived features used by the strategy.
    """
    df = df.copy()
    df["return"] = df["close"].pct_change()
    df["rsi"] = compute_rsi(df["close"], period=14)
    return df


def generate_rsi_signals(df: pd.DataFrame,
                         oversold: float = 30,
                         overbought: float = 70) -> pd.DataFrame:
    """
    Generate long-only RSI signals:
    - Buy when RSI < oversold
    - Exit when RSI > overbought
    """
    df = df.copy()
    df["signal"] = 0

    # Entry and exit rules
    df.loc[df["rsi"] < oversold, "signal"] = 1
    df.loc[df["rsi"] > overbought, "signal"] = 0

    # Forward-fill position state
    df["position"] = df["signal"].replace(to_replace=0, method="ffill").fillna(0)

    return df


def backtest_strategy(df: pd.DataFrame, transaction_cost: float = 0.0005) -> pd.DataFrame:
    """
    Simple vectorized backtest.
    Strategy return uses previous day's position to avoid lookahead bias.
    """
    df = df.copy()

    df["position_shifted"] = df["position"].shift(1).fillna(0)
    df["strategy_return"] = df["position_shifted"] * df["return"]

    # Apply cost when position changes
    trades = df["position"].diff().abs().fillna(0)
    df["cost"] = trades * transaction_cost
    df["net_strategy_return"] = df["strategy_return"] - df["cost"]

    df["buy_hold_equity"] = (1 + df["return"].fillna(0)).cumprod()
    df["strategy_equity"] = (1 + df["net_strategy_return"].fillna(0)).cumprod()

    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    """
    Compute basic backtest metrics.
    """
    strategy_returns = df["net_strategy_return"].dropna()

    total_return = df["strategy_equity"].iloc[-1] - 1
    buy_hold_return = df["buy_hold_equity"].iloc[-1] - 1

    annualized_return = (1 + strategy_returns.mean()) ** 252 - 1
    annualized_vol = strategy_returns.std() * np.sqrt(252)
    sharpe = annualized_return / annualized_vol if annualized_vol != 0 else np.nan

    rolling_max = df["strategy_equity"].cummax()
    drawdown = df["strategy_equity"] / rolling_max - 1
    max_drawdown = drawdown.min()

    trades = df["position"].diff().abs().fillna(0).sum()

    return {
        "Total Strategy Return": total_return,
        "Total Buy & Hold Return": buy_hold_return,
        "Annualized Return": annualized_return,
        "Annualized Volatility": annualized_vol,
        "Sharpe Ratio": sharpe,
        "Max Drawdown": max_drawdown,
        "Trade Count": trades,
    }


def plot_results(df: pd.DataFrame) -> None:
    """
    Plot equity curves.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["buy_hold_equity"], label="Buy & Hold")
    plt.plot(df.index, df["strategy_equity"], label="RSI Strategy")
    plt.title("RSI Strategy Backtest")
    plt.xlabel("Date")
    plt.ylabel("Equity Curve")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def main():
    # Replace with your own CSV file
    filepath = "price_data.csv"

    df = load_price_data(filepath)
    df = prepare_features(df)
    df = generate_rsi_signals(df, oversold=30, overbought=70)
    df = backtest_strategy(df, transaction_cost=0.0005)

    metrics = compute_metrics(df)

    print("\nBacktest Metrics:")
    for key, value in metrics.items():
        if isinstance(value, (float, np.floating)):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")

    plot_results(df)


if __name__ == "__main__":
    main()
```

---

## 7. What this code teaches

This small script teaches the exact workflow:

### Data preparation

* load CSV
* standardize columns
* clean missing values
* compute returns

### Feature engineering

* compute RSI

### Signal generation

* convert indicator into buy/exit decisions

### Backtest

* simulate returns with lagged position
* include transaction costs
* compute equity curve

### Evaluation

* compare with buy-and-hold
* calculate Sharpe
* calculate drawdown

That is the foundation of all later AI trading workflows.

---

## 8. Important caution: avoid common mistakes

### Lookahead bias

Do not use today’s close to trade at today’s close unless that is truly possible in your setup.

That is why the backtest uses:

```python
df["position_shifted"] = df["position"].shift(1)
```

### Overfitting

A strategy that works only on past data may fail live.

### Ignoring costs

A strategy can look profitable before fees and fail after slippage/spread/commission.

### Bad baselines

Always compare against:

* buy-and-hold
* random strategy
* simple technical strategy

---

## 9. How this connects to AI trading later

This RSI workflow is the prototype for later ML workflows.

### Rule-based version

* feature: RSI
* decision: fixed rule

### Supervised learning version

* features: RSI, volatility, moving averages, returns
* target: future return direction
* model: logistic regression, random forest, XGBoost, neural network

### Unsupervised learning version

* features: returns, volatility, momentum
* output: clusters/regimes
* usage: adapt strategy per regime

### Reinforcement learning version

* state: market features
* action: buy/sell/hold
* reward: PnL-adjusted return

So this lesson is really the **first brick** of the entire AI trading stack.

---

## 10. HaruQuant interpretation

For your HaruQuant system, this lesson maps nicely into:

* **data layer** → OHLCV ingestion and cleaning
* **feature layer** → RSI, returns, volatility, momentum
* **strategy layer** → rule-based baseline strategy
* **backtest engine** → execution simulation and equity tracking
* **evaluation layer** → metrics and diagnostics

This means Lesson 1 should become your **baseline workflow template** before adding ML.

---

## 11. Recommended output structure for your project

For your implementation, I would structure this lesson into these files:

* `data_loader.py`
* `feature_engineering.py`
* `rsi_strategy.py`
* `backtester.py`
* `metrics.py`
* `main.py`

That separation will make it easier later to swap RSI with:

* ML models
* RL agents
* regime classifiers

---

## 12. What you should understand before moving on

By the end of this lesson, you should be comfortable with:

* how raw price data becomes model-ready data
* how indicators are features
* how signals become positions
* how positions become returns
* how backtests measure whether a strategy has value

---

## 13. Mini exercise

A good exercise after this lesson is:

1. change RSI thresholds from `30/70` to `20/80`
2. compare results
3. add a moving average filter
4. compare RSI strategy vs buy-and-hold
5. test on different symbols and timeframes

That will make the workflow much more concrete.

---

## 14. Lesson summary

### Main idea

AI in trading starts with a workflow, not with a fancy model.

### Key skills from this lesson

* prepare market data
* engineer simple features
* build a baseline RSI strategy
* backtest properly
* evaluate results realistically

### Why it matters

Later machine learning models must fit into this same pipeline and outperform simple baselines.

---
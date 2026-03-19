# HaruQuant Risk Engine

**Portfolio-First Risk Governance for Algorithmic Trading**

This package implements a professional-grade, portfolio-centric risk management system inspired by institutional trading desks. It separates *planning*, *governance*, and *regime awareness* to ensure scalable, survivable trading systems.

## Table of Contents

- [Overview](#overview)
- [Key Components](#key-components)
- [Architecture](#architecture)
- [Risk Math Foundations](#risk-math-foundations)
- [Module Reference](#module-reference)
  - [RiskGovernor](#riskgovernor)
  - [RiskBudgetAllocator](#riskbudgetallocator)
  - [RiskRegimeDetector](#riskregimedetector)
  - [PositionSizer](#positionsizer)
  - [RiskLimits](#risklimits)
- [Usage Examples](#usage-examples)
- [Integration Guide](#integration-guide)
- [Best Practices](#best-practices)

---

## Quick Start

### Running Risk-Enabled Live Trading

```bash
# Start risk-integrated live trading
python -m apps.live.run_risk --config config/risk_enabled_multi_strategy.json

# Start dashboard (in another terminal)
python -m apps.live.dashboard

# Monitor risk decisions
tail -f logs/risk_enabled/multi_strategy.log | grep "Risk Governor"
```

### Minimal Configuration

```json
{
  "risk_management": {
    "enabled": true,
    "limits": {
      "var_cap_frac": 0.08,
      "es_cap_frac": 0.12
    },
    "governor_config": {
      "timeframe": "H1",
      "start_pos": 0,
      "end_pos": 500
    }
  },
  "position_sizing": {
    "method": "fixed_risk",
    "config": {
      "risk_percent": 1.0,
      "use_dynamic_stop_loss": true,
      "atr_period": 10,
      "atr_target_devider": 3.0,
      "atr_timeframe": "H4"
    }
  }
}
```

---

## Overview

### Design Philosophy

Risk is treated as a **portfolio-level resource**, not a per-trade parameter. This fundamental shift enables:

- **Concentration control** via risk contribution budgeting
- **Regime-aware adaptation** without modifying strategy logic
- **Hard constraints** that cannot be bypassed by optimization
- **Multi-strategy and multi-asset scalability**

### Control Flow

```
Market Data → Signals → Position Sizing → Regime Detection →
Allocation Planning → Risk Gating → Execution
```

Each layer has a specific responsibility and cannot be bypassed.

---

## Key Components

| Component                     | Type              | Purpose                                                                                    |
| ----------------------------- | ----------------- | ------------------------------------------------------------------------------------------ |
| **RiskGovernor**        | Hard Constraints  | Portfolio risk gatekeeper - enforces absolute limits on VaR, ES, margin, and concentration |
| **RiskBudgetAllocator** | Soft Optimization | Plans target positions using risk parity / risk contribution budgeting                     |
| **RiskRegimeDetector**  | State Awareness   | Detects NORMAL vs STRESS regimes to dynamically tighten limits                             |
| **PositionSizer**       | Position Sizing   | Calculates lot sizes using various methods (fixed, Kelly, volatility, etc.)                |
| **RiskLimits**          | Configuration     | Defines portfolio-level hard limits and modeling parameters                                |

---

## Architecture

### Phase 1 Canonical State Foundation

The current risk engine is no longer just a set of standalone runtime components.
Phase 1 adds a canonical state layer that standardizes existing inputs before they
reach higher-level risk logic.

New additive modules:

- `apps/risk/models/` - normalized account, position, symbol, market, and portfolio state models
- `apps/risk/validators/` - thin risk validators that reuse existing utility validators where possible
- `apps/risk/core/portfolio_state_engine.py` - builds a validated `PortfolioState` from raw existing-system inputs

This is intentionally an extension of the current system, not a rewrite:

- `PositionSizer` still owns trade sizing
- `RiskRegimeDetector` still owns regime classification
- `RiskBudgetAllocator` still owns soft portfolio planning
- `RiskGovernor` still owns hard portfolio gating

The canonical state layer exists so later phases can share one validated input
contract instead of each module rebuilding its own assumptions from raw MT5 or
wrapper data.

### Phase 2 Core Risk Metric MVP

Phase 2 adds a normalized metric layer on top of `PortfolioState`.

New additive modules:

- `apps/risk/metrics/` - metric families, registry, and shared metric row contract
- `apps/risk/core/risk_snapshot_engine.py` - orchestrates one current-state metric snapshot

The design stays intentionally simple:

- metrics consume `PortfolioState`, not raw MT5 payloads
- metric rows are normalized so they can be persisted later without redesign
- the math for exposure, covariance, VaR, ES, and RC stays aligned with the existing governor formulas

The initial metric families are:

- account state
- position risk
- symbol risk
- currency exposure
- strategy exposure
- portfolio risk
- margin risk
- concentration

### Three-Layer System

**Layer 1: Regime Detection**

- Monitors market conditions (volatility spikes, correlation spikes, drawdowns)
- Classifies regime as NORMAL or STRESS
- Triggers automatic limit tightening in STRESS

**Layer 2: Allocation Planning**

- Computes target positions using risk contribution budgeting
- Implements risk parity principles
- Applies soft correlation preferences
- Iteratively balances risk across positions

**Layer 3: Governance**

- Evaluates proposed trades against hard limits
- Checks VaR, ES, margin, and concentration caps
- Enforces cluster limits (e.g., max exposure per asset class)
- Returns ACCEPT/REJECT with detailed reasoning

### Why This Separation Matters

- **Prevents bypass**: Optimization logic cannot circumvent risk limits
- **Regime adaptation**: Tighten risk without touching strategy code
- **Extensibility**: Add strategies/assets without redesigning risk system
- **Auditability**: Clear decision trail for every trade

---

## Risk Math Foundations

### Portfolio Variance

```
σ²_p = wᵀ Σ w
```

Where:

- `w` = weight vector (notional positions normalized)
- `Σ` = covariance matrix (rolling volatility + correlation)

### Value at Risk (VaR)

```
VaR = z_α · σ_p · √T · PortfolioValue
```

Where:

- `z_α` = confidence level quantile (e.g., 1.645 for 95%)
- `σ_p` = portfolio standard deviation
- `T` = time horizon in days
- `PortfolioValue` = total notional exposure

### Expected Shortfall (ES / CVaR)

```
ES = (φ(z_α) / (1-α)) · σ_p · √T · PortfolioValue
```

Where:

- `φ(z_α)` = normal PDF at z_α
- `α` = confidence level (e.g., 0.95)

### Risk Contribution

```
RC_i = w_i · (Σw)_i        [absolute contribution]
RC_i% = RC_i / σ²_p        [percentage contribution]
```

Used for:

- Identifying concentration risk
- Risk parity allocation
- Rebalancing triggers

### Portfolio Correlation

```
corr(i, p) = (Σw)_i / (σ_i · σ_p)
```

Measures how aligned each asset is with the overall portfolio. Used for correlation budgeting.

---

## Module Reference

### RiskGovernor

**Purpose**: Portfolio risk gatekeeper that enforces hard constraints.

**Location**: `apps/risk/governor.py`

**Key Methods**:

```python
def evaluate_add_position(
    current_positions: Dict[str, float],
    candidate_symbol: str,
    candidate_lots: float,
    symbol_to_cluster: Optional[Dict[str, str]] = None,
    regime: Optional[RegimeState] = None,
) -> RiskReport
```

Evaluates whether adding a position violates risk limits.

**Checks Performed**:

1. Margin cap (if MT5 margin API available)
2. Absolute VaR and ES caps
3. Incremental (delta) VaR and ES caps
4. Risk contribution concentration limits
5. Cluster caps (e.g., max VaR per asset class)

**Returns**: `RiskReport` with decision (ACCEPT/REJECT) and detailed metrics.

**Regime Handling**:
In STRESS regime, limits are automatically tightened:

- VaR cap: min(config, 7%)
- ES cap: min(config, 10%)
- Delta caps reduced
- Correlation floors raised to 0.75
- Max single RC: min(config, 12%)

---

### RiskBudgetAllocator

**Purpose**: Plans target positions using risk contribution budgeting (risk parity style).

**Location**: `apps/risk/allocator.py`

**Key Methods**:

```python
def compute_target_lots(
    symbols: List[str],
    base_lots: Dict[str, float],
    budgets: Optional[Dict[str, float]] = None,
    regime: Optional[RegimeState] = None,
    max_iters: int = 50,
    lr: float = 0.25,
) -> Dict[str, float]
```

**Algorithm**:

1. Start from base lot sizes (e.g., from volatility sizing)
2. Apply correlation penalty to budgets (favor low-corr additions)
3. Iteratively adjust lots to align risk contributions with target budgets
4. Converge when RC% ≈ budget% (tolerance < 1%)

**Correlation Penalty**:

```python
penalty = exp(-k · (corr - target))  if corr > target
```

Reduces budget allocation for highly correlated positions.

**Helpers**:

```python
def lots_to_deltas(current: Dict[str, float], target: Dict[str, float]) -> Dict[str, float]
```

Computes position changes needed to reach target allocation.

---

### RiskRegimeDetector

**Purpose**: Detects NORMAL vs STRESS market regimes using robust signals.
Not to be confused with price‑action, market structure regimes detection.
    Usually at the instrument leve used to adapt strategy logic,
    e.g. switch a trend‑follower on/off or change indicators.

    Key difference:
    - RiskRegimeDetector is about portfolio risk stress, not price structure.
    - It’s risk gating: tighten limits during stress without changing the strategy’s logic.
    - “Trending/ranging/volatile” is strategy selection/adaptation.

    If you want both:
    - Use trend/range regimes inside strategies to shape signals.
    - Use RiskRegimeDetector above the strategy to tighten caps during stress.

    Portfolio‑level risk signals:
    1) Volatility spike on equal-weight portfolio proxy
        - Goal: detect when the market is moving much more violently than usual.
        - Why: big swings mean your positions can lose money faster than normal.
    2) Correlation spike (average off-diagonal correlation)
        - Goal: detect when assets move together more than usual.
        - Why: diversification breaks down; losses compound faster.
    3) Equity drawdown trigger (optional, if equity_curve provided)
        - Goal: detect when the portfolio has lost a significant amount of value.
        - Why: large drawdowns can lead to margin calls and forced liquidation.

    If at least 2 signals are triggered => STRESS, else NORMAL.


**Location**: `apps/risk/regime.py`

**Detection Logic**:

Uses **majority vote** of 3 signals (STRESS if ≥2 triggered):

1. **Volatility Spike**

   - Equal-weight portfolio volatility > `vol_spike_mult` × median rolling vol
   - Default: 1.8x multiplier
2. **Correlation Spike**

   - Average off-diagonal correlation > `corr_spike_level`
   - Default: 0.55 threshold
3. **Drawdown Trigger**

   - Equity curve drawdown from peak > `dd_trigger_frac`
   - Default: 5% drawdown

**Usage**:

```python
detector = RiskRegimeDetector(
    vol_spike_mult=1.8,
    corr_spike_level=0.55,
    dd_trigger_frac=0.05,
    lookback=60
)

regime = detector.detect(returns_df, equity_curve)
# Returns: RegimeState(name="NORMAL" or "STRESS")
```

---

### PositionSizer

**Purpose**: Calculates position sizes using various risk-based methods.

**Location**: `apps/risk/position_sizing.py`

**Available Methods**:

| Method               | Description                                 | Key Parameters                          |
| -------------------- | ------------------------------------------- | --------------------------------------- |
| `fixed_lot`        | Constant lot size                           | `lot_size` (default: 0.1)             |
| `milestone`        | Increase size at balance milestones         | `milestone_amount`, `lot_increment` |
| `fixed_risk`       | Risk fixed % per trade (requires stop loss) | `risk_percent` (default: 1.0%)        |
| `kelly`            | Kelly Criterion optimal sizing              | `win_rate`, `avg_win`, `avg_loss` |
| `volatility`       | ATR-based inverse volatility                | `risk_percent`, `atr_multiplier`    |
| `fixed_fractional` | Fixed % of capital per position             | `fraction` (default: 2.0%)            |

**Example Usage**:

```python
# Fixed risk sizing (1% risk per trade)
sizer = PositionSizer(
    method="fixed_risk",
    config={"risk_percent": 1.0}
)

lots = sizer.calculate_size(
    account_balance=10000,
    entry_price=1.1000,
    stop_loss=1.0950,
    symbol_info=symbol_info
)

# Volatility-based sizing
sizer = PositionSizer(
    method="volatility",
    config={"risk_percent": 1.5, "atr_multiplier": 1.0}
)

lots = sizer.calculate_size(
    account_balance=10000,
    entry_price=1.1000,
    context={"atr": 0.0020},
    symbol_info=symbol_info
)
```

**Helper Functions**:

```python
validate_position_size(size, symbol_info, max_size=None)
# Rounds to lot step, enforces min/max

estimate_kelly_parameters(backtest_result)
# Estimates Kelly params from backtest history
```

**Dynamic Stop Loss (ATR-Based)**:

When strategies don't provide stop loss, PositionSizer can automatically calculate it using ATR:

```python
sizer = PositionSizer(
    method="fixed_risk",
    config={
        "risk_percent": 1.0,
        "use_dynamic_stop_loss": true,
        "atr_period": 10,
        "atr_target_devider": 3.0,
        "atr_timeframe": "H4"
    },
    mt5_client=mt5_client
)

# Automatically calculates stop loss when not provided
lots = sizer.calculate_size(
    account_balance=10000,
    entry_price=1.1000,
    stop_loss=None,        # Will auto-calculate
    symbol="EURUSD",
    signal_type="buy"
)
# Stop Loss = Entry - (ATR(10) / 3) for buy signals
# Stop Loss = Entry + (ATR(10) / 3) for sell signals
```

**Formula**:

```
1. Fetch data on specified timeframe (default: H4)
2. Calculate ATR with period N (default: 10)
3. Stop Distance = ATR / target_devider (default: 3)
4. For BUY: stop_loss = entry_price - stop_distance
   For SELL: stop_loss = entry_price + stop_distance
```

**Benefits**:

- Volatility-adaptive stops (wider in volatile markets, tighter in calm)
- Symbol-specific (XAUUSD gets wider stops than EURUSD automatically)
- No manual configuration needed
- Automatically updates with market conditions

---

### RiskLimits

**Purpose**: Configuration dataclass for portfolio-level risk limits.

**Location**: `apps/risk/risk_limits.py`

**Key Parameters**:

**Hard Caps** (fractions of equity):

- `var_cap_frac`: Portfolio VaR cap (default: 0.10 = 10%)
- `es_cap_frac`: Portfolio ES cap (default: 0.15 = 15%)
- `delta_var_cap_frac`: Max VaR increase per trade (default: 0.02 = 2%)
- `delta_es_cap_frac`: Max ES increase per trade (default: 0.03 = 3%)
- `max_margin_used_frac`: Max margin usage (default: 0.50 = 50%)

**Correlation Controls**:

- `min_pair_corr`: Conservative correlation floor (default: 0.20)
- `stressed_corr_floor`: Floor in STRESS regime (default: 0.60)
- `use_stressed_corr`: Enable stressed correlation (default: True)

**VaR/ES Settings**:

- `confidence_level`: VaR confidence (default: 0.95)
- `time_horizon_days`: Risk horizon (default: 1 day)

**Rolling Windows**:

- `vol_lookback`: Volatility window (default: 20 bars)
- `corr_lookback`: Correlation window (default: 60 bars)

**Concentration Controls**:

- `max_single_rc_frac`: Max risk contribution per symbol (default: 0.20 = 20%)
- `rc_rebalance_tolerance`: RC deviation tolerance (default: 0.05 = 5%)

**Cluster Limits** (optional):

- `cluster_var_caps`: Dict[cluster, var_cap_frac]
- `cluster_es_caps`: Dict[cluster, es_cap_frac]

**Example**:

```python
limits = RiskLimits(
    var_cap_frac=0.08,           # 8% max VaR
    es_cap_frac=0.12,            # 12% max ES
    delta_var_cap_frac=0.015,    # 1.5% max delta VaR
    max_single_rc_frac=0.15,     # 15% max single position RC
    cluster_var_caps={
        "FOREX": 0.06,
        "COMMODITIES": 0.04
    }
)
```

**CorrelationPreference**:

Soft preference for low-correlation additions (used by allocator):

```python
corr_pref = CorrelationPreference(
    target_corr=0.50,        # Prefer corr ≤ 0.50
    penalty_strength=2.0,    # Exponential penalty steepness
    min_budget_frac=0.30     # Never reduce budget below 30%
)
```

---

## Usage Examples

### Example 1: Basic Risk Governance

```python
from apps.risk import RiskGovernor, RiskLimits

# Configure limits
limits = RiskLimits(
    var_cap_frac=0.10,
    es_cap_frac=0.15,
    delta_var_cap_frac=0.02
)

# Initialize governor
governor = RiskGovernor(
    mt5_client=mt5_client,
    limits=limits,
    timeframe="D1",
    start_pos=0,
    end_pos=500
)

# Evaluate adding a position
current_positions = {"EURUSD": 0.5, "GBPUSD": 0.3}

report = governor.evaluate_add_position(
    current_positions=current_positions,
    candidate_symbol="USDJPY",
    candidate_lots=0.2
)

if report.decision == "ACCEPT":
    print(f"Trade approved. New VaR: ${report.new_var:,.2f}")
    # Execute trade
else:
    print(f"Trade rejected: {report.reason}")
```

### Example 2: Regime-Aware Allocation

```python
from apps.risk import RiskGovernor, RiskBudgetAllocator, RiskRegimeDetector, RiskLimits

# Setup
limits = RiskLimits()
governor = RiskGovernor(mt5_client, limits)
allocator = RiskBudgetAllocator(governor)
detector = RiskRegimeDetector()

# Get market data
symbols = ["EURUSD", "GBPUSD", "USDJPY"]
returns_df = get_returns_data(symbols)  # Your data function
equity_curve = get_equity_curve()        # Your equity tracking

# Detect regime
regime = detector.detect(returns_df, equity_curve)
print(f"Current regime: {regime.name}")

# Compute base lot sizes (e.g., from volatility)
base_lots = {
    "EURUSD": 0.3,
    "GBPUSD": 0.2,
    "USDJPY": 0.4
}

# Compute risk-balanced target lots
target_lots = allocator.compute_target_lots(
    symbols=symbols,
    base_lots=base_lots,
    regime=regime
)

print(f"Target lots: {target_lots}")

# Compute position changes
current_lots = {"EURUSD": 0.2, "GBPUSD": 0.1, "USDJPY": 0.3}
deltas = allocator.lots_to_deltas(current_lots, target_lots)

# Gate each change through governor
for symbol, delta in deltas.items():
    if abs(delta) < 0.01:
        continue

    report = governor.evaluate_add_position(
        current_positions=current_lots,
        candidate_symbol=symbol,
        candidate_lots=delta,
        regime=regime
    )

    if report.decision == "ACCEPT":
        print(f"{symbol}: Execute {delta:+.2f} lots")
        current_lots[symbol] = current_lots.get(symbol, 0) + delta
    else:
        print(f"{symbol}: Rejected - {report.reason}")
```

### Example 3: Multi-Method Position Sizing

```python
from apps.risk import PositionSizer

# Method 1: Fixed risk (1% per trade)
sizer_fixed = PositionSizer("fixed_risk", {"risk_percent": 1.0})

lots1 = sizer_fixed.calculate_size(
    account_balance=10000,
    entry_price=1.1000,
    stop_loss=1.0950,
    symbol_info=symbol_info
)

# Method 2: Kelly Criterion
sizer_kelly = PositionSizer("kelly", {
    "kelly_fraction_limit": 0.25,
    "win_rate": 0.55,
    "avg_win": 150,
    "avg_loss": 100
})

lots2 = sizer_kelly.calculate_size(
    account_balance=10000,
    entry_price=1.1000
)

# Method 3: ATR-based volatility
sizer_vol = PositionSizer("volatility", {
    "risk_percent": 1.5,
    "atr_multiplier": 1.0
})

lots3 = sizer_vol.calculate_size(
    account_balance=10000,
    entry_price=1.1000,
    context={"atr": 0.0025},
    symbol_info=symbol_info
)

print(f"Fixed risk: {lots1:.2f} lots")
print(f"Kelly: {lots2:.2f} lots")
print(f"Volatility: {lots3:.2f} lots")
```

### Example 4: Cluster Limits

```python
limits = RiskLimits(
    var_cap_frac=0.10,
    cluster_var_caps={
        "FOREX": 0.06,
        "COMMODITIES": 0.04,
        "INDICES": 0.05
    },
    cluster_es_caps={
        "FOREX": 0.08,
        "COMMODITIES": 0.06,
        "INDICES": 0.07
    }
)

governor = RiskGovernor(mt5_client, limits)

# Define symbol clusters
symbol_to_cluster = {
    "EURUSD": "FOREX",
    "GBPUSD": "FOREX",
    "XAUUSD": "COMMODITIES",
    "XTIUSD": "COMMODITIES",
    "US30": "INDICES"
}

current_positions = {
    "EURUSD": 0.5,
    "GBPUSD": 0.4,
    "XAUUSD": 0.2
}

report = governor.evaluate_add_position(
    current_positions=current_positions,
    candidate_symbol="USDJPY",
    candidate_lots=0.3,
    symbol_to_cluster=symbol_to_cluster
)

# Will check both portfolio-level AND FOREX cluster caps
```

---

## Integration Guide

### Required MT5 Client Interface

Your MT5 client must implement these methods:

**Required**:

```python
def get_bars(symbol: str, timeframe: str, count: int = 100, start_pos: int = 0) -> pd.DataFrame:
    """Returns OHLC DataFrame with 'close' or 'Close' column

    Args:
        symbol: Trading symbol (e.g., "EURUSD")
        timeframe: Timeframe string (e.g., "D1", "H1", "H4", "M1")
        count: Number of bars to fetch
        start_pos: Starting position (0 = most recent)

    Returns:
        DataFrame with OHLC data (lowercase or uppercase column names)
    """

def get_symbol_info(symbol: str):
    """Returns object with trade_contract_size, trade_tick_value, trade_tick_size"""

def get_account_equity() -> float:
    """Returns current account equity"""
```

**Optional** (for margin checks):

```python
def get_margin_required(symbol: str, lots: float) -> float:
    """Returns margin required for position"""
```

**Note**: Risk modules automatically handle both lowercase ('close') and uppercase ('Close') column names.

### Typical Integration Flow

```python
# 1. Initialize components
limits = RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12)
governor = RiskGovernor(mt5_client, limits, timeframe="D1")
allocator = RiskBudgetAllocator(governor)
detector = RiskRegimeDetector()
sizer = PositionSizer("fixed_risk", {"risk_percent": 1.0})

# 2. Generate strategy signals
signals = strategy.generate_signals()  # Your strategy

# 3. Calculate base position sizes
base_lots = {}
for signal in signals:
    lots = sizer.calculate_size(
        account_balance=mt5_client.get_account_equity(),
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        symbol_info=mt5_client.get_symbol_info(signal.symbol)
    )
    base_lots[signal.symbol] = lots

# 4. Detect market regime
returns_df = build_returns_dataframe()  # Your data pipeline
regime = detector.detect(returns_df, equity_curve)

# 5. Compute risk-balanced allocations
target_lots = allocator.compute_target_lots(
    symbols=list(base_lots.keys()),
    base_lots=base_lots,
    regime=regime
)

# 6. Gate through risk governor
current_positions = get_current_positions()  # Your position tracking

for symbol, target_lot in target_lots.items():
    delta = target_lot - current_positions.get(symbol, 0)

    report = governor.evaluate_add_position(
        current_positions=current_positions,
        candidate_symbol=symbol,
        candidate_lots=delta,
        regime=regime
    )

    if report.decision == "ACCEPT":
        execute_trade(symbol, delta)  # Your execution
        current_positions[symbol] = target_lot
    else:
        log.warning(f"Trade rejected: {symbol} - {report.reason}")
```

### Where This Module Sits

```
┌─────────────────────┐
│   Data Layer        │ ← MT5Client, get_data()
└──────────┬──────────┘
	   │
           ▼
┌─────────────────────┐
│   Strategy Layer    │ ← Signal generation, indicators
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Position Sizing    │ ← PositionSizer
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Regime Detection   │ ← RiskRegimeDetector
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Allocation       │ ← RiskBudgetAllocator
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Risk Governance   │ ← RiskGovernor (MUST NOT BE BYPASSED)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Execution Layer    │ ← Broker API, order management
└─────────────────────┘
```

**Critical**: The RiskGovernor gate **must never be bypassed**. All position changes flow through it.

### Key Features

- **Dynamic Position Sizing**: Replaces hardcoded volumes with risk-based calculation
  - Methods: fixed_risk, Kelly Criterion, volatility (ATR), milestone, fixed_fractional
- **Regime Detection**: Automatically detects NORMAL vs STRESS market conditions
  - Tightens risk limits during stress periods
  - Uses 3-signal majority vote (volatility spike, correlation spike, drawdown)
- **Risk Budget Allocation**: Portfolio-level risk parity
  - Balances risk contributions across positions
  - Favors low-correlation additions
- **Risk Governor**: Hard constraints enforcement
  - VaR and ES caps (portfolio + incremental)
  - Margin limits
  - Concentration limits (risk contribution)
  - Cluster limits (per asset class)

---

## Full Risk Management Cycle

### Step-by-Step Flow

#### 1. Market Data Collection

```python
# Engine fetches data for all symbols
# - Strategy timeframe data (for signals)
# - Daily data (for regime detection)
# - Account equity tracking
```

#### 2. Signal Generation

```python
# Each strategy processes new bars
for strategy in strategies:
    if new_bar_detected:
        signal = strategy.get_signal()
        # Example signal:
        # {
        #     'signal': 'buy',
        #     'entry_price': 1.1000,
        #     'stop_loss': 1.0950,
        #     'reason': 'EMA crossover...'
        # }
```

#### 3. Position Sizing

```python
# Calculate base lot size for each signal
position_sizer = PositionSizer(method='fixed_risk', config={'risk_percent': 1.0})

volume = position_sizer.calculate_size(
    account_balance=10000,
    entry_price=1.1000,
    stop_loss=1.0950,
    symbol_info=symbol_info
)
# Output: 2.04 lots (risking 1% of $10,000 with 50-pip stop)
```

#### 4. Regime Detection

```python
# Detect current market regime
regime_detector = RiskRegimeDetector()

regime = regime_detector.detect(
    returns_df=portfolio_returns,  # Daily returns for all symbols
    equity_curve=equity_series      # Your account equity history
)
# Output: RegimeState(name='NORMAL') or RegimeState(name='STRESS')

# In STRESS, limits are automatically tightened:
# - VaR cap: 10% → 7%
# - ES cap: 15% → 10%
# - Correlation floor: 0.20 → 0.75
# - Max single RC: 20% → 12%
```

#### 5. Risk Budget Allocation

```python
# Allocate risk budgets across positions
allocator = RiskBudgetAllocator(risk_governor, correlation_preference)

# Base lots from position sizing
base_lots = {
    'EURUSD': 0.50,
    'GBPUSD': 0.40,
    'XAUUSD': 0.30
}

# Risk budgets from strategy configs
budgets = {
    'EURUSD': 0.30,  # 30% of portfolio risk
    'GBPUSD': 0.30,  # 30%
    'XAUUSD': 0.40   # 40%
}

target_lots = allocator.compute_target_lots(
    symbols=['EURUSD', 'GBPUSD', 'XAUUSD'],
    base_lots=base_lots,
    budgets=budgets,
    regime=regime
)
# Output: {'EURUSD': 0.45, 'GBPUSD': 0.42, 'XAUUSD': 0.35}
# (Adjusted based on correlations and risk contributions)
```

#### 6. Risk Governor Gating

```python
# Gate each trade through risk governor
governor = RiskGovernor(mt5_client, risk_limits)

report = governor.evaluate_add_position(
    current_positions={'EURUSD': 0.30, 'GBPUSD': 0.25},
    candidate_symbol='XAUUSD',
    candidate_lots=0.35,
    symbol_to_cluster={'EURUSD': 'FOREX', 'GBPUSD': 'FOREX', 'XAUUSD': 'METALS'},
    regime=regime
)

if report.decision == 'ACCEPT':
    # Trade approved
    print(f"New VaR: ${report.new_var:,.2f}")
    print(f"Delta VaR: ${report.delta_var:,.2f}")
    execute_trade()
else:
    # Trade rejected
    print(f"Rejected: {report.reason}")
    # Example reasons:
    # - "Portfolio VaR cap exceeded"
    # - "Risk contribution cap exceeded by ['XAUUSD']"
    # - "Cluster cap exceeded: METALS VaR > cap"
```

#### 7. Execution

```python
# If approved by governor, execute the trade
trade_executor.execute_signal(signal, volume=target_volume)
```

---

## Quick Start

### 1. Install Dependencies

Ensure you have all risk management dependencies:

```bash
pip install numpy pandas scipy
```

### 2. Create Configuration

Use the provided risk-enabled config:

```bash
config/risk_enabled_multi_strategy.json
```

Key sections:

- `risk_management`: Risk limits, regime detector, correlation preferences
- `position_sizing`: Sizing method and config
- `symbol_clusters`: Symbol-to-cluster mapping
- `strategies`: Each strategy has a `risk_budget` field

### 3. Run Live Trading

```bash
python -m apps.live.run_risk --config config/risk_enabled_multi_strategy.json
```

### 4. Monitor Dashboard

In another terminal:

```bash
python -m apps.live.dashboard
```

---

## Configuration

### Complete Example Config

```json
{
  "user_id": 1,
  "db_path": "data/database/haruquant.db",
  "mt5": {
    "login": 12345678,
    "password": "your_password",
    "server": "YourBroker-Demo",
    "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
  },
  "risk_management": {
    "enabled": true,
    "limits": {
      "var_cap_frac": 0.08,
      "es_cap_frac": 0.12,
      "delta_var_cap_frac": 0.015,
      "delta_es_cap_frac": 0.02,
      "max_margin_used_frac": 0.45,
      "min_pair_corr": 0.20,
      "stressed_corr_floor": 0.65,
      "use_stressed_corr": true,
      "confidence_level": 0.95,
      "time_horizon_days": 1,
      "vol_lookback": 20,
      "corr_lookback": 60,
      "max_single_rc_frac": 0.18,
      "rc_rebalance_tolerance": 0.05,
      "cluster_var_caps": {
        "FOREX": 0.05,
        "METALS": 0.04
      },
      "cluster_es_caps": {
        "FOREX": 0.07,
        "METALS": 0.06
      }
    },
    "regime_detector": {
      "vol_spike_mult": 1.8,
      "corr_spike_level": 0.55,
      "dd_trigger_frac": 0.05,
      "lookback": 60
    },
    "correlation_preference": {
      "target_corr": 0.50,
      "penalty_strength": 2.0,
      "min_budget_frac": 0.30
    },
    "governor_config": {
      "timeframe": "D1",
      "start_pos": 0,
      "end_pos": 500
    }
  },
  "position_sizing": {
    "method": "fixed_risk",
    "config": {
      "risk_percent": 1.0
    },
    "fallback_volume": 0.01
  },
  "symbol_clusters": {
    "XAUUSD": "METALS",
    "EURUSD": "FOREX",
    "GBPUSD": "FOREX",
    "USDJPY": "FOREX"
  },
  "strategies": [
    {
      "name": "EURUSD_Trend",
      "strategy_type": "TrendFollowing",
      "symbol": "EURUSD",
      "timeframe": "M1",
      "magic_number": 100001,
      "params": {
        "fast_period": 20,
        "slow_period": 50,
        "filter_period": 200
      },
      "initial_bars": 250,
      "risk_budget": 0.25
    }
  ]
}
```

### Configuration Parameters

#### Risk Limits

| Parameter                | Description                     | Default | Recommended |
| ------------------------ | ------------------------------- | ------- | ----------- |
| `var_cap_frac`         | Max portfolio VaR (% of equity) | 0.10    | 0.08-0.12   |
| `es_cap_frac`          | Max portfolio ES (% of equity)  | 0.15    | 0.12-0.18   |
| `delta_var_cap_frac`   | Max VaR increase per trade      | 0.02    | 0.01-0.02   |
| `delta_es_cap_frac`    | Max ES increase per trade       | 0.03    | 0.02-0.03   |
| `max_margin_used_frac` | Max margin usage                | 0.50    | 0.40-0.50   |
| `max_single_rc_frac`   | Max risk from single position   | 0.20    | 0.15-0.20   |

#### Position Sizing Methods

**1. Fixed Risk (Recommended for Most Cases)**

```json
{
  "method": "fixed_risk",
  "config": {
    "risk_percent": 1.0
  }
}
```

- Risks fixed % of account per trade
- Requires stop loss

**2. Volatility-Based (ATR)**

```json
{
  "method": "volatility",
  "config": {
    "risk_percent": 1.5,
    "atr_multiplier": 1.0
  }
}
```

- Sizes inversely to volatility
- Requires ATR in signal context

**3. Kelly Criterion**

```json
{
  "method": "kelly",
  "config": {
    "kelly_fraction_limit": 0.25,
    "win_rate": 0.55,
    "avg_win": 150,
    "avg_loss": 100
  }
}
```

- Optimal sizing based on edge
- Use with caution (can be aggressive)

**4. Milestone**

```json
{
  "method": "milestone",
  "config": {
    "initial_balance": 10000,
    "base_lot_size": 0.1,
    "milestone_amount": 3000,
    "lot_increment": 0.2
  }
}
```

- Increases size at profit milestones
- Controlled growth

#### Risk Budgets

Assign risk budgets to strategies (must sum to ~1.0):

```json
{
  "strategies": [
    {
      "name": "EURUSD_Trend",
      "risk_budget": 0.30
    },
    {
      "name": "GBPUSD_Trend",
      "risk_budget": 0.30
    },
    {
      "name": "XAUUSD_Trend",
      "risk_budget": 0.40
    }
  ]
}
```

---

## Running the System

### Standard Command

```bash
python -m apps.live.run_risk --config config/risk_enabled_multi_strategy.json
```

### Expected Startup Output

```
================================================================================
Starting HaruQuant Risk-Integrated Live Trading System
================================================================================
Config file: config/risk_enabled_multi_strategy.json
...
================================================================================
Initializing Risk Management System
================================================================================
Initializing Position Sizer...
Position Sizer: fixed_risk - {'risk_percent': 1.0}
Initializing Regime Detector...
Regime Detector configured: {'vol_spike_mult': 1.8, ...}
Initializing Risk Limits...
Risk Limits: VaR=8.0%, ES=12.0%
Initializing Risk Governor...
Risk Governor initialized
Initializing Risk Budget Allocator...
Risk Budget Allocator initialized
Initial equity: $10,000.00
================================================================================
Risk Management System Initialized Successfully
================================================================================
...
Risk-Integrated Live Trading Engine Started Successfully
================================================================================
Strategies: 6
  - EURUSD_Trend (EURUSD M1) [Risk Budget: 0.2]
  - GBPUSD_Trend (GBPUSD M1) [Risk Budget: 0.2]
  - XAUUSD_Trend (XAUUSD M1) [Risk Budget: 0.2]
  ...
================================================================================
Risk Management:
  Status: ENABLED
  Position Sizing: fixed_risk
  Current Regime: NORMAL
================================================================================
```

### Signal Processing Output

When a signal is detected and processed:

```
[EURUSD_Trend] New bar closed: 2026-01-08 10:30:00
Collected 1 signals
Calculating base position sizes...
[EURUSD_Trend] Calculated volume: 0.204 lots (balance=$10,000.00)
Running risk budget allocation...
Base lots: {'EURUSD': 0.204}
Risk budgets: {'EURUSD': 0.2}
Allocated lots: {'EURUSD': 0.204}
============================================================
[EURUSD_Trend] SIGNAL: BUY
============================================================
Symbol: EURUSD
Time: 2026-01-08 10:30:00
Reason: Fast(20) crossed above Slow(50) > Filter(200)
Entry Price: 1.10000
[EURUSD_Trend] Portfolio check passed
[EURUSD_Trend] All safety checks passed
[EURUSD_Trend] Gating through Risk Governor...
============================================================
Risk Governor Decision: ACCEPT
Reason: All risk limits satisfied.
Current VaR: $450.00
New VaR: $612.00
Delta VaR: $162.00
Current ES: $580.00
New ES: $790.00
Delta ES: $210.00
Risk Contributions: {'GBPUSD': 0.45, 'EURUSD': 0.55}
============================================================
[EURUSD_Trend] Trade APPROVED by Risk Governor
Order sent: BUY 0.204 EURUSD at 1.10000
============================================================
Total trades today: 1
```

---

## Understanding the Flow

### What Happens Each Iteration

```
Every 2 seconds:
├── 1. Check if trading is enabled (state file)
├── 2. Update equity curve
├── 3. Detect market regime (NORMAL/STRESS)
│   ├── Fetch D1 data for all symbols
│   ├── Calculate returns
│   ├── Check 3 signals (vol spike, corr spike, drawdown)
│   └── Update current_regime
├── 4. Check each strategy for new bars
│   ├── If new bar:
│   │   ├── Process signal
│   │   └── Add to pending_signals list
│   └── Continue
├── 5. Calculate position sizes for all signals
│   ├── Use PositionSizer (fixed_risk, Kelly, etc.)
│   └── Add 'volume' field to signals
├── 6. Run risk budget allocation (entry signals only)
│   ├── Collect base_lots and budgets
│   ├── Run RiskBudgetAllocator
│   └── Adjust volumes based on risk contributions
├── 7. Gate each signal through risk governor
│   ├── Get current portfolio positions
│   ├── Call governor.evaluate_add_position()
│   ├── Log detailed risk report
│   └── ACCEPT or REJECT
├── 8. Execute approved trades
│   └── trade_executor.execute_signal()
├── 9. Update state and export status
└── Sleep 2 seconds
```

### Regime-Based Adjustments

When regime changes from NORMAL to STRESS:

```python
# NORMAL Limits
VaR Cap: 8% of equity
ES Cap: 12% of equity
Delta VaR Cap: 1.5% per trade
Max Single RC: 18%
Correlation Floor: 0.20

# STRESS Limits (automatically applied)
VaR Cap: min(8%, 7%) = 7%
ES Cap: min(12%, 10%) = 10%
Delta VaR Cap: reduced proportionally
Max Single RC: min(18%, 12%) = 12%
Correlation Floor: max(0.20, 0.75) = 0.75
```

The system **automatically** tightens all limits without touching strategy code.

---

## Monitoring & Debugging

### Log Files

Located in `logs/risk_enabled/`:

**multi_strategy.log**

- Full system logs
- Risk calculations
- Governor decisions

**trades.log**

- Trade executions only
- Quick trade audit trail

### Key Log Markers

Search for these in logs:

```bash
# Regime changes
grep "Current Regime:" logs/risk_enabled/multi_strategy.log

# Risk governor decisions
grep "Risk Governor Decision:" logs/risk_enabled/multi_strategy.log

# Trade rejections
grep "REJECT" logs/risk_enabled/multi_strategy.log

# Position sizing
grep "Calculated volume:" logs/risk_enabled/multi_strategy.log

# Risk allocation
grep "Allocated lots:" logs/risk_enabled/multi_strategy.log
```

### Dashboard

Real-time monitoring:

```bash
python -m apps.live.dashboard
```

Shows:

- Active strategies
- Current regime
- Portfolio positions
- Recent signals
- Trade statistics

### State File

Control trading without restarting:

**risk_enabled_state.json**

```json
{
  "enabled": true,
  "paused": false,
  "trade_count": 15,
  "last_trade_date": "2026-01-08",
  "last_run": "2026-01-08T15:30:00"
}
```

Modify while running:

- Set `"enabled": false` to stop new trades
- Set `"paused": true` to temporarily pause

---

## Advanced Configuration

### Custom Position Sizing

Create your own sizing method:

```python
# In apps/risk/position_sizing.py

class PositionSizer:
    def _my_custom_sizing(self, account_balance, entry_price, context):
        """Your custom sizing logic."""
        # Example: Combine fixed risk with volatility adjustment
        base_risk = account_balance * 0.01
        atr = context.get('atr', 0.001)
        volatility_factor = 1.0 / (atr * 10000)  # Inverse vol

        position_size = (base_risk * volatility_factor) / (entry_price * 100000)
        return position_size

# In config
{
  "position_sizing": {
    "method": "my_custom",  # Add to valid_methods
    "config": {}
  }
}
```

### Multiple Regime Thresholds

Adjust regime detector sensitivity:

```json
{
  "regime_detector": {
    "vol_spike_mult": 2.0,      // Higher = less sensitive to vol spikes
    "corr_spike_level": 0.60,   // Higher = less sensitive to correlation
    "dd_trigger_frac": 0.08,    // Higher = trigger on larger drawdowns
    "lookback": 90              // Longer window = smoother detection
  }
}
```

### Per-Cluster Limits

Set different limits for each asset class:

```json
{
  "cluster_var_caps": {
    "FOREX": 0.05,       // Max 5% VaR from all forex
    "METALS": 0.04,      // Max 4% VaR from metals
    "INDICES": 0.03,     // Max 3% VaR from indices
    "CRYPTO": 0.02       // Max 2% VaR from crypto
  },
  "cluster_es_caps": {
    "FOREX": 0.07,
    "METALS": 0.06,
    "INDICES": 0.05,
    "CRYPTO": 0.03
  }
}

{
  "symbol_clusters": {
    "EURUSD": "FOREX",
    "GBPUSD": "FOREX",
    "XAUUSD": "METALS",
    "XAGUSD": "METALS",
    "US30": "INDICES",
    "BTCUSD": "CRYPTO"
  }
}
```

## Best Practices

### 0. Start Conservative

First deployment:

```json
{
  "risk_management": {
    "limits": {
      "var_cap_frac": 0.05,      // Very conservative
      "es_cap_frac": 0.08,
      "delta_var_cap_frac": 0.01,
      "max_single_rc_frac": 0.15
    }
  },
  "position_sizing": {
    "method": "fixed_risk",
    "config": {
      "risk_percent": 0.5        // Half of normal
    }
  }
}
```

Gradually increase as system proves stable.

### 1. Always Use Regime Detection

Don't manually adjust limits. Let the regime detector tighten them automatically during stress.

```python
# ✓ Good
regime = detector.detect(returns_df, equity_curve)
report = governor.evaluate_add_position(..., regime=regime)

# ✗ Bad
if market_looks_scary:
    limits.var_cap_frac = 0.05  # Manual override
```

### 2. Respect the Decision

Don't override rejected trades or try to "work around" the governor.

```python
# ✓ Good
if report.decision == "REJECT":
    logger.warning(f"Trade rejected: {report.reason}")
    return

# ✗ Bad
if report.decision == "REJECT":
    # Try with smaller size...
    report2 = governor.evaluate_add_position(..., candidate_lots=lots * 0.5)
    # This defeats the purpose of incremental caps!
```

### 3. Use Cluster Limits for Multi-Asset

Group correlated symbols to prevent concentration in one asset class.

```python
symbol_to_cluster = {
    "EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX",
    "XAUUSD": "COMMODITIES", "XTIUSD": "COMMODITIES",
    "US30": "INDICES", "NAS100": "INDICES"
}

limits = RiskLimits(
    cluster_var_caps={"FOREX": 0.06, "COMMODITIES": 0.04, "INDICES": 0.04}
)
```

### 4. Combine Position Sizing with Allocation

Use PositionSizer for per-symbol base sizes, then RiskBudgetAllocator for portfolio balance.

```python
# Step 1: Per-symbol sizing (volatility-adjusted)
base_lots = {
    symbol: sizer.calculate_size(...)
    for symbol in symbols
}

# Step 2: Portfolio-level risk parity
target_lots = allocator.compute_target_lots(symbols, base_lots)
```

### 5. Log Risk Reports

Always log the full RiskReport for audit trails.

```python
report = governor.evaluate_add_position(...)

logger.info(f"""
Risk Report: {report.decision}
Reason: {report.reason}
Current VaR: ${report.current_var:,.2f}
New VaR: ${report.new_var:,.2f}
Delta VaR: ${report.delta_var:,.2f}
Risk Contributions: {report.rc_map_new}
""")
```

### 6. Backtest Your Risk Limits

Before live Use historical data to validate that your limits would have protected capital.

```python
## Test how often limits would have been hit
from apps.backtest import VectorizedBacktest
from apps.risk import RiskGovernor, RiskLimits

limits = RiskLimits(var_cap_frac=0.08, ...)
governor = RiskGovernor(mt5_client, limits)

rejected = 0
for trade in historical_trades:
    report = governor.evaluate_add_position(...)
    if report.decision == "REJECT":
        rejected += 1

print(f"Rejection rate: {rejected / len(historical_trades):.1%}")
# Aim for 5-15% rejection rate

# OR


# During backtest, track how often limits were hit
rejected_count = 0
total_signals = 0

for signal in backtest_signals:
    total_signals += 1
    report = governor.evaluate_add_position(...)

    if report.decision == "REJECT":
        rejected_count += 1
        logger.info(f"Historical rejection: {report.reason}")

print(f"Rejection rate: {rejected_count / total_signals:.1%}")
```

### 7. Monitor RC Imbalance

Periodically check if risk is concentrated in one position.

```python
# Check current risk contributions
equity = mt5_client.get_account_equity()
_, _, _, rc_map = governor._compute_portfolio_risk(
    positions=current_positions,
    equity=equity,
    eff=limits
)

for symbol, rc_pct in rc_map.items():
    if rc_pct > 0.20:  # More than 20% of risk
        logger.warning(f"{symbol} contributes {rc_pct:.1%} of portfolio risk!")

# Optionally rebalance
rebalance_deltas = governor.propose_rc_rebalance(
    positions=current_positions,
    target_rc_budget={s: 1/len(current_positions) for s in current_positions}
)
```

### 8. Test Edge Cases

Ensure the system handles:

- All positions closed (empty portfolio)
- Single position (no diversification)
- Highly correlated pairs
- Missing data for some symbols
- Extreme volatility spikes

---

## Troubleshooting

**Q: Governor always rejects trades with "inf" VaR**

**Root Cause**: Insufficient historical data for VaR calculation, commonly on demo accounts.

**Common Scenario**: MT5 demo accounts often have **NO daily (D1) historical data** available, causing VaR calculations to return infinity as a fail-safe.

**Solutions**:

1. **Use shorter timeframes** (Recommended for demo accounts):

   ```json
   {
     "risk_management": {
       "governor_config": {
         "timeframe": "H1",     // Hourly instead of daily
         "start_pos": 0,
         "end_pos": 500         // 500 hours ≈ 21 days
       },
       "regime_detector": {
         "timeframe": "H4"      // 4-hour for regime detection
       }
     },
     "position_sizing": {
       "config": {
         "atr_timeframe": "H4"  // 4-hour for ATR calculation
       }
     }
   }
   ```
2. **Reduce data requirements** (if D1 data is available):

   ```json
   {
     "governor_config": {
       "timeframe": "D1",
       "end_pos": 60          // Reduce from 500 to 60 days
     }
   }
   ```
3. **Verify data availability**:

   ```python
   df = mt5_client.get_bars("EURUSD", "D1", count=60, start_pos=0)
   print(f"Available D1 bars: {len(df)}")  # Should be ≥ 60

   # If empty, switch to H1/H4
   df_h1 = mt5_client.get_bars("EURUSD", "H1", count=500, start_pos=0)
   print(f"Available H1 bars: {len(df_h1)}")  # Should have data
   ```

**Trade-offs**:

- H1/H4 data: ✅ Works on demo, ✅ More frequent updates, ⚠️ More sensitive to short-term volatility
- D1 data: ✅ Smoother estimates, ✅ Less noise, ⚠️ May not be available on demo accounts

**Additional Checks**:

- Verify MT5 client returns valid 'Close' prices
- Ensure symbol_info has valid contract_size or tick_value
- Check that data has enough bars (≥ max(vol_lookback, corr_lookback))

**Q: Allocator returns same lots as input**

- Returns dataframe is likely empty or insufficient
- Check data quality and timeframe alignment
- Verify symbols exist in historical data

**Q: Regime always NORMAL despite volatility**

- Check returns_df has enough history (≥ lookback parameter)
- Verify equity_curve is a pandas Series
- Adjust detection thresholds (vol_spike_mult, corr_spike_level)

**Q: Margin check always fails**

- Implement get_margin_required() in MT5 client
- Or set max_margin_used_frac very high to disable

**Q: Position sizing returns 0.01 (minimum)**

- Check account_balance > 0
- Verify entry_price and stop_loss are valid
- For volatility method, ensure ATR is in context
- For Kelly, ensure win_rate, avg_win, avg_loss are provided

### Issue: Regime Always NORMAL Despite Volatility

**Cause**: Detection thresholds too high or insufficient data

**Solution**:

- Lower `vol_spike_mult` (try 1.5 instead of 1.8)
- Lower `corr_spike_level` (try 0.50 instead of 0.55)
- Ensure equity curve has enough history (>20 points)

### Issue: Position Sizing Returns 0.01 (Minimum)

**Cause**: Risk calculation error or missing parameters

**Solution**:

- For `fixed_risk`: Ensure signal has `stop_loss`
- For `volatility`: Ensure signal has `atr` in context
- For `kelly`: Provide `win_rate`, `avg_win`, `avg_loss`

```python
# Add ATR to signal (in strategy)
def get_signal(self, data, index):
    signal = {...}
    signal['atr'] = data.iloc[index]['atr_14']
    return signal
```

### Issue: Allocation Returns Same Lots as Input

**Cause**: Empty returns dataframe or correlation calculation error

**Solution**:

- Check D1 data is available for symbols
- Verify symbols are spelled correctly
- Check logs for "Insufficient data for regime detection"

### Issue: All Trades Rejected for "Delta VaR Cap"

**Cause**: Incremental caps too tight or existing positions too risky

**Solution**:

- Increase `delta_var_cap_frac` (e.g., 0.02 instead of 0.015)
- Reduce existing positions
- Check if regime is STRESS (tightens limits)

---

## Summary

The HaruQuant Risk Engine provides institutional-grade risk management through:

1. **Portfolio-level thinking** - Risk is a shared resource, not per-trade
2. **Multi-layer defense** - Regime detection → Allocation → Governance
3. **Mathematical rigor** - VaR, ES, risk contributions, correlation modeling
4. **Flexibility** - Multiple position sizing methods, soft + hard constraints
5. **Regime awareness** - Automatic tightening during stress periods
6. **Auditability** - Detailed reports for every decision

Use it to build trading systems that survive adverse conditions and scale across strategies.

---

## Usage Tests & Examples (Local)

These scripts live under `tests/usage/risk/` and are intended for hands-on learning with your local MT5 setup.
Most scripts connect to MT5 and use live data. Make sure MT5 is running and your default broker credentials
exist in the local DB.

### Usage Files Overview

1. `01_position_sizing.py` - Position sizing methods (live MT5)
2. `02_regime_detection.py` - Regime detection (live + synthetic), includes `main_actual()` bar-by-bar mode
3. `03_risk_allocation.py` - Risk budget allocation and rebalancing
4. `04_risk_governor.py` - Accept/reject scenarios and caps
5. `05_full_scenarios.py` - End-to-end workflows
6. `06_simple_single_strategy.py` - Single-strategy trading loop
7. `07_multi_strategy_portfolio.py` - Multi-strategy trading loop
8. `08_integrate_existing_system.py` - Wrapper pattern for integration

### Run Commands

```bash
python tests/usage/risk/01_position_sizing.py
python tests/usage/risk/02_regime_detection.py
python tests/usage/risk/03_risk_allocation.py
python tests/usage/risk/04_risk_governor.py
python tests/usage/risk/05_full_scenarios.py
python -m tests.usage.risk.06_simple_single_strategy
python -m tests.usage.risk.07_multi_strategy_portfolio
python -m tests.usage.risk.08_integrate_existing_system
```

### Notes

- These scripts are not unit tests; they are live usage demos.
- If MT5 data is limited, prefer `H1` timeframes and smaller lookbacks.
- You can customize symbols, limits, and timeframes directly in each script.

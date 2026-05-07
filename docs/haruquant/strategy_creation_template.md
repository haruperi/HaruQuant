# HaruQuant Strategy Creation Template v1.0

**Purpose:** Standardize how every HaruQuant strategy is created so simple signal strategies and complex stateful strategies can be built, tested, debugged, and run through the same engine conventions.

**Core rule:** every strategy must use `on_bar()` as the universal feature/signal-preparation layer. Complex strategies may also use `on_event()` for stateful trade management, but `on_event()` should consume precomputed `on_bar()` features/activators wherever possible.

---

## 1. Unified Strategy Lifecycle

```text
Validate Parameters
→ Initialize Strategy State
→ Calculate Features in on_bar()
→ Generate Signal Activators in on_bar()
→ Parse Simple Signals with get_signal()
→ Optional Stateful Management in on_event()
→ Return SignalDict or TradeAction objects
→ Risk Controls Approve/Reject
→ Execution Engine Executes Approved Actions
```

### Simple strategy lifecycle

```text
on_init()
→ on_bar()
→ get_signal()
→ SignalDict
```

### Complex stateful strategy lifecycle

```text
on_init()
→ on_bar()
→ on_event()
→ list[TradeAction]
```

---

## 2. Main Design Decision

Do not create separate incompatible standards for simple and complex strategies.

Instead, use one layered standard:

```text
on_bar() = market features + signal activators
get_signal() = simple bar signal parser
on_event() = stateful position/order/basket manager
```

This means:

- Simple strategies can directly set `entry_signal`, `exit_signal`, `pending_signal`, and `price` in `on_bar()`.
- Complex strategies can set activator columns in `on_bar()` such as `buy_setup_active`, `sell_add_active`, `buy_exit_active`, etc.
- `on_event()` then combines those activators with live/backtest context: positions, orders, PnL, side state, group IDs, and risk limits.

Final execution still belongs to the engine and risk controls, not the strategy.

---

## 3. Strategy Types Supported

| Strategy Type | on_bar | get_signal | on_event | Output |
|---|---:|---:|---:|---|
| EMA crossover | Yes | Yes | Optional | `SignalDict` |
| RSI mean reversion | Yes | Yes | Optional | `SignalDict` |
| Breakout | Yes | Yes | Optional | `SignalDict` |
| Pending order strategy | Yes | Yes | Optional | `SignalDict` |
| Martingale | Yes | Optional | Yes | `list[TradeAction]` |
| Pyramiding | Yes | Optional | Yes | `list[TradeAction]` |
| Trade decomposition | Yes | Optional | Yes | `list[TradeAction]` |
| Hedge/grid | Yes | Optional | Yes | `list[TradeAction]` |
| Multi-timeframe structure strategy | Yes | Optional | Yes | `list[TradeAction]` |

---

## 4. Required Strategy File Structure

For simple projects, one strategy file is acceptable:

```text
strategies/
  trend_following.py
  rsi_martingale.py
  pyramiding.py
  trade_decomposition.py
```

For production and generated strategies, prefer this structure:

```text
haruquant/
  strategies/
    <strategy_name>/
      __init__.py
      strategy.py
      config.py
      README.md
      tests/
        test_params.py
        test_on_bar.py
        test_get_signal.py
        test_no_lookahead.py
        test_on_event.py
        test_state_reset.py
        test_action_metadata.py
        test_risk_limits.py
```

Minimum tests for all strategies:

```text
test_params.py
test_on_bar.py
test_no_lookahead.py
```

Additional tests for complex strategies:

```text
test_on_event.py
test_state_reset.py
test_action_metadata.py
test_risk_limits.py
test_group_ids.py
```

---

## 5. Universal Strategy Contract

Every strategy must follow this shape:

```python
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy, SignalDict


class MyStrategy(BaseStrategy):
    strategy_name = "MyStrategy"
    strategy_type = "simple"  # simple | stateful | hybrid
    signal_schema_version = "1.0"
    action_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self._load_params()
        self._validate_params()

    def _load_params(self) -> None:
        self.symbol = self.params.get("symbol", "UNKNOWN")

    def _validate_params(self) -> None:
        pass

    def on_init(self) -> None:
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        return super().get_signal(data, index)
```

Complex strategies add:

```python
from services.strategy.stateful import StatefulStrategyMixin, StrategyContext, TradeAction


class MyComplexStrategy(StatefulStrategyMixin, BaseStrategy):
    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        return []
```

---

## 6. Required Standard Columns from on_bar()

Every `on_bar()` must guarantee these columns exist:

| Column | Type | Meaning |
|---|---:|---|
| `entry_signal` | int | `1 = buy`, `-1 = sell`, `0 = none` |
| `exit_signal` | int | `1 = exit buy`, `-1 = exit sell`, `0 = none` |
| `pending_signal` | int | `1 = buy stop`, `-1 = sell stop`, `2 = buy limit`, `-2 = sell limit` |
| `cancel_pending_signal` | int | Cancel pending order signal |
| `pending_signal_2` | int | Optional second pending leg |
| `cancel_pending_signal_2` | int | Optional cancel for second pending leg |
| `price` | float | Primary signal price |
| `price_2` | float | Secondary signal price |
| `stop_loss` | float | Optional stop loss |
| `take_profit` | float | Optional take profit |
| `signal_reason` | str | Human-readable signal reason |
| `setup_id` | str | Setup identifier |
| `group_id` | str | Basket/group identifier |

Helper:

```python
def _ensure_signal_columns(self, data: pd.DataFrame) -> pd.DataFrame:
    defaults = {
        "entry_signal": 0,
        "exit_signal": 0,
        "pending_signal": 0,
        "cancel_pending_signal": 0,
        "pending_signal_2": 0,
        "cancel_pending_signal_2": 0,
        "price": float("nan"),
        "price_2": float("nan"),
        "stop_loss": float("nan"),
        "take_profit": float("nan"),
        "signal_reason": "",
        "setup_id": "",
        "group_id": "",
    }
    for col, default in defaults.items():
        if col not in data.columns:
            data[col] = default
    return data
```

---

## 7. Standard Activator Columns for Complex Strategies

Complex strategies should create activator columns in `on_bar()`.

Recommended names:

```text
buy_setup_active
sell_setup_active
buy_add_active
sell_add_active
buy_exit_active
sell_exit_active
buy_pyramid_active
sell_pyramid_active
buy_martingale_active
sell_martingale_active
buy_decompose_active
sell_decompose_active
buy_trail_active
sell_trail_active
```

Activator columns answer:

```text
Is the market condition present?
```

`on_event()` answers:

```text
Given current positions, orders, basket PnL, state, and risk limits, what action should be proposed?
```

---

## 8. Standard on_bar() Template

```python
def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate indicators, features, signal columns, and event activators.
    This method must work for both simple and complex strategies.
    """
    data = data.copy()

    data = self._calculate_indicators(data)
    data = self._shift_features(data)
    data = self._ensure_signal_columns(data)
    data = self._generate_simple_signals(data)
    data = self._generate_event_activators(data)

    return data
```

Required helper methods:

```python
def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
    return data


def _shift_features(self, data: pd.DataFrame) -> pd.DataFrame:
    return data


def _generate_simple_signals(self, data: pd.DataFrame) -> pd.DataFrame:
    return data


def _generate_event_activators(self, data: pd.DataFrame) -> pd.DataFrame:
    return data
```

---

## 9. Lookahead Bias Rule

If a strategy executes at the current bar open, it must use only information available from the previous completed bar.

Standard rule:

```text
Signal used at bar N open must be based on bar N-1 or earlier.
```

Example:

```python
data["rsi_signal"] = data["rsi_14"].shift(1)
data["ema_fast_signal"] = data["ema_20"].shift(1)
data["ema_slow_signal"] = data["ema_50"].shift(1)
```

If a strategy deliberately trades at bar close, this must be documented in the README.

---

## 10. Standard get_signal() Template

`get_signal()` is for simple strategies and simple bar-level signals.

```python
def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
    row = data.iloc[index]

    entry = int(row.get("entry_signal", 0) or 0)
    exit_sig = int(row.get("exit_signal", 0) or 0)
    pending = int(row.get("pending_signal", 0) or 0)
    cancel = int(row.get("cancel_pending_signal", 0) or 0)
    pending_2 = int(row.get("pending_signal_2", 0) or 0)
    cancel_2 = int(row.get("cancel_pending_signal_2", 0) or 0)

    if (
        entry == 0
        and exit_sig == 0
        and pending == 0
        and cancel == 0
        and pending_2 == 0
        and cancel_2 == 0
    ):
        return None

    price = row.get("price")
    if pd.isna(price):
        price = row.get("close")

    price_2 = row.get("price_2")
    if pd.isna(price_2):
        price_2 = None

    stop_loss = row.get("stop_loss")
    if pd.isna(stop_loss):
        stop_loss = None

    take_profit = row.get("take_profit")
    if pd.isna(take_profit):
        take_profit = None

    return {
        "entry_signal": entry,
        "exit_signal": exit_sig,
        "pending_signal": pending,
        "cancel_pending_signal": cancel,
        "pending_signal_2": pending_2,
        "cancel_pending_signal_2": cancel_2,
        "price": float(price) if price is not None else None,
        "price_2": float(price_2) if price_2 is not None else None,
        "time": row.name,
        "reason": str(row.get("signal_reason", "Signal detected")),
        "stop_loss": float(stop_loss) if stop_loss is not None else None,
        "take_profit": float(take_profit) if take_profit is not None else None,
    }
```

---

## 11. Standard on_event() Template

Use `on_event()` only when the strategy needs stateful position/order/basket logic.

```python
def on_event(self, context: StrategyContext) -> list[TradeAction]:
    """
    Generate stateful trade action proposals.

    This method should not execute trades directly.
    It should only return TradeAction objects for the engine/risk layer.
    """
    if not self._should_process_event(context):
        return []

    actions: list[TradeAction] = []
    actions.extend(self._process_side("BUY", context))
    actions.extend(self._process_side("SELL", context))

    return self._post_process_actions(actions, context)
```

Event guard:

```python
def _should_process_event(self, context: StrategyContext) -> bool:
    return is_bar_close(context)
```

Side processor:

```python
def _process_side(self, side: str, context: StrategyContext) -> list[TradeAction]:
    positions = positions_for_side(context, side)
    side_key = side.lower()
    side_state = self.state.setdefault(side_key, self._empty_side_state())
    current_price = current_mid_price(context)

    if not positions:
        return self._initial_entry_actions(side, current_price, side_state, context)

    actions: list[TradeAction] = []
    actions.extend(self._exit_actions(side, current_price, positions, side_state, context))
    actions.extend(self._add_position_actions(side, current_price, positions, side_state, context))
    actions.extend(self._modify_position_actions(side, current_price, positions, side_state, context))
    return actions
```

---

## 12. Standard TradeAction Metadata

Every `TradeAction` should include enough information for auditing and grouping.

Recommended fields:

```text
action_type
symbol
side
volume
price
stop_loss
take_profit
ticket
setup_id
group_id
metadata
reason
```

Recommended metadata:

```python
metadata={
    "strategy_name": self.__class__.__name__,
    "strategy_id": self.strategy_id,
    "setup_type": "martingale",  # or pyramid/decomposition/grid/etc.
    "step": steps + 1,
    "source": "on_event",
    "signal_schema_version": self.signal_schema_version,
}
```

Rules:

- Always include `reason`.
- Use stable `setup_id` for related trades.
- Use stable `group_id` for basket management.
- Add step numbers for martingale/grid/averaging strategies.
- Add parent/child metadata for decomposition strategies.

---

## 13. Parameter Rules

All parameters must be loaded and validated in `__init__`.

```python
def __init__(self, params: Optional[Dict[str, Any]] = None):
    super().__init__(params)

    self.symbol = self.params.get("symbol", "UNKNOWN")
    self.initial_lot = float(self.params.get("initial_lot", 0.1))
    self.pip_value = float(self.params.get("pip_value", 0.0001))
    self.max_steps = int(self.params.get("max_steps", 6))
    self.max_lot = float(self.params.get("max_lot", 5.0))
    self.strategy_risk_controls = self.params.get("risk_controls", {})

    self._validate_params()
```

Validation example:

```python
def _validate_params(self) -> None:
    if self.initial_lot <= 0:
        raise ValueError("initial_lot must be positive.")
    if self.pip_value <= 0:
        raise ValueError("pip_value must be positive.")
    if self.max_steps <= 0:
        raise ValueError("max_steps must be positive.")
    if self.max_lot <= 0:
        raise ValueError("max_lot must be positive.")
```

Rules:

- Cast every parameter to the expected type.
- Validate every parameter that affects volume, distance, number of positions, risk, or exits.
- Use explicit defaults.
- Do not use raw user params directly inside trading logic.

---

## 14. State Rules

Complex strategies must use side-specific state.

```python
def on_init(self) -> None:
    self.state.setdefault("buy", self._empty_side_state())
    self.state.setdefault("sell", self._empty_side_state())


def _empty_side_state(self) -> dict:
    return {
        "last_price": 0.0,
        "steps": 0,
        "total_volume": 0.0,
        "active_group_id": None,
    }
```

Rules:

- State must be initialized in `on_init()`.
- State must reset when a basket/group closes.
- BUY and SELL state must be independent unless the strategy explicitly links them.
- State must be serializable later if live trading persistence is required.

---

## 15. Risk-Control Compatibility

Strategies propose actions. Risk controls approve, modify, or reject them.

Strategies may include local sanity checks, but must not bypass global risk controls.

Common risk-control fields:

```text
enabled
max_open_positions_per_strategy
max_layers_per_setup
max_martingale_step
max_total_lots
max_symbol_exposure
max_strategy_drawdown
allow_multiple_action_batches_per_event
```

Strategy-local overrides should be passed through params:

```python
"risk_controls": {
    "max_layers_per_setup": 6,
    "max_total_lots": 3.0,
    "max_symbol_exposure": 2.0,
}
```

---

## 16. Simple Strategy Template

```python
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy, SignalDict
from services.utils.logger import logger


class MySimpleStrategy(BaseStrategy):
    strategy_name = "MySimpleStrategy"
    strategy_type = "simple"
    signal_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.symbol = self.params.get("symbol", "UNKNOWN")
        self.fast_period = int(self.params.get("fast_period", 20))
        self.slow_period = int(self.params.get("slow_period", 50))
        self._validate_params()

    def _validate_params(self) -> None:
        if self.fast_period <= 0:
            raise ValueError("fast_period must be positive.")
        if self.slow_period <= 0:
            raise ValueError("slow_period must be positive.")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period.")

    def on_init(self) -> None:
        logger.info(
            "%s initialized for %s fast=%s slow=%s",
            self.strategy_name,
            self.symbol,
            self.fast_period,
            self.slow_period,
        )

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data = self._calculate_indicators(data)
        data = self._shift_features(data)
        data = self._ensure_signal_columns(data)
        data = self._generate_simple_signals(data)
        return data

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        data[f"sma_{self.fast_period}"] = data["close"].rolling(self.fast_period).mean()
        data[f"sma_{self.slow_period}"] = data["close"].rolling(self.slow_period).mean()
        return data

    def _shift_features(self, data: pd.DataFrame) -> pd.DataFrame:
        fast = f"sma_{self.fast_period}"
        slow = f"sma_{self.slow_period}"
        data[f"{fast}_signal"] = data[fast].shift(1)
        data[f"{slow}_signal"] = data[slow].shift(1)
        data[f"prev_{fast}_signal"] = data[f"{fast}_signal"].shift(1)
        data[f"prev_{slow}_signal"] = data[f"{slow}_signal"].shift(1)
        return data

    def _ensure_signal_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        defaults = {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "pending_signal_2": 0,
            "cancel_pending_signal_2": 0,
            "price": float("nan"),
            "price_2": float("nan"),
            "stop_loss": float("nan"),
            "take_profit": float("nan"),
            "signal_reason": "",
            "setup_id": "",
            "group_id": "",
        }
        for col, default in defaults.items():
            if col not in data.columns:
                data[col] = default
        return data

    def _generate_simple_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        fast = f"sma_{self.fast_period}_signal"
        slow = f"sma_{self.slow_period}_signal"
        prev_fast = f"prev_sma_{self.fast_period}_signal"
        prev_slow = f"prev_sma_{self.slow_period}_signal"

        buy = (data[fast] > data[slow]) & (data[prev_fast] <= data[prev_slow])
        sell = (data[fast] < data[slow]) & (data[prev_fast] >= data[prev_slow])

        data.loc[buy, "entry_signal"] = 1
        data.loc[buy, "price"] = data.loc[buy, "open"]
        data.loc[buy, "signal_reason"] = "Bullish moving average crossover"

        data.loc[sell, "entry_signal"] = -1
        data.loc[sell, "price"] = data.loc[sell, "open"]
        data.loc[sell, "signal_reason"] = "Bearish moving average crossover"

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        return super().get_signal(data, index)
```

---

## 17. Complex Stateful Strategy Template

```python
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy
from services.strategy.stateful import StatefulStrategyMixin, StrategyContext, TradeAction
from services.utils.logger import logger

from data.strategies.stateful_common import (
    current_mid_price,
    is_bar_close,
    positions_for_side,
)


class MyStatefulStrategy(StatefulStrategyMixin, BaseStrategy):
    strategy_name = "MyStatefulStrategy"
    strategy_type = "stateful"
    signal_schema_version = "1.0"
    action_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.symbol = self.params.get("symbol", "UNKNOWN")
        self.initial_lot = float(self.params.get("initial_lot", 0.1))
        self.min_step_pips = float(self.params.get("min_step_pips", 30.0))
        self.pip_value = float(self.params.get("pip_value", 0.0001))
        self.max_steps = int(self.params.get("max_steps", 6))
        self.max_lot = float(self.params.get("max_lot", 5.0))
        self.strategy_risk_controls = self.params.get("risk_controls", {})
        self._validate_params()

    def _validate_params(self) -> None:
        if self.initial_lot <= 0:
            raise ValueError("initial_lot must be positive.")
        if self.min_step_pips <= 0:
            raise ValueError("min_step_pips must be positive.")
        if self.pip_value <= 0:
            raise ValueError("pip_value must be positive.")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive.")
        if self.max_lot <= 0:
            raise ValueError("max_lot must be positive.")

    def on_init(self) -> None:
        self.state.setdefault("buy", self._empty_side_state())
        self.state.setdefault("sell", self._empty_side_state())
        logger.info("%s initialized for %s", self.strategy_name, self.symbol)

    def _empty_side_state(self) -> dict:
        return {
            "last_price": 0.0,
            "steps": 0,
            "total_volume": 0.0,
            "active_group_id": None,
        }

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data = self._calculate_indicators(data)
        data = self._shift_features(data)
        data = self._ensure_signal_columns(data)
        data = self._generate_event_activators(data)
        return data

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        return data

    def _shift_features(self, data: pd.DataFrame) -> pd.DataFrame:
        return data

    def _ensure_signal_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        defaults = {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "pending_signal_2": 0,
            "cancel_pending_signal_2": 0,
            "price": float("nan"),
            "price_2": float("nan"),
            "stop_loss": float("nan"),
            "take_profit": float("nan"),
            "signal_reason": "",
            "setup_id": "",
            "group_id": "",
            "buy_setup_active": False,
            "sell_setup_active": False,
            "buy_add_active": False,
            "sell_add_active": False,
            "buy_exit_active": False,
            "sell_exit_active": False,
        }
        for col, default in defaults.items():
            if col not in data.columns:
                data[col] = default
        return data

    def _generate_event_activators(self, data: pd.DataFrame) -> pd.DataFrame:
        return data

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not self._should_process_event(context):
            return []

        actions: list[TradeAction] = []
        actions.extend(self._process_side("BUY", context))
        actions.extend(self._process_side("SELL", context))
        return self._post_process_actions(actions, context)

    def _should_process_event(self, context: StrategyContext) -> bool:
        return is_bar_close(context)

    def _process_side(self, side: str, context: StrategyContext) -> list[TradeAction]:
        positions = positions_for_side(context, side)
        side_state = self.state.setdefault(side.lower(), self._empty_side_state())
        current_price = current_mid_price(context)

        if not positions:
            return self._initial_entry_actions(side, current_price, side_state, context)

        actions: list[TradeAction] = []
        actions.extend(self._exit_actions(side, current_price, positions, side_state, context))
        actions.extend(self._add_position_actions(side, current_price, positions, side_state, context))
        actions.extend(self._modify_position_actions(side, current_price, positions, side_state, context))
        return actions

    def _initial_entry_actions(self, side: str, current_price: float, side_state: dict, context: StrategyContext) -> list[TradeAction]:
        return []

    def _exit_actions(self, side: str, current_price: float, positions, side_state: dict, context: StrategyContext) -> list[TradeAction]:
        return []

    def _add_position_actions(self, side: str, current_price: float, positions, side_state: dict, context: StrategyContext) -> list[TradeAction]:
        return []

    def _modify_position_actions(self, side: str, current_price: float, positions, side_state: dict, context: StrategyContext) -> list[TradeAction]:
        return []

    def _post_process_actions(self, actions: list[TradeAction], context: StrategyContext) -> list[TradeAction]:
        return actions

    def _make_group_id(self, context: StrategyContext, side: str, setup_type: str) -> str:
        return f"{context.strategy_id}:{context.symbol}:{side}:{setup_type}"
```

---

## 18. Martingale Strategy Standard

Required parameters:

```text
rsi_period or trigger_period
entry_trigger
initial_lot
multiplier
min_step_pips
target_profit
pip_value
max_lot
max_steps
```

Required side state:

```python
{
    "last_price": 0.0,
    "total_volume": 0.0,
    "steps": 0,
    "active_group_id": None,
}
```

Required rules:

- Must cap max steps.
- Must cap max lot.
- Must define basket exit logic.
- Must reset side state after basket close.
- Must attach martingale step metadata.
- Must support risk-control limits.

---

## 19. Pyramiding Strategy Standard

Required parameters:

```text
fast_ma_period
slow_ma_period
initial_lot
lot_divisor or add_lot_model
min_step_pips
trailing_sl_pips
pip_value
max_positions_per_side
```

Required rules:

- Add only when the basket is profitable.
- Add only when trend remains confirmed.
- Add only after minimum step distance.
- Cap max positions per side.
- Move SL or define another risk-locking rule.

Required action types:

```text
OPEN
MODIFY_SL
```

---

## 20. Trade Decomposition Strategy Standard

Required parameters:

```text
rsi_period or trigger_period
initial_lot
vol_increase
vol_decrease
trade_distance
trail_points
child_take_profit_pips
pip_value
```

Required action types:

```text
OPEN
REDUCE
CLOSE
MODIFY_TP
MOVE_TO_BREAKEVEN
```

Required rules:

- Parent and child trades must be identified in metadata.
- Partial close volume must not exceed open position volume.
- Group ID must remain stable across the decomposition cycle.
- Remaining positions must be moved or managed according to deterministic rules.

---

## 21. Multi-Timeframe Strategy Standard

Multi-timeframe strategies must explicitly define:

```text
execution_timeframe
signal_timeframe
filter_timeframe
higher_timeframe
lower_timeframe
```

Rules:

- The execution timeframe controls the event loop.
- Higher timeframe values must only update after the higher timeframe candle closes.
- Higher timeframe columns must include timeframe in the name.
- All alignment must avoid lookahead bias.

Example column names:

```text
h1_trend_direction
h1_structure_high
m5_entry_trigger
m5_retest_active
```

---

## 22. Strategy README Template

```md
# <StrategyName>

## Strategy Type

simple | stateful | hybrid

## Purpose

<Brief description>

## Market Assumption

<Trend following, mean reversion, volatility breakout, basket recovery, etc.>

## Entry Logic

- BUY:
- SELL:

## Exit Logic

- Exit BUY:
- Exit SELL:

## Position Management

<For complex strategies: martingale, pyramid, decomposition, hedge, grid, etc.>

## Parameters

| Parameter | Type | Default | Description |
|---|---:|---:|---|
| symbol | str | UNKNOWN | Trading symbol |
| initial_lot | float | 0.1 | Initial volume |

## Signal Columns

| Column | Description |
|---|---|
| entry_signal | Buy/sell signal |
| exit_signal | Exit signal |

## Event Activator Columns

| Column | Description |
|---|---|
| buy_setup_active | BUY setup condition |
| sell_setup_active | SELL setup condition |

## TradeAction Types Used

- OPEN
- CLOSE
- MODIFY_SL

## Risk Controls

- max_open_positions_per_strategy
- max_layers_per_setup
- max_total_lots
- max_strategy_drawdown

## Lookahead Bias Handling

Explain what is shifted and when signals are executed.

## Tests

```bash
pytest haruquant/strategies/<strategy_name>/tests/
```
```

---

## 23. Prompt for Creating a New Strategy

Use this prompt with coding agents:

```text
You are implementing one HaruQuant trading strategy.

Follow HaruQuant Strategy Creation Template v1.0 exactly.

Strategy name:
<STRATEGY_NAME>

Strategy type:
simple | stateful | hybrid

Market logic:
<DESCRIBE MARKET EDGE>

Entry logic:
<BUY/SELL CONDITIONS>

Exit logic:
<EXIT CONDITIONS>

Position management logic:
<MARTINGALE/PYRAMIDING/DECOMPOSITION/GRID/NONE>

Parameters:
<LIST PARAMS WITH TYPES AND DEFAULTS>

Risk controls:
<LIST RISK LIMITS>

Required implementation rules:
1. Inherit from BaseStrategy.
2. If stateful, also use StatefulStrategyMixin.
3. Implement on_init().
4. Implement on_bar() for features, signal columns, and activators.
5. Implement get_signal() for simple signal output or safely inherit the base parser.
6. Implement on_event() only if stateful trade management is needed.
7. Never execute trades directly from the strategy.
8. Return SignalDict or list[TradeAction], depending on strategy type.
9. Validate all parameters.
10. Avoid lookahead bias.
11. Use setup_id/group_id for multi-position logic.
12. Add reason and metadata to every TradeAction.
13. Add tests for params, on_bar, no-lookahead, on_event, state reset, risk limits, and metadata.

Return the full implementation file by file.
```

---

## 24. Definition of Done

A strategy is complete only when:

```text
1. It inherits from BaseStrategy.
2. It implements on_init().
3. It implements on_bar().
4. on_bar() always returns standard signal columns.
5. Parameters are loaded and validated.
6. Indicator values are shifted when needed to avoid lookahead bias.
7. Simple strategies return SignalDict through get_signal().
8. Complex strategies return list[TradeAction] through on_event().
9. No strategy executes trades directly.
10. Multi-position strategies use setup_id/group_id.
11. TradeAction objects include reason and metadata.
12. Strategy-local risk_controls are supported where needed.
13. Tests exist.
14. README exists.
15. It can run through Portfolio.run().
```

---

## 25. Migration Path for Current HaruQuant Strategies

### Step 1: Keep the current BaseStrategy

The current `BaseStrategy` already provides the right foundation: `on_init()`, `on_bar()`, `get_signal()`, signal columns, helper methods, and optional event hooks.

### Step 2: Expand the simple template

Add these columns to the simple strategy template:

```text
pending_signal_2
cancel_pending_signal_2
stop_loss
take_profit
signal_reason
setup_id
group_id
```

### Step 3: Do not force complex strategies into get_signal()

Martingale, pyramiding, decomposition, hedge, and grid strategies should keep using `on_event()`.

### Step 4: Gradually move indicator calculations into on_bar()

Current complex strategies can continue working, but the target should be:

```text
Before:
on_event() calculates indicators and manages positions

After:
on_bar() calculates indicators and activators
on_event() manages positions using activators + context
```

### Step 5: Extend StrategyContext later

To make the standard cleaner, add the latest signal row to `StrategyContext`:

```python
signal_row: dict | None
signal_features: dict | None
```

Then `on_event()` can consume `on_bar()` outputs directly.

---

## 26. Final Rule

```text
on_bar() creates market truth.
get_signal() converts simple market truth into SignalDict.
on_event() converts market truth + portfolio state into TradeAction objects.
risk controls decide whether those actions are allowed.
execution engine performs approved actions.
```

This keeps simple strategies simple, while supporting advanced stateful strategies without breaking HaruQuant's architecture.

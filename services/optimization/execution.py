"""
Optimization execution helpers built on the trading engine.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Any, Dict, Type, cast

import pandas as pd

from services.analytics import drawdowns, metrics, ratios, returns
from services.strategy import BaseStrategy


def load_strategy_from_path(path: str, class_name: str) -> Type[BaseStrategy]:
    """Dynamically load a strategy class from a file path."""
    spec = importlib.util.spec_from_file_location("dynamic_strategy", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Type[BaseStrategy], getattr(module, class_name))


def normalize_engine_type(engine_type: str) -> str:
    raw = str(engine_type or "vectorized").strip().lower().replace("-", "_")
    if raw == "vectorised":
        raw = "vectorized"
    if raw not in {"vectorized", "event_driven"}:
        raise ValueError(f"Unsupported engine_type: {engine_type}")
    return raw


def _infer_trading_timeframe(data: pd.DataFrame) -> str:
    if not isinstance(data.index, pd.DatetimeIndex) or len(data.index) < 2:
        return "M1"
    deltas = data.index.to_series().diff().dropna()
    if deltas.empty:
        return "M1"
    seconds = int(max(60, deltas.median().total_seconds()))
    mapping = {
        60: "M1",
        300: "M5",
        900: "M15",
        1800: "M30",
        3600: "H1",
        14400: "H4",
        86400: "D1",
        604800: "W1",
    }
    return mapping.get(seconds, "M1")


def _seed_engine_account(engine: Any, initial_balance: float) -> None:
    account = engine.account_info()
    account["balance"] = float(initial_balance)
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = float(initial_balance)
    account["margin"] = 0.0
    account["margin_free"] = float(initial_balance)
    account["margin_level"] = 0.0


def _ensure_engine_symbol(engine: Any, symbol_name: str):
    for row in engine.state.trading_symbols:
        if str(getattr(row, "name", "") or "") == str(symbol_name):
            return row
    symbol_row = engine.client.symbol_info(symbol_name)
    if symbol_row is None:
        raise ValueError(f"Symbol info unavailable for {symbol_name}")
    engine.state.trading_symbols.append(symbol_row)
    return symbol_row


def _trade_records_to_frame(records) -> pd.DataFrame:
    rows = [record.to_dict() for record in records or []]
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    for col in ("open_time", "close_time"):
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame


def _equity_points_to_series(points, initial_balance: float) -> pd.Series:
    if not points:
        return pd.Series([float(initial_balance)])

    rows = [point.to_dict() for point in points]
    frame = pd.DataFrame(rows)
    if "timestamp" not in frame.columns or "equity" not in frame.columns:
        return pd.Series([float(initial_balance)])

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp")
    if frame.empty:
        return pd.Series([float(initial_balance)])

    equity_series = pd.Series(
        frame["equity"].astype(float).to_numpy(),
        index=frame["timestamp"],
    )
    first_ts = equity_series.index[0]
    initial_point = pd.Series([float(initial_balance)], index=[first_ts])
    return pd.concat([initial_point, equity_series]).sort_index(kind="mergesort")


@dataclass
class EngineOptimizationResult:
    """Small optimization-facing result contract built from Engine outputs."""

    trades: pd.DataFrame
    equity_curve: pd.Series
    initial_balance: float
    final_balance: float
    processed_ticks: int = 0
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0

    def summary(self) -> Dict[str, float]:
        return {
            "total_trades": float(self.total_trades),
            "win_rate": float(self.win_rate),
            "profit_factor": float(self.profit_factor),
            "sharpe_ratio": float(self.sharpe_ratio),
            "sortino_ratio": float(self.sortino_ratio),
            "calmar_ratio": float(self.calmar_ratio),
            "total_return_pct": float(self.total_return_pct),
            "max_drawdown_pct": float(self.max_drawdown_pct),
            "final_balance": float(self.final_balance),
            "processed_ticks": float(self.processed_ticks),
        }


def _build_result(
    engine: Any,
    processed_ticks: int,
    initial_balance: float,
) -> EngineOptimizationResult:
    trades_df = _trade_records_to_frame(engine.get_completed_trades())
    equity_series = _equity_points_to_series(
        engine.get_equity_curve(),
        initial_balance,
    )
    if len(equity_series) == 0:
        equity_series = pd.Series([float(initial_balance)])

    ret_series = returns.daily_returns(equity_series)
    cagr_value = returns.cagr(equity_series)
    max_dd_pct = drawdowns.max_strategy_drawdown_percent(equity_series)

    return EngineOptimizationResult(
        trades=trades_df,
        equity_curve=equity_series,
        initial_balance=float(initial_balance),
        final_balance=float(equity_series.iloc[-1]),
        processed_ticks=int(processed_ticks),
        total_trades=int(metrics.total_trades(trades_df)) if not trades_df.empty else 0,
        win_rate=float(metrics.win_rate(trades_df)) if not trades_df.empty else 0.0,
        profit_factor=float(ratios.profit_factor(trades_df)) if not trades_df.empty else 0.0,
        sharpe_ratio=float(ratios.sharpe_ratio(ret_series)) if len(ret_series) >= 2 else 0.0,
        sortino_ratio=float(ratios.sortino_ratio(ret_series, annualize=False)) if len(ret_series) >= 2 else 0.0,
        calmar_ratio=float(ratios.calmar_ratio(cagr_value, max_dd_pct)),
        total_return_pct=float(((equity_series.iloc[-1] - float(initial_balance)) / float(initial_balance)) * 100.0)
        if float(initial_balance) > 0.0
        else 0.0,
        max_drawdown_pct=float(max_dd_pct),
    )


def run_strategy_backtest(
    strategy_class: Type[BaseStrategy],
    data: pd.DataFrame,
    symbol: str,
    params: Dict[str, Any],
    initial_balance: float,
    engine_type: str = "vectorised",
    position_size: float = 0.1,
) -> EngineOptimizationResult:
    """Run one optimization candidate through the trading engine."""
    import haruquant as hqt

    # Build a centralized configuration overrides
    # Following the example_17 pattern: hqt.Portfolio.run(overrides)
    overrides = {
        "engine_type": normalize_engine_type(engine_type),
        "backend": "sim",
        "account": {
            "initial_balance": float(initial_balance),
        },
        "data": {
            "symbols": [symbol],
            # These are required by SimulationConfig but will be ignored 
            # because we pass preloaded_data
            "source": "metatrader", 
            "timeframe": _infer_trading_timeframe(data),
            "start": data.index[0],
            "end": data.index[-1],
            "warmup_start": data.index[0],
        },
        "strategy": {
            "name": strategy_class.__name__ if hasattr(strategy_class, "__name__") else str(strategy_class),
            "params": params,
        },
        "execution": {
            "position_size": {
                "type": "fixed_lot",
                "lot_size": float(position_size),
            }
        },
        "preloaded_data": data, # Our new feature to avoid reloading
    }

    # Execute via the centralized HaruQuant API
    portfolio = hqt.Portfolio.run(overrides)
    
    # Map back to EngineOptimizationResult for compatibility with optimization methods
    analytics = portfolio.analytics()
    metrics_all = analytics.get("metrics", {}).get("all", {})
    ratios_all = analytics.get("ratios", {}).get("all", {})
    summary = analytics.get("summary", {})
    
    # Result mapping
    result = portfolio.result()
    return EngineOptimizationResult(
        trades=result["trades"],
        equity_curve=result["equity_curve"]["equity"] if not result["equity_curve"].empty else pd.Series([initial_balance]),
        initial_balance=float(initial_balance),
        final_balance=portfolio.final_value,
        processed_ticks=int(portfolio.metadata().get("processed_ticks", 0)),
        total_trades=int(metrics_all.get("total_trades", 0)),
        win_rate=float(metrics_all.get("win_rate", 0.0)),
        profit_factor=float(ratios_all.get("profit_factor", 0.0)),
        sharpe_ratio=float(ratios_all.get("sharpe_ratio", 0.0)),
        sortino_ratio=float(ratios_all.get("sortino_ratio", 0.0)),
        calmar_ratio=float(ratios_all.get("calmar_ratio", 0.0)),
        total_return_pct=portfolio.total_return(),
        max_drawdown_pct=float(summary.get("max_drawdown_pct", 0.0)),
    )


def run_strategy_backtest_from_path(
    strategy_path: str,
    class_name: str,
    data: pd.DataFrame,
    symbol: str,
    params: Dict[str, Any],
    initial_balance: float,
    engine_type: str = "vectorised",
    position_size: float = 0.1,
) -> EngineOptimizationResult:
    strategy_class = load_strategy_from_path(strategy_path, class_name)
    return run_strategy_backtest(
        strategy_class=strategy_class,
        data=data,
        symbol=symbol,
        params=params,
        initial_balance=initial_balance,
        engine_type=engine_type,
        position_size=position_size,
    )

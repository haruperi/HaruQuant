"""Simulator session runtime and helpers."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import asdict, replace
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.api.legacy.websocket import backtest_log_manager
from apps.mt5 import get_mt5_api
from apps.mt5.client import MT5Client
from apps.risk.core import PortfolioStateEngine
from apps.risk.core.governance_engine import GovernanceEngine
from apps.risk.core.portfolio_risk_engine import PortfolioRiskEngine
from apps.risk.core.recommendation_engine import RecommendationEngine
from apps.risk.core.risk_scorecard_engine import RiskScorecardEngine
from apps.risk.core.risk_snapshot_engine import RiskSnapshotEngine
from apps.risk.core.timeline_reconstructor import TimelineReconstructor
from apps.risk.limits import RiskLimits
from apps.risk.metrics import RiskSnapshot
from apps.risk.metrics.math import extract_currency_exposure
from apps.risk.models import PortfolioState, PositionState
from apps.risk.scoring import RiskScorecard
from apps.risk.simulation import HypotheticalOrderAction, ReplayFrame, WhatIfEngine
from apps.risk.storage import RiskRepository, RiskSnapshotStore
from apps.simulation.serializers import (
    _apply_leverage_override_to_state,
    _estimate_state_margin_used,
    _serialize_governance_report,
    _serialize_recommendation_batch,
)
from apps.sqlite.database_operations import DatabaseManager
from apps.trading import Engine, core
from apps.utils.data_validator import DataValidator
from apps.utils.logger import logger

from backend.api.legacy.routes.backtest import _generate_ticks_for_backtest, _resolve_modelling

mt5 = get_mt5_api()
FX_CLUSTER_CURRENCIES = {"USD", "EUR", "JPY", "CAD", "AUD", "NZD", "CHF", "GBP"}

def _object_to_dict(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    try:
        return dict(vars(value))
    except Exception:
        return {}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, (int, float)):
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        return numeric
    return value


def _json_safe_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(key): _json_safe_value(value)
        for key, value in payload.items()
    }


def _extract_symbol_currency_clusters(symbol: str, spec: Any = None) -> List[str]:
    payload = _object_to_dict(spec)
    base = str(payload.get("currency_base") or payload.get("base_currency") or "").upper()
    profit = str(payload.get("currency_profit") or payload.get("profit_currency") or "").upper()
    token = str(symbol).upper()
    if not base and len(token) >= 6 and token[:6].isalpha():
        base = token[:3]
    if not profit and len(token) >= 6 and token[:6].isalpha():
        profit = token[3:6]
    clusters: List[str] = []
    for currency in (base, profit):
        if currency in FX_CLUSTER_CURRENCIES and currency not in clusters:
            clusters.append(currency)
    return clusters


def _build_symbol_currency_clusters(symbols: List[str], symbol_specs: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        str(symbol): _extract_symbol_currency_clusters(symbol, symbol_specs.get(symbol))
        for symbol in symbols
    }


def _default_currency_cluster_var_caps(limit_frac: float) -> Dict[str, float]:
    if limit_frac <= 0.0:
        return {}
    return {currency: float(limit_frac) for currency in sorted(FX_CLUSTER_CURRENCIES)}


class _EngineSimulatorFacade:
    def __init__(self, engine: Engine):
        self._simulator = engine
        self.engine = engine
        from apps.trading.trade import Trade
        self.trade_api = Trade(api=self.engine)

    @property
    def _positions_data(self) -> Dict[int, Any]:
        return {
            int(getattr(pos, "ticket", getattr(pos, "position_id", 0)) or 0): pos
            for pos in self.engine.state.trading_deals
        }

    @property
    def _orders_data(self) -> Dict[int, Any]:
        return {
            int(getattr(order, "ticket", 0) or 0): order
            for order in self.engine.state.trading_orders
        }

    @property
    def _account_data(self):
        return self.engine.account_info()

    def monitor_positions(self):
        return self.engine.monitor_positions(verbose=False)

    def monitor_account(self, _totals=None):
        return self.engine.monitor_account(verbose=False)

    def modify_position(self, pos_data: dict, new_sl=None, new_tp=None):
        ticket = int(pos_data.get("ticket") or pos_data.get("position_id") or pos_data.get("identifier") or 0)
        symbol = str(pos_data.get("symbol", "") or "")
        result = self.trade_api.PositionModify(
            symbol=symbol,
            ticket=ticket,
            sl=float(new_sl or 0.0),
            tp=float(new_tp or 0.0),
        )
        return int(getattr(result, "retcode", 0) or 0) == 10009

    def close_position(self, pos_data: dict, reason: str = "manual"):
        symbol_name = str(pos_data.get("symbol", "") or "")
        ticket = int(pos_data.get("ticket") or pos_data.get("position_id") or pos_data.get("identifier") or 0)
        result = self.trade_api.PositionClose(
            symbol=symbol_name,
            ticket=ticket,
        )
        return int(getattr(result, "retcode", 0) or 0) in (10008, 10009)

    def order_modify(self, order_data: dict, new_open_price: float, new_sl: float, new_tp: float):
        result = self.trade_api.OrderModify(
            ticket=int(order_data.get("ticket") or 0),
            price=float(new_open_price or 0.0),
            sl=float(new_sl or 0.0),
            tp=float(new_tp or 0.0),
        )
        return int(getattr(result, "retcode", 0) or 0) == 10009

    def order_delete(self, order_data: dict):
        result = self.trade_api.OrderDelete(
            ticket=int(order_data.get("ticket") or 0)
        )
        return int(getattr(result, "retcode", 0) or 0) == 10009


class _SimulatorPortfolioStateRiskAdapter:
    def __init__(self, state: PortfolioState):
        self._state = state

    def get_account_equity(self):
        return float(self._state.account.equity)

    def get_account_currency(self):
        return str(self._state.account.currency or "USD")

    def get_peak_equity(self):
        peak_equity = self._state.metadata.get("peak_equity")
        if peak_equity is None:
            return None
        return float(peak_equity)

    def get_symbol_info(self, symbol):
        spec = self._state.symbols[symbol]
        return {
            "trade_contract_size": spec.contract_size,
            "trade_tick_value": spec.tick_value,
            "trade_tick_size": spec.tick_size,
        }

    def get_margin_required(self, symbol, lots):
        try:
            spec = self._state.symbols.get(symbol)
            market = self._state.markets.get(symbol)
            if spec is None or market is None or market.bars.empty:
                return None

            bars = market.bars
            close_column = "close" if "close" in bars.columns else "Close"
            if close_column not in bars.columns:
                return None
            last_close = float(bars[close_column].iloc[-1] or 0.0)
            contract_size = float(spec.contract_size or 0.0)
            leverage = float(
                self._state.account.metadata.get("leverage")
                or self._state.metadata.get("account_leverage")
                or 0.0
            )
            if contract_size <= 0.0 or last_close <= 0.0 or leverage <= 0.0:
                return None
            notional = abs(float(lots)) * contract_size * last_close
            return notional / leverage
        except Exception:
            return None

    def get_bars(self, symbol, timeframe, count=100, start_pos=0):
        market = self._state.markets.get(symbol)
        if market is None:
            return None
        bars = market.bars.copy()
        if "Close" in bars.columns and "close" not in bars.columns:
            bars = bars.rename(columns={"Close": "close"})
        if start_pos > 0:
            bars = bars.iloc[start_pos:]
        if count is not None and count > 0:
            bars = bars.tail(int(count))
        return bars


class SimulatorSession:
    def __init__(self, session_id: int, config: Dict[str, Any], db: DatabaseManager):
        self.session_id = session_id
        self.config = dict(config)
        self.db = db
        self.engine = Engine(backend="sim")
        self.simulator = _EngineSimulatorFacade(self.engine)
        from apps.trading.trade import Trade
        self.trade_api = Trade(api=self.engine)
        self.symbols = [
            s.strip().upper()
            for s in str(self.config.get("symbol", "") or "").split(",")
            if s.strip()
        ] or ["EURUSD"]
        self.speed_multiplier = float(self.config.get("speed_multiplier", 1.0) or 1.0)
        self.current_bar_index = int(self.config.get("current_bar_index", 0) or 0)
        self.total_bars = 0
        self.visible_start_bar_index = 0
        self.visible_start_tick_index = 0
        self.symbol_digits = 5
        self.paused = False
        self.strategy = None
        self.strategies_by_symbol: Dict[str, Any] = {}
        self.replay_trades = []
        self.data = None
        self.tick_data = None
        self.data_by_symbol: Dict[str, Any] = {}
        self.symbol_digits_by_symbol: Dict[str, int] = {}
        self.current_market_by_symbol: Dict[str, Dict[str, Any]] = {}
        self.current_bar_index_by_symbol: Dict[str, int] = {}
        self._bar_first_tick_index: Dict[tuple[str, int], int] = {}
        self.risk_state_engine = PortfolioStateEngine()
        self.risk_snapshot_engine = RiskSnapshotEngine()
        self.risk_scorecard_engine = RiskScorecardEngine()
        self.recommendation_engine = RecommendationEngine(
            snapshot_engine=self.risk_snapshot_engine,
            scorecard_engine=self.risk_scorecard_engine,
        )
        self.what_if_engine = WhatIfEngine(
            snapshot_engine=self.risk_snapshot_engine,
            scorecard_engine=self.risk_scorecard_engine,
            recommendation_engine=self.recommendation_engine,
        )
        self.timeline_reconstructor = TimelineReconstructor()
        self.risk_repository = RiskRepository(self.db)
        self.risk_snapshot_store = RiskSnapshotStore(self.risk_repository)
        self.latest_risk_state: Optional[PortfolioState] = None
        self.latest_risk_snapshot: Optional[RiskSnapshot] = None
        self.latest_risk_scorecard: Optional[RiskScorecard] = None
        self.latest_recommendation_batch = None
        self.latest_regime_report = None
        self.previous_regime_state = None
        self.timeline_signature = "timestamp:empty"
        self.risk_run_id: Optional[int] = self._parse_optional_int(
            self.config.get("risk_run_id")
        )
        self.latest_risk_snapshot_id: Optional[int] = None
        self.latest_risk_replay_frame_id: Optional[int] = None
        self._seed_account()
        self._ensure_symbols()

    @staticmethod
    def _parse_optional_int(value: Any) -> Optional[int]:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _seed_account(self):
        initial_balance = float(self.config.get("initial_balance", 10000.0) or 10000.0)
        requested_leverage = self.config.get("leverage", 400)
        try:
            leverage = int(requested_leverage)
        except (TypeError, ValueError):
            leverage = 400
        if leverage <= 0:
            leverage = 0
        account = self.engine.account_info()
        account["balance"] = initial_balance
        account["credit"] = 0.0
        account["profit"] = 0.0
        account["equity"] = initial_balance
        account["margin"] = 0.0
        account["margin_free"] = initial_balance
        account["margin_level"] = 0.0
        account["commission"] = float(self.config.get("commission", 7.0) or 7.0)
        account["leverage"] = leverage if leverage > 0 else 0
        account["currency"] = str(account.get("currency") or account.get("currency_code") or "USD")
        self.engine.state.execution_settings = core.DotDict(
            {
                "slippage_model": str(self.config.get("slippage_type", "fixed") or "fixed"),
                "slippage_points": float(self.config.get("slippage", 0.0) or 0.0),
                "slippage_min": float(self.config.get("slippage_min", 0.0) or 0.0),
                "slippage_max": float(self.config.get("slippage_max", 0.0) or 0.0),
            }
        )
        self._configure_margin_tier_policy()

    def _configure_margin_tier_policy(self):
        leverage = float(self.engine.account_info().get("leverage", 0.0) or 0.0)
        self.engine.state.execution_settings.margin_tier_policy = core.DotDict(
            {
                "enabled": leverage >= 1000.0,
                "threshold_notional": 500000.0,
                "base_leverage": 1000.0,
                "excess_leverage": 500.0,
            }
        )

    def apply_mt5_account_defaults(self):
        requested_leverage = self.config.get("leverage", 400)
        try:
            leverage = int(requested_leverage)
        except (TypeError, ValueError):
            leverage = 400
        if leverage > 0:
            return

        try:
            account_info = self.engine.client.account_info()
        except Exception:
            account_info = None

        if account_info is None:
            return

        row = account_info._asdict() if hasattr(account_info, "_asdict") else {}
        mt5_leverage = row.get("leverage")
        try:
            effective_leverage = int(mt5_leverage)
        except (TypeError, ValueError):
            effective_leverage = 0
        if effective_leverage > 0:
            self.config["leverage"] = effective_leverage
            account = self.engine.account_info()
            account["leverage"] = effective_leverage
        self._configure_margin_tier_policy()

    def _ensure_symbol(self, symbol_name: str):
        for row in self.engine.state.trading_symbols:
            if str(getattr(row, "name", "") or "") == symbol_name:
                digits = int(getattr(row, "digits", 5) or 5)
                self.symbol_digits = digits
                self.symbol_digits_by_symbol[symbol_name] = digits
                return row
        symbol_info = self.engine.client.symbol_info(symbol_name)
        if symbol_info is None:
            raise ValueError(f"Symbol info unavailable for {symbol_name}")
        self.engine.state.trading_symbols.append(symbol_info)
        digits = int(getattr(symbol_info, "digits", 5) or 5)
        self.symbol_digits = digits
        self.symbol_digits_by_symbol[symbol_name] = digits
        return symbol_info

    def _ensure_symbols(self):
        for symbol_name in self.symbols:
            self._ensure_symbol(symbol_name)

    def set_strategy(self, strategy_instance):
        self.strategy = strategy_instance
        self.strategies_by_symbol = {}
        if hasattr(self.strategy, "on_init"):
            self.strategy.on_init()

    def set_strategy_map(self, strategies_by_symbol: Dict[str, Any]):
        self.strategy = None
        self.strategies_by_symbol = dict(strategies_by_symbol or {})
        for strategy_instance in self.strategies_by_symbol.values():
            if hasattr(strategy_instance, "on_init"):
                strategy_instance.on_init()

    def set_replay_trades(self, trades):
        self.replay_trades = list(trades or [])

    def _timeframe_seconds(self) -> int:
        mapping = {
            "M1": 60,
            "M5": 300,
            "M15": 900,
            "M30": 1800,
            "H1": 3600,
            "H4": 14400,
            "D1": 86400,
            "W1": 604800,
        }
        return int(mapping.get(str(self.config.get("timeframe", "M1")).upper(), 60))

    def _parse_config_datetime(self, value: Any):
        if not value:
            return None
        text = str(value)
        return datetime.fromisoformat(text.replace("Z", "+00:00"))

    def _initial_load_window(self) -> tuple[Optional[int], Optional[datetime], Optional[datetime]]:
        number_of_bars = self.config.get("number_of_bars")
        start_time = self._parse_config_datetime(self.config.get("start_time"))
        end_time = self._parse_config_datetime(self.config.get("end_time"))
        warmup_by = str(self.config.get("warmup_by", "date") or "date").lower()
        warmup_bars = int(self.config.get("warmup_bars", 0) or 0)
        warmup_start_time = self._parse_config_datetime(self.config.get("warmup_start_date"))

        load_count = int(number_of_bars) if number_of_bars else None
        if load_count is not None and warmup_by == "bars" and warmup_bars > 0:
            load_count += warmup_bars

        load_start_time = start_time
        if load_count is None and warmup_by == "date" and warmup_start_time is not None:
            load_start_time = warmup_start_time

        return load_count, load_start_time, end_time

    def _load_auxiliary_step_data(self, symbol: str, data, data_mode: str):
        if data is None or data.empty:
            return None
        first_index = data.index[0]
        last_index = data.index[-1]
        end_dt = last_index + pd.to_timedelta(self._timeframe_seconds(), unit="s")

        if data_mode in {"m1_ohlc", "synthetic_ticks"}:
            step_data = self.engine.client.get_bars(
                symbol=symbol,
                timeframe="M1",
                date_from=first_index.to_pydatetime() if hasattr(first_index, "to_pydatetime") else first_index,
                date_to=end_dt.to_pydatetime() if hasattr(end_dt, "to_pydatetime") else end_dt,
            )
            if step_data is None or step_data.empty:
                raise ValueError("No M1 data loaded for simulator session")
            return DataValidator.prepare_data(step_data)

        if data_mode == "real_ticks":
            step_data = self.engine.client.get_ticks(
                symbol=symbol,
                start=first_index.to_pydatetime() if hasattr(first_index, "to_pydatetime") else first_index,
                end=end_dt.to_pydatetime() if hasattr(end_dt, "to_pydatetime") else end_dt,
            )
            if step_data is None or len(step_data) == 0:
                raise ValueError("No tick data loaded for simulator session")
            step_data.columns = [str(c).lower() for c in step_data.columns]
            return step_data

        return None

    def _build_tick_stream(self, symbol: str, data, data_mode: str, step_data=None):
        request_like = core.DotDict(
            {
                "spread_type": str(self.config.get("spread_type", "use-broker") or "use-broker"),
                "spread": float(self.config.get("spread", 0.0) or 0.0),
                "spread_min": float(self.config.get("spread_min", 0.0) or 0.0),
                "spread_max": float(self.config.get("spread_max", 0.0) or 0.0),
            }
        )
        ticks_data, _ = _generate_ticks_for_backtest(
            engine=self.engine,
            symbol_name=symbol,
            timeframe=str(self.config.get("timeframe", "M1") or "M1"),
            request=request_like,
            data_mode=data_mode,
            bars_data=data,
            step_data=step_data,
        )
        return ticks_data

    def load_historical_bars(self):
        data_mode = _resolve_modelling(self.config.get("data_resolution"))
        timeframe = str(self.config.get("timeframe", "M1") or "M1")
        load_count, load_start_time, load_end_time = self._initial_load_window()

        merged_ticks = []
        self.data_by_symbol = {}
        self.current_market_by_symbol = {}
        self.current_bar_index_by_symbol = {}
        self._bar_first_tick_index = {}

        for symbol in self.symbols:
            if load_count:
                data = self.engine.client.get_bars(
                    symbol=symbol,
                    timeframe=timeframe,
                    count=int(load_count),
                )
            else:
                data = self.engine.client.get_bars(
                    symbol=symbol,
                    timeframe=timeframe,
                    date_from=load_start_time,
                    date_to=load_end_time,
                )
            if data is None or data.empty:
                raise ValueError(f"No historical bars loaded for simulator session: {symbol}")
            data = DataValidator.prepare_data(data)
            strategy_instance = self.strategies_by_symbol.get(symbol) or self.strategy
            if strategy_instance is not None and hasattr(strategy_instance, "on_bar"):
                data = strategy_instance.on_bar(data)
            self.data_by_symbol[symbol] = data

            step_data = self._load_auxiliary_step_data(symbol, data, data_mode)
            symbol_ticks = self._build_tick_stream(symbol, data, data_mode, step_data=step_data).copy()
            symbol_ticks["_symbol"] = symbol
            source_times = pd.DatetimeIndex(symbol_ticks["source_bar_time"])
            bar_indices = data.index.get_indexer(source_times)
            symbol_ticks["_bar_index"] = bar_indices
            merged_ticks.append(symbol_ticks)

        if not merged_ticks:
            raise ValueError("No ticks generated for simulator session")

        self.data = self.data_by_symbol.get(self.symbols[0])
        self._apply_visible_start_offset()
        self.tick_data = pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")
        for tick_index, (_, tick_row) in enumerate(self.tick_data.iterrows()):
            symbol = str(tick_row.get("_symbol", "") or "")
            bar_index = int(tick_row.get("_bar_index", 0) or 0)
            self._bar_first_tick_index.setdefault((symbol, bar_index), tick_index)

        self.total_bars = len(self.tick_data)
        if self.total_bars <= 0:
            raise ValueError("No ticks generated for simulator session")
        visible_tick_indices = [
            int(self._bar_first_tick_index[(symbol, self.visible_start_bar_index)])
            for symbol in self.symbols
            if (symbol, self.visible_start_bar_index) in self._bar_first_tick_index
        ]
        self.visible_start_tick_index = min(visible_tick_indices) if visible_tick_indices else 0
        if self.config.get("current_bar_index") in (None, ""):
            self.current_bar_index = self.visible_start_tick_index
        self.current_bar_index = max(0, min(self.current_bar_index, self.total_bars - 1))
        try:
            timeline = self.timeline_reconstructor.build_timeline(
                self.tick_data,
                frame_mode="timestamp",
            )
            self.timeline_signature = self.timeline_reconstructor.timeline_signature(
                timeline,
                frame_mode="timestamp",
            )
        except Exception:
            self.timeline_signature = "timestamp:empty"

    def _apply_visible_start_offset(self):
        base_data = self.data_by_symbol.get(self.symbols[0]) if self.symbols else self.data
        if base_data is None or base_data.empty:
            self.visible_start_bar_index = 0
            return

        visible_start_bar_index = 0
        number_of_bars = self.config.get("number_of_bars")
        warmup_by = str(self.config.get("warmup_by", "date") or "date").lower()
        warmup_bars = int(self.config.get("warmup_bars", 0) or 0)

        if number_of_bars and warmup_by == "bars" and warmup_bars > 0:
            visible_start_bar_index = warmup_bars
        elif self.config.get("start_time"):
            target_dt = self._parse_config_datetime(self.config.get("start_time"))
            if target_dt is not None:
                visible_start_bar_index = int(base_data.index.searchsorted(pd.Timestamp(target_dt), side="left"))

        self.visible_start_bar_index = max(0, min(visible_start_bar_index, len(base_data.index) - 1))

    def _bar_row(self, index: int):
        if self.data is None or index < 0 or index >= len(self.data):
            return None
        return self.data.iloc[index]

    def _symbol_bar_row(self, symbol: str, index: int):
        symbol_data = self.data_by_symbol.get(symbol)
        if symbol_data is None or index < 0 or index >= len(symbol_data):
            return None
        return symbol_data.iloc[index]

    def _tick_row(self, index: int):
        if self.tick_data is None or index < 0 or index >= len(self.tick_data):
            return None
        return self.tick_data.iloc[index]

    def _tick_timestamp(self, index: int):
        if self.tick_data is None or index < 0 or index >= len(self.tick_data.index):
            return None
        return self.tick_data.index[index]

    def _same_tick_time(self, left_index: int, right_index: int) -> bool:
        left = self._tick_timestamp(left_index)
        right = self._tick_timestamp(right_index)
        if left is None or right is None:
            return False
        return bool(left == right)

    def _tick_symbol(self, index: int) -> str:
        row = self._tick_row(index)
        if row is None:
            return self.symbols[0]
        return str(row.get("_symbol", self.symbols[0]) or self.symbols[0])

    def _bar_index_for_tick(self, index: int) -> int:
        row = self._tick_row(index)
        if row is None:
            return 0
        return int(row.get("_bar_index", 0) or 0)

    def get_bar(self, index: int):
        tick_row = self._tick_row(index)
        if tick_row is None or not self.data_by_symbol:
            return None
        symbol = self._tick_symbol(index)
        bar_index = self._bar_index_for_tick(index)
        row = self._symbol_bar_row(symbol, bar_index)
        if row is None:
            return None

        start_tick_index = self._bar_first_tick_index.get((symbol, bar_index), index)
        bar_ticks = self.tick_data.iloc[start_tick_index : index + 1]
        bar_ticks = bar_ticks[
            (bar_ticks["_symbol"] == symbol) & (bar_ticks["_bar_index"] == bar_index)
        ]
        bid_values = pd.to_numeric(bar_ticks["bid"], errors="coerce").dropna()
        if bid_values.empty:
            open_price = float(row.get("close", row.get("Close", 0.0)) or 0.0)
            high_price = open_price
            low_price = open_price
            close_price = open_price
        else:
            open_price = float(bid_values.iloc[0])
            high_price = float(bid_values.max())
            low_price = float(bid_values.min())
            close_price = float(bid_values.iloc[-1])

        payload = _json_safe_dict(row.to_dict())
        payload["open"] = open_price
        payload["high"] = high_price
        payload["low"] = low_price
        payload["close"] = close_price
        payload["symbol"] = symbol
        payload["time"] = (
            self.data_by_symbol[symbol].index[bar_index].isoformat()
            if hasattr(self.data_by_symbol[symbol].index[bar_index], "isoformat")
            else str(self.data_by_symbol[symbol].index[bar_index])
        )
        return payload

    def _update_symbol_from_tick(self, row, index: int):
        symbol = self._tick_symbol(index)
        bar_index = self._bar_index_for_tick(index)
        bid = float(row.get("bid", row.get("close", row.get("Close", 0.0))) or 0.0)
        ask = float(row.get("ask", bid) or bid)
        spread = float(row.get("spread", 0.0) or 0.0)
        tick_time = self._tick_timestamp(index)
        self.engine.state.current_tick_datetime = (
            tick_time.to_pydatetime() if hasattr(tick_time, "to_pydatetime") else tick_time
        )
        self.engine.state.current_tick_epoch = (
            int(tick_time.timestamp()) if hasattr(tick_time, "timestamp") else None
        )
        self.engine._build_symbol_map()
        self.engine._update_symbol_tick(self.engine._build_symbol_map(), symbol, bid, ask)
        bar_snapshot = self.get_bar(index) or {}
        self.current_market_by_symbol[symbol] = {
            "symbol": symbol,
            "time": bar_snapshot.get("time"),
            "open": float(bar_snapshot.get("open", bid) or bid),
            "high": float(bar_snapshot.get("high", bid) or bid),
            "low": float(bar_snapshot.get("low", bid) or bid),
            "close": float(bar_snapshot.get("close", bid) or bid),
            "bid": bid,
            "ask": ask,
            "spread": spread,
        }
        self.current_bar_index_by_symbol[symbol] = int(bar_index)
        return symbol, bid, ask

    def _account_snapshot(self):
        account = self.engine.account_info()
        return {
            "balance": float(account.get("balance", 0.0) or 0.0),
            "equity": float(account.get("equity", 0.0) or 0.0),
            "margin": float(account.get("margin", 0.0) or 0.0),
            "profit": float(account.get("profit", 0.0) or 0.0),
            "margin_free": float(account.get("margin_free", 0.0) or 0.0),
            "margin_level": float(account.get("margin_level", 0.0) or 0.0),
        }

    def process_bar_at_index(self, index: int):
        row = self._tick_row(index)
        if row is None:
            return self._account_snapshot()
        symbol, bid, ask = self._update_symbol_from_tick(row, index)
        self.engine._apply_tick_signals(
            symbol_name=symbol,
            bid=bid,
            ask=ask,
            entry_signal=float(row.get("entry_signal", 0.0) or 0.0),
            exit_signal=float(row.get("exit_signal", row.get("exit_trade", 0.0)) or 0.0),
            pending_signal=float(row.get("pending_signal", 0.0) or 0.0),
            cancel_pending_signal=float(row.get("cancel_pending_signal", 0.0) or 0.0),
            pending_signal_2=float(row.get("pending_signal_2", 0.0) or 0.0),
            cancel_pending_signal_2=float(row.get("cancel_pending_signal_2", 0.0) or 0.0),
            signal_price=float(row.get("price", 0.0) or 0.0),
            signal_price_2=float(row.get("price_2", 0.0) or 0.0),
            sl=float(row.get("sl", 0.0) or 0.0),
            tp=float(row.get("tp", 0.0) or 0.0),
            volume=float(self.config.get("lot_size", 0.1) or 0.1),
            verbose=False,
        )
        self.engine.monitor_pending_orders(verbose=False)
        self.engine.monitor_positions(verbose=False)
        self.engine.monitor_account(verbose=False)
        return self._account_snapshot()

    def advance_frames(self, count: int) -> List[Dict[str, Any]]:
        frames: List[Dict[str, Any]] = []
        requested = max(0, int(count or 0))
        if requested <= 0:
            return frames

        for _ in range(requested):
            if self.current_bar_index >= self.total_bars:
                break

            frame_by_symbol: Dict[str, Dict[str, Any]] = {}
            while self.current_bar_index < self.total_bars:
                tick_index = self.current_bar_index
                bar = self.get_bar(tick_index)
                symbol = self._tick_symbol(tick_index)
                account = self.process_bar_at_index(tick_index)
                indicators = self.get_indicators_at_index(tick_index)

                if bar:
                    frame_by_symbol[symbol] = {
                        "bar": bar,
                        "index": tick_index,
                        "account": account,
                        "indicators": indicators,
                    }

                self.current_bar_index += 1
                if (
                    self.current_bar_index >= self.total_bars
                    or not self._same_tick_time(tick_index, self.current_bar_index)
                ):
                    break

            if frame_by_symbol:
                frames.extend(
                    frame_by_symbol[symbol]
                    for symbol in self.symbols
                    if symbol in frame_by_symbol
                )
                self.save_state()

        return frames

    def get_indicators_at_index(self, index: int):
        symbol = self._tick_symbol(index)
        row = self._symbol_bar_row(symbol, self._bar_index_for_tick(index))
        if row is None:
            return {}
        excluded = {"open", "high", "low", "close", "tick_volume", "real_volume", "spread", "Open", "High", "Low", "Close", "TickVolume", "RealVolume", "Spread"}
        out = {}
        for key, value in row.to_dict().items():
            if str(key) in excluded:
                continue
            if isinstance(value, (int, float, str, bool)) or value is None:
                out[str(key)] = _json_safe_value(value)
        return out

    def execute_trade(self, request: Dict[str, Any]):
        request_symbol = str(request.get("symbol", "") or "").strip().upper()
        target_symbol = request_symbol or self.symbols[0]

        row = self._tick_row(max(self.current_bar_index - 1, 0))
        if row is None or self._tick_symbol(max(self.current_bar_index - 1, 0)) != target_symbol:
            row = None
            if self.tick_data is not None and not self.tick_data.empty:
                matches = self.tick_data[self.tick_data["_symbol"] == target_symbol]
                if not matches.empty:
                    row = matches.iloc[-1]
        if row is not None:
            bid = float(row.get("bid", 0.0) or 0.0)
            ask = float(row.get("ask", bid) or bid)
            self.engine._build_symbol_map()
            self.engine._update_symbol_tick(self.engine._build_symbol_map(), target_symbol, bid, ask)
            symbol = target_symbol
        else:
            symbol = target_symbol
            tick = self.engine.symbol_info_tick(symbol)
            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)
        side = str(request.get("side", "buy") or "buy").lower()
        order_type_str = "BUY" if side == "buy" else "SELL"
        price = request.get("price")
        if price is None:
            price = ask if order_type_str == "BUY" else bid
        result = self.trade_api.PositionOpen(
            symbol=symbol,
            order_type=order_type_str,
            volume=float(request.get("volume", 0.1) or 0.1),
            price=float(price or 0.0),
            sl=float(request.get("sl") or 0.0),
            tp=float(request.get("tp") or 0.0),
            comment=str(request.get("comment") or "Manual trade"),
        )
        self.engine.monitor_positions(verbose=False)
        self.engine.monitor_account(verbose=False)
        return _object_to_dict(result)

    def place_pending_order(self, request: Dict[str, Any]):
        order_type_map = {
            "buy_limit": "BUY_LIMIT",
            "sell_limit": "SELL_LIMIT",
            "buy_stop": "BUY_STOP",
            "sell_stop": "SELL_STOP",
            "buy_stop_limit": "BUY_STOP_LIMIT",
            "sell_stop_limit": "SELL_STOP_LIMIT",
        }
        symbol = str(request.get("symbol", "") or "").strip().upper() or self.symbols[0]
        order_type_str = order_type_map.get(str(request.get("type", "")).lower(), "BUY_LIMIT")
        result = self.trade_api.OrderOpen(
            symbol=symbol,
            order_type=order_type_str,
            volume=float(request.get("volume", 0.1) or 0.1),
            price=float(request.get("price", 0.0) or 0.0),
            sl=float(request.get("sl") or 0.0),
            tp=float(request.get("tp") or 0.0),
            comment=str(request.get("comment") or "Pending order"),
        )
        self.engine.monitor_account(verbose=False)
        return _object_to_dict(result)

    def get_market_snapshots(self):
        return [
            self.current_market_by_symbol[symbol]
            for symbol in self.symbols
            if symbol in self.current_market_by_symbol
        ]

    def risk_limits_enforced(self) -> bool:
        return bool(self.config.get("risk_limits_enforced", True))

    def evaluate_pre_trade_governance(
        self,
        *,
        symbol: str,
        signed_volume: float,
    ):
        state = self.latest_risk_state or self.build_risk_state()
        if state.limits is None:
            return None

        risk_engine = PortfolioRiskEngine(
            mt5_client=_SimulatorPortfolioStateRiskAdapter(state),
            timeframe=str(state.metadata.get("timeframe", "H1")),
            start_pos=0,
            end_pos=max(max((market.row_count for market in state.markets.values()), default=0), 1),
        )
        governance = GovernanceEngine(
            risk_engine=risk_engine,
            limits=state.limits,
        )
        projected_state = self.project_state_for_signed_volume(
            symbol=str(symbol),
            signed_volume=float(signed_volume),
        )
        forced_decision = None
        forced_reason = None
        if len(projected_state.positions) < len(state.positions):
            forced_decision = "ACCEPT"
            forced_reason = "Candidate reduces or nets existing exposure."
        return governance.evaluate_transition_from_states(
            state,
            projected_state,
            forced_decision=forced_decision,
            forced_reason=forced_reason,
        )

    def project_state_for_signed_volume(
        self,
        *,
        symbol: str,
        signed_volume: float,
    ) -> PortfolioState:
        state = self.latest_risk_state or self.build_risk_state()
        candidate_symbol = str(symbol)
        projected_positions = list(state.positions)
        applied = False
        for index, position in enumerate(projected_positions):
            if position.symbol != candidate_symbol:
                continue
            next_lots = float(position.lots) + float(signed_volume)
            if abs(next_lots) < 1e-12:
                projected_positions.pop(index)
            else:
                projected_positions[index] = replace(
                    position,
                    lots=next_lots,
                    side="LONG" if next_lots >= 0 else "SHORT",
                )
            applied = True
            break
        if not applied and abs(float(signed_volume)) > 0.0:
            projected_positions.append(
                PositionState(
                    symbol=candidate_symbol,
                    lots=float(signed_volume),
                    side="LONG" if float(signed_volume) >= 0 else "SHORT",
                    cluster=getattr(state, "symbol_to_cluster", {}).get(candidate_symbol),
                )
            )
        projected_account = state.account
        projected_state = replace(
            state,
            positions=projected_positions,
            exposures=self.risk_state_engine._compute_exposures(
                state.account,
                projected_positions,
                state.symbols,
                state.markets,
            ),
        )
        projected_margin_used = _estimate_state_margin_used(projected_state)
        projected_account = replace(
            projected_account,
            margin_used=float(projected_margin_used),
            free_margin=float(state.account.equity or 0.0) - float(projected_margin_used),
        )
        return replace(
            projected_state,
            account=projected_account,
        )

    def build_manual_trade_review(
        self,
        *,
        symbol: str,
        signed_volume: float,
    ) -> dict:
        current_state = self.latest_risk_state or self.build_risk_state()
        projected_state = self.project_state_for_signed_volume(
            symbol=str(symbol),
            signed_volume=float(signed_volume),
        )
        if current_state.limits is None:
            return {"governance": None, "rows": []}

        risk_engine = PortfolioRiskEngine(
            mt5_client=_SimulatorPortfolioStateRiskAdapter(current_state),
            timeframe=str(current_state.metadata.get("timeframe", "H1")),
            start_pos=0,
            end_pos=max(max((market.row_count for market in current_state.markets.values()), default=0), 1),
        )
        governance_engine = GovernanceEngine(
            risk_engine=risk_engine,
            limits=current_state.limits,
        )
        governance = governance_engine.evaluate_transition_from_states(
            current_state,
            projected_state,
        )
        effective_limits = governance_engine.effective_limits(None)
        current_var, current_es, current_margin, current_rc = risk_engine.compute_portfolio_risk_from_state(
            current_state,
            limits=effective_limits,
        )
        new_var, new_es, new_margin, new_rc = risk_engine.compute_portfolio_risk_from_state(
            projected_state,
            limits=effective_limits,
        )

        def _fmt_ratio(value: Optional[float]) -> str:
            if value is None or not math.isfinite(float(value)):
                return "--"
            return f"{float(value) * 100:.2f}%"

        def _normalize_abs_map(payload: Optional[Dict[str, float]]) -> Dict[str, float]:
            absolute_map = {
                str(key): abs(float(val))
                for key, val in (payload or {}).items()
                if abs(float(val or 0.0)) > 1e-12
            }
            total = float(sum(absolute_map.values()))
            if total <= 0.0:
                return {}
            return {key: float(value) / total for key, value in absolute_map.items()}

        current_equity = float(current_state.account.equity or 0.0)
        new_equity = float(projected_state.account.equity or 0.0)
        current_currency_weights = _normalize_abs_map(extract_currency_exposure(current_state))
        proposed_currency_weights = _normalize_abs_map(extract_currency_exposure(projected_state))
        proposed_currency_count = max(1, len(proposed_currency_weights))
        currency_weight_limit = (1.0 / float(proposed_currency_count)) * (
            1.0 + float(effective_limits.max_currency_exposure_frac)
        )
        current_rc_weights = _normalize_abs_map(current_rc)
        proposed_rc_weights = _normalize_abs_map(new_rc)
        proposed_symbol_count = max(1, len(proposed_rc_weights))
        single_rc_limit = (1.0 / float(proposed_symbol_count)) + float(effective_limits.max_single_rc_frac)

        rows = [
            {
                "key": "portfolio_var_cap",
                "item": "Portfolio VaR",
                "current_value": _fmt_ratio((current_var / current_equity) if current_equity > 0.0 else None),
                "proposed_value": _fmt_ratio((new_var / new_equity) if new_equity > 0.0 else None),
                "reference_value": _fmt_ratio(effective_limits.var_cap_frac),
                "acceptable": float(new_var) <= float(effective_limits.var_cap_frac) * max(new_equity, 0.0),
            },
            {
                "key": "portfolio_es_cap",
                "item": "Portfolio CVaR",
                "current_value": _fmt_ratio((current_es / current_equity) if current_equity > 0.0 else None),
                "proposed_value": _fmt_ratio((new_es / new_equity) if new_equity > 0.0 else None),
                "reference_value": _fmt_ratio(effective_limits.es_cap_frac),
                "acceptable": float(new_es) <= float(effective_limits.es_cap_frac) * max(new_equity, 0.0),
            },
            {
                "key": "delta_var_cap",
                "item": "Delta VaR",
                "current_value": "0.00%",
                "proposed_value": _fmt_ratio(((new_var - current_var) / new_equity) if new_equity > 0.0 else None),
                "reference_value": _fmt_ratio(effective_limits.delta_var_cap_frac),
                "acceptable": float(new_var - current_var) <= float(effective_limits.delta_var_cap_frac) * max(new_equity, 0.0),
            },
            {
                "key": "delta_es_cap",
                "item": "Delta CVaR",
                "current_value": "0.00%",
                "proposed_value": _fmt_ratio(((new_es - current_es) / new_equity) if new_equity > 0.0 else None),
                "reference_value": _fmt_ratio(effective_limits.delta_es_cap_frac),
                "acceptable": float(new_es - current_es) <= float(effective_limits.delta_es_cap_frac) * max(new_equity, 0.0),
            },
            {
                "key": "margin_cap",
                "item": "Margin Used",
                "current_value": _fmt_ratio((current_margin / current_equity) if current_equity > 0.0 else None),
                "proposed_value": _fmt_ratio((new_margin / new_equity) if new_equity > 0.0 else None),
                "reference_value": _fmt_ratio(effective_limits.max_margin_used_frac),
                "acceptable": float(new_margin or 0.0) <= float(effective_limits.max_margin_used_frac) * max(new_equity, 0.0),
            },
        ]

        for currency in sorted(proposed_currency_weights.keys()):
            proposed_weight = float(proposed_currency_weights.get(currency, 0.0))
            rows.append(
                {
                    "key": f"currency_weight:{currency}",
                    "item": f"Currency Weight {currency}",
                    "current_value": _fmt_ratio(current_currency_weights.get(currency)),
                    "proposed_value": _fmt_ratio(proposed_weight),
                    "reference_value": _fmt_ratio(currency_weight_limit),
                    "acceptable": proposed_weight <= currency_weight_limit,
                }
            )

        for symbol_key in sorted(proposed_rc_weights.keys()):
            proposed_weight = float(proposed_rc_weights.get(symbol_key, 0.0))
            rows.append(
                {
                    "key": f"single_rc:{symbol_key}",
                    "item": f"Single RC {symbol_key}",
                    "current_value": _fmt_ratio(current_rc_weights.get(symbol_key)),
                    "proposed_value": _fmt_ratio(proposed_weight),
                    "reference_value": _fmt_ratio(single_rc_limit),
                    "acceptable": proposed_weight <= single_rc_limit,
                }
            )

        return {
            "governance": _serialize_governance_report(governance),
            "rows": rows,
        }

    def evaluate_current_governance(self):
        state = self.latest_risk_state or self.build_risk_state()
        if state.limits is None:
            return None
        risk_engine = PortfolioRiskEngine(
            mt5_client=_SimulatorPortfolioStateRiskAdapter(state),
            timeframe=str(state.metadata.get("timeframe", "H1")),
            start_pos=0,
            end_pos=max(max((market.row_count for market in state.markets.values()), default=0), 1),
        )
        governance = GovernanceEngine(
            risk_engine=risk_engine,
            limits=state.limits,
        )
        return governance.evaluate_portfolio_state(state)

    def build_risk_state(self) -> PortfolioState:
        market_data: Dict[str, pd.DataFrame] = {}
        for symbol in self.symbols:
            symbol_data = self.data_by_symbol.get(symbol)
            if symbol_data is None:
                continue
            current_symbol_bar = self.current_bar_index_by_symbol.get(symbol)
            if current_symbol_bar is None:
                market_data[symbol] = symbol_data.iloc[0:0].copy()
                continue
            capped_index = max(0, min(int(current_symbol_bar), len(symbol_data.index) - 1))
            market_data[symbol] = symbol_data.iloc[: capped_index + 1].copy()

        current_tick_dt = getattr(self.engine.state, "current_tick_datetime", None)
        as_of = None
        if current_tick_dt is not None:
            as_of = (
                current_tick_dt.isoformat()
                if hasattr(current_tick_dt, "isoformat")
                else str(current_tick_dt)
            )

        symbol_specs: Dict[str, Any] = {}
        for symbol in self.symbols:
            spec = self.engine.symbol_info(symbol)
            if spec is not None:
                symbol_specs[symbol] = spec
        symbol_to_clusters = _build_symbol_currency_clusters(self.symbols, symbol_specs)
        symbol_to_cluster = {
            symbol: clusters[0]
            for symbol, clusters in symbol_to_clusters.items()
            if clusters
        }

        limits = RiskLimits(
            var_cap_frac=max(0.0, float(self.config.get("risk_var_cap_frac", 0.10) or 0.10)),
            es_cap_frac=max(0.0, float(self.config.get("risk_es_cap_frac", 0.15) or 0.15)),
            delta_var_cap_frac=max(0.0, float(self.config.get("risk_delta_var_cap_frac", 0.02) or 0.02)),
            delta_es_cap_frac=max(0.0, float(self.config.get("risk_delta_es_cap_frac", 0.03) or 0.03)),
            max_margin_used_frac=max(0.0, float(self.config.get("risk_max_margin_used_frac", 0.50) or 0.50)),
            max_currency_exposure_frac=max(0.0, float(self.config.get("risk_max_currency_exposure_frac", 0.20) or 0.20)),
            max_single_rc_frac=max(0.0, float(self.config.get("risk_max_single_rc_frac", 0.10) or 0.10)),
            warning_utilization_frac=max(0.0, float(self.config.get("risk_warning_utilization_frac", 0.90) or 0.90)),
            confidence_level=float(self.config.get("risk_confidence_level", 0.95) or 0.95),
            time_horizon_days=max(1, int(self.config.get("risk_horizon_value", 1) or 1)),
            vol_lookback=max(2, int(self.config.get("risk_vol_lookback", 20) or 20)),
            corr_lookback=max(2, int(self.config.get("risk_corr_lookback", 60) or 60)),
        )

        state = self.risk_state_engine.build_state(
            account=self.engine.account_info(),
            positions=list(self.simulator._positions_data.values()),
            symbol_specs=symbol_specs,
            market_data=market_data,
            limits=limits,
            symbol_to_cluster=symbol_to_cluster,
            symbol_to_clusters=symbol_to_clusters,
            timeframe=str(self.config.get("timeframe", "M1") or "M1"),
            as_of=as_of,
            metadata={
                "source": "simulation_session",
                "session_id": int(self.session_id),
                "mode": str(self.config.get("mode", "manual") or "manual"),
                "current_bar_index": int(self.current_bar_index),
                "symbols": list(self.symbols),
                "timeframe": str(self.config.get("timeframe", "M1") or "M1"),
                "risk_horizon_unit": str(self.config.get("risk_horizon_unit", "days") or "days"),
                "risk_horizon_value": max(1, int(self.config.get("risk_horizon_value", 1) or 1)),
            },
        )
        self.latest_risk_state = state
        return state

    def refresh_risk_state(self) -> Optional[PortfolioState]:
        try:
            state = self.build_risk_state()
            try:
                self.latest_risk_snapshot = self.risk_snapshot_engine.build_snapshot(
                    state,
                    shared={
                        "previous_regime": self.previous_regime_state,
                        "equity_curve": self.engine.get_equity_curve(),
                    },
                )
                self.latest_risk_scorecard = self.risk_scorecard_engine.build_scorecard(
                    self.latest_risk_snapshot
                )
                self.latest_recommendation_batch = self.recommendation_engine.build_recommendations(
                    state,
                    snapshot=self.latest_risk_snapshot,
                    scorecard=self.latest_risk_scorecard,
                    candidate_symbols=self.symbols,
                    hedge_symbols=self.symbols,
                    max_recommendations=6,
                )
                self.latest_regime_report = self.latest_risk_snapshot.regime_report
                self.previous_regime_state = self.latest_risk_snapshot.regime_state
            except Exception as exc:
                self.latest_risk_snapshot = None
                self.latest_risk_scorecard = None
                self.latest_recommendation_batch = None
                self.latest_regime_report = None
                logger.warning(
                    f"Failed to build risk snapshot | session={self.session_id} err={exc}"
                )
            try:
                self.latest_governance_report = self.evaluate_current_governance()
            except Exception as exc:
                self.latest_governance_report = None
                logger.warning(
                    f"Failed to build governance report | session={self.session_id} err={exc}"
                )
            return state
        except Exception as exc:
            logger.warning(
                f"Failed to build risk state | session={self.session_id} err={exc}"
            )
            return None

    def get_risk_summary(self) -> Dict[str, Any]:
        snapshot = self.latest_risk_snapshot
        if snapshot is None:
            return {}

        summary = dict(snapshot.summary or {})
        metric_rows = list(getattr(snapshot, "metric_rows", []) or [])
        def _json_safe_number(value: Any) -> Any:
            if isinstance(value, (int, float)):
                numeric = float(value)
                if not math.isfinite(numeric):
                    return None
            return value

        currency_exposure = []
        currency_weights = []
        pair_correlations = []
        max_risk_contribution_frac = 0.0
        max_risk_contribution_symbol = None
        for row in metric_rows:
            scope = getattr(row, "scope", None)
            metric_key = getattr(row, "metric_key", None)
            scope_key = getattr(row, "scope_key", None)
            numeric_value = _json_safe_number(getattr(row, "numeric_value", None))
            if scope == "currency" and metric_key == "net_currency_exposure" and scope_key:
                currency_exposure.append(
                    {
                        "currency": str(scope_key),
                        "value": numeric_value,
                    }
                )
            if scope == "pair" and metric_key == "pair_correlation" and scope_key:
                pair_correlations.append(
                    {
                        "pair": str(scope_key),
                        "value": numeric_value,
                    }
                )
            if (
                scope == "symbol"
                and metric_key == "risk_contribution_frac"
                and scope_key
                and isinstance(numeric_value, (int, float))
            ):
                contribution_value = abs(float(numeric_value))
                if contribution_value >= max_risk_contribution_frac:
                    max_risk_contribution_frac = contribution_value
                    max_risk_contribution_symbol = str(scope_key)

        currency_exposure.sort(key=lambda item: abs(float(item.get("value") or 0.0)), reverse=True)
        pair_correlations.sort(
            key=lambda item: abs(float(item.get("value") or 0.0)),
            reverse=True,
        )
        total_currency_exposure = float(
            sum(abs(float(item.get("value") or 0.0)) for item in currency_exposure)
        )
        for item in currency_exposure:
            numeric_value = float(item.get("value") or 0.0)
            currency_weights.append(
                {
                    "currency": item["currency"],
                    "value": (abs(numeric_value) / total_currency_exposure)
                    if total_currency_exposure > 0.0
                    else 0.0,
                }
            )

        return {
            "gross_exposure": _json_safe_number(summary.get("gross_exposure")),
            "net_exposure": _json_safe_number(summary.get("net_exposure")),
            "margin_used": _json_safe_number(summary.get("margin_used")),
            "margin_used_frac": _json_safe_number(summary.get("margin_used_frac")),
            "portfolio_var": _json_safe_number(summary.get("portfolio_var")),
            "portfolio_es": _json_safe_number(summary.get("portfolio_es")),
            "max_single_exposure_frac": _json_safe_number(summary.get("max_single_exposure_frac")),
            "average_pair_correlation": _json_safe_number(summary.get("average_pair_correlation")),
            "max_pair_correlation": _json_safe_number(summary.get("max_pair_correlation")),
            "hidden_overlap_score": _json_safe_number(summary.get("hidden_overlap_score")),
            "redundancy_score": _json_safe_number(summary.get("redundancy_score")),
            "effective_independent_bets": _json_safe_number(summary.get("effective_independent_bets")),
            "diversification_ratio": _json_safe_number(summary.get("diversification_ratio")),
            "current_drawdown": _json_safe_number(summary.get("current_drawdown")),
            "max_drawdown": _json_safe_number(summary.get("max_drawdown")),
            "drawdown_velocity": _json_safe_number(summary.get("drawdown_velocity")),
            "time_under_water": _json_safe_number(summary.get("time_under_water")),
            "compliance_state": summary.get("compliance_state"),
            "governance_decision": summary.get("governance_decision"),
            "governance_reason": summary.get("governance_reason"),
            "regime_name": summary.get("regime_name"),
            "regime_confidence": _json_safe_number(summary.get("regime_confidence")),
            "regime_signals_triggered": summary.get("regime_signals_triggered") or [],
            "regime_warnings": summary.get("regime_warnings") or [],
            "market_regime": summary.get("market_regime"),
            "volatility_regime": summary.get("volatility_regime"),
            "liquidity_regime": summary.get("liquidity_regime"),
            "crisis_regime": summary.get("crisis_regime"),
            "regime_transition_changed": bool(summary.get("regime_transition_changed", False)),
            "currency_exposure": currency_exposure,
            "currency_weights": currency_weights,
            "pair_correlations": pair_correlations,
            "max_risk_contribution_frac": max_risk_contribution_frac,
            "max_risk_contribution_symbol": max_risk_contribution_symbol,
        }

    def get_governance_report(self) -> Optional[Dict[str, Any]]:
        if getattr(self, "latest_governance_report", None) is None:
            return None
        return _serialize_governance_report(self.latest_governance_report)

    def get_risk_score_summary(self) -> Dict[str, Any]:
        scorecard = self.latest_risk_scorecard
        if scorecard is None:
            return {}

        summary = dict(scorecard.summary or {})
        score_rows = list(getattr(scorecard, "score_rows", []) or [])

        def _json_safe_number(value: Any) -> Any:
            if isinstance(value, (int, float)):
                numeric = float(value)
                if not math.isfinite(numeric):
                    return None
                return numeric
            return value

        detailed_scores = {}
        for row in score_rows:
            score_key = getattr(row, "score_key", None)
            if not score_key:
                continue
            context = getattr(row, "context", {}) or {}
            detailed_scores[str(score_key)] = {
                "value": _json_safe_number(getattr(row, "score_value", None)),
                "confidence": _json_safe_number(getattr(row, "confidence", None)),
                "confidence_label": getattr(row, "confidence_label", None),
                "explanation": getattr(row, "explanation", None),
                "context": _json_safe_dict(dict(context)),
            }

        return {
            "portfolio_health_score": _json_safe_number(summary.get("portfolio_health_score")),
            "concentration_score": _json_safe_number(summary.get("concentration_score")),
            "stress_resilience_score": _json_safe_number(summary.get("stress_resilience_score")),
            "regime_alignment_score": _json_safe_number(summary.get("regime_alignment_score")),
            "leverage_safety_score": _json_safe_number(summary.get("leverage_safety_score")),
            "margin_safety_score": _json_safe_number(summary.get("margin_safety_score")),
            "diversification_score": _json_safe_number(summary.get("diversification_score")),
            "governance_compliance_score": _json_safe_number(summary.get("governance_compliance_score")),
            "overall_risk_quality_score": _json_safe_number(summary.get("overall_risk_quality_score")),
            "overall_confidence": _json_safe_number(summary.get("overall_confidence")),
            "overall_confidence_label": summary.get("overall_confidence_label"),
            "details": detailed_scores,
        }

    def get_recommendation_summary(self) -> Dict[str, Any]:
        batch = self.latest_recommendation_batch
        return _serialize_recommendation_batch(batch)

    def ensure_risk_run(self) -> int:
        if self.risk_run_id:
            return int(self.risk_run_id)
        run_id = self.risk_snapshot_store.create_run(
            label=str(
                self.config.get("session_name")
                or f"Simulation Session {self.session_id}"
            ),
            description=(
                f"Risk storage for simulation session {self.session_id} "
                f"({','.join(self.symbols)} {self.config.get('timeframe', 'M1')})"
            ),
            source="simulation",
            context={
                "session_id": int(self.session_id),
                "symbols": list(self.symbols),
                "timeframe": str(self.config.get("timeframe", "M1") or "M1"),
                "mode": str(self.config.get("mode", "manual") or "manual"),
                "timeline_signature": self.timeline_signature,
            },
        )
        self.risk_run_id = int(run_id)
        self.config["risk_run_id"] = int(run_id)
        self.db.update_simulation_session(self.session_id, config=dict(self.config))
        return int(run_id)

    def persist_current_risk_bundle(
        self,
        *,
        backtest_id: Optional[int] = None,
    ) -> Optional[int]:
        if self.latest_risk_snapshot is None:
            return None
        run_id = self.ensure_risk_run()
        snapshot_id = self.risk_snapshot_store.store_snapshot_bundle(
            run_id=run_id,
            snapshot=self.latest_risk_snapshot,
            scorecard=self.latest_risk_scorecard,
            recommendations=self.latest_recommendation_batch,
            backtest_id=backtest_id,
        )
        self.latest_risk_snapshot_id = int(snapshot_id)
        return int(snapshot_id)

    def persist_what_if_comparison(self, comparison: Any) -> Dict[str, Optional[int]]:
        run_id = self.ensure_risk_run()
        snapshot_id = self.persist_current_risk_bundle()
        frame = self.build_current_replay_frame()
        replay_frame_id = self.risk_snapshot_store.store_replay_frame(
            run_id=run_id,
            frame=frame,
            snapshot_id=snapshot_id,
            what_if=comparison,
        )
        self.latest_risk_replay_frame_id = int(replay_frame_id)
        return {
            "risk_run_id": int(run_id),
            "risk_snapshot_id": int(snapshot_id) if snapshot_id else None,
            "risk_replay_frame_id": int(replay_frame_id),
        }

    def build_current_replay_frame(self) -> ReplayFrame:
        state = self.latest_risk_state or self.build_risk_state()
        snapshot = self.latest_risk_snapshot or self.risk_snapshot_engine.build_snapshot(
            state,
            shared={
                "previous_regime": self.previous_regime_state,
                "equity_curve": self.engine.get_equity_curve(),
            },
        )
        scorecard = self.latest_risk_scorecard or self.risk_scorecard_engine.build_scorecard(
            snapshot
        )
        recommendations = self.latest_recommendation_batch
        tick_index = max(min(self.current_bar_index - 1, self.total_bars - 1), 0)
        tick_timestamp = self._tick_timestamp(tick_index)
        frame_timestamp = (
            pd.Timestamp(tick_timestamp)
            if tick_timestamp is not None
            else pd.Timestamp.utcnow()
        )
        return ReplayFrame(
            frame_index=int(self.current_bar_index),
            timestamp=frame_timestamp,
            capture_timestamp=frame_timestamp,
            state=state,
            snapshot=snapshot,
            scorecard=scorecard,
            recommendations=recommendations,
            context={
                "timeframe": str(self.config.get("timeframe", "M1") or "M1"),
                "timeline_signature": self.timeline_signature,
            },
        )

    def evaluate_what_if(
        self,
        *,
        actions: List[HypotheticalOrderAction],
        leverage_override: Optional[int] = None,
    ):
        frame = self.build_current_replay_frame()
        comparison = self.what_if_engine.evaluate(
            frame,
            actions,
            include_recommendations=True,
            candidate_symbols=self.symbols,
            hedge_symbols=self.symbols,
            max_recommendations=6,
            snapshot_shared={
                "previous_regime": self.previous_regime_state,
                "equity_curve": self.engine.get_equity_curve(),
            },
        )
        baseline_margin = float(
            frame.state.account.margin_used
            or frame.snapshot.state.account.margin_used
            or 0.0
        )
        projected_margin = float(comparison.projected_state.account.margin_used or 0.0)
        comparison.summary.update(
            {
                "baseline_margin_used": baseline_margin,
                "projected_margin_used": projected_margin,
                "margin_used_delta": projected_margin - baseline_margin,
                "baseline_compliance_state": frame.snapshot.summary.get("compliance_state"),
                "projected_compliance_state": comparison.projected_snapshot.summary.get(
                    "compliance_state"
                ),
                "baseline_governance_decision": frame.snapshot.summary.get(
                    "governance_decision"
                ),
                "projected_governance_decision": comparison.projected_snapshot.summary.get(
                    "governance_decision"
                ),
            }
        )
        if leverage_override is None or leverage_override <= 0:
            return comparison

        projected_state = _apply_leverage_override_to_state(
            comparison.projected_state,
            int(leverage_override),
        )
        projected_snapshot = self.risk_snapshot_engine.build_snapshot(
            projected_state,
            shared={
                "previous_regime": self.previous_regime_state,
                "equity_curve": self.engine.get_equity_curve(),
            },
        )
        projected_scorecard = self.risk_scorecard_engine.build_scorecard(projected_snapshot)
        projected_recommendations = self.recommendation_engine.build_recommendations(
            projected_state,
            snapshot=projected_snapshot,
            scorecard=projected_scorecard,
            candidate_symbols=self.symbols,
            hedge_symbols=self.symbols,
            max_recommendations=6,
        )

        baseline_summary = comparison.summary or {}
        projected_margin = float(projected_state.account.margin_used or 0.0)

        comparison.summary.update(
            {
                **baseline_summary,
                "projected_margin_used": projected_margin,
                "margin_used_delta": projected_margin
                - float(baseline_summary.get("baseline_margin_used", 0.0) or 0.0),
                "projected_compliance_state": projected_snapshot.summary.get("compliance_state"),
                "projected_governance_decision": projected_snapshot.summary.get("governance_decision"),
                "leverage_override": int(leverage_override),
            }
        )
        return replace(
            comparison,
            projected_state=projected_state,
            projected_snapshot=projected_snapshot,
            projected_scorecard=projected_scorecard,
            projected_recommendations=projected_recommendations,
        )

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def finalize_for_saved_backtest(self, user_id: int) -> int:
        for order in list(self.simulator._orders_data.values()):
            order_data = _object_to_dict(order)
            ok = self.simulator.order_delete(order_data)
            if not ok:
                raise RuntimeError(
                    f"Failed to delete pending order {order_data.get('ticket') or order_data.get('id')}"
                )

        for position in list(self.simulator._positions_data.values()):
            pos_data = _object_to_dict(position)
            ok = self.simulator.close_position(pos_data, reason="simulation_stop_save")
            if not ok:
                raise RuntimeError(
                    f"Failed to close position {pos_data.get('ticket') or pos_data.get('position_id')}"
                )

        totals = self.simulator.monitor_positions()
        self.simulator.monitor_account(totals)

        strategy_id = self.config.get("strategy_id")
        strategy_version_id = self.config.get("strategy_version_id")
        strategy_name = "Simulation Session"
        strategy_version = "simulation"

        if strategy_id:
            strategy = db_manager.get_strategy(int(strategy_id))
            if strategy:
                strategy_name = str(strategy.get("name") or strategy_name)
        if strategy_version_id:
            version = db_manager.get_strategy_version(int(strategy_version_id))
            if version:
                strategy_version = str(
                    version.get("version")
                    or version.get("version_name")
                    or strategy_version
                )

        start_dt = None
        end_dt = None
        if self.tick_data is not None and len(self.tick_data.index) > 0:
            first_index = self.tick_data.index[0]
            start_dt = (
                first_index.to_pydatetime()
                if hasattr(first_index, "to_pydatetime")
                else first_index
            )
            current_idx = min(max(self.current_bar_index - 1, 0), len(self.tick_data.index) - 1)
            end_index = self.tick_data.index[current_idx]
            end_dt = (
                end_index.to_pydatetime()
                if hasattr(end_index, "to_pydatetime")
                else end_index
            )

        if start_dt is None:
            start_dt = datetime.utcnow()
        if end_dt is None:
            end_dt = datetime.utcnow()

        symbol = str(self.config.get("symbol", "") or "")
        timeframe = str(self.config.get("timeframe", "M1") or "M1")
        alias = str(
            self.config.get("alias")
            or self.config.get("session_name")
            or f"Saved Simulation - {symbol} {timeframe}"
        )
        description = str(
            self.config.get("description")
            or f"Saved from simulation session {self.session_id}"
        )

        backtest_id = db_manager.create_backtest_run(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_dt,
            end_date=end_dt,
            engine_type="simulation",
            data_resolution=str(self.config.get("data_resolution", "trading_timeframe") or "trading_timeframe"),
            config_hash=str(hash((self.session_id, symbol, timeframe, self.current_bar_index))),
            strategy_version_id=int(strategy_version_id) if strategy_version_id else None,
            user_id=user_id,
            symbols=self.symbols,
            timeframes=[timeframe],
            initial_balance=float(self.config.get("initial_balance", 10000.0) or 10000.0),
            alias=alias,
            description=description,
        )

        completed_trades = self.engine.get_completed_trades()
        equity_curve = self.engine.get_equity_curve()
        if completed_trades:
            db_manager.save_backtest_trades(backtest_id, completed_trades)
        if equity_curve:
            db_manager.save_backtest_equity_curve(backtest_id, equity_curve)

        final_balance = float(
            self.engine.account_info().get(
                "balance",
                self.config.get("initial_balance", 10000.0),
            )
            or self.config.get("initial_balance", 10000.0)
        )
        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=final_balance,
        )
        return backtest_id

    def save_state(self):
        self.db.update_simulation_session(self.session_id, current_bar_index=self.current_bar_index)

    def visible_total_steps(self) -> int:
        return max(0, int(self.total_bars - self.visible_start_tick_index))

    def visible_current_step(self) -> int:
        return max(0, int(self.current_bar_index - self.visible_start_tick_index))

    def resolve_base_bar_index(self, target_time: Optional[str], fallback_index: Optional[int]) -> int:
        base_data = self.data_by_symbol.get(self.symbols[0]) if self.symbols else self.data
        if base_data is None or base_data.empty:
            return 0

        if target_time:
            try:
                target_dt = pd.Timestamp(target_time)
                if getattr(target_dt, "tzinfo", None) is not None:
                    target_dt = target_dt.tz_convert(None)
                bar_index = int(base_data.index.searchsorted(target_dt, side="left"))
                if bar_index >= len(base_data.index):
                    return len(base_data.index) - 1
                return max(self.visible_start_bar_index, bar_index)
            except Exception:
                pass

        visible_index = self.visible_start_bar_index + int(fallback_index or 0)
        return max(self.visible_start_bar_index, min(visible_index, len(base_data.index) - 1))

    def seek_to_bar(self, index: int):
        base_data = self.data_by_symbol.get(self.symbols[0]) if self.symbols else self.data
        if base_data is None or base_data.empty:
            self.current_bar_index = 0
        else:
            symbol = self.symbols[0]
            bar_index = max(0, min(int(index), len(base_data.index) - 1))
            self.current_bar_index = self._bar_first_tick_index.get((symbol, bar_index), 0)
        self.save_state()

    def stop(self):
        try:
            self.engine.client.shutdown()
        except Exception:
            pass


"""Trading simulator and backtest API routes."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import asdict, replace
from datetime import datetime
import math
from typing import Annotated, Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from apps.api.auth_utils import get_user_id_from_token
from apps.api.websocket import backtest_log_manager
from apps.utils.logger import logger
from apps.mt5 import get_mt5_api
from apps.mt5.client import MT5Client
from apps.risk.core import PortfolioStateEngine
from apps.risk.core.timeline_reconstructor import TimelineReconstructor
from apps.risk.core.governance_engine import GovernanceEngine
from apps.risk.core.portfolio_risk_engine import PortfolioRiskEngine
from apps.risk.core.recommendation_engine import RecommendationEngine
from apps.risk.core.risk_scorecard_engine import RiskScorecardEngine
from apps.risk.core.risk_snapshot_engine import RiskSnapshotEngine
from apps.risk.limits import RiskLimits
from apps.risk.models import PortfolioState
from apps.risk.metrics import RiskSnapshot
from apps.risk.scoring import RiskScorecard
from apps.risk.simulation import HypotheticalOrderAction, ReplayFrame, WhatIfEngine
from apps.risk.storage import RiskRepository, RiskSnapshotStore
from apps.trading import Engine, core
from apps.sqlite.database_operations import DatabaseManager
from apps.strategy import storage
from apps.utils.data_getters import load_dukascopy
from apps.utils.data_manipulator import TicksGenerator
from apps.utils.data_validator import DataValidator

router = APIRouter()
backtest_router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)
mt5 = get_mt5_api()


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
        self.symbol_digits = 5
        self.paused = False
        self.strategy = None
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
        if hasattr(self.strategy, "on_init"):
            self.strategy.on_init()

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
        number_of_bars = self.config.get("number_of_bars")
        start_time = self.config.get("start_time")
        end_time = self.config.get("end_time")
        if len(self.symbols) > 1 and self.strategy is not None:
            raise ValueError("Multi-symbol strategy simulation is not supported yet.")

        merged_ticks = []
        self.data_by_symbol = {}
        self.current_market_by_symbol = {}
        self.current_bar_index_by_symbol = {}
        self._bar_first_tick_index = {}

        for symbol in self.symbols:
            if number_of_bars:
                data = self.engine.client.get_bars(
                    symbol=symbol,
                    timeframe=timeframe,
                    count=int(number_of_bars),
                )
            else:
                date_from = datetime.fromisoformat(start_time.replace("Z", "+00:00")) if start_time else None
                date_to = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if end_time else None
                data = self.engine.client.get_bars(
                    symbol=symbol,
                    timeframe=timeframe,
                    date_from=date_from,
                    date_to=date_to,
                )
            if data is None or data.empty:
                raise ValueError(f"No historical bars loaded for simulator session: {symbol}")
            data = DataValidator.prepare_data(data)
            if self.strategy is not None and hasattr(self.strategy, "on_bar"):
                data = self.strategy.on_bar(data)
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
        self.tick_data = pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")
        for tick_index, (_, tick_row) in enumerate(self.tick_data.iterrows()):
            symbol = str(tick_row.get("_symbol", "") or "")
            bar_index = int(tick_row.get("_bar_index", 0) or 0)
            self._bar_first_tick_index.setdefault((symbol, bar_index), tick_index)

        self.total_bars = len(self.tick_data)
        if self.total_bars <= 0:
            raise ValueError("No ticks generated for simulator session")
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

        payload = row.to_dict()
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
                out[str(key)] = value
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

        current_positions = {
            str(sym): float(lots)
            for sym, lots in dict(state.position_map or {}).items()
            if abs(float(lots)) > 0.0
        }
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
        return governance.evaluate_add_position(
            current_positions=current_positions,
            candidate_symbol=str(symbol),
            candidate_lots=float(signed_volume),
        )

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

        limits = RiskLimits(
            var_cap_frac=max(0.0, float(self.config.get("risk_var_cap_frac", 0.10) or 0.10)),
            es_cap_frac=max(0.0, float(self.config.get("risk_es_cap_frac", 0.15) or 0.15)),
            delta_var_cap_frac=max(0.0, float(self.config.get("risk_delta_var_cap_frac", 0.02) or 0.02)),
            delta_es_cap_frac=max(0.0, float(self.config.get("risk_delta_es_cap_frac", 0.03) or 0.03)),
            max_margin_used_frac=max(0.0, float(self.config.get("risk_max_margin_used_frac", 0.50) or 0.50)),
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

        currency_exposure.sort(key=lambda item: abs(float(item.get("value") or 0.0)), reverse=True)
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

        def _json_safe_number(value: Any) -> Any:
            if isinstance(value, (int, float)):
                numeric = float(value)
                if not math.isfinite(numeric):
                    return None
                return numeric
            return value

        return {
            "portfolio_health_score": _json_safe_number(summary.get("portfolio_health_score")),
            "leverage_safety_score": _json_safe_number(summary.get("leverage_safety_score")),
            "margin_safety_score": _json_safe_number(summary.get("margin_safety_score")),
            "diversification_score": _json_safe_number(summary.get("diversification_score")),
            "governance_compliance_score": _json_safe_number(summary.get("governance_compliance_score")),
            "overall_risk_quality_score": _json_safe_number(summary.get("overall_risk_quality_score")),
            "overall_confidence": _json_safe_number(summary.get("overall_confidence")),
            "overall_confidence_label": summary.get("overall_confidence_label"),
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
            self.config.get("session_name")
            or f"Saved Simulation - {symbol} {timeframe}"
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
            description=f"Saved from simulation session {self.session_id}",
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
                return max(0, bar_index)
            except Exception:
                pass

        return max(0, min(int(fallback_index or 0), len(base_data.index) - 1))

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


def _normalize_position(position: dict) -> dict:
    pos_type = position.get("type")
    is_buy = pos_type == mt5.POSITION_TYPE_BUY or str(pos_type).lower() == "buy"
    return {
        "id": int(
            position.get("id")
            or position.get("ticket")
            or position.get("identifier")
            or 0
        ),
        "symbol": position.get("symbol", ""),
        "type": "buy" if is_buy else "sell",
        "volume": float(position.get("volume") or 0.0),
        "open_price": float(position.get("price_open") or 0.0),
        "price": float(
            position.get("price_current") or position.get("price_open") or 0.0
        ),
        "sl": float(position.get("sl") or 0.0),
        "tp": float(position.get("tp") or 0.0),
        "profit": float(position.get("profit") or 0.0),
        "swap": float(position.get("swap") or 0.0),
        "commission": float(position.get("commission") or 0.0),
        "margin_required": float(position.get("margin_required") or 0.0),
        "time": position.get("time"),
        "comment": position.get("comment", ""),
    }


def _position_notional_from_payload(active: SimulatorSession, position: dict) -> float:
    symbol_name = str(position.get("symbol", "") or "")
    if not symbol_name:
        return 0.0

    symbol_info = active.engine.symbol_info(symbol_name)
    contract_size = float(
        getattr(symbol_info, "trade_contract_size", 0.0) or 0.0
    )
    if contract_size <= 0.0:
        return 0.0

    market_price = float(
        position.get("price_current") or position.get("price_open") or 0.0
    )
    volume = float(position.get("volume") or 0.0)
    if market_price <= 0.0 or volume <= 0.0:
        return 0.0

    raw_notional = float(volume * contract_size * market_price)
    profit_currency = str(
        getattr(symbol_info, "currency_profit", getattr(symbol_info, "profit_currency", "")) or ""
    ).upper().strip()
    account_currency = _simulator_account_currency(active)
    return _convert_simulator_value_to_account_currency(
        active,
        raw_notional,
        profit_currency,
        account_currency,
    )


def _simulator_account_currency(active: SimulatorSession) -> str:
    if getattr(active, "latest_risk_state", None) is not None:
        currency = getattr(active.latest_risk_state.account, "currency", None)
        if currency:
            token = str(currency).upper().strip()
            if token:
                return token
    account = active.engine.account_info()
    token = str(account.get("currency") or account.get("currency_code") or "USD").upper().strip()
    return token or "USD"


def _convert_simulator_value_to_account_currency(
    active: SimulatorSession,
    value: float,
    source_currency: str,
    target_currency: str,
) -> float:
    amount = float(value or 0.0)
    source = str(source_currency or "").upper().strip()
    target = str(target_currency or "").upper().strip()
    if amount == 0.0 or not source or not target or source == target:
        return amount
    rate = _simulator_currency_conversion_rate(active, source, target)
    if rate is None or rate <= 0.0:
        return amount
    return float(amount * rate)


def _simulator_currency_conversion_rate(
    active: SimulatorSession,
    source: str,
    target: str,
) -> Optional[float]:
    if source == target:
        return 1.0

    direct = _simulator_direct_currency_conversion_rate(active, source, target)
    if direct is not None:
        return direct

    for bridge in ("USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD"):
        if bridge in {source, target}:
            continue
        leg_one = _simulator_direct_currency_conversion_rate(active, source, bridge)
        if leg_one is None:
            continue
        leg_two = _simulator_direct_currency_conversion_rate(active, bridge, target)
        if leg_two is None:
            continue
        return float(leg_one * leg_two)

    return None


def _simulator_direct_currency_conversion_rate(
    active: SimulatorSession,
    source: str,
    target: str,
) -> Optional[float]:
    direct_symbol = f"{source}{target}"
    direct_price = _simulator_price_for_symbol(active, direct_symbol)
    if direct_price is not None and direct_price > 0.0:
        return float(direct_price)

    inverse_symbol = f"{target}{source}"
    inverse_price = _simulator_price_for_symbol(active, inverse_symbol)
    if inverse_price is not None and inverse_price > 0.0:
        return float(1.0 / inverse_price)

    return None


def _simulator_price_for_symbol(active: SimulatorSession, symbol: str) -> Optional[float]:
    market = getattr(active, "current_market_by_symbol", {}).get(symbol)
    if market is not None:
        try:
            price = float(market.get("close", 0.0) or 0.0)
        except Exception:
            price = 0.0
        if price > 0.0:
            return price

    state = getattr(active, "latest_risk_state", None)
    if state is not None:
        market_state = state.markets.get(symbol)
        if market_state is not None and market_state.last_close is not None:
            try:
                price = float(market_state.last_close)
            except Exception:
                price = 0.0
            if price > 0.0:
                return price

    symbol_data = getattr(active, "data_by_symbol", {}).get(symbol)
    if symbol_data is not None and not symbol_data.empty:
        close_col = "close" if "close" in symbol_data.columns else "Close"
        if close_col in symbol_data.columns:
            try:
                price = float(symbol_data[close_col].iloc[-1])
            except Exception:
                price = 0.0
            if price > 0.0:
                return price

    return None


def _normalize_order(order: dict) -> dict:
    type_map = {
        mt5.ORDER_TYPE_BUY_LIMIT: "buy_limit",
        mt5.ORDER_TYPE_SELL_LIMIT: "sell_limit",
        mt5.ORDER_TYPE_BUY_STOP: "buy_stop",
        mt5.ORDER_TYPE_SELL_STOP: "sell_stop",
        mt5.ORDER_TYPE_BUY_STOP_LIMIT: "buy_stop_limit",
        mt5.ORDER_TYPE_SELL_STOP_LIMIT: "sell_stop_limit",
    }
    order_type = order.get("type")
    return {
        "id": int(
            order.get("ticket") or order.get("identifier") or order.get("id") or 0
        ),
        "symbol": order.get("symbol", ""),
        "type": type_map.get(order_type, str(order_type)),
        "volume": float(
            order.get("volume_current") or order.get("volume_initial") or 0.0
        ),
        "open_price": float(order.get("open_price") or order.get("price_open") or 0.0),
        "sl": float(order.get("sl") or 0.0),
        "tp": float(order.get("tp") or 0.0),
        "time": order.get("time"),
        "expiry_date": order.get("expiry_date"),
        "comment": order.get("comment", ""),
    }


def _position_info_to_dict(position: Any) -> dict:
    if isinstance(position, dict):
        return position
    if hasattr(position, "_asdict"):
        return dict(position._asdict())
    time_value = position.Time() if hasattr(position, "Time") else None
    return {
        "ticket": int(getattr(position, "ticket", 0) or 0),
        "identifier": int(getattr(position, "identifier", 0) or 0),
        "symbol": getattr(position, "symbol", ""),
        "type": int(getattr(position, "type", 0) or 0),
        "volume": float(getattr(position, "volume", 0.0) or 0.0),
        "price_open": float(getattr(position, "price_open", 0.0) or 0.0),
        "price_current": float(getattr(position, "price_current", 0.0) or 0.0),
        "sl": float(getattr(position, "sl", 0.0) or 0.0),
        "tp": float(getattr(position, "tp", 0.0) or 0.0),
        "profit": float(getattr(position, "profit", 0.0) or 0.0),
        "swap": float(getattr(position, "swap", 0.0) or 0.0),
        "commission": float(getattr(position, "commission", 0.0) or 0.0),
        "margin_required": float(getattr(position, "margin_required", 0.0) or 0.0),
        "time": int(time_value) if time_value is not None else None,
        "comment": getattr(position, "comment", ""),
    }


def _order_info_to_dict(order: Any) -> dict:
    if isinstance(order, dict):
        return order
    if hasattr(order, "_asdict"):
        return dict(order._asdict())
    time_value = order.TimeSetup() if hasattr(order, "TimeSetup") else None
    return {
        "ticket": int(getattr(order, "ticket", 0) or 0),
        "identifier": int(getattr(order, "position_id", 0) or 0),
        "symbol": getattr(order, "symbol", ""),
        "type": int(getattr(order, "type", 0) or 0),
        "volume_initial": float(getattr(order, "volume_initial", 0.0) or 0.0),
        "volume_current": float(getattr(order, "volume_current", 0.0) or 0.0),
        "price_open": float(getattr(order, "price_open", 0.0) or 0.0),
        "sl": float(getattr(order, "sl", 0.0) or 0.0),
        "tp": float(getattr(order, "tp", 0.0) or 0.0),
        "time": int(time_value) if time_value is not None else None,
        "comment": getattr(order, "comment", ""),
    }


def _collect_positions_orders(active: SimulatorSession) -> tuple[list[dict], list[dict]]:
    positions_raw = active.simulator._simulator.positions_get() or []
    orders_raw = active.simulator._simulator.orders_get() or []
    position_payloads = [_position_info_to_dict(pos) for pos in positions_raw]
    gross_notional = float(
        sum(_position_notional_from_payload(active, pos) for pos in position_payloads)
    )
    positions = []
    for pos in position_payloads:
        normalized = _normalize_position(pos)
        exposure = _position_notional_from_payload(active, pos)
        normalized["exposure"] = float(exposure)
        normalized["weight"] = float(exposure / gross_notional) if gross_notional > 0.0 else 0.0
        positions.append(normalized)
    orders = [_normalize_order(_order_info_to_dict(order)) for order in orders_raw]
    return positions, orders


def _serialize_limit_events(events: Optional[List[Any]]) -> list[dict]:
    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
        return value

    output: list[dict] = []
    for event in events or []:
        output.append(
            {
                "rule_key": getattr(event, "rule_key", None),
                "severity": getattr(event, "severity", None),
                "message": getattr(event, "message", None),
                "observed_value": _json_safe_number(getattr(event, "observed_value", None)),
                "threshold_value": _json_safe_number(getattr(event, "threshold_value", None)),
                "scope": getattr(event, "scope", "portfolio"),
                "scope_key": getattr(event, "scope_key", None),
            }
        )
    return output


def _serialize_governance_report(report: Any) -> dict:
    governance_state = getattr(report, "governance_state", None)
    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
            return numeric
        return value

    return {
        "decision": getattr(report, "decision", None),
        "reason": getattr(report, "reason", None),
        "compliance_state": getattr(governance_state, "status", None) if governance_state else None,
        "current_var": _json_safe_number(getattr(report, "current_var", None)),
        "new_var": _json_safe_number(getattr(report, "new_var", None)),
        "delta_var": _json_safe_number(getattr(report, "delta_var", None)),
        "current_es": _json_safe_number(getattr(report, "current_es", None)),
        "new_es": _json_safe_number(getattr(report, "new_es", None)),
        "delta_es": _json_safe_number(getattr(report, "delta_es", None)),
        "current_margin_used": _json_safe_number(getattr(report, "current_margin_used", None)),
        "new_margin_used": _json_safe_number(getattr(report, "new_margin_used", None)),
        "warnings": _serialize_limit_events(getattr(report, "warnings", None)),
        "breaches": _serialize_limit_events(getattr(report, "breaches", None)),
    }


def _serialize_recommendation_batch(batch: Any) -> dict:
    if batch is None:
        return {"items": []}

    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
            return numeric
        return value

    items = []
    for item in list(getattr(batch, "recommendations", []) or []):
        action = getattr(item, "action", None)
        score = getattr(item, "recommendation_score", None)
        if action is None or score is None:
            continue
        raw_action_type = str(getattr(action, "action_type", "") or "")
        display_action = raw_action_type
        if (
            raw_action_type == "rebalance"
            and _json_safe_number(getattr(score, "margin_used_delta", None)) is not None
        ):
            margin_delta = float(getattr(score, "margin_used_delta", 0.0) or 0.0)
            if margin_delta < 0:
                display_action = "cut_margin"
        items.append(
            {
                "action_type": raw_action_type,
                "display_action": display_action,
                "symbol": getattr(action, "symbol", None),
                "delta_lots": _json_safe_number(getattr(action, "delta_lots", None)),
                "usefulness_score": _json_safe_number(getattr(score, "usefulness_score", None)),
                "var_delta": _json_safe_number(getattr(score, "var_delta", None)),
                "es_delta": _json_safe_number(getattr(score, "es_delta", None)),
                "margin_used_delta": _json_safe_number(
                    getattr(score, "margin_used_delta", None)
                ),
                "governance_feasible": bool(getattr(item, "governance_feasible", False)),
                "explanation": getattr(item, "explanation", None),
            }
        )
    return {
        "items": items,
        "recommendation_count": int(
            batch.summary.get("recommendation_count", len(items)) or len(items)
        ),
        "feasible_count": int(batch.summary.get("feasible_count", 0) or 0),
        "top_action_type": batch.summary.get("top_action_type"),
        "top_action_symbol": batch.summary.get("top_action_symbol"),
        "top_usefulness_score": _json_safe_number(
            batch.summary.get("top_usefulness_score")
        ),
    }


def _apply_leverage_override_to_state(
    state: PortfolioState,
    leverage_override: int,
) -> PortfolioState:
    effective_leverage = max(1, int(leverage_override))
    current_leverage = float(
        state.account.metadata.get("leverage")
        or state.metadata.get("account_leverage")
        or 0.0
    )
    current_margin_used = float(state.account.margin_used or 0.0)
    if current_leverage > 0.0:
        projected_margin_used = current_margin_used * (current_leverage / effective_leverage)
    else:
        projected_margin_used = current_margin_used
    new_account_metadata = {
        **dict(state.account.metadata or {}),
        "leverage": effective_leverage,
    }
    new_account = replace(
        state.account,
        margin_used=float(projected_margin_used),
        free_margin=float(state.account.equity) - float(projected_margin_used),
        metadata=new_account_metadata,
    )
    new_metadata = {
        **dict(state.metadata or {}),
        "account_leverage": effective_leverage,
    }
    return replace(
        state,
        account=new_account,
        metadata=new_metadata,
    )


def _serialize_what_if_comparison(comparison: Any) -> dict:
    if comparison is None:
        return {}

    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
            return numeric
        return value

    summary = dict(getattr(comparison, "summary", {}) or {})
    projected_snapshot = getattr(comparison, "projected_snapshot", None)
    projected_scorecard = getattr(comparison, "projected_scorecard", None)
    projected_recommendations = getattr(comparison, "projected_recommendations", None)
    baseline_frame = getattr(comparison, "baseline_frame", None)

    return {
        "summary": {key: _json_safe_number(value) for key, value in summary.items()},
        "actions": [
            {
                "action_type": getattr(action, "action_type", None),
                "symbol": getattr(action, "symbol", None),
                "delta_lots": _json_safe_number(getattr(action, "delta_lots", None)),
                "target_lots": _json_safe_number(getattr(action, "target_lots", None)),
                "rationale": getattr(action, "rationale", None),
            }
            for action in list(getattr(comparison, "actions", []) or [])
        ],
        "baseline": {
            "compliance_state": baseline_frame.snapshot.summary.get("compliance_state")
            if baseline_frame is not None
            else None,
            "overall_risk_quality_score": _json_safe_number(
                baseline_frame.scorecard.summary.get("overall_risk_quality_score")
                if baseline_frame is not None
                else None
            ),
        },
        "projected": {
            "compliance_state": projected_snapshot.summary.get("compliance_state")
            if projected_snapshot is not None
            else None,
            "governance_decision": projected_snapshot.summary.get("governance_decision")
            if projected_snapshot is not None
            else None,
            "governance_reason": projected_snapshot.summary.get("governance_reason")
            if projected_snapshot is not None
            else None,
            "overall_risk_quality_score": _json_safe_number(
                projected_scorecard.summary.get("overall_risk_quality_score")
                if projected_scorecard is not None
                else None
            ),
            "risk_snapshot": {
                "portfolio_var": _json_safe_number(
                    projected_snapshot.summary.get("portfolio_var")
                    if projected_snapshot is not None
                    else None
                ),
                "portfolio_es": _json_safe_number(
                    projected_snapshot.summary.get("portfolio_es")
                    if projected_snapshot is not None
                    else None
                ),
                "margin_used": _json_safe_number(
                    projected_snapshot.summary.get("margin_used")
                    if projected_snapshot is not None
                    else None
                ),
                "compliance_state": projected_snapshot.summary.get("compliance_state")
                if projected_snapshot is not None
                else None,
            },
        },
        "projected_recommendations": _serialize_recommendation_batch(
            projected_recommendations
        ),
    }


def _refresh_session_risk_state(active: SimulatorSession) -> None:
    active.refresh_risk_state()


# session_id -> SimulatorSession
active_sessions: Dict[int, SimulatorSession] = {}


class SimulationStartRequest(BaseModel):
    """Request to start a simulation session."""

    session_name: Optional[str] = None
    symbol: str
    timeframe: str = "M1"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    number_of_bars: Optional[int] = None
    initial_balance: float = 10000.0
    speed_multiplier: float = 1.0
    commission: float = 7.0
    leverage: int = 400
    slippage_type: str = "fixed"
    slippage: float = 0.0
    slippage_min: float = 0.0
    slippage_max: float = 10.0
    spread_type: str = "use-broker"
    spread: float = 20.0
    spread_min: float = 10.0
    spread_max: float = 50.0
    data_resolution: str = "trading_timeframe"
    risk_confidence_level: float = 0.95
    risk_horizon_unit: str = "days"
    risk_horizon_value: int = 1
    risk_vol_lookback: int = 20
    risk_corr_lookback: int = 60
    risk_var_cap_frac: float = 0.10
    risk_es_cap_frac: float = 0.15
    risk_delta_var_cap_frac: float = 0.02
    risk_delta_es_cap_frac: float = 0.03
    risk_max_margin_used_frac: float = 0.50
    risk_max_single_rc_frac: float = 0.10
    risk_warning_utilization_frac: float = 0.90
    risk_limits_enforced: bool = True
    mode: str = Field(default="manual", description="manual | strategy | replay")

    strategy_id: Optional[int] = None
    strategy_version_id: Optional[int] = None
    strategy_params: Optional[Dict[str, Any]] = None

    replay_source: Optional[str] = None  # backtest | csv
    replay_backtest_id: Optional[int] = None
    replay_file_name: Optional[str] = None

    sma_period: Optional[int] = 14
    ema_period: Optional[int] = 14
    rsi_period: Optional[int] = 14
    indicators_enabled: bool = False
    indicator_sma_enabled: bool = False
    indicator_ema_enabled: bool = False
    indicator_rsi_enabled: bool = False


class SimulationUpdateRequest(BaseModel):
    """Request to update a simulation session."""

    speed_multiplier: Optional[float] = None
    paused: Optional[bool] = None
    indicators_enabled: Optional[bool] = None
    indicator_sma_enabled: Optional[bool] = None
    indicator_ema_enabled: Optional[bool] = None
    indicator_rsi_enabled: Optional[bool] = None


class ManualTradeRequest(BaseModel):
    """Request to execute a manual trade."""

    symbol: Optional[str] = None
    side: str = Field(..., description="buy | sell")
    volume: float = 0.1
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None


class PendingOrderRequest(BaseModel):
    """Request to place a pending order."""

    symbol: Optional[str] = None
    type: str = Field(
        ...,
        description="buy_limit | sell_limit | buy_stop | sell_stop | buy_stop_limit | sell_stop_limit",
    )
    volume: float
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None
    expiry_date: Optional[str] = None
    expiration_mode: Optional[str] = "gtc"


class PositionModifyRequest(BaseModel):
    """Request to modify a position."""

    sl: Optional[float] = None
    tp: Optional[float] = None


class OrderModifyRequest(BaseModel):
    """Request to modify a pending order."""

    volume: Optional[float] = None
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


class SeekRequest(BaseModel):
    """Request to seek to a bar index."""

    bar_index: Optional[int] = None
    target_time: Optional[str] = None


class AdvanceRequest(BaseModel):
    """Request to advance by N synchronized simulator frames."""

    count: int = 1


class WhatIfActionRequest(BaseModel):
    """One hypothetical non-mutating portfolio action."""

    action_type: str
    symbol: str
    delta_lots: Optional[float] = None
    target_lots: Optional[float] = None
    rationale: Optional[str] = None


class WhatIfRequest(BaseModel):
    """Request to evaluate a what-if scenario against the current simulator state."""

    actions: List[WhatIfActionRequest] = Field(default_factory=list)
    leverage_override: Optional[int] = None


def _load_strategy_class(user_id: int, strategy_id: int, version_id: int):
    version = db_manager.get_strategy_version(version_id)
    strategy = db_manager.get_strategy(strategy_id)
    if version is None:
        raise ValueError(f"Strategy version {version_id} not found")
    if strategy is None:
        raise ValueError(f"Strategy {strategy_id} not found")

    user = db_manager.get_user(user_id=user_id)
    username = (user.get("username") if user else "") or ""
    strategy_name = (strategy.get("name") if strategy else "") or ""

    strategy_class = storage.load_strategy_class(
        user_id=user_id,
        strategy_id=strategy_id,
        version=version["version"],
        username=username,
        strategy_name=strategy_name,
    )
    return strategy_class


def _resolve_strategy_version_id(strategy_id: int) -> int:
    strategy = db_manager.get_strategy(strategy_id)
    if not strategy or not strategy.get("active_version_id"):
        raise ValueError("Strategy or active version not found")
    return int(strategy["active_version_id"])


@router.post("/start")
async def start_simulation(
    request: SimulationStartRequest, authorization: str = AUTH_HEADER
):
    """Start a new simulation session."""
    try:
        user_id = get_user_id_from_token(authorization)
        config = request.dict()
        config["user_id"] = user_id

        session_id = db_manager.create_simulation_session(user_id, config)
        session = SimulatorSession(session_id=session_id, config=config, db=db_manager)

        if request.mode == "strategy":
            if not request.strategy_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="strategy_id is required for strategy mode",
                )
            version_id = (
                request.strategy_version_id
                if request.strategy_version_id
                else _resolve_strategy_version_id(request.strategy_id)
            )
            strategy_class = _load_strategy_class(
                user_id, request.strategy_id, version_id
            )
            params = request.strategy_params or {}
            params.setdefault("symbol", request.symbol)
            strategy_instance = strategy_class(params=params)
            session.set_strategy(strategy_instance)

        if request.mode == "replay":
            if request.replay_source == "csv" and not request.replay_backtest_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Import CSV via /api/import/sqx and provide replay_backtest_id",
                )
            if request.replay_backtest_id:
                trades = db_manager.get_backtest_trades(request.replay_backtest_id)
                session.set_replay_trades(trades)

        session.load_historical_bars()
        session.apply_mt5_account_defaults()
        session.refresh_risk_state()
        session.ensure_risk_run()
        db_manager.update_simulation_session(
            session_id,
            total_bars=session.total_bars,
            status="running",
            speed_multiplier=request.speed_multiplier,
        )

        active_sessions[session_id] = session
        credentials = db_manager.get_mt5_credentials(user_id) or {}
        company = ""
        try:
            account_info = session.engine.client.account_info()
            if account_info is not None:
                row = account_info._asdict() if hasattr(account_info, "_asdict") else {}
                company = str(row.get("company") or "")
        except Exception:
            company = ""
        return {
            "session_id": session_id,
            "status": "running",
            "total_bars": session.total_bars,
            "symbol_digits": session.symbol_digits,
            "risk_run_id": session.risk_run_id,
            "account_leverage": session.engine.account_info().get("leverage"),
            "account_login": credentials.get("login"),
            "account_server": credentials.get("server"),
            "account_company": company or None,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to start simulator session: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/sessions")
async def list_sessions(authorization: str = AUTH_HEADER):
    """List sessions for the authenticated user."""
    user_id = get_user_id_from_token(authorization)
    return db_manager.list_simulation_sessions(user_id=user_id)


@router.get("/paused")
async def list_paused_sessions(authorization: str = AUTH_HEADER):
    """List paused sessions for resume."""
    user_id = get_user_id_from_token(authorization)
    return db_manager.get_paused_simulation_sessions(user_id=user_id)


@router.get("/{session_id}")
async def get_session(session_id: int, authorization: str = AUTH_HEADER):
    """Get a simulation session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}")
async def update_session(  # noqa: C901
    session_id: int, request: SimulationUpdateRequest, authorization: str = AUTH_HEADER
):
    """Update speed or pause state."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if request.speed_multiplier is not None:
        db_manager.update_simulation_session(
            session_id, speed_multiplier=request.speed_multiplier
        )
        if active:
            active.speed_multiplier = float(request.speed_multiplier)

    if request.paused is not None and active:
        if request.paused:
            active.pause()
        else:
            active.resume()

    indicator_updates = {}
    if request.indicators_enabled is not None:
        indicator_updates["indicators_enabled"] = request.indicators_enabled
    if request.indicator_sma_enabled is not None:
        indicator_updates["indicator_sma_enabled"] = request.indicator_sma_enabled
    if request.indicator_ema_enabled is not None:
        indicator_updates["indicator_ema_enabled"] = request.indicator_ema_enabled
    if request.indicator_rsi_enabled is not None:
        indicator_updates["indicator_rsi_enabled"] = request.indicator_rsi_enabled

    if indicator_updates:
        session_config = dict(session.get("config") or {})
        session_config.update(indicator_updates)
        db_manager.update_simulation_session(session_id, config=session_config)
        if active:
            active.config.update(indicator_updates)

    return {"session_id": session_id, "status": "updated"}


@router.get("/{session_id}/bar/{bar_index}")
async def get_bar(session_id: int, bar_index: int, authorization: str = AUTH_HEADER):
    """Get a specific bar by index."""
    user_id = get_user_id_from_token(authorization)
    session_data = db_manager.get_simulation_session(session_id)
    if not session_data or session_data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    bar = active.get_bar(bar_index)
    if bar is None:
        raise HTTPException(status_code=404, detail="Bar not found")

    # Process bar through simulator for account updates
    account = active.process_bar_at_index(bar_index)
    indicators = active.get_indicators_at_index(bar_index)
    _refresh_session_risk_state(active)

    return {
        "bar": bar,
        "index": bar_index,
        "total_bars": active.total_bars,
        "digits": active.symbol_digits,
        "account": account,
        "indicators": indicators,
        "completed": bar_index >= active.total_bars - 1,
    }


@router.post("/{session_id}/advance")
async def advance_bars(
    session_id: int, request: AdvanceRequest, authorization: str = AUTH_HEADER
):
    """Advance the simulation by N bars and return them."""
    user_id = get_user_id_from_token(authorization)
    session_data = db_manager.get_simulation_session(session_id)
    if not session_data or session_data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    bars = active.advance_frames(request.count)

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)
    _refresh_session_risk_state(active)

    positions, orders = _collect_positions_orders(active)

    return {
        "bars": bars,
        "current_index": active.current_bar_index,
        "total_bars": active.total_bars,
        "digits": active.symbol_digits,
        "completed": active.current_bar_index >= active.total_bars,
        "positions": positions,
        "orders": orders,
        "market": active.get_market_snapshots(),
        "risk_snapshot": active.get_risk_summary(),
        "risk_scorecard": active.get_risk_score_summary(),
        "recommendations": active.get_recommendation_summary(),
        "governance": active.get_governance_report(),
    }


@router.get("/{session_id}/positions")
async def get_positions(session_id: int, authorization: str = AUTH_HEADER):
    """Get current positions and orders for a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)
    _refresh_session_risk_state(active)

    positions, orders = _collect_positions_orders(active)

    return {
        "positions": positions,
        "orders": orders,
        "market": active.get_market_snapshots(),
        "risk_snapshot": active.get_risk_summary(),
        "risk_scorecard": active.get_risk_score_summary(),
        "recommendations": active.get_recommendation_summary(),
        "governance": active.get_governance_report(),
        "account": {
            "balance": float(active.simulator._account_data.balance),
            "equity": float(active.simulator._account_data.equity),
            "margin": float(active.simulator._account_data.margin),
            "profit": float(active.simulator._account_data.profit),
            "margin_free": float(active.simulator._account_data.margin_free),
            "margin_level": float(active.simulator._account_data.margin_level),
        },
    }


@router.post("/{session_id}/trade")
async def execute_trade(
    session_id: int, request: ManualTradeRequest, authorization: str = AUTH_HEADER
):
    """Execute a manual trade within a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    signed_volume = abs(float(request.volume or 0.0))
    if str(request.side or "buy").lower() == "sell":
        signed_volume *= -1.0
    governance = active.evaluate_pre_trade_governance(
        symbol=str(request.symbol or active.symbols[0]).strip().upper() or active.symbols[0],
        signed_volume=signed_volume,
    )
    if (
        active.risk_limits_enforced()
        and governance is not None
        and str(getattr(governance, "decision", "ACCEPT")) != "ACCEPT"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "governance_reject",
                "governance": _serialize_governance_report(governance),
            },
        )

    trade = active.execute_trade(request.dict())
    if not trade:
        raise HTTPException(status_code=500, detail="Trade execution failed")

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)
    _refresh_session_risk_state(active)

    positions, orders = _collect_positions_orders(active)

    # Return updated positions and orders
    return {
        "trade": trade,
        "positions": positions,
        "orders": orders,
        "governance": active.get_governance_report() or (_serialize_governance_report(governance) if governance is not None else None),
        "risk_snapshot": active.get_risk_summary(),
        "risk_scorecard": active.get_risk_score_summary(),
        "recommendations": active.get_recommendation_summary(),
    }


@router.post("/{session_id}/order/pending")
async def place_pending_order(
    session_id: int, request: PendingOrderRequest, authorization: str = AUTH_HEADER
):
    """Place a pending order within a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    signed_volume = abs(float(request.volume or 0.0))
    if str(request.type or "").lower().startswith("sell"):
        signed_volume *= -1.0
    governance = active.evaluate_pre_trade_governance(
        symbol=str(request.symbol or active.symbols[0]).strip().upper() or active.symbols[0],
        signed_volume=signed_volume,
    )
    if (
        active.risk_limits_enforced()
        and governance is not None
        and str(getattr(governance, "decision", "ACCEPT")) != "ACCEPT"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "governance_reject",
                "governance": _serialize_governance_report(governance),
            },
        )

    order = active.place_pending_order(request.dict())
    if not order:
        raise HTTPException(status_code=500, detail="Pending order failed")

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)
    _refresh_session_risk_state(active)

    positions, orders = _collect_positions_orders(active)

    return {
        "order": order,
        "positions": positions,
        "orders": orders,
        "governance": active.get_governance_report() or (_serialize_governance_report(governance) if governance is not None else None),
        "risk_snapshot": active.get_risk_summary(),
        "risk_scorecard": active.get_risk_score_summary(),
        "recommendations": active.get_recommendation_summary(),
    }


@router.post("/{session_id}/what-if")
async def evaluate_what_if(
    session_id: int,
    request: WhatIfRequest,
    authorization: str = AUTH_HEADER,
):
    """Evaluate a hypothetical portfolio change without mutating the live simulator."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    _refresh_session_risk_state(active)
    actions = [
        HypotheticalOrderAction(
            action_type=str(item.action_type or "").strip(),
            symbol=str(item.symbol or "").strip().upper(),
            delta_lots=item.delta_lots,
            target_lots=item.target_lots,
            rationale=str(item.rationale or ""),
        )
        for item in request.actions
        if str(item.symbol or "").strip()
    ]
    comparison = active.evaluate_what_if(
        actions=actions,
        leverage_override=request.leverage_override,
    )
    storage_refs = active.persist_what_if_comparison(comparison)
    payload = _serialize_what_if_comparison(comparison)
    payload.update(storage_refs)
    return payload


@router.patch("/{session_id}/positions/{position_id}")
async def modify_position(
    session_id: int,
    position_id: int,
    request: PositionModifyRequest,
    authorization: str = AUTH_HEADER,
):
    """Modify a position's SL/TP."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(
            f"Modify position request | session={session_id} position={position_id} "
            f"sl={request.sl} tp={request.tp}"
        )

        pos = active.simulator._positions_data.get(int(position_id))
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")

        pos_data = _object_to_dict(pos)
        ok = active.simulator.modify_position(
            pos_data,
            new_sl=request.sl if request.sl is not None else pos_data.get("sl", 0.0),
            new_tp=request.tp if request.tp is not None else pos_data.get("tp", 0.0),
        )
        if not ok:
            logger.error(
                f"Modify position failed | session={session_id} position={position_id}"
            )
            raise HTTPException(status_code=500, detail="Failed to modify position")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)
        _refresh_session_risk_state(active)

        positions, orders = _collect_positions_orders(active)

        return {
            "positions": positions,
            "orders": orders,
            "market": active.get_market_snapshots(),
            "risk_snapshot": active.get_risk_summary(),
            "risk_scorecard": active.get_risk_score_summary(),
            "recommendations": active.get_recommendation_summary(),
            "governance": active.get_governance_report(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Modify position error | session={session_id} position={position_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to modify position")


@router.delete("/{session_id}/positions/{position_id}")
async def close_position(
    session_id: int,
    position_id: int,
    authorization: str = AUTH_HEADER,
):
    """Close a position."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(
            f"Close position request | session={session_id} position={position_id}"
        )

        pos = active.simulator._positions_data.get(int(position_id))
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")

        pos_data = _object_to_dict(pos)
        ok = active.simulator.close_position(pos_data, reason="manual")
        if not ok:
            logger.error(
                f"Close position failed | session={session_id} position={position_id}"
            )
            raise HTTPException(status_code=500, detail="Failed to close position")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)
        _refresh_session_risk_state(active)

        positions, orders = _collect_positions_orders(active)

        return {
            "positions": positions,
            "orders": orders,
            "market": active.get_market_snapshots(),
            "risk_snapshot": active.get_risk_summary(),
            "risk_scorecard": active.get_risk_score_summary(),
            "recommendations": active.get_recommendation_summary(),
            "governance": active.get_governance_report(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Close position error | session={session_id} position={position_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to close position")


@router.post("/{session_id}/positions/{position_id}/partial")
async def partial_close_position(
    session_id: int,
    position_id: int,
    request: Request,
    authorization: str = AUTH_HEADER,
):
    """Partially close a position by the given volume."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        body = await request.json()
        volume = float(body.get("volume", 0.0) or 0.0)
        if volume <= 0:
            raise HTTPException(status_code=400, detail="Volume must be > 0")

        logger.info(
            f"Partial close request | session={session_id} position={position_id} volume={volume}"
        )

        pos = active.simulator._positions_data.get(int(position_id))
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")

        pos_data = _object_to_dict(pos)
        current_volume = float(pos_data.get("volume", 0.0) or 0.0)

        if volume >= current_volume:
            # Full close
            ok = active.simulator.close_position(pos_data, reason="manual")
        else:
            # Partial close via Trade.PositionClosePartial
            symbol = str(pos_data.get("symbol", "") or "")
            ticket = int(pos_data.get("ticket") or pos_data.get("position_id") or pos_data.get("identifier") or 0)
            result = active.simulator.trade_api.PositionClosePartial(
                symbol=symbol,
                ticket=ticket,
                volume=volume,
            )
            ok = int(getattr(result, "retcode", 0) or 0) in (10008, 10009)

        if not ok:
            logger.error(
                f"Partial close failed | session={session_id} position={position_id}"
            )
            raise HTTPException(status_code=500, detail="Failed to close position")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)
        _refresh_session_risk_state(active)
        positions, orders = _collect_positions_orders(active)
        return {
            "positions": positions,
            "orders": orders,
            "market": active.get_market_snapshots(),
            "risk_snapshot": active.get_risk_summary(),
            "risk_scorecard": active.get_risk_score_summary(),
            "recommendations": active.get_recommendation_summary(),
            "governance": active.get_governance_report(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Partial close error | session={session_id} position={position_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to close position")


@router.patch("/{session_id}/orders/{order_id}")
async def modify_order(
    session_id: int,
    order_id: int,
    request: OrderModifyRequest,
    authorization: str = AUTH_HEADER,
):
    """Modify a pending order's price/SL/TP and optionally reduce its volume."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(
            f"Modify order request | session={session_id} order={order_id} "
            f"volume={request.volume} price={request.price} sl={request.sl} tp={request.tp}"
        )

        order = active.simulator._orders_data.get(int(order_id))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order_data = _object_to_dict(order)
        normalized_order = _normalize_order(_order_info_to_dict(order))
        current_volume = float(
            order_data.get("volume_current") or order_data.get("volume_initial") or 0.0
        )
        if request.volume is not None:
            if request.volume <= 0:
                raise HTTPException(status_code=400, detail="Volume must be > 0")
            if request.volume > current_volume:
                raise HTTPException(
                    status_code=400,
                    detail=f"Volume cannot exceed current order volume ({current_volume:.2f})",
                )

        new_price = (
            request.price if request.price is not None else order_data.get("open_price")
        )
        new_sl = float(request.sl if request.sl is not None else order_data.get("sl", 0.0))
        new_tp = float(request.tp if request.tp is not None else order_data.get("tp", 0.0))
        requested_volume = float(request.volume) if request.volume is not None else current_volume

        if request.volume is not None and abs(requested_volume - current_volume) > 1e-12:
            delete_ok = active.simulator.order_delete(order_data)
            if not delete_ok:
                logger.error(
                    f"Delete order before recreate failed | session={session_id} order={order_id}"
                )
                raise HTTPException(status_code=500, detail="Failed to modify order")

            recreated = active.place_pending_order(
                {
                    "type": str(normalized_order.get("type", "") or ""),
                    "volume": requested_volume,
                    "price": float(new_price or 0.0),
                    "sl": new_sl,
                    "tp": new_tp,
                    "comment": str(normalized_order.get("comment") or "Pending order"),
                }
            )
            if not recreated or int(recreated.get("retcode", 0) or 0) not in (10008, 10009):
                active.place_pending_order(
                    {
                        "type": str(normalized_order.get("type", "") or ""),
                        "volume": current_volume,
                        "price": float(normalized_order.get("open_price") or 0.0),
                        "sl": float(normalized_order.get("sl") or 0.0),
                        "tp": float(normalized_order.get("tp") or 0.0),
                        "comment": str(normalized_order.get("comment") or "Pending order"),
                    }
                )
                logger.error(f"Recreate order failed | session={session_id} order={order_id}")
                raise HTTPException(status_code=500, detail="Failed to modify order")
        else:
            ok = active.simulator.order_modify(
                order_data,
                new_open_price=float(new_price or 0.0),
                new_sl=new_sl,
                new_tp=new_tp,
            )
            if not ok:
                logger.error(f"Modify order failed | session={session_id} order={order_id}")
                raise HTTPException(status_code=500, detail="Failed to modify order")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)
        _refresh_session_risk_state(active)

        positions, orders = _collect_positions_orders(active)

        return {
            "positions": positions,
            "orders": orders,
            "market": active.get_market_snapshots(),
            "risk_snapshot": active.get_risk_summary(),
            "risk_scorecard": active.get_risk_score_summary(),
            "recommendations": active.get_recommendation_summary(),
            "governance": active.get_governance_report(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Modify order error | session={session_id} order={order_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to modify order")


@router.delete("/{session_id}/orders/{order_id}")
async def delete_order(
    session_id: int,
    order_id: int,
    authorization: str = AUTH_HEADER,
):
    """Delete a pending order."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(f"Delete order request | session={session_id} order={order_id}")

        order = active.simulator._orders_data.get(int(order_id))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order_data = _object_to_dict(order)
        ok = active.simulator.order_delete(order_data)
        if not ok:
            logger.error(f"Delete order failed | session={session_id} order={order_id}")
            raise HTTPException(status_code=500, detail="Failed to delete order")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)
        _refresh_session_risk_state(active)

        positions, orders = _collect_positions_orders(active)

        return {
            "positions": positions,
            "orders": orders,
            "market": active.get_market_snapshots(),
            "risk_snapshot": active.get_risk_summary(),
            "risk_scorecard": active.get_risk_score_summary(),
            "recommendations": active.get_recommendation_summary(),
            "governance": active.get_governance_report(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Delete order error | session={session_id} order={order_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to delete order")


@router.post("/{session_id}/resume")
async def resume_session(session_id: int, authorization: str = AUTH_HEADER):
    """Resume a paused session."""
    user_id = get_user_id_from_token(authorization)
    session_data = db_manager.get_simulation_session(session_id)
    if not session_data or session_data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if active:
        active.resume()
        return {"session_id": session_id, "status": "running"}

    config = session_data.get("config") or {}
    config["user_id"] = user_id
    config["current_bar_index"] = session_data.get("current_bar_index", 0)
    config["status"] = "running"

    session = SimulatorSession(session_id=session_id, config=config, db=db_manager)
    session.load_historical_bars()
    session.apply_mt5_account_defaults()
    session.refresh_risk_state()
    session.ensure_risk_run()
    active_sessions[session_id] = session
    db_manager.update_simulation_session(session_id, status="running")

    return {"session_id": session_id, "status": "running"}


@router.post("/{session_id}/seek")
async def seek_session(
    session_id: int, request: SeekRequest, authorization: str = AUTH_HEADER
):
    """Seek to a bar index."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    target_bar_index = active.resolve_base_bar_index(request.target_time, request.bar_index)
    active.seek_to_bar(target_bar_index)
    if active.current_bar_index < active.total_bars:
        active.process_bar_at_index(active.current_bar_index)
        _refresh_session_risk_state(active)
    return {"session_id": session_id, "bar_index": active.current_bar_index}


@router.delete("/{session_id}")
async def delete_session(session_id: int, authorization: str = AUTH_HEADER):
    """Delete a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.pop(session_id, None)
    if active:
        active.stop()

    db_manager.delete_simulation_session(session_id)
    return {"session_id": session_id, "status": "deleted"}


@router.post("/{session_id}/stop-and-save")
async def stop_and_save_session(session_id: int, authorization: str = AUTH_HEADER):
    """Stop a simulation session and persist it as a completed backtest run."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.pop(session_id, None)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    save_succeeded = False
    risk_snapshot_id: Optional[int] = None
    try:
        backtest_id = active.finalize_for_saved_backtest(user_id)
        _refresh_session_risk_state(active)
        risk_snapshot_id = active.persist_current_risk_bundle(backtest_id=backtest_id)
        save_succeeded = True
    except Exception as exc:
        active_sessions[session_id] = active
        logger.error(
            f"Stop and save session failed | session={session_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to save simulation")
    finally:
        if save_succeeded:
            with suppress(Exception):
                active.stop()

    db_manager.delete_simulation_session(session_id)
    return {
        "session_id": session_id,
        "status": "saved",
        "backtest_id": backtest_id,
        "risk_run_id": active.risk_run_id,
        "risk_snapshot_id": risk_snapshot_id,
    }


# ========================================
# Backtest Routes
# ========================================

class BacktestRequest(BaseModel):
    """Request payload for running a backtest."""

    symbol: str
    timeframe: str
    range_by: Optional[str] = "dates"  # "dates" or "bars"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    warmup_by: Optional[str] = "date"  # "date" or "bars"
    warmup_start_date: Optional[str] = None
    warmup_bars: Optional[int] = None
    initial_capital: float = 10000
    commission: float = 0.0
    slippage_type: Optional[str] = "fixed"
    slippage: int = 0
    slippage_min: int = 0
    slippage_max: int = 10
    spread_type: Optional[str] = "use-broker"
    spread: int = 20
    spread_min: int = 10
    spread_max: int = 50
    leverage: int = 100
    data_source: Optional[str] = "mt5"
    engine_type: Optional[str] = "simulator"
    data_resolution: Optional[str] = "trading_timeframe"
    position_sizing_method: Optional[str] = "fixed_lot"
    lot_size: float = 0.1
    risk_percent: float = 1.0
    base_lot_size: float = 0.1
    milestone_amount: float = 3000
    lot_increment: float = 0.2
    kelly_fraction_limit: float = 0.25
    fraction: float = 2.0
    fractional_factor: float = 2.0
    use_dynamic_stop_loss: bool = False
    atr_multiplier: float = 2.0
    win_rate: float = 0.55
    avg_win: float = 150.0
    avg_loss: float = 100.0
    alias: Optional[str] = None
    description: Optional[str] = None


class BacktestResponse(BaseModel):
    """Response model for backtest runs."""

    backtest_id: int
    strategy_id: Optional[int] = None
    strategy_version_id: Optional[int]
    status: str
    strategy_name: str
    symbol: Optional[str]
    timeframe: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    initial_balance: Optional[float]
    final_balance: Optional[float]
    total_trades: Optional[int]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    created_at: str
    completed_at: Optional[str]
    alias: Optional[str] = None
    description: Optional[str] = None
    engine_type: Optional[str] = None
    data_resolution: Optional[str] = None
    trades: Optional[List[Dict[str, Any]]] = None


class BacktestUpdateRequest(BaseModel):
    """Request payload for updating backtest metadata."""

    alias: Optional[str] = None
    description: Optional[str] = None


class PortfolioBacktestRequest(BaseModel):
    """Request payload for running a multi-symbol portfolio backtest."""

    symbols: str  # Comma-separated list of symbols
    timeframe: str
    range_by: Optional[str] = "dates"  # "dates" or "bars"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    warmup_by: Optional[str] = "date"  # "date" or "bars"
    warmup_start_date: Optional[str] = None
    warmup_bars: Optional[int] = None
    initial_capital: float = 50000  # Higher default for portfolio
    commission: float = 0.0
    slippage_type: Optional[str] = "fixed"
    slippage: int = 0
    slippage_min: int = 0
    slippage_max: int = 10
    spread_type: Optional[str] = "use-broker"
    spread: int = 20
    spread_min: int = 10
    spread_max: int = 50
    leverage: int = 100
    data_source: Optional[str] = "mt5"
    data_resolution: Optional[str] = "trading_timeframe"
    allocation_method: Optional[str] = "equal_weight"  # "equal_weight" or "risk_parity"
    lot_size: float = 0.1  # Base lot size per symbol
    position_sizing_method: Optional[str] = "fixed_lot"
    risk_percent: float = 1.0
    base_lot_size: float = 0.1
    milestone_amount: float = 3000
    lot_increment: float = 0.2
    kelly_fraction_limit: float = 0.25
    fraction: float = 2.0
    fractional_factor: float = 2.0
    use_dynamic_stop_loss: bool = False
    atr_multiplier: float = 2.0
    win_rate: float = 0.55
    avg_win: float = 150.0
    avg_loss: float = 100.0
    alias: Optional[str] = None
    description: Optional[str] = None


class PortfolioBacktestResponse(BaseModel):
    """Response model for portfolio backtest runs."""

    backtest_id: int
    status: str
    portfolio_name: str
    symbols: List[str]
    timeframe: str
    start_date: Optional[str]
    end_date: Optional[str]
    initial_balance: float
    final_balance: Optional[float]
    total_return: Optional[float]
    total_return_pct: Optional[float]
    total_trades: Optional[int]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown_pct: Optional[float]
    created_at: str
    completed_at: Optional[str]
    allocation_method: str
    asset_results: Optional[Dict[str, Dict[str, Any]]] = None


def _parse_request_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported date value: {value!r}")


def _parse_symbol(value: str) -> str:
    """Parse single symbol from string (for backward compatibility)."""
    symbols = [s.strip().upper() for s in value.split(",") if s.strip()]
    if not symbols:
        raise ValueError("Symbol is required")
    if len(symbols) > 1:
        raise ValueError(
            f"Multi-symbol backtest detected ({', '.join(symbols)}). "
            "Please use the POST /api/backtest/portfolio/run/{{strategy_id}} endpoint for multi-symbol backtests."
        )
    return symbols[0]


def _parse_symbols(value: str) -> List[str]:
    """Parse multiple symbols from comma-separated string."""
    symbols = [s.strip().upper() for s in value.split(",") if s.strip()]
    if not symbols:
        raise ValueError("At least one symbol is required")
    return symbols


def _resolve_modelling(mode: Optional[str]) -> str:
    resolved = str(mode or "trading_timeframe").strip().lower()
    allowed = {
        "trading_timeframe",
        "m1_ohlc",
        "synthetic_ticks",
        "real_ticks",
    }
    if resolved not in allowed:
        raise ValueError(f"Unsupported data_resolution: {mode}")
    return resolved


# ----------------------------
# Vectorized Engine Support
# ----------------------------
def _resolve_engine_type(value: Optional[str]) -> str:
    raw = str(value or "event_driven").strip().lower()
    if raw == "simulator":
        raw = "event_driven"
    raw = raw.replace("-", "_")
    if raw == "vectorized":
        raw = "vectorised"
    if raw not in {"event_driven", "vectorised"}:
        raise ValueError(f"Unsupported engine_type: {value}")
    return raw


def _load_mt5_bars(
    client: MT5Client,
    symbol: str,
    timeframe: str,
    request: BacktestRequest,
):
    if request.range_by == "bars":
        if request.number_of_bars is None:
            raise ValueError("number_of_bars is required when range_by='bars'")
        # Add warmup bars to the total count
        total_bars = request.number_of_bars
        if request.warmup_by == "bars" and request.warmup_bars:
            total_bars += request.warmup_bars
        return client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            count=total_bars,
        )

    # For date-based range, use warmup_start_date if provided
    start_date = _parse_request_date(request.start_date)
    if request.warmup_by == "date" and request.warmup_start_date:
        start_date = _parse_request_date(request.warmup_start_date)

    return client.get_bars(
        symbol=symbol,
        timeframe=timeframe,
        date_from=start_date,
        date_to=_parse_request_date(request.end_date),
    )


def _load_mt5_ticks(client: MT5Client, symbol: str, request: BacktestRequest):
    if request.range_by == "bars":
        if request.number_of_bars is None:
            raise ValueError("number_of_bars is required when range_by='bars'")
        tick_count = request.number_of_bars * 100
        # Add warmup bars to tick count estimate
        if request.warmup_by == "bars" and request.warmup_bars:
            tick_count += request.warmup_bars * 100
        return client.get_ticks(symbol=symbol, count=tick_count)

    # For date-based range, use warmup_start_date if provided
    start_date = _parse_request_date(request.start_date)
    if request.warmup_by == "date" and request.warmup_start_date:
        start_date = _parse_request_date(request.warmup_start_date)

    return client.get_ticks(
        symbol=symbol,
        start=start_date,
        end=_parse_request_date(request.end_date),
    )


def _load_data(  # noqa: C901
    request: BacktestRequest,
    symbol: str,
    data_mode: str,
    user_id: int,
) -> Tuple[Any, Optional[Any], str]:
    data_source = (request.data_source or "mt5").strip().lower()

    if data_source not in {"mt5", "metatrader5", "dukascopy"}:
        raise ValueError(f"Unsupported data_source: {request.data_source}")

    data = None
    step_data = None

    if data_source in {"mt5", "metatrader5"}:
        credentials = db_manager.get_mt5_credentials(user_id)
        client = MT5Client()
        if credentials:
            ok = client.connect(
                path=credentials.get("path", ""),
                login=credentials.get("login", 0),
                password=credentials.get("password", ""),
                server=credentials.get("server", ""),
            )
        else:
            ok = False
        if not ok:
            raise RuntimeError("Failed to connect to MT5")

        try:
            data = _load_mt5_bars(client, symbol, request.timeframe, request)
            if data is None or data.empty:
                raise ValueError("No trading timeframe data loaded from MT5")
            data = DataValidator.prepare_data(data)

            if data_mode in {"m1_ohlc", "synthetic_ticks"}:
                step_data = _load_mt5_bars(client, symbol, "M1", request)
                if step_data is None or step_data.empty:
                    raise ValueError("No M1 data loaded from MT5")
                step_data = DataValidator.prepare_data(step_data)
            elif data_mode == "real_ticks":
                step_data = _load_mt5_ticks(client, symbol, request)
                if step_data is None or len(step_data) == 0:
                    raise ValueError("No tick data loaded from MT5")
                step_data.columns = [str(c).lower() for c in step_data.columns]
        finally:
            client.shutdown()
    else:
        if request.range_by == "bars":
            if request.number_of_bars is None:
                raise ValueError("number_of_bars is required when range_by='bars'")
            # Add warmup bars to total count
            total_bars = request.number_of_bars
            if request.warmup_by == "bars" and request.warmup_bars:
                total_bars += request.warmup_bars
            data = load_dukascopy(
                symbol=symbol,
                timeframe=request.timeframe,
                count=total_bars,
            )
        else:
            # Use warmup_start_date if provided for date range
            start_date = request.start_date
            if request.warmup_by == "date" and request.warmup_start_date:
                start_date = request.warmup_start_date
            data = load_dukascopy(
                symbol=symbol,
                timeframe=request.timeframe,
                start_date=start_date,
                end_date=request.end_date,
            )

        if data is None or data.empty:
            raise ValueError("No trading timeframe data loaded from Dukascopy")
        data = DataValidator.prepare_data(data)

        if data_mode == "real_ticks":
            raise ValueError("Real ticks are not available for Dukascopy source")
        if data_mode in {"m1_ohlc", "synthetic_ticks"}:
            # Use warmup_start_date for M1 data as well
            start_date = request.start_date
            if request.warmup_by == "date" and request.warmup_start_date:
                start_date = request.warmup_start_date
            step_data = load_dukascopy(
                symbol=symbol,
                timeframe="M1",
                start_date=start_date,
                end_date=request.end_date,
            )
            if step_data is None or step_data.empty:
                raise ValueError("No M1 data loaded from Dukascopy")
            step_data = DataValidator.prepare_data(step_data)

    return data, step_data, data_source


def _load_strategy_class(user_id: int, strategy_id: int, version_id: int):
    version = db_manager.get_strategy_version(version_id)
    strategy = db_manager.get_strategy(strategy_id)
    if version is None:
        raise ValueError(f"Strategy version {version_id} not found")
    if strategy is None:
        raise ValueError(f"Strategy {strategy_id} not found")

    user = db_manager.get_user(user_id=user_id)
    username = (user.get("username") if user else "") or ""
    strategy_name = (strategy.get("name") if strategy else "") or ""

    strategy_class = storage.load_strategy_class(
        user_id=user_id,
        strategy_id=strategy_id,
        version=version["version"],
        username=username,
        strategy_name=strategy_name,
    )

    return version, strategy, strategy_class


def _seed_engine_account(engine: Engine, initial_capital: float) -> None:
    account = engine.account_info()
    account["balance"] = float(initial_capital)
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = float(initial_capital)
    account["margin"] = 0.0
    account["margin_free"] = float(initial_capital)
    account["margin_level"] = 0.0


def _normalize_position_sizing_method(value: Optional[str]) -> str:
    raw = str(value or "fixed_lot").strip().lower().replace("-", "_")
    mapping = {
        "fixed_lot": "fixed_lot",
        "fixed_percent": "fixed_risk",
        "fixed_risk": "fixed_risk",
        "milestone": "milestone",
        "kelly_criterion": "kelly",
        "kelly": "kelly",
        "volatility_adjusted_atr": "volatility",
        "volatility": "volatility",
        "fixed_fractional": "fixed_fractional",
    }
    return mapping.get(raw, "fixed_lot")


def _build_position_sizing_config(request: BacktestRequest, method: str) -> dict:
    if method == "fixed_risk":
        return {
            "risk_percent": float(request.risk_percent),
            "use_dynamic_stop_loss": bool(getattr(request, "use_dynamic_stop_loss", False)),
        }
    if method == "milestone":
        return {
            "initial_balance": float(request.initial_capital),
            "base_lot_size": float(request.base_lot_size),
            "milestone_amount": float(request.milestone_amount),
            "lot_increment": float(request.lot_increment),
        }
    if method == "kelly":
        return {
            "kelly_fraction_limit": float(request.kelly_fraction_limit),
            "win_rate": float(getattr(request, "win_rate", 0.55)),
            "avg_win": float(getattr(request, "avg_win", 150.0)),
            "avg_loss": float(getattr(request, "avg_loss", 100.0)),
        }
    if method == "volatility":
        return {
            "risk_percent": float(request.risk_percent),
            "atr_multiplier": float(getattr(request, "atr_multiplier", 2.0)),
        }
    if method == "fixed_fractional":
        return {
            "fraction": float(getattr(request, "fractional_factor", request.fraction)),
        }
    return {"lot_size": float(request.lot_size)}


def _configure_backtest_engine(
    engine: Engine,
    request: BacktestRequest,
    historical_data=None,
) -> None:
    account = engine.account_info()
    account["balance"] = float(request.initial_capital)
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = float(request.initial_capital)
    account["margin"] = 0.0
    account["margin_free"] = float(request.initial_capital)
    account["margin_level"] = 0.0
    account["commission"] = float(request.commission)
    account["leverage"] = int(request.leverage)

    engine.state.execution_settings = core.DotDict(
        {
            "slippage_model": str(request.slippage_type or "fixed"),
            "slippage_points": float(request.slippage or 0),
            "slippage_min": float(request.slippage_min or 0),
            "slippage_max": float(request.slippage_max or 0),
        }
    )

    method = _normalize_position_sizing_method(request.position_sizing_method)
    if method == "fixed_lot":
        engine.configure_position_sizing(enabled=False)
        return

    engine.configure_position_sizing(
        enabled=True,
        position_sizing_method=method,
        position_sizing_config=_build_position_sizing_config(request, method),
        historical_data=historical_data or {},
    )


def _ensure_engine_symbol(engine: Engine, symbol_name: str):
    for row in engine.state.trading_symbols:
        if str(getattr(row, "name", "") or "") == str(symbol_name):
            return row
    symbol_row = engine.client.symbol_info(symbol_name)
    if symbol_row is None:
        raise ValueError(f"Symbol info unavailable for {symbol_name}")
    engine.state.trading_symbols.append(symbol_row)
    return symbol_row


def _resolve_tick_generator_config(request: BacktestRequest, data_mode: str) -> tuple[str, str]:
    model_map = {
        "trading_timeframe": "timeframe_ticks",
        "m1_ohlc": "m1_ticks",
        "synthetic_ticks": "synthetic_ticks",
        "real_ticks": "real_ticks",
    }
    spread_map = {
        "use-broker": "native_spread",
        "broker": "native_spread",
        "fixed": "fixed_spread",
        "fixed_spread": "fixed_spread",
        "variable": "variable_spread",
        "variable_spread": "variable_spread",
    }
    tick_model = model_map.get(str(data_mode), "timeframe_ticks")
    spread_model = spread_map.get(str(request.spread_type or "use-broker").strip().lower(), "native_spread")
    return tick_model, spread_model


def _generate_ticks_for_backtest(
    engine: Engine,
    symbol_name: str,
    timeframe: str,
    request: BacktestRequest,
    data_mode: str,
    bars_data,
    step_data=None,
):
    symbol_info = _ensure_engine_symbol(engine, symbol_name)
    tick_model, spread_model = _resolve_tick_generator_config(request, data_mode)
    point_value = float(getattr(symbol_info, "point", 0.00001) or 0.00001)

    generator_kwargs = {
        "model": tick_model,
        "trading_timeframe": timeframe,
        "point_value": point_value,
        "spread_model": spread_model,
    }
    if spread_model == "fixed_spread":
        generator_kwargs["fixed_spread_points"] = float(request.spread or 0)
    elif spread_model == "variable_spread":
        generator_kwargs["min_spread_points"] = float(request.spread_min or 0)
        generator_kwargs["max_spread_points"] = float(request.spread_max or request.spread_min or 0)

    if tick_model == "m1_ticks":
        generator_kwargs["m1_data"] = step_data
    elif tick_model == "synthetic_ticks":
        generator_kwargs["m1_data"] = step_data
    elif tick_model == "real_ticks":
        generator_kwargs["real_ticks"] = step_data

    ticks_generator = TicksGenerator(**generator_kwargs)
    ticks_data = ticks_generator.generate(bars_data.copy())
    if ticks_data is None or ticks_data.empty:
        raise ValueError(f"No ticks generated for {symbol_name}")
    return ticks_data, tick_model



async def _run_backtest_task(
    backtest_id: int,
    user_id: int,
    strategy_id: int,
    version_id: int,
    request: BacktestRequest,
) -> None:
    """Background task to run a backtest using the simulator."""
    loop = asyncio.get_event_loop()

    def log_sink(record: Any) -> None:
        log_data = {
            "timestamp": record.time.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "source": record.name,
            "backtest_id": backtest_id,
        }
        with suppress(Exception):
            asyncio.run_coroutine_threadsafe(
                backtest_log_manager.broadcast(backtest_id, log_data), loop
            )

    handler_id = logger.add(log_sink, level="INFO", raw=True)

    try:
        await asyncio.sleep(2.0)
        db_manager.update_backtest_status(backtest_id, "running")

        symbol = _parse_symbol(request.symbol)
        engine_type = _resolve_engine_type(request.engine_type)
        data_mode = _resolve_modelling(request.data_resolution)
        if engine_type == "vectorised" and data_mode != "trading_timeframe":
            raise ValueError(
                "Vectorized engine only supports trading_timeframe data resolution"
            )

        version, strategy_meta, strategy_class = _load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
        )

        data, step_data, data_source = _load_data(
            request=request,
            symbol=symbol,
            data_mode=data_mode,
            user_id=user_id,
        )

        params = dict(version.get("parameters") or {})
        params["symbol"] = symbol
        params["timeframe"] = request.timeframe
        strategy_instance = strategy_class(params=params)
        if hasattr(strategy_instance, "on_init"):
            strategy_instance.on_init()
        if hasattr(strategy_instance, "on_bar"):
            data = strategy_instance.on_bar(data)

        engine = Engine(backend="sim")
        _configure_backtest_engine(
            engine,
            request,
            historical_data={symbol: {request.timeframe: data.copy()}},
        )
        _ensure_engine_symbol(engine, symbol)

        ticks_data, tick_model = _generate_ticks_for_backtest(
            engine=engine,
            symbol_name=symbol,
            timeframe=request.timeframe,
            request=request,
            data_mode=data_mode,
            bars_data=data,
            step_data=step_data,
        )

        logger.info(
            f"Running simulator backtest {backtest_id} | "
            f"symbol={symbol} timeframe={request.timeframe} "
            f"engine={engine_type} mode={data_mode} ticks_model={tick_model} source={data_source}"
        )

        engine.configure_run_schedule(
            positions_every=1,
            pending_orders_every=1,
            account_every=4,
            portfolio_every=4,
            risk_every=4,
        )
        processed = engine.run(
            ticks_data,
            position_size=float(request.lot_size),
            monitor_verbose=False,
            show_progress=False,
        )

        completed_trades = engine.get_completed_trades()
        equity_curve = engine.get_equity_curve()
        if completed_trades:
            db_manager.save_backtest_trades(backtest_id, completed_trades)
        if equity_curve:
            db_manager.save_backtest_equity_curve(backtest_id, equity_curve)

        final_balance = float(engine.account_info().get("balance", request.initial_capital) or request.initial_capital)
        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=final_balance,
        )
        logger.info(
            f"Backtest {backtest_id} completed successfully | processed_ticks={processed} trades={len(completed_trades)}"
        )
        engine.client.shutdown()

    except Exception as exc:
        logger.error(f"Backtest {backtest_id} failed: {exc}")
        db_manager.update_backtest_status(backtest_id, "failed")
    finally:
        try:
            logger.remove(handler_id)
            logger.info(f"WebSocket handler removed for backtest {backtest_id}")
        except Exception as exc:
            logger.warning(f"Error removing WebSocket handler: {exc}")

        try:
            await asyncio.sleep(5.0)
            await backtest_log_manager.clear_buffer(backtest_id)
            logger.info(f"Log buffer cleared for backtest {backtest_id}")
        except Exception as exc:
            logger.warning(f"Error clearing log buffer: {exc}")

        logger.info(f"Background task completed for backtest {backtest_id}")


@backtest_router.post("/run/{strategy_id}", response_model=BacktestResponse)
async def run_backtest(
    strategy_id: int,
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    authorization: Annotated[Optional[str], Header()] = None,
) -> BacktestResponse:
    """Run a backtest for a strategy."""
    try:
        user_id = get_user_id_from_token(authorization)
        symbol = _parse_symbol(request.symbol)
        engine_type = _resolve_engine_type(request.engine_type)

        strategy = db_manager.get_strategy(strategy_id)
        if not strategy or not strategy.get("active_version_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy or active version not found",
            )

        version_id = int(strategy["active_version_id"])
        start_dt = _parse_request_date(request.start_date) or datetime.utcnow()
        end_dt = _parse_request_date(request.end_date) or datetime.utcnow()

        backtest_id = db_manager.create_backtest_run(
            strategy_name=strategy["name"],
            strategy_version="1.0.0",
            start_date=start_dt,
            end_date=end_dt,
            engine_type=engine_type,
            data_resolution=request.data_resolution or "trading_timeframe",
            config_hash=str(hash((strategy_id, symbol, request.timeframe))),
            symbols=[symbol],
            timeframes=[request.timeframe],
            initial_balance=request.initial_capital,
            alias=request.alias,
            description=request.description,
            strategy_version_id=version_id,
            user_id=user_id,
        )

        background_tasks.add_task(
            _run_backtest_task,
            backtest_id=backtest_id,
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
            request=request,
        )

        backtest_run = db_manager.get_backtest_run(backtest_id)
        if backtest_run is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load backtest run",
            )

        response_data = {
            "backtest_id": backtest_run["backtest_id"],
            "strategy_version_id": backtest_run.get("strategy_version_id"),
            "status": backtest_run["status"],
            "strategy_name": backtest_run["strategy_name"],
            "symbol": symbol,
            "timeframe": request.timeframe,
            "start_date": backtest_run["start_date"],
            "end_date": backtest_run["end_date"],
            "initial_balance": backtest_run["initial_balance"],
            "final_balance": backtest_run.get("final_balance"),
            "total_trades": backtest_run.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "created_at": backtest_run["created_at"],
            "completed_at": backtest_run.get("completed_at"),
            "engine_type": engine_type,
            "data_resolution": request.data_resolution or "trading_timeframe",
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(f"Invalid backtest request: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Error starting backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start backtest: {str(exc)}",
        )


@backtest_router.get("/strategy/{strategy_id}", response_model=List[BacktestResponse])
async def list_strategy_backtests(strategy_id: int) -> List[BacktestResponse]:
    """List all backtests for a strategy."""
    try:
        strategy = db_manager.get_strategy(strategy_id)
        if not strategy or not strategy.get("active_version_id"):
            return []

        backtests = db_manager.get_all_backtests(
            strategy_version_id=strategy["active_version_id"]
        )

        response_list = []
        for bt in backtests:
            response_list.append(
                BacktestResponse(
                    backtest_id=bt["backtest_id"],
                    strategy_id=strategy_id,
                    strategy_version_id=bt.get("strategy_version_id"),
                    status=bt["status"],
                    strategy_name=bt["strategy_name"],
                    symbol=",".join(bt.get("symbols", []) or []) or None,
                    timeframe=(
                        bt.get("timeframes", [""])[0] if bt.get("timeframes") else None
                    ),
                    start_date=bt.get("start_date"),
                    end_date=bt.get("end_date"),
                    initial_balance=bt.get("initial_balance"),
                    final_balance=bt.get("final_balance"),
                    total_trades=bt.get("total_trades"),
                    win_rate=None,
                    profit_factor=None,
                    sharpe_ratio=None,
                    max_drawdown=None,
                    created_at=bt["created_at"],
                    completed_at=bt.get("completed_at"),
                    alias=bt.get("alias"),
                    description=bt.get("description"),
                    engine_type=bt.get("engine_type"),
                    data_resolution=bt.get("data_resolution"),
                )
            )

        return response_list

    except Exception as exc:
        logger.error(f"Error listing backtests: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backtests: {str(exc)}",
        )


@backtest_router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(backtest_id: int) -> BacktestResponse:
    """Get a specific backtest."""
    try:
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        trades = []
        with suppress(Exception):
            trades = db_manager.get_backtest_trades(backtest_id)

        response_data = {
            "backtest_id": backtest["backtest_id"],
            "strategy_id": backtest.get("strategy_id"),
            "strategy_version_id": backtest.get("strategy_version_id"),
            "status": backtest["status"],
            "strategy_name": backtest["strategy_name"],
            "symbol": ",".join(backtest.get("symbols", []) or []) or None,
            "timeframe": (
                backtest.get("timeframes", [""])[0]
                if backtest.get("timeframes")
                else None
            ),
            "start_date": backtest.get("start_date"),
            "end_date": backtest.get("end_date"),
            "initial_balance": backtest.get("initial_balance"),
            "final_balance": backtest.get("final_balance"),
            "total_trades": backtest.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "created_at": backtest["created_at"],
            "completed_at": backtest.get("completed_at"),
            "alias": backtest.get("alias"),
            "description": backtest.get("description"),
            "engine_type": backtest.get("engine_type"),
            "data_resolution": backtest.get("data_resolution"),
            "trades": trades,
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backtest: {str(exc)}",
        )


@backtest_router.websocket("/ws/{backtest_id}/logs")
async def backtest_logs_websocket(websocket: WebSocket, backtest_id: int) -> None:
    """Websocket endpoint for streaming backtest logs in real time."""
    logger.info(f"WebSocket connection attempt for backtest {backtest_id}")
    await backtest_log_manager.connect(backtest_id, websocket)
    logger.info(f"WebSocket connected for backtest {backtest_id}")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for backtest {backtest_id}")
        await backtest_log_manager.disconnect(backtest_id, websocket)
    except Exception as exc:
        logger.error(f"WebSocket error for backtest {backtest_id}: {exc}")
        await backtest_log_manager.disconnect(backtest_id, websocket)


@backtest_router.get("/", response_model=List[BacktestResponse])
async def list_all_backtests(
    user_id: int = 1, limit: int = 100
) -> List[BacktestResponse]:
    """List all backtests across all strategies."""
    try:
        backtests = db_manager.get_all_backtests(user_id=user_id, limit=limit)
        response_list = []
        for bt in backtests:
            response_list.append(
                BacktestResponse(
                    backtest_id=bt["backtest_id"],
                    strategy_id=bt.get("strategy_id"),
                    strategy_version_id=bt.get("strategy_version_id"),
                    status=bt["status"],
                    strategy_name=bt["strategy_name"],
                    symbol=",".join(bt.get("symbols", []) or []) or None,
                    timeframe=(
                        bt.get("timeframes", [""])[0] if bt.get("timeframes") else None
                    ),
                    start_date=bt.get("start_date"),
                    end_date=bt.get("end_date"),
                    initial_balance=bt.get("initial_balance"),
                    final_balance=bt.get("final_balance"),
                    total_trades=bt.get("total_trades"),
                    win_rate=None,
                    profit_factor=None,
                    sharpe_ratio=None,
                    max_drawdown=None,
                    created_at=bt["created_at"],
                    completed_at=bt.get("completed_at"),
                    alias=bt.get("alias"),
                    description=bt.get("description"),
                    engine_type=bt.get("engine_type"),
                    data_resolution=bt.get("data_resolution"),
                )
            )
        return response_list

    except Exception as exc:
        logger.error(f"Error listing all backtests: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list all backtests: {str(exc)}",
        )


@backtest_router.put("/{backtest_id}", response_model=BacktestResponse)
async def update_backtest(
    backtest_id: int, request: BacktestUpdateRequest
) -> BacktestResponse:
    """Update backtest metadata (alias, description)."""
    try:
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        if request.alias is not None or request.description is not None:
            db_manager.update_backtest_metadata(
                backtest_id=backtest_id,
                alias=request.alias,
                description=request.description,
            )

        updated = db_manager.get_backtest_run(backtest_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load backtest {backtest_id}",
            )

        response_data = {
            "backtest_id": updated["backtest_id"],
            "strategy_id": updated.get("strategy_id"),
            "strategy_version_id": updated.get("strategy_version_id"),
            "status": updated["status"],
            "strategy_name": updated["strategy_name"],
            "symbol": ",".join(updated.get("symbols", []) or []) or None,
            "timeframe": (
                updated.get("timeframes", [""])[0]
                if updated.get("timeframes")
                else None
            ),
            "start_date": updated.get("start_date"),
            "end_date": updated.get("end_date"),
            "initial_balance": updated.get("initial_balance"),
            "final_balance": updated.get("final_balance"),
            "total_trades": updated.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "created_at": updated["created_at"],
            "completed_at": updated.get("completed_at"),
            "alias": updated.get("alias"),
            "description": updated.get("description"),
            "engine_type": updated.get("engine_type"),
            "data_resolution": updated.get("data_resolution"),
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error updating backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update backtest: {str(exc)}",
        )


@backtest_router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest_endpoint(backtest_id: int) -> None:
    """Delete a backtest and all associated data."""
    try:
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        success = db_manager.delete_backtest(backtest_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete backtest {backtest_id}",
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error deleting backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete backtest: {str(exc)}",
        )


# ========================================
# Portfolio Backtest Endpoints
# ========================================


async def _run_portfolio_backtest_task(
    backtest_id: int,
    user_id: int,
    strategy_id: int,
    version_id: int,
    request: PortfolioBacktestRequest,
) -> None:
    """Background task to run a portfolio backtest."""
    loop = asyncio.get_event_loop()

    def log_sink(record: Any) -> None:
        log_data = {
            "timestamp": record.time.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "source": record.name,
            "backtest_id": backtest_id,
        }
        with suppress(Exception):
            asyncio.run_coroutine_threadsafe(
                backtest_log_manager.broadcast(backtest_id, log_data), loop
            )

    handler_id = logger.add(log_sink, level="INFO", raw=True)

    try:
        await asyncio.sleep(2.0)
        db_manager.update_backtest_status(backtest_id, "running")

        symbols = _parse_symbols(request.symbols)
        data_mode = _resolve_modelling(request.data_resolution)

        # Load strategy class
        version, strategy_meta, strategy_class = _load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
        )

        # Load data and create strategies for each symbol
        data_dict = {}
        strategy_dict = {}
        symbol_specs = {}

        for symbol in symbols:
            # Load data for this symbol
            data, step_data, data_source = _load_data(
                request=BacktestRequest(
                    symbol=symbol,
                    timeframe=request.timeframe,
                    range_by=request.range_by,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    number_of_bars=request.number_of_bars,
                    warmup_by=request.warmup_by,
                    warmup_start_date=request.warmup_start_date,
                    warmup_bars=request.warmup_bars,
                    initial_capital=request.initial_capital,
                    commission=request.commission,
                    slippage=request.slippage,
                    leverage=request.leverage,
                    data_source=request.data_source,
                    data_resolution=request.data_resolution,
                    lot_size=request.lot_size,
                ),
                symbol=symbol,
                data_mode=data_mode,
                user_id=user_id,
            )

            # Create strategy instance for this symbol
            params = dict(version.get("parameters") or {})
            params["symbol"] = symbol
            params["timeframe"] = request.timeframe
            strategy_instance = strategy_class(params=params)
            if hasattr(strategy_instance, "on_init"):
                strategy_instance.on_init()
            if hasattr(strategy_instance, "on_bar"):
                data = strategy_instance.on_bar(data)

            data_dict[symbol] = data
            strategy_dict[symbol] = strategy_instance

        engine = Engine(backend="sim")
        _configure_backtest_engine(
            engine,
            request,
            historical_data={
                symbol_name: {request.timeframe: symbol_data.copy()}
                for symbol_name, symbol_data in data_dict.items()
            },
        )

        merged_ticks = []
        tick_model_used = None
        for symbol in symbols:
            _ensure_engine_symbol(engine, symbol)
            ticks_data, tick_model = _generate_ticks_for_backtest(
                engine=engine,
                symbol_name=symbol,
                timeframe=request.timeframe,
                request=BacktestRequest(
                    symbol=symbol,
                    timeframe=request.timeframe,
                    range_by=request.range_by,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    number_of_bars=request.number_of_bars,
                    warmup_by=request.warmup_by,
                    warmup_start_date=request.warmup_start_date,
                    warmup_bars=request.warmup_bars,
                    initial_capital=request.initial_capital,
                    commission=request.commission,
                    slippage_type=request.slippage_type,
                    slippage=request.slippage,
                    spread_type=request.spread_type,
                    spread=request.spread,
                    spread_min=request.spread_min,
                    spread_max=request.spread_max,
                    leverage=request.leverage,
                    data_source=request.data_source,
                    engine_type="event_driven",
                    data_resolution=request.data_resolution,
                    lot_size=request.lot_size,
                    alias=request.alias,
                    description=request.description,
                ),
                data_mode=data_mode,
                bars_data=data_dict[symbol],
                step_data=None,
            )
            ticks_data = ticks_data.copy()
            ticks_data["symbol"] = symbol
            ticks_data["signal_timeframe"] = request.timeframe
            merged_ticks.append(ticks_data)
            tick_model_used = tick_model

        if not merged_ticks:
            raise ValueError("No merged portfolio ticks generated")

        portfolio_ticks = merged_ticks[0] if len(merged_ticks) == 1 else pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")

        logger.info(
            f"Running portfolio backtest {backtest_id} | "
            f"symbols={symbols} timeframe={request.timeframe} "
            f"allocation={request.allocation_method} ticks_model={tick_model_used}"
        )

        engine.configure_run_schedule(
            positions_every=1,
            pending_orders_every=1,
            account_every=4,
            portfolio_every=4,
            risk_every=4,
        )
        processed = engine.run(
            portfolio_ticks,
            position_size=float(request.lot_size),
            monitor_verbose=False,
            show_progress=False,
        )

        completed_trades = engine.get_completed_trades()
        equity_curve = engine.get_equity_curve()
        if completed_trades:
            db_manager.save_backtest_trades(backtest_id, completed_trades)
        if equity_curve:
            db_manager.save_backtest_equity_curve(backtest_id, equity_curve)

        final_balance = float(engine.account_info().get("balance", request.initial_capital) or request.initial_capital)
        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=final_balance,
        )

        logger.info(f"Portfolio backtest {backtest_id} completed successfully")
        logger.info(f"Final balance: ${final_balance:,.2f}")
        logger.info(f"Processed ticks: {processed} | Total trades: {len(completed_trades)}")
        engine.client.shutdown()

    except Exception as exc:
        logger.error(f"Portfolio backtest {backtest_id} failed: {exc}")
        db_manager.update_backtest_status(backtest_id, "failed")
    finally:
        try:
            logger.remove(handler_id)
            logger.info(
                f"WebSocket handler removed for portfolio backtest {backtest_id}"
            )
        except Exception as exc:
            logger.warning(f"Error removing WebSocket handler: {exc}")

        try:
            await asyncio.sleep(5.0)
            await backtest_log_manager.clear_buffer(backtest_id)
            logger.info(f"Log buffer cleared for portfolio backtest {backtest_id}")
        except Exception as exc:
            logger.warning(f"Error clearing log buffer: {exc}")

        logger.info(f"Portfolio backtest task completed for backtest {backtest_id}")


@backtest_router.post("/portfolio/run/{strategy_id}", response_model=PortfolioBacktestResponse)
async def run_portfolio_backtest(
    strategy_id: int,
    request: PortfolioBacktestRequest,
    background_tasks: BackgroundTasks,
    authorization: Annotated[Optional[str], Header()] = None,
) -> PortfolioBacktestResponse:
    """Run a portfolio backtest with multiple symbols."""
    try:
        user_id = get_user_id_from_token(authorization)
        symbols = _parse_symbols(request.symbols)

        strategy = db_manager.get_strategy(strategy_id)
        if not strategy or not strategy.get("active_version_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy or active version not found",
            )

        version_id = int(strategy["active_version_id"])
        start_dt = _parse_request_date(request.start_date) or datetime.utcnow()
        end_dt = _parse_request_date(request.end_date) or datetime.utcnow()

        # Create backtest run in database
        backtest_id = db_manager.create_backtest_run(
            strategy_name=strategy["name"],
            strategy_version="1.0.0",
            start_date=start_dt,
            end_date=end_dt,
            engine_type="event_driven",
            data_resolution=request.data_resolution or "trading_timeframe",
            config_hash=str(hash((strategy_id, tuple(symbols), request.timeframe))),
            symbols=symbols,
            timeframes=[request.timeframe],
            initial_balance=request.initial_capital,
            alias=request.alias,
            description=request.description,
            strategy_version_id=version_id,
            user_id=user_id,
        )

        # Add background task
        background_tasks.add_task(
            _run_portfolio_backtest_task,
            backtest_id=backtest_id,
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
            request=request,
        )

        backtest_run = db_manager.get_backtest_run(backtest_id)
        if backtest_run is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load backtest run",
            )

        response_data = {
            "backtest_id": backtest_run["backtest_id"],
            "status": backtest_run["status"],
            "portfolio_name": backtest_run["strategy_name"],
            "symbols": symbols,
            "timeframe": request.timeframe,
            "start_date": backtest_run["start_date"],
            "end_date": backtest_run["end_date"],
            "initial_balance": backtest_run["initial_balance"],
            "final_balance": backtest_run.get("final_balance"),
            "total_return": None,
            "total_return_pct": None,
            "total_trades": backtest_run.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown_pct": None,
            "created_at": backtest_run["created_at"],
            "completed_at": backtest_run.get("completed_at"),
            "allocation_method": request.allocation_method or "equal_weight",
            "asset_results": None,
        }

        return PortfolioBacktestResponse(**response_data)

    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(f"Invalid portfolio backtest request: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Error starting portfolio backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start portfolio backtest: {str(exc)}",
        )


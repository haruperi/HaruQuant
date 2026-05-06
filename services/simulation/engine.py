"""
Simulator engine execution and state management.
"""
import time
from typing import Any, Mapping

import pandas as pd

from services.data.mt5 import get_connected_mt5_client, get_mt5_api
from services.risk import (
    AllocationPlanner,
    CorrelationPreference,
    GovernanceEngine,
    PortfolioStateEngine,
    PositionSizer,
    PortfolioRiskEngine,
    RiskLimits,
    RiskRegimeDetector,
)
from services.execution.core import RunResult
from services.utils.logger import logger
from services.execution import core
from services.simulation.event_driven import run_event_driven_simulation
from services.simulation.position_sizing import (
    _position_sizer_config,
    _position_sizer_method,
)
from services.simulation.vectorized import run_vectorized_simulation

from services.simulation.config import AccountConfig, SimulationConfig


class _SimulationRiskSymbolInfo:
    def __init__(self, raw_symbol):
        self.raw_symbol = raw_symbol

    def __getattr__(self, name):
        return getattr(self.raw_symbol, name)

    def get(self, name, default=None):
        return getattr(self.raw_symbol, name, default)

    def get_contract_size(self):
        return float(getattr(self.raw_symbol, "trade_contract_size", 100000.0) or 100000.0)

    def get_lots_min(self):
        return float(getattr(self.raw_symbol, "volume_min", 0.01) or 0.01)

    def get_lots_max(self):
        return float(getattr(self.raw_symbol, "volume_max", 100.0) or 100.0)

    def get_lots_step(self):
        return float(getattr(self.raw_symbol, "volume_step", 0.01) or 0.01)


class _SimulationRiskAdapter:
    def __init__(self, engine, historical_data):
        self.engine = engine
        self.historical_data = historical_data or {}

    def get_account_equity(self):
        account = self.engine.account_info()
        return float(account.get("equity", account.get("balance", 0.0)) or 0.0)

    def get_account_currency(self):
        account = self.engine.account_info()
        return str(account.get("currency") or account.get("currency_code") or "USD")

    def get_symbol_info(self, symbol):
        sym = self.engine.symbol_info(symbol)
        if sym is None:
            return None
        return _SimulationRiskSymbolInfo(sym)

    def get_margin_required(self, symbol, lots):
        sym = self.engine.symbol_info(symbol)
        if sym is None:
            return None
        price = float(getattr(sym, "ask", getattr(sym, "bid", 0.0)) or 0.0)
        if price <= 0.0:
            return None
        return self.engine._strict_order_calc_margin(0, symbol, abs(float(lots)), price)

    def get_bars(self, symbol: str, timeframe: str, count: int = 100, start_pos: int = 0):
        symbol_frames = self.historical_data.get(str(symbol), {})
        df = symbol_frames.get(str(timeframe))
        if df is None or df.empty:
            return pd.DataFrame()

        out = df
        current_dt = getattr(self.engine.state, "current_tick_datetime", None)
        if current_dt is not None and isinstance(out.index, pd.DatetimeIndex):
            out = out[out.index <= pd.Timestamp(current_dt)]
        if out.empty:
            return pd.DataFrame()

        if start_pos and start_pos > 0:
            out = out.iloc[start_pos:]
        if count is not None and count > 0:
            out = out.tail(int(count))
        return out.copy()


class Engine:
    def __init__(self, backend="sim"):
        """
        Initialise trading engine.
        
        Args:
            backend (str): Backend to use. Options: "sim", "mt5".
        """

        self.backend = backend
        self.mt5 = get_mt5_api()
        self.client = get_connected_mt5_client()
        self.mt5_account = self.client.account_info()
        self.state = core.SimulatorState(account_info=self.mt5_account)
        if backend == "sim":
            self.api = self
        elif backend == "mt5":
            self.api = self.mt5
        else:
            raise ValueError(f"Unknown backend: {backend}")

        # Optional callback scheduler for future run-loop orchestration.
        # `None` disables a callback; positive int means "run every N ticks".
        self.run_schedule = {
            "auto": True,
            "positions": None,
            "pending_orders": None,
            "account": None,
            "portfolio": None,
            "risk": None,
        }
        self._schedule_state_dirty = True
        self.default_signal_volume = 0.01
        self.fast_mode = False
        self.risk_management = {
            "enabled": False,
            "position_sizer": None,
            "regime_detector": None,
            "governor": None,
            "allocator": None,
            "symbol_clusters": {},
            "risk_budgets": {},
            "historical_data": {},
            "governor_timeframe": None,
            "enable_regime_detection": False,
            "enable_allocation": False,
        }
        self.position_sizing = {
            "enabled": False,
            "position_sizer": None,
            "adapter": None,
        }
        self._risk_adapter = None
        self._portfolio_state_engine = PortfolioStateEngine()
        self._risk_equity_history = []
        self.equity_snapshot_policy = "bar_close"

        logger.info(f"successfully initialised trading engine {self.backend}")

    def run_vectorized(
        self,
        data,
        initial_balance=10000.0,
        contract_size=100000.0,
        position_size=0.01,
        commission_per_lot=0.0,
        slippage_model="none",
        slippage_points=0.0,
        slippage_min=None,
        slippage_max=None,
    ):
        """Run prepared tick data through the vectorized backend."""
        return run_vectorized_simulation(
            self,
            data,
            initial_balance=initial_balance,
            contract_size=contract_size,
            position_size=position_size,
            commission_per_lot=commission_per_lot,
            slippage_model=slippage_model,
            slippage_points=slippage_points,
            slippage_min=slippage_min,
            slippage_max=slippage_max,
        )

    def run(self, config: SimulationConfig | Mapping[str, Any]):
        """
        Public simulation entry point.

        The public contract is a simulation config dict or ``SimulationConfig``.
        Prepared tick DataFrames are executed through ``run_prepared``.
        """
        from services.simulation.runner import SimulationRunner

        return SimulationRunner(self).run(config)

    def run_prepared(self, prepared, config: SimulationConfig) -> int:
        """Execute already-prepared simulation data through the selected engine."""
        self.equity_snapshot_policy = str(
            getattr(config.reporting, "equity_snapshot_policy", "bar_close") or "bar_close"
        )
        self._configure_simulation_position_sizing(prepared, config)
        if config.engine_type == "vectorized":
            if self.equity_snapshot_policy not in {"bar_close", "position_update"}:
                logger.warning(
                    "Vectorized simulation currently supports only 'bar_close' and "
                    "'position_update' equity snapshots; "
                    f"falling back from {self.equity_snapshot_policy!r}."
                )
            if config.execution.position_size.type != "fixed_lot":
                logger.warning(
                    "Vectorized simulation does not support dynamic position sizing for %r; "
                    "falling back to the event-driven engine so size is resolved at order time.",
                    config.execution.position_size.type,
                )
                return int(
                    self.run_event_driven(
                        prepared.ticks,
                        position_size=None,
                        commission_per_lot=config.account.commission,
                        slippage_model=config.execution.slippage_model,
                        slippage_points=config.execution.slippage_points,
                        slippage_min=config.execution.slippage_min,
                        slippage_max=config.execution.slippage_max,
                    )
                    or 0
                )
            return int(
                self.run_vectorized(
                    prepared.ticks,
                    initial_balance=config.account.initial_balance,
                    contract_size=config.execution.contract_size,
                    position_size=float(config.execution.position_size.lot_size),
                    commission_per_lot=config.account.commission,
                    slippage_model=config.execution.slippage_model,
                    slippage_points=config.execution.slippage_points,
                    slippage_min=config.execution.slippage_min,
                    slippage_max=config.execution.slippage_max,
                )
                or 0
            )
        if config.engine_type == "event_driven":
            return int(
                self.run_event_driven(
                    prepared.ticks,
                    position_size=None,
                    commission_per_lot=config.account.commission,
                    slippage_model=config.execution.slippage_model,
                    slippage_points=config.execution.slippage_points,
                    slippage_min=config.execution.slippage_min,
                    slippage_max=config.execution.slippage_max,
                )
                or 0
            )
        raise ValueError(f"unsupported simulation engine_type: {config.engine_type}")

    def _configure_simulation_position_sizing(self, prepared, config: SimulationConfig) -> None:
        position_config = config.execution.position_size
        self.default_signal_volume = float(position_config.lot_size)
        historical_data = {
            str(symbol): {str(config.data.timeframe): frame.copy()}
            for symbol, frame in getattr(prepared, "signal_bars_by_symbol", {}).items()
        }
        self.configure_position_sizing(
            enabled=True,
            position_sizing_method=_position_sizer_method(position_config.type),
            position_sizing_config=_position_sizer_config(config, position_config),
            historical_data=historical_data,
        )

    def _strict_order_calc_profit(self, order_type, symbol, volume, price_open, price_close):
        if self.client is None or not hasattr(self.client, "order_calc_profit"):
            raise RuntimeError("MT5 order_calc_profit access is unavailable.")
        value = self.client.order_calc_profit(
            int(order_type),
            str(symbol),
            float(volume),
            float(price_open),
            float(price_close),
        )
        if value is None:
            raise RuntimeError("MT5 order_calc_profit returned None.")
        return float(value)

    def _strict_order_calc_margin(self, order_type, symbol, volume, price_open):
        if self.client is None or not hasattr(self.client, "order_calc_margin"):
            raise RuntimeError("MT5 order_calc_margin access is unavailable.")
        value = self.client.order_calc_margin(
            int(order_type),
            str(symbol),
            float(volume),
            float(price_open),
        )
        if value is None:
            raise RuntimeError("MT5 order_calc_margin returned None.")
        margin_value = float(value)
        if self.backend != "sim":
            return margin_value

        baseline_leverage = float(getattr(self.mt5_account, "leverage", 0.0) or 0.0)
        requested_leverage = float(self.account_info().get("leverage", baseline_leverage) or baseline_leverage)
        if baseline_leverage > 0.0 and requested_leverage > 0.0:
            margin_value = float(margin_value * (baseline_leverage / requested_leverage))
        return margin_value

    @staticmethod
    def _to_dict(value):
        if value is None:
            return {}
        if hasattr(value, "_asdict"):
            return dict(value._asdict())
        if isinstance(value, dict):
            return dict(value)
        try:
            return dict(vars(value))
        except Exception:
            return {}

    def _sync_live_state_to_simulator_state(self):
        """Mirror live MT5 account/orders/positions into simulator-shaped state."""
        if self.backend != "mt5":
            return

        account_raw = self.client.account_info() if self.client is not None else None
        account_data = self._to_dict(account_raw)
        self.state.trading_account = core.DotDict(account_data)

        self.state.trading_symbols = []
        self.state.trading_deals = []
        self.state.trading_orders = []

        positions = self.api.positions_get() if hasattr(self.api, "positions_get") else ()
        orders = self.api.orders_get() if hasattr(self.api, "orders_get") else ()

        symbol_names = set()
        for pos in positions or ():
            row = self._to_dict(pos)
            sym = str(row.get("symbol", "") or "")
            if sym:
                symbol_names.add(sym)
        for order in orders or ():
            row = self._to_dict(order)
            sym = str(row.get("symbol", "") or "")
            if sym:
                symbol_names.add(sym)

        symbol_map = {}
        for symbol in sorted(symbol_names):
            info_raw = self.api.symbol_info(symbol)
            info_dict = self._to_dict(info_raw)
            if not info_dict:
                continue
            symbol_map[symbol] = info_dict
            self.state.trading_symbols.append(core.SymbolInfo(info_dict))

        now = int(time.time())
        for pos in positions or ():
            row = self._to_dict(pos)
            symbol = str(row.get("symbol", "") or "")
            if not symbol:
                continue

            order_type = int(row.get("type", 0) or 0)
            volume = float(row.get("volume", 0.0) or 0.0)
            price_open = float(row.get("price_open", row.get("price_current", 0.0)) or 0.0)

            sym = symbol_map.get(symbol, {})
            bid = float(sym.get("bid", 0.0) or 0.0)
            ask = float(sym.get("ask", 0.0) or 0.0)
            close_price = bid if order_type == 0 else ask
            if close_price <= 0.0:
                close_price = float(row.get("price_current", price_open) or price_open)

            profit = float(row.get("profit", 0.0) or 0.0)
            margin_required = float(row.get("margin", 0.0) or 0.0)
            try:
                if volume > 0.0 and price_open > 0.0 and close_price > 0.0:
                    profit_calc = self.client.order_calc_profit(
                        order_type, symbol, volume, price_open, close_price
                    )
                    if profit_calc is not None:
                        profit = float(profit_calc)
                    margin_calc = self.client.order_calc_margin(
                        order_type, symbol, volume, price_open
                    )
                    if margin_calc is not None:
                        margin_required = float(margin_calc)
            except Exception:
                pass

            ticket = int(
                row.get("ticket", row.get("identifier", row.get("position_id", 0))) or 0
            )
            deal_row = core.DealInfo(
                ticket=ticket,
                order=int(row.get("order", ticket) or ticket),
                time=int(row.get("time", now) or now),
                time_msc=int(row.get("time_msc", now * 1000) or now * 1000),
                time_update=int(row.get("time_update", now) or now),
                time_update_msc=int(row.get("time_update_msc", now * 1000) or now * 1000),
                type=order_type,
                entry=0,  # open position in simulator convention
                magic=int(row.get("magic", 0) or 0),
                reason=int(row.get("reason", 0) or 0),
                position_id=int(row.get("identifier", ticket) or ticket),
                volume=volume,
                price=float(row.get("price_current", price_open) or price_open),
                price_open=price_open,
                price_current=close_price,
                sl=float(row.get("sl", 0.0) or 0.0),
                tp=float(row.get("tp", 0.0) or 0.0),
                margin_required=margin_required,
                commission=float(row.get("commission", 0.0) or 0.0),
                swap=float(row.get("swap", 0.0) or 0.0),
                profit=profit,
                fee=float(row.get("fee", 0.0) or 0.0),
                symbol=symbol,
                comment=str(row.get("comment", "") or ""),
                external_id=str(row.get("external_id", "") or ""),
            )
            self.state.trading_deals.append(deal_row)

        for order in orders or ():
            row = self._to_dict(order)
            order_type = int(row.get("type", -1) or -1)
            if order_type not in (2, 3, 4, 5):
                continue
            order_row = core.OrderInfo(
                action="order_open",
                ticket=int(row.get("ticket", 0) or 0),
                time_setup=int(row.get("time_setup", now) or now),
                time_setup_msc=int(row.get("time_setup_msc", now * 1000) or now * 1000),
                time_done=int(row.get("time_done", 0) or 0),
                time_done_msc=int(row.get("time_done_msc", 0) or 0),
                time_expiration=int(row.get("time_expiration", 0) or 0),
                type=order_type,
                type_time=int(row.get("type_time", 0) or 0),
                type_filling=int(row.get("type_filling", 0) or 0),
                state=int(row.get("state", 1) or 1),
                magic=int(row.get("magic", 0) or 0),
                reason=int(row.get("reason", 0) or 0),
                position_id=int(row.get("position_id", 0) or 0),
                position_by_id=int(row.get("position_by_id", 0) or 0),
                volume_initial=float(
                    row.get("volume_initial", row.get("volume_current", row.get("volume", 0.0)))
                    or 0.0
                ),
                volume_current=float(
                    row.get("volume_current", row.get("volume_initial", row.get("volume", 0.0)))
                    or 0.0
                ),
                price_open=float(row.get("price_open", row.get("price_current", 0.0)) or 0.0),
                sl=float(row.get("sl", 0.0) or 0.0),
                tp=float(row.get("tp", 0.0) or 0.0),
                price_current=float(row.get("price_current", row.get("price_open", 0.0)) or 0.0),
                price_stoplimit=float(row.get("price_stoplimit", 0.0) or 0.0),
                symbol=str(row.get("symbol", "") or ""),
                comment=str(row.get("comment", "") or ""),
                external_id=str(row.get("external_id", "") or ""),
                margin_required=float(row.get("margin_required", 0.0) or 0.0),
            )
            self.state.trading_orders.append(order_row)

    def account_info(self):
        return self.state.trading_account

    def terminal_info(self):
        return self.state.terminal_info

    @property
    def trading_symbols(self):
        return self.state.trading_symbols

    @property
    def trading_deals(self):
        return self.state.trading_deals

    @property
    def trading_history_deals(self):
        return self.state.trading_history_deals

    @property
    def trading_orders(self):
        return self.state.trading_orders

    @property
    def trading_history_orders(self):
        return self.state.trading_history_orders

    @property
    def completed_trades(self):
        return self.state.completed_trade_records

    @property
    def equity_curve(self):
        return self.state.completed_equity_curve

    def get_completed_trades(self):
        return list(self.state.completed_trade_records)

    def get_equity_curve(self):
        return list(self.state.completed_equity_curve)

    def get_run_result(self, processed_ticks: int = 0):
        _ = processed_ticks # no longer stored in RunResult
        return RunResult(
            trades=self.get_completed_trades(),
            equity_curve=self.get_equity_curve(),
        )

    def reset_runtime(self, account_config: AccountConfig):
        """Reset simulator runtime state to a clean account baseline."""
        if not isinstance(account_config, AccountConfig):
            raise TypeError("account_config must be an AccountConfig instance")

        if self.backend != "sim":
            self._sync_live_state_to_simulator_state()
            return self.account_info()

        account = self.account_info()
        if account is None:
            self.state.trading_account = core.DotDict()
            account = self.state.trading_account

        preserved_currency = str(
            account.get("currency")
            or account.get("currency_code")
            or account_config.currency
            or "USD"
        ).upper()

        account["balance"] = float(account_config.initial_balance)
        account["credit"] = 0.0
        account["profit"] = 0.0
        account["equity"] = float(account_config.initial_balance)
        account["margin"] = 0.0
        account["margin_free"] = float(account_config.initial_balance)
        account["margin_level"] = 0.0
        account["commission"] = float(account_config.commission)
        leverage = int(account_config.leverage)
        if leverage == 0:
            leverage = int(getattr(self.mt5_account, "leverage", 0.0) or 400)
            logger.info(f"Inheriting MT5 account leverage: {leverage}")
        
        account["leverage"] = leverage
        account["currency"] = preserved_currency

        self.state.trading_deals = []
        self.state.trading_history_deals = []
        self.state.trading_orders = []
        self.state.trading_history_orders = []
        self.state.current_tick_epoch = None
        self.state.current_tick_datetime = None
        self.state.execution_settings = core.DotDict()
        self.equity_snapshot_policy = "bar_close"
        self.clear_completed_trades()
        self._risk_equity_history = []
        self._schedule_state_dirty = True
        return account

    def clear_completed_trades(self):
        self.state.completed_trade_records = []
        self.state.completed_equity_curve = []
        self.state.equity_peak = None
        self.state.open_trade_records_by_ticket = {}
        self.state.open_trade_trackers_by_ticket = {}

    def history_deals_get(self, date_from=None, date_to=None, group=None, ticket=None):
        return core.history_deals_get(self.state, date_from, date_to, group, ticket)

    def history_deals_total(self, date_from, date_to):
        return core.history_deals_total(self.state, date_from, date_to)

    def positions_get(self, symbol=None, group=None, ticket=None):
        return core.positions_get(self.state, symbol=symbol, group=group, ticket=ticket)

    def positions_total(self):
        return core.positions_total(self.state)
        
    def orders_get(self, symbol=None, group=None, ticket=None):
        return core.orders_get(self.state, symbol=symbol, group=group, ticket=ticket)

    def orders_total(self):
        return core.orders_total(self.state)
        
    def history_orders_get(self, date_from=None, date_to=None, group=None, ticket=None):
        return core.history_orders_get(self.state, date_from=date_from, date_to=date_to, group=group, ticket=ticket)
        
    def history_orders_total(self, date_from, date_to):
        return core.history_orders_total(self.state, date_from=date_from, date_to=date_to)
        
    def symbols_get(self, group=None):
        return core.symbols_get(self.state, group=group)
        
    def symbols_total(self):
        return core.symbols_total(self.state)
        
    def symbol_info(self, name: str):
        return core.symbol_info(self.state, name)

    def symbol_info_tick(self, name: str):
        # In the simulator, the tick information (bid/ask/last) is stored on the symbol object itself
        return core.symbol_info(self.state, name)

    def order_send(self, request, verbose: bool = False):
        return core.order_send(
            self.state,
            request,
            profit_calculator=self._strict_order_calc_profit,
            margin_calculator=self._strict_order_calc_margin,
            strict_calc_access=True,
            verbose=verbose,
        )

    @staticmethod
    def _signal_to_float_array(data, col_name_map, names):
        for name in names:
            col = col_name_map.get(name)
            if col is not None:
                return data[col].fillna(0.0).to_numpy(dtype="float64", copy=False)
        return None

    @staticmethod
    def _signal_to_object_array(data, col_name_map, names):
        for name in names:
            col = col_name_map.get(name)
            if col is not None:
                return data[col].to_numpy(copy=False)
        return None

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _safe_int(value, default=0):
        try:
            if value is None:
                return int(default)
            return int(value)
        except Exception:
            return int(default)

    def _build_symbol_map(self):
        symbol_map = {}
        mutable_symbols = []
        replaced_any = False
        for sym in self.state.trading_symbols:
            mutable = sym
            if not isinstance(sym, core.SymbolInfo):
                row = self._to_dict(sym)
                if row:
                    mutable = core.SymbolInfo(row)
                    replaced_any = True
            mutable_symbols.append(mutable)
            name = str(getattr(mutable, "name", "") or "")
            if name and name not in symbol_map:
                symbol_map[name] = mutable
        if replaced_any:
            self.state.trading_symbols = mutable_symbols
        return symbol_map

    def _default_run_symbol(self):
        if not self.state.trading_symbols:
            return None
        first = self.state.trading_symbols[0]
        name = str(getattr(first, "name", "") or "")
        return name or None

    def _resolve_tick_symbol(self, idx, symbol_values, default_symbol):
        if symbol_values is None:
            return default_symbol
        value = symbol_values[idx]
        symbol = str(value or "")
        return symbol or default_symbol

    def _update_symbol_tick(self, symbol_map, symbol_name, bid, ask):
        if not symbol_name:
            return
        sym = symbol_map.get(symbol_name)
        if sym is None:
            return
        try:
            sym.bid = float(bid)
            sym.ask = float(ask)
            sym.last = float(bid)
        except Exception:
            return

    def _order_type_from_pending_signal(self, pending_signal):
        # Strategy base contract:
        #  1=BUY_STOP, -1=SELL_STOP, 2=BUY_LIMIT, -2=SELL_LIMIT
        code = self._safe_int(pending_signal, 0)
        mapping = {
            1: 4,   # ORDER_TYPE_BUY_STOP
            -1: 5,  # ORDER_TYPE_SELL_STOP
            2: 2,   # ORDER_TYPE_BUY_LIMIT
            -2: 3,  # ORDER_TYPE_SELL_LIMIT
        }
        return mapping.get(code)

    def _iter_positions_for_exit(self, symbol_name, exit_signal):
        # exit_signal: 1=Exit Buy (close long), -1=Exit Sell (close short)
        target_type = 0 if self._safe_int(exit_signal, 0) == 1 else 1
        for pos in list(self.state.trading_deals):
            if str(getattr(pos, "symbol", "") or "") != symbol_name:
                continue
            if self._safe_int(getattr(pos, "type", -1), -1) != target_type:
                continue
            yield pos

    def _iter_pending_for_cancel(self, symbol_name, cancel_pending_signal):
        pending_type = self._order_type_from_pending_signal(cancel_pending_signal)
        if pending_type is None:
            return
        for order in list(self.state.trading_orders):
            if str(getattr(order, "symbol", "") or "") != symbol_name:
                continue
            if self._safe_int(getattr(order, "type", -1), -1) != pending_type:
                continue
            yield order

    def _exec_exit_signal(self, symbol_name, exit_signal, bid, ask, verbose: bool = False):
        side = self._safe_int(exit_signal, 0)
        if side not in (1, -1):
            return False
        changed = False
        for pos in self._iter_positions_for_exit(symbol_name, side):
            pos_type = self._safe_int(getattr(pos, "type", -1), -1)
            close_type = 1 if pos_type == 0 else 0
            close_price = float(bid) if close_type == 1 else float(ask)
            request = {
                "action": 1,  # TRADE_ACTION_DEAL
                "symbol": symbol_name,
                "type": close_type,
                "position": self._safe_int(
                    getattr(
                        pos,
                        "ticket",
                        getattr(pos, "position_id", getattr(pos, "identifier", 0)),
                    ),
                    0,
                ),
                "volume": self._safe_float(getattr(pos, "volume", 0.0), 0.0),
                "price": close_price,
            }
            result = self.order_send(request, verbose=verbose)
            if self._safe_int(getattr(result, "retcode", 0), 0) in (10008, 10009):
                changed = True
        return changed

    def _exec_entry_signal(
        self,
        symbol_name,
        entry_signal,
        bid,
        ask,
        sl=0.0,
        tp=0.0,
        volume=None,
        verbose: bool = False,
    ):
        side = self._safe_int(entry_signal, 0)
        if side not in (1, -1):
            return False
        order_type = 0 if side == 1 else 1  # BUY / SELL
        open_price = float(ask) if side == 1 else float(bid)
        lot_size = self._resolve_signal_volume(
            symbol_name,
            "buy" if side == 1 else "sell",
            open_price,
            stop_loss=sl,
            fallback_volume=volume,
        )
        request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": symbol_name,
            "type": order_type,
            "volume": lot_size,
            "price": open_price,
            "sl": float(self._safe_float(sl, 0.0)),
            "tp": float(self._safe_float(tp, 0.0)),
            "comment": "Signal entry",
        }
        result = self.order_send(request, verbose=verbose)
        return self._safe_int(getattr(result, "retcode", 0), 0) in (10008, 10009)

    def _exec_pending_signal(
        self,
        symbol_name,
        pending_signal,
        bid,
        ask,
        signal_price=None,
        sl=0.0,
        tp=0.0,
        volume=None,
        verbose: bool = False,
    ):
        order_type = self._order_type_from_pending_signal(pending_signal)
        if order_type is None:
            return False
        price = self._safe_float(signal_price, 0.0)
        if price <= 0.0:
            # Fallback if strategy did not provide pending price.
            if order_type in (2, 4):  # buy limit / buy stop
                price = float(ask)
            else:  # sell limit / sell stop
                price = float(bid)
        lot_size = self._resolve_signal_volume(
            symbol_name,
            "buy" if order_type in (2, 4) else "sell",
            float(price),
            stop_loss=sl,
            fallback_volume=volume,
        )
        request = {
            "action": 5,  # TRADE_ACTION_PENDING
            "symbol": symbol_name,
            "type": order_type,
            "volume": lot_size,
            "price": float(price),
            "sl": float(self._safe_float(sl, 0.0)),
            "tp": float(self._safe_float(tp, 0.0)),
            "comment": "Signal pending",
        }
        result = self.order_send(request, verbose=verbose)
        return self._safe_int(getattr(result, "retcode", 0), 0) in (10008, 10009)

    def _exec_cancel_pending_signal(self, symbol_name, cancel_pending_signal, verbose: bool = False):
        code = self._safe_int(cancel_pending_signal, 0)
        if code == 0:
            return False
        changed = False
        for order in self._iter_pending_for_cancel(symbol_name, code):
            request = {
                "action": 8,  # TRADE_ACTION_REMOVE
                "order": self._safe_int(getattr(order, "ticket", 0), 0),
            }
            result = self.order_send(request, verbose=verbose)
            if self._safe_int(getattr(result, "retcode", 0), 0) == 10009:
                changed = True
        return changed

    def _apply_tick_signals(
        self,
        symbol_name,
        bid,
        ask,
        entry_signal,
        exit_signal,
        pending_signal,
        cancel_pending_signal,
        pending_signal_2=0.0,
        cancel_pending_signal_2=0.0,
        signal_price=0.0,
        signal_price_2=0.0,
        sl=0.0,
        tp=0.0,
        volume=None,
        verbose: bool = False,
    ):
        if not symbol_name:
            return False
        state_changed = False
        # Exit/cancel first, then entry/new pending.
        if self._exec_exit_signal(symbol_name, exit_signal, bid, ask, verbose=verbose):
            state_changed = True
        if self._exec_cancel_pending_signal(symbol_name, cancel_pending_signal, verbose=verbose):
            state_changed = True
        if self._exec_cancel_pending_signal(symbol_name, cancel_pending_signal_2, verbose=verbose):
            state_changed = True
        if self._exec_entry_signal(
            symbol_name,
            entry_signal,
            bid,
            ask,
            sl=sl,
            tp=tp,
            volume=volume,
            verbose=verbose,
        ):
            state_changed = True
        if self._exec_pending_signal(
            symbol_name,
            pending_signal,
            bid,
            ask,
            signal_price=signal_price,
            sl=sl,
            tp=tp,
            volume=volume,
            verbose=verbose,
        ):
            state_changed = True
        if self._exec_pending_signal(
            symbol_name,
            pending_signal_2,
            bid,
            ask,
            signal_price=signal_price_2,
            sl=sl,
            tp=tp,
            volume=volume,
            verbose=verbose,
        ):
            state_changed = True
        return state_changed

    @staticmethod
    def _normalize_schedule_every(value):
        if value is None:
            return None
        every = int(value)
        if every <= 0:
            raise ValueError("Schedule interval must be a positive integer or None.")
        return every

    def configure_run_schedule(
        self,
        auto: bool = True,
        positions_every=None,
        pending_orders_every=None,
        account_every=None,
        portfolio_every=None,
        risk_every=None,
    ):
        """Configure optional callback intervals for Engine.run tick scheduling."""
        manual_schedule = any(
            v is not None
            for v in (
                positions_every,
                pending_orders_every,
                account_every,
                portfolio_every,
                risk_every,
            )
        )
        self.run_schedule["auto"] = auto if not manual_schedule else False

        self.run_schedule["positions"] = self._normalize_schedule_every(positions_every)
        self.run_schedule["pending_orders"] = self._normalize_schedule_every(
            pending_orders_every
        )
        self.run_schedule["account"] = self._normalize_schedule_every(account_every)
        self.run_schedule["portfolio"] = self._normalize_schedule_every(portfolio_every)
        self.run_schedule["risk"] = self._normalize_schedule_every(risk_every)

    def configure_position_sizing(
        self,
        enabled: bool = True,
        position_sizing_method: str = "fixed_lot",
        position_sizing_config=None,
        historical_data=None,
    ):
        if not enabled:
            self.position_sizing = {
                "enabled": False,
                "position_sizer": None,
                "adapter": None,
            }
            return

        adapter = _SimulationRiskAdapter(self, historical_data or {})
        position_sizer = PositionSizer(
            method=position_sizing_method,
            config=position_sizing_config or {},
            mt5_client=adapter,
        )
        self.position_sizing = {
            "enabled": True,
            "position_sizer": position_sizer,
            "adapter": adapter,
        }

    def _position_sizing_enabled(self):
        return bool(self.position_sizing.get("enabled")) and self.position_sizing.get("position_sizer") is not None

    def _resolve_signal_volume(
        self,
        symbol_name,
        signal_type: str,
        entry_price: float,
        stop_loss=None,
        fallback_volume=None,
    ) -> float:
        lot_size = float(self.default_signal_volume if fallback_volume is None else fallback_volume)
        if not self._position_sizing_enabled():
            return lot_size

        adapter = self.position_sizing.get("adapter")
        position_sizer = self.position_sizing.get("position_sizer")
        if position_sizer is None:
            return lot_size

        symbol_info = adapter.get_symbol_info(symbol_name) if adapter is not None else None
        sized = position_sizer.calculate_size(
            account_balance=float(self.account_info().get("equity", self.account_info().get("balance", 0.0)) or 0.0),
            entry_price=float(entry_price),
            stop_loss=None if stop_loss is None or float(stop_loss) <= 0.0 else float(stop_loss),
            symbol_info=symbol_info,
            context={},
            symbol=symbol_name,
            signal_type=signal_type,
        )
        if sized is None or float(sized) <= 0.0:
            return lot_size
        return float(sized)

    def configure_risk_management(
        self,
        enabled: bool = True,
        historical_data=None,
        position_sizing_method: str = "fixed_risk",
        position_sizing_config=None,
        risk_limits=None,
        governor_timeframe: str = "H1",
        governor_start_pos: int = 0,
        governor_end_pos: int = 500,
        enable_regime_detection: bool = True,
        regime_config=None,
        enable_allocation: bool = False,
        correlation_preference=None,
        risk_budgets=None,
        symbol_clusters=None,
    ):
        self._risk_equity_history = []
        if not enabled:
            self.risk_management = {
                "enabled": False,
                "position_sizer": None,
                "regime_detector": None,
                "governor": None,
                "allocator": None,
                "symbol_clusters": {},
                "risk_budgets": {},
                "historical_data": {},
                "governor_timeframe": None,
                "enable_regime_detection": False,
                "enable_allocation": False,
            }
            self._risk_adapter = None
            return

        limits_obj = risk_limits if isinstance(risk_limits, RiskLimits) else RiskLimits(**(risk_limits or {}))
        regime_cfg = regime_config or {}
        corr_pref = correlation_preference if isinstance(correlation_preference, CorrelationPreference) else CorrelationPreference(**(correlation_preference or {}))

        self._risk_adapter = _SimulationRiskAdapter(self, historical_data or {})
        governance_engine = GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=self._risk_adapter,
                timeframe=governor_timeframe,
                start_pos=int(governor_start_pos),
                end_pos=int(governor_end_pos),
            ),
            limits=limits_obj,
        )
        position_sizer = PositionSizer(
            method=position_sizing_method,
            config=position_sizing_config or {},
            mt5_client=self._risk_adapter,
        )
        regime_detector = RiskRegimeDetector(**regime_cfg)
        allocator = AllocationPlanner(governance_engine, corr_pref) if enable_allocation else None

        self.risk_management = {
            "enabled": True,
            "position_sizer": position_sizer,
            "regime_detector": regime_detector,
            "governance_engine": governance_engine,
            "allocator": allocator,
            "symbol_clusters": dict(symbol_clusters or {}),
            "risk_budgets": dict(risk_budgets or {}),
            "historical_data": historical_data or {},
            "governor_timeframe": str(governor_timeframe),
            "enable_regime_detection": bool(enable_regime_detection),
            "enable_allocation": bool(enable_allocation),
        }

    def _risk_enabled(self):
        return bool(self.risk_management.get("enabled")) and self._risk_adapter is not None

    def _aggregate_net_positions(self):
        positions = {}
        for position in self.state.trading_deals:
            if str(getattr(position, "entry", 0)) != "0":
                continue
            symbol_name = str(getattr(position, "symbol", "") or "")
            if not symbol_name:
                continue
            volume = float(getattr(position, "volume", 0.0) or 0.0)
            if volume <= 0.0:
                continue
            order_type = int(getattr(position, "type", -1) or -1)
            signed_volume = volume if order_type == 0 else -volume
            positions[symbol_name] = float(positions.get(symbol_name, 0.0) + signed_volume)
            if abs(positions[symbol_name]) < 1e-12:
                positions.pop(symbol_name, None)
        return positions

    def _build_risk_equity_series(self):
        curve = self.get_equity_curve()
        if curve:
            timestamps = [pd.Timestamp(point.timestamp) for point in curve if getattr(point, "timestamp", None) is not None]
            values = [float(point.equity) for point in curve if getattr(point, "timestamp", None) is not None]
            if timestamps and values and len(timestamps) == len(values):
                return pd.Series(values, index=pd.DatetimeIndex(timestamps))
        if self._risk_equity_history:
            return pd.Series([item[1] for item in self._risk_equity_history], index=pd.DatetimeIndex([item[0] for item in self._risk_equity_history]))
        current_dt = getattr(self.state, "current_tick_datetime", None)
        current_equity = float(self.account_info().get("equity", self.account_info().get("balance", 0.0)) or 0.0)
        if current_dt is None:
            return None
        return pd.Series([current_equity], index=pd.DatetimeIndex([pd.Timestamp(current_dt)]))

    def _record_risk_equity_point(self):
        current_dt = getattr(self.state, "current_tick_datetime", None)
        if current_dt is None:
            return
        current_equity = float(self.account_info().get("equity", self.account_info().get("balance", 0.0)) or 0.0)
        timestamp = pd.Timestamp(current_dt)
        if self._risk_equity_history and self._risk_equity_history[-1][0] == timestamp:
            self._risk_equity_history[-1] = (timestamp, current_equity)
            return
        self._risk_equity_history.append((timestamp, current_equity))
        if len(self._risk_equity_history) > 5000:
            self._risk_equity_history = self._risk_equity_history[-5000:]

    def _candidate_signal_type(self, candidate):
        action = candidate.get("action")
        code = self._safe_int(candidate.get("signal_code"), 0)
        if action == "entry":
            return "buy" if code == 1 else "sell"
        if code in (1, 2):
            return "buy"
        return "sell"

    def _candidate_signed_lots(self, candidate, lots: float):
        signal_type = self._candidate_signal_type(candidate)
        return float(lots if signal_type == "buy" else -lots)

    def _execute_candidate(self, candidate, volume: float, verbose: bool = False):
        if candidate.get("action") == "entry":
            return self._exec_entry_signal(
                candidate.get("symbol_name"),
                candidate.get("signal_code"),
                candidate.get("bid"),
                candidate.get("ask"),
                sl=candidate.get("sl", 0.0),
                tp=candidate.get("tp", 0.0),
                volume=volume,
                verbose=verbose,
            )
        return self._exec_pending_signal(
            candidate.get("symbol_name"),
            candidate.get("signal_code"),
            candidate.get("bid"),
            candidate.get("ask"),
            signal_price=candidate.get("signal_price", 0.0),
            sl=candidate.get("sl", 0.0),
            tp=candidate.get("tp", 0.0),
            volume=volume,
            verbose=verbose,
        )

    def _build_risk_candidate(
        self,
        action,
        symbol_name,
        signal_code,
        bid,
        ask,
        signal_price=0.0,
        sl=0.0,
        tp=0.0,
        requested_volume=0.0,
    ):
        return {
            "action": str(action),
            "symbol_name": str(symbol_name or ""),
            "signal_code": int(self._safe_int(signal_code, 0)),
            "bid": float(self._safe_float(bid, 0.0)),
            "ask": float(self._safe_float(ask, 0.0)),
            "signal_price": float(self._safe_float(signal_price, 0.0)),
            "sl": float(self._safe_float(sl, 0.0)),
            "tp": float(self._safe_float(tp, 0.0)),
            "requested_volume": float(self._safe_float(requested_volume, 0.0)),
        }

    def _build_risk_portfolio_state(self, positions, governance_engine, symbols):
        if self._risk_adapter is None:
            raise ValueError("Risk adapter is not initialized.")

        risk_engine = governance_engine.risk_engine
        timeframe = str(risk_engine.timeframe or "D1")
        count = max(int(risk_engine.end_pos - risk_engine.start_pos), 1)
        start_pos = int(risk_engine.start_pos)
        clean_symbols = sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})

        symbol_specs = {}
        market_data = {}
        for symbol in clean_symbols:
            spec = self._risk_adapter.get_symbol_info(symbol)
            if spec is not None:
                symbol_specs[symbol] = spec
            bars = self._risk_adapter.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                count=count,
                start_pos=start_pos,
            )
            if bars is not None and not bars.empty:
                market_data[symbol] = bars.copy()

        return self._portfolio_state_engine.build_state(
            account=self.account_info(),
            positions=positions,
            symbol_specs=symbol_specs,
            market_data=market_data,
            limits=governance_engine.limits,
            symbol_to_cluster=self.risk_management.get("symbol_clusters") or {},
            timeframe=timeframe,
            metadata={
                "source": "simulation_risk_governance",
                "start_pos": start_pos,
                "count": count,
            },
        )


    def _risk_log_report(self, candidate, base_lots, target_lots, regime, report, verbose: bool = False):
        if not verbose:
            return
        regime_name = "NORMAL" if regime is None else str(regime.name)
        print(
            f"[risk] symbol={candidate.get('symbol_name')} action={candidate.get('action')} "
            f"side={self._candidate_signal_type(candidate).upper()} base_lots={float(base_lots):.4f} "
            f"target_lots={float(target_lots):.4f} regime={regime_name} decision={report.decision} "
            f"reason={report.reason} new_var={float(report.new_var):.2f} delta_var={float(report.delta_var):.2f} "
            f"new_es={float(report.new_es):.2f} delta_es={float(report.delta_es):.2f}"
        )

    def _execute_risk_batch(self, candidates, fallback_volume: float, verbose: bool = False):
        if not candidates or not self._risk_enabled():
            return False

        if self._has_open_positions():
            self.monitor_positions(verbose=False)
            self.monitor_account(verbose=False)
        self._record_risk_equity_point()

        governance_engine = self.risk_management.get("governance_engine")
        position_sizer = self.risk_management.get("position_sizer")
        allocator = self.risk_management.get("allocator")
        regime_detector = self.risk_management.get("regime_detector")
        current_positions = self._aggregate_net_positions()

        prepared = []
        for candidate in candidates:
            symbol_name = candidate.get("symbol_name")
            raw_symbol_info = self._risk_adapter.get_symbol_info(symbol_name) if self._risk_adapter is not None else None
            stop_loss = candidate.get("sl", 0.0) or None
            entry_price = float(candidate.get("signal_price") or 0.0)
            if entry_price <= 0.0:
                entry_price = float(candidate.get("ask") if self._candidate_signal_type(candidate) == "buy" else candidate.get("bid"))
            base_lots = float(candidate.get("requested_volume") or fallback_volume)
            if position_sizer is not None:
                sized = position_sizer.calculate_size(
                    account_balance=float(self.account_info().get("equity", self.account_info().get("balance", 0.0)) or 0.0),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    symbol_info=raw_symbol_info,
                    symbol=symbol_name,
                    signal_type=self._candidate_signal_type(candidate),
                )
                if sized > 0.0:
                    base_lots = float(sized)
            candidate["entry_price"] = float(entry_price)
            candidate["base_lots"] = float(base_lots)
            prepared.append(candidate)

        regime = None
        if self.risk_management.get("enable_regime_detection") and regime_detector is not None and governance_engine is not None:
            symbols = sorted({str(candidate.get("symbol_name")) for candidate in prepared if candidate.get("symbol_name")})
            if symbols:
                risk_engine = governance_engine.risk_engine
                returns_df = risk_engine.build_returns_df(
                    risk_engine.get_data(symbols, exclude_current_bar=True),
                    symbols,
                )
                equity_curve = self._build_risk_equity_series()
                regime = regime_detector.detect(returns_df, equity_curve) if not returns_df.empty else None

        target_map = {f"{idx}:{candidate['symbol_name']}:{candidate['action']}": candidate["base_lots"] for idx, candidate in enumerate(prepared)}
        if self.risk_management.get("enable_allocation") and allocator is not None and len(prepared) > 1:
            alloc_symbols = []
            alloc_base_lots = {}
            alloc_budgets = {}
            for idx, candidate in enumerate(prepared):
                key = f"{idx}:{candidate['symbol_name']}:{candidate['action']}"
                alloc_symbols.append(key)
                alloc_base_lots[key] = float(candidate["base_lots"])
                alloc_budgets[key] = float(self.risk_management.get("risk_budgets", {}).get(candidate["symbol_name"], 0.0) or 0.0)
            target_map = allocator.compute_target_lots(
                symbols=alloc_symbols,
                base_lots=alloc_base_lots,
                budgets=alloc_budgets,
                regime=regime,
            )

        state_changed = False
        for idx, candidate in enumerate(prepared):
            key = f"{idx}:{candidate['symbol_name']}:{candidate['action']}"
            target_lots = float(target_map.get(key, candidate["base_lots"]))
            if target_lots <= 0.0:
                continue
            signed_lots = self._candidate_signed_lots(candidate, target_lots)
            current_state = self._build_risk_portfolio_state(
                current_positions,
                governance_engine,
                symbols=list(current_positions.keys()) + [candidate["symbol_name"]],
            )
            report = governance_engine.evaluate_add_position_from_state(
                current_state=current_state,
                candidate_symbol=candidate["symbol_name"],
                candidate_lots=signed_lots,
                regime=regime,
            )
            self._risk_log_report(candidate, candidate["base_lots"], target_lots, regime, report, verbose=verbose)
            if report.decision != "ACCEPT":
                continue
            if self._execute_candidate(candidate, target_lots, verbose=verbose):
                current_positions[candidate["symbol_name"]] = float(current_positions.get(candidate["symbol_name"], 0.0) + signed_lots)
                if abs(current_positions[candidate["symbol_name"]]) < 1e-12:
                    current_positions.pop(candidate["symbol_name"], None)
                state_changed = True

        return state_changed

    @staticmethod
    def _due_by_interval(tick_number: int, every):
        return every is not None and (tick_number == 1 or tick_number % every == 0)

    def _run_scheduled_callbacks(
        self,
        tick_number: int,
        verbose: bool = False,
        is_bar_close: bool = False,
    ):
        schedule = self.run_schedule
        state_changed = False

        if schedule.get("auto") and is_bar_close:
            # Auto-mode: Trigger everything at bar close
            snapshot_policy = str(
                getattr(self, "equity_snapshot_policy", "bar_close") or "bar_close"
            ).lower()
            if snapshot_policy == "bar_close" and self._has_open_positions():
                self.monitor_positions(verbose=verbose)
                state_changed = True
            if self._has_pending_orders():
                self.monitor_pending_orders(verbose=verbose)
                state_changed = True

            if snapshot_policy == "bar_close":
                self.monitor_account(verbose=verbose)
            self.monitor_portfolio(verbose=verbose)
            self.monitor_risk(verbose=verbose)
            self._schedule_state_dirty = False
            return

        # Manual/Legacy mode: Trigger based on tick intervals
        positions_every = schedule.get("positions")
        positions_due = self._due_by_interval(tick_number, positions_every)
        if positions_due:
            if self._has_open_positions():
                self.monitor_positions(verbose=verbose)
                state_changed = True

        pending_orders_every = schedule.get("pending_orders")
        pending_due = self._due_by_interval(tick_number, pending_orders_every)
        if pending_due:
            if self._has_pending_orders():
                self.monitor_pending_orders(verbose=verbose)
                state_changed = True

        if state_changed:
            self._schedule_state_dirty = True

        account_every = schedule.get("account")
        account_due = self._due_by_interval(tick_number, account_every)
        portfolio_every = schedule.get("portfolio")
        portfolio_due = self._due_by_interval(tick_number, portfolio_every)
        risk_every = schedule.get("risk")
        risk_due = self._due_by_interval(tick_number, risk_every)

        run_state_checks = self._schedule_state_dirty and (
            account_due or portfolio_due or risk_due
        )

        if run_state_checks and account_due:
            self.monitor_account(verbose=verbose)

        if run_state_checks and portfolio_due:
            self.monitor_portfolio(verbose=verbose)

        if run_state_checks and risk_due:
            self.monitor_risk(verbose=verbose)

        if run_state_checks:
            self._schedule_state_dirty = False

    def _has_open_positions(self):
        # Keep guard O(1) in simulator mode to avoid unnecessary monitor calls.
        if self.backend == "sim":
            return bool(self.state.trading_deals)
        return True

    def _has_pending_orders(self):
        # Keep guard O(1) in simulator mode to avoid unnecessary monitor calls.
        if self.backend == "sim":
            return bool(self.state.trading_orders)
        return True

    def run_event_driven(
        self,
        data,
        position_size=None,
        commission_per_lot=0.0,
        slippage_model="none",
        slippage_points=0.0,
        slippage_min=None,
        slippage_max=None,
        monitor_verbose: bool = False,
        show_progress: bool = False,
        progress_desc: str = "Tester Progress",
        frame_observer=None,
    ):
        """Run prepared tick data through the event-driven backend."""
        return run_event_driven_simulation(
            self,
            data,
            position_size=position_size,
            commission_per_lot=commission_per_lot,
            slippage_model=slippage_model,
            slippage_points=slippage_points,
            slippage_min=slippage_min,
            slippage_max=slippage_max,
            monitor_verbose=monitor_verbose,
            show_progress=show_progress,
            progress_desc=progress_desc,
            frame_observer=frame_observer,
        )

    def monitor_positions(self, verbose: bool = False):
        if self.backend == "mt5":
            self._sync_live_state_to_simulator_state()
            return core.monitor_positions(
                self.state,
                verbose=verbose,
                allow_auto_close=False,
                profit_calculator=self._strict_order_calc_profit,
                strict_calc_access=True,
            )
        return core.monitor_positions(
            self.state,
            verbose=verbose,
            profit_calculator=self._strict_order_calc_profit,
            strict_calc_access=True,
        )

    def monitor_pending_orders(self, verbose: bool = False):
        if self.backend == "mt5":
            self._sync_live_state_to_simulator_state()
            return core.monitor_pending_orders(
                self.state,
                verbose=verbose,
                allow_auto_trigger=False,
                allow_auto_expire=False,
                profit_calculator=self._strict_order_calc_profit,
                margin_calculator=self._strict_order_calc_margin,
                strict_calc_access=True,
            )
        return core.monitor_pending_orders(
            self.state,
            verbose=verbose,
            profit_calculator=self._strict_order_calc_profit,
            margin_calculator=self._strict_order_calc_margin,
            strict_calc_access=True,
        )

    def monitor_account(self, verbose: bool = False):
        if self.backend == "mt5":
            self._sync_live_state_to_simulator_state()
        return core.monitor_account(self.state, verbose=verbose)

    def monitor_portfolio(self, verbose: bool = False):
        # Placeholder hook for future portfolio checks in Engine.run scheduler.
        _ = verbose
        return None

    def monitor_risk(self, verbose: bool = False):
        # Placeholder hook for future risk checks in Engine.run scheduler.
        _ = verbose
        return None

    def order_check(self, request):
        # order_check is not strictly required by simulator logic yet, 
        # but returning empty dict prevents missing method errors from Trade
        return {}


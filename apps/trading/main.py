"""
Simulator engine execution and state management.
"""
import time

from apps.mt5 import MT5Utils, get_mt5_api
from apps.utils.logger import logger
from apps.trading import core


class Engine:
    def __init__(self, backend="sim"):
        """
        Initialise trading engine.
        
        Args:
            backend (str): Backend to use. Options: "sim", "mt5".
        """

        self.backend = backend
        self.mt5 = get_mt5_api()
        self.client = MT5Utils.get_connected_client()
        self.mt5_account = self.client.account_info()
        self.state = core.SimulatorState(account_info=self.mt5_account)
        if backend == "sim":
            self.api = self
        elif backend == "mt5":
            self.api = self.mt5
        else:
            raise ValueError(f"Unknown backend: {backend}")

        logger.info(f"successfully initialised trading engine {self.backend}")

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

    def order_send(self, request):
        return core.order_send(self.state, request)

    def run(self, data):
        """Simple backtest loop placeholder that iterates over tick data."""
        if data is None:
            return 0

        if not hasattr(data, "columns") or not hasattr(data, "iterrows"):
            raise ValueError("Engine.run expects a tick DataFrame input.")

        cols_lower = {str(col).lower() for col in data.columns}
        required = {"bid", "ask"}
        missing = required - cols_lower
        if missing:
            raise ValueError(
                f"Engine.run expects tick DataFrame columns {sorted(required)}; "
                f"missing {sorted(missing)}."
            )

        processed = 0
        for _, _row in data.iterrows():
            processed += 1

        return processed

    def monitor_positions(self, verbose: bool = False):
        if self.backend == "mt5":
            self._sync_live_state_to_simulator_state()
            return core.monitor_positions(
                self.state,
                verbose=verbose,
                allow_auto_close=False,
            )
        return core.monitor_positions(self.state, verbose=verbose)

    def monitor_pending_orders(self, verbose: bool = False):
        if self.backend == "mt5":
            self._sync_live_state_to_simulator_state()
            return core.monitor_pending_orders(
                self.state,
                verbose=verbose,
                allow_auto_trigger=False,
                allow_auto_expire=False,
            )
        return core.monitor_pending_orders(self.state, verbose=verbose)

    def monitor_account(self, verbose: bool = False):
        if self.backend == "mt5":
            self._sync_live_state_to_simulator_state()
        return core.monitor_account(self.state, verbose=verbose)

    def order_check(self, request):
        # order_check is not strictly required by simulator logic yet, 
        # but returning empty dict prevents missing method errors from Trade
        return {}

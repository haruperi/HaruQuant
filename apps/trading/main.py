"""
Simulator engine execution and state management.
"""
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

    def order_check(self, request):
        # order_check is not strictly required by simulator logic yet, 
        # but returning empty dict prevents missing method errors from Trade
        return {}

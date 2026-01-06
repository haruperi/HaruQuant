"""
AccountInfo class for accessing account information.

This module provides a platform-agnostic implementation of account information
access, inspired by MT5's AccountInfo.mqh but designed to work with any
trading platform through adapter patterns.

Copyright 2025, HaruQuant
"""

from enum import Enum
from typing import Any, Dict, Optional, Protocol

from apps.logger import logger


class AccountTradeMode(Enum):
    """Account trade mode enumeration."""

    DEMO = "demo"
    CONTEST = "contest"
    REAL = "real"
    UNKNOWN = "unknown"


class AccountStopoutMode(Enum):
    """Account stopout mode enumeration."""

    PERCENT = "percent"
    MONEY = "money"
    UNKNOWN = "unknown"


class AccountMarginMode(Enum):
    """Account margin mode enumeration."""

    RETAIL_NETTING = "netting"
    EXCHANGE = "exchange"
    RETAIL_HEDGING = "hedging"
    UNKNOWN = "unknown"


class OrderType(Enum):
    """Order type enumeration."""

    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"
    BUY_STOP_LIMIT = "buy_stop_limit"
    SELL_STOP_LIMIT = "sell_stop_limit"


class AccountDataProvider(Protocol):
    """
    Protocol for account data providers.

    Any trading platform adapter should implement this protocol
    to provide account information to the AccountInfo class.
    """

    def get_login(self) -> int:
        """Get account login/ID."""
        ...

    def get_trade_mode(self) -> AccountTradeMode:
        """Get account trade mode."""
        ...

    def get_leverage(self) -> int:
        """Get account leverage."""
        ...

    def get_stopout_mode(self) -> AccountStopoutMode:
        """Get stopout mode."""
        ...

    def get_margin_mode(self) -> AccountMarginMode:
        """Get margin calculation mode."""
        ...

    def get_trade_allowed(self) -> bool:
        """Check if trading is allowed."""
        ...

    def get_trade_expert(self) -> bool:
        """Check if expert advisors are allowed."""
        ...

    def get_limit_orders(self) -> int:
        """Get maximum allowed limit orders."""
        ...

    def get_balance(self) -> float:
        """Get account balance."""
        ...

    def get_credit(self) -> float:
        """Get account credit."""
        ...

    def get_profit(self) -> float:
        """Get current profit."""
        ...

    def get_equity(self) -> float:
        """Get account equity."""
        ...

    def get_margin(self) -> float:
        """Get used margin."""
        ...

    def get_free_margin(self) -> float:
        """Get free margin."""
        ...

    def get_margin_level(self) -> float:
        """Get margin level percentage."""
        ...

    def get_margin_call(self) -> float:
        """Get margin call level."""
        ...

    def get_margin_stopout(self) -> float:
        """Get margin stopout level."""
        ...

    def get_name(self) -> str:
        """Get account holder name."""
        ...

    def get_server(self) -> str:
        """Get server name."""
        ...

    def get_currency(self) -> str:
        """Get account currency."""
        ...

    def get_company(self) -> str:
        """Get broker company name."""
        ...

    def calc_order_profit(
        self,
        symbol: str,
        trade_operation: OrderType,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> Optional[float]:
        """Calculate order profit."""
        ...

    def calc_margin(
        self, symbol: str, trade_operation: OrderType, volume: float, price: float
    ) -> Optional[float]:
        """Calculate required margin."""
        ...

    def get_symbol_info(self, symbol: str, property_name: str) -> Optional[float]:
        """Get symbol information."""
        ...


class MT5AccountProvider:
    """
    Implementation of AccountDataProvider using MT5Client.

    This class adapts an MT5Client instance to the AccountDataProvider protocol,
    providing full access to MT5's calculation functions for margin and profit.
    """

    def __init__(self, mt5_client):
        """
        Initialize MT5AccountProvider.

        Args:
            mt5_client: Instance of MT5Client with active connection
        """
        self._client = mt5_client
        self._account_data: Dict[str, Any] = {}
        self._refresh_account_data()

    def _refresh_account_data(self) -> None:
        """Refresh account data from MT5."""
        account_data = self._client.fetch_account_info()
        if account_data is None:
            logger.warning("Failed to fetch account data from MT5")
            self._account_data = {}
        else:
            self._account_data = account_data

    def get_login(self) -> int:
        """Get account login/ID."""
        return int(self._account_data.get("login", 0))

    def get_trade_mode(self) -> AccountTradeMode:
        """Get account trade mode."""
        mode = int(self._account_data.get("trade_mode", -1))
        return {
            0: AccountTradeMode.DEMO,
            1: AccountTradeMode.CONTEST,
            2: AccountTradeMode.REAL,
        }.get(mode, AccountTradeMode.UNKNOWN)

    def get_leverage(self) -> int:
        """Get account leverage."""
        return int(self._account_data.get("leverage", 0))

    def get_stopout_mode(self) -> AccountStopoutMode:
        """Get stopout mode."""
        mode = int(self._account_data.get("margin_so_mode", -1))
        return {
            0: AccountStopoutMode.PERCENT,
            1: AccountStopoutMode.MONEY,
        }.get(mode, AccountStopoutMode.UNKNOWN)

    def get_margin_mode(self) -> AccountMarginMode:
        """Get margin calculation mode."""
        mode = int(self._account_data.get("margin_mode", -1))
        return {
            0: AccountMarginMode.RETAIL_NETTING,
            1: AccountMarginMode.EXCHANGE,
            2: AccountMarginMode.RETAIL_HEDGING,
        }.get(mode, AccountMarginMode.UNKNOWN)

    def get_trade_allowed(self) -> bool:
        """Check if trading is allowed."""
        return bool(self._account_data.get("trade_allowed", False))

    def get_trade_expert(self) -> bool:
        """Check if expert advisors are allowed."""
        return bool(self._account_data.get("trade_expert", False))

    def get_limit_orders(self) -> int:
        """Get maximum allowed limit orders."""
        return int(self._account_data.get("limit_orders", 0))

    def get_balance(self) -> float:
        """Get account balance."""
        self._refresh_account_data()
        return float(self._account_data.get("balance", 0.0))

    def get_credit(self) -> float:
        """Get account credit."""
        self._refresh_account_data()
        return float(self._account_data.get("credit", 0.0))

    def get_profit(self) -> float:
        """Get current profit."""
        self._refresh_account_data()
        return float(self._account_data.get("profit", 0.0))

    def get_equity(self) -> float:
        """Get account equity."""
        self._refresh_account_data()
        return float(self._account_data.get("equity", 0.0))

    def get_margin(self) -> float:
        """Get used margin."""
        self._refresh_account_data()
        return float(self._account_data.get("margin", 0.0))

    def get_free_margin(self) -> float:
        """Get free margin."""
        self._refresh_account_data()
        return float(self._account_data.get("margin_free", 0.0))

    def get_margin_level(self) -> float:
        """Get margin level percentage."""
        self._refresh_account_data()
        return float(self._account_data.get("margin_level", 0.0))

    def get_margin_call(self) -> float:
        """Get margin call level."""
        return float(self._account_data.get("margin_so_call", 0.0))

    def get_margin_stopout(self) -> float:
        """Get margin stopout level."""
        return float(self._account_data.get("margin_so_so", 0.0))

    def get_name(self) -> str:
        """Get account holder name."""
        return str(self._account_data.get("name", ""))

    def get_server(self) -> str:
        """Get server name."""
        return str(self._account_data.get("server", ""))

    def get_currency(self) -> str:
        """Get account currency."""
        return str(self._account_data.get("currency", ""))

    def get_company(self) -> str:
        """Get broker company name."""
        return str(self._account_data.get("company", ""))

    def calc_order_profit(
        self,
        symbol: str,
        trade_operation: OrderType,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> Optional[float]:
        """Calculate order profit using MT5's native function."""
        try:
            import MetaTrader5 as mt5

            # Map OrderType to MT5 order type (tolerant to different enum classes)
            op_name = (
                getattr(trade_operation, "name", None)
                or str(trade_operation).split(".")[-1]
            )
            op_name = op_name.upper()

            if op_name == "BUY":
                mt5_order_type = mt5.ORDER_TYPE_BUY
            elif op_name == "SELL":
                mt5_order_type = mt5.ORDER_TYPE_SELL
            else:
                logger.warning(
                    f"Unsupported order type for profit calculation: {trade_operation}"
                )
                return None

            profit = mt5.order_calc_profit(
                mt5_order_type, symbol, volume, price_open, price_close
            )

            if profit is None:
                error_code, error_desc = mt5.last_error()
                logger.error(
                    f"MT5 order_calc_profit failed for {symbol}: {error_code} - {error_desc}"
                )
                return None

            return float(profit)

        except Exception as e:
            logger.error(f"Error calculating order profit: {e}")
            return None

    def calc_margin(
        self, symbol: str, trade_operation: OrderType, volume: float, price: float
    ) -> Optional[float]:
        """Calculate required margin using MT5's native function."""
        try:
            import MetaTrader5 as mt5

            # Map OrderType to MT5 order type (tolerant to different enum classes)
            op_name = (
                getattr(trade_operation, "name", None)
                or str(trade_operation).split(".")[-1]
            )
            op_name = op_name.upper()

            if op_name == "BUY":
                mt5_order_type = mt5.ORDER_TYPE_BUY
            elif op_name == "SELL":
                mt5_order_type = mt5.ORDER_TYPE_SELL
            else:
                logger.warning(
                    f"Unsupported order type for margin calculation: {trade_operation}"
                )
                return None

            margin = mt5.order_calc_margin(mt5_order_type, symbol, volume, price)

            if margin is None:
                error_code, error_desc = mt5.last_error()
                logger.error(
                    f"MT5 order_calc_margin failed for {symbol}: {error_code} - {error_desc}"
                )
                return None

            return float(margin)

        except Exception as e:
            logger.error(f"Error calculating margin: {e}")
            return None

    def get_symbol_info(self, symbol: str, property_name: str) -> Optional[float]:
        """Get symbol property from MT5."""
        try:
            symbol_info = self._client.get_symbol_info(symbol)
            if symbol_info is None:
                return None

            # Map property names to symbol info keys
            property_map = {
                "SYMBOL_VOLUME_MIN": "volume_min",
                "SYMBOL_VOLUME_MAX": "volume_max",
                "SYMBOL_VOLUME_STEP": "volume_step",
                "SYMBOL_TRADE_CONTRACT_SIZE": "trade_contract_size",
                "SYMBOL_POINT": "point",
            }

            key = property_map.get(property_name)
            if key:
                val = symbol_info.get(key)
                return float(val) if val is not None else None

            # If not in map, try direct key lookup (lowercase)
            val = symbol_info.get(property_name.lower())
            return float(val) if val is not None else None

        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}.{property_name}: {e}")
            return None


class BacktestAccountProvider:
    """
    Implementation of AccountDataProvider for backtesting.

    This class simulates account operations and calculations without
    requiring a live MT5 connection. It maintains internal state and
    calculates margin/profit using standard formulas.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        currency: str = "USD",
        leverage: int = 100,
        margin_mode: AccountMarginMode = AccountMarginMode.RETAIL_HEDGING,
        stopout_mode: AccountStopoutMode = AccountStopoutMode.PERCENT,
        margin_call: float = 80.0,
        margin_stopout: float = 50.0,
        symbol_specs: Optional[Dict[str, Dict[str, Any]]] = None,
        trade_provider: Optional[Any] = None,
    ):
        """
        Initialize BacktestAccountProvider.

        Args:
            initial_balance: Starting account balance
            currency: Account currency
            leverage: Account leverage (e.g., 100 for 1:100)
            margin_mode: Margin calculation mode
            stopout_mode: Stopout mode (percent or money)
            margin_call: Margin call level
            margin_stopout: Margin stopout level
            symbol_specs: Dictionary of symbol specifications for calculations
            trade_provider: Optional BacktestTradeProvider to sync balance with
        """
        # Account static properties
        self._login = 99999999  # Simulated login
        self._name = "Backtest Account"
        self._server = "Backtest-Server"
        self._company = "HaruQuant Backtest"
        self._currency = currency
        self._leverage = leverage
        self._trade_mode = AccountTradeMode.DEMO
        self._margin_mode = margin_mode
        self._stopout_mode = stopout_mode
        self._trade_allowed = True
        self._trade_expert = True
        self._limit_orders = 0  # Unlimited
        self._margin_call = margin_call
        self._margin_stopout = margin_stopout

        # Account dynamic properties
        self._balance = initial_balance
        self._credit = 0.0
        self._profit = 0.0  # Unrealized P/L from open positions
        self._margin = 0.0  # Used margin from open positions

        # Trade provider for syncing balance
        self._trade_provider = trade_provider

        # Symbol specifications
        self._symbol_specs = symbol_specs or self._get_default_symbol_specs()

        logger.info(
            f"BacktestAccountProvider initialized: {initial_balance} {currency}, leverage 1:{leverage}"
        )

    @classmethod
    def from_mt5_account(
        cls,
        mt5_client,
        initial_balance: Optional[float] = None,
        symbols: Optional[list] = None,
    ):
        """
        Create BacktestAccountProvider matching MT5 account settings.

        Args:
            mt5_client: MT5Client instance with active connection
            initial_balance: Override balance (uses MT5 balance if None)
            symbols: List of symbols to fetch specs for (uses common pairs if None)

        Returns:
            BacktestAccountProvider configured to match MT5 account

        Example:
            >>> from apps.mt5 import MT5Client
            >>> client = MT5Client()
            >>> client.initialize()
            >>> provider = BacktestAccountProvider.from_mt5_account(
            ...     client,
            ...     symbols=["EURUSD", "GBPUSD", "XAUUSD"]
            ... )
        """
        # Fetch account info from MT5
        account_data = mt5_client.fetch_account_info()
        if not account_data:
            logger.error("Failed to fetch account data from MT5")
            return cls()  # Return with defaults

        # Extract account properties
        balance = initial_balance or account_data.get("balance", 10000.0)
        currency = account_data.get("currency", "USD")
        leverage = account_data.get("leverage", 100)

        # Map margin mode
        margin_mode_val = account_data.get("margin_mode", 0)
        if margin_mode_val == 0:
            margin_mode = AccountMarginMode.RETAIL_NETTING
        elif margin_mode_val == 1:
            margin_mode = AccountMarginMode.EXCHANGE
        elif margin_mode_val == 2:
            margin_mode = AccountMarginMode.RETAIL_HEDGING
        else:
            margin_mode = AccountMarginMode.RETAIL_NETTING

        # Map stopout mode
        stopout_mode_val = account_data.get("margin_so_mode", 0)
        if stopout_mode_val == 0:
            stopout_mode = AccountStopoutMode.PERCENT
        elif stopout_mode_val == 1:
            stopout_mode = AccountStopoutMode.MONEY
        else:
            stopout_mode = AccountStopoutMode.PERCENT

        margin_call = account_data.get("margin_so_call", 80.0)
        margin_stopout = account_data.get("margin_so_so", 50.0)

        # Fetch symbol specifications from MT5
        symbol_specs = cls._fetch_mt5_symbol_specs(mt5_client, symbols)

        logger.info(
            f"Created BacktestAccountProvider from MT5 account: "
            f"leverage={leverage}, margin_mode={margin_mode.value}"
        )

        return cls(
            initial_balance=balance,
            currency=currency,
            leverage=leverage,
            margin_mode=margin_mode,
            stopout_mode=stopout_mode,
            margin_call=margin_call,
            margin_stopout=margin_stopout,
            symbol_specs=symbol_specs,
        )

    @staticmethod
    def _fetch_mt5_symbol_specs(
        mt5_client, symbols: Optional[list] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch symbol specifications from MT5."""
        if symbols is None:
            symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]

        symbol_specs = {}
        for symbol in symbols:
            symbol_info = mt5_client.get_symbol_info(symbol)
            if symbol_info:
                symbol_specs[symbol] = {
                    "contract_size": symbol_info.get("trade_contract_size", 100000),
                    "volume_min": symbol_info.get("volume_min", 0.01),
                    "volume_max": symbol_info.get("volume_max", 100.0),
                    "volume_step": symbol_info.get("volume_step", 0.01),
                    "point": symbol_info.get("point", 0.00001),
                    "currency_base": symbol_info.get("currency_base", ""),
                    "currency_profit": symbol_info.get("currency_profit", ""),
                }
                logger.debug(f"Fetched symbol spec for {symbol} from MT5")
            else:
                logger.warning(f"Could not fetch symbol info for {symbol} from MT5")

        return symbol_specs

    def _get_default_symbol_specs(self) -> Dict[str, Dict[str, Any]]:
        """Get default symbol specifications for common instruments."""
        return {
            "EURUSD": {
                "contract_size": 100000,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "point": 0.00001,
                "currency_base": "EUR",
                "currency_profit": "USD",
            },
            "GBPUSD": {
                "contract_size": 100000,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "point": 0.00001,
                "currency_base": "GBP",
                "currency_profit": "USD",
            },
            "USDJPY": {
                "contract_size": 100000,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "point": 0.001,
                "currency_base": "USD",
                "currency_profit": "JPY",
            },
            "XAUUSD": {
                "contract_size": 100,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "point": 0.01,
                "currency_base": "XAU",
                "currency_profit": "USD",
            },
        }

    # Account property getters

    def get_login(self) -> int:
        """Get account login/ID."""
        return self._login

    def get_trade_mode(self) -> AccountTradeMode:
        """Get account trade mode."""
        return self._trade_mode

    def get_leverage(self) -> int:
        """Get account leverage."""
        return self._leverage

    def get_stopout_mode(self) -> AccountStopoutMode:
        """Get stopout mode."""
        return self._stopout_mode

    def get_margin_mode(self) -> AccountMarginMode:
        """Get margin calculation mode."""
        return self._margin_mode

    def get_trade_allowed(self) -> bool:
        """Check if trading is allowed."""
        return self._trade_allowed

    def get_trade_expert(self) -> bool:
        """Check if expert advisors are allowed."""
        return self._trade_expert

    def get_limit_orders(self) -> int:
        """Get maximum allowed limit orders."""
        return self._limit_orders

    def get_balance(self) -> float:
        """Get account balance."""
        # If linked to trade_provider, use its balance (source of truth)
        if self._trade_provider is not None:
            return float(
                self._trade_provider._balance
            )  # pylint: disable=protected-access
        return self._balance

    def get_credit(self) -> float:
        """Get account credit."""
        return self._credit

    def get_profit(self) -> float:
        """Get current profit."""
        return self._profit

    def get_equity(self) -> float:
        """Equity = Balance + Credit + Profit."""
        # If linked to trade_provider, use its equity (source of truth)
        if self._trade_provider is not None:
            return float(
                self._trade_provider._equity
            )  # pylint: disable=protected-access
        return self._balance + self._credit + self._profit

    def get_margin(self) -> float:
        """Get used margin."""
        return self._margin

    def get_free_margin(self) -> float:
        """Free Margin = Equity - Margin."""
        return self.get_equity() - self._margin

    def get_margin_level(self) -> float:
        """Margin Level = (Equity / Margin) * 100."""
        if self._margin <= 0:
            return 0.0
        return (self.get_equity() / self._margin) * 100.0

    def get_margin_call(self) -> float:
        """Get margin call level."""
        return self._margin_call

    def get_margin_stopout(self) -> float:
        """Get margin stopout level."""
        return self._margin_stopout

    def get_name(self) -> str:
        """Get account holder name."""
        return self._name

    def get_server(self) -> str:
        """Get server name."""
        return self._server

    def get_currency(self) -> str:
        """Get account currency."""
        return self._currency

    def get_company(self) -> str:
        """Get broker company name."""
        return self._company

    # Calculation methods

    def calc_order_profit(
        self,
        symbol: str,
        trade_operation: OrderType,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> Optional[float]:
        """Calculate order profit using standard formulas."""
        if symbol not in self._symbol_specs:
            logger.warning(f"Symbol {symbol} not found in symbol specs")
            return None

        spec = self._symbol_specs[symbol]
        contract_size = spec["contract_size"]

        # Normalize order type name (supports multiple enum classes)
        op_name = (
            getattr(trade_operation, "name", None)
            or str(trade_operation).split(".")[-1]
        )
        op_name = op_name.upper()

        # Calculate price difference
        if op_name == "BUY":
            price_diff = price_close - price_open
        elif op_name == "SELL":
            price_diff = price_open - price_close
        else:
            logger.warning(
                f"Unsupported order type for profit calculation: {trade_operation}"
            )
            return None

        # Calculate profit: Volume * ContractSize * PriceDiff
        profit = volume * contract_size * price_diff

        # Handle currency conversion (simplified)
        currency_profit = spec.get("currency_profit", "USD")
        if (
            currency_profit != self._currency
            and currency_profit == "JPY"
            and self._currency == "USD"
        ):
            profit = profit / price_close  # Approximate conversion
            # Add more conversion logic as needed

        return float(profit)

    def calc_margin(
        self, symbol: str, trade_operation: OrderType, volume: float, price: float
    ) -> Optional[float]:
        """Calculate required margin using standard formula."""
        if symbol not in self._symbol_specs:
            logger.warning(f"Symbol {symbol} not found in symbol specs")
            return None

        spec = self._symbol_specs[symbol]
        contract_size = spec["contract_size"]

        # Margin = (Volume * ContractSize * Price) / Leverage
        margin = (volume * contract_size * price) / self._leverage

        return float(margin)

    def get_symbol_info(self, symbol: str, property_name: str) -> Optional[float]:
        """Get symbol property."""
        if symbol not in self._symbol_specs:
            return None

        spec = self._symbol_specs[symbol]

        # Map property names to spec keys
        property_map = {
            "SYMBOL_VOLUME_MIN": "volume_min",
            "SYMBOL_VOLUME_MAX": "volume_max",
            "SYMBOL_VOLUME_STEP": "volume_step",
            "SYMBOL_TRADE_CONTRACT_SIZE": "contract_size",
            "SYMBOL_POINT": "point",
        }

        key = property_map.get(property_name)
        if key:
            return spec.get(key)

        # Try direct lookup
        return spec.get(property_name.lower())

    # State management methods for backtesting

    def update_balance(self, amount: float) -> None:
        """Update account balance (e.g., after closing a trade)."""
        self._balance += amount
        logger.debug(f"Balance updated: {self._balance:.2f} {self._currency}")

    def update_profit(self, profit: float) -> None:
        """Update unrealized profit from open positions."""
        self._profit = profit

    def update_margin(self, margin: float) -> None:
        """Update used margin from open positions."""
        self._margin = margin

    def reset(self, initial_balance: Optional[float] = None) -> None:
        """Reset account to initial state."""
        if initial_balance is not None:
            self._balance = initial_balance
        self._profit = 0.0
        self._margin = 0.0
        self._credit = 0.0
        logger.info(f"Account reset to {self._balance:.2f} {self._currency}")

    def add_symbol_spec(self, symbol: str, spec: Dict[str, Any]) -> None:
        """Add or update symbol specification."""
        self._symbol_specs[symbol] = spec
        logger.debug(f"Symbol spec added/updated for {symbol}")

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"BacktestAccountProvider(balance={self._balance:.2f}, "
            f"equity={self.get_equity():.2f}, "
            f"margin={self._margin:.2f}, "
            f"free_margin={self.get_free_margin():.2f})"
        )


class AccountInfo:
    """
    Class for accessing account information.

    This class provides a clean interface to account information
    regardless of the underlying trading platform. It uses a data
    provider pattern to abstract platform-specific implementations.

    Usage:
        # With MT5 provider for live trading
        from apps.mt5 import MT5Client
        from apps.trade import AccountInfo, MT5AccountProvider

        client = MT5Client()
        client.initialize()
        provider = MT5AccountProvider(client)
        account = AccountInfo(provider)

        # With backtest provider
        from apps.trade import BacktestAccountProvider

        provider = BacktestAccountProvider(initial_balance=10000.0)
        account = AccountInfo(provider)

        # Access account information
        balance = account.balance()
        equity = account.equity()
        is_demo = account.trade_mode() == AccountTradeMode.DEMO
    """

    def __init__(self, data_provider: AccountDataProvider):
        """
        Initialize AccountInfo.

        Args:
            data_provider: Data provider implementing AccountDataProvider protocol.
                          Use MT5AccountProvider for live trading or
                          BacktestAccountProvider for backtesting.
        """
        self._provider = data_provider

    # Fast access methods to integer account properties

    def login(self) -> int:
        """
        Get account login/ID.

        Returns:
            Account login number.
        """
        return self._provider.get_login()

    def trade_mode(self) -> AccountTradeMode:
        """
        Get account trade mode.

        Returns:
            AccountTradeMode enum value.
        """
        return self._provider.get_trade_mode()

    def trade_mode_description(self) -> str:
        """
        Get account trade mode as a descriptive string.

        Returns:
            Human-readable description of trade mode.
        """
        mode = self.trade_mode()
        descriptions = {
            AccountTradeMode.DEMO: "Demo trading account",
            AccountTradeMode.CONTEST: "Contest trading account",
            AccountTradeMode.REAL: "Real trading account",
            AccountTradeMode.UNKNOWN: "Unknown trade account",
        }
        return descriptions.get(mode, "Unknown trade account")

    def leverage(self) -> int:
        """
        Get account leverage.

        Returns:
            Leverage ratio (e.g., 100 for 1:100).
        """
        return self._provider.get_leverage()

    def stopout_mode(self) -> AccountStopoutMode:
        """
        Get stopout mode.

        Returns:
            AccountStopoutMode enum value.
        """
        return self._provider.get_stopout_mode()

    def stopout_mode_description(self) -> str:
        """
        Get stopout mode as a descriptive string.

        Returns:
            Human-readable description of stopout mode.
        """
        mode = self.stopout_mode()
        descriptions = {
            AccountStopoutMode.PERCENT: "Level is specified in percentage",
            AccountStopoutMode.MONEY: "Level is specified in money",
            AccountStopoutMode.UNKNOWN: "Unknown stopout mode",
        }
        return descriptions.get(mode, "Unknown stopout mode")

    def margin_mode(self) -> AccountMarginMode:
        """
        Get margin calculation mode.

        Returns:
            AccountMarginMode enum value.
        """
        return self._provider.get_margin_mode()

    def margin_mode_description(self) -> str:
        """
        Get margin mode as a descriptive string.

        Returns:
            Human-readable description of margin mode.
        """
        mode = self.margin_mode()
        descriptions = {
            AccountMarginMode.RETAIL_NETTING: "Netting",
            AccountMarginMode.EXCHANGE: "Exchange",
            AccountMarginMode.RETAIL_HEDGING: "Hedging",
            AccountMarginMode.UNKNOWN: "Unknown margin mode",
        }
        return descriptions.get(mode, "Unknown margin mode")

    def trade_allowed(self) -> bool:
        """
        Check if trading is allowed for this account.

        Returns:
            True if trading is allowed, False otherwise.
        """
        return self._provider.get_trade_allowed()

    def trade_expert(self) -> bool:
        """
        Check if expert advisors/automated trading is allowed.

        Returns:
            True if expert trading is allowed, False otherwise.
        """
        return self._provider.get_trade_expert()

    def limit_orders(self) -> int:
        """
        Get maximum number of allowed limit orders.

        Returns:
            Maximum limit orders (0 means unlimited).
        """
        return self._provider.get_limit_orders()

    # Fast access methods to double account properties

    def balance(self) -> float:
        """
        Get account balance.

        Returns:
            Current account balance.
        """
        return self._provider.get_balance()

    def credit(self) -> float:
        """
        Get account credit.

        Returns:
            Credit provided by broker.
        """
        return self._provider.get_credit()

    def profit(self) -> float:
        """
        Get current unrealized profit/loss.

        Returns:
            Current profit (positive) or loss (negative).
        """
        return self._provider.get_profit()

    def equity(self) -> float:
        """
        Get account equity.

        Equity = Balance + Credit + Profit

        Returns:
            Current account equity.
        """
        return self._provider.get_equity()

    def margin(self) -> float:
        """
        Get used margin.

        Returns:
            Amount of margin currently used.
        """
        return self._provider.get_margin()

    def free_margin(self) -> float:
        """
        Get free margin.

        Free Margin = Equity - Margin

        Returns:
            Available margin for new positions.
        """
        return self._provider.get_free_margin()

    def margin_level(self) -> float:
        """
        Get margin level percentage.

        Margin Level = (Equity / Margin) * 100

        Returns:
            Margin level in percentage.
        """
        return self._provider.get_margin_level()

    def margin_call(self) -> float:
        """
        Get margin call level.

        Returns:
            Margin call level (percentage or money depending on stopout mode).
        """
        return self._provider.get_margin_call()

    def margin_stopout(self) -> float:
        """
        Get margin stopout level.

        Returns:
            Stopout level (percentage or money depending on stopout mode).
        """
        return self._provider.get_margin_stopout()

    # Fast access methods to string account properties

    def name(self) -> str:
        """
        Get account holder name.

        Returns:
            Name of the account holder.
        """
        return self._provider.get_name()

    def server(self) -> str:
        """
        Get server name.

        Returns:
            Name of the trading server.
        """
        return self._provider.get_server()

    def currency(self) -> str:
        """
        Get account currency.

        Returns:
            Base currency of the account (e.g., "USD", "EUR").
        """
        return self._provider.get_currency()

    def company(self) -> str:
        """
        Get broker company name.

        Returns:
            Name of the broker company.
        """
        return self._provider.get_company()

    # Calculation and check methods

    def order_profit_check(
        self,
        symbol: str,
        trade_operation: OrderType,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> Optional[float]:
        """
        Calculate potential profit for an order.

        Args:
            symbol: Trading symbol (e.g., "EURUSD").
            trade_operation: Type of trading operation.
            volume: Volume in lots.
            price_open: Opening price.
            price_close: Closing price.

        Returns:
            Calculated profit or None if calculation failed.
        """
        return self._provider.calc_order_profit(
            symbol, trade_operation, volume, price_open, price_close
        )

    def margin_check(
        self, symbol: str, trade_operation: OrderType, volume: float, price: float
    ) -> Optional[float]:
        """
        Calculate required margin for an order.

        Args:
            symbol: Trading symbol (e.g., "EURUSD").
            trade_operation: Type of trading operation.
            volume: Volume in lots.
            price: Opening price.

        Returns:
            Required margin or None if calculation failed.
        """
        return self._provider.calc_margin(symbol, trade_operation, volume, price)

    def free_margin_check(
        self, symbol: str, trade_operation: OrderType, volume: float, price: float
    ) -> Optional[float]:
        """
        Calculate free margin after opening an order.

        Args:
            symbol: Trading symbol (e.g., "EURUSD").
            trade_operation: Type of trading operation.
            volume: Volume in lots.
            price: Opening price.

        Returns:
            Remaining free margin or None if calculation failed.
        """
        margin = self.margin_check(symbol, trade_operation, volume, price)
        if margin is None:
            return None
        return self.free_margin() - margin

    def max_lot_check(
        self,
        symbol: str,
        trade_operation: OrderType,
        price: float,
        percent: float = 100.0,
    ) -> float:
        """
        Calculate maximum lot size based on available margin.

        Args:
            symbol: Trading symbol (e.g., "EURUSD").
            trade_operation: Type of trading operation.
            price: Opening price.
            percent: Percentage of available margin to use (1-100).

        Returns:
            Maximum lot size (0.0 if calculation failed or invalid parameters).
        """
        # Validate parameters
        if not symbol or price <= 0.0 or percent < 1 or percent > 100:
            logger.warning("AccountInfo.max_lot_check: invalid parameters")
            return 0.0

        # Calculate margin requirements for 1 lot
        margin = self.margin_check(symbol, trade_operation, 1.0, price)
        if margin is None or margin < 0.0:
            logger.error("AccountInfo.max_lot_check: margin calculation failed")
            return 0.0

        # For pending orders (zero margin)
        if margin == 0.0:
            max_vol = self._provider.get_symbol_info(symbol, "SYMBOL_VOLUME_MAX")
            return max_vol if max_vol is not None else 0.0

        # Calculate maximum volume based on available margin
        volume = (self.free_margin() * percent / 100.0) / margin

        # Get symbol volume constraints
        step_vol = self._provider.get_symbol_info(symbol, "SYMBOL_VOLUME_STEP")
        if step_vol and step_vol > 0.0:
            volume = step_vol * int(volume / step_vol)

        # Apply minimum volume constraint
        min_vol = self._provider.get_symbol_info(symbol, "SYMBOL_VOLUME_MIN")
        if min_vol and volume < min_vol:
            volume = 0.0

        # Apply maximum volume constraint
        max_vol = self._provider.get_symbol_info(symbol, "SYMBOL_VOLUME_MAX")
        if max_vol and volume > max_vol:
            volume = max_vol

        # Round to 2 decimal places
        return round(volume, 2)

    def __repr__(self) -> str:
        """Return string representation of AccountInfo."""
        return (
            f"AccountInfo(login={self.login()}, "
            f"balance={self.balance():.2f} {self.currency()}, "
            f"equity={self.equity():.2f}, "
            f"mode={self.trade_mode().value})"
        )

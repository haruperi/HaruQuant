"""
Trade class (MT5-specific).

This module mirrors the MQL5 Standard Library Trade interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/ctrade

Execution boundary:
- This module is the live MT5 Python transport path.
- For simulation/backtest execution, prefer `hqt_engine.sim.CTrade`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()


class Trade:
    """
    Class for easy access to trade functions in MT5.

    This class is based on the MQL5 Standard Library Trade API.
    """

    def __init__(self, api: Optional[Any] = None) -> None:
        """Initialize."""
        self._api = api if api is not None else get_mt5_api()
        self._log_level: int = 0
        self._magic: int = 0
        self._deviation: int = 0
        self._type_filling: Optional[int] = None
        self._type_time: Optional[int] = None
        self._async: bool = False
        self._margin_mode: Optional[int] = None

        self._last_request: dict[str, Any] = {}
        self._last_result: dict[str, Any] = {}
        self._last_check: dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _tick(self, symbol: str) -> Optional[Any]:
        return self._api.symbol_info_tick(symbol)

    def _send_request(self, request: dict[str, Any]) -> bool:
        if self._attempt_request(request):
            return True
        if not self._should_retry_filling():
            return False
        return self._retry_with_fillings(request)

    def _attempt_request(self, request: dict[str, Any]) -> bool:
        self._last_request = dict(request)
        self._last_check = self._perform_check(request)
        result = self._api.order_send(request)
        self._last_result = self._normalize_result(result)
        return self._is_success(result)

    def _should_retry_filling(self) -> bool:
        retcode = self._last_result.get("retcode")
        comment = str(self._last_result.get("comment", ""))
        if retcode == 10030:
            return True
        return "Unsupported filling mode" in comment

    def _retry_with_fillings(self, request: dict[str, Any]) -> bool:
        for mode in (
            mt5.ORDER_FILLING_RETURN,
            mt5.ORDER_FILLING_IOC,
            mt5.ORDER_FILLING_FOK,
        ):
            request_fallback = dict(request)
            request_fallback["type_filling"] = int(mode)
            if self._attempt_request(request_fallback):
                return True

        request_fallback = dict(request)
        request_fallback.pop("type_filling", None)
        return self._attempt_request(request_fallback)

    def _perform_check(self, request: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(self._api, "order_check"):
            return {}
        check = self._api.order_check(request)
        if check is None:
            return {}
        return check._asdict() if hasattr(check, "_asdict") else dict(check)

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        if result is None:
            return {}
        if hasattr(result, "_asdict"):
            return dict(result._asdict())
        if isinstance(result, dict):
            return dict(result)
        return {"result": result}

    def _is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if hasattr(result, "retcode"):
            retcode = getattr(result, "retcode", None)
        elif isinstance(result, dict):
            retcode = result.get("retcode")
        else:
            retcode = None
        return retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)

    def _request_base(self, symbol: str) -> dict[str, Any]:
        if hasattr(self._api, "symbol_select"):
            self._api.symbol_select(symbol, True)
        if self._type_filling is None:
            self._type_filling = self._resolve_filling_mode(symbol)
        request: dict[str, Any] = {
            "symbol": symbol,
            "magic": self._magic,
            "deviation": self._deviation,
        }
        if self._type_filling is not None:
            request["type_filling"] = self._type_filling
        if self._type_time is not None:
            request["type_time"] = self._type_time
        return request

    def _resolve_filling_mode(self, symbol: str) -> Optional[int]:
        info = self._api.symbol_info(symbol)
        if info is None:
            return None
        data = info._asdict() if hasattr(info, "_asdict") else dict(info)

        trade_fill = data.get("trade_fill_mode")
        if isinstance(trade_fill, int) and trade_fill in (
            mt5.ORDER_FILLING_FOK,
            mt5.ORDER_FILLING_IOC,
            mt5.ORDER_FILLING_RETURN,
        ):
            return trade_fill

        fill_mask = data.get("filling_mode")
        if isinstance(fill_mask, int):
            if fill_mask & mt5.ORDER_FILLING_FOK:
                return int(mt5.ORDER_FILLING_FOK)
            if fill_mask & mt5.ORDER_FILLING_IOC:
                return int(mt5.ORDER_FILLING_IOC)
            if fill_mask & mt5.ORDER_FILLING_RETURN:
                return int(mt5.ORDER_FILLING_RETURN)

        return None

    def _get_position(self, symbol: Optional[str] = None, ticket: Optional[int] = None):
        if ticket is not None:
            positions = self._api.positions_get(ticket=ticket)
        elif symbol is not None:
            positions = self._api.positions_get(symbol=symbol)
        else:
            return None
        if not positions:
            return None
        return positions[0]

    # ---------------------------------------------------------------------
    # Setting parameters
    # ---------------------------------------------------------------------
    def LogLevel(self, level: Optional[int] = None) -> int:
        """Set logging level."""
        if level is None:
            return self._log_level
        self._log_level = int(level)
        return self._log_level

    def SetExpertMagicNumber(self, magic: int) -> None:
        """Set the expert ID."""
        self._magic = int(magic)

    def SetDeviationInPoints(self, deviation: int) -> None:
        """Set the allowed deviation."""
        self._deviation = int(deviation)

    def SetTypeFilling(self, filling: int) -> None:
        """Set filling type of the order."""
        self._type_filling = int(filling)

    def SetTypeFillingBySymbol(self, symbol: str) -> bool:
        """Set filling type of the order according to symbol settings."""
        filling = self._resolve_filling_mode(symbol)
        if filling is None:
            return False
        self._type_filling = int(filling)
        return True

    def SetAsyncMode(self, mode: bool) -> None:
        """Set asynchronous mode for trade operations."""
        self._async = bool(mode)

    def SetMarginMode(self) -> bool:
        """Set margin calculation mode in accordance with the current account settings."""
        info = self._api.account_info()
        if info is None:
            return False
        data = info._asdict() if hasattr(info, "_asdict") else dict(info)
        self._margin_mode = data.get("margin_mode")
        return True

    # ---------------------------------------------------------------------
    # Operations with orders
    # ---------------------------------------------------------------------
    def OrderOpen(
        self,
        symbol: str,
        order_type: int,
        volume: float,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[int] = None,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Places a pending order with specified parameters."""
        request = self._request_base(symbol)
        request.update(
            {
                "action": mt5.TRADE_ACTION_PENDING,
                "type": order_type,
                "volume": float(volume),
                "price": float(price),
                "sl": float(sl),
                "tp": float(tp),
                "comment": comment,
            }
        )
        if stoplimit:
            request["stoplimit"] = float(stoplimit)
        if type_time is not None:
            request["type_time"] = int(type_time)
        if expiration is not None:
            request["expiration"] = int(expiration.timestamp())
        return self._send_request(request)

    def OrderModify(
        self,
        ticket: int,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[int] = None,
        expiration: Optional[datetime] = None,
    ) -> bool:
        """Modify the pending order parameters."""
        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": int(ticket),
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
        }
        if stoplimit:
            request["stoplimit"] = float(stoplimit)
        if type_time is not None:
            request["type_time"] = int(type_time)
        if expiration is not None:
            request["expiration"] = int(expiration.timestamp())
        return self._send_request(request)

    def OrderDelete(self, ticket: int) -> bool:
        """Delete a pending order."""
        request = {"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)}
        return self._send_request(request)

    # ---------------------------------------------------------------------
    # Operations with positions
    # ---------------------------------------------------------------------
    def PositionOpen(
        self,
        symbol: str,
        order_type: int,
        volume: float,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> bool:
        """Open a position with specified parameters."""
        tick = self._tick(symbol)
        if tick is None:
            return False
        if hasattr(tick, "_asdict"):
            tick_data = tick._asdict()
        elif isinstance(tick, dict):
            tick_data = dict(tick)
        else:
            return False
        if price == 0.0:
            price = (
                tick_data.get("ask")
                if order_type == mt5.ORDER_TYPE_BUY
                else tick_data.get("bid")
            )
        request = self._request_base(symbol)
        request.update(
            {
                "action": mt5.TRADE_ACTION_DEAL,
                "type": order_type,
                "volume": float(volume),
                "price": float(price),
                "sl": float(sl),
                "tp": float(tp),
                "comment": comment,
            }
        )
        return self._send_request(request)

    def PositionModify(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
        sl: float = 0.0,
        tp: float = 0.0,
    ) -> bool:
        """Modify position parameters by the specified symbol or position ticket."""
        position = self._get_position(symbol=symbol, ticket=ticket)
        if position is None:
            return False
        if hasattr(position, "_asdict"):
            data = position._asdict()
        elif isinstance(position, dict):
            data = dict(position)
        else:
            return False
        # Use "id" for simulator, "ticket" for MT5
        position_id = int(data.get("id") or data.get("ticket") or 0)
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": data.get("symbol"),
            "position": position_id,
            "sl": float(sl),
            "tp": float(tp),
        }
        return self._send_request(request)

    def PositionClose(
        self, symbol: Optional[str] = None, ticket: Optional[int] = None
    ) -> bool:
        """Close a position for the specified symbol."""
        position = self._get_position(symbol=symbol, ticket=ticket)
        if position is None:
            return False
        if hasattr(position, "_asdict"):
            data = position._asdict()
        elif isinstance(position, dict):
            data = dict(position)
        else:
            return False
        symbol_name = data.get("symbol")
        tick = self._tick(symbol_name)
        if tick is None:
            return False
        if hasattr(tick, "_asdict"):
            tick_data = tick._asdict()
        elif isinstance(tick, dict):
            tick_data = dict(tick)
        else:
            return False
        pos_type = data.get("type")
        volume = data.get("volume")
        # Handle both string types ("buy", "sell") and MT5 integer constants
        is_buy = pos_type == mt5.POSITION_TYPE_BUY or str(pos_type).lower() == "buy"
        if is_buy:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick_data.get("bid")
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick_data.get("ask")
        request = self._request_base(symbol_name)
        # Use "id" for simulator, "ticket" for MT5
        position_id = int(data.get("id") or data.get("ticket") or 0)
        request.update(
            {
                "action": mt5.TRADE_ACTION_DEAL,
                "type": order_type,
                "position": position_id,
                "volume": float(volume),
                "price": float(price),
            }
        )
        return self._send_request(request)

    def PositionClosePartial(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
        volume: float = 0.0,
    ) -> bool:
        """Close the position partially for a specified symbol or ticket."""
        position = self._get_position(symbol=symbol, ticket=ticket)
        if position is None:
            return False
        if hasattr(position, "_asdict"):
            data = position._asdict()
        elif isinstance(position, dict):
            data = dict(position)
        else:
            return False
        symbol_name = data.get("symbol")
        tick = self._tick(symbol_name)
        if tick is None:
            return False
        if hasattr(tick, "_asdict"):
            tick_data = tick._asdict()
        elif isinstance(tick, dict):
            tick_data = dict(tick)
        else:
            return False
        pos_type = data.get("type")
        # Handle both string types ("buy", "sell") and MT5 integer constants
        is_buy = pos_type == mt5.POSITION_TYPE_BUY or str(pos_type).lower() == "buy"
        if is_buy:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick_data.get("bid")
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick_data.get("ask")
        request = self._request_base(symbol_name)
        # Use "id" for simulator, "ticket" for MT5
        position_id = int(data.get("id") or data.get("ticket") or 0)
        request.update(
            {
                "action": mt5.TRADE_ACTION_DEAL,
                "type": order_type,
                "position": position_id,
                "volume": float(volume),
                "price": float(price),
            }
        )
        return self._send_request(request)

    def PositionCloseBy(self, ticket: int, ticket_by: int) -> bool:
        """Close a position with the specified ticket by an opposite position."""
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "type": mt5.ORDER_TYPE_CLOSE_BY,
            "position": int(ticket),
            "position_by": int(ticket_by),
        }
        return self._send_request(request)

    # ---------------------------------------------------------------------
    # Additional methods
    # ---------------------------------------------------------------------
    def Buy(
        self,
        volume: float,
        symbol: str,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> bool:
        """Open a long position with specified parameters."""
        return self.PositionOpen(
            symbol, mt5.ORDER_TYPE_BUY, volume, price, sl, tp, comment
        )

    def Sell(
        self,
        volume: float,
        symbol: str,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> bool:
        """Open a short position with specified parameters."""
        return self.PositionOpen(
            symbol, mt5.ORDER_TYPE_SELL, volume, price, sl, tp, comment
        )

    def BuyLimit(
        self,
        volume: float,
        symbol: str,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[int] = None,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Places a pending order of the Buy Limit type with specified parameters."""
        return self.OrderOpen(
            symbol,
            mt5.ORDER_TYPE_BUY_LIMIT,
            volume,
            price,
            sl,
            tp,
            stoplimit,
            type_time,
            expiration,
            comment,
        )

    def BuyStop(
        self,
        volume: float,
        symbol: str,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[int] = None,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Places a pending order of the Buy Stop type with specified parameters."""
        return self.OrderOpen(
            symbol,
            mt5.ORDER_TYPE_BUY_STOP,
            volume,
            price,
            sl,
            tp,
            stoplimit,
            type_time,
            expiration,
            comment,
        )

    def SellLimit(
        self,
        volume: float,
        symbol: str,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[int] = None,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Places a pending order of the Sell Limit type with specified parameters."""
        return self.OrderOpen(
            symbol,
            mt5.ORDER_TYPE_SELL_LIMIT,
            volume,
            price,
            sl,
            tp,
            stoplimit,
            type_time,
            expiration,
            comment,
        )

    def SellStop(
        self,
        volume: float,
        symbol: str,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[int] = None,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Places a pending order of the Sell Stop type with specified parameters."""
        return self.OrderOpen(
            symbol,
            mt5.ORDER_TYPE_SELL_STOP,
            volume,
            price,
            sl,
            tp,
            stoplimit,
            type_time,
            expiration,
            comment,
        )

    # ---------------------------------------------------------------------
    # Access to the last request parameters
    # ---------------------------------------------------------------------
    def Request(self) -> dict[str, Any]:
        """Get the copy of the last request structure."""
        return dict(self._last_request)

    def RequestAction(self) -> int:
        """Get the trade operation type."""
        return int(self._last_request.get("action", 0))

    def RequestActionDescription(self) -> str:
        """Get the trade operation type as string."""
        value = self.RequestAction()
        mapping = {
            getattr(mt5, "TRADE_ACTION_DEAL", None): "Deal",
            getattr(mt5, "TRADE_ACTION_PENDING", None): "Pending",
            getattr(mt5, "TRADE_ACTION_SLTP", None): "SL/TP",
            getattr(mt5, "TRADE_ACTION_MODIFY", None): "Modify",
            getattr(mt5, "TRADE_ACTION_REMOVE", None): "Remove",
        }
        return mapping.get(value, "Unknown")

    def RequestMagic(self) -> int:
        """Get the magic number of the Expert Advisor."""
        return int(self._last_request.get("magic", self._magic))

    def RequestOrder(self) -> int:
        """Get the order ticket used in the last request."""
        return int(self._last_request.get("order", 0))

    def RequestSymbol(self) -> str:
        """Get the name of the symbol used in the last request."""
        return str(self._last_request.get("symbol", ""))

    def RequestVolume(self) -> float:
        """Get the trade volume used in the last request."""
        return float(self._last_request.get("volume", 0.0))

    def RequestPrice(self) -> float:
        """Get the price used in the last request."""
        return float(self._last_request.get("price", 0.0))

    def RequestStopLimit(self) -> float:
        """Get the price of Stop Limit order used in the last request."""
        return float(self._last_request.get("stoplimit", 0.0))

    def RequestSL(self) -> float:
        """Get the Stop Loss price of the order used in the last request."""
        return float(self._last_request.get("sl", 0.0))

    def RequestTP(self) -> float:
        """Get the Take Profit price of the order used in the last request."""
        return float(self._last_request.get("tp", 0.0))

    def RequestDeviation(self) -> int:
        """Get the maximum allowable price deviation used in the last request."""
        return int(self._last_request.get("deviation", 0))

    def RequestType(self) -> int:
        """Get the type of the order used in the last request."""
        return int(self._last_request.get("type", 0))

    def RequestTypeDescription(self) -> str:
        """Get the type of the order (as string) used in the last request."""
        value = self.RequestType()
        mapping = {
            getattr(mt5, "ORDER_TYPE_BUY", None): "Buy",
            getattr(mt5, "ORDER_TYPE_SELL", None): "Sell",
            getattr(mt5, "ORDER_TYPE_BUY_LIMIT", None): "Buy Limit",
            getattr(mt5, "ORDER_TYPE_SELL_LIMIT", None): "Sell Limit",
            getattr(mt5, "ORDER_TYPE_BUY_STOP", None): "Buy Stop",
            getattr(mt5, "ORDER_TYPE_SELL_STOP", None): "Sell Stop",
            getattr(mt5, "ORDER_TYPE_BUY_STOP_LIMIT", None): "Buy Stop Limit",
            getattr(mt5, "ORDER_TYPE_SELL_STOP_LIMIT", None): "Sell Stop Limit",
            getattr(mt5, "ORDER_TYPE_CLOSE_BY", None): "Close By",
        }
        return mapping.get(value, "Unknown")

    def RequestTypeFilling(self) -> int:
        """Get the filling type of the order used in the last request."""
        return int(self._last_request.get("type_filling", 0))

    def RequestTypeFillingDescription(self) -> str:
        """Get the filling type of the order (as string) used in the last request."""
        value = self.RequestTypeFilling()
        mapping = {
            getattr(mt5, "ORDER_FILLING_FOK", None): "FOK",
            getattr(mt5, "ORDER_FILLING_IOC", None): "IOC",
            getattr(mt5, "ORDER_FILLING_RETURN", None): "Return",
        }
        return mapping.get(value, "Unknown")

    def RequestTypeTime(self) -> int:
        """Get the validity period of the order used in the last request."""
        return int(self._last_request.get("type_time", 0))

    def RequestTypeTimeDescription(self) -> str:
        """Get the validity period of the order (as string) used in the last request."""
        value = self.RequestTypeTime()
        mapping = {
            getattr(mt5, "ORDER_TIME_GTC", None): "GTC",
            getattr(mt5, "ORDER_TIME_DAY", None): "Day",
            getattr(mt5, "ORDER_TIME_SPECIFIED", None): "Specified",
            getattr(mt5, "ORDER_TIME_SPECIFIED_DAY", None): "Specified Day",
        }
        return mapping.get(value, "Unknown")

    def RequestExpiration(self) -> int:
        """Get the expiration time of the order used in the last request."""
        return int(self._last_request.get("expiration", 0))

    def RequestComment(self) -> str:
        """Get the comment of the order used in the last request."""
        return str(self._last_request.get("comment", ""))

    def RequestPosition(self) -> int:
        """Get position ticket."""
        return int(self._last_request.get("position", 0))

    def RequestPositionBy(self) -> int:
        """Get opposite position ticket."""
        return int(self._last_request.get("position_by", 0))

    # ---------------------------------------------------------------------
    # Access to the last request checking results
    # ---------------------------------------------------------------------
    def CheckResult(self) -> dict[str, Any]:
        """Get the copy of the structure of the last request check result."""
        return dict(self._last_check)

    def CheckResultRetcode(self) -> int:
        """Get the retcode field of MqlTradeCheckResult."""
        return int(self._last_check.get("retcode", 0))

    def CheckResultRetcodeDescription(self) -> str:
        """Get the retcode description of MqlTradeCheckResult."""
        retcode = self.CheckResultRetcode()
        if hasattr(self._api, "trade_retcode_description"):
            return str(self._api.trade_retcode_description(retcode))
        return str(retcode)

    def CheckResultBalance(self) -> float:
        """Get the balance field of MqlTradeCheckResult."""
        return float(self._last_check.get("balance", 0.0))

    def CheckResultEquity(self) -> float:
        """Get the equity field of MqlTradeCheckResult."""
        return float(self._last_check.get("equity", 0.0))

    def CheckResultProfit(self) -> float:
        """Get the floating profit after executing a trading operation."""
        return float(self._last_check.get("profit", 0.0))

    def CheckResultMargin(self) -> float:
        """Get the margin field of MqlTradeCheckResult."""
        return float(self._last_check.get("margin", 0.0))

    def CheckResultMarginFree(self) -> float:
        """Get the margin_free field of MqlTradeCheckResult."""
        return float(self._last_check.get("margin_free", 0.0))

    def CheckResultMarginLevel(self) -> float:
        """Get the margin_level field of MqlTradeCheckResult."""
        return float(self._last_check.get("margin_level", 0.0))

    def CheckResultComment(self) -> str:
        """Get the comment field of MqlTradeCheckResult."""
        return str(self._last_check.get("comment", ""))

    # ---------------------------------------------------------------------
    # Access to the last request execution results
    # ---------------------------------------------------------------------
    def Result(self) -> dict[str, Any]:
        """Get the copy of the structure of the last request result."""
        return dict(self._last_result)

    def ResultRetcode(self) -> int:
        """Get the code of request result."""
        return int(self._last_result.get("retcode", 0))

    def ResultRetcodeDescription(self) -> str:
        """Get the code of request result as a string."""
        retcode = self.ResultRetcode()
        if hasattr(self._api, "trade_retcode_description"):
            return str(self._api.trade_retcode_description(retcode))
        return str(retcode)

    def ResultDeal(self) -> int:
        """Get the deal ticket."""
        return int(self._last_result.get("deal", 0))

    def ResultOrder(self) -> int:
        """Get the order ticket."""
        return int(self._last_result.get("order", 0))

    def ResultVolume(self) -> float:
        """Get the volume of deal or order."""
        return float(self._last_result.get("volume", 0.0))

    def ResultPrice(self) -> float:
        """Get the price, confirmed by broker."""
        return float(self._last_result.get("price", 0.0))

    def ResultBid(self) -> float:
        """Get the current bid price (the requote)."""
        return float(self._last_result.get("bid", 0.0))

    def ResultAsk(self) -> float:
        """Get the current ask price (the requote)."""
        return float(self._last_result.get("ask", 0.0))

    def ResultComment(self) -> str:
        """Get the broker comment."""
        return str(self._last_result.get("comment", ""))

    # ---------------------------------------------------------------------
    # Auxiliary methods
    # ---------------------------------------------------------------------
    def FormatRequest(self) -> str:
        """Prepare the formatted string with last request parameters."""
        return f"Request: {self._last_request}"

    def FormatRequestResult(self) -> str:
        """Prepare the formatted string with results of the last request execution."""
        return f"Result: {self._last_result}"

    def PrintRequest(self) -> None:
        """Print the last request parameters into journal."""
        print(self.FormatRequest())

    def PrintResult(self) -> None:
        """Print the results of the last request into journal."""
        print(self.FormatRequestResult())

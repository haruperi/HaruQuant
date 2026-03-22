"""
Trade class (MT5-specific).

This module mirrors the MQL5 Standard Library Trade interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/ctrade


"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
import dataclasses
from types import SimpleNamespace

from apps.mt5 import get_mt5_api
from apps.utils import trade_validators as tv

mt5 = get_mt5_api()


@dataclasses.dataclass
class TradeResult:
    retcode: int = 0
    deal: int = 0
    order: int = 0
    volume: float = 0.0
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    comment: str = ""

    def __bool__(self) -> bool:
        if mt5 is None: return False
        placed = getattr(mt5, "TRADE_RETCODE_PLACED", 10008)
        return self.retcode in (mt5.TRADE_RETCODE_DONE, placed)

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
        self._type_filling_by_symbol: dict[str, int] = {}
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

    @staticmethod
    def _obj_to_dict(obj: Any) -> dict[str, Any]:
        if obj is None:
            return {}
        if hasattr(obj, "_asdict"):
            return dict(obj._asdict())
        if isinstance(obj, dict):
            return dict(obj)
        try:
            return dict(vars(obj))
        except Exception:
            return {}

    class _SymbolInfoAdapter:
        def __init__(self, raw: Any) -> None:
            self.raw = raw
            self.data = Trade._obj_to_dict(raw)

        def _get(self, method_name: str, attr_name: str, default: float = 0.0) -> float:
            method = getattr(self.raw, method_name, None)
            if callable(method):
                return float(method())
            return float(self.data.get(attr_name, default) or default)

        def VolumeMin(self) -> float:
            return self._get("VolumeMin", "volume_min", 0.0)

        def VolumeMax(self) -> float:
            return self._get("VolumeMax", "volume_max", 1e9)

        def VolumeStep(self) -> float:
            return self._get("VolumeStep", "volume_step", 0.0)

        def VolumeLimit(self) -> float:
            return self._get("VolumeLimit", "volume_limit", 0.0)

        def TradeTickSize(self) -> float:
            return self._get("TradeTickSize", "trade_tick_size", 0.0)

        def Point(self) -> float:
            return self._get("Point", "point", 0.0)

        def Digits(self) -> int:
            method = getattr(self.raw, "Digits", None)
            if callable(method):
                return int(method())
            return int(self.data.get("digits", 0) or 0)

        def TradeStopsLevel(self) -> int:
            return int(self._get("TradeStopsLevel", "trade_stops_level", 0.0))

        def TradeFreezeLevel(self) -> int:
            return int(self._get("TradeFreezeLevel", "trade_freeze_level", 0.0))

        def Bid(self) -> float:
            return self._get("Bid", "bid", 0.0)

        def Ask(self) -> float:
            return self._get("Ask", "ask", 0.0)

        def TradeContractSize(self) -> float:
            return self._get("TradeContractSize", "trade_contract_size", 100000.0)

    class _AccountInfoAdapter:
        def __init__(self, raw: Any, state: tv.BacktestState) -> None:
            self.raw = raw
            self.data = Trade._obj_to_dict(raw)
            self._state = state

        def _get(self, method_name: str, attr_name: str, default: float = 0.0) -> float:
            method = getattr(self.raw, method_name, None)
            if callable(method):
                return float(method())
            return float(self.data.get(attr_name, default) or default)

        def MarginFree(self) -> float:
            return self._get("MarginFree", "margin_free", 0.0)

        def Margin(self) -> float:
            return self._get("Margin", "margin", 0.0)

        def MarginLevel(self) -> float:
            return self._get("MarginLevel", "margin_level", 0.0)

        def Equity(self) -> float:
            return self._get("Equity", "equity", 0.0)

        def LimitOrders(self) -> int:
            return int(self._get("LimitOrders", "limit_orders", 0.0))

        def Leverage(self) -> int:
            return int(self._get("Leverage", "leverage", 1.0))

        def GetState(self) -> tv.BacktestState:
            return self._state

    def _build_validation_state(
        self,
        symbol_hint: Optional[str] = None,
        ticket_hint: Optional[int] = None,
    ) -> tv.BacktestState:
        state = tv.BacktestState()

        symbols: set[str] = set()
        if symbol_hint:
            symbols.add(str(symbol_hint))

        orders = self._api.orders_get() if hasattr(self._api, "orders_get") else ()
        for order in orders or ():
            row = self._obj_to_dict(order)
            ticket = int(row.get("ticket", 0) or 0)
            if ticket <= 0:
                continue
            symbol = str(row.get("symbol", "") or "")
            if symbol:
                symbols.add(symbol)
            state.trading_orders[str(ticket)] = {
                "ticket": str(ticket),
                "action": "order_open",
                "type": str(int(row.get("type", 0) or 0)),
                "price": str(
                    float(
                        row.get("price_open", row.get("price_current", row.get("price", 0.0)))
                        or 0.0
                    )
                ),
                "limit_price": str(float(row.get("price_stoplimit", 0.0) or 0.0)),
            }

        positions = self._api.positions_get() if hasattr(self._api, "positions_get") else ()
        for position in positions or ():
            row = self._obj_to_dict(position)
            ticket = int(
                row.get("ticket", row.get("identifier", row.get("position_id", 0))) or 0
            )
            if ticket <= 0:
                continue
            symbol = str(row.get("symbol", "") or "")
            if symbol:
                symbols.add(symbol)
            state.trading_deals[str(ticket)] = {
                "ticket": str(ticket),
                "symbol": symbol,
                "entry": "0",
                "volume": str(float(row.get("volume", 0.0) or 0.0)),
                "price_open": str(float(row.get("price_open", row.get("price", 0.0)) or 0.0)),
                "type": str(int(row.get("type", 0) or 0)),
            }

        if ticket_hint:
            ticket_key = str(int(ticket_hint))
            order_row = state.trading_orders.get(ticket_key)
            if order_row and order_row.get("symbol"):
                symbols.add(order_row["symbol"])

        for symbol in symbols:
            info = self._api.symbol_info(symbol) if hasattr(self._api, "symbol_info") else None
            if info is None:
                continue
            row = self._obj_to_dict(info)
            state.trading_symbols[symbol] = {
                "volume_min": str(float(row.get("volume_min", 0.0) or 0.0)),
                "volume_max": str(float(row.get("volume_max", 0.0) or 0.0)),
                "volume_step": str(float(row.get("volume_step", 0.0) or 0.0)),
            }

        return state

    def _validation_fail(self, res: tv.TradeValidationResult) -> TradeResult:
        self._last_check = {"retcode": int(res.retcode), "comment": str(res.comment)}
        self._last_result = {"retcode": int(res.retcode), "comment": str(res.comment)}
        return TradeResult(retcode=int(res.retcode), comment=str(res.comment))

    def _validation_context(
        self,
        symbol: Optional[str],
        ticket: Optional[int] = None,
    ) -> tuple[Any, Optional[Any], tv.BacktestState]:
        state = self._build_validation_state(symbol_hint=symbol, ticket_hint=ticket)
        raw_account = self._api.account_info() if hasattr(self._api, "account_info") else None
        account = self._AccountInfoAdapter(raw_account, state)
        symbol_info = None
        if symbol:
            raw_symbol = self._api.symbol_info(symbol) if hasattr(self._api, "symbol_info") else None
            if raw_symbol is not None:
                symbol_info = self._SymbolInfoAdapter(raw_symbol)
        return account, symbol_info, state

    def _resolve_order_type(self, order_type: Any) -> int:
        if isinstance(order_type, int):
            return int(order_type)
        if not isinstance(order_type, str):
            raise TypeError("order_type must be int or string")

        token = order_type.strip().upper().replace("-", "_").replace(" ", "_")
        if token.startswith("ORDER_TYPE_"):
            token = token[len("ORDER_TYPE_") :]

        mapping = {
            "BUY": mt5.ORDER_TYPE_BUY,
            "SELL": mt5.ORDER_TYPE_SELL,
            "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
            "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
            "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
            "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
            "BUY_STOP_LIMIT": mt5.ORDER_TYPE_BUY_STOP_LIMIT,
            "SELL_STOP_LIMIT": mt5.ORDER_TYPE_SELL_STOP_LIMIT,
            "CLOSE_BY": mt5.ORDER_TYPE_CLOSE_BY,
        }
        if token not in mapping:
            raise ValueError(f"Unsupported order_type: {order_type}")
        return int(mapping[token])

    def _resolve_order_time(self, type_time: Any) -> int:
        if isinstance(type_time, int):
            return int(type_time)
        if not isinstance(type_time, str):
            raise TypeError("type_time must be int or string")

        token = type_time.strip().upper().replace("-", "_").replace(" ", "_")
        if token.startswith("ORDER_TIME_"):
            token = token[len("ORDER_TIME_") :]

        mapping = {
            "GTC": mt5.ORDER_TIME_GTC,
            "DAY": mt5.ORDER_TIME_DAY,
            "SPECIFIED": mt5.ORDER_TIME_SPECIFIED,
            "SPECIFIED_DAY": mt5.ORDER_TIME_SPECIFIED_DAY,
        }
        if token not in mapping:
            raise ValueError(f"Unsupported type_time: {type_time}")
        return int(mapping[token])

    def _resolve_order_filling(self, filling: Any) -> int:
        if isinstance(filling, int):
            return int(filling)
        if not isinstance(filling, str):
            raise TypeError("filling must be int or string")

        token = filling.strip().upper().replace("-", "_").replace(" ", "_")
        if token.startswith("ORDER_FILLING_"):
            token = token[len("ORDER_FILLING_") :]

        mapping = {
            "FOK": mt5.ORDER_FILLING_FOK,
            "IOC": mt5.ORDER_FILLING_IOC,
            "RETURN": mt5.ORDER_FILLING_RETURN,
        }
        if token not in mapping:
            raise ValueError(f"Unsupported filling: {filling}")
        return int(mapping[token])

    def _send_request(self, request: dict[str, Any]) -> TradeResult:
        if self._attempt_request(request):
            pass
        elif self._should_retry_filling():
            self._retry_with_fillings(request)
            
        return TradeResult(
            retcode=self.ResultRetcode(),
            deal=self.ResultDeal(),
            order=self.ResultOrder(),
            volume=self.ResultVolume(),
            price=self.ResultPrice(),
            bid=self.ResultBid(),
            ask=self.ResultAsk(),
            comment=self.ResultComment(),
        )

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
        # First retry without forcing type_filling and let terminal/server resolve it.
        request_fallback = dict(request)
        request_fallback.pop("type_filling", None)
        if self._attempt_request(request_fallback):
            return True

        candidates: list[int] = []
        symbol = request.get("symbol")
        if isinstance(symbol, str):
            resolved = self._resolve_filling_mode(symbol)
            if resolved is not None:
                candidates.append(int(resolved))

        for mode in (
            mt5.ORDER_FILLING_IOC,
            mt5.ORDER_FILLING_FOK,
            mt5.ORDER_FILLING_RETURN,
        ):
            if int(mode) not in candidates:
                candidates.append(int(mode))

        for mode in candidates:
            request_fallback = dict(request)
            request_fallback["type_filling"] = int(mode)
            if self._attempt_request(request_fallback):
                return True

        return False

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
        symbol_key = str(symbol).upper()
        filling = self._type_filling_by_symbol.get(symbol_key)
        if filling is None and self._type_filling is not None:
            filling = int(self._type_filling)
        if filling is None:
            filling = self._resolve_filling_mode(symbol)
        request: dict[str, Any] = {
            "symbol": symbol,
            "magic": self._magic,
            "deviation": self._deviation,
        }
        if filling is not None:
            request["type_filling"] = int(filling)
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
        trade_exec = data.get("trade_exemode")
        if isinstance(fill_mask, int):
            allowed_modes: list[int] = []

            # Preferred path: SYMBOL_FILLING_* bitmask flags.
            flag_to_order = [
                ("SYMBOL_FILLING_FOK", mt5.ORDER_FILLING_FOK),
                ("SYMBOL_FILLING_IOC", mt5.ORDER_FILLING_IOC),
                ("SYMBOL_FILLING_RETURN", mt5.ORDER_FILLING_RETURN),
            ]
            for flag_name, order_mode in flag_to_order:
                flag = getattr(mt5, flag_name, None)
                if isinstance(flag, int) and (fill_mask & flag):
                    allowed_modes.append(int(order_mode))

            # Fallback path for terminals that expose filling_mode as legacy bitmask.
            # Common convention: 1=FOK, 2=IOC, 4=RETURN.
            if not allowed_modes:
                if fill_mask & 1:
                    allowed_modes.append(int(mt5.ORDER_FILLING_FOK))
                if fill_mask & 2:
                    allowed_modes.append(int(mt5.ORDER_FILLING_IOC))
                if fill_mask & 4:
                    allowed_modes.append(int(mt5.ORDER_FILLING_RETURN))

            # Final fallback: some terminals expose direct enum value in filling_mode.
            if not allowed_modes and fill_mask in (
                mt5.ORDER_FILLING_FOK,
                mt5.ORDER_FILLING_IOC,
                mt5.ORDER_FILLING_RETURN,
            ):
                allowed_modes.append(int(fill_mask))

            if allowed_modes:
                is_market_exec = (
                    isinstance(trade_exec, int)
                    and trade_exec == getattr(mt5, "SYMBOL_TRADE_EXECUTION_MARKET", -1)
                )
                if is_market_exec:
                    preference = (
                        int(mt5.ORDER_FILLING_IOC),
                        int(mt5.ORDER_FILLING_FOK),
                        int(mt5.ORDER_FILLING_RETURN),
                    )
                else:
                    preference = (
                        int(mt5.ORDER_FILLING_RETURN),
                        int(mt5.ORDER_FILLING_IOC),
                        int(mt5.ORDER_FILLING_FOK),
                    )
                for candidate in preference:
                    if candidate in allowed_modes:
                        return candidate

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

    def SetTypeFilling(self, filling: Any) -> None:
        """Set filling type of the order."""
        self._type_filling = self._resolve_order_filling(filling)

    def SetTypeTime(self, type_time: Any) -> None:
        """Set order time type (e.g. GTC, DAY, SPECIFIED, SPECIFIED_DAY)."""
        self._type_time = self._resolve_order_time(type_time)

    def SetTypeFillingBySymbol(self, symbol: str) -> bool:
        """Set filling type of the order according to symbol settings."""
        filling = self._resolve_filling_mode(symbol)
        if filling is None:
            return False
        self._type_filling_by_symbol[str(symbol).upper()] = int(filling)
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
        order_type: Any,
        volume: float,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[Any] = None,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> TradeResult:
        """Places a pending order with specified parameters."""
        resolved_order_type = self._resolve_order_type(order_type)
        request = self._request_base(symbol)
        request.update(
            {
                "action": mt5.TRADE_ACTION_PENDING,
                "type": resolved_order_type,
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
            request["type_time"] = self._resolve_order_time(type_time)
        if expiration is not None:
            request["expiration"] = int(expiration.timestamp())
        account, symbol_info, _ = self._validation_context(symbol=symbol)
        req_obj = SimpleNamespace(**request)
        vres = tv.open_pending_order_validations(req_obj, account, symbol_info)
        if not vres.ok:
            return self._validation_fail(vres)
        return self._send_request(request)

    def OrderModify(
        self,
        ticket: int,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        stoplimit: float = 0.0,
        type_time: Optional[Any] = None,
        expiration: Optional[datetime] = None,
    ) -> TradeResult:
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
            request["type_time"] = self._resolve_order_time(type_time)
        symbol = None
        if hasattr(self._api, "orders_get"):
            existing = self._api.orders_get(ticket=int(ticket))
            if existing:
                symbol = self._obj_to_dict(existing[0]).get("symbol")
        if expiration is not None:
            request["expiration"] = int(expiration.timestamp())
        _, symbol_info, state = self._validation_context(
            symbol=str(symbol) if symbol else None,
            ticket=int(ticket),
        )
        vres = tv.modify_pending_order_validations(
            ticket=int(ticket),
            price=float(price),
            sl=float(sl),
            tp=float(tp),
            expiration=int(request.get("expiration", 0) or 0),
            state=state,
            symbol_info=symbol_info,
        )
        if not vres.ok:
            return self._validation_fail(vres)
        return self._send_request(request)

    def OrderDelete(self, ticket: int) -> TradeResult:
        """Delete a pending order."""
        request = {"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)}
        _, _, state = self._validation_context(symbol=None, ticket=int(ticket))
        vres = tv.delete_pending_order_validations(int(ticket), state)
        if not vres.ok:
            return self._validation_fail(vres)
        return self._send_request(request)

    # ---------------------------------------------------------------------
    # Operations with positions
    # ---------------------------------------------------------------------
    def PositionOpen(
        self,
        symbol: str,
        order_type: Any,
        volume: float,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> TradeResult:
        """Open a position with specified parameters."""
        resolved_order_type = self._resolve_order_type(order_type)
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
                if resolved_order_type == mt5.ORDER_TYPE_BUY
                else tick_data.get("bid")
            )
        request = self._request_base(symbol)
        request.update(
            {
                "action": mt5.TRADE_ACTION_DEAL,
                "type": resolved_order_type,
                "volume": float(volume),
                "price": float(price),
                "sl": float(sl),
                "tp": float(tp),
                "comment": comment,
            }
        )
        account, symbol_info, _ = self._validation_context(symbol=symbol)
        req_obj = SimpleNamespace(**request)
        vres = tv.open_position_validations(req_obj, account, symbol_info)
        if not vres.ok:
            return self._validation_fail(vres)
        return self._send_request(request)

    def PositionModify(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
        sl: float = 0.0,
        tp: float = 0.0,
    ) -> TradeResult:
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
        _, symbol_info, state = self._validation_context(
            symbol=str(data.get("symbol")) if data.get("symbol") else None,
            ticket=position_id,
        )
        vres = tv.modify_position_validations(
            str(data.get("symbol") or ""),
            int(position_id),
            state,
            sl=sl,
            tp=tp,
            symbol_info=symbol_info,
        )
        if not vres.ok:
            return self._validation_fail(vres)
        return self._send_request(request)

    def PositionClose(
        self, symbol: Optional[str] = None, ticket: Optional[int] = None
    ) -> TradeResult:
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
        _, _, state = self._validation_context(symbol=symbol_name, ticket=position_id)
        vres = tv.close_position_validations(str(symbol_name or ""), int(position_id), state)
        if not vres.ok:
            return self._validation_fail(vres)
        return self._send_request(request)

    def PositionClosePartial(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
        volume: float = 0.0,
    ) -> TradeResult:
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
        _, _, state = self._validation_context(symbol=symbol_name, ticket=position_id)
        vres = tv.close_partial_position_validations(
            str(symbol_name or ""),
            int(position_id),
            float(volume),
            state,
        )
        if not vres.ok:
            return self._validation_fail(vres)
        return self._send_request(request)

    def PositionCloseBy(self, ticket: int, ticket_by: int) -> TradeResult:
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
    ) -> TradeResult:
        """Open a long position with specified parameters."""
        return self.PositionOpen(
            symbol, "BUY", volume, price, sl, tp, comment
        )

    def Sell(
        self,
        volume: float,
        symbol: str,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> TradeResult:
        """Open a short position with specified parameters."""
        return self.PositionOpen(
            symbol, "SELL", volume, price, sl, tp, comment
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
    ) -> TradeResult:
        """Places a pending order of the Buy Limit type with specified parameters."""
        return self.OrderOpen(
            symbol,
            "BUY_LIMIT",
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
    ) -> TradeResult:
        """Places a pending order of the Buy Stop type with specified parameters."""
        return self.OrderOpen(
            symbol,
            "BUY_STOP",
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
    ) -> TradeResult:
        """Places a pending order of the Sell Limit type with specified parameters."""
        return self.OrderOpen(
            symbol,
            "SELL_LIMIT",
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
    ) -> TradeResult:
        """Places a pending order of the Sell Stop type with specified parameters."""
        return self.OrderOpen(
            symbol,
            "SELL_STOP",
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

"""Helpers to read MT5 client/account/symbol objects with wrapper compatibility."""

from __future__ import annotations

from typing import Any


def _call_or_attr(obj: Any, method_name: str, attr_name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    method = getattr(obj, method_name, None)
    if callable(method):
        try:
            return method()
        except Exception:
            return default
    return getattr(obj, attr_name, default)


def account_balance(account: Any) -> float:
    return float(_call_or_attr(account, 'Balance', 'balance', 0.0) or 0.0)


def account_equity(account: Any) -> float:
    return float(_call_or_attr(account, 'Equity', 'equity', 0.0) or 0.0)


def account_margin(account: Any) -> float:
    return float(_call_or_attr(account, 'Margin', 'margin', 0.0) or 0.0)


def account_free_margin(account: Any) -> float:
    return float(_call_or_attr(account, 'FreeMargin', 'margin_free', 0.0) or 0.0)


def account_margin_level(account: Any) -> float:
    return float(_call_or_attr(account, 'MarginLevel', 'margin_level', 0.0) or 0.0)


def account_profit(account: Any) -> float:
    return float(_call_or_attr(account, 'Profit', 'profit', 0.0) or 0.0)


def account_currency(account: Any) -> str:
    return str(_call_or_attr(account, 'Currency', 'currency', '') or '')


def account_leverage(account: Any) -> int:
    return int(_call_or_attr(account, 'Leverage', 'leverage', 1) or 1)


def account_trade_allowed(account: Any) -> bool:
    return bool(_call_or_attr(account, 'TradeAllowed', 'trade_allowed', True))


def account_trade_expert(account: Any) -> bool:
    return bool(_call_or_attr(account, 'TradeExpert', 'trade_expert', True))


def symbol_bid(symbol_info: Any) -> float:
    return float(_call_or_attr(symbol_info, 'Bid', 'bid', 0.0) or 0.0)


def symbol_ask(symbol_info: Any) -> float:
    return float(_call_or_attr(symbol_info, 'Ask', 'ask', 0.0) or 0.0)


def symbol_name(symbol_info: Any) -> str:
    return str(_call_or_attr(symbol_info, 'Name', 'name', '') or '')


def symbol_trade_mode_description(symbol_info: Any) -> str:
    raw = _call_or_attr(symbol_info, 'TradeModeDescription', 'trade_mode', '')
    return str(raw or '')


def symbol_volume_min(symbol_info: Any) -> float:
    return float(_call_or_attr(symbol_info, 'LotsMin', 'volume_min', 0.0) or 0.0)


def symbol_volume_max(symbol_info: Any) -> float:
    return float(_call_or_attr(symbol_info, 'LotsMax', 'volume_max', 0.0) or 0.0)


def symbol_volume_step(symbol_info: Any) -> float:
    return float(_call_or_attr(symbol_info, 'LotsStep', 'volume_step', 0.0) or 0.0)

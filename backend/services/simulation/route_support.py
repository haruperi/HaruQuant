"""Shared helpers for simulator route payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.mcp.mt5_mcp import get_mt5_api

from .session_runtime import SimulatorSession

mt5 = get_mt5_api()


def normalize_position(position: dict) -> dict:
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


def _simulator_account_currency(active: SimulatorSession) -> str:
    if getattr(active, "latest_risk_state", None) is not None:
        currency = getattr(active.latest_risk_state.account, "currency", None)
        if currency:
            token = str(currency).upper().strip()
            if token:
                return token
    account = active.engine.account_info()
    token = str(
        account.get("currency") or account.get("currency_code") or "USD"
    ).upper().strip()
    return token or "USD"


def _simulator_price_for_symbol(
    active: SimulatorSession, symbol: str
) -> Optional[float]:
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


def _position_notional_from_payload(active: SimulatorSession, position: dict) -> float:
    symbol_name = str(position.get("symbol", "") or "")
    if not symbol_name:
        return 0.0

    symbol_info = active.engine.symbol_info(symbol_name)
    contract_size = float(getattr(symbol_info, "trade_contract_size", 0.0) or 0.0)
    if contract_size <= 0.0:
        return 0.0

    market_price = float(position.get("price_current") or position.get("price_open") or 0.0)
    volume = float(position.get("volume") or 0.0)
    if market_price <= 0.0 or volume <= 0.0:
        return 0.0

    raw_notional = float(volume * contract_size * market_price)
    profit_currency = str(
        getattr(
            symbol_info,
            "currency_profit",
            getattr(symbol_info, "profit_currency", ""),
        )
        or ""
    ).upper().strip()
    account_currency = _simulator_account_currency(active)
    return _convert_simulator_value_to_account_currency(
        active,
        raw_notional,
        profit_currency,
        account_currency,
    )


def _parse_replay_time(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 1e12:
            raw /= 1000.0
        return datetime.fromtimestamp(raw, tz=timezone.utc).replace(tzinfo=None)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


def _first_present(mapping: dict, *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _replay_side(trade: dict) -> str:
    raw = _first_present(trade, "type", "side", "direction", "order_type")
    text = str(raw or "").lower()
    return "buy" if raw == 0 or "buy" in text or "long" in text else "sell"


def _replay_float(trade: dict, *keys: str, default: float = 0.0) -> float:
    value = _first_present(trade, *keys)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _current_replay_time_by_symbol(active: SimulatorSession) -> dict[str, datetime]:
    out: dict[str, datetime] = {}
    for symbol, market in getattr(active, "current_market_by_symbol", {}).items():
        parsed = _parse_replay_time((market or {}).get("time"))
        if parsed is not None:
            out[str(symbol)] = parsed
    return out


def _replay_position_payloads(active: SimulatorSession) -> list[dict]:
    if active.config.get("mode") != "replay" or not active.replay_trades:
        return []

    current_time_by_symbol = _current_replay_time_by_symbol(active)
    if not current_time_by_symbol:
        return []

    payloads: list[dict] = []
    for index, raw_trade in enumerate(active.replay_trades):
        if not isinstance(raw_trade, dict):
            continue
        symbol = str(raw_trade.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        current_market = getattr(active, "current_market_by_symbol", {}).get(symbol) or {}
        current_time = current_time_by_symbol.get(symbol)
        if current_time is None:
            continue

        open_time = _parse_replay_time(
            _first_present(raw_trade, "open_time", "time_open", "entry_time", "time", "entry_dt")
        )
        close_time = _parse_replay_time(
            _first_present(raw_trade, "close_time", "time_close", "exit_time", "exit_dt")
        )
        if open_time is None or current_time < open_time:
            continue
        if close_time is not None and current_time >= close_time:
            continue

        open_price = _replay_float(raw_trade, "open_price", "entry_price", "price_open")
        current_price = float(current_market.get("close") or current_market.get("bid") or open_price or 0.0)
        volume = _replay_float(raw_trade, "volume", "lots", "size", default=0.0)
        if open_price <= 0.0 or current_price <= 0.0 or volume <= 0.0:
            continue

        side = _replay_side(raw_trade)
        symbol_info = active.engine.symbol_info(symbol)
        contract_size = float(getattr(symbol_info, "trade_contract_size", 100000.0) or 100000.0)
        price_delta = current_price - open_price if side == "buy" else open_price - current_price
        profit = float(price_delta * volume * contract_size)
        raw_id = _first_present(raw_trade, "trade_id", "id", "ticket", "order", "position_id", "deal_id")
        try:
            ticket = int(raw_id)
        except (TypeError, ValueError):
            ticket = 900000000 + index

        payloads.append(
            {
                "ticket": ticket,
                "identifier": ticket,
                "symbol": symbol,
                "type": side,
                "volume": volume,
                "price_open": open_price,
                "price_current": current_price,
                "sl": _replay_float(raw_trade, "sl", "stop_loss"),
                "tp": _replay_float(raw_trade, "tp", "take_profit"),
                "profit": profit,
                "swap": _replay_float(raw_trade, "swap"),
                "commission": _replay_float(raw_trade, "commission", "commissions"),
                "margin_required": 0.0,
                "time": open_time.isoformat(),
                "comment": f"replay:{raw_id or index + 1}",
            }
        )

    return payloads


def normalize_order(order: dict) -> dict:
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
        "id": int(order.get("ticket") or order.get("identifier") or order.get("id") or 0),
        "symbol": order.get("symbol", ""),
        "type": type_map.get(order_type, str(order_type)),
        "volume": float(order.get("volume_current") or order.get("volume_initial") or 0.0),
        "open_price": float(order.get("open_price") or order.get("price_open") or 0.0),
        "sl": float(order.get("sl") or 0.0),
        "tp": float(order.get("tp") or 0.0),
        "time": order.get("time"),
        "expiry_date": order.get("expiry_date"),
        "comment": order.get("comment", ""),
    }


def position_info_to_dict(position: Any) -> dict:
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


def order_info_to_dict(order: Any) -> dict:
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


def collect_positions_orders(active: SimulatorSession) -> tuple[list[dict], list[dict]]:
    positions_raw = active.simulator._simulator.positions_get() or []
    orders_raw = active.simulator._simulator.orders_get() or []
    position_payloads = []
    for pos in positions_raw:
        payload = position_info_to_dict(pos)
        volume = float(payload.get("volume", 0.0) or 0.0)
        if abs(volume) <= 1e-12:
            continue
        position_payloads.append(payload)
    position_payloads.extend(_replay_position_payloads(active))
    gross_notional = float(
        sum(_position_notional_from_payload(active, pos) for pos in position_payloads)
    )
    positions = []
    for pos in position_payloads:
        normalized = normalize_position(pos)
        exposure = _position_notional_from_payload(active, pos)
        normalized["exposure"] = float(exposure)
        normalized["weight"] = (
            float(exposure / gross_notional) if gross_notional > 0.0 else 0.0
        )
        positions.append(normalized)
    orders = [normalize_order(order_info_to_dict(order)) for order in orders_raw]
    return positions, orders


def refresh_session_risk_state(active: SimulatorSession) -> None:
    active.refresh_risk_state()


def monitor_refresh_collect(
    active: SimulatorSession,
) -> tuple[list[dict], list[dict]]:
    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)
    refresh_session_risk_state(active)
    return collect_positions_orders(active)


def build_session_state_response(active: SimulatorSession) -> Dict[str, Any]:
    positions, orders = monitor_refresh_collect(active)
    
    # Return replay_trades if in replay mode, otherwise return engine trades
    is_replay = active.config.get("mode") == "replay"
    trades = active.replay_trades if is_replay else active.engine.get_completed_trades()
    
    return {
        "positions": positions,
        "orders": orders,
        "trades": trades,
        "market": active.get_market_snapshots(),
        "risk_snapshot": active.get_risk_summary(),
        "risk_scorecard": active.get_risk_score_summary(),
        "recommendations": active.get_recommendation_summary(),
        "governance": active.get_governance_report(),
    }

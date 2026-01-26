"""
Order send usage example (tester + live).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import MetaTrader5 as mt5
from apps.ctrade import CSymbolInfo
from apps.simulator import TradeGateway, TradeSimulator
from apps.sqlite import SQLiteDatabase


def _run_scenario(
    trade: Any, sim: TradeSimulator, symbol: str, label: str, is_tester: bool
) -> None:
    sim.start(is_tester=is_tester)
    info = CSymbolInfo(symbol)
    info.Name(symbol)
    info.Refresh()
    info.RefreshRates()
    if not info.IsSynchronized():
        print(f"[{label}] Failed to synchronize symbol data.")
        return

    pip = info.PipSize()
    ask = info.Ask()
    bid = info.Bid()

    trade.SetExpertMagicNumber(123456)
    trade.SetDeviationInPoints(10)

    # Market orders
    trade.Buy(0.1, symbol, price=ask, sl=ask - 20 * pip, tp=ask + 40 * pip, comment="buy")
    trade.Sell(0.1, symbol, price=bid, sl=bid + 20 * pip, tp=bid - 40 * pip, comment="sell")

    # Pending orders
    expiry = datetime.now(timezone.utc) + timedelta(days=1)
    trade.BuyLimit(
        0.1,
        symbol,
        price=bid - 5 * pip,
        sl=bid - 20 * pip,
        tp=bid + 40 * pip,
        expiration=expiry,
        comment="buy limit",
    )
    trade.SellLimit(
        0.1,
        symbol,
        price=ask + 5 * pip,
        sl=ask + 20 * pip,
        tp=ask - 40 * pip,
        expiration=expiry,
        comment="sell limit",
    )
    trade.BuyStop(
        0.1,
        symbol,
        price=ask + 5 * pip,
        sl=ask - 20 * pip,
        tp=ask + 40 * pip,
        expiration=expiry,
        comment="buy stop",
    )
    trade.SellStop(
        0.1,
        symbol,
        price=bid - 5 * pip,
        sl=bid + 20 * pip,
        tp=bid - 40 * pip,
        expiration=expiry,
        comment="sell stop",
    )

    # Position modifications / closes
    positions = sim.positions_get()
    if positions:
        ticket = (
            positions[0]["id"]
            if isinstance(positions[0], dict)
            else positions[0].ticket
        )
        trade.PositionModify(ticket=ticket, sl=ask - 10 * pip, tp=ask + 30 * pip)
        trade.PositionClose(ticket=ticket)

    # Pending order modifications / deletes
    orders = sim.orders_get()
    if orders:
        first_order = orders[0]
        order_id = (
            first_order["id"] if isinstance(first_order, dict) else first_order.ticket
        )
        order_price = (
            first_order["open_price"]
            if isinstance(first_order, dict)
            else first_order.price_open
        )
        trade.OrderModify(order_id, price=order_price)
        trade.OrderDelete(order_id)

    print(f"[{label}] Orders:\n", sim.orders_get())
    print(f"[{label}] Positions:\n", sim.positions_get())
    print(f"[{label}] Last request:\n", trade.Request())
    print(f"[{label}] Last check:\n", trade.CheckResult())
    print(f"[{label}] Last result:\n", trade.Result())


def main() -> None:
    symbol = "EURUSD"

    if not mt5.initialize():
        print(f"Failed to initialize MT5. Error = {mt5.last_error()}")
        return

    db = SQLiteDatabase()
    db.initialize_database()
    sim = TradeSimulator(simulator_name="OrderSendDemo", deposit=1000.0, db=db)
    gateway = TradeGateway(sim)

    trade = gateway.get_trade(is_tester=True)
    _run_scenario(trade, sim, symbol, "Tester", True)

    trade = gateway.get_trade(is_tester=False)
    _run_scenario(trade, sim, symbol, "Live", False)

    mt5.shutdown()


if __name__ == "__main__":
    main()

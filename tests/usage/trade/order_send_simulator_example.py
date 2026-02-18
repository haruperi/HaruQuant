"""
Example usage of MT5-like order_send in the simulator.
"""

import os
import sys

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import get_mt5_api
from apps.mt5 import Trade
from apps.simulation.data import (
    TradeSimulator,
    AccountInfoSimulator,
    SymbolInfoSimulator,
    SymbolTickSimulator,
)

mt5 = get_mt5_api()


def main() -> None:
    print("=" * 70)
    print("OrderSend Simulator Example")
    print("=" * 70)
    print()

    account = AccountInfoSimulator(balance=10000, equity=10000, margin_free=10000)
    symbols = {
        "EURUSD": SymbolInfoSimulator(
            symbol="EURUSD",
            bid=1.1000,
            ask=1.1002,
            point=0.00001,
            trade_stops_level=10,
        )
    }
    ticks = {
        "EURUSD": SymbolTickSimulator(
            bid=1.1000,
            ask=1.1002,
            last=1.1001,
        )
    }

    sim = TradeSimulator(
        account_data=account,
        symbols_data=symbols,
        ticks_data=ticks,
    )

    trade = Trade(api=sim)
    trade.SetDeviationInPoints(10)
    trade.SetTypeFillingBySymbol("EURUSD")

    print("1) Open position (BUY)")
    ok = trade.PositionOpen(
        symbol="EURUSD",
        order_type=mt5.ORDER_TYPE_BUY,
        volume=0.10,
        price=0.0,
        sl=1.0990,
        tp=1.1015,
        comment="Sim open",
    )
    print(f"   success={ok} retcode={trade.ResultRetcode()} {trade.ResultRetcodeDescription()}")
    pos_id = trade.ResultOrder()
    print(f"   position_id={pos_id}")
    print()

    print("2) Modify position (SL/TP)")
    ok = trade.PositionModify(
        ticket=int(pos_id),
        sl=1.0995,
        tp=1.1018,
    )
    print(f"   success={ok} retcode={trade.ResultRetcode()} {trade.ResultRetcodeDescription()}")
    print()

    print("3) Close position")
    ok = trade.PositionClose(ticket=int(pos_id))
    print(f"   success={ok} retcode={trade.ResultRetcode()} {trade.ResultRetcodeDescription()}")
    print()

    print("4) Place pending order (BUY LIMIT)")
    ok = trade.OrderOpen(
        symbol="EURUSD",
        order_type=mt5.ORDER_TYPE_BUY_LIMIT,
        volume=0.10,
        price=1.0990,
        sl=1.0980,
        tp=1.1010,
        comment="Sim pending",
    )
    print(f"   success={ok} retcode={trade.ResultRetcode()} {trade.ResultRetcodeDescription()}")
    order_id = trade.ResultOrder()
    print(f"   order_id={order_id}")
    print()

    print("5) Modify pending order")
    ok = trade.OrderModify(
        ticket=int(order_id),
        price=1.0985,
        sl=1.0975,
        tp=1.1015,
    )
    print(f"   success={ok} retcode={trade.ResultRetcode()} {trade.ResultRetcodeDescription()}")
    print()

    print("6) Delete pending order")
    ok = trade.OrderDelete(ticket=int(order_id))
    print(f"   success={ok} retcode={trade.ResultRetcode()} {trade.ResultRetcodeDescription()}")
    print()

    # Prefer direct C++ info API; fallback keeps example runnable on wrappers.
    history = []
    if hasattr(sim, "_simulator") and hasattr(sim._simulator, "history_order_infos_get"):
        history = sim._simulator.history_order_infos_get() or []
    else:
        history = sim.history_orders_get() or []
    print(f"History orders count: {len(history)}")
    if history:
        last = history[-1]._asdict() if hasattr(history[-1], "_asdict") else dict(history[-1])
        print(f"Last history state: {last.get('state')}")

    print()
    print("=" * 70)
    print("Example Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()



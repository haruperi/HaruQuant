"""
C++ OMS usage example: state machine + idempotent client_order_id.
"""

from __future__ import annotations


def main() -> None:
    try:
        import hqt_engine.sim as sim
    except ImportError:
        print("hqt_engine.sim not available. Build bridge first.")
        return

    client = sim.SimulatorClient()

    symbol = sim.SymbolInfoData()
    symbol.symbol = "EURUSD"
    symbol.point = 0.00001
    symbol.spread = 10
    symbol.bid = 1.10000
    symbol.ask = 1.10010
    client.set_symbol_info(symbol)

    tick = sim.SymbolTickData()
    tick.time = 1
    tick.time_msc = 1000
    tick.bid = 1.10000
    tick.ask = 1.10010
    tick.last = 1.10000
    client.set_symbol_tick("EURUSD", tick)

    req = sim.TradeRequest()
    req.action = 1  # DEAL
    req.type = 0  # BUY
    req.symbol = "EURUSD"
    req.volume = 0.10
    req.client_order_id = "sample-client-001"

    first = client.order_send(req)
    second = client.order_send(req)  # idempotent replay
    print("first.order :", first.order)
    print("second.order:", second.order)
    print("cached same :", first.order == second.order)
    print("state       :", client.order_state_name(first.order))

    pending = sim.TradeRequest()
    pending.action = 5  # PENDING
    pending.type = 2  # BUY_LIMIT
    pending.symbol = "EURUSD"
    pending.volume = 0.10
    pending.price = 1.09500
    place = client.order_send(pending)
    print("pending state:", client.order_state_name(place.order))

    remove = sim.TradeRequest()
    remove.action = 8
    remove.order = place.order
    client.order_send(remove)
    print("after cancel :", client.order_state_name(place.order))


if __name__ == "__main__":
    main()


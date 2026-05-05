from haruquant.execution import core


def test_order_send_close_uses_position_type_for_buy_profit_calculation():
    state = core.SimulatorState({"balance": 10000.0, "equity": 10000.0, "commission": 7.0})
    state.trading_symbols = [
        core.SymbolInfo(
            {
                "name": "AUDUSD",
                "bid": 1.1020,
                "ask": 1.1022,
                "last": 1.1021,
                "point": 0.00001,
                "trade_contract_size": 100000.0,
            }
        )
    ]
    state.trading_deals = [
        core.DealInfo(
            {
                "ticket": 1,
                "position_id": 1,
                "type": 0,
                "entry": 0,
                "volume": 0.1,
                "price_open": 1.1000,
                "price_current": 1.1000,
                "sl": 0.0,
                "tp": 0.0,
                "commission": -0.7,
                "swap": 0.0,
                "symbol": "AUDUSD",
            }
        )
    ]

    calls = []

    def profit_calculator(order_type, symbol, volume, price_open, price_close):
        calls.append((order_type, symbol, volume, price_open, price_close))
        assert order_type == 0
        return 20.0

    result = core.order_send(
        state,
        {
            "action": 1,
            "symbol": "AUDUSD",
            "type": 1,
            "position": 1,
            "volume": 0.1,
            "price": 1.1020,
        },
        profit_calculator=profit_calculator,
        strict_calc_access=True,
    )

    assert result.retcode == 10009
    assert calls == [(0, "AUDUSD", 0.1, 1.1, 1.102)]
    assert state.trading_account.balance == 10019.3
    assert len(state.trading_deals) == 0

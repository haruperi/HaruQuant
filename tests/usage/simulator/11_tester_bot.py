"""
Tester bot usage example.
"""

import MetaTrader5 as mt5
from apps.ctrade import CTrade
from apps.simulator.tester import Tester


def main() -> None:
    if not mt5.initialize():
        print(f"Failed to Initialize MetaTrader5. Error = {mt5.last_error()}")
        mt5.shutdown()
        return

    tester_config = {
        "bot_name": "MY EA",
        "symbols": ["EURUSD", "USDCAD", "USDJPY"],
        "timeframe": "H1",
        "start_date": "01.01.2025 00:00",
        "end_date": "31.12.2025 00:00",
        "modelling": "1-minute-ohlc",
        "deposit": 1000,
        "leverage": "1:100",
    }

    tester = Tester(tester_config=tester_config, mt5_instance=mt5)

    symbol = "EURUSD"
    magic_number = 10012026
    slippage = 100
    sl = 500
    tp = 700

    tester.sim.set_magic_number(magic_number)
    tester.sim.set_deviation_in_points(slippage)
    m_trade = CTrade(api=tester.sim)
    m_trade.SetExpertMagicNumber(magic_number)
    m_trade.SetDeviationInPoints(slippage)

    symbol_info = tester.sim.symbol_info(symbol=symbol)
    if not symbol_info:
        print("Failed to read symbol info.")
        return

    def pos_exists(magic: int, pos_type: int) -> bool:
        for position in tester.sim.positions_get():
            if position["type"] == pos_type and position["magic"] == magic:
                return True
        return False

    def on_tick() -> None:
        tick_info = tester.sim.symbol_info_tick(symbol=symbol)
        if not tick_info:
            return

        ask = tick_info["ask"]
        bid = tick_info["bid"]
        pts = symbol_info.get("point", 0.00001)

        if not pos_exists(magic=magic_number, pos_type=mt5.POSITION_TYPE_BUY):
            m_trade.Buy(
                volume=0.1,
                symbol=symbol,
                price=ask,
                sl=ask - sl * pts,
                tp=ask + tp * pts,
                comment="Tester buy",
            )
            print("Buy result:", m_trade.Result())

        if not pos_exists(magic=magic_number, pos_type=mt5.POSITION_TYPE_SELL):
            m_trade.Sell(
                volume=0.1,
                symbol=symbol,
                price=bid,
                sl=bid + sl * pts,
                tp=bid - tp * pts,
                comment="Tester sell",
            )
            print("Sell result:", m_trade.Result())

    tester.OnTick(ontick_func=on_tick)


if __name__ == "__main__":
    main()

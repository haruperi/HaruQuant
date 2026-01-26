"""
Tester 101 usage example.
"""

import MetaTrader5 as mt5
from apps.simulator.tester import Tester


def main() -> None:
    config = {
        "bot_name": "MY EA",
        "symbols": ["EURUSD", "USDCAD", "USDJPY"],
        "timeframe": "H1",
        "start_date": "02.01.2026 03:00",
        "end_date": "26.01.2026 03:00",
        "modelling": "real_ticks",
        "deposit": 10000,
        "leverage": "1:1000",
    }

    tester = Tester(tester_config=config, mt5_instance=mt5)

    def ontick_function() -> None:
        pass

    tester.OnTick(ontick_function)


if __name__ == "__main__":
    main()

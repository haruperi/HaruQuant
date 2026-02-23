/**
FILE: src\engine\usage.cpp

PURPOSE:
Defines usage.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in usage.cpp.
- File-local helpers supporting the main public or internal entry points.

DATA FLOW:
Callers provide requests or data -> this file applies core logic -> outputs state changes or results.

DEPENDENCIES:
- Internal modules: Neighboring headers under cpp/include and shared utility components.
- External systems: Standard C++ library and optional third-party libs linked by CMake.

DESIGN NOTES:
- Keep behavior deterministic for backtest and unit-test reliability.
- Prefer explicit validation and retcode-based failure signaling.
- Preserve low coupling between domains through typed interfaces.
*/
#include "usage/logger_usage.hpp"

#include "engine/engine.hpp"
#include "util/logger.hpp"

#include <vector>

namespace haruquant::usage {

void run_logger_usage_example() {
    util::info("C++ logger usage example start");

    haruquant::sim::TradeSimulator client;
    haruquant::SymbolInfo symbol;
    symbol.Name("EURUSD");
    symbol.SetPoint(0.00001);
    symbol.SetSpread(10);
    symbol.UpdatePrice(1.10000, 1.10010, 1);
    client.set_symbol_info(symbol);

    haruquant::sim::SymbolTickData tick;
    tick.time = 1;
    tick.time_msc = 1000;
    tick.bid = 1.10000;
    tick.ask = 1.10010;
    tick.last = 1.10000;
    client.set_symbol_tick("EURUSD", tick);

    haruquant::sim::BacktestEngine engine(client);

    std::vector<haruquant::sim::BacktestBarStep> bars;
    haruquant::sim::BacktestBarStep b1;
    b1.time_msc = 60'000;
    b1.close = 1.10000;
    b1.entry_signal = 1;
    bars.push_back(b1);

    haruquant::sim::BacktestBarStep b2;
    b2.time_msc = 120'000;
    b2.close = 1.10020;
    b2.exit_signal = 1;
    bars.push_back(b2);

    engine.run_trading_timeframe("EURUSD", 0.01, bars);

    util::info("C++ logger usage example finish");
}

}  // namespace haruquant::usage



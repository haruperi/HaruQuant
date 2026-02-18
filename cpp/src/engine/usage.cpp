/**
 * @file usage.cpp
 * @brief Unified engine usage compilation unit.
 */

#include "usage/logger_usage.hpp"

#include "engine/engine.hpp"
#include "util/logger.hpp"

#include <vector>

namespace hqt::usage {

void run_logger_usage_example() {
    util::info("C++ logger usage example start");

    hqt::sim::TradeSimulator client;
    hqt::SymbolInfo symbol;
    symbol.Name("EURUSD");
    symbol.SetPoint(0.00001);
    symbol.SetSpread(10);
    symbol.UpdatePrice(1.10000, 1.10010, 1);
    client.set_symbol_info(symbol);

    hqt::sim::SymbolTickData tick;
    tick.time = 1;
    tick.time_msc = 1000;
    tick.bid = 1.10000;
    tick.ask = 1.10010;
    tick.last = 1.10000;
    client.set_symbol_tick("EURUSD", tick);

    hqt::sim::BacktestEngine engine(client);

    std::vector<hqt::sim::BacktestBarStep> bars;
    hqt::sim::BacktestBarStep b1;
    b1.time_msc = 60'000;
    b1.close = 1.10000;
    b1.entry_signal = 1;
    bars.push_back(b1);

    hqt::sim::BacktestBarStep b2;
    b2.time_msc = 120'000;
    b2.close = 1.10020;
    b2.exit_signal = 1;
    bars.push_back(b2);

    engine.run_trading_timeframe("EURUSD", 0.01, bars);

    util::info("C++ logger usage example finish");
}

}  // namespace hqt::usage


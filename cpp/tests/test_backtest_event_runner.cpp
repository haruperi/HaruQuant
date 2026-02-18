/**
 * @file test_backtest_event_runner.cpp
 * @brief Tests for event-driven backtest runner lifecycle callbacks.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <string>
#include <vector>

namespace {

using hqt::sim::BacktestBarStep;
using hqt::sim::BacktestEngine;
using hqt::sim::ModelTick;
using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;

SimulatorClient make_client() {
    SimulatorClient client;

    SymbolInfoData symbol;
    symbol.symbol = "EURUSD";
    symbol.digits = 5;
    symbol.point = 0.00001;
    symbol.spread = 10;
    symbol.volume_min = 0.01;
    symbol.volume_step = 0.01;
    symbol.volume_max = 100.0;
    symbol.trade_contract_size = 100000.0;
    symbol.trade_tick_size = 0.00001;
    symbol.trade_tick_value = 1.0;
    symbol.bid = 1.10000;
    symbol.ask = 1.10010;
    client.set_symbol_info(symbol);
    return client;
}

TEST(BacktestEventRunnerTest, EmitsBarTickAndTradeLifecycleEvents) {
    SimulatorClient client = make_client();
    BacktestEngine engine(client);

    std::size_t bar_events = 0;
    std::size_t tick_events = 0;
    std::vector<std::string> trade_events;

    engine.set_on_bar_processed([&](std::size_t, const BacktestBarStep&, const hqt::sim::SimulatorState&) {
        ++bar_events;
    });
    engine.set_on_tick_processed([&](const ModelTick&, const hqt::sim::SimulatorState&) {
        ++tick_events;
    });
    engine.set_on_trade_event([&](const hqt::sim::BacktestTradeEvent& event, const hqt::sim::SimulatorState&) {
        trade_events.push_back(event.event_type);
    });

    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 1, 0},  // open buy
        {2000, 1.10020, 10.0, 0, 0},
        {3000, 1.10030, 10.0, 0, 1},  // close buy
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    EXPECT_EQ(bar_events, 3U);
    EXPECT_EQ(tick_events, 3U);
    ASSERT_EQ(trade_events.size(), 2U);
    EXPECT_EQ(trade_events[0], "open");
    EXPECT_EQ(trade_events[1], "close");
}

TEST(BacktestEventRunnerTest, TickModeEmitsTickEventsDeterministically) {
    SimulatorClient client = make_client();
    BacktestEngine engine(client);

    std::vector<int64_t> observed_times;
    engine.set_on_tick_processed([&](const ModelTick& tick, const hqt::sim::SimulatorState&) {
        observed_times.push_back(tick.time_msc);
    });

    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 0, 0},
        {2000, 1.10010, 10.0, 0, 0},
    };
    const std::vector<ModelTick> ticks{
        {900, 1.10000, 1.10010, 1.10005},
        {1000, 1.10001, 1.10011, 1.10006},
        {1500, 1.10002, 1.10012, 1.10007},
        {2000, 1.10003, 1.10013, 1.10008},
    };

    engine.run_trading_timeframe_with_ticks("EURUSD", 0.10, bars, ticks);

    ASSERT_EQ(observed_times.size(), ticks.size());
    EXPECT_EQ(observed_times[0], 900);
    EXPECT_EQ(observed_times[1], 1000);
    EXPECT_EQ(observed_times[2], 1500);
    EXPECT_EQ(observed_times[3], 2000);
}

}  // namespace


/**
 * @file test_backtest_vectorized.cpp
 * @brief Tests for C++ vectorized backtest engine.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <vector>

namespace {

using hqt::sim::BacktestBarStep;
using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;
using hqt::sim::VectorizedBacktestEngine;

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

std::vector<BacktestBarStep> sample_bars() {
    return {
        {1000, 1.10000, 10.0, 1, 0},  // open buy
        {2000, 1.10020, 10.0, 0, 0},
        {3000, 1.10030, 10.0, 0, 1},  // close buy
        {4000, 1.10025, 10.0, -1, 0}, // open sell
        {5000, 1.10010, 10.0, 0, -1}  // close sell
    };
}

TEST(VectorizedBacktestTest, RunsAndTracksProcessedBarsAndTrades) {
    SimulatorClient client = make_client();
    VectorizedBacktestEngine engine(client);
    const auto bars = sample_bars();
    engine.run("EURUSD", 0.10, bars);

    EXPECT_EQ(engine.processed_bars(), bars.size());
    EXPECT_GE(engine.total_trades(), 2U);
}

TEST(VectorizedBacktestTest, DeterministicRepeatability) {
    SimulatorClient client1 = make_client();
    SimulatorClient client2 = make_client();
    VectorizedBacktestEngine engine1(client1);
    VectorizedBacktestEngine engine2(client2);
    const auto bars = sample_bars();

    engine1.run("EURUSD", 0.10, bars);
    engine2.run("EURUSD", 0.10, bars);

    EXPECT_EQ(engine1.processed_bars(), engine2.processed_bars());
    EXPECT_EQ(engine1.total_trades(), engine2.total_trades());
    EXPECT_DOUBLE_EQ(engine1.account_snapshot().balance, engine2.account_snapshot().balance);
}

TEST(VectorizedBacktestTest, LargeBatchSmoke) {
    SimulatorClient client = make_client();
    VectorizedBacktestEngine engine(client);

    std::vector<BacktestBarStep> bars;
    bars.reserve(1000);
    for (int i = 0; i < 1000; ++i) {
        BacktestBarStep b;
        b.time_msc = static_cast<int64_t>((i + 1) * 1000);
        b.close = 1.10000 + (static_cast<double>(i % 20) * 0.00001);
        if (i % 200 == 0) {
            b.entry_signal = 1;
        } else if (i % 200 == 100) {
            b.exit_signal = 1;
        }
        bars.push_back(b);
    }

    engine.run("EURUSD", 0.10, bars);
    EXPECT_EQ(engine.processed_bars(), bars.size());
}

}  // namespace


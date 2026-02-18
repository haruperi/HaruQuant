/**
 * @file test_sim_backtest_single_symbol.cpp
 * @brief Tests for single-symbol trading_timeframe backtest engine.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <vector>

namespace {

using hqt::sim::BacktestBarStep;
using hqt::sim::BacktestEngine;
using hqt::sim::TradeSimulator;
using hqt::sim::SymbolInfoData;

class SimBacktestSingleSymbolTest : public ::testing::Test {
protected:
    void SetUp() override {
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
    }

    TradeSimulator client;
    SymbolInfoData symbol;
};

TEST_F(SimBacktestSingleSymbolTest, DeterministicBarCallbackOrder) {
    BacktestEngine engine(client);

    std::vector<int64_t> observed_times;
    std::vector<std::size_t> observed_indices;
    engine.set_on_bar_processed([&](
                                    std::size_t idx,
                                    const BacktestBarStep& bar,
                                    const hqt::sim::SimulatorState& state) {
        observed_indices.push_back(idx);
        observed_times.push_back(bar.time_msc);
        EXPECT_EQ(state.current_bar_index, idx);
        EXPECT_EQ(state.current_time_us, bar.time_msc * 1000);
    });

    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 0, 0},
        {2000, 1.10020, 10.0, 0, 0},
        {3000, 1.10010, 10.0, 0, 0},
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    ASSERT_EQ(observed_indices.size(), 3U);
    EXPECT_EQ(observed_indices[0], 0U);
    EXPECT_EQ(observed_indices[1], 1U);
    EXPECT_EQ(observed_indices[2], 2U);
    EXPECT_EQ(observed_times[0], 1000);
    EXPECT_EQ(observed_times[1], 2000);
    EXPECT_EQ(observed_times[2], 3000);
    EXPECT_EQ(engine.state().processed_events, 3U);
    EXPECT_FALSE(engine.state().running);
}

TEST_F(SimBacktestSingleSymbolTest, SignalSequencingOpensAndClosesPositions) {
    BacktestEngine engine(client);
    std::vector<std::size_t> position_counts;
    engine.set_on_bar_processed([&](
                                    std::size_t,
                                    const BacktestBarStep&,
                                    const hqt::sim::SimulatorState&) {
        position_counts.push_back(client.positions_get().size());
    });

    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 1, 0},   // open buy
        {2000, 1.10040, 10.0, 0, 0},   // hold
        {3000, 1.10030, 10.0, 0, 1},   // close buy
        {4000, 1.10020, 10.0, -1, 0},  // open sell
        {5000, 1.09980, 10.0, 0, -1},  // close sell
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    const auto open_positions = client.positions_get();
    EXPECT_TRUE(open_positions.empty());

    ASSERT_EQ(position_counts.size(), 5U);
    EXPECT_EQ(position_counts[0], 1U);
    EXPECT_EQ(position_counts[1], 1U);
    EXPECT_EQ(position_counts[2], 0U);
    EXPECT_EQ(position_counts[3], 1U);
    EXPECT_EQ(position_counts[4], 0U);

    const auto deals = client.history_deals_get();
    EXPECT_EQ(deals.size(), 2U);  // close events are recorded as deals
}

}  // namespace


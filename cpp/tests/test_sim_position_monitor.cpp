/**
 * @file test_sim_position_monitor.cpp
 * @brief Tests for position/account monitoring in BacktestEngine.
 */

#include <gtest/gtest.h>
#include "sim/backtest_engine.hpp"

#include <optional>
#include <vector>

namespace {

using hqt::sim::AutoCloseReason;
using hqt::sim::BacktestBarStep;
using hqt::sim::BacktestEngine;
using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;

class SimPositionMonitorTest : public ::testing::Test {
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

    SimulatorClient client;
    SymbolInfoData symbol;
};

TEST_F(SimPositionMonitorTest, StopLossAutoCloseTracksReason) {
    BacktestEngine engine(client);
    uint64_t opened_ticket = 0;
    engine.set_on_bar_processed([&](
                                    std::size_t idx,
                                    const BacktestBarStep&,
                                    const hqt::sim::SimulatorState&) {
        if (idx == 0U) {
            const auto positions = client.positions_get();
            ASSERT_EQ(positions.size(), 1U);
            opened_ticket = positions[0].ticket;
        }
    });

    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 1, 0, 1.09900, 1.10150},  // open buy
        {2000, 1.09880, 10.0, 0, 0, 0.0, 0.0},          // hits SL
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    EXPECT_GT(opened_ticket, 0U);
    EXPECT_TRUE(client.positions_get().empty());
    EXPECT_EQ(engine.close_reason(opened_ticket), AutoCloseReason::StopLoss);
}

TEST_F(SimPositionMonitorTest, TakeProfitCloseAndAccountSnapshot) {
    BacktestEngine engine(client);
    uint64_t opened_ticket = 0;
    std::vector<std::size_t> position_counts;
    engine.set_on_bar_processed([&](
                                    std::size_t idx,
                                    const BacktestBarStep&,
                                    const hqt::sim::SimulatorState&) {
        position_counts.push_back(client.positions_get().size());
        if (idx == 0U) {
            const auto positions = client.positions_get();
            ASSERT_EQ(positions.size(), 1U);
            opened_ticket = positions[0].ticket;
        }
    });

    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 1, 0, 1.09900, 1.10100},  // open buy
        {2000, 1.10120, 10.0, 0, 0, 0.0, 0.0},          // hits TP
        {3000, 1.10120, 10.0, 0, 0, 0.0, 0.0},          // no open positions
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    ASSERT_EQ(position_counts.size(), 3U);
    EXPECT_EQ(position_counts[0], 1U);
    EXPECT_EQ(position_counts[1], 0U);
    EXPECT_EQ(position_counts[2], 0U);

    EXPECT_GT(opened_ticket, 0U);
    EXPECT_EQ(engine.close_reason(opened_ticket), AutoCloseReason::TakeProfit);

    const auto& snapshot = engine.account_snapshot();
    EXPECT_DOUBLE_EQ(snapshot.margin, 0.0);
    EXPECT_DOUBLE_EQ(snapshot.profit, 0.0);
    EXPECT_GE(snapshot.equity, snapshot.balance);
}

}  // namespace


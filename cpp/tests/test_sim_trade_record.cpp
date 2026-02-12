/**
 * @file test_sim_trade_record.cpp
 * @brief Tests for trade record tracking in backtest engine.
 */

#include <gtest/gtest.h>
#include "sim/backtest_engine.hpp"

#include <vector>

namespace {

using hqt::sim::BacktestBarStep;
using hqt::sim::BacktestEngine;
using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;

class SimTradeRecordTest : public ::testing::Test {
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

TEST_F(SimTradeRecordTest, TracksMfeMaeBarsTimeAndRMultiple) {
    BacktestEngine engine(client);

    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 1, 0, 1.09900, 0.0},  // open buy
        {2000, 1.10050, 10.0, 0, 0, 0.0, 0.0},      // favorable move
        {3000, 1.09950, 10.0, 0, 0, 0.0, 0.0},      // adverse move
        {4000, 1.10020, 10.0, 0, 1, 0.0, 0.0},      // signal close
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    const auto& completed = engine.completed_trades();
    ASSERT_EQ(completed.size(), 1U);
    const auto& trade = completed.front();

    EXPECT_EQ(trade.symbol, "EURUSD");
    EXPECT_GT(trade.ticket, 0U);
    EXPECT_TRUE(trade.is_buy);
    EXPECT_GT(trade.initial_risk_usd, 0.0);
    EXPECT_GT(trade.mfe_usd, 0.0);
    EXPECT_GT(trade.mae_usd, 0.0);
    EXPECT_EQ(trade.bars_in_trade, 3);
    EXPECT_DOUBLE_EQ(trade.time_in_trade_seconds, 3.0);
    EXPECT_NEAR(trade.r_multiple, trade.profit_loss / trade.initial_risk_usd, 1e-9);
}

}  // namespace


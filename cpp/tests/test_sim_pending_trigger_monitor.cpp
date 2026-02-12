/**
 * @file test_sim_pending_trigger_monitor.cpp
 * @brief Tests for pending trigger/expiry monitoring in BacktestEngine.
 */

#include <gtest/gtest.h>
#include "sim/backtest_engine.hpp"

#include <vector>

namespace {

using hqt::sim::BacktestBarStep;
using hqt::sim::BacktestEngine;
using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;
using hqt::sim::TradeRequest;

class SimPendingTriggerMonitorTest : public ::testing::Test {
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

TEST_F(SimPendingTriggerMonitorTest, TriggeredPendingMovesToFilledHistory) {
    TradeRequest place;
    place.action = 5;       // TRADE_ACTION_PENDING
    place.type = 2;         // BUY_LIMIT
    place.symbol = "EURUSD";
    place.volume = 0.10;
    place.price = 1.09900;
    place.sl = 1.09800;
    place.tp = 1.10050;

    const auto place_result = client.order_send(place);
    ASSERT_EQ(place_result.retcode, 10008);
    const uint64_t order_ticket = place_result.order;

    BacktestEngine engine(client);
    const std::vector<BacktestBarStep> bars{
        {1000, 1.10020, 10.0, 0, 0, 0.0, 0.0},  // no trigger
        {2000, 1.09890, 10.0, 0, 0, 0.0, 0.0},  // ask=1.09900 -> trigger
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    EXPECT_TRUE(client.orders_get(order_ticket).empty());
    const auto positions = client.positions_get();
    ASSERT_EQ(positions.size(), 1U);
    EXPECT_EQ(positions[0].type, 0U);  // BUY

    const auto history = client.history_orders_get(order_ticket);
    ASSERT_EQ(history.size(), 1U);
    EXPECT_EQ(history[0].reason, 4U);  // ORDER_STATE_FILLED
}

TEST_F(SimPendingTriggerMonitorTest, ExpiredPendingMovesToExpiredHistory) {
    TradeRequest place;
    place.action = 5;        // TRADE_ACTION_PENDING
    place.type = 5;          // SELL_STOP
    place.symbol = "EURUSD";
    place.volume = 0.10;
    place.price = 1.09500;
    place.type_time = 2;     // ORDER_TIME_SPECIFIED
    place.expiration = 2;    // seconds

    const auto place_result = client.order_send(place);
    ASSERT_EQ(place_result.retcode, 10008);
    const uint64_t order_ticket = place_result.order;

    BacktestEngine engine(client);
    const std::vector<BacktestBarStep> bars{
        {1000, 1.10000, 10.0, 0, 0, 0.0, 0.0},  // not expired
        {3000, 1.10010, 10.0, 0, 0, 0.0, 0.0},  // now sec=3 -> expired
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);

    EXPECT_TRUE(client.orders_get(order_ticket).empty());
    EXPECT_TRUE(client.positions_get().empty());

    const auto history = client.history_orders_get(order_ticket);
    ASSERT_EQ(history.size(), 1U);
    EXPECT_EQ(history[0].reason, 6U);  // ORDER_STATE_EXPIRED
    EXPECT_EQ(history[0].time, 3);
    EXPECT_EQ(history[0].time_msc, 3000);
}

}  // namespace


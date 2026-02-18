/**
 * @file test_sim_order_send_market.cpp
 * @brief Tests for TradeSimulator order_send market execution.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::TradeSimulator;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRequest;

class SimOrderSendMarketTest : public ::testing::Test {
protected:
    void SetUp() override {
        symbol.symbol = "EURUSD";
        symbol.digits = 5;
        symbol.point = 0.00001;
        symbol.volume_min = 0.01;
        symbol.volume_step = 0.01;
        symbol.volume_max = 100.0;
        symbol.trade_contract_size = 100000.0;
        symbol.trade_tick_size = 0.00001;
        symbol.trade_tick_value = 1.0;
        symbol.bid = 1.10000;
        symbol.ask = 1.10015;

        tick.bid = 1.10000;
        tick.ask = 1.10015;
        tick.last = 1.10000;
        tick.time = 1700000000;
        tick.time_msc = 1700000000000;
    }

    TradeSimulator client;
    SymbolInfoData symbol;
    SymbolTickData tick;
};

TEST_F(SimOrderSendMarketTest, BuyMarketOrderSuccess) {
    client.set_symbol_info(symbol);
    client.set_symbol_tick("EURUSD", tick);

    TradeRequest request;
    request.action = 1;  // TRADE_ACTION_DEAL
    request.type = 0;    // ORDER_TYPE_BUY
    request.symbol = "EURUSD";
    request.volume = 0.10;
    request.comment = "buy test";

    const auto result = client.order_send(request);
    EXPECT_EQ(result.retcode, 10009);
    EXPECT_GT(result.order, 0U);

    const auto positions = client.positions_get();
    ASSERT_EQ(positions.size(), 1U);
    EXPECT_EQ(positions[0].symbol, "EURUSD");
    EXPECT_EQ(positions[0].type, 0U);
    EXPECT_DOUBLE_EQ(positions[0].volume, 0.10);
}

TEST_F(SimOrderSendMarketTest, SellMarketOrderSuccess) {
    client.set_symbol_info(symbol);
    client.set_symbol_tick("EURUSD", tick);

    TradeRequest request;
    request.action = 1;  // TRADE_ACTION_DEAL
    request.type = 1;    // ORDER_TYPE_SELL
    request.symbol = "EURUSD";
    request.volume = 0.20;
    request.comment = "sell test";

    const auto result = client.order_send(request);
    EXPECT_EQ(result.retcode, 10009);
    EXPECT_GT(result.order, 0U);

    const auto positions = client.positions_get();
    ASSERT_EQ(positions.size(), 1U);
    EXPECT_EQ(positions[0].symbol, "EURUSD");
    EXPECT_EQ(positions[0].type, 1U);
    EXPECT_DOUBLE_EQ(positions[0].volume, 0.20);
}

TEST_F(SimOrderSendMarketTest, InvalidRequestRetcodes) {
    client.set_symbol_info(symbol);
    client.set_symbol_tick("EURUSD", tick);

    TradeRequest bad_action;
    bad_action.action = 0;
    bad_action.type = 0;
    bad_action.symbol = "EURUSD";
    bad_action.volume = 0.1;
    EXPECT_EQ(client.order_send(bad_action).retcode, 10013);

    TradeRequest bad_volume;
    bad_volume.action = 1;
    bad_volume.type = 0;
    bad_volume.symbol = "EURUSD";
    bad_volume.volume = 0.0;
    EXPECT_EQ(client.order_send(bad_volume).retcode, 10014);

    TradeRequest bad_symbol;
    bad_symbol.action = 1;
    bad_symbol.type = 0;
    bad_symbol.symbol = "UNKNOWN";
    bad_symbol.volume = 0.1;
    EXPECT_EQ(client.order_send(bad_symbol).retcode, 10021);
}

}  // namespace



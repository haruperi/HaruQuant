/**
 * @file test_sim_pending_orders.cpp
 * @brief Tests for pending order lifecycle via SimulatorClient order_send.
 */

#include <gtest/gtest.h>
#include "sim/simulator_client.hpp"

namespace {

using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRequest;

class SimPendingOrdersTest : public ::testing::Test {
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

        client.set_symbol_info(symbol);
        client.set_symbol_tick("EURUSD", tick);
    }

    SimulatorClient client;
    SymbolInfoData symbol;
    SymbolTickData tick;
};

TEST_F(SimPendingOrdersTest, PlaceModifyDeletePendingOrderLifecycle) {
    TradeRequest place;
    place.action = 5;  // TRADE_ACTION_PENDING
    place.type = 2;    // BUY_LIMIT
    place.symbol = "EURUSD";
    place.volume = 0.10;
    place.price = 1.09500;
    place.sl = 1.09000;
    place.tp = 1.10500;
    place.comment = "pending test";

    const auto place_result = client.order_send(place);
    EXPECT_EQ(place_result.retcode, 10008);
    EXPECT_GT(place_result.order, 0U);

    const uint64_t order_ticket = place_result.order;
    auto active_orders = client.orders_get(order_ticket);
    ASSERT_EQ(active_orders.size(), 1U);
    EXPECT_EQ(active_orders[0].symbol, "EURUSD");
    EXPECT_DOUBLE_EQ(active_orders[0].price_open, 1.09500);
    EXPECT_DOUBLE_EQ(active_orders[0].sl, 1.09000);
    EXPECT_DOUBLE_EQ(active_orders[0].tp, 1.10500);

    TradeRequest modify;
    modify.action = 7;  // TRADE_ACTION_MODIFY
    modify.order = order_ticket;
    modify.price = 1.09400;
    modify.sl = 1.08900;
    modify.tp = 1.10600;

    const auto mod_result = client.order_send(modify);
    EXPECT_EQ(mod_result.retcode, 10009);

    active_orders = client.orders_get(order_ticket);
    ASSERT_EQ(active_orders.size(), 1U);
    EXPECT_DOUBLE_EQ(active_orders[0].price_open, 1.09400);
    EXPECT_DOUBLE_EQ(active_orders[0].sl, 1.08900);
    EXPECT_DOUBLE_EQ(active_orders[0].tp, 1.10600);

    TradeRequest remove;
    remove.action = 8;  // TRADE_ACTION_REMOVE
    remove.order = order_ticket;

    const auto del_result = client.order_send(remove);
    EXPECT_EQ(del_result.retcode, 10009);

    active_orders = client.orders_get(order_ticket);
    EXPECT_TRUE(active_orders.empty());

    const auto hist_orders = client.history_orders_get(order_ticket);
    ASSERT_EQ(hist_orders.size(), 1U);
    EXPECT_EQ(hist_orders[0].ticket, order_ticket);
    EXPECT_EQ(hist_orders[0].reason, 2U);  // ORDER_STATE_CANCELED
}

TEST_F(SimPendingOrdersTest, InvalidModifyAndDeleteRetcodes) {
    TradeRequest modify;
    modify.action = 7;
    modify.order = 999999;
    EXPECT_EQ(client.order_send(modify).retcode, 10035);

    TradeRequest remove;
    remove.action = 8;
    remove.order = 999999;
    EXPECT_EQ(client.order_send(remove).retcode, 10035);
}

}  // namespace


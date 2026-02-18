/**
 * @file test_sim_oms_state_machine.cpp
 * @brief Tests for OMS state transitions and idempotent submissions.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::OmsOrderState;
using hqt::sim::TradeSimulator;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRequest;

class SimOmsStateMachineTest : public ::testing::Test {
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

        tick.bid = 1.10000;
        tick.ask = 1.10010;
        tick.last = 1.10000;
        tick.time = 1700000000;
        tick.time_msc = 1700000000000;
        client.set_symbol_tick("EURUSD", tick);
    }

    TradeSimulator client;
    SymbolInfoData symbol;
    SymbolTickData tick;
};

TEST_F(SimOmsStateMachineTest, IdempotentSubmissionReturnsCachedResult) {
    TradeRequest req;
    req.action = 1;  // TRADE_ACTION_DEAL
    req.type = 0;    // BUY
    req.symbol = "EURUSD";
    req.volume = 0.10;
    req.client_order_id = "client-001";

    const auto first = client.order_send(req);
    ASSERT_EQ(first.retcode, 10009);
    ASSERT_GT(first.order, 0U);

    const auto second = client.order_send(req);
    EXPECT_EQ(second.retcode, first.retcode);
    EXPECT_EQ(second.order, first.order);
    EXPECT_EQ(client.idempotency_cache_size(), 1U);

    const auto positions = client.positions_get();
    EXPECT_EQ(positions.size(), 1U);
}

TEST_F(SimOmsStateMachineTest, DuplicateClientOrderIdDifferentPayloadRejected) {
    TradeRequest req;
    req.action = 5;  // TRADE_ACTION_PENDING
    req.type = 2;    // BUY_LIMIT
    req.symbol = "EURUSD";
    req.volume = 0.10;
    req.price = 1.09900;
    req.client_order_id = "client-dup";

    const auto first = client.order_send(req);
    ASSERT_EQ(first.retcode, 10008);

    TradeRequest changed = req;
    changed.price = 1.09850;
    const auto second = client.order_send(changed);
    EXPECT_EQ(second.retcode, 10013);
}

TEST_F(SimOmsStateMachineTest, MarketOrderTransitionsToFilled) {
    TradeRequest req;
    req.action = 1;  // TRADE_ACTION_DEAL
    req.type = 0;    // BUY
    req.symbol = "EURUSD";
    req.volume = 0.10;

    const auto result = client.order_send(req);
    ASSERT_EQ(result.retcode, 10009);
    ASSERT_GT(result.order, 0U);
    EXPECT_EQ(client.order_state(result.order), OmsOrderState::Filled);
    EXPECT_EQ(client.order_state_name(result.order), "FILLED");
}

TEST_F(SimOmsStateMachineTest, PendingOrderCancelTransitionsToCanceled) {
    TradeRequest place;
    place.action = 5;  // TRADE_ACTION_PENDING
    place.type = 2;    // BUY_LIMIT
    place.symbol = "EURUSD";
    place.volume = 0.10;
    place.price = 1.09500;

    const auto place_result = client.order_send(place);
    ASSERT_EQ(place_result.retcode, 10008);
    ASSERT_GT(place_result.order, 0U);
    EXPECT_EQ(client.order_state_name(place_result.order), "ACCEPTED");

    TradeRequest remove;
    remove.action = 8;  // TRADE_ACTION_REMOVE
    remove.order = place_result.order;
    const auto remove_result = client.order_send(remove);
    ASSERT_EQ(remove_result.retcode, 10009);
    EXPECT_EQ(client.order_state_name(place_result.order), "CANCELED");
}

TEST_F(SimOmsStateMachineTest, PendingOrderCanBeMarkedExpired) {
    TradeRequest place;
    place.action = 5;  // TRADE_ACTION_PENDING
    place.type = 5;    // SELL_STOP
    place.symbol = "EURUSD";
    place.volume = 0.10;
    place.price = 1.09500;

    const auto place_result = client.order_send(place);
    ASSERT_EQ(place_result.retcode, 10008);
    ASSERT_GT(place_result.order, 0U);

    ASSERT_TRUE(client.set_history_order_state(place_result.order, 6U));  // ORDER_STATE_EXPIRED
    EXPECT_EQ(client.order_state_name(place_result.order), "EXPIRED");
}

}  // namespace



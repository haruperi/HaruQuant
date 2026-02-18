/**
 * @file test_simulator_client_getters.cpp
 * @brief Tests for TradeSimulator getter API.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::TradeSimulator;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRecordData;

TEST(TradeSimulatorGettersTest, AccountInfoAndLastErrorDefaults) {
    TradeSimulator client;

    const auto& account = client.account_info();
    EXPECT_DOUBLE_EQ(account.balance, 10000.0);
    EXPECT_EQ(account.currency, "USD");

    const auto [code, message] = client.last_error();
    EXPECT_EQ(code, 1);
    EXPECT_EQ(message, "Success");
}

TEST(TradeSimulatorGettersTest, SymbolInfoAndTickLookup) {
    TradeSimulator client;

    SymbolInfoData symbol;
    symbol.symbol = "EURUSD";
    symbol.digits = 5;
    client.set_symbol_info(symbol);

    SymbolTickData tick;
    tick.bid = 1.1000;
    tick.ask = 1.1002;
    client.set_symbol_tick("EURUSD", tick);

    const auto* info = client.symbol_info("EURUSD");
    ASSERT_NE(info, nullptr);
    EXPECT_EQ(info->symbol, "EURUSD");
    EXPECT_EQ(info->digits, 5);

    const auto* sym_tick = client.symbol_info_tick("EURUSD");
    ASSERT_NE(sym_tick, nullptr);
    EXPECT_DOUBLE_EQ(sym_tick->bid, 1.1000);
    EXPECT_DOUBLE_EQ(sym_tick->ask, 1.1002);

    EXPECT_EQ(client.symbol_info("GBPUSD"), nullptr);
    EXPECT_EQ(client.symbol_info_tick("GBPUSD"), nullptr);
}

TEST(TradeSimulatorGettersTest, EmptyContainersReturnEmptyVectors) {
    TradeSimulator client;

    EXPECT_TRUE(client.positions_get().empty());
    EXPECT_TRUE(client.orders_get().empty());
    EXPECT_TRUE(client.history_orders_get().empty());
    EXPECT_TRUE(client.history_deals_get().empty());
}

TEST(TradeSimulatorGettersTest, PositionsFilterByTicketAndSymbol) {
    TradeSimulator client;

    TradeRecordData eurusd;
    eurusd.ticket = 10;
    eurusd.symbol = "EURUSD";
    client.upsert_position(eurusd);

    TradeRecordData gbpusd;
    gbpusd.ticket = 20;
    gbpusd.symbol = "GBPUSD";
    client.upsert_position(gbpusd);

    auto all = client.positions_get();
    EXPECT_EQ(all.size(), 2U);

    auto by_ticket = client.positions_get(10);
    ASSERT_EQ(by_ticket.size(), 1U);
    EXPECT_EQ(by_ticket[0].symbol, "EURUSD");

    auto by_symbol = client.positions_get(std::nullopt, "GBPUSD");
    ASSERT_EQ(by_symbol.size(), 1U);
    EXPECT_EQ(by_symbol[0].ticket, 20U);

    auto no_match = client.positions_get(999);
    EXPECT_TRUE(no_match.empty());
}

TEST(TradeSimulatorGettersTest, OrdersFilterByTicketAndSymbol) {
    TradeSimulator client;

    TradeRecordData a;
    a.ticket = 101;
    a.symbol = "EURUSD";
    client.upsert_order(a);

    TradeRecordData b;
    b.ticket = 202;
    b.symbol = "USDJPY";
    client.upsert_order(b);

    auto by_ticket = client.orders_get(202);
    ASSERT_EQ(by_ticket.size(), 1U);
    EXPECT_EQ(by_ticket[0].symbol, "USDJPY");

    auto by_symbol = client.orders_get(std::nullopt, "EURUSD");
    ASSERT_EQ(by_symbol.size(), 1U);
    EXPECT_EQ(by_symbol[0].ticket, 101U);
}

}  // namespace



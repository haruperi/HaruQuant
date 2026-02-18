/**
 * @file test_position_book.cpp
 * @brief Tests for PositionBook and reconciliation hooks.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::AccountInfoData;
using hqt::sim::FillEvent;
using hqt::sim::PositionBook;
using hqt::sim::PositionMode;

TEST(PositionBookTest, NettingModeMaintainsSingleNetPositionPerSymbol) {
    PositionBook book(PositionMode::Netting);

    FillEvent buy;
    buy.symbol = "EURUSD";
    buy.is_buy = true;
    buy.volume = 1.0;
    buy.price = 1.1000;
    book.apply_fill(buy);

    FillEvent sell_partial;
    sell_partial.symbol = "EURUSD";
    sell_partial.is_buy = false;
    sell_partial.volume = 0.4;
    sell_partial.price = 1.1010;
    book.apply_fill(sell_partial);

    const auto positions = book.snapshot_positions();
    ASSERT_EQ(positions.size(), 1U);
    const auto it = positions.find("EURUSD");
    ASSERT_NE(it, positions.end());
    EXPECT_DOUBLE_EQ(it->second.net_volume, 0.6);
    EXPECT_DOUBLE_EQ(it->second.long_volume, 0.6);
    EXPECT_DOUBLE_EQ(it->second.short_volume, 0.0);
}

TEST(PositionBookTest, HedgingModeMaintainsMultipleLegs) {
    PositionBook book(PositionMode::Hedging);

    FillEvent buy;
    buy.symbol = "EURUSD";
    buy.is_buy = true;
    buy.volume = 1.0;
    buy.price = 1.1000;
    book.apply_fill(buy);

    FillEvent sell;
    sell.symbol = "EURUSD";
    sell.is_buy = false;
    sell.volume = 0.7;
    sell.price = 1.1005;
    book.apply_fill(sell);

    const auto legs = book.legs_for_symbol("EURUSD");
    ASSERT_EQ(legs.size(), 2U);
    EXPECT_TRUE(legs[0].is_buy);
    EXPECT_FALSE(legs[1].is_buy);

    const auto positions = book.snapshot_positions();
    const auto it = positions.find("EURUSD");
    ASSERT_NE(it, positions.end());
    EXPECT_DOUBLE_EQ(it->second.long_volume, 1.0);
    EXPECT_DOUBLE_EQ(it->second.short_volume, 0.7);
    EXPECT_DOUBLE_EQ(it->second.net_volume, 0.3);
}

TEST(PositionBookTest, PeriodicAndReconnectHooksReturnReportMetadata) {
    PositionBook book(PositionMode::Netting);

    FillEvent buy;
    buy.symbol = "EURUSD";
    buy.is_buy = true;
    buy.volume = 1.0;
    buy.price = 1.1000;
    book.apply_fill(buy);

    AccountInfoData account;
    account.balance = 10000.0;
    account.equity = 10000.0;
    account.margin = 0.0;
    book.apply_account_snapshot(account);

    auto broker_positions = book.snapshot_positions();
    AccountInfoData broker_account = book.snapshot_account();

    const auto periodic = book.periodic_reconcile(broker_positions, broker_account);
    EXPECT_TRUE(periodic.ok);
    EXPECT_EQ(periodic.trigger, "periodic");
    EXPECT_EQ(periodic.position_mismatch_count, 0U);
    EXPECT_EQ(periodic.account_mismatch_count, 0U);

    broker_positions["EURUSD"].net_volume = 0.5;  // force mismatch
    const auto reconnect = book.reconnect_reconcile(broker_positions, broker_account);
    EXPECT_FALSE(reconnect.ok);
    EXPECT_EQ(reconnect.trigger, "reconnect");
    EXPECT_GT(reconnect.position_mismatch_count, 0U);
    EXPECT_FALSE(reconnect.issues.empty());
}

}  // namespace


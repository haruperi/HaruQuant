/**
 * @file test_sim_data.cpp
 * @brief Tests for simulation DTOs.
 */

#include <gtest/gtest.h>
#include "sim/sim_data.hpp"

namespace {

using hqt::sim::AccountInfoData;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRecordData;

TEST(SimDataTest, AccountInfoDefaults) {
    AccountInfoData data;

    EXPECT_EQ(data.login, 12345678);
    EXPECT_EQ(data.leverage, 100);
    EXPECT_DOUBLE_EQ(data.balance, 10000.0);
    EXPECT_EQ(data.currency, "USD");
    EXPECT_TRUE(data.trade_allowed);
}

TEST(SimDataTest, AccountInfoToDictMapping) {
    AccountInfoData data;
    auto dict = data.to_dict();

    EXPECT_EQ(dict.at("login"), "12345678");
    EXPECT_EQ(dict.at("leverage"), "100");
    EXPECT_EQ(dict.at("currency"), "USD");
    EXPECT_EQ(dict.at("trade_allowed"), "true");
}

TEST(SimDataTest, SymbolTickDefaults) {
    SymbolTickData tick;

    EXPECT_EQ(tick.time, 0);
    EXPECT_DOUBLE_EQ(tick.bid, 0.0);
    EXPECT_DOUBLE_EQ(tick.ask, 0.0);
    EXPECT_EQ(tick.volume, 0);
}

TEST(SimDataTest, SymbolInfoDefaults) {
    SymbolInfoData info;

    EXPECT_EQ(info.symbol, "EURUSD");
    EXPECT_EQ(info.digits, 5);
    EXPECT_DOUBLE_EQ(info.point, 0.00001);
    EXPECT_DOUBLE_EQ(info.volume_min, 0.01);
    EXPECT_DOUBLE_EQ(info.volume_step, 0.01);
    EXPECT_DOUBLE_EQ(info.volume_max, 100.0);
}

TEST(SimDataTest, SymbolInfoToDictMapping) {
    SymbolInfoData info;
    auto dict = info.to_dict();

    EXPECT_EQ(dict.at("symbol"), "EURUSD");
    EXPECT_EQ(dict.at("digits"), "5");
    EXPECT_EQ(dict.at("spread_float"), "true");
    EXPECT_EQ(dict.at("volume_min"), "0.01");
}

TEST(SimDataTest, TradeRecordToDictMapping) {
    TradeRecordData rec;
    rec.ticket = 42;
    rec.symbol = "EURUSD";
    rec.volume = 0.1;
    rec.comment = "test";

    auto dict = rec.to_dict();

    EXPECT_EQ(dict.at("ticket"), "42");
    EXPECT_EQ(dict.at("symbol"), "EURUSD");
    EXPECT_EQ(dict.at("volume"), "0.1");
    EXPECT_EQ(dict.at("comment"), "test");
}

}  // namespace


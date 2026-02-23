#include "core/state.hpp"
#include "trading/trade.hpp"
#include <gtest/gtest.h>


using namespace haruquant::core;
using namespace haruquant::trading;

class WrapperTradeTest : public ::testing::Test {
protected:
  BacktestState state;
  Trade *trade;

  void SetUp() override { trade = new Trade(&state); }

  void TearDown() override { delete trade; }
};

TEST_F(WrapperTradeTest, BuyCreatesOrderRequest) {
  trade->RequestMagic(123);
  EXPECT_TRUE(trade->Buy(0.5, "EURUSD", 1.1000, 1.0950, 1.1050, "Test"));

  EXPECT_EQ(trade->ResultRetcode(), 10009); // DONE

  // In our placeholder implementation, PositionOpen populates
  // state.trading_orders
  bool found = false;
  for (const auto &kv : state.trading_orders) {
    if (kv.second.at("symbol") == "EURUSD" &&
        kv.second.at("action") == "position_open") {
      found = true;
      EXPECT_EQ(kv.second.at("volume"),
                "0.500000"); // std::to_string default formatting
      break;
    }
  }
  EXPECT_TRUE(found);
}

TEST_F(WrapperTradeTest, ValidatesNullState) {
  Trade null_trade(nullptr);
  EXPECT_FALSE(null_trade.Buy(0.1, "GBPUSD"));
  EXPECT_EQ(null_trade.ResultRetcode(), 10013); // INVALID
}

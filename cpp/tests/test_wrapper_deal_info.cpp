#include "core/state.hpp"
#include "trading/deal_info.hpp"
#include <gtest/gtest.h>


using namespace haruquant::core;
using namespace haruquant::trading;

class DealInfoTest : public ::testing::Test {
protected:
  BacktestState state;
  DealInfo *deal;

  void SetUp() override {
    state.trading_deals["2001"]["ticket"] = "2001";
    state.trading_deals["2001"]["order"] = "1001";
    state.trading_deals["2001"]["symbol"] = "USDJPY";
    state.trading_deals["2001"]["type"] = "0"; // Buy
    state.trading_deals["2001"]["volume"] = "0.5";
    state.trading_deals["2001"]["price"] = "150.250";
    state.trading_deals["2001"]["commission"] = "-2.50";

    deal = new DealInfo(&state);
  }

  void TearDown() override { delete deal; }
};

TEST_F(DealInfoTest, SelectsValidDeal) {
  EXPECT_TRUE(deal->Ticket(2001));
  EXPECT_EQ(deal->Ticket(), 2001);
  EXPECT_EQ(deal->Order(), 1001);
  EXPECT_EQ(deal->Symbol(), "USDJPY");
  EXPECT_EQ(deal->Type(), 0);
  EXPECT_DOUBLE_EQ(deal->Volume(), 0.5);
  EXPECT_DOUBLE_EQ(deal->Price(), 150.250);
  EXPECT_DOUBLE_EQ(deal->Commission(), -2.50);
}

TEST_F(DealInfoTest, FailsToSelectInvalidDeal) {
  EXPECT_FALSE(deal->Ticket(9999));
}

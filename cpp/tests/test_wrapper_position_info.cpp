#include "core/state.hpp"
#include "trading/position_info.hpp"
#include <gtest/gtest.h>
#include <memory>


using namespace haruquant::core;
using namespace haruquant::trading;

class PositionInfoTest : public ::testing::Test {
protected:
  std::shared_ptr<BacktestState> state;
  PositionInfo *position;

  void SetUp() override {
    state = std::make_shared<BacktestState>();
    state->trading_deals["8001"]["ticket"] = "8001";
    state->trading_deals["8001"]["symbol"] = "ETHUSD";
    state->trading_deals["8001"]["entry"] = "0";
    state->trading_deals["8001"]["type"] = "1"; // Sell
    state->trading_deals["8001"]["volume"] = "5.5";
    state->trading_deals["8001"]["price_open"] = "2000.50";
    state->trading_deals["8001"]["profit"] = "150.25";

    position = new PositionInfo(state);
  }

  void TearDown() override { delete position; }
};

TEST_F(PositionInfoTest, SelectBySymbolValid) {
  EXPECT_TRUE(position->Select("ETHUSD"));
  EXPECT_EQ(position->Ticket(), 8001);
  EXPECT_EQ(position->Symbol(), "ETHUSD");
  EXPECT_EQ(position->Type(), 1);
  EXPECT_DOUBLE_EQ(position->Volume(), 5.5);
  EXPECT_DOUBLE_EQ(position->PriceOpen(), 2000.50);
  EXPECT_DOUBLE_EQ(position->Profit(), 150.25);
}

TEST_F(PositionInfoTest, SelectBySymbolInvalid) {
  EXPECT_FALSE(position->Select("BTCUSD"));
}

TEST_F(PositionInfoTest, SelectByTicketValid) {
  EXPECT_TRUE(position->SelectByTicket(8001));
  EXPECT_EQ(position->Symbol(), "ETHUSD");
}

TEST_F(PositionInfoTest, SelectByTicketInvalid) {
  EXPECT_FALSE(position->SelectByTicket(9999));
}

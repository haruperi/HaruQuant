#include "core/state.hpp"
#include "trading/history_order_info.hpp"
#include <gtest/gtest.h>
#include <memory>


using namespace haruquant::core;
using namespace haruquant::trading;

class HistoryOrderInfoTest : public ::testing::Test {
protected:
  std::shared_ptr<BacktestState> state;
  HistoryOrderInfo *order;

  void SetUp() override {
    state = std::make_shared<BacktestState>();
    state->trading_history_orders["5001"]["ticket"] = "5001";
    state->trading_history_orders["5001"]["symbol"] = "USDJPY";
    state->trading_history_orders["5001"]["state"] = "4"; // Filled
    state->trading_history_orders["5001"]["volume_initial"] = "2.0";
    state->trading_history_orders["5001"]["time_done"] = "1620000000";

    order = new HistoryOrderInfo(state);
  }

  void TearDown() override { delete order; }
};

TEST_F(HistoryOrderInfoTest, FailsToSelectInvalidOrder) {
  EXPECT_FALSE(order->Ticket(9999)); // Uses Ticket() method for select
}

TEST_F(HistoryOrderInfoTest, SelectsValidOrder) {
  EXPECT_TRUE(order->Ticket(5001));
  EXPECT_EQ(order->Ticket(), 5001);
  EXPECT_EQ(order->Symbol(), "USDJPY");
  EXPECT_EQ(order->State(), 4);
  EXPECT_DOUBLE_EQ(order->VolumeInitial(), 2.0);
  EXPECT_EQ(order->TimeDone(), 1620000000);
}

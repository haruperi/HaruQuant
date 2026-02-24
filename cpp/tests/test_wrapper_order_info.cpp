#include "core/state.hpp"
#include "trading/order_info.hpp"
#include <gtest/gtest.h>
#include <memory>


using namespace haruquant::core;
using namespace haruquant::trading;

class OrderInfoTest : public ::testing::Test {
protected:
  std::shared_ptr<BacktestState> state;
  OrderInfo *order;

  void SetUp() override {
    state = std::make_shared<BacktestState>();
    state->trading_orders["1001"]["ticket"] = "1001";
    state->trading_orders["1001"]["symbol"] = "EURUSD";
    state->trading_orders["1001"]["type"] = "0"; // Buy
    state->trading_orders["1001"]["volume_initial"] = "1.5";
    state->trading_orders["1001"]["price_open"] = "1.08500";

    state->trading_orders["1002"]["ticket"] = "1002";
    state->trading_orders["1002"]["symbol"] = "GBPUSD";

    order = new OrderInfo(state);
  }

  void TearDown() override { delete order; }
};

TEST_F(OrderInfoTest, FailsToSelectInvalidOrder) {
  EXPECT_FALSE(order->Select(9999));
}

TEST_F(OrderInfoTest, SelectsValidOrder) {
  EXPECT_TRUE(order->Select(1001));
  EXPECT_EQ(order->Ticket(), 1001);
  EXPECT_EQ(order->Symbol(), "EURUSD");
  EXPECT_EQ(order->Type(), 0);
  EXPECT_DOUBLE_EQ(order->VolumeInitial(), 1.5);
  EXPECT_DOUBLE_EQ(order->PriceOpen(), 1.08500);
}

TEST_F(OrderInfoTest, ReadPropertiesFromAnotherOrder) {
  EXPECT_TRUE(order->Select(1002));
  EXPECT_EQ(order->Ticket(), 1002);
  EXPECT_EQ(order->Symbol(), "GBPUSD");
}

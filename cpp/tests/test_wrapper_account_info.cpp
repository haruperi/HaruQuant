#include "core/state.hpp"
#include "trading/account_info.hpp"
#include <gtest/gtest.h>


using namespace haruquant::core;
using namespace haruquant::trading;

class AccountInfoTest : public ::testing::Test {
protected:
  BacktestState state;
  AccountInfo *account;

  void SetUp() override {
    // Setup state
    state.trading_account["login"] = "123456";
    state.trading_account["trade_mode"] = "0"; // ACCOUNT_TRADE_MODE_DEMO
    state.trading_account["leverage"] = "100";
    state.trading_account["balance"] = "10000.50";
    state.trading_account["currency"] = "USD";
    state.trading_account["name"] = "Test User";

    account = new AccountInfo(&state);
  }

  void TearDown() override { delete account; }
};

TEST_F(AccountInfoTest, IntegerPropertiesReadCorrectly) {
  EXPECT_EQ(account->Login(), 123456);
  EXPECT_EQ(account->TradeMode(), 0);
  EXPECT_EQ(account->Leverage(), 100);
}

TEST_F(AccountInfoTest, DoublePropertiesReadCorrectly) {
  EXPECT_DOUBLE_EQ(account->Balance(), 10000.50);
}

TEST_F(AccountInfoTest, StringPropertiesReadCorrectly) {
  EXPECT_EQ(account->Currency(), "USD");
  EXPECT_EQ(account->Name(), "Test User");
}

TEST_F(AccountInfoTest, MissingPropertiesDefaultToZeroOrEmpty) {
  EXPECT_EQ(account->LimitOrders(), 0);
  EXPECT_DOUBLE_EQ(account->Credit(), 0.0);
  EXPECT_EQ(account->Company(), "");
}

TEST_F(AccountInfoTest, NullStateHandledGracefully) {
  AccountInfo null_account(nullptr);
  EXPECT_EQ(null_account.Login(), 0);
  EXPECT_DOUBLE_EQ(null_account.Balance(), 0.0);
  EXPECT_EQ(null_account.Currency(), "");
}

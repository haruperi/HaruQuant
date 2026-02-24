#include "core/state.hpp"
#include "trading/terminal_info.hpp"
#include <gtest/gtest.h>
#include <memory>


using namespace haruquant::core;
using namespace haruquant::trading;

class TerminalInfoTest : public ::testing::Test {
protected:
  std::shared_ptr<BacktestState> state;
  TerminalInfo *terminal;

  void SetUp() override {
    state = std::make_shared<BacktestState>();
    state->terminal_info["build"] = "4000";
    state->terminal_info["connected"] = "1";
    state->terminal_info["trade_allowed"] = "1";
    state->terminal_info["ping_last"] = "25";
    state->terminal_info["company"] = "MetaQuotes Software Corp.";

    terminal = new TerminalInfo(state);
  }

  void TearDown() override { delete terminal; }
};

TEST_F(TerminalInfoTest, IntegerPropertiesReadCorrectly) {
  EXPECT_EQ(terminal->Build(), 4000);
  EXPECT_EQ(terminal->Connected(), 1);
  EXPECT_EQ(terminal->TradeAllowed(), 1);
  EXPECT_EQ(terminal->PingLast(), 25);
}

TEST_F(TerminalInfoTest, StringPropertiesReadCorrectly) {
  EXPECT_EQ(terminal->Company(), "MetaQuotes Software Corp.");
}

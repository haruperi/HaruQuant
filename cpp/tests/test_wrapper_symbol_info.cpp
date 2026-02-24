#include "core/state.hpp"
#include "trading/symbol_info.hpp"
#include <gtest/gtest.h>
#include <memory>


using namespace haruquant::core;
using namespace haruquant::trading;

class SymbolInfoTest : public ::testing::Test {
protected:
  std::shared_ptr<BacktestState> state;
  SymbolInfo *symbol;

  void SetUp() override {
    state = std::make_shared<BacktestState>();
    state->trading_symbols["EURUSD"]["ask"] = "1.08500";
    state->trading_symbols["EURUSD"]["bid"] = "1.08490";
    state->trading_symbols["EURUSD"]["digits"] = "5";
    state->trading_symbols["EURUSD"]["spread"] = "10";
    state->trading_symbols["EURUSD"]["description"] = "Euro vs US Dollar";

    symbol = new SymbolInfo(state);
  }

  void TearDown() override { delete symbol; }
};

TEST_F(SymbolInfoTest, FailsWithoutSelectingName) {
  EXPECT_EQ(symbol->Name(), "");
  EXPECT_DOUBLE_EQ(symbol->Ask(), 0.0);
}

TEST_F(SymbolInfoTest, ReadsPropertiesCorrectlyAfterSelect) {
  symbol->Name("EURUSD");
  EXPECT_EQ(symbol->Name(), "EURUSD");
  EXPECT_DOUBLE_EQ(symbol->Ask(), 1.08500);
  EXPECT_DOUBLE_EQ(symbol->Bid(), 1.08490);
  EXPECT_EQ(symbol->Digits(), 5);
  EXPECT_EQ(symbol->Spread(), 10);
  EXPECT_EQ(symbol->Description(), "Euro vs US Dollar");
}

TEST_F(SymbolInfoTest, MissingPropertiesAreZeroEmpty) {
  symbol->Name("EURUSD");
  EXPECT_DOUBLE_EQ(symbol->MarginInitial(), 0.0);
  EXPECT_EQ(symbol->Page(), "");
}

TEST_F(SymbolInfoTest, NormalizePriceMethod) {
  symbol->Name("EURUSD");
  // With 5 digits, 1.085004 -> 1.08500, 1.085006 -> 1.08501
  EXPECT_DOUBLE_EQ(symbol->NormalizePrice(1.085004), 1.08500);
  EXPECT_DOUBLE_EQ(symbol->NormalizePrice(1.085006), 1.08501);
}

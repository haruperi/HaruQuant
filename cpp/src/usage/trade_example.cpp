#include "core/state.hpp"
#include "trading/trade.hpp"
#include <iostream>
#include <memory>

void demonstrate_trade() {
  // Setup your Backtest Engine State
  auto state = std::make_shared<haruquant::core::BacktestState>();

  // Initialize Trade wrapper
  haruquant::trading::Trade trade(state);

  // Configure trade request settings globally
  trade.SetExpertMagicNumber(123456);
  trade.SetDeviationInPoints(10.0);
  trade.LogLevel(1); // LOG_LEVEL_ERRORS

  bool success = trade.PositionOpen("EURUSD", 0, 0.1, 1.0850, 1.0800, 1.0900,
                                    "Moving Average Strategy");

  if (success) {
    std::cout << "Order placed successfully! Retcode: "
              << trade.ResultRetcodeDescription() << "\n";
  } else {
    std::cout << "Order failed... Retcode: " << trade.ResultRetcode() << "\n";
  }
}

int main() {
  demonstrate_trade();
  return 0;
}


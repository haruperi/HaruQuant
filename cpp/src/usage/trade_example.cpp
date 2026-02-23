#include "core/state.hpp"
#include "trading/trade.hpp"
#include <iostream>

void demonstrate_trade() {
  // Setup your Backtest Engine State
  haruquant::core::BacktestState state;

  // Initialize Trade wrapper
  haruquant::trading::Trade trade(&state);

  // Configure trade requests globally
  trade.RequestMagic(123456);
  trade.RequestDeviation(10.0);
  trade.LogLevel(1); // LOG_LEVEL_ERRORS

  // Issue a Buy Order
  bool success = trade.Buy(0.1, "EURUSD", 1.0850, 1.0800, 1.0900,
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

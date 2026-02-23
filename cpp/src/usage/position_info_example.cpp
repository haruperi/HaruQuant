#include "core/state.hpp"
#include "trading/position_info.hpp"
#include <iostream>

void demonstrate_position_info() {
  haruquant::core::BacktestState state;

  // Simulate an open position present in the state
  std::string test_symbol = "ETHUSD";
  state.trading_positions[test_symbol]["ticket"] = "80001";
  state.trading_positions[test_symbol]["symbol"] = "ETHUSD";
  state.trading_positions[test_symbol]["type"] =
      "1"; // e.g., POSITION_TYPE_SELL
  state.trading_positions[test_symbol]["volume"] = "5.0";
  state.trading_positions[test_symbol]["price_open"] = "2000.50";
  state.trading_positions[test_symbol]["profit"] = "150.25";

  // Instantiate PositionInfo helper
  haruquant::trading::PositionInfo position(&state);

  // Select the position by its symbol
  if (position.Select("ETHUSD")) {
    std::cout << "Selected Position Symbol: " << position.Symbol() << "\n";
    std::cout << "Position Ticket: " << position.Ticket() << "\n";
    std::cout << "Position Volume: " << position.Volume() << "\n";
    std::cout << "Position Open Price: " << position.PriceOpen() << "\n";
    std::cout << "Position Floating Profit: " << position.Profit() << "\n";
  } else {
    std::cout << "Position not found.\n";
  }
}

int main() {
  demonstrate_position_info();
  return 0;
}

#include "core/state.hpp"
#include "trading/symbol_info.hpp"
#include <iostream>

void demonstrate_symbol_info() {
  // 1. You hold your state
  haruquant::core::BacktestState state;

  // 2. You populate properties (e.g., from Python/MT5) for a symbol like
  // "EURUSD"
  state.trading_symbols["EURUSD"]["ask"] = "1.08500";
  state.trading_symbols["EURUSD"]["bid"] = "1.08490";
  state.trading_symbols["EURUSD"]["digits"] = "5";
  state.trading_symbols["EURUSD"]["trade_calc_mode"] =
      "0"; // e.g. SYMBOL_CALC_MODE_FOREX

  // 3. You instantiate the SymbolInfo helper
  haruquant::trading::SymbolInfo symbol(&state);

  // 4. You must set the name of the symbol you want to query
  symbol.Name("EURUSD");

  // 5. Query it like MQL5
  std::cout << "Symbol: " << symbol.Name() << "\n";
  std::cout << "Ask: " << symbol.Ask() << "\n";
  std::cout << "Bid: " << symbol.Bid() << "\n";
  std::cout << "Digits: " << symbol.Digits() << "\n";

  // 6. Use helper methods like NormalizePrice
  double raw_price = 1.0850067;
  double norm_price = symbol.NormalizePrice(raw_price);
  std::cout << "Normalized Price: " << norm_price
            << "\n"; // Will round to 5 digits
}

int main() {
  demonstrate_symbol_info();
  return 0;
}

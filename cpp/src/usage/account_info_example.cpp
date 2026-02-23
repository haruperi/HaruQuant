#include "core/state.hpp"
#include "trading/account_info.hpp"
#include <iostream>

void demonstrate_account_info() {
  // 1. You hold your state
  haruquant::core::BacktestState state;

  // 2. You populate properties (e.g., from Python/MT5)
  state.trading_account["login"] = "12345678";
  state.trading_account["balance"] = "10500.25";
  state.trading_account["currency"] = "USD";
  state.trading_account["company"] = "MetaQuotes Software Corp.";

  // 3. You instantiate the AccountInfo helper
  haruquant::trading::AccountInfo account(&state);

  // 4. You query it just like MQL5
  std::cout << "Login: " << account.Login() << "\n";
  std::cout << "Balance: " << account.Balance() << " " << account.Currency()
            << "\n";
}

int main() {
  demonstrate_account_info();
  return 0;
}

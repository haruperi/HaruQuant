#include "core/state.hpp"
#include "trading/terminal_info.hpp"
#include <iostream>
#include <memory>

void demonstrate_terminal_info() {
  auto state = std::make_shared<haruquant::core::BacktestState>();

  // Simulate terminal properties
  state->terminal_info["build"] = "4000";
  state->terminal_info["connected"] = "1";
  state->terminal_info["trade_allowed"] = "1";
  state->terminal_info["ping_last"] = "25";
  state->terminal_info["company"] = "MetaQuotes Software Corp.";

  // Instantiate TerminalInfo helper
  haruquant::trading::TerminalInfo terminal(state);

  std::cout << "Terminal Build: " << terminal.Build() << "\n";
  std::cout << "Terminal Company: " << terminal.Company() << "\n";
  std::cout << "Is Connected: " << (terminal.Connected() ? "Yes" : "No")
            << "\n";
  std::cout << "Last Ping: " << terminal.PingLast() << " ms\n";
  std::cout << "Automated Trading Allowed: "
            << (terminal.TradeAllowed() ? "Yes" : "No") << "\n";
}

int main() {
  demonstrate_terminal_info();
  return 0;
}

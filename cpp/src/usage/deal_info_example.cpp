#include "core/state.hpp"
#include "trading/deal_info.hpp"
#include <iostream>
#include <memory>

void demonstrate_deal_info() {
  auto state = std::make_shared<haruquant::core::BacktestState>();

  // Simulate a deal present in the state
  std::string test_ticket = "20001";
  state->trading_deals[test_ticket]["ticket"] = test_ticket;
  state->trading_deals[test_ticket]["order"] = "10001";
  state->trading_deals[test_ticket]["symbol"] = "USDJPY";
  state->trading_deals[test_ticket]["type"] = "0"; // e.g., DEAL_TYPE_BUY
  state->trading_deals[test_ticket]["volume"] = "0.5";
  state->trading_deals[test_ticket]["price"] = "150.250";
  state->trading_deals[test_ticket]["commission"] = "-2.50";

  // Instantiate DealInfo helper
  haruquant::trading::DealInfo deal(state);

  // Select the deal by its ticket number
  if (deal.Ticket(20001)) {
    std::cout << "Selected Deal Ticket: " << deal.Ticket() << "\n";
    std::cout << "Deal Symbol: " << deal.Symbol() << "\n";
    std::cout << "Associated Order: " << deal.Order() << "\n";
    std::cout << "Deal Volume: " << deal.Volume() << "\n";
    std::cout << "Execution Price: " << deal.Price() << "\n";
    std::cout << "Commission Paid: " << deal.Commission() << "\n";
  } else {
    std::cout << "Deal not found.\n";
  }
}

int main() {
  demonstrate_deal_info();
  return 0;
}

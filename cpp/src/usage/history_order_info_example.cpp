#include "core/state.hpp"
#include "trading/history_order_info.hpp"
#include <iostream>
#include <memory>

void demonstrate_history_order_info() {
  auto state = std::make_shared<haruquant::core::BacktestState>();

  // Simulate a historical order present in the state
  std::string test_ticket = "10002";
  state->trading_history_orders[test_ticket]["ticket"] = test_ticket;
  state->trading_history_orders[test_ticket]["symbol"] = "GBPUSD";
  state->trading_history_orders[test_ticket]["state"] =
      "4"; // e.g., ORDER_STATE_FILLED
  state->trading_history_orders[test_ticket]["volume_initial"] = "1.0";
  state->trading_history_orders[test_ticket]["time_done"] = "1700000000";

  // Instantiate HistoryOrderInfo helper
  haruquant::trading::HistoryOrderInfo history_order(state);

  // Select the order by its ticket number
  if (history_order.Ticket(
          10002)) { // Note that MQL5 uses "Ticket()" as the selector here
    std::cout << "Selected Historical Order Ticket: " << history_order.Ticket()
              << "\n";
    std::cout << "Historical Order Symbol: " << history_order.Symbol() << "\n";
    std::cout << "Historical Order State: " << history_order.State() << "\n";
    std::cout << "Historical Order Time Done: " << history_order.TimeDone()
              << "\n";
  } else {
    std::cout << "Historical order not found.\n";
  }
}

int main() {
  demonstrate_history_order_info();
  return 0;
}

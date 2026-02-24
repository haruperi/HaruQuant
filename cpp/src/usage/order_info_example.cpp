#include "core/state.hpp"
#include "trading/order_info.hpp"
#include <iostream>
#include <memory>

void demonstrate_order_info() {
  auto state = std::make_shared<haruquant::core::BacktestState>();

  // Simulate an active order present in the state
  std::string test_ticket = "10001";
  state->trading_orders[test_ticket]["ticket"] = test_ticket;
  state->trading_orders[test_ticket]["symbol"] = "EURUSD";
  state->trading_orders[test_ticket]["type"] = "0"; // e.g., ORDER_TYPE_BUY
  state->trading_orders[test_ticket]["volume_initial"] = "1.5";
  state->trading_orders[test_ticket]["price_open"] = "1.08500";

  // Instantiate OrderInfo helper
  haruquant::trading::OrderInfo order(state);

  // Select the order by its ticket number
  if (order.Select(10001)) {
    std::cout << "Selected Order Ticket: " << order.Ticket() << "\n";
    std::cout << "Order Symbol: " << order.Symbol() << "\n";
    std::cout << "Order Volume: " << order.VolumeInitial() << "\n";
    std::cout << "Order Price: " << order.PriceOpen() << "\n";
  } else {
    std::cout << "Order not found.\n";
  }
}

int main() {
  demonstrate_order_info();
  return 0;
}

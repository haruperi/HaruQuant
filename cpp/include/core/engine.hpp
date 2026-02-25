#pragma once

#include "trading/account_info.hpp"

namespace haruquant::core {

class Engine {
public:
    explicit Engine(const haruquant::trading::AccountInfo& account);

    // Updates floating PnL for all open positions and closes positions
    // when SL/TP is hit. Logs position status when verbose=true.
    void monitor_positions(bool verbose = false);

    // Monitors pending orders for expiration and trigger conditions.
    // Triggered orders are executed as market deals and removed from pending.
    void monitor_pending_orders(bool verbose = false);

    // Recalculates account metrics from current open positions.
    void monitor_account();

private:
    haruquant::trading::AccountInfo account_{};
};

}  // namespace haruquant::core

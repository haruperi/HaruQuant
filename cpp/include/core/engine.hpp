#pragma once

#include "trading/account_info.hpp"

#include <string>
#include <vector>

namespace haruquant::core {

class BacktestSimulator;

struct EngineRunRow {
    long long index_ns{0};
    double open{0.0};
    double high{0.0};
    double low{0.0};
    double close{0.0};
    double bid{0.0};
    double ask{0.0};
    double last{0.0};
    double volume{0.0};
    long long entry_signal{0};
    long long exit_signal{0};
    double spread_points{0.0};
};

class Engine {
public:
    explicit Engine(const haruquant::trading::AccountInfo& account);

    // Iterates a simple bar stream and logs BUY signals.
    void run(const std::vector<EngineRunRow>& signal_data,
             const std::vector<EngineRunRow>& execution_data = {},
             const std::string& loop_model = "ohlc",
             const std::string& symbol = "",
             long start_unix_sec = 0,
             long end_unix_sec = 0,
             const std::string& spread_mode = "data",
             double spread_points = 10.0,
             double spread_min = 5.0,
             double spread_max = 20.0,
             double trade_volume = 0.0,
             bool verbose = false);

    // Updates floating PnL for all open positions and closes positions
    // when SL/TP is hit. Logs position status when verbose=true.
    void monitor_positions(bool verbose = false);

    // Monitors pending orders for expiration and trigger conditions.
    // Triggered orders are executed as market deals and removed from pending.
    void monitor_pending_orders(bool verbose = false);

    // Recalculates account metrics from current open positions.
    void monitor_account(bool verbose = false);

private:
    void monitor_positions_impl(BacktestSimulator& simulator, bool verbose = false);
    void monitor_pending_orders_impl(BacktestSimulator& simulator, bool verbose = false);

    haruquant::trading::AccountInfo account_{};
};

}  // namespace haruquant::core

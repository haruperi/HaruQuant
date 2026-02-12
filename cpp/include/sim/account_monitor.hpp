/**
 * @file account_monitor.hpp
 * @brief Position/account monitoring helpers for simulation backtest loop.
 */

#pragma once

#include "sim/sim_data.hpp"
#include "sim/simulator_client.hpp"

#include <string>

namespace hqt::sim {

/**
 * @brief Aggregated open-position totals for account monitoring.
 */
struct PositionTotals {
    double profit{0.0};
    double margin{0.0};
    double commission{0.0};
    double fee{0.0};
    double swap{0.0};
};

/**
 * @brief Computes MT5-style account metrics from open positions.
 */
class AccountMonitor {
public:
    [[nodiscard]] PositionTotals monitor_positions(
        const SimulatorClient& client,
        const std::string& symbol,
        double bid,
        double ask) const;

    [[nodiscard]] AccountInfoData monitor_account(
        const AccountInfoData& base,
        const PositionTotals& totals) const;
};

}  // namespace hqt::sim


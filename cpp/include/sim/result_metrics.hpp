/**
 * @file result_metrics.hpp
 * @brief Backtest result metric aggregation helpers.
 */

#pragma once

#include "sim/trade_record.hpp"

#include <cstddef>
#include <vector>

namespace hqt::sim {

struct ResultMetricsSummary {
    double initial_balance{0.0};
    double final_balance{0.0};
    double total_return{0.0};
    double total_return_pct{0.0};

    std::size_t total_trades{0};
    std::size_t winning_trades{0};
    std::size_t losing_trades{0};
    std::size_t breakeven_trades{0};

    double win_rate{0.0};        // percent
    double gross_profit{0.0};
    double gross_loss{0.0};
    double profit_factor{0.0};

    double max_drawdown{0.0};
    double max_drawdown_pct{0.0};
    double sharpe_ratio{0.0};
};

class ResultMetrics {
public:
    [[nodiscard]] static ResultMetricsSummary from_trades(
        const std::vector<TradeRecord>& trades,
        double initial_balance,
        double final_balance);
};

}  // namespace hqt::sim


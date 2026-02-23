/**
FILE: tests\test_sim_result_metrics.cpp

PURPOSE:
Defines test_sim_result_metrics.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_sim_result_metrics.cpp.
- File-local helpers supporting the main public or internal entry points.

DATA FLOW:
Callers provide requests or data -> this file applies core logic -> outputs state changes or results.

DEPENDENCIES:
- Internal modules: Neighboring headers under cpp/include and shared utility components.
- External systems: Standard C++ library and optional third-party libs linked by CMake.

DESIGN NOTES:
- Keep behavior deterministic for backtest and unit-test reliability.
- Prefer explicit validation and retcode-based failure signaling.
- Preserve low coupling between domains through typed interfaces.
*/
#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <cmath>
#include <limits>
#include <vector>

namespace {

using hqt::sim::ResultMetrics;
using hqt::sim::TradeRecord;

TEST(SimResultMetricsTest, CalculatesCoreSummaryMetrics) {
    std::vector<TradeRecord> trades{
        {.profit_loss = 100.0},
        {.profit_loss = -40.0},
        {.profit_loss = 60.0},
        {.profit_loss = 0.0},
    };

    const auto summary = ResultMetrics::from_trades(trades, 1000.0, 1120.0);

    EXPECT_DOUBLE_EQ(summary.total_return, 120.0);
    EXPECT_DOUBLE_EQ(summary.total_return_pct, 12.0);
    EXPECT_EQ(summary.total_trades, 4U);
    EXPECT_EQ(summary.winning_trades, 2U);
    EXPECT_EQ(summary.losing_trades, 1U);
    EXPECT_EQ(summary.breakeven_trades, 1U);
    EXPECT_DOUBLE_EQ(summary.win_rate, 50.0);
    EXPECT_DOUBLE_EQ(summary.gross_profit, 160.0);
    EXPECT_DOUBLE_EQ(summary.gross_loss, 40.0);
    EXPECT_DOUBLE_EQ(summary.profit_factor, 4.0);
    EXPECT_GT(summary.max_drawdown_pct, 0.0);
    EXPECT_GT(summary.sharpe_ratio, 0.0);
}

TEST(SimResultMetricsTest, NoTradesReturnsZeroedMetrics) {
    const auto summary = ResultMetrics::from_trades({}, 1000.0, 1000.0);

    EXPECT_EQ(summary.total_trades, 0U);
    EXPECT_DOUBLE_EQ(summary.total_return, 0.0);
    EXPECT_DOUBLE_EQ(summary.total_return_pct, 0.0);
    EXPECT_DOUBLE_EQ(summary.win_rate, 0.0);
    EXPECT_DOUBLE_EQ(summary.profit_factor, 0.0);
    EXPECT_DOUBLE_EQ(summary.max_drawdown_pct, 0.0);
    EXPECT_DOUBLE_EQ(summary.sharpe_ratio, 0.0);
}

TEST(SimResultMetricsTest, ProfitFactorInfinityWhenNoLosses) {
    std::vector<TradeRecord> trades{
        {.profit_loss = 10.0},
        {.profit_loss = 20.0},
    };

    const auto summary = ResultMetrics::from_trades(trades, 1000.0, 1030.0);
    EXPECT_TRUE(std::isinf(summary.profit_factor));
}

}  // namespace



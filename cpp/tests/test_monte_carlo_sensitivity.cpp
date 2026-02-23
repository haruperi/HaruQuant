/**
FILE: tests\test_monte_carlo_sensitivity.cpp

PURPOSE:
Defines test_monte_carlo_sensitivity.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_monte_carlo_sensitivity.cpp.
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

#include <unordered_map>
#include <vector>

using haruquant::sim::MonteCarloAnalyzer;
using haruquant::sim::MonteCarloMode;
using haruquant::sim::SensitivityAnalyzer;

TEST(MonteCarloSensitivityTest, MonteCarloBootstrapProducesSummary) {
    const std::vector<double> pnl{1.0, -0.5, 0.3, 0.2, -0.1, 0.7};
    const auto summary = MonteCarloAnalyzer::simulate(pnl, 200U, 42U, MonteCarloMode::Bootstrap, 0.10);

    EXPECT_EQ(summary.simulations, 200U);
    EXPECT_GT(summary.p95, summary.p05);
    EXPECT_GE(summary.probability_positive, 0.0);
    EXPECT_LE(summary.probability_positive, 1.0);
}

TEST(MonteCarloSensitivityTest, MonteCarloModesAreDeterministicWithSeed) {
    const std::vector<double> pnl{0.2, -0.1, 0.4, -0.2, 0.1};
    const auto a = MonteCarloAnalyzer::simulate(pnl, 120U, 7U, MonteCarloMode::Shuffle, 0.10);
    const auto b = MonteCarloAnalyzer::simulate(pnl, 120U, 7U, MonteCarloMode::Shuffle, 0.10);
    EXPECT_DOUBLE_EQ(a.mean, b.mean);
    EXPECT_DOUBLE_EQ(a.stddev, b.stddev);
    EXPECT_DOUBLE_EQ(a.p50, b.p50);
}

TEST(MonteCarloSensitivityTest, SensitivityReportBuildsNormalizedMapAndStability) {
    haruquant::sim::OptimizationParamSpace space{
        {"x", {0.0, 1.0, 2.0, 3.0}},
        {"y", {-2.0, -1.0, 0.0}},
    };

    auto objective = [](const std::unordered_map<std::string, double>& p) {
        const double x = p.at("x");
        const double y = p.at("y");
        return -((x - 2.0) * (x - 2.0)) - ((y + 1.0) * (y + 1.0));
    };

    const auto report = SensitivityAnalyzer::analyze(space, objective, 0U);
    EXPECT_GT(report.evaluations, 0U);
    EXPECT_GE(report.stability_score, 0.0);
    EXPECT_LE(report.stability_score, 1.0);
    EXPECT_EQ(report.normalized_sensitivity.size(), 2U);
}



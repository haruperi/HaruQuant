/**
 * @file test_monte_carlo_sensitivity.cpp
 * @brief Tests for C++ Monte Carlo and sensitivity analyzers (IP-43).
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <unordered_map>
#include <vector>

using hqt::sim::MonteCarloAnalyzer;
using hqt::sim::MonteCarloMode;
using hqt::sim::SensitivityAnalyzer;

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
    hqt::sim::OptimizationParamSpace space{
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


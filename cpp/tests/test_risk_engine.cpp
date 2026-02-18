/**
 * @file test_risk_engine.cpp
 * @brief Tests for first-slice C++ risk primitives.
 */

#include <gtest/gtest.h>
#include <unordered_map>
#include "risk/risk_engine.hpp"

namespace {

using hqt::risk::PositionSizingConfig;
using hqt::risk::PositionSizer;
using hqt::risk::CorrelationPreference;
using hqt::risk::ExposureConstraints;
using hqt::risk::RiskAccountState;
using hqt::risk::RiskBudgetAllocator;
using hqt::risk::RiskGovernor;
using hqt::risk::RiskGovernorConfig;
using hqt::risk::RiskMode;
using hqt::risk::RiskRegimeDetector;
using hqt::risk::validate_position_size;

TEST(RiskEngineTest, RegimeDetectorStressWhenVolAndCorrSpike) {
    RiskRegimeDetector detector(1.5, 0.5, 0.1, 10, 5);
    std::vector<std::vector<double>> returns_matrix;
    returns_matrix.reserve(20);

    for (int i = 0; i < 15; ++i) {
        returns_matrix.push_back({0.001, -0.001});
    }
    returns_matrix.push_back({0.08, 0.09});
    returns_matrix.push_back({-0.07, -0.08});
    returns_matrix.push_back({0.09, 0.10});
    returns_matrix.push_back({-0.08, -0.09});
    returns_matrix.push_back({0.10, 0.11});

    std::vector<double> equity_curve;
    equity_curve.reserve(20);
    for (int i = 0; i < 20; ++i) {
        equity_curve.push_back(10000.0 - (i * 120.0));
    }

    const auto state = detector.detect(returns_matrix, equity_curve);
    EXPECT_EQ(state.name, "STRESS");
}

TEST(RiskEngineTest, PositionSizerFixedRiskFormula) {
    PositionSizingConfig cfg;
    cfg.risk_percent = 1.0;
    PositionSizer sizer("fixed_risk", cfg);
    const double size = sizer.calculate_size(10000.0, 1.1000, 1.0990, 100000.0);
    EXPECT_NEAR(size, 1.0, 1e-9);
}

TEST(RiskEngineTest, ValidatePositionSizeClampAndStep) {
    const double out = validate_position_size(0.237, 0.01, 1.0, 0.01, 0.2, false);
    EXPECT_NEAR(out, 0.2, 1e-9);
}

TEST(RiskEngineTest, RiskGovernorRejectsDrawdownAndExposure) {
    RiskGovernorConfig cfg;
    cfg.max_drawdown_frac = 0.10;
    cfg.max_gross_exposure = 2.0;
    cfg.max_net_exposure = 1.0;
    RiskGovernor gov(cfg);

    RiskAccountState dd_state{8900.0, 10000.0, 0.5, 0.1};
    auto dd_decision = gov.can_trade(dd_state, 0.1, 0.1);
    EXPECT_FALSE(dd_decision.allowed);
    EXPECT_EQ(dd_decision.reason, "max_drawdown_exceeded");
    EXPECT_EQ(dd_decision.policy_code, "MAX_DRAWDOWN");

    RiskAccountState gross_state{9900.0, 10000.0, 1.9, 0.2};
    auto gross_decision = gov.can_trade(gross_state, 0.2, 0.1);
    EXPECT_FALSE(gross_decision.allowed);
    EXPECT_EQ(gross_decision.reason, "max_gross_exposure_exceeded");
    EXPECT_EQ(gross_decision.policy_code, "MAX_GROSS_EXPOSURE");

    RiskAccountState net_state{9900.0, 10000.0, 0.5, 0.95};
    auto net_decision = gov.can_trade(net_state, 0.1, 0.1);
    EXPECT_FALSE(net_decision.allowed);
    EXPECT_EQ(net_decision.reason, "max_net_exposure_exceeded");
    EXPECT_EQ(net_decision.policy_code, "MAX_NET_EXPOSURE");
}

TEST(RiskEngineTest, RiskBudgetAllocatorComputesTargetsAndDeltas) {
    CorrelationPreference pref;
    pref.target_corr = 0.5;
    pref.penalty_strength = 2.0;
    pref.min_budget_frac = 0.3;
    RiskBudgetAllocator allocator(pref);

    std::unordered_map<std::string, double> base{
        {"EURUSD", 1.0},
        {"GBPUSD", 1.0},
    };
    std::unordered_map<std::string, double> budgets{
        {"EURUSD", 0.5},
        {"GBPUSD", 0.5},
    };
    std::unordered_map<std::string, double> corr_map{
        {"EURUSD", 0.9},
        {"GBPUSD", 0.1},
    };

    const auto target = allocator.compute_target_lots(base, budgets, corr_map);
    ASSERT_EQ(target.size(), 2U);
    EXPECT_LT(target.at("EURUSD"), target.at("GBPUSD"));

    const auto deltas = allocator.lots_to_deltas(base, target);
    EXPECT_NEAR(deltas.at("EURUSD"), target.at("EURUSD") - 1.0, 1e-9);
    EXPECT_NEAR(deltas.at("GBPUSD"), target.at("GBPUSD") - 1.0, 1e-9);
}

TEST(RiskEngineTest, RiskBudgetAllocatorAppliesExposureConstraints) {
    RiskBudgetAllocator allocator;
    ExposureConstraints constraints;
    constraints.max_total_exposure = 1.0;
    constraints.max_symbol_exposure = 0.7;
    constraints.max_strategy_exposure["S1"] = 0.8;
    constraints.max_asset_exposure["FX"] = 0.9;

    std::unordered_map<std::string, double> target{
        {"EURUSD", 0.8},
        {"GBPUSD", 0.6},
    };
    std::unordered_map<std::string, std::string> symbol_to_strategy{
        {"EURUSD", "S1"},
        {"GBPUSD", "S1"},
    };
    std::unordered_map<std::string, std::string> symbol_to_asset{
        {"EURUSD", "FX"},
        {"GBPUSD", "FX"},
    };

    const auto constrained = allocator.apply_exposure_constraints(
        target, symbol_to_strategy, symbol_to_asset, constraints);
    ASSERT_EQ(constrained.size(), 2U);
    EXPECT_LE(constrained.at("EURUSD"), 0.7);
    EXPECT_LE(constrained.at("GBPUSD"), 0.7);
    EXPECT_LE(constrained.at("EURUSD") + constrained.at("GBPUSD"), 1.0 + 1e-12);
}

TEST(RiskEngineTest, RiskGovernorModeSpecificSizeAndMarginChecks) {
    RiskGovernorConfig cfg;
    cfg.max_drawdown_frac = 0.10;
    cfg.max_gross_exposure = 2.0;
    cfg.max_net_exposure = 1.0;
    cfg.live_limit_multiplier = 0.90;
    cfg.backtest_limit_multiplier = 1.10;
    cfg.min_order_size = 0.05;
    cfg.max_order_size = 2.0;
    cfg.max_margin_utilization = 0.80;
    RiskGovernor gov(cfg);

    RiskAccountState state{9800.0, 10000.0, 1.7, 0.7};

    const auto size_reject = gov.can_trade_with_mode(
        state, 0.01, 0.1, 0.1, 100.0, 1000.0, RiskMode::Live);
    EXPECT_FALSE(size_reject.allowed);
    EXPECT_EQ(size_reject.policy_code, "SIZE_INVALID");

    const auto margin_reject = gov.can_trade_with_mode(
        state, 0.1, 0.1, 0.1, 900.0, 1000.0, RiskMode::Live);
    EXPECT_FALSE(margin_reject.allowed);
    EXPECT_EQ(margin_reject.policy_code, "INSUFFICIENT_MARGIN");

    const auto live_reject = gov.can_trade_with_mode(
        state, 0.1, 0.15, 0.10, 100.0, 1000.0, RiskMode::Live);
    EXPECT_FALSE(live_reject.allowed);
    EXPECT_EQ(live_reject.policy_code, "MAX_GROSS_EXPOSURE");

    const auto backtest_accept = gov.can_trade_with_mode(
        state, 0.1, 0.15, 0.10, 100.0, 1000.0, RiskMode::Backtest);
    EXPECT_TRUE(backtest_accept.allowed);
    EXPECT_EQ(backtest_accept.policy_code, "OK");
}

}  // namespace

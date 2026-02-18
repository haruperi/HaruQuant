/**
 * @file test_allocation_models.cpp
 * @brief Tests for allocation and exposure constraint primitives.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::ExposureConstraints;
using hqt::sim::PortfolioAllocator;

TEST(AllocationModelsTest, EqualWeightAllocation) {
    const auto alloc = PortfolioAllocator::equal_weight({"EURUSD", "GBPUSD", "USDJPY"}, 0.9);
    ASSERT_EQ(alloc.size(), 3U);
    EXPECT_NEAR(alloc.at("EURUSD"), 0.3, 1e-9);
    EXPECT_NEAR(alloc.at("GBPUSD"), 0.3, 1e-9);
    EXPECT_NEAR(alloc.at("USDJPY"), 0.3, 1e-9);
}

TEST(AllocationModelsTest, RiskParityInverseVol) {
    const auto alloc = PortfolioAllocator::risk_parity(
        {{"LOW_VOL", 0.01}, {"HIGH_VOL", 0.05}},
        1.0);
    ASSERT_EQ(alloc.size(), 2U);
    EXPECT_GT(alloc.at("LOW_VOL"), alloc.at("HIGH_VOL"));
    EXPECT_NEAR(alloc.at("LOW_VOL") + alloc.at("HIGH_VOL"), 1.0, 1e-9);
}

TEST(AllocationModelsTest, CustomAllocationNormalized) {
    const auto alloc = PortfolioAllocator::custom(
        {{"A", 2.0}, {"B", 1.0}},
        0.9,
        true);
    ASSERT_EQ(alloc.size(), 2U);
    EXPECT_NEAR(alloc.at("A"), 0.6, 1e-9);
    EXPECT_NEAR(alloc.at("B"), 0.3, 1e-9);
}

TEST(AllocationModelsTest, ExposureConstraintsApplied) {
    ExposureConstraints constraints;
    constraints.max_total_exposure = 0.8;
    constraints.max_symbol_exposure = 0.5;
    constraints.max_strategy_exposure["trend"] = 0.6;
    constraints.max_asset_exposure["FX"] = 0.7;

    const auto constrained = PortfolioAllocator::apply_exposure_constraints(
        {{"EURUSD", 0.6}, {"GBPUSD", 0.4}, {"XAUUSD", 0.4}},
        {{"EURUSD", "trend"}, {"GBPUSD", "trend"}, {"XAUUSD", "carry"}},
        {{"EURUSD", "FX"}, {"GBPUSD", "FX"}, {"XAUUSD", "METAL"}},
        constraints);

    ASSERT_EQ(constrained.size(), 3U);
    EXPECT_LE(constrained.at("EURUSD"), 0.5);
    EXPECT_LE(constrained.at("EURUSD") + constrained.at("GBPUSD"), 0.7 + 1e-9);
    EXPECT_LE(constrained.at("EURUSD") + constrained.at("GBPUSD") + constrained.at("XAUUSD"), 0.8 + 1e-9);
}

}  // namespace


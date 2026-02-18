/**
 * @file test_rebalance_policies.cpp
 * @brief Tests for scheduled and event-triggered rebalance policy.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::RebalanceController;
using hqt::sim::RebalancePolicy;

TEST(RebalancePoliciesTest, ScheduledRebalanceTriggersAtInterval) {
    RebalancePolicy policy;
    policy.schedule_interval_msc = 60'000;
    policy.drift_threshold = 0.0;
    RebalanceController controller(policy);

    EXPECT_TRUE(controller.should_rebalance(1'000, {}, {}));  // First run.
    controller.mark_rebalanced(1'000);

    EXPECT_FALSE(controller.should_rebalance(30'000, {}, {}));
    EXPECT_TRUE(controller.should_rebalance(61'000, {}, {}));
}

TEST(RebalancePoliciesTest, DriftTriggeredRebalance) {
    RebalancePolicy policy;
    policy.schedule_interval_msc = 0;
    policy.drift_threshold = 0.10;
    RebalanceController controller(policy);

    const bool should_rebalance = controller.should_rebalance(
        10'000,
        {{"EURUSD", 0.20}, {"GBPUSD", 0.80}},
        {{"EURUSD", 0.35}, {"GBPUSD", 0.65}});
    EXPECT_TRUE(should_rebalance);

    const bool should_not_rebalance = controller.should_rebalance(
        20'000,
        {{"EURUSD", 0.30}, {"GBPUSD", 0.70}},
        {{"EURUSD", 0.35}, {"GBPUSD", 0.65}});
    EXPECT_FALSE(should_not_rebalance);
}

}  // namespace


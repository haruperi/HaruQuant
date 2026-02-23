/**
FILE: tests\test_rebalance_policies.cpp

PURPOSE:
Defines test_rebalance_policies.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_rebalance_policies.cpp.
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

namespace {

using haruquant::sim::RebalanceController;
using haruquant::sim::RebalancePolicy;

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



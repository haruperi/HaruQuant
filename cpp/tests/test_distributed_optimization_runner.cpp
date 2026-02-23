/**
FILE: tests\test_distributed_optimization_runner.cpp

PURPOSE:
Defines test_distributed_optimization_runner.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_distributed_optimization_runner.cpp.
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

#include <atomic>
#include <chrono>
#include <thread>
#include <unordered_map>
#include <vector>

using haruquant::sim::DistributedOptimizationRunner;
using haruquant::sim::OptimizationWorkerPolicy;

namespace {

std::vector<std::unordered_map<std::string, double>> params_list() {
    return {
        {{"x", 0.0}, {"y", 0.0}},
        {{"x", 1.0}, {"y", -1.0}},
        {{"x", 2.0}, {"y", -1.0}},
        {{"x", 3.0}, {"y", 1.0}},
    };
}

double objective(const std::unordered_map<std::string, double>& p) {
    const double x = p.at("x");
    const double y = p.at("y");
    return -((x - 2.0) * (x - 2.0)) - ((y + 1.0) * (y + 1.0));
}

}  // namespace

TEST(DistributedOptimizationRunnerTest, ExecutesAllTasksAcrossWorkers) {
    OptimizationWorkerPolicy policy;
    policy.max_workers = 2U;
    policy.max_restarts = 0U;
    policy.task_timeout_ms = 1000;
    policy.heartbeat_ms = 10;

    const auto result = DistributedOptimizationRunner::run(params_list(), objective, policy);
    ASSERT_EQ(result.health.submitted, 4U);
    EXPECT_EQ(result.health.completed, 4U);
    EXPECT_EQ(result.health.failed, 0U);
    ASSERT_EQ(result.trials.size(), 4U);
    EXPECT_DOUBLE_EQ(result.trials.front().score, 0.0);
    EXPECT_DOUBLE_EQ(result.trials.front().params.at("x"), 2.0);
    EXPECT_DOUBLE_EQ(result.trials.front().params.at("y"), -1.0);
}

TEST(DistributedOptimizationRunnerTest, RestartsOnTransientFailure) {
    OptimizationWorkerPolicy policy;
    policy.max_workers = 2U;
    policy.max_restarts = 1U;
    policy.task_timeout_ms = 1000;
    policy.heartbeat_ms = 10;

    std::atomic<int> first_failures{0};
    auto flaky = [&](const std::unordered_map<std::string, double>& p) {
        if (p.at("x") == 1.0 && first_failures.fetch_add(1) == 0) {
            throw std::runtime_error("transient failure");
        }
        return objective(p);
    };

    const auto result = DistributedOptimizationRunner::run(params_list(), flaky, policy);
    EXPECT_EQ(result.health.completed, 4U);
    EXPECT_EQ(result.health.failed, 0U);
    EXPECT_GE(result.health.restarted, 1U);
}

TEST(DistributedOptimizationRunnerTest, RetriesTimedOutTaskThenCompletes) {
    OptimizationWorkerPolicy policy;
    policy.max_workers = 2U;
    policy.max_restarts = 1U;
    policy.task_timeout_ms = 10;
    policy.heartbeat_ms = 5;

    std::atomic<int> timeout_once{0};
    auto sometimes_slow = [&](const std::unordered_map<std::string, double>& p) {
        if (p.at("x") == 3.0 && timeout_once.fetch_add(1) == 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        return objective(p);
    };

    const auto result = DistributedOptimizationRunner::run(params_list(), sometimes_slow, policy);
    EXPECT_EQ(result.health.completed, 4U);
    EXPECT_EQ(result.health.failed, 0U);
    EXPECT_GE(result.health.timeout_restarts, 1U);
    EXPECT_GE(result.health.restarted, 1U);
}



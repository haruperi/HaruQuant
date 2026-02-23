/**
FILE: tests\test_wfo_wfm.cpp

PURPOSE:
Defines test_wfo_wfm.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_wfo_wfm.cpp.
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

#include <vector>

using hqt::sim::EdgeDetector;
using hqt::sim::WfmCellResult;
using hqt::sim::WfoSpec;
using hqt::sim::WfoWfmOrchestrator;
using hqt::sim::WfoWindow;
using hqt::sim::WfoWindowResult;

TEST(WfoWfmTest, BuildWindowsUsesTrainTestAndStep) {
    const WfoSpec spec{50, 20, 20};
    const auto windows = WfoWfmOrchestrator::build_windows(120, spec);

    ASSERT_EQ(windows.size(), 3U);
    EXPECT_EQ(windows[0].train_start, 0U);
    EXPECT_EQ(windows[0].train_end, 50U);
    EXPECT_EQ(windows[0].test_start, 50U);
    EXPECT_EQ(windows[0].test_end, 70U);
    EXPECT_EQ(windows[2].train_start, 40U);
    EXPECT_EQ(windows[2].test_end, 110U);
}

TEST(WfoWfmTest, RunWfoAndSummarizeProducesExpectedStats) {
    const WfoSpec spec{50, 20, 20};
    const auto results = WfoWfmOrchestrator::run_wfo(
        120,
        spec,
        [](const WfoWindow& w, bool is_train) {
            const double base = 1.0 + (static_cast<double>(w.train_start) * 0.001);
            return is_train ? base : (base * 0.8);
        });

    ASSERT_EQ(results.size(), 3U);
    const auto summary = WfoWfmOrchestrator::summarize(results);

    EXPECT_EQ(summary.num_windows, 3U);
    EXPECT_GT(summary.avg_train_score, summary.avg_test_score);
    EXPECT_GT(summary.overfitting_ratio, 0.0);
    EXPECT_LT(summary.overfitting_ratio, 1.0);
}

TEST(WfoWfmTest, RunWfmReturnsOneCellPerSpec) {
    const std::vector<WfoSpec> specs{
        WfoSpec{60, 20, 20},
        WfoSpec{80, 20, 20},
    };

    const auto matrix = WfoWfmOrchestrator::run_wfm(
        220,
        specs,
        [](const WfoWindow& w, bool is_train) {
            const double base = 2.0 + (static_cast<double>(w.test_end) * 0.0001);
            return is_train ? base : (base - 0.2);
        });

    ASSERT_EQ(matrix.size(), 2U);
    for (const WfmCellResult& cell : matrix) {
        EXPECT_GT(cell.summary.num_windows, 0U);
    }
}

TEST(WfoWfmTest, EdgeDetectorConfirmsSkillWhenPValueIsLow) {
    std::vector<WfoWindowResult> results;
    results.reserve(10);
    for (std::size_t i = 0; i < 10; ++i) {
        WfoWindowResult r;
        r.window = WfoWindow{i * 10, i * 10 + 5, i * 10 + 5, i * 10 + 10};
        r.train_score = 0.4;
        r.test_score = 0.2;
        results.push_back(r);
    }

    const auto report = EdgeDetector::from_wfo(results, 0.05);
    EXPECT_TRUE(report.skill_confirmed);
    EXPECT_LT(report.p_value, 0.05);
    EXPECT_EQ(report.verdict, "EDGE_CONFIRMED");
}



/**
FILE: tests\test_experiment_registry.cpp

PURPOSE:
Defines test_experiment_registry.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_experiment_registry.cpp.
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

#include <unordered_set>
#include <vector>

using haruquant::sim::ExperimentRecord;
using haruquant::sim::ExperimentRegistry;
using haruquant::sim::SeasonalPatternAnalyzer;
using haruquant::sim::SymbolClassifier;

TEST(ExperimentRegistryTest, UpsertAndAllAreSearchable) {
    ExperimentRegistry registry;

    ExperimentRecord a;
    a.experiment_id = "exp-001";
    a.strategy = "trend";
    a.symbol = "EURUSD";
    a.timeframe = "M15";
    a.period_start_msc = 1'000;
    a.period_end_msc = 2'000;
    a.metadata["owner"] = "research";
    registry.upsert(a);

    ExperimentRecord b;
    b.experiment_id = "exp-002";
    b.strategy = "mean_rev";
    b.symbol = "XAUUSD";
    b.timeframe = "H1";
    b.period_start_msc = 2'500;
    b.period_end_msc = 4'000;
    registry.upsert(b);

    const auto all = registry.all();
    ASSERT_EQ(all.size(), 2U);

    const auto trend = registry.query("trend", std::nullopt, std::nullopt, std::nullopt);
    ASSERT_EQ(trend.size(), 1U);
    EXPECT_EQ(trend.front().experiment_id, "exp-001");
}

TEST(ExperimentRegistryTest, QueryBySymbolAndPeriodOverlap) {
    ExperimentRegistry registry;

    ExperimentRecord a{"exp-001", "s1", "EURUSD", "M5", 1'000, 2'000, {}};
    ExperimentRecord b{"exp-002", "s1", "EURUSD", "M5", 3'000, 4'000, {}};
    ExperimentRecord c{"exp-003", "s1", "GBPUSD", "M5", 1'500, 3'500, {}};
    registry.upsert(a);
    registry.upsert(b);
    registry.upsert(c);

    const auto eur = registry.query(std::nullopt, "EURUSD", 1'500, 3'200);
    ASSERT_EQ(eur.size(), 2U);
    EXPECT_EQ(eur.front().experiment_id, "exp-001");
    EXPECT_EQ(eur.back().experiment_id, "exp-002");
}

TEST(ExperimentRegistryTest, SymbolClassificationSupportsAssetClassAndVolRegime) {
    const auto fx = SymbolClassifier::classify("EURUSD", 0.08);
    EXPECT_EQ(fx.asset_class, "fx");
    EXPECT_EQ(fx.volatility_regime, "low");

    const auto crypto = SymbolClassifier::classify("BTCUSD", 0.55);
    EXPECT_EQ(crypto.asset_class, "crypto");
    EXPECT_EQ(crypto.volatility_regime, "extreme");
}

TEST(ExperimentRegistryTest, SeasonalPatternAnalyzerBuildsDayAndHolidayBuckets) {
    const std::vector<int64_t> ts_msc{
        0LL * 86400LL * 1000LL,  // day 0
        1LL * 86400LL * 1000LL,  // day 1
        2LL * 86400LL * 1000LL,  // day 2
        3LL * 86400LL * 1000LL   // day 3
    };
    const std::vector<double> rets{0.01, -0.01, 0.02, 0.00};
    const std::unordered_set<int64_t> holidays{1LL};  // second sample day

    const auto report = SeasonalPatternAnalyzer::analyze(ts_msc, rets, holidays);
    ASSERT_EQ(report.day_of_week.size(), 7U);
    ASSERT_EQ(report.holiday_vs_non_holiday.size(), 2U);

    const auto non_holiday = report.holiday_vs_non_holiday[0];
    const auto holiday = report.holiday_vs_non_holiday[1];
    EXPECT_EQ(holiday.count, 1U);
    EXPECT_EQ(non_holiday.count, 3U);
}



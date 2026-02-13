/**
 * @file test_sim_tick_models.cpp
 * @brief Tests for deterministic tick model generators.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <vector>

namespace {

using hqt::sim::ModelTick;
using hqt::sim::TickModel;
using hqt::sim::TickModelBar;

TEST(SimTickModelsTest, M1OhlcSequenceOrderAndLength) {
    const std::vector<TickModelBar> bars{
        {1000, 1.1000, 1.1010, 1.0990, 1.1005, 10.0},  // bullish
        {2000, 1.2000, 1.2010, 1.1980, 1.1990, 8.0},   // bearish
    };

    const auto ticks = TickModel::generate_m1_ohlc(bars, 0.0001, 10.0);
    ASSERT_EQ(ticks.size(), 8U);

    EXPECT_DOUBLE_EQ(ticks[0].bid, 1.1000);
    EXPECT_DOUBLE_EQ(ticks[1].bid, 1.0990);
    EXPECT_DOUBLE_EQ(ticks[2].bid, 1.1010);
    EXPECT_DOUBLE_EQ(ticks[3].bid, 1.1005);

    EXPECT_DOUBLE_EQ(ticks[4].bid, 1.2000);
    EXPECT_DOUBLE_EQ(ticks[5].bid, 1.2010);
    EXPECT_DOUBLE_EQ(ticks[6].bid, 1.1980);
    EXPECT_DOUBLE_EQ(ticks[7].bid, 1.1990);
}

TEST(SimTickModelsTest, SyntheticTicksDeterministicExpansion) {
    const std::vector<TickModelBar> bars{
        {3000, 1.3000, 1.3010, 1.2990, 1.3005, 5.0},
    };

    const auto ticks_a = TickModel::generate_synthetic_ticks(bars, 0.0001, 10.0, 2);
    const auto ticks_b = TickModel::generate_synthetic_ticks(bars, 0.0001, 10.0, 2);

    EXPECT_EQ(ticks_a, ticks_b);
    ASSERT_EQ(ticks_a.size(), 10U);  // 1 + 3*(support_points+1) with support_points=2
    EXPECT_DOUBLE_EQ(ticks_a.front().bid, 1.3000);
    EXPECT_DOUBLE_EQ(ticks_a.back().bid, 1.3005);
}

TEST(SimTickModelsTest, RealTicksPassthrough) {
    const std::vector<ModelTick> input{
        {100, 1.1000, 1.1002, 1.1000},
        {101, 1.1001, 1.1003, 1.1001},
        {102, 1.0999, 1.1001, 1.0999},
    };

    const auto output = TickModel::passthrough_real_ticks(input);
    EXPECT_EQ(output, input);
}

}  // namespace


/**
 * @file test_replay_clock.cpp
 * @brief Unit tests for ReplayClock deterministic playback controls.
 */

#include <gtest/gtest.h>
#include "engine/replay_clock.hpp"

#include <vector>

using namespace hqt;

TEST(ReplayClockTest, DeterministicAdvanceSequence) {
    const std::vector<int64_t> timeline = {1000, 2000, 3000, 4000};
    ReplayClock a(timeline);
    ReplayClock b(timeline);

    std::vector<int64_t> out_a;
    std::vector<int64_t> out_b;

    while (!a.finished()) {
        auto x = a.advance();
        ASSERT_TRUE(x.has_value());
        out_a.push_back(*x);
    }
    while (!b.finished()) {
        auto x = b.advance();
        ASSERT_TRUE(x.has_value());
        out_b.push_back(*x);
    }

    EXPECT_EQ(out_a, out_b);
    EXPECT_EQ(a.timeline_signature(), b.timeline_signature());
}

TEST(ReplayClockTest, PauseResumeAndStepByBar) {
    ReplayClock clock({10, 20, 30, 40});
    clock.pause();
    EXPECT_TRUE(clock.paused());

    // advance() should be blocked while paused
    EXPECT_FALSE(clock.advance().has_value());
    EXPECT_EQ(clock.cursor(), 0U);

    // step_by_bar is a debug control and should still advance.
    auto stepped = clock.step_by_bar(2);
    ASSERT_TRUE(stepped.has_value());
    EXPECT_EQ(*stepped, 20);
    EXPECT_EQ(clock.cursor(), 2U);

    clock.resume();
    EXPECT_FALSE(clock.paused());
    auto next = clock.advance();
    ASSERT_TRUE(next.has_value());
    EXPECT_EQ(*next, 30);
}

TEST(ReplayClockTest, StepBeyondEndStopsAtLastBar) {
    ReplayClock clock({1, 2, 3});
    auto last = clock.step_by_bar(10);
    ASSERT_TRUE(last.has_value());
    EXPECT_EQ(*last, 3);
    EXPECT_TRUE(clock.finished());
}

TEST(ReplayClockTest, StateSnapshotContainsReproducibleCursorInfo) {
    ReplayClock clock({100, 200, 300});
    clock.set_speed_multiplier(2.0);
    auto stepped = clock.step_by_bar(2);
    ASSERT_TRUE(stepped.has_value());
    clock.pause();

    const auto st = clock.state();
    EXPECT_EQ(st.cursor, 2U);
    EXPECT_EQ(st.current_time_us, 200);
    EXPECT_TRUE(st.paused);
    EXPECT_DOUBLE_EQ(st.speed_multiplier, 2.0);
    EXPECT_EQ(st.timeline_signature, clock.timeline_signature());
}

TEST(ReplayClockTest, DifferentTimelinesProduceDifferentSignatures) {
    ReplayClock a({1, 2, 3});
    ReplayClock b({1, 2, 4});
    EXPECT_NE(a.timeline_signature(), b.timeline_signature());
}

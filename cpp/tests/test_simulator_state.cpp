/**
 * @file test_simulator_state.cpp
 * @brief Tests for simulation module scaffold state.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::SimulatorState;

TEST(SimulatorStateTest, DefaultConstruction) {
    SimulatorState state;

    EXPECT_FALSE(state.running);
    EXPECT_FALSE(state.paused);
    EXPECT_EQ(state.current_time_us, 0);
    EXPECT_EQ(state.current_bar_index, 0U);
    EXPECT_EQ(state.processed_events, 0U);
}

TEST(SimulatorStateTest, ResetRestoresDefaults) {
    SimulatorState state;
    state.running = true;
    state.paused = true;
    state.current_time_us = 123456;
    state.current_bar_index = 42;
    state.processed_events = 7;

    state.reset();

    EXPECT_FALSE(state.running);
    EXPECT_FALSE(state.paused);
    EXPECT_EQ(state.current_time_us, 0);
    EXPECT_EQ(state.current_bar_index, 0U);
    EXPECT_EQ(state.processed_events, 0U);
}

}  // namespace


/**
FILE: tests\test_simulator_state.cpp

PURPOSE:
Defines test_simulator_state.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_simulator_state.cpp.
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

using haruquant::sim::SimulatorState;

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



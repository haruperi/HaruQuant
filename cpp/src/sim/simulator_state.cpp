#include "sim/simulator_state.hpp"

namespace hqt::sim {

void SimulatorState::reset() noexcept {
    running = false;
    paused = false;
    current_time_us = 0;
    current_bar_index = 0;
    processed_events = 0;
}

}  // namespace hqt::sim


/**
 * @file simulator_state.hpp
 * @brief Minimal simulation runtime state container.
 *
 * PR-001 scaffold: establishes a dedicated simulation module surface
 * without changing existing runtime behavior.
 */

#pragma once

#include <cstddef>
#include <cstdint>

namespace hqt::sim {

/**
 * @brief Mutable state shared by simulation runtime components.
 */
struct SimulatorState {
    bool running{false};
    bool paused{false};
    int64_t current_time_us{0};
    std::size_t current_bar_index{0};
    std::size_t processed_events{0};

    /**
     * @brief Reset state to construction defaults.
     */
    void reset() noexcept;
};

}  // namespace hqt::sim


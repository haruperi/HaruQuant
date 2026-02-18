/**
 * @file models.cpp
 * @brief Unified engine models compilation unit.
 */

#include "engine/engine.hpp"

#include <sstream>

namespace hqt::sim {

namespace {

template <typename T>
std::string to_string_num(T value) {
    std::ostringstream oss;
    oss << value;
    return oss.str();
}

}  // namespace

Dict SymbolTickData::to_dict() const {
    return {
        {"time", to_string_num(time)},
        {"bid", to_string_num(bid)},
        {"ask", to_string_num(ask)},
        {"last", to_string_num(last)},
        {"volume", to_string_num(volume)},
        {"time_msc", to_string_num(time_msc)},
        {"flags", to_string_num(flags)},
        {"volume_real", to_string_num(volume_real)},
    };
}

void SimulatorState::reset() noexcept {
    running = false;
    paused = false;
    current_time_us = 0;
    current_bar_index = 0;
    processed_events = 0;
}

}  // namespace hqt::sim

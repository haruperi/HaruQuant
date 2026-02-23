/**
FILE: src\engine\models.cpp

PURPOSE:
Defines models.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in models.cpp.
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
#include "engine/engine.hpp"

#include <sstream>

namespace haruquant::sim {

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

}  // namespace haruquant::sim


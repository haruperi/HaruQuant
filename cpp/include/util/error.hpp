/**
FILE: include\util\error.hpp

PURPOSE:
Defines error.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in error.hpp.
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
#pragma once

#include <string>

namespace hqt::util {

struct ErrorInfo {
    int code{0};
    std::string name{"OK"};
    std::string message{"The operation completed successfully"};
    std::string domain{"trade"};
    bool retryable{false};
};

[[nodiscard]] ErrorInfo error_from_retcode(int code);
[[nodiscard]] std::string error_name(int code);
[[nodiscard]] bool is_success_retcode(int code) noexcept;

}  // namespace hqt::util



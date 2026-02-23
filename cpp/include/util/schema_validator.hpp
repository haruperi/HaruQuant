/**
FILE: include\util\schema_validator.hpp

PURPOSE:
Defines schema_validator.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in schema_validator.hpp.
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

#include <cstdint>
#include <string>
#include <unordered_map>
#include <variant>

namespace hqt::util {

using SchemaValue = std::variant<std::string, std::int64_t, double, bool>;
using SchemaPayload = std::unordered_map<std::string, SchemaValue>;

struct ValidationResult {
    bool ok;
    std::string message;
};

ValidationResult validate_market_schema(const SchemaPayload& payload);
ValidationResult validate_trade_schema(const SchemaPayload& payload);
ValidationResult validate_config_schema(const SchemaPayload& payload);

}  // namespace hqt::util



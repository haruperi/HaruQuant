/**
FILE: src\engine\schema_validator.cpp

PURPOSE:
Defines schema_validator.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in schema_validator.cpp.
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
#include "util/schema_validator.hpp"

#include <algorithm>
#include <cctype>
#include <optional>
#include <regex>
#include <string>
#include <unordered_set>
#include <vector>

namespace hqt::util {
namespace {

std::string to_upper(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return text;
}

bool has_required_fields(const SchemaPayload& payload, const std::vector<std::string>& fields,
                         std::string& missing_field) {
    for (const auto& field : fields) {
        if (!payload.contains(field)) {
            missing_field = field;
            return false;
        }
    }
    return true;
}

std::optional<std::string> as_string(const SchemaPayload& payload, const std::string& key) {
    const auto it = payload.find(key);
    if (it == payload.end()) {
        return std::nullopt;
    }
    if (const auto* value = std::get_if<std::string>(&it->second)) {
        return *value;
    }
    return std::nullopt;
}

std::optional<double> as_number(const SchemaPayload& payload, const std::string& key) {
    const auto it = payload.find(key);
    if (it == payload.end()) {
        return std::nullopt;
    }
    if (const auto* value = std::get_if<double>(&it->second)) {
        return *value;
    }
    if (const auto* value = std::get_if<std::int64_t>(&it->second)) {
        return static_cast<double>(*value);
    }
    return std::nullopt;
}

std::optional<std::int64_t> as_int(const SchemaPayload& payload, const std::string& key) {
    const auto it = payload.find(key);
    if (it == payload.end()) {
        return std::nullopt;
    }
    if (const auto* value = std::get_if<std::int64_t>(&it->second)) {
        return *value;
    }
    return std::nullopt;
}

std::optional<bool> as_bool(const SchemaPayload& payload, const std::string& key) {
    const auto it = payload.find(key);
    if (it == payload.end()) {
        return std::nullopt;
    }
    if (const auto* value = std::get_if<bool>(&it->second)) {
        return *value;
    }
    return std::nullopt;
}

bool is_iso8601_utc(const std::string& value) {
    static const std::regex pattern(
        R"(^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$)");
    return std::regex_match(value, pattern);
}

ValidationResult ok_result(const std::string& message) {
    return ValidationResult{true, message};
}

ValidationResult error_result(const std::string& message) {
    return ValidationResult{false, message};
}

}  // namespace

ValidationResult validate_market_schema(const SchemaPayload& payload) {
    std::string missing_field;
    if (!has_required_fields(payload, {"symbol", "timestamp", "bid", "ask", "volume"}, missing_field)) {
        return error_result("missing required field: " + missing_field);
    }

    const auto symbol = as_string(payload, "symbol");
    if (!symbol || symbol->empty()) {
        return error_result("symbol must be a non-empty string");
    }

    const auto timestamp = as_string(payload, "timestamp");
    if (!timestamp || !is_iso8601_utc(*timestamp)) {
        return error_result("timestamp must be ISO-8601 UTC string (e.g. 2026-02-17T13:20:00Z)");
    }

    const auto bid = as_number(payload, "bid");
    const auto ask = as_number(payload, "ask");
    const auto volume = as_number(payload, "volume");
    if (!bid || !ask || !volume) {
        return error_result("bid, ask, and volume must be numeric");
    }
    if (*bid <= 0.0 || *ask <= 0.0) {
        return error_result("bid and ask must be > 0");
    }
    if (*ask < *bid) {
        return error_result("ask must be greater than or equal to bid");
    }
    if (*volume < 0.0) {
        return error_result("volume must be >= 0");
    }

    if (payload.contains("last")) {
        const auto last = as_number(payload, "last");
        if (!last || *last <= 0.0) {
            return error_result("last must be numeric and > 0 when provided");
        }
    }

    return ok_result("Market schema is valid");
}

ValidationResult validate_trade_schema(const SchemaPayload& payload) {
    std::string missing_field;
    if (!has_required_fields(payload, {"symbol", "side", "order_type", "volume"}, missing_field)) {
        return error_result("missing required field: " + missing_field);
    }

    const auto symbol = as_string(payload, "symbol");
    if (!symbol || symbol->empty()) {
        return error_result("symbol must be a non-empty string");
    }

    const auto side = as_string(payload, "side");
    if (!side) {
        return error_result("side must be a string");
    }
    const std::string side_normalized = to_upper(*side);
    if (side_normalized != "BUY" && side_normalized != "SELL") {
        return error_result("side must be BUY or SELL");
    }

    const auto order_type = as_string(payload, "order_type");
    if (!order_type) {
        return error_result("order_type must be a string");
    }
    static const std::unordered_set<std::string> kOrderTypes = {
        "MARKET", "LIMIT", "STOP", "STOP_LIMIT",
        "BUY", "SELL", "BUY_LIMIT", "SELL_LIMIT",
        "BUY_STOP", "SELL_STOP", "BUY_STOP_LIMIT", "SELL_STOP_LIMIT"};
    const std::string order_type_normalized = to_upper(*order_type);
    if (!kOrderTypes.contains(order_type_normalized)) {
        return error_result("order_type is not supported");
    }

    const auto volume = as_number(payload, "volume");
    if (!volume || *volume <= 0.0) {
        return error_result("volume must be numeric and > 0");
    }

    if (payload.contains("price")) {
        const auto value = as_number(payload, "price");
        if (!value || *value <= 0.0) {
            return error_result("price must be numeric and > 0");
        }
    }
    if (payload.contains("stop_loss")) {
        const auto value = as_number(payload, "stop_loss");
        if (!value || *value < 0.0) {
            return error_result("stop_loss must be numeric and >= 0");
        }
    }
    if (payload.contains("take_profit")) {
        const auto value = as_number(payload, "take_profit");
        if (!value || *value < 0.0) {
            return error_result("take_profit must be numeric and >= 0");
        }
    }
    if (payload.contains("magic")) {
        const auto value = as_int(payload, "magic");
        if (!value || *value < 0) {
            return error_result("magic must be integer and >= 0");
        }
    }
    if (payload.contains("deviation")) {
        const auto value = as_int(payload, "deviation");
        if (!value || *value < 0) {
            return error_result("deviation must be integer and >= 0");
        }
    }

    return ok_result("Trade schema is valid");
}

ValidationResult validate_config_schema(const SchemaPayload& payload) {
    std::string missing_field;
    if (!has_required_fields(payload,
                             {"mode", "logging.level", "risk.max_positions",
                              "risk.max_drawdown_pct", "risk.max_risk_per_trade_pct"},
                             missing_field)) {
        return error_result("missing required field: " + missing_field);
    }

    const auto mode = as_string(payload, "mode");
    if (!mode) {
        return error_result("mode must be a string");
    }
    const std::string normalized_mode = to_upper(*mode);
    if (normalized_mode != "BACKTEST" && normalized_mode != "PAPER" && normalized_mode != "LIVE") {
        return error_result("mode must be BACKTEST, PAPER, or LIVE");
    }

    const auto level = as_string(payload, "logging.level");
    if (!level) {
        return error_result("logging.level must be a string");
    }
    std::string normalized_level = to_upper(*level);
    if (normalized_level == "WARN") {
        normalized_level = "WARNING";
    } else if (normalized_level == "FATAL") {
        normalized_level = "CRITICAL";
    }
    static const std::unordered_set<std::string> kLevels = {
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"};
    if (!kLevels.contains(normalized_level)) {
        return error_result("invalid logging.level");
    }

    if (payload.contains("logging.stderr_enabled")) {
        const auto stderr_enabled = as_bool(payload, "logging.stderr_enabled");
        if (!stderr_enabled) {
            return error_result("logging.stderr_enabled must be a bool");
        }
    }

    const auto max_positions = as_int(payload, "risk.max_positions");
    if (!max_positions || *max_positions < 1) {
        return error_result("risk.max_positions must be integer and >= 1");
    }

    const auto max_drawdown = as_number(payload, "risk.max_drawdown_pct");
    const auto max_risk = as_number(payload, "risk.max_risk_per_trade_pct");
    if (!max_drawdown || *max_drawdown < 0.0 || *max_drawdown > 100.0) {
        return error_result("risk.max_drawdown_pct must be numeric in [0, 100]");
    }
    if (!max_risk || *max_risk < 0.0 || *max_risk > 100.0) {
        return error_result("risk.max_risk_per_trade_pct must be numeric in [0, 100]");
    }

    return ok_result("Config schema is valid");
}

}  // namespace hqt::util



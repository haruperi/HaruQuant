/**
 * @file schema_validator.hpp
 * @brief Lightweight C++ schema validation primitives for core payload contracts.
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


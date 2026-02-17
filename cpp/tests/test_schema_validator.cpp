/**
 * @file test_schema_validator.cpp
 * @brief Unit tests for C++ schema validation primitives.
 */

#include <gtest/gtest.h>

#include "util/schema_validator.hpp"

using namespace hqt::util;

TEST(SchemaValidatorTest, MarketSchemaValidPayload) {
    SchemaPayload payload{
        {"symbol", std::string("EURUSD")},
        {"timestamp", std::string("2026-02-17T13:30:00Z")},
        {"bid", 1.1000},
        {"ask", 1.1002},
        {"volume", 1234.0},
    };

    const ValidationResult result = validate_market_schema(payload);
    EXPECT_TRUE(result.ok);
}

TEST(SchemaValidatorTest, MarketSchemaRejectsAskBelowBid) {
    SchemaPayload payload{
        {"symbol", std::string("EURUSD")},
        {"timestamp", std::string("2026-02-17T13:30:00Z")},
        {"bid", 1.2000},
        {"ask", 1.1000},
        {"volume", 10.0},
    };

    const ValidationResult result = validate_market_schema(payload);
    EXPECT_FALSE(result.ok);
}

TEST(SchemaValidatorTest, TradeSchemaValidPayload) {
    SchemaPayload payload{
        {"symbol", std::string("EURUSD")},
        {"side", std::string("buy")},
        {"order_type", std::string("market")},
        {"volume", 0.1},
        {"price", 1.1001},
    };

    const ValidationResult result = validate_trade_schema(payload);
    EXPECT_TRUE(result.ok);
}

TEST(SchemaValidatorTest, TradeSchemaRejectsInvalidSide) {
    SchemaPayload payload{
        {"symbol", std::string("EURUSD")},
        {"side", std::string("hold")},
        {"order_type", std::string("market")},
        {"volume", 0.1},
    };

    const ValidationResult result = validate_trade_schema(payload);
    EXPECT_FALSE(result.ok);
}

TEST(SchemaValidatorTest, ConfigSchemaValidPayload) {
    SchemaPayload payload{
        {"mode", std::string("paper")},
        {"logging.level", std::string("warn")},
        {"risk.max_positions", static_cast<std::int64_t>(5)},
        {"risk.max_drawdown_pct", 20.0},
        {"risk.max_risk_per_trade_pct", 2.0},
        {"logging.stderr_enabled", true},
    };

    const ValidationResult result = validate_config_schema(payload);
    EXPECT_TRUE(result.ok);
}

TEST(SchemaValidatorTest, ConfigSchemaRejectsInvalidMode) {
    SchemaPayload payload{
        {"mode", std::string("demo")},
        {"logging.level", std::string("info")},
        {"risk.max_positions", static_cast<std::int64_t>(5)},
        {"risk.max_drawdown_pct", 20.0},
        {"risk.max_risk_per_trade_pct", 2.0},
    };

    const ValidationResult result = validate_config_schema(payload);
    EXPECT_FALSE(result.ok);
}


/**
FILE: tests\test_data_structures.cpp

PURPOSE:
Defines test_data_structures.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_data_structures.cpp.
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
#include "data/tick.hpp"
#include "data/bar.hpp"
#include "trading/symbol_info.hpp"

using namespace haruquant;

// ============================================================================
// Tick Tests
// ============================================================================

TEST(TickTest, DefaultConstruction) {
    Tick t;
    EXPECT_EQ(t.timestamp_us, 0);
    EXPECT_EQ(t.symbol_id, 0);
    EXPECT_EQ(t.bid, 0);
    EXPECT_EQ(t.ask, 0);
    EXPECT_EQ(t.bid_volume, 0);
    EXPECT_EQ(t.ask_volume, 0);
    EXPECT_EQ(t.spread_points, 0);
}

TEST(TickTest, ParameterizedConstruction) {
    Tick t(1000000, 1, 110520, 110523, 1000, 1000, 3);
    EXPECT_EQ(t.timestamp_us, 1000000);
    EXPECT_EQ(t.symbol_id, 1);
    EXPECT_EQ(t.bid, 110520);
    EXPECT_EQ(t.ask, 110523);
    EXPECT_EQ(t.bid_volume, 1000);
    EXPECT_EQ(t.ask_volume, 1000);
    EXPECT_EQ(t.spread_points, 3);
}

TEST(TickTest, IsValid) {
    Tick valid(1000000, 1, 110520, 110523, 1000, 1000, 3);
    EXPECT_TRUE(valid.is_valid());

    Tick invalid_zero_bid(1000000, 1, 0, 110523, 1000, 1000, 3);
    EXPECT_FALSE(invalid_zero_bid.is_valid());

    Tick invalid_ask_less_bid(1000000, 1, 110523, 110520, 1000, 1000, -3);
    EXPECT_FALSE(invalid_ask_less_bid.is_valid());
}

TEST(TickTest, MidPrice) {
    Tick t(1000000, 1, 110520, 110524, 1000, 1000, 4);
    EXPECT_EQ(t.mid_price(), 110522);  // (110520 + 110524) / 2
}

TEST(TickTest, CacheLineAlignment) {
    EXPECT_EQ(sizeof(Tick), 64);
    EXPECT_EQ(alignof(Tick), 64);
}

// ============================================================================
// Bar Tests
// ============================================================================

TEST(BarTest, DefaultConstruction) {
    Bar b;
    EXPECT_EQ(b.timestamp_us, 0);
    EXPECT_EQ(b.symbol_id, 0);
    EXPECT_EQ(b.timeframe, Timeframe::M1);
    EXPECT_EQ(b.open, 0);
    EXPECT_EQ(b.high, 0);
    EXPECT_EQ(b.low, 0);
    EXPECT_EQ(b.close, 0);
}

TEST(BarTest, ParameterizedConstruction) {
    Bar b(1000000, 1, Timeframe::H1, 110500, 110600, 110400, 110550, 1000, 5000, 10);
    EXPECT_EQ(b.timestamp_us, 1000000);
    EXPECT_EQ(b.symbol_id, 1);
    EXPECT_EQ(b.timeframe, Timeframe::H1);
    EXPECT_EQ(b.open, 110500);
    EXPECT_EQ(b.high, 110600);
    EXPECT_EQ(b.low, 110400);
    EXPECT_EQ(b.close, 110550);
}

TEST(BarTest, IsValid) {
    Bar valid(1000000, 1, Timeframe::M1, 110500, 110600, 110400, 110550, 1000, 5000, 10);
    EXPECT_TRUE(valid.is_valid());

    Bar invalid_high(1000000, 1, Timeframe::M1, 110500, 110450, 110400, 110550, 1000, 5000, 10);
    EXPECT_FALSE(invalid_high.is_valid());  // high < close

    Bar invalid_low(1000000, 1, Timeframe::M1, 110500, 110600, 110560, 110550, 1000, 5000, 10);
    EXPECT_FALSE(invalid_low.is_valid());  // low > close
}

TEST(BarTest, IsBullish) {
    Bar bullish(1000000, 1, Timeframe::M1, 110500, 110600, 110400, 110550, 1000, 5000, 10);
    EXPECT_TRUE(bullish.is_bullish());
    EXPECT_FALSE(bullish.is_bearish());
}

TEST(BarTest, IsBearish) {
    Bar bearish(1000000, 1, Timeframe::M1, 110550, 110600, 110400, 110500, 1000, 5000, 10);
    EXPECT_TRUE(bearish.is_bearish());
    EXPECT_FALSE(bearish.is_bullish());
}

TEST(BarTest, Range) {
    Bar b(1000000, 1, Timeframe::M1, 110500, 110600, 110400, 110550, 1000, 5000, 10);
    EXPECT_EQ(b.range(), 200);  // 110600 - 110400
}

TEST(BarTest, Body) {
    Bar bullish(1000000, 1, Timeframe::M1, 110500, 110600, 110400, 110550, 1000, 5000, 10);
    EXPECT_EQ(bullish.body(), 50);  // |110550 - 110500|

    Bar bearish(1000000, 1, Timeframe::M1, 110550, 110600, 110400, 110500, 1000, 5000, 10);
    EXPECT_EQ(bearish.body(), 50);  // |110500 - 110550|
}

TEST(BarTest, Alignment) {
    EXPECT_EQ(sizeof(Bar), 128);
    EXPECT_EQ(alignof(Bar), 64);
}

// ============================================================================
// Timeframe Tests
// ============================================================================

TEST(TimeframeTest, ToStringConversion) {
    EXPECT_EQ(timeframe_to_string(Timeframe::M1), "M1");
    EXPECT_EQ(timeframe_to_string(Timeframe::M5), "M5");
    EXPECT_EQ(timeframe_to_string(Timeframe::H1), "H1");
    EXPECT_EQ(timeframe_to_string(Timeframe::H4), "H4");
    EXPECT_EQ(timeframe_to_string(Timeframe::D1), "D1");
    EXPECT_EQ(timeframe_to_string(Timeframe::W1), "W1");
    EXPECT_EQ(timeframe_to_string(Timeframe::MN1), "MN1");
}

TEST(TimeframeTest, MinuteValues) {
    EXPECT_EQ(timeframe_minutes(Timeframe::M1), 1);
    EXPECT_EQ(timeframe_minutes(Timeframe::M5), 5);
    EXPECT_EQ(timeframe_minutes(Timeframe::M15), 15);
    EXPECT_EQ(timeframe_minutes(Timeframe::H1), 60);
    EXPECT_EQ(timeframe_minutes(Timeframe::H4), 240);
    EXPECT_EQ(timeframe_minutes(Timeframe::D1), 1440);
}

// ============================================================================
// SymbolInfo Tests
// ============================================================================

// NOTE: These tests have been disabled as they use the old deprecated API.
// SymbolInfo has been migrated to MT5 standard library API.
// See test_trade.cpp for comprehensive tests of the MT5-aligned implementation.

/*
TEST(SymbolInfoTest, DefaultConstruction) {
    SymbolInfo info;
    EXPECT_EQ(info.symbol_id, 0);
    EXPECT_EQ(info.digits, 0);
    EXPECT_EQ(info.trade_mode, TradeMode::FULL);
}

TEST(SymbolInfoTest, CanTrade) {
    SymbolInfo info;
    info.trade_mode = TradeMode::FULL;
    EXPECT_TRUE(info.can_trade());
    EXPECT_TRUE(info.can_trade_long());
    EXPECT_TRUE(info.can_trade_short());

    info.trade_mode = TradeMode::LONG_ONLY;
    EXPECT_TRUE(info.can_trade());
    EXPECT_TRUE(info.can_trade_long());
    EXPECT_FALSE(info.can_trade_short());

    info.trade_mode = TradeMode::DISABLED;
    EXPECT_FALSE(info.can_trade());
}

TEST(SymbolInfoTest, ValidateVolume) {
    SymbolInfo info;
    info.volume_min = 0.01;
    info.volume_max = 100.0;
    info.volume_step = 0.01;

    EXPECT_DOUBLE_EQ(info.validate_volume(0.005), 0.01);  // Clamped to min
    EXPECT_DOUBLE_EQ(info.validate_volume(150.0), 100.0);  // Clamped to max
    EXPECT_DOUBLE_EQ(info.validate_volume(1.234), 1.23);   // Rounded to step
}

TEST(SymbolInfoTest, FixedPointConversion) {
    SymbolInfo info;
    info.digits = 5;

    // Test double to fixed conversion
    EXPECT_EQ(info.double_to_fixed(1.10523), 110523);
    EXPECT_EQ(info.double_to_fixed(1.0), 100000);

    // Test fixed to double conversion
    EXPECT_DOUBLE_EQ(info.fixed_to_double(110523), 1.10523);
    EXPECT_DOUBLE_EQ(info.fixed_to_double(100000), 1.0);

    // Test round-trip
    double original = 1.10523;
    int64_t fixed = info.double_to_fixed(original);
    double recovered = info.fixed_to_double(fixed);
    EXPECT_DOUBLE_EQ(recovered, original);
}

TEST(SymbolInfoTest, FixedPointConversionGold) {
    SymbolInfo info;
    info.digits = 2;  // Gold typically has 2 digits

    EXPECT_EQ(info.double_to_fixed(2350.50), 235050);
    EXPECT_DOUBLE_EQ(info.fixed_to_double(235050), 2350.50);
}
*/


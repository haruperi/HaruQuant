/**
FILE: tests\test_utilities.cpp

PURPOSE:
Defines test_utilities.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_utilities.cpp.
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
#include "util/fixed_point.hpp"
#include "util/timestamp.hpp"
#include "util/random.hpp"
#include "engine/event.hpp"
#include "data/bar.hpp"
#include <cmath>

using namespace hqt;

// ============================================================================
// FixedPoint Tests
// ============================================================================

TEST(FixedPointTest, FromDoubleConversion) {
    // 5 digits precision
    EXPECT_EQ(FixedPoint::from_double(1.10523, 5), 110523);
    EXPECT_EQ(FixedPoint::from_double(1.0, 5), 100000);
    EXPECT_EQ(FixedPoint::from_double(0.00001, 5), 1);

    // 2 digits precision (gold)
    EXPECT_EQ(FixedPoint::from_double(2350.50, 2), 235050);
    EXPECT_EQ(FixedPoint::from_double(2350.00, 2), 235000);
}

TEST(FixedPointTest, ToDoubleConversion) {
    // 5 digits precision
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(110523, 5), 1.10523);
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(100000, 5), 1.0);

    // 2 digits precision
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(235050, 2), 2350.50);
}

TEST(FixedPointTest, RoundTrip) {
    // Test round-trip conversion maintains precision
    double original = 1.10523;
    int64_t fixed = FixedPoint::from_double(original, 5);
    double recovered = FixedPoint::to_double(fixed, 5);
    EXPECT_DOUBLE_EQ(recovered, original);
}

TEST(FixedPointTest, Addition) {
    int64_t a = FixedPoint::from_double(1.1, 5);
    int64_t b = FixedPoint::from_double(2.2, 5);
    int64_t result = FixedPoint::add(a, b);
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(result, 5), 3.3);
}

TEST(FixedPointTest, Subtraction) {
    int64_t a = FixedPoint::from_double(5.5, 5);
    int64_t b = FixedPoint::from_double(2.2, 5);
    int64_t result = FixedPoint::subtract(a, b);
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(result, 5), 3.3);
}

TEST(FixedPointTest, MultiplyInt) {
    int64_t value = FixedPoint::from_double(1.5, 5);
    int64_t result = FixedPoint::multiply_int(value, 3);
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(result, 5), 4.5);
}

TEST(FixedPointTest, DivideInt) {
    int64_t value = FixedPoint::from_double(9.0, 5);
    int64_t result = FixedPoint::divide_int(value, 3);
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(result, 5), 3.0);
}

TEST(FixedPointTest, MultiplyFixedPoint) {
    // 1.5 * 2.0 = 3.0
    int64_t a = FixedPoint::from_double(1.5, 5);
    int64_t b = FixedPoint::from_double(2.0, 5);
    int64_t result = FixedPoint::multiply(a, b, 5, 5, 5);
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(result, 5), 3.0);
}

TEST(FixedPointTest, DivideFixedPoint) {
    // 9.0 / 3.0 = 3.0
    int64_t a = FixedPoint::from_double(9.0, 5);
    int64_t b = FixedPoint::from_double(3.0, 5);
    int64_t result = FixedPoint::divide(a, b, 5, 5, 5);
    EXPECT_DOUBLE_EQ(FixedPoint::to_double(result, 5), 3.0);
}

TEST(FixedPointTest, DivideByZero) {
    int64_t a = FixedPoint::from_double(9.0, 5);
    int64_t result_int = FixedPoint::divide_int(a, 0);
    EXPECT_EQ(result_int, 0);

    int64_t result_fixed = FixedPoint::divide(a, 0, 5, 5, 5);
    EXPECT_EQ(result_fixed, 0);
}

TEST(FixedPointTest, Abs) {
    int64_t positive = FixedPoint::from_double(5.5, 5);
    int64_t negative = FixedPoint::from_double(-5.5, 5);

    EXPECT_EQ(FixedPoint::abs(positive), positive);
    EXPECT_EQ(FixedPoint::abs(negative), positive);
}

TEST(FixedPointTest, Compare) {
    int64_t a = FixedPoint::from_double(1.1, 5);
    int64_t b = FixedPoint::from_double(2.2, 5);

    EXPECT_EQ(FixedPoint::compare(a, b), -1);
    EXPECT_EQ(FixedPoint::compare(b, a), 1);
    EXPECT_EQ(FixedPoint::compare(a, a), 0);
}

TEST(FixedPointTest, MinMax) {
    int64_t a = FixedPoint::from_double(1.1, 5);
    int64_t b = FixedPoint::from_double(2.2, 5);

    EXPECT_EQ(FixedPoint::min(a, b), a);
    EXPECT_EQ(FixedPoint::max(a, b), b);
}

TEST(FixedPointTest, Clamp) {
    int64_t value = FixedPoint::from_double(5.0, 5);
    int64_t min_val = FixedPoint::from_double(2.0, 5);
    int64_t max_val = FixedPoint::from_double(8.0, 5);

    EXPECT_EQ(FixedPoint::clamp(value, min_val, max_val), value);

    int64_t too_low = FixedPoint::from_double(1.0, 5);
    EXPECT_EQ(FixedPoint::clamp(too_low, min_val, max_val), min_val);

    int64_t too_high = FixedPoint::from_double(10.0, 5);
    EXPECT_EQ(FixedPoint::clamp(too_high, min_val, max_val), max_val);
}

// ============================================================================
// Timestamp Tests
// ============================================================================

TEST(TimestampTest, NowUs) {
    int64_t now1 = Timestamp::now_us();
    int64_t now2 = Timestamp::now_us();

    EXPECT_GT(now1, 0);
    EXPECT_GE(now2, now1);  // Time should advance
}

TEST(TimestampTest, Conversions) {
    // Seconds
    EXPECT_EQ(Timestamp::to_seconds(1'000'000), 1);
    EXPECT_EQ(Timestamp::from_seconds(1), 1'000'000);

    // Milliseconds
    EXPECT_EQ(Timestamp::to_milliseconds(1'000'000), 1'000);
    EXPECT_EQ(Timestamp::from_milliseconds(1'000), 1'000'000);
}

TEST(TimestampTest, FloorOperations) {
    // 2026-02-10 14:35:27.123456
    int64_t ts = 1'770'672'927'123'456LL;

    // Floor to minute: 2026-02-10 14:35:00.000000
    int64_t floor_min = Timestamp::floor_to_minute(ts);
    EXPECT_EQ(floor_min % (60LL * 1'000'000LL), 0);

    // Floor to hour: 2026-02-10 14:00:00.000000
    int64_t floor_hour = Timestamp::floor_to_hour(ts);
    EXPECT_EQ(floor_hour % (3600LL * 1'000'000LL), 0);

    // Floor to day: 2026-02-10 00:00:00.000000
    int64_t floor_day = Timestamp::floor_to_day(ts);
    EXPECT_EQ(floor_day % (86400LL * 1'000'000LL), 0);
}

TEST(TimestampTest, ISO8601Conversion) {
    // Create a known timestamp: 2026-02-10 14:30:00.123456 UTC
    int64_t ts = Timestamp::from_seconds(1'770'733'800) + 123'456;

    std::string iso = Timestamp::to_iso8601(ts);
    EXPECT_NE(iso.find("2026-02-10"), std::string::npos);
    EXPECT_NE(iso.find("14:30:00"), std::string::npos);
    EXPECT_NE(iso.find("123456"), std::string::npos);
}

TEST(TimestampTest, ToDate) {
    // 2026-02-10
    int64_t ts = Timestamp::from_seconds(1'770'733'800);
    std::string date = Timestamp::to_date(ts);
    EXPECT_EQ(date, "2026-02-10");
}

// ============================================================================
// SeededRNG Tests
// ============================================================================

TEST(SeededRNGTest, Determinism) {
    SeededRNG rng1(12345);
    SeededRNG rng2(12345);

    // Same seed should produce same sequence
    for (int i = 0; i < 100; ++i) {
        EXPECT_EQ(rng1.next_int(1, 100), rng2.next_int(1, 100));
    }
}

TEST(SeededRNGTest, DifferentSeeds) {
    SeededRNG rng1(12345);
    SeededRNG rng2(54321);

    // Different seeds should produce different sequences
    int matches = 0;
    for (int i = 0; i < 100; ++i) {
        if (rng1.next_int(1, 100) == rng2.next_int(1, 100)) {
            ++matches;
        }
    }
    EXPECT_LT(matches, 10);  // Should have very few matches
}

TEST(SeededRNGTest, Reset) {
    SeededRNG rng(12345);

    int64_t first = rng.next_int(1, 100);
    (void)rng.next_int(1, 100);  // Advance state
    rng.reset();  // Reset to initial seed
    int64_t after_reset = rng.next_int(1, 100);

    EXPECT_EQ(first, after_reset);
}

TEST(SeededRNGTest, NextIntRange) {
    SeededRNG rng(12345);

    for (int i = 0; i < 1000; ++i) {
        int64_t value = rng.next_int(10, 20);
        EXPECT_GE(value, 10);
        EXPECT_LE(value, 20);
    }
}

TEST(SeededRNGTest, NextDoubleRange) {
    SeededRNG rng(12345);

    for (int i = 0; i < 1000; ++i) {
        double value = rng.next_double(0.0, 1.0);
        EXPECT_GE(value, 0.0);
        EXPECT_LT(value, 1.0);
    }
}

TEST(SeededRNGTest, NextBool) {
    SeededRNG rng(12345);

    int true_count = 0;
    for (int i = 0; i < 10000; ++i) {
        if (rng.next_bool(0.5)) {
            ++true_count;
        }
    }

    // Should be approximately 50% (within 5% tolerance)
    EXPECT_GT(true_count, 4500);
    EXPECT_LT(true_count, 5500);
}

TEST(SeededRNGTest, GetSeed) {
    uint64_t seed = 12345;
    SeededRNG rng(seed);
    EXPECT_EQ(rng.get_seed(), seed);
}

// ============================================================================
// Event Tests
// ============================================================================

TEST(EventTest, DefaultConstruction) {
    Event e;
    EXPECT_EQ(e.timestamp_us, 0);
    EXPECT_EQ(e.type, EventType::CUSTOM);
}

TEST(EventTest, TickEventCreation) {
    Event e = Event::tick(1000000, 1);
    EXPECT_EQ(e.timestamp_us, 1000000);
    EXPECT_EQ(e.type, EventType::TICK);
    EXPECT_EQ(e.data.tick_data.symbol_id, 1);
}

TEST(EventTest, BarCloseEventCreation) {
    Event e = Event::bar_close(1000000, 1, static_cast<uint16_t>(Timeframe::H1));
    EXPECT_EQ(e.timestamp_us, 1000000);
    EXPECT_EQ(e.type, EventType::BAR_CLOSE);
    EXPECT_EQ(e.data.bar_data.symbol_id, 1);
    EXPECT_EQ(e.data.bar_data.timeframe, static_cast<uint16_t>(Timeframe::H1));
}

TEST(EventTest, OrderTriggerEventCreation) {
    Event e = Event::order_trigger(1000000, 12345);
    EXPECT_EQ(e.timestamp_us, 1000000);
    EXPECT_EQ(e.type, EventType::ORDER_TRIGGER);
    EXPECT_EQ(e.data.order_data.order_ticket, 12345);
}

TEST(EventTest, TimerEventCreation) {
    Event e = Event::timer(1000000, 99);
    EXPECT_EQ(e.timestamp_us, 1000000);
    EXPECT_EQ(e.type, EventType::TIMER);
    EXPECT_EQ(e.data.timer_data.timer_id, 99);
}

TEST(EventTest, Comparison) {
    Event early(1000000, EventType::TICK);
    Event late(2000000, EventType::TICK);

    // For min-heap, earlier events should be "greater" (to be on top)
    EXPECT_TRUE(early > late);
    EXPECT_FALSE(late > early);
}

TEST(EventTest, Equality) {
    Event e1 = Event::tick(1000000, 1);
    Event e2 = Event::tick(1000000, 1);
    Event e3 = Event::tick(2000000, 1);

    EXPECT_TRUE(e1 == e2);
    EXPECT_FALSE(e1 == e3);
}

TEST(EventTest, ComparatorForPriorityQueue) {
    Event early(1000000, EventType::TICK);
    Event late(2000000, EventType::TICK);

    EventComparator comp;

    // Comparator should order so earliest events come first
    EXPECT_FALSE(comp(early, late));  // early should NOT come after late
    EXPECT_TRUE(comp(late, early));   // late SHOULD come after early
}


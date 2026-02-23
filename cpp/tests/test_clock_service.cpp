/**
FILE: tests\test_clock_service.cpp

PURPOSE:
Defines test_clock_service.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_clock_service.cpp.
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
#include "engine/clock_service.hpp"

using namespace hqt;

TEST(ClockServiceTest, EventTimeModeUsesObservedEventTime) {
    ClockService clock(ClockMode::EVENT_TIME);
    clock.observe_event_time(1'000'000);
    clock.observe_event_time(2'000'000);
    clock.observe_processing_time(9'000'000);

    EXPECT_EQ(clock.canonical_now(), 2'000'000);
}

TEST(ClockServiceTest, ProcessingTimeModeUsesObservedProcessingTime) {
    ClockService clock(ClockMode::PROCESSING_TIME);
    clock.observe_event_time(10'000'000);
    clock.observe_processing_time(2'500'000);
    clock.observe_processing_time(3'000'000);

    EXPECT_EQ(clock.canonical_now(), 3'000'000);
}

TEST(ClockServiceTest, TimeDoesNotMoveBackwards) {
    ClockService clock(ClockMode::EVENT_TIME);
    clock.observe_event_time(5'000'000);
    clock.observe_event_time(4'000'000);

    EXPECT_EQ(clock.canonical_now(), 5'000'000);
}

TEST(ClockServiceTest, NormalizeUtcWithOffsetAndDst) {
    ClockService clock(
        ClockMode::EVENT_TIME,
        TimezoneNormalizationPolicy::APPLY_OFFSET,
        DstPolicy::APPLY_ONE_HOUR
    );

    const int64_t local_time = 10LL * 3600LL * 1'000'000LL;  // 10:00 local
    const int64_t utc_time = clock.normalize_to_utc(local_time, 120, true);  // UTC+2 + DST
    EXPECT_EQ(utc_time, 7LL * 3600LL * 1'000'000LL);  // 07:00 UTC
}

TEST(ClockServiceTest, RejectNonUtcWhenConfigured) {
    ClockService clock(
        ClockMode::EVENT_TIME,
        TimezoneNormalizationPolicy::REJECT_NON_UTC,
        DstPolicy::NO_DST
    );

    EXPECT_THROW(
        static_cast<void>(clock.normalize_to_utc(1'000'000, 60, false)),
        std::invalid_argument
    );
}



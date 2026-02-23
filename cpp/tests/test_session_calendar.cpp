/**
FILE: tests\test_session_calendar.cpp

PURPOSE:
Defines test_session_calendar.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_session_calendar.cpp.
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
#include "engine/session_calendar.hpp"

#include <optional>

using namespace hqt;

namespace {

SymbolInfo make_symbol(uint32_t id, const std::string& name, int digits, double point, double contract_size) {
    SymbolInfo s;
    s.SetSymbolId(id);
    s.Name(name);
    s.SetDigits(digits);
    s.SetPoint(point);
    s.SetContractSize(contract_size);
    return s;
}

}  // namespace

TEST(SessionCalendarTest, SymbolMetadataMappingUsesSymbolInfo) {
    SessionCalendar cal;
    cal.register_session("fx_core", {{1, 9 * 60, 17 * 60}});

    const auto eurusd = make_symbol(1, "EURUSD", 5, 0.00001, 100000.0);
    cal.register_symbol(eurusd, "fx_core");

    const auto info = cal.get_symbol_info(1);
    ASSERT_TRUE(info.has_value());
    EXPECT_EQ(info->Digits(), 5);
    EXPECT_DOUBLE_EQ(info->Point(), 0.00001);
    EXPECT_DOUBLE_EQ(info->ContractSize(), 100000.0);
}

TEST(SessionCalendarTest, MarketOpenWithinTradingWindow) {
    SessionCalendar cal;
    cal.register_session("fx_core", {{1, 9 * 60, 17 * 60}});
    cal.register_symbol(make_symbol(1, "EURUSD", 5, 0.00001, 100000.0), "fx_core");

    // Monday 2026-01-05 10:00:00 UTC
    const int64_t monday_10utc = 1767607200000000LL;
    EXPECT_TRUE(cal.is_market_open(1, monday_10utc));

    // Monday 2026-01-05 18:00:00 UTC (outside)
    const int64_t monday_18utc = 1767636000000000LL;
    EXPECT_FALSE(cal.is_market_open(1, monday_18utc));
}

TEST(SessionCalendarTest, HolidayBlocksTrading) {
    SessionCalendar cal;
    cal.register_session("fx_core", {{1, 9 * 60, 17 * 60}});
    cal.add_holiday("fx_core", 2026, 1, 5);  // Monday holiday
    cal.register_symbol(make_symbol(1, "EURUSD", 5, 0.00001, 100000.0), "fx_core");

    const int64_t monday_10utc = 1767607200000000LL;
    const auto decision = cal.can_trade_symbol(1, monday_10utc);
    EXPECT_FALSE(decision.allowed);
    EXPECT_EQ(decision.reason, SessionBlockReason::HOLIDAY);
}

TEST(SessionCalendarTest, DstOffsetAffectsSessionGate) {
    SessionCalendar cal(
        120,  // UTC+2 base
        DstPolicy::APPLY_ONE_HOUR
    );
    // Local session 09:00-10:00 local
    cal.register_session("fx_local", {{1, 9 * 60, 10 * 60}});
    cal.register_symbol(make_symbol(2, "GBPUSD", 5, 0.00001, 100000.0), "fx_local");

    // Monday 06:30 UTC with +2 and DST(+1) => local 09:30 -> open
    const int64_t monday_0630utc = 1767594600000000LL;
    EXPECT_TRUE(cal.is_market_open(2, monday_0630utc, true));

    // Same timestamp without DST => local 08:30 -> closed
    EXPECT_FALSE(cal.is_market_open(2, monday_0630utc, false));
}

TEST(SessionCalendarTest, NextOpenTimeFindsFutureWindow) {
    SessionCalendar cal;
    cal.register_session("fx_core", {{1, 9 * 60, 17 * 60}});
    cal.register_symbol(make_symbol(1, "EURUSD", 5, 0.00001, 100000.0), "fx_core");

    // Monday 08:00 UTC -> next open should be Monday 09:00 UTC (+1h)
    const int64_t monday_08utc = 1767600000000000LL;
    const auto next = cal.next_open_time(1, monday_08utc);
    ASSERT_TRUE(next.has_value());
    EXPECT_EQ(*next, monday_08utc + 3600LL * 1000000LL);
}

TEST(SessionCalendarTest, UnknownSymbolReturnsReason) {
    SessionCalendar cal;
    const auto decision = cal.can_trade_symbol(999, 1767607200000000LL);
    EXPECT_FALSE(decision.allowed);
    EXPECT_EQ(decision.reason, SessionBlockReason::UNKNOWN_SYMBOL);
}



# Session Calendar (IP-07)

## Overview

`SessionCalendar` is implemented in:

- `cpp/include/engine/session_calendar.hpp`

It provides:
- trading session hour rules by weekday
- holiday blocking by session
- timezone offset + DST policy handling
- symbol metadata/session mapping via existing `SymbolInfo`

## Symbol Metadata Mapping

`SessionCalendar` reuses `SymbolInfo` from:

- `cpp/include/trading/symbol_info.hpp`

Mapped metadata includes:
- `Digits()`
- `Point()`
- `ContractSize()`
- `SymbolId()`

## Basic Setup

```cpp
#include "engine/session_calendar.hpp"

hqt::SessionCalendar cal(0, hqt::DstPolicy::NO_DST);  // UTC, no DST
cal.register_session("fx_core", {
    {1, 9 * 60, 17 * 60},  // Monday 09:00-17:00
    {2, 9 * 60, 17 * 60},  // Tuesday
});
cal.add_holiday("fx_core", 2026, 1, 1);

hqt::SymbolInfo eurusd;
eurusd.SetSymbolId(1);
eurusd.SetDigits(5);
eurusd.SetPoint(0.00001);
eurusd.SetContractSize(100000.0);

cal.register_symbol(eurusd, "fx_core");
```

## Runtime Gate

Use `can_trade_symbol(...)` for strategy/live-controller restrictions:

```cpp
auto gate = cal.can_trade_symbol(symbol_id, timestamp_us, /*is_dst=*/false);
if (!gate.allowed) {
    // reason: UNKNOWN_SYMBOL / UNKNOWN_SESSION / HOLIDAY / OUTSIDE_SESSION
}
```

Shortcut:

```cpp
bool open = cal.is_market_open(symbol_id, timestamp_us);
```

## Next Open Time

```cpp
auto next_open = cal.next_open_time(symbol_id, timestamp_us);
if (next_open.has_value()) {
    // schedule next attempt at *next_open
}
```


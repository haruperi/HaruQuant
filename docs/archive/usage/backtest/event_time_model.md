# Event Time Model (IP-06)

## Overview

IP-06 introduces:
- `ClockService` (`cpp/include/engine/clock_service.hpp`)
- `EventSequencer` (`cpp/include/engine/event_sequencer.hpp`)

These provide canonical time handling and deterministic event ordering for backtests/live simulation.

## ClockService

`ClockService` supports:
- `ClockMode::EVENT_TIME`
- `ClockMode::PROCESSING_TIME`

Typical usage:

```cpp
#include "engine/clock_service.hpp"

hqt::ClockService clock(hqt::ClockMode::EVENT_TIME);
clock.observe_event_time(1'700'000'000'000'000);
auto now = clock.canonical_now();
```

Timezone/DST normalization:

```cpp
hqt::ClockService clock(
    hqt::ClockMode::EVENT_TIME,
    hqt::TimezoneNormalizationPolicy::APPLY_OFFSET,
    hqt::DstPolicy::APPLY_ONE_HOUR
);

// Convert local timestamp to UTC
int64_t utc_ts = clock.normalize_to_utc(local_ts, 120, true);
```

## EventSequencer

`EventSequencer` provides deterministic ordering for:
- merged multi-stream event flow
- per-symbol event flow

Ordering keys:
1. `timestamp_us` asc
2. `symbol_id` asc
3. `stream_id` asc
4. insertion sequence asc

Typical usage:

```cpp
#include "engine/event_sequencer.hpp"

hqt::EventSequencer seq;
seq.push(1, hqt::Event::tick(1000000, 1));
seq.push(2, hqt::Event::tick(1000000, 2));

auto merged = seq.ordered_merged();
auto eurusd = seq.ordered_for_symbol(1);
```


# ReplayClock (IP-08)

## Overview

`ReplayClock` is implemented in:

- `cpp/include/engine/replay_clock.hpp`

It provides deterministic replay-time progression with:
- `pause()`
- `resume()`
- `advance()`
- `step_by_bar(n)`

It also exposes deterministic timeline signatures and snapshot state for replay incident reproduction.

## Basic Usage

```cpp
#include "engine/replay_clock.hpp"

hqt::ReplayClock clock({1000, 2000, 3000, 4000});
clock.pause();
clock.step_by_bar(1);  // debug step while paused
clock.resume();

while (!clock.finished()) {
    auto t = clock.advance();
    if (!t.has_value()) {
        break;
    }
    // process bar/event at *t
}
```

## Incident Reproduction Hook

Use deterministic state and signature snapshots:

```cpp
auto state = clock.state();
auto sig = clock.timeline_signature();
```

Persist `state` + `sig` alongside run artifacts to make replay debugging reproducible.

## Python Replay Consistency Hook

Replay event sequence fingerprinting helper:

- `apps/simulation/replay_hooks.py`

Functions:
- `replay_fingerprint(events)`
- `compare_replay_runs(baseline, candidate)`


# Event Ordering Performance (IP-06)

Date: 2026-02-17

## Scope

Benchmark evidence for deterministic event/time engine changes:
- `ClockService`
- `EventSequencer`

## Build and Test Command

Legacy `backend/scripts/build_cpp.py` helper removed during cleanup.

## Result Snapshot

- C++ test suite executed: `278` tests
- Passed: `278`
- Failed: `0`
- Total reported test time: `8.08 sec`

## Relevant IP-06 Tests

- `ClockServiceTest.*` (`cpp/tests/test_clock_service.cpp`)
- `EventSequencerTest.*` (`cpp/tests/test_event_sequencer.cpp`)

These validate deterministic ordering and canonical clock behavior under event-time/processing-time modes.


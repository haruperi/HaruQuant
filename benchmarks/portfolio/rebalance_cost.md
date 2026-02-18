# Rebalance Cost Notes (IP-26)

## Scope
Initial benchmark notes for allocation/rebalance/exposure primitives in C++.

## Current Status
- Functional baseline implemented for:
  - allocation models: equal-weight, risk-parity, custom
  - exposure constraints: symbol, strategy, asset, total
  - rebalance triggers: scheduled interval + drift threshold
- Dedicated micro-benchmark harness will be added with live-controller integration work.

## Operational Guidance
- Exposure constraint application currently uses deterministic clipping + optional total scaling.
- Rebalance checks are lightweight map comparisons suitable for pre-run or periodic control loops.

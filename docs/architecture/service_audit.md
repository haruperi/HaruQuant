# HaruQuant Service Audit

This document is the working map for cleaning up the current service layer before
moving toward the intended root `services` architecture.

The current service layer lives under `backend/services`, not under
root `services`. The top-level `haruquant` package still looks like an older,
smaller library surface, and the `backend` package still contains the old
control-plane implementation.

## Current Snapshot

- Legacy service root: `backend/services`
- New service root: `services`
- Migrated utility root: `services/utils` from `backend/common`
- Python files: about 388
- Code size: about 2.95 MB
- Remaining legacy service folders: none under `backend/services`
- New root service folders: 10 domain/support folders under `services`
- Main issue: the old `backend/services` root has been removed. Remaining
  cleanup should focus on API/app boundaries and reducing heavy imports inside
  the new owners.

## Target Domain Shape

The long-term target is to make services read like business capabilities:

- `data`
- `indicator`
- `strategy`
- `simulation`
- `analytics`
- `risk`
- `execution`
- `reporting`
- `memory`
- `audit`
- `cost`

Supporting concepts such as approval, policy, evidence, reconciliation, safety,
shadow mode, and monitoring should become submodules of those domains unless they
have a strong reason to remain top-level services.

## Current Folder Map

| Current folder | Current purpose | Suggested destination |
| --- | --- | --- |
| `ai_chat` | Chat gateway, conversation context, page action planning, CEO chat orchestration | Move toward `agents` or `agents/orchestration`; keep deterministic helpers in services only if needed |
| `analytics` | Metrics, returns, drawdowns, ratios, distributions, statistical tests | `services/analytics` |
| `approval` | Approval request/vote/override lifecycle | Governance submodule, likely under `audit`, `risk`, or `strategy` depending on use |
| `audit` | Replay, export, signing, legal hold, integrity manifests | `services/audit` |
| `cost` | Cost enforcement | `services/cost` |
| `evidence` | Evidence bundle assembly, manifest, storage | Likely `services/audit/evidence` or `services/strategy/evidence` |
| `execution` | Execution intent assembly, trade validation, readiness, receipts, send service | `services/execution` |
| `features` | Feature pipeline and leakage controls | Likely `services/data/features` or `services/research/features` |
| `indicators` | Technical indicators and validation helpers | `services/indicator` |
| `live_trading` | Live trading config, engine, session, risk integration, notifications | Split between `services/execution`, `services/risk`, and app runtime |
| `market_data` | Dukascopy data loading, instrument map, validation, manipulation | `services/data` |
| `modeling` | Unsupervised modeling and feature-set research | Likely `services/analytics/modeling` or research area |
| `monitoring` | Observation ingestion, incidents, stale state, tool health, workflow timeout | Likely `services/audit/monitoring` or platform support |
| `notification` | Email, SMS, Telegram, templates, notification manager | App/platform support; not a core trading service |
| `optimization` | Monte Carlo, walk-forward, parameter search, parallel execution | `services/simulation/optimization` or `services/analytics/optimization` |
| `performance` | Latency monitor and hot snapshot cache | Platform support or `services/audit/performance` |
| `policy` | Compliance policy models and resolver | Governance support; used by risk/execution/approval |
| `portfolio` | Portfolio proposals, impacts, contributions, snapshots | `services/risk/portfolio` or `services/analytics/portfolio` |
| `proposals` | Proposal readiness, state transitions, hypothesis transformation | Strategy lifecycle support |
| `reconciliation` | Broker truth comparison, persistence, retry guard, startup loader | `services/execution/reconciliation` |
| `research` | Edge research, market structure, scorecards, seasonality, null models | Research/analytics area, not generic service root |
| `risk` | Risk decisions, snapshots, restrictions, validity, request assembly | Fold into canonical `services/risk` |
| `risk_engine` | Large quantitative risk engine with limits, metrics, models, regimes, simulation | Canonical `services/risk` after careful migration |
| `safety` | Kill switch state machine, recovery approval, audit | `services/risk/kill_switch` or `services/execution/safety` |
| `shadow` | Shadow execution/feed/reporting | `services/execution/shadow` |
| `simulation` | Simulator sessions, engines, reporting, data prep, vectorized/event-driven backtests | `services/simulation` |
| `strategy` | Strategy base, adapter, catalog, storage, baselines, blueprint design | `services/strategy` |
| `strategy_gov` | Promotion, lifecycle, registry, retirement, suspension | `services/strategy/lifecycle` or `services/strategy/governance` |

## Biggest Coupling Points

These folders are widely imported or central enough that they should be moved
slowly, with direct import cutovers and no compatibility wrappers:

- `risk_engine`
- `strategy`
- `execution`
- `ai_chat`
- `simulation`

The current `backend/services/__init__.py` is also a major coupling point because
it re-exports many unrelated domains from one package. Long-term, this should stop
being the main import surface.

## Large Files To Split

These files are likely creating a lot of the spaghetti feeling:

- `backend/services/market_data/dukascopy_instruments.py`
- `services/simulation/session_runtime.py`
- `services/research/market_structure.py`
- `backend/agents/chat/ai_chat/ai_gateway.py`
- `services/execution/core.py`
- `backend/services/market_data/data_validator.py`
- `services/simulation/engine.py`
- `services/execution/trade.py`
- `services/execution/trade_validators.py`
- `services/optimization/monte_carlo.py`

## Refactor Principles

1. Move one domain at a time.
2. Remove old service packages after each migration.
3. Prefer service facades named `service.py` for external callers.
4. Move pure schemas and DTOs into `schemas`.
5. Keep agents out of deterministic service internals.
6. Keep API routes thin; they should orchestrate service calls, not own logic.
7. Do not combine live broker side effects with analytics, research, or simulation.

## Recommended Migration Order

1. `analytics`
   - Low side-effect risk.
   - Maps cleanly to the target architecture.
   - Good first proof that the migration pattern works.

2. `data`
   - Clear domain boundary.
   - Needs file splitting, especially instrument metadata and validation.

3. `indicator`
   - Clear boundary and mostly pure functions.

4. `strategy`
   - Important domain, but currently imported widely.
   - Move behind a stable `service.py` facade.

5. `simulation`
   - Big but conceptually clear.
   - Should move after data, indicators, strategy, and analytics are stable.

6. `execution`
   - High-risk because of live/order semantics.
   - Needs careful separation of models, validation, routing, receipts, and bridges.

7. `risk` + `risk_engine`
   - Highest complexity.
   - Should become one canonical `risk` domain after the surrounding services settle.

8. Governance/support cleanup
   - Fold `approval`, `policy`, `evidence`, `safety`, `shadow`,
     `reconciliation`, `monitoring`, and `performance` into their owning domains.

9. `ai_chat`
   - Move agent orchestration into `agents`.
   - Keep only deterministic context or retrieval services under `services` if still
     needed.

## First Practical Step

Start with the foundational utility and data packages.

Completed:

- `backend/common` -> `services/utils`
- `backend/services/market_data` -> `services/data`
- `backend/services/indicators` -> `services/indicator`
- `backend/services/strategy` -> `services/strategy`
- `backend/services/simulation` -> `services/simulation`
- `backend/services/analytics` -> `services/analytics`
- `backend/services/execution` -> `services/execution`
- `backend/services/risk` + `backend/services/risk_engine` -> `services/risk`
- `backend/services/live_trading` -> split across `services/execution/live`
  and `services/risk/live`
- `backend/services/optimization` -> `services/optimization`
- `backend/services/research` -> `services/research`
- `backend/services/notification` -> `services/notification`
- `backend/services/approval` -> `services/execution/approval`
- `backend/services/shadow` -> `services/execution/shadow`
- `backend/services/reconciliation` -> `services/execution/reconciliation`
- `backend/services/monitoring` -> `services/execution/monitoring`
- `backend/services/performance` -> `services/execution/performance`
- `backend/services/safety` -> `services/risk/safety`
- `backend/services/evidence` -> `services/strategy/evidence`
- `backend/services/policy` -> `services/risk/policy`
- `backend/services/compliance_rollout.py` -> `services/risk/policy/compliance_rollout.py`
- `backend/services/portfolio` -> `services/risk/portfolio`
- `backend/services/proposals` -> `services/strategy/proposals`
- `backend/services/strategy_gov` -> `services/strategy/governance`
- `backend/services/audit` -> `services/strategy/evidence/audit`
- `backend/services/cost` -> `services/execution/cost`
- `backend/services/features` -> `services/data/features`
- `backend/services/modeling` -> `services/research/modeling`
- `backend/services/ai_chat` -> `backend/agents/chat/ai_chat`
- `backend/services/tool_executor.py` -> `backend/agents/chat/ai_chat/tool_executor.py`
- `backend/services/trade_action_governor.py` -> `services/execution/trade_action_governor.py`

Next candidates:

- `api` and `app` boundaries should follow once the service graph is stable.

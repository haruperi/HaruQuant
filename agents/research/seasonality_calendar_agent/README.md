# Seasonality and Calendar Agent

## Purpose

Analyzes session, calendar, day-of-week, month-end, holiday, and seasonal behavior.

## Department

Research Department

## Inputs

- symbol or symbols
- timeframe or timeframes
- data_window
- research_question
- context_revision
- evidence_refs

## Outputs

- evidence
- optional LLM analysis proposal
- deterministic decision
- audit metadata
- `seasonality_calendar_report` artifact

## Allowed Actions

- `analyze_seasonality`
- `flag_calendar_risk`
- `summarize_session_patterns`
- `save_seasonality_report`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `get_session_calendar`
- `get_holiday_calendar`
- `calculate_seasonality_profile`
- `save_seasonality_calendar_report`

## Tests

Run:

```bash
pytest agents/research/seasonality_calendar_agent/tests/
```

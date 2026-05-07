# Technical Analyst Agent

## Purpose

Analyzes price structure, indicators, trend, momentum, volatility, support, and resistance.

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
- `technical_analysis_report` artifact

## Allowed Actions

- `analyze_price_structure`
- `classify_trend_state`
- `summarize_indicators`
- `flag_technical_risks`
- `save_technical_report`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `get_ohlcv_data`
- `calculate_indicators`
- `detect_support_resistance`
- `detect_price_patterns`
- `save_technical_analysis_report`

## Tests

Run:

```bash
pytest agents/research/technical_analyst_agent/tests/
```

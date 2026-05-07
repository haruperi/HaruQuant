# Cross-Asset / Intermarket Agent

## Purpose

Analyzes related markets, correlations, divergences, intermarket pressure, and exposure context.

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
- `cross_asset_intermarket_report` artifact

## Allowed Actions

- `analyze_cross_asset_context`
- `flag_correlation_shift`
- `flag_intermarket_divergence`
- `save_intermarket_report`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `get_cross_asset_data`
- `calculate_correlations`
- `detect_intermarket_divergence`
- `save_cross_asset_report`

## Tests

Run:

```bash
pytest agents/research/cross_asset_intermarket_agent/tests/
```

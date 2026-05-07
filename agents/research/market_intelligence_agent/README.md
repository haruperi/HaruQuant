# Market Intelligence Agent

## Purpose

Studies market regimes, liquidity, volatility, session behavior, spread behavior, and symbol personality.

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
- `market_intelligence_report` artifact

## Allowed Actions

- `summarize_market_context`
- `classify_market_regime`
- `flag_spread_risk`
- `flag_volatility_risk`
- `flag_liquidity_risk`
- `recommend_research_strategy_families`
- `save_market_report`

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
- `get_tick_data`
- `get_spread_history`
- `get_session_calendar`
- `get_volatility_regime_history`
- `get_symbol_metadata`
- `save_market_intelligence_report`

## Tests

Run:

```bash
pytest agents/research/market_intelligence_agent/tests/
```

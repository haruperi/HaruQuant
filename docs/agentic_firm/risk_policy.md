# HaruQuant Agentic AI Trading Firm — Standard Prop Firm Risk Policy

**Document:** `risk_policy.md`  
**Target path:** `docs/agentic_firm/risk_policy.md`  
**Version:** 1.2.0 — Standard Prop Firm Compliance Edition  
**Status:** Draft for Board Review  
**Owner:** Human Board / Haruperi  
**Applies to:** HaruQuant multi-agent research, backtesting, paper trading, prop-firm challenge simulation, funded-account simulation, and future live/prop-firm trading workflows  
**Effective date:** 2026-05-03  
**Primary profile:** Standard Prop Firm Compliance Profile  

---

## 1. Purpose

This Risk Policy defines the mandatory risk controls for the HaruQuant Agentic AI Trading Firm when operating under a standard prop-firm environment.

The policy exists to ensure that HaruQuant can use multi-agent LLM systems for research, strategy creation, backtesting, monitoring, paper trading, challenge trading, funded-account simulation, and future live trading without allowing any agent, strategy, or execution service to violate prop-firm-style risk rules.

The core principle is:

> **HaruQuant must stop trading before the prop firm stops the account.**

This policy is binding on:

1. Human Board / Haruperi.
2. CEO Agent.
3. Planner / Orchestrator Agent.
4. Research Agents.
5. Strategy Creator Agent.
6. Strategy Reviewer Agent.
7. Codegen Agent.
8. Backtest Agent.
9. Optimization Comparator Agent.
10. Robustness Agent.
11. Statistical Validation Agent.
12. Risk Reviewer Agent.
13. Portfolio Manager Agent.
14. Execution Planner Agent.
15. Paper Execution Agent.
16. Live Execution Agent.
17. Performance Reporter Agent.
18. Audit Agent.
19. Cost Optimizer Agent.
20. RiskGovernor service.
21. Kill Switch service.
22. Any future HaruQuant autonomous or semi-autonomous agent.

LLM agents may propose, explain, analyze, compare, and recommend. Only deterministic risk services may size, approve, reject, block, or halt trades.

---

## 2. Standard Prop Firm Compliance Profile

HaruQuant uses one default profile for prop-firm trading.

This profile is intentionally simple and conservative. It is designed to work across typical prop-firm challenge and funded-account conditions without creating multiple confusing rule modes.

```yaml
standard_prop_firm_profile:
  name: "standard_prop_firm_compliance"
  max_daily_loss_pct: 5.0
  max_total_loss_pct: 10.0
  max_total_loss_type: "static_from_initial_balance"
  monthly_profit_target_pct: 10.0
  news_restriction_minutes_before: 10
  news_restriction_minutes_after: 10
  overnight_holding_allowed: false
  weekend_holding_allowed: false
  best_day_rule_pct: 50.0
  automated_trading_allowed: true
  human_approval_required_for_live_activation: true
```

### 2.1 External rule limits

These are the hard prop-firm-style limits:

| Rule | Standard limit | Meaning |
|---|---:|---|
| Maximum daily loss | 5% | Account equity must never fall more than 5% from the relevant daily reference balance. |
| Maximum total loss | 10% | Account equity must never fall below 90% of the initial account balance. |
| Profit target | 10% per month / cycle | Target profit is 10% of initial balance for the active evaluation or monthly cycle. |
| News restriction | 10 minutes before to 10 minutes after | No new trades, trade closures, stop-loss hits, or take-profit hits should occur inside restricted high-impact news windows. |
| Overnight holding | Restricted | Positions should be closed before the broker/platform daily rollover cutoff. |
| Weekend holding | Restricted | Positions should be closed before the weekend cutoff. |
| Best Day Rule | 50% | The best positive trading day must not contribute more than 50% of total positive-day profit. |

### 2.2 Internal HaruQuant safety buffers

HaruQuant must stop before reaching external limits.

| External rule | External breach level | HaruQuant warning | HaruQuant critical | HaruQuant hard stop |
|---|---:|---:|---:|---:|
| Daily loss | 5.0% | 2.5% | 3.5% | 4.0% |
| Total loss | 10.0% | 5.0% | 7.5% | 8.5% |
| Monthly drawdown | Internal rule | 3.0% | 5.0% | 6.0% |
| Portfolio drawdown | Internal rule | 4.0% | 6.5% | 8.0% |
| Best Day Rule | 50.0% | 40.0% | 45.0% | 50.0% |

The RiskGovernor must use internal HaruQuant stop levels for live blocking, not only the external prop-firm breach levels.

---

## 3. Authority Hierarchy

Risk authority follows this order:

```text
Human Board
→ Constitution
→ Risk Policy
→ Standard Prop Firm Compliance Profile
→ RiskGovernor
→ Kill Switch
→ Execution Bridge
→ Agents
```

Rules:

1. The Human Board may approve or reject live trading.
2. The Human Board may change risk thresholds.
3. LLM agents may not change risk thresholds.
4. LLM agents may not disable the RiskGovernor.
5. LLM agents may not disable the Kill Switch.
6. LLM agents may not bypass audit logging.
7. Live orders may only pass through the Execution Bridge after RiskGovernor approval.
8. Any conflict between an agent recommendation and this Risk Policy is resolved in favor of this Risk Policy.

---

## 4. Capital Reference Definitions

### 4.1 Initial balance

The **initial balance** is the starting balance assigned to the prop-firm account, challenge account, funded-account simulation, or paper account.

Example:

```yaml
initial_balance: 100000.00
```

### 4.2 Daily reference balance

The **daily reference balance** is the account balance or equity reference used to calculate the daily loss limit at the start of the broker/platform trading day.

The RiskGovernor must store a daily snapshot:

```yaml
daily_reference:
  date: "YYYY-MM-DD"
  balance_at_day_start: 100000.00
  equity_at_day_start: 100000.00
  max_allowed_daily_loss_amount: 5000.00
  internal_hard_stop_daily_loss_amount: 4000.00
```

### 4.3 Equity

Equity includes:

1. Balance.
2. Floating profit/loss.
3. Commissions.
4. Swaps.
5. Fees.

All loss-limit rules must be evaluated using equity, not only closed balance.

### 4.4 Static total loss floor

The standard profile uses a static total-loss floor.

Formula:

```text
minimum_allowed_equity = initial_balance × (1 - max_total_loss_pct)
```

For a 100,000 account:

```text
minimum_allowed_equity = 100,000 × (1 - 0.10) = 90,000
```

HaruQuant internal hard stop:

```text
internal_minimum_equity = initial_balance × (1 - 0.085)
```

For a 100,000 account:

```text
internal_minimum_equity = 100,000 × 0.915 = 91,500
```

---

## 5. Maximum Risk Per Trade

### 5.1 Default risk per trade

HaruQuant default risk per trade is:

```yaml
max_risk_per_trade_pct: 0.25
```

This means a single trade may not risk more than 0.25% of initial account balance or current equity, whichever produces the smaller risk amount.

### 5.2 Absolute trade-risk cap

The maximum possible risk per trade is:

```yaml
absolute_max_risk_per_trade_pct: 0.50
```

No agent, strategy, optimization run, or execution path may exceed this cap.

### 5.3 Reduced-risk states

Risk per trade must be reduced automatically when account conditions deteriorate.

| Condition | Max risk per trade |
|---|---:|
| Normal state | 0.25% |
| Daily loss > 1.5% | 0.15% |
| Daily loss > 2.5% | 0.10% |
| Daily loss > 3.5% | No new trades unless reducing exposure |
| Total drawdown > 5.0% | 0.10% |
| Total drawdown > 7.5% | No new trades |

### 5.4 Position-size formula

For stop-loss-based trades:

```text
position_size = risk_amount / stop_loss_value_per_unit
```

Where:

```text
risk_amount = min(initial_balance, current_equity) × risk_pct
```

If no valid stop loss exists, the RiskGovernor must either:

1. Reject the trade; or
2. Apply a synthetic risk distance based on volatility, ADR, ATR, or worst-case model.

No live trade may be approved without a measurable risk amount.

---

## 6. Maximum Daily Loss

### 6.1 External daily loss rule

The standard prop-firm maximum daily loss is:

```yaml
max_daily_loss_pct: 5.0
```

The account must never lose more than 5% in a single trading day, including open floating losses, closed losses, commissions, swaps, and fees.

### 6.2 HaruQuant internal daily stop

HaruQuant must stop earlier:

```yaml
internal_daily_warning_pct: 2.5
internal_daily_critical_pct: 3.5
internal_daily_hard_stop_pct: 4.0
external_daily_breach_pct: 5.0
```

### 6.3 Daily loss actions

| Daily loss level | Action |
|---:|---|
| 0.0% to 1.5% | Normal trading allowed. |
| > 1.5% | Reduce max risk per trade. |
| > 2.5% | Warning state; block new high-risk entries. |
| > 3.5% | Critical state; only risk-reducing trades allowed. |
| >= 4.0% | Hard stop; block all new trades and notify Human Board. |
| >= 5.0% | External breach state; should never be reached. |

### 6.4 Daily loss calculation

```text
daily_loss_pct = (daily_reference_equity - current_equity) / initial_balance × 100
```

The RiskGovernor must evaluate daily loss before every order, after every fill, on every equity update, and on every broker heartbeat.

---

## 7. Maximum Weekly Loss

### 7.1 Weekly loss rule

HaruQuant internal weekly loss limit:

```yaml
max_weekly_loss_pct: 6.0
weekly_warning_pct: 3.0
weekly_critical_pct: 4.5
weekly_hard_stop_pct: 6.0
```

### 7.2 Weekly loss actions

| Weekly loss level | Action |
|---:|---|
| > 3.0% | Reduce risk per trade by 50%. |
| > 4.5% | Block new strategies and high-correlation trades. |
| >= 6.0% | Stop new trading until Human Board review. |

### 7.3 Weekly loss formula

```text
weekly_loss_pct = (week_start_equity - current_equity) / initial_balance × 100
```

---

## 8. Maximum Monthly Drawdown

### 8.1 Monthly drawdown rule

HaruQuant internal monthly drawdown limit:

```yaml
max_monthly_drawdown_pct: 6.0
monthly_warning_pct: 3.0
monthly_critical_pct: 5.0
monthly_hard_stop_pct: 6.0
```

### 8.2 Monthly drawdown actions

| Monthly drawdown level | Action |
|---:|---|
| > 3.0% | Reduce all strategy allocations. |
| > 5.0% | Pause weakest live strategy. |
| >= 6.0% | Stop all new trading until Board review. |

### 8.3 Monthly profit target rule

The standard prop-firm target is:

```yaml
monthly_profit_target_pct: 10.0
```

HaruQuant must treat the 10% profit target as a target, not as permission to overtrade.

Rules:

1. Agents may not force trades to reach the monthly target.
2. Risk per trade may not be increased merely because the account is below target.
3. The RiskGovernor may reduce trading when target pressure creates overtrading risk.
4. The Performance Reporter must show progress toward the target without recommending reckless volume.

---

## 9. Maximum Portfolio Drawdown

### 9.1 Portfolio drawdown rule

HaruQuant internal portfolio drawdown limit:

```yaml
max_portfolio_drawdown_pct: 8.0
portfolio_warning_pct: 4.0
portfolio_critical_pct: 6.5
portfolio_hard_stop_pct: 8.0
```

### 9.2 Portfolio drawdown actions

| Portfolio drawdown | Action |
|---:|---|
| > 4.0% | Reduce total portfolio risk. |
| > 6.5% | Pause new strategy deployments. |
| >= 8.0% | Stop all new trading and require Board review. |

### 9.3 Portfolio drawdown formula

```text
portfolio_drawdown_pct = (portfolio_equity_high_watermark - current_equity) / portfolio_equity_high_watermark × 100
```

---

## 10. Maximum Symbol Exposure

### 10.1 Symbol exposure rule

No single symbol may dominate portfolio risk.

```yaml
max_symbol_risk_pct_of_account: 1.00
max_symbol_nominal_exposure_pct_of_equity: 25.0
max_open_positions_per_symbol: 2
```

### 10.2 Symbol exposure actions

The RiskGovernor must reject a new trade if it would cause:

1. Total risk on one symbol to exceed 1.00% of account equity.
2. Nominal exposure on one symbol to exceed 25% of account equity.
3. More than 2 simultaneous open positions on one symbol.
4. Duplicate strategy entries that are effectively the same directional trade.

### 10.3 Symbol grouping examples

The following are treated as single-symbol clusters for exposure purposes:

| Cluster | Instruments |
|---|---|
| Gold | XAUUSD, GOLD, broker-specific gold CFDs |
| Silver | XAGUSD, SILVER |
| Euro dollar | EURUSD, EURUSD micro/mini variants |
| Nasdaq | NAS100, US100, USTEC, NQ CFD variants |

---

## 11. Maximum Correlated Exposure

### 11.1 Correlation rule

HaruQuant must limit correlated open risk.

```yaml
max_pairwise_correlation_for_new_trade: 0.70
preferred_pairwise_correlation_for_new_trade: 0.50
max_correlated_cluster_risk_pct: 1.50
correlation_lookback_bars: 500
```

### 11.2 Correlation actions

The RiskGovernor must:

1. Calculate rolling correlations between candidate symbol returns and open-position symbols.
2. Calculate directional correlation impact.
3. Reject trades that push cluster risk above the maximum.
4. Prefer portfolio-diversifying trades over redundant trades.
5. Treat same-direction highly correlated trades as risk concentration.

### 11.3 Correlation examples

| Example | Risk treatment |
|---|---|
| Long EURUSD and long GBPUSD | Potential USD-short cluster. |
| Short EURUSD and long USDCHF | Potential USD-long cluster. |
| Long XAUUSD and short USDJPY | May share USD weakness exposure. |
| Long NAS100 and long US500 | Equity-index risk cluster. |

---

## 12. Maximum USD-Cluster Exposure

### 12.1 USD-cluster rule

Because Forex and metals often create hidden USD exposure, HaruQuant must track aggregate USD directional risk.

```yaml
max_usd_cluster_risk_pct: 2.00
preferred_usd_cluster_risk_pct: 1.25
max_usd_cluster_nominal_exposure_pct_of_equity: 50.0
```

### 12.2 USD exposure calculation

The RiskGovernor must classify each trade as:

1. USD long.
2. USD short.
3. USD neutral or mixed.

Examples:

| Trade | USD cluster |
|---|---|
| Long EURUSD | USD short |
| Short EURUSD | USD long |
| Long GBPUSD | USD short |
| Short USDJPY | USD short |
| Long USDCHF | USD long |
| Long XAUUSD | Usually USD short / anti-USD risk |

### 12.3 USD-cluster rejection

Reject a new trade if:

1. It would push USD-cluster risk above 2.00%.
2. It would create excessive same-direction USD exposure.
3. It would combine with news-event risk in a major USD release window.
4. It would expose the account to a dollar shock that could threaten the daily-loss limit.

---

## 13. Maximum Number of Simultaneous Positions

### 13.1 Account-level position limit

```yaml
max_simultaneous_positions_total: 8
preferred_simultaneous_positions_total: 5
max_pending_orders_total: 10
```

### 13.2 Strategy-level position limit

```yaml
max_positions_per_strategy: 2
max_pending_orders_per_strategy: 3
```

### 13.3 Position limit actions

The RiskGovernor must reject any trade that would exceed:

1. Account-level open-position limit.
2. Symbol-level open-position limit.
3. Strategy-level open-position limit.
4. Pending-order limit.

---

## 14. Maximum Strategy Allocation

### 14.1 Allocation rule

No single live strategy may control too much portfolio risk.

```yaml
max_live_strategy_risk_allocation_pct: 1.00
preferred_live_strategy_risk_allocation_pct: 0.50
max_paper_strategy_risk_allocation_pct: 0.50
```

### 14.2 Strategy allocation actions

The Portfolio Manager and RiskGovernor must reject allocation increases if:

1. The strategy has insufficient paper-trading evidence.
2. The strategy recently breached internal drawdown thresholds.
3. The strategy is highly correlated with existing live strategies.
4. The strategy would become the dominant driver of portfolio P&L.
5. The strategy depends on one exceptional trading day.

---

## 15. Maximum Live Strategies

### 15.1 Live strategy limit

```yaml
max_live_strategies: 5
preferred_live_strategies: 3
```

### 15.2 Live strategy activation requirements

A strategy may become live only after:

1. Formal strategy specification.
2. Strategy review approval.
3. Backtest pass.
4. Robustness test pass.
5. Statistical validation pass or Board-approved exception.
6. Paper trading pass.
7. Risk review pass.
8. Portfolio review pass.
9. Human Board approval.
10. RiskGovernor registration.
11. Audit registration.

### 15.3 Live strategy removal

A live strategy must be paused or retired if:

1. It breaches internal drawdown rules.
2. It materially deviates from expected behavior.
3. It fails execution-quality checks.
4. It creates excessive correlation.
5. It violates consistency rules.
6. It causes repeated RiskGovernor blocks.

---

## 16. Maximum Paper Strategies

### 16.1 Paper strategy limit

```yaml
max_paper_strategies: 20
preferred_paper_strategies: 10
```

### 16.2 Paper strategy admission requirements

A strategy may enter paper trading only after:

1. Formal strategy specification.
2. Strategy review approval.
3. Code review pass.
4. Unit tests pass.
5. Backtest result exists.
6. Basic risk review exists.
7. It does not duplicate an existing paper/live strategy.

### 16.3 Paper strategy removal

A paper strategy must be removed, revised, or archived if:

1. It fails to trade for too long without valid reason.
2. It violates its own expected behavior.
3. It exceeds drawdown thresholds.
4. It has poor execution quality.
5. It depends on restricted news windows.
6. It contributes no portfolio diversification.

---

## 17. Spread Filters

### 17.1 Spread rule

HaruQuant must reject trades when spreads are abnormal.

```yaml
spread_filter:
  enabled: true
  max_spread_multiplier_vs_median: 2.0
  max_spread_percent_of_atr: 10.0
  block_if_spread_data_missing: true
```

### 17.2 Symbol-specific spread thresholds

Example defaults:

```yaml
symbol_spread_limits:
  EURUSD:
    max_spread_points: 15
  GBPUSD:
    max_spread_points: 20
  USDJPY:
    max_spread_points: 20
  XAUUSD:
    max_spread_points: 50
  NAS100:
    max_spread_points: 300
```

These values must be adjusted to match the actual broker symbol settings, digits, contract specification, and historical spread behavior.

### 17.3 Spread actions

Reject a trade if:

1. Current spread exceeds symbol limit.
2. Current spread exceeds 2× recent median spread.
3. Spread data is missing.
4. Spread spike occurs near news.
5. Spread makes expected reward/risk invalid.

---

## 18. Slippage Filters

### 18.1 Slippage rule

HaruQuant must monitor and limit execution slippage.

```yaml
slippage_filter:
  enabled: true
  max_expected_slippage_points: 5
  max_actual_slippage_points: 10
  max_slippage_percent_of_risk: 10.0
  block_after_consecutive_bad_fills: 3
```

### 18.2 Slippage actions

| Event | Action |
|---|---|
| Expected slippage too high | Reject new order. |
| Actual slippage exceeds limit | Log execution warning. |
| 3 bad fills in a row | Pause strategy. |
| Slippage threatens daily loss | Trigger critical risk state. |
| Slippage data missing | Block live execution. |

### 18.3 Slippage reporting

The Performance Reporter must include:

1. Average slippage by symbol.
2. Average slippage by strategy.
3. Worst fill.
4. Slippage as percentage of expected risk.
5. Broker/session slippage patterns.

---

## 19. News-Event Blocks

### 19.1 News restriction window

Standard prop-firm profile:

```yaml
news_event_blocks:
  enabled: true
  minutes_before_high_impact_event: 10
  minutes_after_high_impact_event: 10
  apply_to_new_entries: true
  apply_to_exits: true
  apply_to_stop_loss_hits: true
  apply_to_take_profit_hits: true
  apply_to_pending_order_triggers: true
```

### 19.2 Restricted event types

The news block applies to high-impact events including:

1. Central bank rate decisions.
2. Monetary policy statements.
3. CPI / inflation releases.
4. Non-farm payrolls.
5. Unemployment releases.
6. GDP releases.
7. Retail sales releases.
8. Major central bank speeches.
9. Unexpected emergency policy statements.
10. Major geopolitical shock events if detected by the News/Event Risk Agent.

### 19.3 Affected instruments

The event block applies to all instruments directly affected by the event currency or asset class.

Examples:

| Event | Affected instruments |
|---|---|
| USD NFP | USD pairs, XAUUSD, US indices |
| FOMC | USD pairs, XAUUSD, US indices, crypto if enabled |
| ECB rate decision | EUR pairs, European indices |
| BOE rate decision | GBP pairs, UK indices |
| CPI release | Currency pairs and indices linked to the releasing country |

### 19.4 News block actions

During restricted windows, HaruQuant must:

1. Block new entries.
2. Block new pending orders.
3. Cancel unprotected pending orders if required.
4. Avoid opening positions likely to close inside the window.
5. Alert the Human Board if an existing position may be exposed.
6. Prevent strategies from intentionally exploiting news slippage, gaps, or latency.

### 19.5 Pre-news flattening rule

Because overnight and news restrictions are strict in this standard profile, HaruQuant should flatten positions on affected instruments before the news window unless a Board-approved exception exists.

Default:

```yaml
pre_news_flatten_minutes_before: 15
```

---

## 20. Overnight and Weekend Restrictions

### 20.1 Overnight restriction

Standard profile:

```yaml
overnight_holding_allowed: false
```

HaruQuant must close or avoid opening positions that are expected to remain open beyond the broker/platform rollover cutoff.

Default rule:

```yaml
close_before_daily_rollover_minutes: 30
```

### 20.2 Weekend restriction

Standard profile:

```yaml
weekend_holding_allowed: false
```

HaruQuant must close positions before the weekend cutoff.

Default rule:

```yaml
close_before_weekend_minutes: 120
```

### 20.3 Overnight/weekend actions

The Execution Agent must:

1. Block new entries near rollover if the trade cannot reasonably close in time.
2. Close open positions before daily rollover cutoff.
3. Close open positions before weekend cutoff.
4. Cancel pending orders before weekend cutoff.
5. Alert Human Board if any position cannot be closed.
6. Log all forced closures.

---

## 21. Forbidden Trading Practices

HaruQuant agents, strategies, and execution services must never engage in forbidden prop-firm-style practices.

### 21.1 Forbidden execution behavior

The following are prohibited:

1. Latency arbitrage.
2. Price-feed arbitrage.
3. Broker error exploitation.
4. Platform-freeze exploitation.
5. Gap exploitation designed to bypass fair execution.
6. Toxic order flooding.
7. Hyperactive order submission.
8. Intentional server overload.
9. Quote-stuffing behavior.
10. Duplicate order spam.
11. Abusive scalping dependent on execution defects.
12. Strategies that require unrealistic fills.

### 21.2 Forbidden risk behavior

The following are prohibited:

1. Martingale without explicit Board approval and hard risk cap.
2. Unlimited grid trading.
3. Averaging down without bounded total risk.
4. Increasing size after losses to recover drawdown.
5. Increasing size merely to reach a profit target.
6. Opening highly correlated positions to hide concentration.
7. Splitting one oversized trade into many smaller trades to bypass limits.
8. Taking trades that can breach daily loss if all stops are hit.
9. Trading without measurable risk.

### 21.3 Forbidden account behavior

The following are prohibited:

1. Copying identical trades across multiple accounts without allocation approval.
2. Opposite-direction hedging across accounts to manipulate outcomes.
3. Coordinated group trading that violates prop-firm conditions.
4. Using another trader's signals without disclosure and validation.
5. Using strategies that cannot be independently explained, tested, and audited.
6. Trading from unapproved broker accounts.
7. Changing account credentials or broker connection settings without audit.

### 21.4 Forbidden agent behavior

Agents must never:

1. Disable the RiskGovernor.
2. Disable the Kill Switch.
3. Change risk thresholds.
4. Place live orders directly.
5. Hide losses.
6. Delete backtest evidence.
7. Delete audit logs.
8. Override prop-firm restrictions.
9. Continue trading after hard-stop conditions.
10. Misclassify live trades as paper trades.

---

## 22. EA and Automation Compliance

### 22.1 Automation allowed only inside controls

Automated trading is allowed only when the following controls are active:

1. RiskGovernor.
2. Kill Switch.
3. Execution Bridge.
4. Audit Logger.
5. Broker heartbeat monitor.
6. Spread filter.
7. Slippage filter.
8. News-event filter.
9. Overnight/weekend filter.
10. Strategy lifecycle registry.

### 22.2 EA request throttling

HaruQuant must prevent automation from overwhelming the broker or platform.

```yaml
automation_limits:
  max_order_requests_per_minute: 20
  max_order_modifications_per_minute: 30
  max_account_queries_per_second: 5
  max_symbol_queries_per_second: 10
  block_duplicate_order_requests: true
  min_seconds_between_identical_orders: 10
```

### 22.3 Automation heartbeat

The Execution Bridge must maintain heartbeat checks.

```yaml
heartbeat:
  broker_heartbeat_interval_seconds: 5
  max_missed_heartbeats: 3
  action_on_missed_heartbeats: "block_new_orders"
```

### 22.4 EA failure rules

If automation behaves abnormally, HaruQuant must:

1. Stop new orders.
2. Cancel unsafe pending orders if policy requires.
3. Notify Human Board.
4. Write incident report.
5. Require Board approval before resuming live automation.

Automation abnormality includes:

1. Repeated failed orders.
2. Repeated rejected orders.
3. Unexpected lot size.
4. Unexpected symbol.
5. Unexpected side.
6. Duplicate orders.
7. Orders without strategy ID.
8. Orders without risk approval ID.
9. Orders without audit log entry.

---

## 23. Allocation Compliance

### 23.1 Account allocation rule

HaruQuant must treat prop-firm allocation as a portfolio-level constraint.

```yaml
allocation_compliance:
  max_accounts_per_strategy: 1
  max_total_live_prop_firm_capital_multiplier: 1.0
  duplicate_strategy_across_accounts_allowed: false
  cross_account_hedging_allowed: false
  copy_trading_allowed_without_board_approval: false
```

### 23.2 Strategy duplication rule

A strategy is considered duplicated if it has substantially similar:

1. Entry logic.
2. Exit logic.
3. Symbol universe.
4. Timeframe.
5. Trade timing.
6. Risk behavior.
7. Equity curve.
8. Signal correlation.

Duplicate strategies may not be used to bypass allocation, risk, or consistency constraints.

### 23.3 Allocation approval

The Human Board must approve:

1. New prop-firm account activation.
2. New live strategy allocation.
3. Increasing live allocation.
4. Running the same strategy on multiple accounts.
5. Using copy trading.
6. Using external signals.
7. Connecting new broker accounts.

### 23.4 Allocation monitoring

The Portfolio Manager must report:

1. Total allocated simulated prop-firm capital.
2. Live strategy allocation.
3. Paper strategy allocation.
4. Strategy overlap.
5. Signal correlation across accounts.
6. Account-level drawdown.
7. Aggregate drawdown risk.

---

## 24. Consistency Rule and Best Day Rule

### 24.1 Best Day Rule

HaruQuant uses a 50% Best Day Rule.

```yaml
consistency_rule:
  enabled: true
  best_day_rule_pct: 50.0
  warning_pct: 40.0
  critical_pct: 45.0
  hard_limit_pct: 50.0
```

The best positive trading day must not contribute more than 50% of total positive-day profit.

### 24.2 Best Day Rule formula

```text
best_day_score = best_positive_day_profit / total_positive_days_profit × 100
```

Where:

1. `best_positive_day_profit` is the largest profit from a single positive trading day.
2. `total_positive_days_profit` is the sum of all positive trading days.
3. Losing days are not included in the denominator.

### 24.3 Example

If the best day earns 6,000 and total positive-day profit is 10,000:

```text
best_day_score = 6,000 / 10,000 × 100 = 60%
```

This fails the 50% Best Day Rule.

If the best day earns 4,000 and total positive-day profit is 10,000:

```text
best_day_score = 4,000 / 10,000 × 100 = 40%
```

This passes but enters HaruQuant warning state.

### 24.4 Consistency actions

| Best Day Score | Action |
|---:|---|
| < 35% | Healthy consistency. |
| 35% to 40% | Monitor. |
| > 40% | Warning; avoid high-size trades. |
| > 45% | Critical; reduce risk and prioritize steady trading. |
| >= 50% | Do not claim target passed; continue only with strict risk control or stop for review. |

### 24.5 Profit target and consistency interaction

A strategy or account may reach the 10% profit target but still fail consistency if one day contributes too much profit.

The Performance Reporter must show both:

1. Profit target progress.
2. Best Day Rule score.

The CEO Agent may not recommend passing, scaling, or live promotion unless both the profit target and consistency rule are satisfied.

---

## 25. Broker-Disconnect Behavior

### 25.1 Disconnect rule

If broker connectivity is unstable, HaruQuant must protect the account before seeking opportunity.

```yaml
broker_disconnect_policy:
  block_new_orders_on_disconnect: true
  cancel_pending_orders_on_critical_disconnect: true
  max_missed_heartbeats: 3
  critical_disconnect_seconds: 30
  require_board_review_after_critical_disconnect: true
```

### 25.2 Disconnect states

| State | Condition | Action |
|---|---|---|
| Healthy | Heartbeat normal | Trading allowed. |
| Warning | 1 missed heartbeat | Monitor. |
| Degraded | 2 missed heartbeats | Block new high-risk orders. |
| Disconnected | 3 missed heartbeats | Block all new orders. |
| Critical | > 30 seconds disconnected | Trigger incident workflow. |

### 25.3 Reconnect rules

After reconnecting:

1. Refresh account info.
2. Refresh open positions.
3. Refresh pending orders.
4. Refresh latest ticks.
5. Recalculate equity.
6. Recalculate daily loss.
7. Recalculate total loss.
8. Recalculate exposure.
9. Re-enable trading only if RiskGovernor confirms safe state.
10. Require Board review after critical disconnect.

---

## 26. Kill Switch Rules

### 26.1 Kill Switch authority

The Kill Switch is a deterministic service. It may stop trading without LLM approval.

No agent may override the Kill Switch.

### 26.2 Kill Switch triggers

The Kill Switch must trigger if any of the following occur:

1. Daily loss reaches 4.0% internal hard stop.
2. Total loss reaches 8.5% internal hard stop.
3. Weekly loss reaches 6.0%.
4. Monthly drawdown reaches 6.0%.
5. Portfolio drawdown reaches 8.0%.
6. Broker disconnect becomes critical.
7. RiskGovernor becomes unavailable.
8. Audit Logger becomes unavailable.
9. Execution Bridge sends order without risk approval ID.
10. Live order size exceeds approved size.
11. Strategy sends unregistered symbol.
12. Strategy sends duplicate order spam.
13. Spread exceeds emergency threshold.
14. Slippage exceeds emergency threshold.
15. News filter detects restricted high-impact event exposure.
16. Overnight/weekend restriction would be violated.
17. Best Day Score reaches or exceeds 50% while target/passing status is being evaluated.
18. Human Board manually triggers kill switch.

### 26.3 Kill Switch actions

Depending on severity, the Kill Switch may:

1. Block all new orders.
2. Block only new risk-increasing orders.
3. Cancel pending orders.
4. Pause one strategy.
5. Pause all live strategies.
6. Disable live trading globally.
7. Notify Human Board.
8. Create incident report.
9. Require Board review before resuming.

### 26.4 Position-closing policy

The Kill Switch must not automatically close all open positions unless the Constitution or Human Board has approved that behavior.

Default action:

```yaml
kill_switch_default_position_action: "block_new_orders_and_alert"
```

Emergency action:

```yaml
kill_switch_emergency_position_action: "close_positions_if_required_to_prevent_rule_breach"
```

---

## 27. RiskGovernor Enforcement Points

The RiskGovernor must evaluate rules at these points:

1. Before strategy activation.
2. Before paper trading admission.
3. Before live trading admission.
4. Before every trade proposal.
5. Before every order placement.
6. Before every order modification.
7. Before every position increase.
8. After every fill.
9. After every close.
10. After every equity update.
11. After every broker heartbeat.
12. Before every daily rollover.
13. Before every weekend cutoff.
14. Before every known high-impact news event.
15. Before every Board approval request.

---

## 28. Agent-Specific Risk Duties

### 28.1 CEO Agent

The CEO Agent must:

1. Enforce this policy in all recommendations.
2. Refuse unsafe execution requests.
3. Escalate prop-firm risk issues to Human Board.
4. Never recommend breaching risk limits.
5. Require evidence before strategy promotion.

### 28.2 Planner Agent

The Planner Agent must:

1. Mark execution proposals as high or critical risk.
2. Require RiskGovernor for all trading actions.
3. Require Board approval for live activation.
4. Add audit requirements to all agent plans.

### 28.3 Strategy Creator Agent

The Strategy Creator Agent must:

1. Include risk assumptions in every strategy spec.
2. Avoid unbounded martingale/grid behavior.
3. Include stop-loss or synthetic-risk model.
4. Include spread/slippage assumptions.
5. Include news/overnight/weekend compatibility.

### 28.4 Strategy Reviewer Agent

The Strategy Reviewer Agent must reject strategies that:

1. Cannot measure risk.
2. Depend on forbidden practices.
3. Depend on news-window execution.
4. Depend on overnight/weekend exposure when not allowed.
5. Depend on unrealistic fills.
6. Fail consistency requirements.

### 28.5 Backtest Agent

The Backtest Agent must:

1. Simulate spread.
2. Simulate slippage.
3. Simulate commissions.
4. Simulate restricted news windows where possible.
5. Report daily-loss breaches.
6. Report total-loss breaches.
7. Report Best Day Score.
8. Report drawdown and exposure.

### 28.6 Risk Reviewer Agent

The Risk Reviewer Agent must:

1. Explain risk but not approve execution.
2. Identify prop-firm rule risks.
3. Identify consistency risks.
4. Identify overexposure risks.
5. Identify forbidden-practice risks.

### 28.7 Portfolio Manager Agent

The Portfolio Manager Agent must:

1. Control strategy allocation recommendations.
2. Prevent overconcentration.
3. Prevent duplicate strategy exposure.
4. Prevent correlation clustering.
5. Require Board approval for live allocation changes.

### 28.8 Execution Agent

The Execution Agent must:

1. Never place live orders without RiskGovernor approval.
2. Never place orders inside restricted windows.
3. Never hold overnight/weekend when restricted.
4. Never exceed approved size.
5. Log every order attempt.
6. Stop on broker disconnect.

### 28.9 Audit Agent

The Audit Agent must:

1. Verify every trade has a risk approval ID.
2. Verify every order matches the approval token.
3. Verify no rules were bypassed.
4. Verify no evidence was deleted.
5. Verify no strategy skipped lifecycle stages.
6. Verify prop-firm constraints were enforced.

---

## 29. Default Configuration File

HaruQuant must implement this policy in `configs/risk_thresholds.yaml`.

```yaml
risk_profile:
  name: standard_prop_firm_compliance
  initial_balance: 100000.00

prop_firm_rules:
  max_daily_loss_pct: 5.0
  max_total_loss_pct: 10.0
  max_total_loss_type: static_from_initial_balance
  monthly_profit_target_pct: 10.0
  news_restriction_minutes_before: 10
  news_restriction_minutes_after: 10
  overnight_holding_allowed: false
  weekend_holding_allowed: false
  best_day_rule_pct: 50.0

internal_buffers:
  daily_warning_pct: 2.5
  daily_critical_pct: 3.5
  daily_hard_stop_pct: 4.0
  total_warning_pct: 5.0
  total_critical_pct: 7.5
  total_hard_stop_pct: 8.5
  monthly_drawdown_warning_pct: 3.0
  monthly_drawdown_critical_pct: 5.0
  monthly_drawdown_hard_stop_pct: 6.0
  portfolio_drawdown_warning_pct: 4.0
  portfolio_drawdown_critical_pct: 6.5
  portfolio_drawdown_hard_stop_pct: 8.0

trade_risk:
  max_risk_per_trade_pct: 0.25
  absolute_max_risk_per_trade_pct: 0.50
  reduce_risk_after_daily_loss_pct: 1.5
  block_new_trades_after_daily_loss_pct: 3.5

exposure:
  max_symbol_risk_pct: 1.0
  max_symbol_nominal_exposure_pct_of_equity: 25.0
  max_correlated_cluster_risk_pct: 1.5
  preferred_pairwise_correlation: 0.50
  max_pairwise_correlation: 0.70
  max_usd_cluster_risk_pct: 2.0
  preferred_usd_cluster_risk_pct: 1.25
  max_simultaneous_positions_total: 8
  max_positions_per_symbol: 2
  max_positions_per_strategy: 2

strategies:
  max_live_strategies: 5
  preferred_live_strategies: 3
  max_paper_strategies: 20
  preferred_paper_strategies: 10
  max_live_strategy_risk_allocation_pct: 1.0
  preferred_live_strategy_risk_allocation_pct: 0.5

spread_filter:
  enabled: true
  max_spread_multiplier_vs_median: 2.0
  max_spread_percent_of_atr: 10.0
  block_if_spread_data_missing: true

slippage_filter:
  enabled: true
  max_expected_slippage_points: 5
  max_actual_slippage_points: 10
  max_slippage_percent_of_risk: 10.0
  block_after_consecutive_bad_fills: 3

news_event_blocks:
  enabled: true
  minutes_before_high_impact_event: 10
  minutes_after_high_impact_event: 10
  pre_news_flatten_minutes_before: 15
  apply_to_new_entries: true
  apply_to_exits: true
  apply_to_stop_loss_hits: true
  apply_to_take_profit_hits: true
  apply_to_pending_order_triggers: true

session_restrictions:
  overnight_holding_allowed: false
  close_before_daily_rollover_minutes: 30
  weekend_holding_allowed: false
  close_before_weekend_minutes: 120

consistency:
  best_day_rule_pct: 50.0
  warning_pct: 40.0
  critical_pct: 45.0
  hard_limit_pct: 50.0

broker_disconnect_policy:
  block_new_orders_on_disconnect: true
  cancel_pending_orders_on_critical_disconnect: true
  max_missed_heartbeats: 3
  critical_disconnect_seconds: 30
  require_board_review_after_critical_disconnect: true

automation_limits:
  max_order_requests_per_minute: 20
  max_order_modifications_per_minute: 30
  max_account_queries_per_second: 5
  max_symbol_queries_per_second: 10
  block_duplicate_order_requests: true
  min_seconds_between_identical_orders: 10

kill_switch:
  enabled: true
  default_position_action: block_new_orders_and_alert
  emergency_position_action: close_positions_if_required_to_prevent_rule_breach
  require_board_review_to_resume: true
```

---

## 30. Acceptance Tests

The RiskGovernor implementation must pass the following tests.

### 30.1 Daily loss tests

- [ ] Reject new trade when daily loss is above 4.0%.
- [ ] Enter warning state when daily loss is above 2.5%.
- [ ] Enter critical state when daily loss is above 3.5%.
- [ ] Include floating P&L in daily loss calculation.
- [ ] Include commission, swap, and fees in daily loss calculation.

### 30.2 Total loss tests

- [ ] Reject new trade when equity is below internal total-loss floor.
- [ ] Trigger kill switch at 8.5% total loss.
- [ ] Detect external breach risk before 10% total loss.
- [ ] Use static initial-balance floor.

### 30.3 Profit target tests

- [ ] Track 10% monthly/cycle target.
- [ ] Prevent risk increase solely to reach target.
- [ ] Report target progress.
- [ ] Report whether target is valid after consistency check.

### 30.4 News tests

- [ ] Block new trade 10 minutes before high-impact event.
- [ ] Block new trade 10 minutes after high-impact event.
- [ ] Block pending-order trigger inside news window.
- [ ] Alert if open position may close inside restricted news window.

### 30.5 Overnight/weekend tests

- [ ] Block trade that cannot close before rollover.
- [ ] Close or alert before daily rollover cutoff.
- [ ] Close or alert before weekend cutoff.
- [ ] Cancel pending orders before weekend cutoff.

### 30.6 Forbidden-practice tests

- [ ] Block martingale size escalation.
- [ ] Block unbounded grid behavior.
- [ ] Block duplicate order spam.
- [ ] Block latency-arbitrage strategy classification.
- [ ] Block risk splitting to bypass limits.

### 30.7 Automation tests

- [ ] Block excessive order requests.
- [ ] Block duplicate order requests.
- [ ] Block orders without strategy ID.
- [ ] Block orders without risk approval ID.
- [ ] Pause automation on repeated broker errors.

### 30.8 Allocation tests

- [ ] Block duplicate strategy across accounts without approval.
- [ ] Block cross-account hedging.
- [ ] Block allocation increase without Board approval.
- [ ] Detect highly correlated duplicate strategies.

### 30.9 Consistency tests

- [ ] Calculate Best Day Score.
- [ ] Warn above 40%.
- [ ] Critical above 45%.
- [ ] Block pass/promotion claim at or above 50%.
- [ ] Report required additional positive-day profit to restore compliance.

### 30.10 Kill switch tests

- [ ] Trigger on daily hard stop.
- [ ] Trigger on total loss hard stop.
- [ ] Trigger on critical broker disconnect.
- [ ] Trigger when RiskGovernor is unavailable.
- [ ] Trigger when Audit Logger is unavailable.
- [ ] Require Board review to resume.

---

## 31. Coverage Checklist

This policy covers all Phase 1.2 requirements.

| Requirement | Covered? | Location |
|---|---:|---|
| Create `risk_policy.md` | Yes | Document header |
| Define max risk per trade | Yes | Section 5 |
| Define max daily loss | Yes | Section 6 |
| Define max weekly loss | Yes | Section 7 |
| Define max monthly drawdown | Yes | Section 8 |
| Define max portfolio drawdown | Yes | Section 9 |
| Define max symbol exposure | Yes | Section 10 |
| Define max correlated exposure | Yes | Section 11 |
| Define max USD-cluster exposure | Yes | Section 12 |
| Define max number of simultaneous positions | Yes | Section 13 |
| Define max strategy allocation | Yes | Section 14 |
| Define max live strategies | Yes | Section 15 |
| Define max paper strategies | Yes | Section 16 |
| Define spread filters | Yes | Section 17 |
| Define slippage filters | Yes | Section 18 |
| Define news-event blocks | Yes | Section 19 |
| Define broker-disconnect behavior | Yes | Section 25 |
| Define kill-switch rules | Yes | Section 26 |
| Define 5% max daily loss | Yes | Section 6 |
| Define 10% max total loss static | Yes | Section 4 and Section 6 |
| Define 10% profit target per month/cycle | Yes | Section 8 |
| Define 10-minute news restriction window | Yes | Section 19 |
| Define overnight/weekend restrictions | Yes | Section 20 |
| Define forbidden practices | Yes | Section 21 |
| Define EA/automation compliance | Yes | Section 22 |
| Define allocation compliance | Yes | Section 23 |
| Define consistency score / Best Day Rule | Yes | Section 24 |

---

## 32. Final Policy Statement

HaruQuant is permitted to operate under prop-firm conditions only when this Risk Policy is active, enforced by the RiskGovernor, monitored by the Kill Switch, recorded by the Audit Logger, and supervised by the Human Board.

The system may research, test, and recommend freely within approved boundaries, but it may not place, modify, or maintain live risk unless every prop-firm compliance rule is satisfied.

The final operating law is:

> **Protect the account first, pass the challenge second, grow the firm third.**

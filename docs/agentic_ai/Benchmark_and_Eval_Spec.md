# Benchmark and Eval Specification (Playbook §15)

## Test Categories

| Category | Location | Purpose |
|---|---|---|
| Golden Tasks | `tests/eval/golden_tasks/` | Known-good inputs with expected outputs |
| Adversarial Tasks | `tests/eval/adversarial_tasks/` | Injection attempts, policy bypass, ambiguous requests |
| Regression Tasks | `tests/eval/regression_tasks/` | Previously-failed cases to prevent recurrence |
| Domain Hard Cases | `tests/eval/domain_hard_cases/` | Complex multi-agent scenarios |

## Files

| File | Contents |
|---|---|
| `trade_analysis.json` | Symbol analysis with expected structure |
| `risk_assessment.json` | Portfolio risk check with expected risk class |
| `market_data.json` | Data fetch with expected bar presence |
| `prompt_injection.json` | Injection attempt → should reject |
| `policy_bypass.json` | Skip risk check attempt → should reject |
| `edge_cases.json` | Oversized/unauthorized → should reject |
| `known_failures.json` | Timeout/parse failures handled gracefully |
| `risk_scenarios.json` | Correlated symbols, high volatility regimes |

## Promotion Criteria (Playbook §15.4)

A prompt/model/tool can be promoted only when ALL criteria pass:
1. **Regression pass**: All regression tests pass
2. **Benchmark pass**: Golden tasks achieve ≥ 90% success rate
3. **Security review**: No critical findings
4. **Rollback plan**: Documented and tested
5. **Owner sign-off**: Component owner approves

## Refresh Cadence

- **Monthly**: Full benchmark run
- **Per-change**: Regression tasks on any modification
- **Owner**: ai_team_lead

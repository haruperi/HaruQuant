"""
HaruQuant Strategy Decision Scorecard.
Converts raw analytics into actionable strategy evaluations.
"""

from typing import Any, Dict, List
import pandas as pd
import numpy as np

def evaluate_strategy_quality(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate strategy quality based on the unified report payload.
    Returns a scorecard with a decision, score, strengths, and warnings.
    """
    # Extract categories safely
    summary = report.get("summary", {}).get("all", {})
    metrics = report.get("metrics", {}).get("all", {})
    ratios = report.get("ratios", {}).get("all", {})
    drawdowns = report.get("drawdowns", {}).get("all", {})
    validation = report.get("validation", {}).get("all", {})

    score = 0.0
    strengths = []
    warnings = []
    fail_reasons = []

    # 1. Profitability & Growth (Max 30 points)
    net_profit = summary.get("return_usd", 0)
    cagr = summary.get("cagr", 0)
    profit_factor = ratios.get("profit_factor", 0)

    if net_profit > 0:
        score += 5
        if cagr > 15:
            score += 10
            strengths.append(f"Strong growth (CAGR: {cagr:.1f}%)")
        elif cagr > 5:
            score += 5
        
        if profit_factor > 2.0:
            score += 15
            strengths.append(f"Excellent profit factor ({profit_factor:.2f})")
        elif profit_factor > 1.5:
            score += 10
            strengths.append(f"Good profit factor ({profit_factor:.2f})")
        elif profit_factor > 1.2:
            score += 5
    else:
        fail_reasons.append("Strategy is not profitable in the testing period.")

    # 2. Risk & Robustness (Max 30 points)
    max_dd_pct = drawdowns.get("max_drawdown_pct", 100)
    sharpe = ratios.get("sharpe_ratio", 0)
    dsr_p = validation.get("dsr_p_value", 1.0)

    if max_dd_pct < 10:
        score += 15
        strengths.append("Very low drawdown exposure")
    elif max_dd_pct < 20:
        score += 10
    elif max_dd_pct > 35:
        warnings.append(f"High maximum drawdown ({max_dd_pct:.1f}%)")
        score -= 5

    if sharpe > 2.0:
        score += 15
        strengths.append("Superior risk-adjusted returns (Sharpe > 2)")
    elif sharpe > 1.0:
        score += 10
        strengths.append("Solid risk-adjusted returns (Sharpe > 1)")
    
    if dsr_p < 0.05:
        score += 5
        strengths.append("Statistically significant edge (DSR P-Value < 0.05)")
    elif dsr_p > 0.5:
        warnings.append("High probability of backtest overfitting (High DSR P-Value)")

    # 3. Execution & Efficiency (Max 20 points)
    win_rate = metrics.get("win_rate", 0)
    expectancy_r = ratios.get("expectancy_r", 0)
    num_trades = metrics.get("total_trades", 0)

    if num_trades < 30:
        warnings.append(f"Small sample size ({num_trades} trades). Results may not be stable.")
        score -= 10
    elif num_trades > 100:
        score += 5

    if expectancy_r > 0.2:
        score += 10
        strengths.append(f"High expectancy per trade ({expectancy_r:.2f} R)")
    elif expectancy_r > 0.1:
        score += 5

    if win_rate > 60:
        score += 5
        strengths.append(f"High win rate ({win_rate:.1f}%)")
    elif win_rate < 35:
        warnings.append(f"Low win rate ({win_rate:.1f}%). Requires high psychological discipline.")

    # 4. Final Decision
    # Normalize score to 0-100 range (though our weights might go slightly over)
    final_score = max(0.0, min(100.0, score))
    
    decision = "REJECT"
    recommended_action = "reject"

    if final_score >= 75 and not fail_reasons:
        decision = "PASS"
        recommended_action = "promote_to_oos"
    elif final_score >= 50 and not fail_reasons:
        decision = "WATCHLIST"
        recommended_action = "run_more_tests"
    
    if fail_reasons:
        decision = "REJECT"
        recommended_action = "reject"

    return {
        "decision": decision,
        "score": round(final_score, 1),
        "strengths": strengths,
        "warnings": warnings,
        "fail_reasons": fail_reasons,
        "recommended_action": recommended_action
    }

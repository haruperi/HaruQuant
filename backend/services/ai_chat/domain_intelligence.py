"""Domain-specific prompt guidance and response shaping for trading copilot tasks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainPromptSpec:
    domain_focus: str
    response_style: str
    prompt_goal: str
    quantitative_rules: tuple[str, ...]
    section_headers: tuple[str, ...]


DOMAIN_PROMPT_SPECS: dict[str, DomainPromptSpec] = {
    "performance_summary": DomainPromptSpec(
        domain_focus="performance_summary",
        response_style="summary",
        prompt_goal="Summarize the current strategy, portfolio, or session state using concrete system metrics.",
        quantitative_rules=(
            "Lead with realized or current metrics before interpretation.",
            "Name the dataset, timeframe, symbol set, or strategy identifiers when available.",
            "Do not invent benchmark comparisons that are not in context or tools.",
        ),
        section_headers=("Summary", "Metrics", "Implications"),
    ),
    "diagnostic": DomainPromptSpec(
        domain_focus="drawdown_diagnosis",
        response_style="diagnostic",
        prompt_goal="Diagnose underperformance, drawdown, or abnormal behavior from backtest, optimization, or live-risk evidence.",
        quantitative_rules=(
            "Explain the likely driver using drawdown, PnL, trade-count, or exposure evidence when available.",
            "Separate observed facts from inference.",
            "If a critical metric is missing, say exactly which metric is absent.",
        ),
        section_headers=("Observed State", "Likely Drivers", "Next Checks"),
    ),
    "comparison": DomainPromptSpec(
        domain_focus="optimization_comparison",
        response_style="compare",
        prompt_goal="Compare strategies, optimization outputs, or current state versus prior expectations with explicit tradeoffs.",
        quantitative_rules=(
            "Compare at least two concrete dimensions such as score, Sharpe, drawdown, exposure, or trade count.",
            "State which side is stronger and why.",
            "Avoid generic 'better/worse' claims without a metric anchor.",
        ),
        section_headers=("Comparison", "Tradeoffs", "Recommendation"),
    ),
    "risk_explanation": DomainPromptSpec(
        domain_focus="risk_explanation",
        response_style="warning",
        prompt_goal="Explain current portfolio or session risk with emphasis on concentration, open positions, and floating PnL.",
        quantitative_rules=(
            "Highlight concentration, exposure, and open-risk conditions before narrative commentary.",
            "Escalate only when the data supports a warning.",
            "Use current state, not stale chat assumptions, as the source of truth.",
        ),
        section_headers=("Risk State", "Primary Exposures", "Operator Warning"),
    ),
    "recommendation": DomainPromptSpec(
        domain_focus="research_recommendation",
        response_style="recommendation",
        prompt_goal="Recommend the next research or review step without implying trade execution authority.",
        quantitative_rules=(
            "Tie each recommendation to an observed metric or missing validation step.",
            "Prefer backtest, optimization, or risk-review actions over vague advice.",
            "Do not present recommendations as live trade instructions.",
        ),
        section_headers=("Assessment", "Recommendation", "Evidence Needed"),
    ),
}


def resolve_domain_prompt_spec(task_class: str) -> DomainPromptSpec:
    return DOMAIN_PROMPT_SPECS.get(task_class, DOMAIN_PROMPT_SPECS["performance_summary"])

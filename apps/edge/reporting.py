"""Edge Lab reporting utilities.

Generates Markdown and JSON reports from EdgeResult objects.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from apps.logger import logger

from .results_schema import EdgeResult, EdgeStats


def _format_value(v: Any, precision: int = 4) -> str:
    """Format a value for display."""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if v != v:  # NaN check
            return "N/A"
        if abs(v) == float("inf"):
            return "Inf" if v > 0 else "-Inf"
        if abs(v) < 0.01 and v != 0:
            return f"{v:.2e}"
        return f"{v:.{precision}f}"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    return str(v)


def _verdict_emoji(stats: EdgeStats) -> str:
    """Generate verdict based on stats."""
    if stats.n_trades < 30:
        return "INSUFFICIENT_DATA"
    if stats.ci_low > 0 and stats.p_value_perm < 0.05:
        return "EDGE_CONFIRMED"
    if stats.ci_low > 0:
        return "POTENTIAL_EDGE"
    if stats.expectancy_r > 0:
        return "WEAK_SIGNAL"
    return "NO_EDGE"


def _append_header(lines: List[str], res: EdgeResult) -> None:
    lines.append(f"# Edge Lab Report: {res.symbol} {res.timeframe}")
    lines.append("")
    lines.append(f"**Strategy:** {res.eds_name}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")


def _append_verdict(lines: List[str], stats: EdgeStats) -> None:
    verdict = _verdict_emoji(stats)
    lines.append(f"## Verdict: {verdict}")
    lines.append("")


def _append_summary(lines: List[str], stats: EdgeStats) -> None:
    lines.append("## Summary Statistics")
    lines.append("")
    lines.append("| Metric | Value | Interpretation |")
    lines.append("|--------|------:|----------------|")
    lines.append(
        f"| Trades | {stats.n_trades} | {'Sufficient' if stats.n_trades >= 200 else 'Low sample'} |"
    )
    lines.append(
        f"| Expectancy (R) | {_format_value(stats.expectancy_r)} | {'Positive' if stats.expectancy_r > 0 else 'Negative'} |"
    )
    lines.append(f"| Win Rate | {_format_value(stats.win_rate * 100, 1)}% | - |")
    lines.append(
        f"| Profit Factor | {_format_value(stats.profit_factor, 2)} | {'>1.5 good' if stats.profit_factor > 1.5 else 'Average'} |"
    )
    lines.append(
        f"| Median MAE (R) | {_format_value(stats.median_mae_r, 3)} | Drawdown risk |"
    )
    lines.append(
        f"| Median MFE (R) | {_format_value(stats.median_mfe_r, 3)} | Profit potential |"
    )
    lines.append(f"| Avg Hold (bars) | {_format_value(stats.avg_hold_bars, 1)} | - |")
    lines.append("")


def _append_validation(lines: List[str], stats: EdgeStats) -> None:
    lines.append("## Statistical Validation")
    lines.append("")
    lines.append("| Test | Value | Threshold | Pass |")
    lines.append("|------|------:|----------:|:----:|")

    ci_pass = stats.ci_low > 0
    lines.append(
        f"| Bootstrap CI Low | {_format_value(stats.ci_low)} | > 0 | {'Yes' if ci_pass else 'No'} |"
    )
    lines.append(f"| Bootstrap CI High | {_format_value(stats.ci_high)} | - | - |")

    pval_pass = stats.p_value_perm < 0.05
    lines.append(
        f"| Permutation p-value | {_format_value(stats.p_value_perm)} | < 0.05 | {'Yes' if pval_pass else 'No'} |"
    )
    lines.append("")


def _append_interpretation(
    lines: List[str], stats: EdgeStats, ci_pass: bool, pval_pass: bool
) -> None:
    lines.append("## Interpretation")
    lines.append("")

    if stats.n_trades < 30:
        lines.append(
            "- **Insufficient sample size.** Need at least 30 trades for meaningful analysis."
        )
    elif stats.n_trades < 100:
        lines.append(
            f"- Sample size ({stats.n_trades}) is marginal. Consider more data for robustness."
        )
    else:
        lines.append(f"- Sample size ({stats.n_trades}) is adequate for analysis.")

    if ci_pass and pval_pass:
        lines.append(
            "- **Strong statistical evidence** for edge (CI > 0 and p < 0.05)."
        )
    elif ci_pass:
        lines.append(
            "- Bootstrap CI suggests positive expectancy, but permutation test not conclusive."
        )
    elif stats.expectancy_r > 0:
        lines.append(
            "- Positive expectancy observed, but confidence interval includes zero."
        )
    else:
        lines.append("- No evidence of positive expectancy.")

    lines.append("")


def _append_extras(lines: List[str], stats: EdgeStats) -> None:
    if not stats.extras:
        return

    lines.append("## Additional Metrics")
    lines.append("")
    for k, v in stats.extras.items():
        if not isinstance(v, (dict, list)):
            lines.append(f"- **{k}**: {_format_value(v)}")
    lines.append("")


def _append_config(lines: List[str], res: EdgeResult) -> None:
    lines.append("## Configuration")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(res.config, indent=2, default=str))
    lines.append("```")
    lines.append("")


def _append_trades(lines: List[str], res: EdgeResult) -> None:
    if not res.trades:
        return

    lines.append("## Trade List")
    lines.append("")
    lines.append("| Entry | Exit | Side | R-Multiple | Hold |")
    lines.append("|-------|------|------|----------:|-----:|")
    for t in res.trades[:50]:  # Limit to first 50
        lines.append(
            f"| {t.entry_time} | {t.exit_time} | {t.side} | {_format_value(t.r_multiple, 2)} | {t.hold_bars} |"
        )
    if len(res.trades) > 50:
        lines.append("| ... | ... | ... | ... | ... |")
        lines.append(f"| *{len(res.trades) - 50} more trades* | | | | |")
    lines.append("")


def _append_footer(lines: List[str]) -> None:
    lines.append("---")
    lines.append("")
    lines.append("### Notes")
    lines.append("")
    lines.append(
        "- **R-Multiple**: Trade result normalized by stop distance (risk unit)"
    )
    lines.append(
        "- **Bootstrap CI**: Block bootstrap confidence interval (accounts for autocorrelation)"
    )
    lines.append(
        "- **Permutation p-value**: Probability of observing this result by chance"
    )
    lines.append("- CI lower bound > 0 is the primary criterion for edge confirmation")
    lines.append("")


def result_to_markdown(res: EdgeResult, include_trades: bool = False) -> str:
    """Convert EdgeResult to formatted Markdown report.

    Args:
        res: EdgeResult object
        include_trades: Whether to include trade list

    Returns:
        Markdown formatted string
    """
    s = res.stats
    lines: List[str] = []

    _append_header(lines, res)
    _append_verdict(lines, s)
    _append_summary(lines, s)
    _append_validation(lines, s)

    ci_pass = s.ci_low > 0
    pval_pass = s.p_value_perm < 0.05
    _append_interpretation(lines, s, ci_pass, pval_pass)

    _append_extras(lines, s)
    _append_config(lines, res)

    if include_trades:
        _append_trades(lines, res)

    _append_footer(lines)

    return "\n".join(lines)


def result_to_summary(res: EdgeResult) -> Dict[str, Any]:
    """Generate a concise summary dictionary.

    Args:
        res: EdgeResult object

    Returns:
        Dictionary with key metrics
    """
    s = res.stats
    return {
        "symbol": res.symbol,
        "timeframe": res.timeframe,
        "eds_name": res.eds_name,
        "n_trades": s.n_trades,
        "expectancy": s.expectancy_r,
        "win_rate": s.win_rate,
        "profit_factor": s.profit_factor,
        "ci_low": s.ci_low,
        "ci_high": s.ci_high,
        "p_value": s.p_value_perm,
        "verdict": _verdict_emoji(s),
        "edge_confirmed": s.ci_low > 0 and s.p_value_perm < 0.05,
    }


def save_markdown(
    res: EdgeResult, path: str | Path, include_trades: bool = False
) -> Path:
    """Save EdgeResult as Markdown file.

    Args:
        res: EdgeResult object
        path: Output file path
        include_trades: Whether to include trade list

    Returns:
        Path to saved file
    """
    p = Path(path)
    content = result_to_markdown(res, include_trades=include_trades)
    p.write_text(content, encoding="utf-8")
    logger.info(f"Saved Markdown report to {p}")
    return p


def save_json(res: EdgeResult, path: str | Path) -> Path:
    """Save EdgeResult as JSON file.

    Args:
        res: EdgeResult object
        path: Output file path

    Returns:
        Path to saved file
    """
    p = Path(path)
    content = json.dumps(res.to_dict(), indent=2, default=str)
    p.write_text(content, encoding="utf-8")
    logger.info(f"Saved JSON report to {p}")
    return p


def generate_multi_symbol_report(
    results: List[EdgeResult],
    output_dir: str | Path,
) -> Path:
    """Generate a combined report for multiple symbols.

    Args:
        results: List of EdgeResult objects
        output_dir: Output directory

    Returns:
        Path to summary file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# Edge Lab Multi-Symbol Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Symbols Analyzed:** {len(results)}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| Symbol | Timeframe | EDS | Trades | Expectancy | CI Low | p-value | Verdict |"
    )
    lines.append(
        "|--------|-----------|-----|-------:|-----------:|-------:|--------:|---------|"
    )

    confirmed = 0
    for res in results:
        s = res.stats
        verdict = _verdict_emoji(s)
        if "CONFIRMED" in verdict:
            confirmed += 1
        lines.append(
            f"| {res.symbol} | {res.timeframe} | {res.eds_name.split()[0]} | "
            f"{s.n_trades} | {_format_value(s.expectancy_r)} | "
            f"{_format_value(s.ci_low)} | {_format_value(s.p_value_perm)} | {verdict} |"
        )

    lines.append("")
    lines.append(f"**Edges Confirmed:** {confirmed}/{len(results)}")
    lines.append("")

    # Save individual reports
    lines.append("## Individual Reports")
    lines.append("")
    for res in results:
        fname = f"{res.symbol}_{res.timeframe}_{res.eds_name.split()[0]}.md"
        save_markdown(res, output_dir / fname)
        save_json(res, output_dir / fname.replace(".md", ".json"))
        lines.append(f"- [{res.symbol} {res.timeframe}](./{fname})")

    lines.append("")

    # Save summary
    summary_path = output_dir / "summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Saved multi-symbol summary to {summary_path}")

    return summary_path


def print_result_summary(res: EdgeResult) -> None:
    """Print a concise result summary to console.

    Args:
        res: EdgeResult object
    """
    s = res.stats
    verdict = _verdict_emoji(s)

    print(f"\n{'='*60}")
    print(f"  {res.eds_name}: {res.symbol} {res.timeframe}")
    print(f"{'='*60}")
    print(f"  Trades:      {s.n_trades}")
    print(f"  Expectancy:  {_format_value(s.expectancy_r)} R")
    print(f"  Win Rate:    {_format_value(s.win_rate * 100, 1)}%")
    print(f"  CI:          [{_format_value(s.ci_low)}, {_format_value(s.ci_high)}]")
    print(f"  p-value:     {_format_value(s.p_value_perm)}")
    print(f"  VERDICT:     {verdict}")
    print(f"{'='*60}\n")

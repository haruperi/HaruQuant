"""Helpers for building versioned Edge Lab profile snapshots."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _metric_row(
    *,
    section: str,
    metric_key: str,
    value: Any,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if _is_number(value):
        return {
            "section": section,
            "metric_key": metric_key,
            "value_num": float(value),
            "value_text": None,
            "value_type": "number",
            "context": context or {},
        }
    return {
        "section": section,
        "metric_key": metric_key,
        "value_num": None,
        "value_text": None if value is None else str(value),
        "value_type": "text",
        "context": context or {},
    }


def _add_scalar_metrics(
    metrics: List[Dict[str, Any]],
    *,
    section: str,
    values: Dict[str, Any],
    prefix: str = "",
) -> None:
    for key, value in values.items():
        metric_key = f"{prefix}{key}" if prefix else str(key)
        if isinstance(value, dict):
            _add_scalar_metrics(
                metrics,
                section=section,
                values=value,
                prefix=f"{metric_key}.",
            )
        elif isinstance(value, list):
            continue
        else:
            metrics.append(_metric_row(section=section, metric_key=metric_key, value=value))


def build_edge_profile_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build a normalized snapshot payload from Edge Lab tab results."""
    dataset = dict(payload.get("dataset") or {})
    core_metric_profile = dict(payload.get("core_metric_profile") or {})
    seasonality_result = dict(payload.get("seasonality_result") or {})
    market_structure_profile = dict(payload.get("market_structure_profile") or {})
    stability = dict(payload.get("market_structure_stability") or {})
    robustness = dict(payload.get("market_structure_robustness") or {})
    scorecard_report = dict(payload.get("scorecard_report") or {})
    automation_metadata = dict(payload.get("automation_metadata") or {})
    artifacts = list(payload.get("artifacts") or [])

    dataset_meta = dict(dataset.get("meta") or {})
    core_summary = dict(core_metric_profile.get("summary") or {})
    seasonality_meta = dict(seasonality_result.get("meta") or {})
    market_summary = dict(market_structure_profile.get("summary") or {})

    scorecard_summary = {
        "final_score": scorecard_report.get("finalScore"),
        "final_label": scorecard_report.get("finalLabel"),
        "overall_confidence": scorecard_report.get("overallConfidence"),
        "score_spec_version": scorecard_report.get("scoreSpecVersion"),
        "research_ready": scorecard_report.get("research_ready"),
        "readiness_label": scorecard_report.get("readiness_label"),
        "readiness_reasons": scorecard_report.get("readiness_reasons") or [],
    }

    metrics: List[Dict[str, Any]] = []
    _add_scalar_metrics(metrics, section="dataset", values=dataset_meta)
    _add_scalar_metrics(metrics, section="core_summary", values=core_summary)
    _add_scalar_metrics(metrics, section="seasonality_meta", values=seasonality_meta)

    for value in core_metric_profile.get("values") or []:
        metric_key = f"{value.get('family')}.{value.get('metric_key')}"
        metrics.append(
            _metric_row(
                section="core_metric",
                metric_key=metric_key,
                value=value.get("value"),
                context=dict(value.get("context") or {}),
            )
        )

    for row in seasonality_result.get("session_summary") or []:
        session = str(row.get("session") or "unknown")
        for key in (
            "bars",
            "avg_range_pips",
            "avg_spread_pips",
            "avg_abs_co_pips",
            "avg_volume",
            "win_rate",
            "opportunity_score",
            "high_rate",
            "low_rate",
            "label",
        ):
            metrics.append(
                _metric_row(
                    section="seasonality_session",
                    metric_key=f"{session}.{key}",
                    value=row.get(key),
                )
            )

    for bucket_name in ("best_sessions", "dead_sessions", "best_hours", "dead_hours"):
        rows = seasonality_result.get("opportunity_windows", {}).get(bucket_name) or []
        if not rows:
            continue
        top = rows[0]
        prefix = f"{bucket_name}.top"
        for key in ("session", "hour", "bars", "avg_range_pips", "avg_spread_pips", "avg_abs_co_pips", "win_rate", "opportunity_score", "label"):
            metrics.append(
                _metric_row(
                    section="seasonality_opportunity",
                    metric_key=f"{prefix}.{key}",
                    value=top.get(key),
                )
            )

    market_scalar_summary = {
        key: value
        for key, value in market_summary.items()
        if not isinstance(value, list)
    }
    _add_scalar_metrics(metrics, section="market_summary", values=market_scalar_summary)

    for row in market_structure_profile.get("values") or []:
        metric_key = f"{row.get('family')}.{row.get('metric_key')}"
        metrics.append(
            _metric_row(
                section="market_value",
                metric_key=metric_key,
                value=row.get("value"),
                context=dict(row.get("context") or {}),
            )
        )

    if stability:
        _add_scalar_metrics(metrics, section="stability", values=stability)
    if robustness:
        _add_scalar_metrics(metrics, section="robustness", values=robustness)

    scores: List[Dict[str, Any]] = []
    for row in scorecard_report.get("rows") or []:
        scores.append(
            {
                "score_key": str(row.get("key") or ""),
                "label": str(row.get("label") or row.get("key") or ""),
                "score": float(row.get("score") or 0.0),
                "confidence": str(row.get("confidence") or ""),
                "explanation": str(row.get("explanation") or ""),
                "inputs": dict(row.get("inputs") or {}),
            }
        )

    strategy_fit: List[Dict[str, Any]] = []
    for index, row in enumerate(scorecard_report.get("strategyFit", {}).get("ranked") or []):
        strategy_fit.append(
            {
                "rank_order": index + 1,
                "archetype": str(row.get("archetype") or ""),
                "fit_score": float(row.get("fitScore") or 0.0),
                "rationale": str(row.get("rationale") or ""),
                "warnings": list(row.get("warnings") or []),
                "anti_fit_conditions": list(row.get("antiFitConditions") or []),
                "inputs": dict(row.get("inputs") or {}),
            }
        )

    summary = {
        "symbol": dataset_meta.get("symbol") or core_metric_profile.get("symbol") or market_structure_profile.get("symbol"),
        "timeframe": dataset_meta.get("timeframe") or core_metric_profile.get("timeframe") or market_structure_profile.get("timeframe"),
        "data_source": (dataset.get("request") or {}).get("data_source") or core_metric_profile.get("data_source") or market_structure_profile.get("data_source"),
        "range_by": (dataset.get("request") or {}).get("range_by") or core_metric_profile.get("range_by") or market_structure_profile.get("range_by"),
        "model_version": market_summary.get("model_version") or "edge_lab_scorecard_v1",
        "baseline_id": market_summary.get("baseline_id") or "edge_lab_profile_snapshot_v1",
        "core_metric_run_id": core_metric_profile.get("run_id"),
        "market_structure_run_id": market_structure_profile.get("run_id"),
        "dataset_meta": dataset_meta,
        "core_metric_summary": core_summary,
        "seasonality_summary": {
            "meta": seasonality_meta,
            "session_summary": seasonality_result.get("session_summary") or [],
            "opportunity_windows": seasonality_result.get("opportunity_windows") or {},
        },
        "market_structure_summary": {
            "summary": market_summary,
            "calibration_metadata": market_summary.get("calibration_metadata") or market_structure_profile.get("calibration_metadata") or {},
        },
        "scorecard_summary": scorecard_summary,
        "automation_metadata": automation_metadata,
        "artifact_refs": artifacts,
        "metrics": metrics,
        "scores": scores,
        "strategy_fit": strategy_fit,
    }
    return summary

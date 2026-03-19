"""Risk limit validators for the canonical risk state."""

from __future__ import annotations

from apps.risk.risk_limits import RiskLimits
from apps.risk.validators.common import ValidationSummary


def validate_risk_limits(limits: RiskLimits) -> ValidationSummary:
    """Validate risk limit configuration for canonical portfolio state."""
    summary = ValidationSummary()

    fraction_fields = [
        ("var_cap_frac", limits.var_cap_frac),
        ("es_cap_frac", limits.es_cap_frac),
        ("delta_var_cap_frac", limits.delta_var_cap_frac),
        ("delta_es_cap_frac", limits.delta_es_cap_frac),
        ("max_margin_used_frac", limits.max_margin_used_frac),
        ("max_single_rc_frac", limits.max_single_rc_frac),
    ]
    for field_name, value in fraction_fields:
        if not 0 < value <= 1:
            summary = summary.add(
                "error",
                "limits_invalid_fraction",
                f"{field_name} must be within (0, 1].",
                field=field_name,
                value=value,
            )

    if limits.confidence_level <= 0 or limits.confidence_level >= 1:
        summary = summary.add(
            "error",
            "limits_invalid_confidence_level",
            "confidence_level must be within (0, 1).",
            value=limits.confidence_level,
        )

    if limits.time_horizon_days <= 0:
        summary = summary.add(
            "error",
            "limits_invalid_horizon",
            "time_horizon_days must be positive.",
            value=limits.time_horizon_days,
        )

    if limits.vol_lookback <= 1 or limits.corr_lookback <= 1:
        summary = summary.add(
            "error",
            "limits_invalid_lookback",
            "vol_lookback and corr_lookback must be greater than 1.",
            vol_lookback=limits.vol_lookback,
            corr_lookback=limits.corr_lookback,
        )

    return summary

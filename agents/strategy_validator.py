"""Validation gate for HaruQuant strategy specs."""

from __future__ import annotations

from agents.schemas import StrategySpec


class StrategySpecValidator:
    def validate(self, spec: StrategySpec) -> dict[str, object]:
        errors: list[str] = []
        warnings: list[str] = []
        if not spec.symbol or spec.symbol == "UNKNOWN":
            errors.append("missing_symbol")
        if not spec.timeframe:
            errors.append("missing_timeframe")
        if not spec.entry_logic or any(len(rule.strip()) < 10 for rule in spec.entry_logic):
            errors.append("vague_entry_rules")
        if not spec.exit_logic or any(len(rule.strip()) < 10 for rule in spec.exit_logic):
            errors.append("vague_exit_rules")
        if not spec.cost_assumptions:
            errors.append("missing_cost_assumptions")
        if not spec.data_requirements:
            errors.append("missing_data_requirements")
        text = " ".join(spec.entry_logic + spec.exit_logic + spec.invalid_conditions).lower()
        if "future" in text and "never use future" not in text:
            errors.append("future_looking_rule")
        if "live without approval" in text:
            errors.append("impossible_live_condition")
        if len(spec.position_sizing) == 0:
            warnings.append("position_sizing_needs_detail")
        return {"valid": not errors, "errors": errors, "warnings": warnings}


__all__ = ["StrategySpecValidator"]

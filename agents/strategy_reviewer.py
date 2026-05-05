"""Strategy Review Department."""

from __future__ import annotations

from typing import Any

from agents._persistence import stable_id, utc_stamp, write_json_artifact
from agents.base import AgentRunContext, AgentRunResult
from agents.schemas import StrategyReview, StrategySpec
from agents.strategy_validator import StrategySpecValidator


class StrategyReviewerAgent:
    agent_name = "strategy_reviewer"

    def review(self, spec: StrategySpec) -> StrategyReview:
        validation = StrategySpecValidator().validate(spec)
        weaknesses = list(validation["errors"]) + list(validation["warnings"])
        text = " ".join(spec.entry_logic + spec.exit_logic).lower()
        checks = {
            "lookahead_bias": "closed bars" in text and "future" not in text.replace("never use future", ""),
            "repainting_risk": "repainting" in " ".join(spec.exit_logic + spec.invalid_conditions).lower(),
            "indicator_warmup": "warmup" in " ".join(spec.invalid_conditions).lower(),
            "spread_slippage_realism": bool(spec.cost_assumptions),
            "risk_governor_compatibility": any("RiskGovernor" in item for item in spec.risk_assumptions),
        }
        for name, passed in checks.items():
            if not passed:
                weaknesses.append(name)
        verdict = "approve" if not weaknesses else "needs_review"
        if validation["errors"]:
            verdict = "reject"
        return StrategyReview(
            review_id=stable_id("review", spec.strategy_name),
            strategy_id=stable_id("strategy", f"{spec.strategy_name}-{spec.version}"),
            reviewer_agent=self.agent_name,
            verdict=verdict,  # type: ignore[arg-type]
            strengths=["Uses structured StrategySpec", "Includes lifecycle-aware test plan"],
            weaknesses=weaknesses,
            required_changes=weaknesses,
        )

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        spec_payload = task_input.get("spec") or task_input
        spec = spec_payload if isinstance(spec_payload, StrategySpec) else StrategySpec.model_validate(spec_payload)
        review = self.review(spec)
        path = write_json_artifact(
            "reports/strategy_reviews",
            f"{review.review_id}-{utc_stamp()}.json",
            review.model_dump(mode="json"),
        )
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed" if review.verdict != "reject" else "blocked",
            output={"review": review.model_dump(mode="json"), "review_uri": path, "codegen_blocked": review.verdict == "reject"},
            evidence_refs=[path],
            decisions=[{"decision": review.verdict, "rationale": "Formal strategy review completed."}],
        )


__all__ = ["StrategyReviewerAgent"]

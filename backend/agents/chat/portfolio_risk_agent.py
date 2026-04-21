"""Portfolio risk chat specialist for exposure-oriented questions."""

from __future__ import annotations

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult


class PortfolioRiskAgent:
    agent_name = "portfolio_risk_agent"

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        risk = self._result(tool_results, "risk_snapshot")
        portfolio = self._result(tool_results, "portfolio_summary")
        positions = self._result(tool_results, "open_positions")
        if risk is None and portfolio is None and positions is None:
            return None

        evidence: list[str] = []
        findings: list[str] = []

        for result in (risk, portfolio, positions):
            if result is None:
                continue
            payload = result.payload
            evidence.append(f"{result.tool_name}: {self._summarize_payload(payload)}")
            if result.tool_name == "open_positions" and payload.get("open_position_count") is not None:
                findings.append(f"Open positions observed: {payload['open_position_count']}.")
            if result.tool_name == "portfolio_summary" and payload.get("aggregate_open_profit") is not None:
                findings.append(f"Aggregate open profit is {payload['aggregate_open_profit']}.")

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary="Risk specialist evidence is available and should anchor the answer on current exposure and open-position state.",
            findings=findings or ["Current risk state is grounded in portfolio and risk snapshots."],
            evidence=evidence or [page_context.payload.summary.headline],
            recommendation="Keep the explanation centered on concentration, open risk, and live session state rather than generic advice.",
            confidence=80 if risk is not None else 70,
        )

    @staticmethod
    def _result(tool_results: list[ToolExecutionResult], tool_name: str) -> ToolExecutionResult | None:
        for result in tool_results:
            if result.tool_name == tool_name and result.success:
                return result
        return None

    @staticmethod
    def _summarize_payload(payload: dict[str, object]) -> str:
        headline = payload.get("headline_metrics")
        if isinstance(headline, dict) and headline:
            return ", ".join(f"{key}={value}" for key, value in list(headline.items())[:4])
        for key in ("aggregate_open_profit", "open_position_count", "status", "session_id"):
            if key in payload:
                return f"{key}={payload[key]}"
        return ", ".join(f"{key}={value}" for key, value in list(payload.items())[:3]) or "no payload"

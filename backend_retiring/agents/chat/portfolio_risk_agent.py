"""Portfolio risk chat specialist for exposure-oriented questions."""

from __future__ import annotations

from typing import Any

from backend_retiring.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend_retiring.agents.chat.ai_chat.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class PortfolioRiskAgent(SpecialistAgentBase):
    """LLM-backed portfolio risk specialist.

    Analyzes live portfolio exposure, open positions, and risk snapshots.
    Returns structured risk findings grounded in current session data.
    Falls back to deterministic string-building if the LLM is unavailable.
    """

    agent_name = "portfolio_risk_agent"

    SYSTEM_PROMPT = """You are HaruQuant's Portfolio Risk specialist.
Analyze the provided live portfolio state and produce a structured JSON risk assessment.

Output schema (JSON only):
{
  "summary": "<one sentence grounded in the live state>",
  "findings": [
    "FACT: <neutral observation of exposure or position>",
    "INTERPRETATION: <what this fact implies for session safety>",
    "RISK: <a specific downside, e.g., concentration, volatility, or leverage risk>"
  ],
  "evidence": ["key=value", ...],
  "recommendation": "<one concrete next action, e.g., 'reduce concentration in XAUUSD', 'monitor kill switch', 'review margin'>",
  "confidence": <integer 0-100>,
  "missing_data": ["<missing field>", ...]
}

Rules:
- findings MUST follow the FACT/INTERPRETATION/RISK prefix pattern.
- if open positions are present, state symbol(s) and floating PnL for each in a FACT.
- if any single symbol exceeds 40 percent of total exposure, flag it as a concentration risk in a RISK finding.
- do not recommend opening or closing live trades.
- if kill switch status or session state is absent, name it in missing_data.
- confidence < 65 if fewer than 2 of {risk_snapshot, portfolio_summary, open_positions} are present.
- maximum 6 findings (2 sets of Fact/Interpretation/Risk).
"""

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context: Any,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        risk = self._get_result(tool_results, "risk_snapshot")
        portfolio = self._get_result(tool_results, "portfolio_summary")
        positions = self._get_result(tool_results, "open_positions")

        if risk is None and portfolio is None and positions is None:
            return None

        deterministic = self._deterministic_artifact(
            task_class=task_class,
            risk=risk,
            portfolio=portfolio,
            positions=positions,
            page_context=page_context,
        )

        user_payload = self._build_user_payload(
            risk=risk,
            portfolio=portfolio,
            positions=positions,
            task_class=task_class,
        )
        raw = self._call_llm_plan(user_payload=user_payload)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=deterministic)

    @staticmethod
    def _build_user_payload(
        *,
        risk: ToolExecutionResult | None,
        portfolio: ToolExecutionResult | None,
        positions: ToolExecutionResult | None,
        task_class: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"task_class": task_class}

        if risk is not None:
            r = risk.payload
            headline = r.get("headline_metrics") or {}
            payload["risk_snapshot"] = {
                "kill_switch_active": r.get("kill_switch_active"),
                "session_id": r.get("session_id"),
                "session_status": r.get("session_status"),
                "headline_metrics": dict(list(headline.items())[:8]) if isinstance(headline, dict) else {},
            }

        if portfolio is not None:
            p = portfolio.payload
            payload["portfolio_summary"] = {
                "aggregate_open_profit": p.get("aggregate_open_profit"),
                "total_exposure": p.get("total_exposure"),
                "symbol_breakdown": p.get("symbol_breakdown"),
                "strategy_count": p.get("strategy_count"),
            }

        if positions is not None:
            pos = positions.payload
            open_list = pos.get("positions") or []
            payload["open_positions"] = {
                "open_position_count": pos.get("open_position_count"),
                "positions": [
                    {
                        "symbol": p.get("symbol"),
                        "floating_pnl": p.get("floating_pnl"),
                        "exposure_pct": p.get("exposure_pct"),
                        "side": p.get("side"),
                    }
                    for p in (open_list[:6] if isinstance(open_list, list) else [])
                ],
            }

        return payload

    def _deterministic_artifact(
        self,
        *,
        task_class: str,
        risk: ToolExecutionResult | None,
        portfolio: ToolExecutionResult | None,
        positions: ToolExecutionResult | None,
        page_context: Any,
    ) -> SpecialistAgentArtifact | None:
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
            summary=(
                "Risk specialist evidence is available and should anchor the answer "
                "on current exposure and open-position state."
            ),
            findings=findings or ["Current risk state is grounded in portfolio and risk snapshots."],
            evidence=evidence or [page_context.payload.summary.headline],
            recommendation=(
                "Keep the explanation centered on concentration, open risk, and live "
                "session state rather than generic advice."
            ),
            confidence=80 if risk is not None else 70,
        )

    @staticmethod
    def _summarize_payload(payload: dict[str, object]) -> str:
        headline = payload.get("headline_metrics")
        if isinstance(headline, dict) and headline:
            return ", ".join(f"{k}={v}" for k, v in list(headline.items())[:4])
        for key in ("aggregate_open_profit", "open_position_count", "status", "session_id"):
            if key in payload:
                return f"{key}={payload[key]}"
        return ", ".join(f"{k}={v}" for k, v in list(payload.items())[:3]) or "no payload"

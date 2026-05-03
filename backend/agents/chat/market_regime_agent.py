"""Market regime specialist for analyzing current market environment."""

from __future__ import annotations

from typing import Any

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class MarketRegimeAgent(SpecialistAgentBase):
    """LLM-backed market regime specialist.

    Analyzes latest candle data, symbol statistics, and technical context 
    to determine the current market regime (e.g., Trending, Mean-Reverting, Volatile).
    """

    agent_name = "market_regime_agent"

    SYSTEM_PROMPT = """You are HaruQuant's Market Regime specialist.
Analyze the provided market data (candles, symbol stats) and determine the current trading environment.

Output schema (JSON only):
{
  "summary": "<one sentence on the current regime, e.g., 'EURUSD is in a low-volatility bullish trend on H1'>",
  "findings": [
    "FACT: <neutral observation of price action, volume, or range>",
    "INTERPRETATION: <how this fact defines the current regime>",
    "RISK: <a regime-specific risk, e.g., 'trend exhaustion', 'whipsaw in range', 'news event gap'>"
  ],
  "evidence": ["key=value", ...],
  "recommendation": "<suggested strategy type, e.g., 'Trend-following', 'Mean-reversion', or 'Sidelines'>",
  "confidence": <integer 0-100>,
  "missing_data": ["<missing field>", ...]
}

Rules:
- findings MUST follow the FACT/INTERPRETATION/RISK prefix pattern.
- If high volatility is detected relative to recent range, flag it in a RISK finding.
- If the price is near major daily/weekly levels (if provided), note it as a FACT.
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
        candle = self._get_result(tool_results, "latest_candle")
        stats = self._get_result(tool_results, "symbol_stats")

        if candle is None and stats is None:
            return None

        # Deterministic fallback
        deterministic = SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary="Market regime evidence is available from latest price data.",
            findings=["Grounding answer on the latest available symbol statistics and candle direction."],
            evidence=[f"symbol={tool_context.get('symbol')}"],
            recommendation="Analyze trend and volatility before confirming the setup.",
            confidence=70,
        )

        user_payload = {
            "task_class": task_class,
            "symbol": tool_context.get("symbol"),
            "timeframe": tool_context.get("timeframe"),
            "latest_candle": candle.payload if candle else None,
            "symbol_stats": stats.payload if stats else None,
        }

        raw = self._call_llm_plan(user_payload=user_payload)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=deterministic)

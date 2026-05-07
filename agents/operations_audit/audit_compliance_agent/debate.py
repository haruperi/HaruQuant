"""TradingAgents-style debate transcript storage."""

from __future__ import annotations

from typing import Any

from agents._shared.persistence import stable_id, utc_stamp, write_json_artifact


class DebateTranscript:
    def store(
        self,
        *,
        strategy_id: str,
        bull_memo: dict[str, Any],
        bear_memo: dict[str, Any],
        synthesis_memo: dict[str, Any],
        portfolio_decision: dict[str, Any],
        evidence_refs: list[str],
    ) -> dict[str, Any]:
        transcript = {
            "transcript_id": stable_id("debate", f"{strategy_id}-{utc_stamp()}"),
            "strategy_id": strategy_id,
            "bull_memo": bull_memo,
            "bear_memo": bear_memo,
            "synthesis_memo": synthesis_memo,
            "final_portfolio_manager_decision": portfolio_decision,
            "evidence_refs": evidence_refs,
        }
        transcript["transcript_uri"] = write_json_artifact("reports/board", f"{transcript['transcript_id']}.json", transcript)
        return transcript


__all__ = ["DebateTranscript"]

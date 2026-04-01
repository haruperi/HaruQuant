"""Deterministic report packaging for agent workflow outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from apps.agents.core.agent_models import AgentResult
from apps.agents.tools.report_tools import ReportTools


@dataclass(frozen=True)
class ReportSection:
    """One compact section in a report packet."""

    name: str
    status: str
    summary: str
    warnings: List[str] = field(default_factory=list)
    evidence_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class ReportPacket:
    """One generated report packet plus its packaged sections."""

    report_name: str
    title: str
    summary: str
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        payload = asdict(self)
        payload["sections"] = [section.to_dict() for section in self.sections]
        return payload


class AgentReporter:
    """Package existing workflow results into deterministic desk memos."""

    def __init__(self, report_tools: ReportTools) -> None:
        self.report_tools = report_tools

    def build_packet(
        self,
        *,
        report_name: str,
        title: str,
        summary: str,
        sections: List[ReportSection],
        metadata: Dict[str, Any] | None = None,
    ) -> ReportPacket:
        """Build one immutable report packet."""
        return ReportPacket(
            report_name=report_name,
            title=title,
            summary=summary,
            sections=list(sections),
            metadata=dict(metadata or {}),
        )

    def section_from_result(self, name: str, result: AgentResult) -> ReportSection:
        """Convert one workflow result into a compact report section."""
        return ReportSection(
            name=name,
            status=result.status,
            summary=result.summary,
            warnings=list(result.warnings or []),
            evidence_count=len(result.evidence or []),
            metadata=dict(result.metadata or {}),
        )

    def write_packet(self, packet: ReportPacket) -> Dict[str, Any]:
        """Persist JSON and Markdown artifacts for one packet."""
        json_artifact = self.report_tools.report_generate_json(
            report_name=packet.report_name,
            payload=packet.to_dict(),
        )
        markdown_artifact = self.report_tools.report_generate_markdown(
            report_name=packet.report_name,
            content=self.render_markdown(packet),
        )
        return {
            "report_packet": packet.to_dict(),
            "artifact_refs": [
                json_artifact["artifact_ref"],
                markdown_artifact["artifact_ref"],
            ],
        }

    def render_markdown(self, packet: ReportPacket) -> str:
        """Render one packet into a simple Markdown memo."""
        lines = [f"# {packet.title}", "", packet.summary, ""]
        for section in packet.sections:
            lines.append(f"## {section.name}")
            lines.append(f"- status: {section.status}")
            lines.append(f"- summary: {section.summary}")
            if section.warnings:
                lines.append(f"- warnings: {', '.join(section.warnings)}")
            lines.append(f"- evidence_count: {section.evidence_count}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

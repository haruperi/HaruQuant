"""Default tool catalog for the current agent foundation."""

from __future__ import annotations

from apps.agents.core.agent_models import ToolSpec
from apps.agents.core.policies import PermissionTier
from apps.agents.core.tool_registry import ToolRegistry
from apps.agents.tools.backtest_tools import BacktestTools
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.report_tools import ReportTools
from apps.agents.tools.risk_tools import RiskTools
from apps.agents.tools.workflow_tools import WorkflowTools


def build_default_tool_registry(
    *,
    edge_tools: EdgeTools | None = None,
    risk_tools: RiskTools | None = None,
    backtest_tools: BacktestTools | None = None,
    report_tools: ReportTools | None = None,
    workflow_tools: WorkflowTools | None = None,
) -> ToolRegistry:
    """Build the current default tool registry."""
    edge = edge_tools or EdgeTools()
    risk = risk_tools or RiskTools()
    backtest = backtest_tools or BacktestTools()
    reports = report_tools or ReportTools()
    workflows = workflow_tools or WorkflowTools()
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            tool_name="edge_list_snapshots",
            domain="edge",
            mode=PermissionTier.READ_ONLY,
            description="List saved Edge profile snapshots.",
        ),
        edge.edge_list_snapshots,
    )
    registry.register(
        ToolSpec(
            tool_name="edge_get_snapshot",
            domain="edge",
            mode=PermissionTier.READ_ONLY,
            description="Load one saved Edge profile snapshot.",
        ),
        edge.edge_get_snapshot,
    )
    registry.register(
        ToolSpec(
            tool_name="risk_get_snapshot_bundle",
            domain="risk",
            mode=PermissionTier.READ_ONLY,
            description="Load one stored risk snapshot bundle.",
        ),
        risk.risk_get_snapshot_bundle,
    )
    registry.register(
        ToolSpec(
            tool_name="risk_get_snapshot_report",
            domain="risk",
            mode=PermissionTier.READ_ONLY,
            description="Build one machine-readable risk report from storage.",
        ),
        risk.risk_get_snapshot_report,
    )
    registry.register(
        ToolSpec(
            tool_name="replay_get_report",
            domain="risk",
            mode=PermissionTier.READ_ONLY,
            description="Build one compact replay report from stored frames.",
        ),
        risk.replay_get_report,
    )
    registry.register(
        ToolSpec(
            tool_name="risk_run_what_if",
            domain="risk",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Run a safe hypothetical comparison on one replay frame.",
        ),
        risk.risk_run_what_if,
    )
    registry.register(
        ToolSpec(
            tool_name="backtest_get_run",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load one persisted backtest run.",
        ),
        backtest.backtest_get_run,
    )
    registry.register(
        ToolSpec(
            tool_name="backtest_get_trades",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load persisted trades for one backtest.",
        ),
        backtest.backtest_get_trades,
    )
    registry.register(
        ToolSpec(
            tool_name="backtest_get_finance_metrics",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load finance metrics for one backtest.",
        ),
        backtest.backtest_get_finance_metrics,
    )
    registry.register(
        ToolSpec(
            tool_name="optimization_get_run",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load one optimization run.",
        ),
        backtest.optimization_get_run,
    )
    registry.register(
        ToolSpec(
            tool_name="optimization_get_top_results",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load top optimization candidates.",
        ),
        backtest.optimization_get_top_results,
    )
    registry.register(
        ToolSpec(
            tool_name="validation_get_wfo_summary",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load walk-forward summary statistics.",
        ),
        backtest.validation_get_wfo_summary,
    )
    registry.register(
        ToolSpec(
            tool_name="validation_get_monte_carlo_summary",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load Monte Carlo summary statistics.",
        ),
        backtest.validation_get_monte_carlo_summary,
    )
    registry.register(
        ToolSpec(
            tool_name="validation_get_manifest",
            domain="validation",
            mode=PermissionTier.READ_ONLY,
            description="Load strategy version manifest metadata.",
        ),
        backtest.validation_get_manifest,
    )
    registry.register(
        ToolSpec(
            tool_name="edge_export_profile_report",
            domain="reporting",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Export one stored Edge snapshot report.",
        ),
        reports.edge_export_profile_report,
    )
    registry.register(
        ToolSpec(
            tool_name="risk_export_report",
            domain="reporting",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Export one stored risk snapshot report.",
        ),
        reports.risk_export_report,
    )
    registry.register(
        ToolSpec(
            tool_name="replay_export_report",
            domain="reporting",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Export one stored replay report.",
        ),
        reports.replay_export_report,
    )
    registry.register(
        ToolSpec(
            tool_name="report_generate_json",
            domain="reporting",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Write one generic JSON report artifact.",
        ),
        reports.report_generate_json,
    )
    registry.register(
        ToolSpec(
            tool_name="report_generate_markdown",
            domain="reporting",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Write one generic Markdown report artifact.",
        ),
        reports.report_generate_markdown,
    )
    registry.register(
        ToolSpec(
            tool_name="workflow_send_notification",
            domain="workflow",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Send a safe operator notification.",
        ),
        workflows.workflow_send_notification,
    )
    registry.register(
        ToolSpec(
            tool_name="workflow_trigger_n8n",
            domain="workflow",
            mode=PermissionTier.ADVISORY_WRITE,
            description="Queue one outbound workflow payload for future n8n delivery.",
        ),
        workflows.workflow_trigger_n8n,
    )
    return registry

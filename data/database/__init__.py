"""Database layer — migrations, SQLite managers, repositories, partitions."""

from data.database.partitions import resolve_partition_target
from data.database.migrations.runner import (
    MigrationRecord,
    apply_pending_migrations,
    default_migrations_dir,
)
from data.database.repositories.ai_chat_repository import (
    AiChatMemorySummaryRow,
    AiChatMessageRow,
    AiChatPinnedFactRow,
    AiChatRepository,
    AiChatSignalProposalRow,
    AiChatThreadRow,
)
from data.database.repositories.agentic_firm_repository import (
    AgenticFirmRepository,
    AgentTaskEventRecord,
    AgentTaskRecord,
    AuditLogRecord,
    EvidenceRefRecord,
)
from data.database.repositories.execution_repository import (
    ExecutionIntentRecord,
    ExecutionReceiptRecord,
    ExecutionRepository,
    ExecutionSendAttemptRecord,
    ReconciliationRunRecord,
)
from data.database.repositories.governance_repository import (
    ApprovalRecord,
    ApprovalVoteRecord,
    GovernanceRepository,
    KillSwitchEventRecord,
    StrategyPromotionRecord,
    StrategyRecord,
)
from data.database.repositories.proposal_repository import (
    ProposalRepository,
)
from data.database.repositories.research_audit_repository import (
    EvidenceBundleRecord,
    EvaluationReportRecord,
    LegalHoldRecord,
    ReplayBundleRecord,
    ResearchAuditRepository,
    TrajectoryLogRecord,
)
from data.database.repositories.risk_repository import (
    RiskRepository,
)
from data.database.repositories.workflow_repository import (
    IncidentRecord,
    WorkflowRecord,
    WorkflowRepository,
)

__all__ = [
    # Migrations
    "MigrationRecord",
    "apply_pending_migrations",
    "default_migrations_dir",
    # Repositories
    "AiChatMemorySummaryRow",
    "AiChatMessageRow",
    "AiChatPinnedFactRow",
    "AiChatRepository",
    "AiChatSignalProposalRow",
    "AiChatThreadRow",
    "AgenticFirmRepository",
    "AgentTaskEventRecord",
    "AgentTaskRecord",
    "ApprovalRecord",
    "ApprovalVoteRecord",
    "AuditLogRecord",
    "EvidenceBundleRecord",
    "EvidenceRefRecord",
    "EvaluationReportRecord",
    "ExecutionIntentRecord",
    "ExecutionReceiptRecord",
    "ExecutionRepository",
    "ExecutionSendAttemptRecord",
    "GovernanceRepository",
    "IncidentRecord",
    "KillSwitchEventRecord",
    "LegalHoldRecord",
    "ProposalRepository",
    "ReconciliationRunRecord",
    "ReplayBundleRecord",
    "ResearchAuditRepository",
    "RiskRepository",
    "StrategyPromotionRecord",
    "StrategyRecord",
    "TrajectoryLogRecord",
    "WorkflowRecord",
    "WorkflowRepository",
    # Partitions
    "resolve_partition_target",
]

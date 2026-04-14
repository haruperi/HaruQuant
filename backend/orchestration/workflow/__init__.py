"""Workflow orchestration modules — state machines, step implementations, and runners."""

from .kill_switch_transitions import (
    KILL_SWITCH_TRANSITIONS,
    is_allowed_kill_switch_transition,
)
from .proposal_transitions import (
    PROPOSAL_TRANSITIONS,
    is_allowed_proposal_transition,
)
from .incident_transitions import (
    INCIDENT_TRANSITIONS,
    is_allowed_incident_transition,
)
from .states import (
    IncidentState,
    KillSwitchState,
    ProposalState,
    WorkflowState,
)
from .transitions import WORKFLOW_TRANSITIONS, is_allowed_workflow_transition
from .services import WorkflowCreateRequest, WorkflowCreationService, WorkflowRuntimeService
from .persistence import (
    WorkflowStepRecord,
    WorkflowStepRecorder,
    WorkflowStepRequest,
    WorkflowTransitionEvent,
    WorkflowTransitionLogger,
)
from .validator import (
    WorkflowStateValidationError,
    WorkflowStateValidator,
    WorkflowValidationContext,
)
from .executor import (
    StepExecutionResult,
    WorkflowExecutionResult,
    WorkflowPlanExecutor,
)

# Step implementations and lightweight runner
from backend.agents.prompts.refine_template import REFINE_AGENT_INSTRUCTION
from .steps_data_transformation import (
    STEP_IMPLEMENTATIONS,
    WorkflowContext,
    step_backtest_strategy,
    step_clean_and_prepare_data,
    step_collect_market_data,
    step_create_features,
    step_define_strategy_or_model,
    step_evaluate_performance,
    step_generate_signals,
    step_refine_and_repeat,
)
from .steps_refine import (
    step_run_refinement_experiments,
    step_agent_evaluate_and_conclude,
)
from .step_runner import (
    WorkflowExecutor,
    WorkflowStepError,
)

__all__ = [
    # State machines
    "INCIDENT_TRANSITIONS",
    "IncidentState",
    "KILL_SWITCH_TRANSITIONS",
    "KillSwitchState",
    "PROPOSAL_TRANSITIONS",
    "ProposalState",
    "WORKFLOW_TRANSITIONS",
    "WorkflowState",
    "is_allowed_incident_transition",
    "is_allowed_kill_switch_transition",
    "is_allowed_proposal_transition",
    "is_allowed_workflow_transition",
    # Services
    "WorkflowCreateRequest",
    "WorkflowCreationService",
    "WorkflowRuntimeService",
    # Persistence
    "WorkflowStepRecord",
    "WorkflowStepRecorder",
    "WorkflowStepRequest",
    "WorkflowTransitionEvent",
    "WorkflowTransitionLogger",
    # Validation
    "WorkflowStateValidationError",
    "WorkflowStateValidator",
    "WorkflowValidationContext",
    # ADK executor
    "StepExecutionResult",
    "WorkflowExecutionResult",
    "WorkflowPlanExecutor",
    # Refine agent prompt
    "REFINE_AGENT_INSTRUCTION",
    # Step implementations
    "STEP_IMPLEMENTATIONS",
    "WorkflowContext",
    "step_backtest_strategy",
    "step_clean_and_prepare_data",
    "step_collect_market_data",
    "step_create_features",
    "step_define_strategy_or_model",
    "step_evaluate_performance",
    "step_generate_signals",
    "step_refine_and_repeat",
    "step_run_refinement_experiments",
    "step_agent_evaluate_and_conclude",
    # Lightweight runner
    "WorkflowExecutor",
    "WorkflowStepError",
]

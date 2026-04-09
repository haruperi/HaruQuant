export const operatorWorkflows = [
  {
    workflowId: "wf_trade_review_001",
    type: "trade_review",
    state: "RECONCILING",
    objective: "Review EURUSD breakout setup before simulated execution",
    owner: "orchestrator_agent",
    updatedAt: "2026-04-09T10:24:00Z",
    currentStep: "reconcile_receipts",
    transitionCount: 11,
    notes: [
      "Workflow entered reconciliation after broker receipt divergence.",
      "Replay coverage already includes strategy, risk, and execution phases.",
      "Operator supervision required before further send attempts.",
    ],
  },
  {
    workflowId: "wf_trade_review_002",
    type: "trade_review",
    state: "BLOCKED_BY_RISK",
    objective: "Validate GBPUSD reversal proposal under paper risk limits",
    owner: "risk_governor_agent",
    updatedAt: "2026-04-09T09:58:00Z",
    currentStep: "risk_decision_review",
    transitionCount: 7,
    notes: [
      "Volatility-adjusted sizing reduced original exposure request.",
      "Session restriction flagged London close proximity.",
      "Awaiting operator acknowledgement of constrained approval path.",
    ],
  },
] as const

export const selectedWorkflow = operatorWorkflows[0]

export const operatorProposals = [
  {
    proposalId: "prop_001",
    symbol: "EURUSD",
    direction: "BUY",
    readiness: "READY_FOR_RISK",
    state: "APPROVED_WITH_LIMITS",
    queuePosition: 1,
    expiryAt: "2026-04-09T10:40:00Z",
    riskDecision: "APPROVE_WITH_LIMITS",
    constraints: ["reduced_size", "spread_cap_1.8"],
  },
  {
    proposalId: "prop_002",
    symbol: "GBPUSD",
    direction: "SELL",
    readiness: "READY_FOR_RISK",
    state: "BLOCKED_BY_POLICY",
    queuePosition: 2,
    expiryAt: "2026-04-09T10:52:00Z",
    riskDecision: "REJECT",
    constraints: ["session_blackout"],
  },
] as const

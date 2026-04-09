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
    authorityState: "RECONCILING",
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
    authorityState: "PROVISIONAL",
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
    authorityState: "PROVISIONAL",
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
    authorityState: "AUTHORITATIVE",
    constraints: ["session_blackout"],
  },
] as const

export const operatorApprovals = [
  {
    approvalId: "appr_live_exec_001",
    actionType: "live_execution",
    targetRefId: "exec_001",
    state: "PENDING",
    requiredCount: 2,
    collectedVotes: 1,
    createdBy: "operator:desk_a",
    pendingRoles: ["approver"],
    expiresAt: "2026-04-09T10:38:00Z",
  },
  {
    approvalId: "appr_policy_001",
    actionType: "policy_change",
    targetRefId: "policy_003",
    state: "PENDING",
    requiredCount: 2,
    collectedVotes: 0,
    createdBy: "approver:risk_ops",
    pendingRoles: ["risk_manager", "compliance"],
    expiresAt: "2026-04-09T11:00:00Z",
  },
] as const

export const operatorIncidents = [
  {
    incidentId: "inc_001",
    severity: "critical",
    state: "OPEN",
    alertType: "broker_conflict",
    source: "reconciliation",
    summary: "Broker receipt diverged from local execution status.",
    recommendedAction: "Hold retries and review reconciliation evidence.",
    authorityState: "RECONCILING",
  },
  {
    incidentId: "inc_002",
    severity: "warning",
    state: "ACKNOWLEDGED",
    alertType: "stale_state",
    source: "monitoring",
    summary: "Market snapshot aged beyond short TTL.",
    recommendedAction: "Refresh market and account snapshots before risk review.",
    authorityState: "PROVISIONAL",
  },
] as const

export const operatorReplayBundles = [
  {
    replayBundleId: "rpb_001",
    workflowId: "wf_trade_review_001",
    completeness: "complete",
    exportProfile: "regulatory_export",
    manifestHash: "a91cf8d2f9e0c3",
    includedRefs: ["evidence_001", "log_001", "log_002", "receipt_001"],
    objectStoreUri: "memory://replay/rpb_001",
    authorityState: "AUTHORITATIVE",
  },
] as const

export const operatorEvidenceBundles = [
  {
    evidenceBundleId: "evidence_001",
    strategyId: "strat_001",
    lifecycleState: "PAPER_APPROVED",
    bundleType: "paper_report",
    contentHash: "hash_paper_bundle_001",
    contentRef: "memory://evidence/evidence_001",
    freshnessStatus: "fresh",
    artifactCount: 3,
    artifacts: [
      "equity_curve",
      "paper_summary",
      "risk_snapshot",
    ],
  },
  {
    evidenceBundleId: "evidence_002",
    strategyId: "strat_001",
    lifecycleState: "LIVE_LIMITED",
    bundleType: "live_limited_report",
    contentHash: "hash_live_bundle_002",
    contentRef: "memory://evidence/evidence_002",
    freshnessStatus: "fresh",
    artifactCount: 2,
    artifacts: [
      "live_limited_summary",
      "governance_signoff",
    ],
  },
] as const

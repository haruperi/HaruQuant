# Approval and Escalation Standard (Playbook §11)

## Action Classes

| Class | Description | Rule |
|---|---|---|
| A | Read-only, no side effect | Auto-allowed |
| B | Low-risk write, reversible | Allow with policy gate |
| C | Material write, approval-worthy | Require human approval |
| D | High-risk, financially material | Strict approval + audit |
| E | Irreversible or prohibited | Deny or special process |

## Approval Packet

Every Class C+ action requires:
- **action**: What will be done
- **reason**: Why it's needed
- **evidence**: Data supporting the decision
- **confidence**: 0.0–1.0 confidence score
- **uncertainty**: What is unknown
- **policy_checks_passed**: Which policies were checked
- **risk_class**: A through E
- **alternatives_considered**: Other options evaluated
- **expected_impact**: Financial/operational/risk impact
- **rollback_plan**: How to undo if wrong
- **escalation_triggers**: What would trigger escalation

## Escalation Triggers

Escalate when:
1. Policy conflict detected
2. Required evidence missing
3. Repeated failures (3+ in 1 hour)
4. Financial/compliance impact exceeds threshold
5. Security anomaly detected
6. Ambiguity unresolved after 2 refinement attempts

## Approval Workflow

```
Request → Policy Check → Build Packet → Route to Approver
  → Approve → Execute → Log
  → Reject → Compensate → Notify
  → Escalate → Human Review → Decision
```

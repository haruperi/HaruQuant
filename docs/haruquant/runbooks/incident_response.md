# Incident Response (Playbook §24)

## Incident Classes

| Severity | Description | Response Time |
|---|---|---|
| Sev 1 | Harmful or critical action executed, severe outage, data/security risk | 15 min |
| Sev 2 | Material workflow failure, repeated bad outputs, financial impact | 1 hour |
| Sev 3 | Degraded behavior, local failures, non-critical impact | 4 hours |
| Sev 4 | Minor issue, non-critical defect, cosmetic | Next business day |

## Response Checklist

1. **Contain impact**: Trigger kill switch if needed (§11.4)
2. **Preserve logs**: Snapshot all traces and span data
3. **Identify affected workflows**: Use observability to scope impact
4. **Compensate side effects**: Execute compensation plans from registry
5. **Notify stakeholders**: Alert on-call owner per component_owners.yaml
6. **Patch and validate**: Fix issue, run benchmark suite
7. **Run postmortem**: Complete postmortem template within 48 hours

## Kill Switch Activation

- **Who can trigger**: On-call owner, risk team lead, CTO
- **What it disables**: All execution and live trading workflows
- **Scope**: Global or per-domain
- **Recovery**: Dual-auth required, risk assessment before re-enable
- **Post-incident checks**: Verify all positions closed, audit logs intact

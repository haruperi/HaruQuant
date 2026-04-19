# Operations Runbook (Playbook §24 + §30)

## Daily Checks

1. **API Health**: `GET /api/health` → `{"status": "healthy"}`
2. **Database**: Check connection pool, run `SELECT 1`
3. **MCP Servers**: Verify all 6 servers respond to tool list
4. **Queue Depth**: Check pending workflow count
5. **Error Rate**: Review last 24h error logs

## Incident Response

| Severity | Response Time | Action |
|---|---|---|
| Sev 1 | 15 min | Kill switch → preserve logs → compensate → notify |
| Sev 2 | 1 hour | Isolate → patch → validate → notify |
| Sev 3 | 4 hours | Investigate → fix → verify |
| Sev 4 | Next business day | Triage → schedule fix |

## Kill Switch Procedure

1. Identify scope (global vs per-domain)
2. Execute: `kill_switch.trigger(scope="global")`
3. Verify all execution workflows halted
4. Assess side effects and compensate
5. Dual-auth recovery required to re-enable

## Common Runbooks

- **Stale risk decision**: Check freshness → re-evaluate → update
- **Failed workflow**: Inspect trace → identify failed step → compensate → retry
- **MCP server down**: Check health → restart → verify tools → requeue
- **Rate limit exceeded**: Check cost_tracker → adjust limits → resume
- **Policy violation**: Review policy check → update policy → re-run

## Postmortem

Complete postmortem template within 48 hours of any Sev 1-2 incident.
Template: `docs/haruquant/operations/runbooks/Postmortem_Template.md`

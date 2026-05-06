# Agent Plan Schema

CEO chat uses the canonical `agents.schemas.AgentPlan` model.

Important fields:

- `conversation_plan_id`
- `user_goal`
- `intent`
- `response_mode`
- `task_class`
- `risk_level`
- `requires_board_approval`
- `requires_risk_governor`
- `allowed_agents`
- `blocked_agents`
- `expected_outputs`
- `evidence_requirements`
- `failure_policy`

The planner must choose from the bounded route catalog in `agents/planner.py`.


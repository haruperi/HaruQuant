# Statistical Validation Agent

Standard HaruQuant Simulation Department agent.

This agent validates input, gathers evidence, optionally summarizes with LLM analysis,
applies deterministic policy, emits a structured `AgentResponse`, and records audit metadata.
It cannot execute trades, approve risk, approve live deployment, or hide failed tests.

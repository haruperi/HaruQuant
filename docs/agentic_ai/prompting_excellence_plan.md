# Prompting Excellence Implementation Plan

| Field | Detail |
|---|---|
| Document ID | HQT-PROMPTING-EXCELLENCE-PLAN |
| Status | ALL PHASES COMPLETE |
| Current Score | 10/10 |
| Target Score | 10/10 |
| Source | Agentic AI Code Review — "Prompting for Effective LLM Reasoning and Planning" |

---

## Audit Findings Summary

| # | Issue | Severity | Current Status |
|---|---|---|---|
| 1 | Prompts are 3-line hardcoded stubs | Critical | Weak |
| 2 | No Chain-of-Thought or ReAct prompting | Critical | Missing |
| 3 | No actual LLM integration (`AgentRuntime` has no implementation) | Critical | Missing |
| 4 | Workflow steps don't share context between stages | High | Weak |
| 5 | Evaluator findings not fed back to generator | High | Partial |
| 6 | No few-shot examples in any prompt | Medium | Missing |
| 7 | No instruction priority layering (system policy → user input → retrieved content) | Medium | Missing |
| 8 | Prompt injection markers are only 5 hardcoded strings | Medium | Weak |
| 9 | No prompt unit tests | Medium | Missing |
| 10 | No prompt retry/repair on validation failure | Low | Missing |

---

## Phase Ordering

```
Phase 1:  Expand Agent Prompts           (foundational — every phase depends on this)
Phase 2:  Implement GeminiAgentRuntime   (enables all LLM-based testing)
Phase 3:  Add Chain-of-Thought Prompting (reasoning structure)
Phase 4:  Implement ReAct Loop           (tool-aware reasoning)
Phase 5:  Wire Prompt Context Chaining   (workflow step context sharing)
Phase 6:  Feed Evaluator Findings Back   (refinement loops with actual feedback)
Phase 7:  Instruction Priority Layering  (security: trust hierarchy)
Phase 8:  Expand Retrieval Guard         (injection defense hardening)
Phase 9:  Prompt Unit Tests              (reliability)
Phase 10: Prompt Retry/Repair            (resilience)
```

---

## Phase 1: Expand Agent Prompts

### Goal
Replace all 13 hardcoded 3-line instruction strings with full 9-section prompts per Playbook §7.2.

### Current State
```python
# backend/agents/strategy_agent.py — 4 lines
STRATEGY_AGENT_INSTRUCTION = """
You are the HaruQuant StrategyAgent.
Generate evidence-backed trade hypotheses, compare candidate actions when needed,
and never emit broker orders or direct execution instructions.
All outputs must be emitted as canonical TradeHypothesis contracts.
""".strip()
```

### Target State
Each agent prompt has 9 sections:
1. **Role** — persona, expertise, tone
2. **Task** — specific objective
3. **Context** — what data/environment it operates on
4. **Tools** — what capabilities it can invoke
5. **Rules** — hard constraints (what it must never do)
6. **Constraints** — operational boundaries (position limits, risk caps)
7. **Escalation Conditions** — when to stop and escalate
8. **Output Schema** — the contract type and field descriptions
9. **Failure Behavior** — what to do when uncertain, confidence scoring, uncertainty reporting

### Tasks
- [x] Create `backend/agents/prompts/` directory with Jinja2-style template system
- [x] Create `PromptComposer` class that assembles prompt sections from config
- [x] Expand all 13 agent instructions to 9-section format
- [x] Add few-shot examples to orchestrator, strategy, compliance, and execution agents
- [x] Add confidence/uncertainty reporting to all prompts
- [x] Keep backward compatibility: `instruction` attribute still exists as assembled string

### Target Files
```
backend/agents/prompts/
  __init__.py                  # PromptComposer, assemble_agent_prompt()
  orchestrator_template.py     # 9-section orchestrator prompt
  strategy_template.py         # 9-section strategy prompt with examples
  execution_template.py        # 9-section execution prompt
  compliance_template.py       # 9-section compliance prompt
  research_template.py         # 9-section research prompt
  monitoring_template.py       # 9-section monitoring prompt
  risk_governor_template.py    # (deterministic — no prompt needed, just metadata)
  portfolio_template.py        # 9-section portfolio prompt
  volatility_template.py       # 9-section volatility prompt
  regime_template.py           # 9-section regime prompt
  drawdown_template.py         # 9-section drawdown prompt
  exposure_template.py         # 9-section exposure prompt
  correlation_template.py      # 9-section correlation prompt
  slippage_template.py         # 9-section slippage prompt
```

### Verification
- [x] All 13 agent instructions are ≥15 lines each with all 9 sections
- [x] At least 4 agents include few-shot examples
- [x] `PromptComposer.assemble(agent_name, context, tools)` produces well-structured prompts
- [x] Existing agent wrappers still work (backward compatible)

---

## Phase 2: Implement GeminiAgentRuntime

### Goal
Create a real `AgentRuntime` implementation that calls Google's Gemini API.

### Current State
```python
# backend/agents/runtime/runner.py — AgentRuntime has NO implementation
class AgentRuntime(Protocol):
    def run(self, *, request: ADKRunRequest, context: AgentExecutionContext) -> AgentExecutionResult: ...
```

### Target State
A `GeminiAgentRuntime` class that:
1. Takes the agent's instruction string as system prompt
2. Takes the request payload as user message
3. Calls Gemini API (`google.genai` or `google.genai.client`)
4. Parses the JSON response
5. Returns `AgentExecutionResult` with output payload, token usage, and tool calls

### Tasks
- [x] Add `google-genai` or `google-generativeai` to requirements
- [x] Create `backend/agents/runtime/gemini_runtime.py` with `GeminiAgentRuntime` class
- [x] Configure API key from `GOOGLE_API_KEY` env var (falls back to `backend/config/environments/.env`)
- [x] Use `AGENT_MODEL` from `backend/config/agent_model.py` as the model name
- [x] Enforce JSON output mode via `generation_config.response_mime_type = "application/json"`
- [x] Map Gemini response to `AgentExecutionResult` with token usage
- [x] Add timeout handling (configurable, default 60s)
- [x] Add error handling (API errors, rate limits, content safety blocks)
- [x] Add structured logging of prompt length, response length, latency, token usage

### Target Files
```
backend/agents/runtime/gemini_runtime.py   # GeminiAgentRuntime class
tests/unit/backend/agents/test_gemini_runtime.py  # Unit tests with mocked Gemini API
```

### Verification
- [x] `GeminiAgentRuntime` implements `AgentRuntime` protocol
- [x] Calling `.run()` with a valid request returns `AgentExecutionResult`
- [x] Token usage is reported in the result
- [x] API errors are caught and re-raised as `AgentRuntimeError`
- [x] Timeout errors fail closed with `final_state = "ERROR"`
- [x] Unit tests pass with mocked Gemini API

---

## Phase 3: Add Chain-of-Thought Prompting

### Goal
Every agent prompt enforces stepwise reasoning before output generation.

### Current State
No prompt contains any CoT instruction. Agents are told what to output but not how to reason.

### Target State
Each 9-section prompt includes a **Reasoning Process** section between Task and Tools:
```
REASONING PROCESS:
Before producing your output, reason through the problem step by step:
1. Analyze the input data and identify key patterns or anomalies
2. Evaluate each possible action against the constraints and rules
3. Cross-reference available evidence (market data, risk metrics, policy checks)
4. Identify any uncertainties or gaps in the available information
5. Only then produce the final output in the required schema

IMPORTANT: Your reasoning must be thorough but concise. Do not skip steps.
If any step reveals a constraint violation or escalation condition, stop and report it.
```

### Tasks
- [x] Add CoT reasoning process section to all 13 agent prompt templates
- [x] For evaluator-optimizer workflows, the CoT section must include self-evaluation criteria
- [x] For orchestrator agent, CoT must include workflow pattern selection reasoning
- [x] Add `CoT_SEPARATOR` constant to cleanly separate reasoning from final answer in response parsing
- [x] Ensure output validation strips CoT text from the final JSON payload

### Verification
- [x] All 13 prompt templates contain a REASONING PROCESS section
- [x] Output validator confirms CoT was performed (presence of reasoning markers)
- [x] CoT text is stripped from the final validated payload

---

## Phase 4: Implement ReAct Loop

### Goal
Tool-aware reasoning loop: Thought → Action → Observation → Thought → ... → Final Answer.

### Current State
No ReAct implementation exists. Agents receive a single prompt and produce a single output.

### Target State
A `ReActAgentRuntime` class that:
1. Receives initial request
2. Generates a Thought (what should I do next?)
3. Selects and executes a Tool (if needed)
4. Receives Observation (tool result)
5. Loops back to step 2 until it has enough information
6. Produces Final Answer

### Tasks
- [x] Create `backend/agents/react/` directory
- [x] Create `react_prompt.py` with ReAct instruction template:
  ```
  You are solving a task using tools. On each step, you must output:
  Thought: <what you need to do or figure out next>
  Action: <tool_name>(<arguments>)  -- OR -- Final: <your final answer>
  
  If you choose Action, wait for Observation before next step.
  If you choose Final, your answer must be a valid JSON matching the output schema.
  Maximum 10 steps. If you exceed this, stop and output your best answer.
  ```
- [x] Create `react_agent.py` with `ReActAgentRuntime` implementing the loop
- [x] Integrate with MCP tool registry to discover available tools
- [x] Implement step counter with max 10 iterations (enforced by `RefineLoopGuard`)
- [x] Parse Thought/Action/Observation/Final from LLM output
- [x] Handle tool execution errors as Observation text
- [x] Add timeout per step (default 30s)
- [x] Add unit tests with mocked LLM and mocked tool calls

### Target Files
```
backend/agents/react/
  __init__.py
  react_prompt.py              # ReAct instruction template
  react_agent.py               # ReActAgentRuntime
  test_react_agent.py          # Unit tests
```

### Verification
- [x] `ReActAgentRuntime` completes a full Thought → Action → Observation → Final cycle
- [x] Max step limit enforced (10 steps → best-effort final)
- [x] Tool errors are reported as Observations, not crashes
- [x] Final answer matches the expected contract schema
- [x] Unit tests pass with mocked tools

---

## Phase 5: Wire Prompt Context Chaining

### Goal
Sequential workflow steps share context — output of step 1 becomes context for step 2.

### Current State
`SequentialWorkflowRunner` runs steps in order but each step receives its original `ADKRunRequest` — no prior results are passed forward.

### Target State
```python
class SequentialWorkflowRunner:
    def run(self, *, steps: tuple[SequentialWorkflowStep, ...]) -> tuple[ADKRunResult, ...]:
        results = []
        context_chain: dict[str, Any] = {}
        for step in steps:
            # Inject prior step results as context
            request = replace(step.request, metadata={
                **step.request.metadata,
                "prior_steps": context_chain,
            })
            result = self._runner.run(agent=step.runtime_agent, request=request)
            context_chain[step.step_name] = {
                "output": result.output_payload,
                "state": result.final_state,
            }
            results.append(result)
        return tuple(results)
```

### Tasks
- [x] Modify `SequentialWorkflowRunner.run()` to build a `context_chain` dict
- [x] Inject `prior_steps` into each step's `request.metadata`
- [x] Add `context_summary` field to limit context size (summarize if > 4000 tokens)
- [x] Modify `EvaluatorOptimizerWorkflowRunner.run()` to include evaluation scores and refinement recommendations in each retry request
- [x] Modify `ParallelWorkflowRunner.run()` to include `peer_tasks` context so parallel results can reference each other's outputs

### Verification
- [x] Step 2's agent receives step 1's output in `request.metadata["prior_steps"]`
- [x] Evaluator-optimizer loop includes evaluation scores in retry request
- [x] Context chain does not exceed 4000 tokens (summary applied if needed)

---

## Phase 6: Feed Evaluator Findings Back to Generator

### Goal
Refinement loops include actual feedback — not just "try again."

### Current State
`EvaluatorOptimizerWorkflowRunner.run()` checks `score >= acceptance_threshold` but does not modify the generator's request between iterations.

### Target State
```python
for iteration in range(max_iterations):
    result = self._runner.run(agent=generator_step.runtime_agent, request=request)
    score = evaluator(result)
    scores.append(score)
    
    if score >= acceptance_threshold:
        break
    
    # Build refinement context
    recommendations = generate_refinement_recommendations(
        evaluation=evaluation_result,
        unsupported_assertions=unsupported_claims,
    )
    request = replace(request, metadata={
        **request.metadata,
        "refinement_iteration": iteration + 1,
        "previous_score": score,
        "improvement_actions": recommendations.improvement_actions,
        "focus_areas": recommendations.focus_areas,
    })
```

### Tasks
- [x] Modify `EvaluatorOptimizerWorkflowRunner.run()` to build refinement context
- [x] Use `generate_refinement_recommendations()` from `evaluator.py`
- [x] Include `refinement_iteration` counter in request metadata
- [x] Add agent prompt instruction to use refinement context: "If you receive refinement feedback, address each improvement action before resubmitting"
- [x] Add unit test verifying refinement context is passed between iterations

### Verification
- [x] Generator receives `improvement_actions` and `focus_areas` on retry
- [x] `refinement_iteration` counter increments correctly
- [x] Unit test confirms context is modified between iterations

---

## Phase 7: Instruction Priority Layering

### Goal
Strict trust hierarchy: system policy > workflow policy > agent instruction > user input > retrieved content > tool output.

### Current State
No instruction layering. All text is concatenated into a single prompt string with no trust boundaries.

### Target State
```python
class PromptComposer:
    def compose(self, *, agent_instruction: str, context: PromptContext) -> str:
        sections = []
        
        # Layer 1: System policy (highest trust)
        if context.system_policy:
            sections.append(f"[SYSTEM POLICY — DO NOT OVERRIDE]\n{context.system_policy}")
        
        # Layer 2: Workflow policy
        if context.workflow_policy:
            sections.append(f"[WORKFLOW POLICY]\n{context.workflow_policy}")
        
        # Layer 3: Agent instruction
        sections.append(f"[AGENT INSTRUCTION]\n{agent_instruction}")
        
        # Layer 4: User input
        if context.user_input:
            sections.append(f"[USER REQUEST]\n{context.user_input}")
        
        # Layer 5: Retrieved content (untrusted)
        if context.retrieved_content:
            sections.append(f"[RETRIEVED CONTEXT — UNVERIFIED]\n{context.retrieved_content}")
        
        # Layer 6: Tool output (untrusted)
        if context.tool_output:
            sections.append(f"[TOOL OUTPUT — RAW DATA]\n{context.tool_output}")
        
        return "\n\n---\n\n".join(sections)
```

### Tasks
- [x] Create `PromptComposer` class in `backend/agents/prompts/__init__.py`
- [x] Create `PromptContext` dataclass with all 6 layers
- [x] Add section delimiters with trust level annotations
- [x] Modify `GeminiAgentRuntime` to use `PromptComposer.compose()` before calling LLM
- [x] Add `RetrievalSafetyReport` check before injecting retrieved content
- [x] Update all agent wrappers to use `PromptComposer` instead of raw instruction strings

### Verification
- [x] Composed prompt contains all present layers in correct order
- [x] Retrieved content is wrapped with `[RETRIEVED CONTEXT — UNVERIFIED]` delimiter
- [x] User input is wrapped with `[USER REQUEST]` delimiter
- [x] System policy section is present and marked as non-overrideable

---

## Phase 8: Expand Retrieval Guard

### Goal
Replace 5 hardcoded injection markers with 20+ comprehensive patterns.

### Current State
```python
# backend/agents/runtime/retrieval_guard.py — 5 markers
_PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "reveal the system prompt",
    "system prompt",
    "execute trade now",
    "<tool>",
)
```

### Target State
```python
_PROMPT_INJECTION_MARKERS = (
    # Direct override attempts
    "ignore previous instructions",
    "ignore all previous",
    "disregard earlier",
    "override your instructions",
    "you are now",
    "new role:",
    # Prompt extraction
    "reveal the system prompt",
    "show your instructions",
    "repeat your prompt",
    "system prompt",
    # Command injection
    "execute trade now",
    "place order",
    "run this code",
    "evaluate this expression",
    # XML/tag injection
    "<tool>",
    "</tool>",
    "<system>",
    "</system>",
    "<instruction>",
    # Encoding tricks
    "\\u00",
    "base64:",
    "rot13",
    # Social engineering
    "this is a test environment",
    "you are in debug mode",
    "simulation mode",
    "no real consequences",
)
```

### Tasks
- [x] Expand `_PROMPT_INJECTION_MARKERS` to 25+ patterns
- [x] Add `_INDIRECT_INJECTION_MARKERS` for multi-step attack patterns
- [x] Add `_ENCODING_INJECTION_MARKERS` for Unicode/Base64/ROT13 tricks
- [x] Add `evaluate_retrieval_text(text)` that returns `RetrievalSafetyReport` with severity level (low/medium/high)
- [x] Add logging of detected markers for audit trail
- [x] Add unit tests for each marker category

### Verification
- [x] All 25+ markers are detected in sample text
- [x] Severity classification works (direct override = high, encoding = medium)
- [x] Unit tests cover all marker categories
- [x] No false positives on legitimate text

---

## Phase 9: Prompt Unit Tests

### Goal
Test each agent prompt produces valid contract output with mocked LLM responses.

### Current State
Zero tests verify prompt behavior against an LLM.

### Target State
```python
def test_strategy_agent_produces_valid_trade_hypothesis(mocked_gemini):
    """Strategy agent must produce valid TradeHypothesis when given market context."""
    runtime = GeminiAgentRuntime(model="gemini-3.1-flash-lite-preview")
    wrapper = StrategyAgentWrapper(
        runner=ADKRunnerService(ADKRunnerConfig("test")),
        output_validator=CanonicalOutputValidator(),
    )
    request = ADKRunRequest(
        workflow_id="test-1",
        correlation_id="corr-1",
        agent_name="strategy_agent",
        input_payload={"symbol": "EURUSD", "timeframe": "H1", "bars": 100},
    )
    result = wrapper.execute(runtime_agent=runtime, request=request)
    
    assert result.output_payload["contract_type"] == "TradeHypothesis"
    assert result.output_payload["schema_version"] == "1.0.0"
    assert "symbol" in result.output_payload
    assert "confidence" in result.output_payload
```

### Tasks
- [x] Create `backend/agents/prompts/test_prompts.py`
- [x] Add one test per agent: verifies output matches contract schema
- [x] Mock `GeminiAgentRuntime` to return predefined JSON responses
- [x] Add tests for failure cases: malformed LLM response, API timeout, content safety block
- [x] Add integration test: full sequential workflow with 3+ steps, verifying context chaining
- [x] Add ReAct unit tests: verify Thought → Action → Observation → Final cycle with mocked tools

### Verification
- [x] 13 agent prompt tests pass (one per agent)
- [x] 5 failure scenario tests pass
- [x] 1 context chaining integration test passes
- [x] 2 ReAct unit tests pass

---

## Phase 10: Prompt Retry/Repair

### Goal
When output validation fails, feed the error back to the LLM for self-correction instead of hard-failing.

### Current State
```python
# backend/agents/runtime/output_validation.py — hard fail
validated_model = validate_contract_payload(payload, self._registry)
# Raises ContractValidationError — no retry mechanism
```

### Target State
```python
class CanonicalOutputValidator:
    def validate_with_retry(
        self, payload: dict, *, max_retries: int = 1, repair_prompt: str | None = None
    ) -> CanonicalValidationResult:
        for attempt in range(max_retries + 1):
            try:
                return self.validate(payload)
            except ContractValidationError as exc:
                if attempt == max_retries:
                    raise
                # Feed error back via repair prompt
                payload = self._request_repair(payload, str(exc), repair_prompt)
    
    def _request_repair(self, payload: dict, error: str, repair_prompt: str | None) -> dict:
        repair_instruction = repair_prompt or (
            "Your previous output failed validation. Fix the following errors:\n"
            f"{error}\n\nReturn ONLY the corrected JSON."
        )
        # Call LLM with repair instruction (implemented in GeminiAgentRuntime)
        ...
```

### Tasks
- [x] Add `validate_with_retry()` method to `CanonicalOutputValidator`
- [x] Implement `_request_repair()` that calls the LLM with error feedback
- [x] Update `ADKRunnerService.run()` to use `validate_with_retry` with `max_retries=1`
- [x] Add `repair_attempted` field to `ADKRunResult`
- [x] Log repair attempts with original error and repaired output
- [x] Add unit tests: validation failure → repair → success, and validation failure → repair → still fails

### Verification
- [x] `validate_with_retry` succeeds on repairable error
- [x] `validate_with_retry` raises after max_retries exhausted
- [x] `repair_attempted` field is True when repair was attempted
- [x] Unit tests pass for both success and failure paths

---

## Cross-Cutting Concerns

### Logging
- Log prompt text (truncated to 500 chars, redacted) on every LLM call
- Log response text (truncated to 500 chars) on every LLM response
- Log token usage, latency, and cost on every run

### Configuration
- All prompt parameters (max CoT length, max ReAct steps, repair retries) configurable via `backend/config/agent_model.py`
- Environment variable overrides for all prompt parameters

### Documentation
- Update `docs/agentic_ai/Catalog.md` with expanded prompt descriptions
- Update `backend/agents/README.md` with prompt architecture diagram

---

## Dependencies

```
Phase 1 (Expand Prompts)      ← no dependencies
Phase 2 (Gemini Runtime)      ← no dependencies
Phase 3 (CoT)                 ← Phase 1 (needs expanded prompts)
Phase 4 (ReAct)               ← Phase 2 (needs Gemini runtime)
Phase 5 (Context Chaining)    ← no dependencies
Phase 6 (Evaluator Feedback)  ← Phase 5 (needs context chaining)
Phase 7 (Priority Layering)   ← Phase 1 (needs expanded prompts)
Phase 8 (Retrieval Guard)     ← no dependencies
Phase 9 (Prompt Tests)        ← Phase 2 (needs Gemini runtime for mocking)
Phase 10 (Retry/Repair)       ← Phase 9 (needs prompt tests infrastructure)
```

---

## Success Criteria

All phases complete when:

1. ✅ All 13 agent prompts are ≥15 lines with all 9 sections
2. ✅ `GeminiAgentRuntime` successfully calls Gemini API
3. ✅ All prompts include Chain-of-Thought reasoning process
4. ✅ `ReActAgentRuntime` completes full Thought → Action → Observation → Final cycle
5. ✅ Sequential workflow steps share context via `prior_steps` metadata
6. ✅ Evaluator-optimizer loop includes refinement recommendations in retry request
7. ✅ `PromptComposer` assembles prompts with strict trust hierarchy
8. ✅ Retrieval guard detects 25+ injection patterns with severity classification
9. ✅ 20+ prompt unit tests pass (13 agents + 5 failures + 2 ReAct)
10. ✅ `validate_with_retry` repairs validation errors before hard-failing

**Target Score: 10/10**

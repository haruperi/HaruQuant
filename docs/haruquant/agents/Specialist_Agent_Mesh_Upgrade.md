# HaruQuant Specialist Agent Mesh: Final Documentation

## Overview
The HaruQuant AI Assistant has been upgraded from a generic chatbot into a high-integrity, multi-agent reasoning mesh. It now operates as a layered runtime that interprets page state, consults specialized experts, and produces governed trading artifacts and UI actions.

## 1. System Architecture
The assistant follows a **Decoupled Reasoning Pipeline**:

1.  **Context Broker**: Aggregates structured page data (visible metrics, tables, charts) via the `PageIntelligenceContract`.
2.  **Conversation Planner**: Analyzes user intent to determine the `task_class` and selects which specialists to consult.
3.  **Specialist Mesh**: A set of bounded agents that provide evidence-led diagnostics using a mandatory **Fact-Interpretation-Risk (F/I/R)** model.
4.  **Synthesis Engine**: Merges specialist findings into a professional, narrative-driven response, suppressing internal markers for a clean UI experience.

---

## 2. Specialist Agent Roster

| Agent Name | Primary Responsibility | Key Inputs | Output Artifacts |
| :--- | :--- | :--- | :--- |
| **StrategyCreatorAgent** | Generates HaruQuant-compatible Python strategies. | Hypothesis, Params | Strategy Script, Schema |
| **StrategyCodeReviewAgent** | Technical sanity check (Look-ahead bias, API compliance). | Strategy Script | Technical Findings, Diffs |
| **BacktestExplainerAgent** | Performance diagnostic and drawdown analysis. | Metrics, Equity Curve | Performance Insights |
| **MarketRegimeAgent** | Analyzes trend, volatility, and session context. | Latest Candles, Stats | Regime Classification |
| **PortfolioRiskAgent** | Monitors exposure, concentration, and drawdown. | Positions, Floating PnL | Risk Caveats |
| **OptimizationAgent** | Ranks and compares parameter sets. | Optimization Results | Robustness Rankings |
| **PageOperatorAgent** | Maps intent to governed UI actions. | Action Affordances | Page Action Plan |
| **TradingAdvisorAgent** | Strategic synthesis and high-level advice. | Aggregated Insights | Strategic Narrative |

---

## 3. Priority Upgrades Delivered (1-8)

### Priority 1: Page Intelligence Contract
Implemented a structured data layer in the frontend. The assistant no longer "scrapes" the DOM; it reads canonical registration objects for **Metrics**, **Tables**, and **Charts**.

### Priority 2 & 3: Tool Attachments & Strategy Creator
Users can now attach specialized "Modes" (tools). The **Strategy Creator** tool generates production-ready HaruQuant artifacts instead of generic code snippets.

### Priority 4: Structured Planning
Replaced the keyword router with an LLM-driven planner that understands multi-step goals and ambiguity.

### Priority 5: Specialist Agent Roster
Built and integrated the full roster of 10 specialists (including previously deferred ones like `MarketRegime` and `CodeReview`).

### Priority 6: Governed Page Actions
Created a browser automation layer. The assistant can now navigate the UI (tabs, filters, exports) only through registered, risk-categorized affordances with user approval.

### Priority 7: Trading Advice Standard
Hardened all prompts to enforce a professional "Evidence-led" standard. Every strategic answer is grounded in visible data.

### Priority 8: Institutional Evaluation
Created a comprehensive evaluation suite with 4 new corpora to ensure regression-free upgrades and quality control.

---

## 4. UI Manual Verification Plan

To ensure the upgrade is working as intended, please perform the following manual tests in the UI:

### Test 1: Data Grounding (Priority 1)
1.  **Navigate** to a completed Backtest Result page.
2.  **Ask**: "What was the Net Profit and Maximum Drawdown for this run?"
3.  **Verification**: Ensure the assistant provides the exact values visible in the UI without guessing or hallucinating.

### Test 2: Strategy Creation (Priority 2 & 3)
1.  **Open** the Chat Panel and click the **[+]** button to attach the **Strategy Creator** tool.
2.  **Ask**: "Create a mean-reversion strategy for EURUSD M15 using Bollinger Bands."
3.  **Verification**: Check that a **Strategy Artifact Card** appears. Click the code preview to ensure it's a valid HaruQuant `on_bar` script.

### Test 3: Governed UI Action (Priority 6)
1.  **Navigate** to the **Optimization** page.
2.  **Ask**: "Switch to the Monte Carlo tab."
3.  **Verification**: Ensure the assistant produces an **Action Plan Preview**. Click **Approve** and verify the UI actually switches to the correct tab.

### Test 4: Professional Reasoning (Priority 7)
1.  **Ask** a strategic question like "Why did this backtest underperform in December?".
2.  **Verification**: Look for a response that separates **Facts** (e.g., "The volatility increased by 40%") from **Interpretations** (e.g., "The trend following logic was whipsawed").

### Test 5: Market Regime Awareness (Priority 5 completion)
1.  **Navigate** to the **Live Trading Dashboard**.
2.  **Ask**: "What is the current market regime for EURUSD right now?"
3.  **Verification**: Ensure the response includes a specific classification (Trending/Ranging) based on the latest candle data.

---

## 5. Governance & Safety
*   **Trading Actions**: No trades can be executed directly from chat. High-risk intents create **Action Drafts** for manual review.
*   **Auditability**: Every specialist artifact and page action plan is persisted in the thread metadata for audit logging.
*   **Sandboxing**: Strategy code is validated for banned operations (e.g., file system access, network calls) during the creation phase.

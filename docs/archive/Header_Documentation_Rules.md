# Generic File Header Documentation — Agent Rules & Template

This standard defines how **summary documentation at the top of every file** must be written.
The goal is that a developer or AI agent can understand a file’s purpose, structure, and responsibilities **without reading the full implementation**.

This format is **language-independent** and must appear at the very beginning of each source file.

---

# 🎯 Objectives

A valid file header must:

* Explain **what the file does**
* Describe **why it exists**
* List major **classes/functions**
* Summarize responsibilities
* Clarify dependencies or constraints
* Provide quick architectural context

It is NOT:

* Full documentation
* A copy of code comments
* A changelog

---

# 📐 Formatting Rules

## 1. Placement

* Must be the **first block** in the file.
* Appears before imports/includes.

## 2. Length

* Keep between **10–40 lines**.
* Must be concise and scannable.

## 3. Tone

* Technical
* Direct
* No marketing language
* No unnecessary explanations

---

# 🧱 Required Sections

Every file header must include the following sections.

---

## FILE PURPOSE

Explain in 1–3 sentences:

* What problem this file solves
* Where it fits in the system
* Its primary responsibility

Example:

> Handles portfolio-level risk calculations and exposure aggregation across multiple strategies.

---

## RESPONSIBILITIES

Bullet list describing:

* Core duties of this file
* What logic belongs here

Example:

* Position sizing calculations
* Risk normalization
* Exposure aggregation

---

## MAIN COMPONENTS

List all major structures defined in this file.

Format:

* `ClassName` — Short description
* `function_name()` — What it does

Example:

* `RiskEngine` — Core risk calculation engine
* `calculate_margin()` — Computes margin usage
* `normalize_volume()` — Adjusts lot size

---

## DATA FLOW (Optional but Recommended)

Explain how data moves through this file.

Example:

> Receives trade signals → applies risk rules → outputs validated orders.

---

## DEPENDENCIES / INTEGRATION

Mention important relationships:

* External modules used
* Systems interacted with
* Expected inputs/outputs

Example:

* Consumes normalized OHLCV data
* Used by Execution Engine
* Emits RiskDecision objects

---

## DESIGN NOTES / CONSTRAINTS

Short architectural guidance:

* Performance assumptions
* Thread safety
* Determinism
* Stateless vs stateful behavior

Example:

> Must remain stateless to allow parallel portfolio simulation.

---

# 🧩 Optional Sections (Use When Needed)

## PUBLIC API

List externally intended classes/functions.

## SIDE EFFECTS

Logging, file writes, state mutation, etc.

## FUTURE EXTENSIONS

Planned evolutions or boundaries.

---

# 🧾 Standard Header Template

Agents must follow this exact structure:

```
FILE: <filename>

PURPOSE:
<Short description of why this file exists and what it solves>

RESPONSIBILITIES:
- ...
- ...
- ...

MAIN COMPONENTS:
- ClassName — description
- function_name() — description

DATA FLOW:
<Input → Processing → Output summary>

DEPENDENCIES:
- Internal modules:
- External systems:

DESIGN NOTES:
- Performance assumptions
- Threading model
- Constraints
```

---

# 🤖 Agent Rules When Generating Headers

Agents must:

1. Summarize intent — not implementation details.
2. Avoid duplicating inline docstrings.
3. Keep descriptions under one line per item.
4. Prefer architectural language over code language.
5. Update header when file responsibilities change.
6. Never exceed 40 lines.

---

# ✅ Good Header Characteristics

* A new engineer understands the file in 10 seconds.
* A reviewer knows where logic belongs.
* An AI agent can navigate the codebase faster.

---

# ❌ Bad Header Characteristics

* Too verbose
* Explains obvious syntax
* Duplicates inline comments
* Lists every private helper

---

# Summary

This header acts as a **navigation layer** for large systems.

Every file must begin with a concise architectural overview describing:

* Why it exists
* What it owns
* What it exposes
* How it fits into the system

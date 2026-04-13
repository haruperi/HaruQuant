# Generic Agent Rules — Test Creation Standards (Language-Independent)

These rules define how automated agents (or developers) must design, write, and maintain tests across any language or technology stack.
The focus is **reliability, coverage, correctness, and long-term maintainability**, not just writing many tests.

---

# 1. Coverage Requirements

## 1.1 Minimum Coverage Threshold

* A build **must fail** if coverage drops below **80%**.
* Coverage exists to ensure core logic is exercised — not to reach artificial 100%.

## 1.2 Meaningful Coverage

Agents must prioritize:

* Decision branches
* Critical algorithms
* Risk-sensitive logic
* State transitions

Avoid:

* Testing trivial getters/setters
* Testing language features already guaranteed by the runtime

---

# 2. Logic-Focused Testing

## 2.1 Test the “Brain”

Tests must validate:

* Algorithms
* Calculations
* Decision trees
* Rule engines
* State machines
* Data transformations

## 2.2 Avoid Implementation Coupling

Tests must verify **observable behavior**, not internal steps.

Good:

* Input → Output validation
* State change verification
* Event emission

Avoid:

* Checking which internal helper functions were called
* Tightly coupling tests to internal structure

---

# 3. Edge Case & Failure Testing

## 3.1 Mandatory Edge Cases

Agents must generate tests covering:

* Zero values
* Negative values
* Empty inputs
* Missing fields
* Invalid formats
* Extremely large inputs
* Boundary conditions

## 3.2 Failure Path Testing

Error handling is part of the public contract.

Tests must validate:

* Correct error type or result state
* No partial or corrupted state
* Safe recovery behavior

---

# 4. Deterministic Tests (No Flakiness)

Tests must produce identical results on every run.

Agents must:

* Control randomness (seed or inject RNG)
* Freeze or mock time sources
* Avoid order-dependent assertions
* Eliminate race conditions

Flaky tests are considered failing tests.

---

# 5. Test Speed & Isolation

## 5.1 Unit Test Constraints

Unit tests must:

* Run locally in seconds
* Require no internet access
* Not connect to real databases
* Not call live APIs
* Not depend on external filesystems

Use:

* Mock data
* Stubs
* In-memory structures

## 5.2 Mocking Policy

Mock only **external system boundaries**:

Allowed:

* Network
* Database
* Broker/API
* Filesystem

Avoid:

* Mocking core business logic
* Mocking mathematical calculations

---

# 6. Test Structure & Separation

Agents must categorize tests into levels:

### Unit Tests

* Fast
* Fully isolated
* Pure logic validation

### Integration Tests

* Validate subsystem interaction
* May use real dependencies

### End-to-End Tests

* Validate full workflows
* Slowest layer
* Run less frequently

---

# 7. Property & Invariant Testing

When applicable, agents should create invariant tests.

Instead of testing single examples, verify rules such as:

* Results remain within valid bounds
* Values never become negative when prohibited
* Serialization/deserialization is lossless
* Risk limits are never exceeded

---

# 8. Readability & Maintainability

Tests are production code.

Agents must:

* Use clear naming conventions
* Keep tests short and focused
* Use reusable fixtures or builders
* Avoid duplicated setup logic

Each test should validate **one behavior only**.

---

# 9. Assertions Quality

Good tests fail for the correct reason.

Agents must:

* Assert meaningful outcomes
* Avoid overly brittle string comparisons
* Avoid asserting unnecessary internal details

---

# 10. Performance Awareness

Tests must not:

* Load massive datasets unless required
* Execute expensive loops unnecessarily
* Introduce artificial delays

If large data testing is required, use:

* Minimal synthetic datasets
* Sampling techniques

---

# 11. Mutation Resistance (Advanced)

A strong test suite detects subtle logic changes.

Agents should design tests that would fail if:

* Comparison operators change
* Boundary conditions shift
* Logic branches invert

---

# 12. Agent Behavioral Guidelines

When generating tests automatically, agents must:

1. Identify critical logic modules first.
2. Generate edge-case tests before happy-path tests.
3. Ensure deterministic execution.
4. Avoid coupling tests to internal implementation.
5. Maintain speed and isolation standards.
6. Enforce coverage thresholds.
7. Prefer clarity over quantity.

---

# Summary

A valid test suite must be:

* Deterministic
* Fast
* Logic-focused
* Behavior-driven
* Failure-aware
* Maintainable
* Coverage-enforced

The objective is not “more tests”, but **trustworthy verification of system behavior**.

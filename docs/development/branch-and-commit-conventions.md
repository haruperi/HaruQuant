# Branch and Commit Conventions

## Purpose

This guide defines the minimum branch and commit conventions for the HaruQuant migration work.

The goal is simple:
- keep each change small
- keep each branch focused on one primary task
- make requirement traceability easy to inspect from git history

## Branch Naming

Use short, task-focused branch names:

`<type>/<scope>-<short-description>`

Recommended branch types:
- `feat`
- `fix`
- `chore`
- `docs`
- `test`
- `refactor`

Examples:
- `docs/phase0-adr-vector-store`
- `feat/contracts-canonical-envelope`
- `test/replay-bundle-smoke`
- `chore/phase1-db-baseline`

Branch naming rules:
- use lowercase only
- separate words with hyphens
- keep the scope short and stable
- create one branch for one primary implementation-plan task when possible

## Commit Messages

Use a conventional format:

`<type>(<scope>): <summary>`

Examples:
- `docs(adr): record vector store decision`
- `feat(contracts): add canonical envelope model`
- `test(schema): add workflow intent validation cases`
- `chore(ci): add migration smoke workflow`

Commit message rules:
- keep the summary imperative and specific
- describe the actual change, not the intention
- prefer one primary concern per commit
- align the scope with the implementation-plan task area where possible

## Task-to-Commit Policy

For migration work, prefer:
- one implementation-plan checklist item per commit
- one primary task per pull request
- one requirement-focused change set at a time

If a task needs supporting edits:
- keep them in the same commit only when they are required to complete that task
- defer unrelated cleanup to a later task

## Traceability Expectations

Each task-oriented commit should make it easy to answer:
- what plan item was completed
- what requirement area it supports
- what docs/tests were updated with it

Recommended practice:
- use the suggested commit message from `docs/agentic_ai/implementation_plan.md` unless there is a clear reason to adjust it
- mention the completed plan item in the PR description
- keep docs and tests close to the code change they describe

## What To Avoid

- long-lived mixed-purpose branches
- large “misc cleanup” commits
- combining multiple unchecked plan items into one commit
- ambiguous commit subjects like `updates`, `changes`, or `wip`

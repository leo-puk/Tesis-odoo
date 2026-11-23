---
name: tesis-software-riguroso
description: Define, implement, refactor, or review software for the Tesis-odoo R1-R4 artifacts with explicit method-first contracts, requirement-to-evidence traceability, and only the code required by approved acceptance criteria. Use for thesis software work in this repository; do not use for ordinary thesis prose or unrelated utilities.
---

# Tesis Software Riguroso

Build only what the approved thesis method requires, and preserve evidence that the implementation satisfies it.

## Canonical thesis source

Before making a claim about the thesis, locate `consulta-tesis/README.md` in the workspace and read the relevant linked Markdown sections. Treat that folder as the only thesis source. Do not consult Word files, PDFs, drafts, notes, or historical deliverables unless the user explicitly requests it. If the folder is missing or internally inconsistent, report the gap instead of guessing.

For result-specific work, read [references/results.md](references/results.md) after the canonical thesis sections. The canonical thesis wins if the reference has become stale; update the reference in the same change when appropriate.

## Required workflow

### 1. Establish the work unit

Identify exactly one primary result or shared infrastructure unit: R1, R2.1, R2.2, R3, R4.1, R4.2, or an explicitly approved cross-cutting concern. State what is outside the unit.

Inspect the repository before proposing structure. Reuse an existing convention only when it remains justified by the current contract.

### 2. Define the method before code

If no approved contract covers the requested behavior, prepare one using [references/method-contract.md](references/method-contract.md). Do not implement until the user approves choices that materially affect scientific validity, scope, inputs, outputs, baselines, metrics, or external cost.

The contract must connect:

`thesis objective -> expected result -> requirement -> acceptance criterion -> validator -> evidence`

Use observable behavior and exact schemas or commands. Distinguish thesis requirements, implementation decisions, assumptions, and exclusions.

### 3. Design the smallest sufficient change

Map every proposed file, dependency, public symbol, configuration value, and output field to an approved requirement or validator. Remove any item without such a mapping.

Prefer the Python standard library and existing project dependencies. Add a dependency only when the contract identifies the capability it supplies, why the existing stack is insufficient, the pinned version, and its licensing or reproducibility impact.

Do not add speculative extension points, placeholder modules, unused abstractions, silent fallbacks, compatibility layers without a named target, duplicate models, generic helper collections, dashboards, services, or deployment infrastructure unless the contract requires them.

### 4. Define validation before implementation

Create or identify the failing validator before changing production code. A validator may be a focused automated test, schema check, fixture comparison, exact CLI invocation, statistical calculation, or recorded manual review when automation is impossible.

Tests must assert behavior and scientific invariants, not implementation trivia. Include negative and boundary cases that follow from the contract. Do not inflate test counts with equivalent cases.

### 5. Implement one vertical behavior

Make the smallest coherent change that turns the validator green. Keep acquisition, normalization, analysis, transformation, evaluation, and reporting separable when their evidence or failure modes differ.

Core evaluation behavior must be deterministic. Record versions, revisions, configuration, inputs, seeds when applicable, and generated artifact hashes. Do not allow network state, wall-clock time, unordered iteration, or mutable external defaults to silently change an evaluated result.

Use comments only for a non-obvious invariant, thesis decision, or external constraint. Do not narrate the code.

### 6. Verify and audit the diff

Follow [references/verification-gates.md](references/verification-gates.md). Run the narrow validator first and the proportional regression suite afterward.

Before completion, inspect the diff and ask of every addition: "Which approved requirement or validator requires this?" Remove additions without a concrete answer.

Report the commands run, pass/fail results, artifacts produced, known limitations, and any acceptance criterion not exercised. Never describe an unexecuted check as passing.

## Change boundaries

- Preserve unrelated user changes and artifacts.
- Do not weaken, delete, or skip a test merely to obtain a passing run.
- Do not alter evaluation samples, labels, baselines, or thresholds after seeing final-sample results unless the thesis method explicitly defines and records a new independent iteration.
- Keep secrets, credentials, private data, and licensed source material out of commits and evidence bundles.
- Ask before external writes, paid model calls, long-running experiments, or changes that broaden the approved work unit.

## Completion condition

A work unit is complete only when its approved acceptance criteria have corresponding executed validators and reproducible evidence, the relevant regression checks pass, and the final diff contains no unmapped implementation.

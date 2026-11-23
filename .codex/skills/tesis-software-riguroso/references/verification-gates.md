# Verification gates

Apply gates in this order. A gate may be marked not applicable only with a reason tied to the approved contract.

## 1. Contract gate

- The contract is approved and names its canonical thesis sections.
- Every acceptance criterion has a validator and evidence artifact.
- Construction, tuning, and final evaluation data are separated where the method requires independence.

## 2. Static gate

- Formatting and static analysis pass using repository-pinned tools.
- New dependencies are pinned and justified.
- No secret, credential, private datum, generated cache, or local absolute path is staged.
- Public schemas, command names, exit codes, and ordering rules match the contract.

## 3. Focused behavior gate

- Each changed behavior has an executed positive validator.
- Contract-derived error, empty, boundary, and malformed-input paths are exercised.
- A bug fix includes evidence that the validator fails without the fix when practical.

## 4. Regression gate

- Run tests for directly affected modules.
- Run integration tests across component boundaries changed by the work.
- For shared schemas or evaluation logic, run all consumers and the metric calculations that depend on them.
- Treat flaky, skipped, or unavailable checks as unresolved evidence, not passes.

## 5. Reproducibility gate

- Record exact command, source revision, environment version, configuration, inputs, seed when applicable, and output locations.
- Hash immutable input and result artifacts used for thesis measurements.
- Repeat timing or stochastic measurements according to the canonical method; do not generalize from an unrecorded single run.

## 6. Minimality gate

Inspect the final diff and map each added file, dependency, public symbol, configuration entry, and output field to a criterion or validator. Remove:

- unused code and imports;
- duplicated parsing or domain models;
- speculative generalization;
- comments that restate syntax;
- compatibility behavior without a named supported target;
- fallback behavior that hides invalid or missing evidence;
- generated artifacts not required as committed evidence.

## 7. Result gate

Report:

- criteria satisfied and their evidence;
- commands executed and actual outcomes;
- criteria not exercised;
- deviations from the approved method;
- limitations that constrain the claim;
- final changed-file list.

Do not claim completion while an approved criterion lacks executed evidence.

# Method contract

Use this contract before implementing a new behavior or materially changing an existing one. Keep it concise; omit a field only when it is demonstrably not applicable.

## Identification

- Contract ID: stable identifier such as `R2.2-QUERY-001`.
- Primary thesis result: R1, R2.1, R2.2, R3, R4.1, or R4.2.
- Canonical thesis sections: exact paths under `consulta-tesis/`.
- Status: proposed, approved, implemented, or verified.

## Scientific purpose

- Claim or decision this behavior supports.
- Indicator or comparison affected.
- Baseline, ground truth, or reference data, if any.
- Independence constraints: construction data, tuning data, and final evaluation data.

## Behavioral contract

- Actor or caller.
- Inputs, types, allowed ranges, and provenance.
- Preconditions.
- Processing rule at the level needed to reproduce the method.
- Outputs and exact schema.
- Error behavior and exit status when applicable.
- Determinism and ordering rules.
- Explicit exclusions.

## Acceptance table

For every criterion record:

| Criterion ID | Given | When | Then | Validator | Evidence artifact |
| --- | --- | --- | --- | --- | --- |
| `<ID>` | Initial state | Operation | Observable result | Exact test or command | Exact output path or record |

Each criterion must be necessary. Split criteria only when they exercise distinct behavior or failure modes.

## Minimal implementation map

List the files or public symbols expected to change and the criterion that requires each one. This is a forecast, not permission to generate scaffolding. Reconcile it with the final diff.

## Reproducibility record

Specify the versions, source revisions, configuration, random seeds, execution environment, timestamps, and hashes that must be captured. Use `not applicable` with a reason rather than leaving ambiguity.

## Approval and change control

Record the approved scope and any later method change separately. A result observed on the final evaluation sample is not a valid reason to retroactively tune the method on that sample.

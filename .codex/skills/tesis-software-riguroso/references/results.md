# Result-specific constraints

Read only the section for the result in scope, after reading the corresponding canonical files under `consulta-tesis/`. These notes route implementation decisions; they do not replace the thesis.

## R1: migration profile

- Produce a profile per module and installation before migration.
- Cover incompatibilities by layer and type, coupling, size, and whether manual work remains beyond rule-based tools.
- Derive coupling from declared dependencies and justified static references; preserve evidence for inferred edges.
- Keep `odoo-bin upgrade_code` and `odoo-module-migrator` as the documented comparison baseline when the canonical method requires them.
- Preserve the paired nature of classification results and the inputs needed for the exact McNemar comparison.
- Keep prediction evidence separate from the human migration used as evaluation ground truth.

## R2.1: local migration information

- Keep planning, versioned acquisition, normalization, persistence, and initial code crossing distinguishable in code and evidence.
- Every information unit must retain version, layer, technical entity, source, revision, and locator when available.
- Inspect addon manifests and technical references before limiting source diffs to relevant paths.
- Persist the collection locally and make the source revisions and acquisition failures auditable.
- R2 supplies migration evidence; it does not correct code or certify functional equivalence.

## R2.2: retrieval and CLI

- The CLI is local and in English.
- Keep relation extraction, graph traversal, ranking, query, reporting, and evaluation independently testable.
- Preserve the evaluated traversal depth, result limit, filters, ordering, and deduplication rules in configuration and evidence.
- Compare the proposed retrieval method with BM25 using the same collection, queries, limits, versions, and relevance judgments.
- Report empty results explicitly; do not remove them from evaluation or treat them as success.
- Keep C1, P1, C2, V1, and T1 definitions aligned with the canonical method. Do not invent a superiority target for complementary measures.
- Stable structured output is the machine contract; presentation output must be derived from it.

## R3: functional equivalence

- Compare origin and destination behavior in isolated Odoo/PostgreSQL environments with controlled input data.
- Run destination module tests and verify that source tests were not deleted or disabled.
- Derive deterministic comparison cases from detected incompatibilities and extended behavior.
- Report equivalence only within the executed cases and list silent divergences and surviving obsolete constructions.
- Keep the defect set, regression oracle, sensitivity sample, and specificity sample auditable and separate.
- R3 must not invoke the language model used by R4.

## R4.1: static incompatibility detector

- Analyze the four in-scope layers: Python, XML, data, and manifest.
- Every finding needs a stable identifier, location, layer, type, applicable version jump, and source evidence.
- Separate detection from transformation so precision and coverage can be evaluated independently.
- Preserve raw findings before filters or presentation aggregation.

## R4.2: multiclass migration

- Determine migration units and order from the approved coupling model.
- Apply deterministic transformations before language-model-assisted transformations.
- Give the model only the affected context and retrieved evidence required by the contract; record the fixed model version, request configuration, and response artifact.
- For non-consecutive jumps, process each intermediate version and report those results separately.
- Accept a migration unit only after module tests and R3 verification pass, including required regression checks for already accepted coupled units.
- Evaluate success by installation, unchanged tests, R3 equivalence, and automated resolution indicators defined in the thesis, not by textual similarity to a human patch.

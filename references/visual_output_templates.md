# Visual Output Templates v3

## Design Goals

1. HTML digest must provide faster evidence navigation than raw source reading.
2. Every high-risk claim must remain machine-checkable via `data-*` attributes.
3. Theory papers require layered rendering: setup -> lemmas -> theorem -> edge examples.
4. Comparative mode must preserve paper ownership (`Paper A` / `Paper B`) at claim level.

## Mandatory UI Blocks

1. Hero summary (`id="architecture"`) with one-sentence takeaway.
2. Interactive controls (search or filters) for claim-level scanning.
3. Claim cards with full metadata:
   - `data-claim-id`
   - `data-claim-class`
   - `data-anchor`
   - `data-severity`
   - `data-source-location`
4. Evidence ledger panel (`id="ledger"`).
5. Gate panel (`id="gate"`) showing strict mode and final gate status.

## Theory-Specific Granularity

Theory template should emphasize micro-structure rather than a single narrative block:

1. Setup section (`id="setup"`) with separate visual boxes for primitives.
2. Lemma section (`id="lemmas"`) with claim-level statement and intuition.
3. Theorem section (`id="theorems"`) with equation block and proof sketch.
4. Numerical section (`id="examples"`) for boundary-case interpretation.

## Review-Specific Granularity

Review template should emphasize thematic strand structure:

1. Scope section (`id="scope"`) with central question and review boundaries.
2. Framework section (`id="framework"`) with the author's organizing taxonomy rendered as a visual grid.
3. Strands section (`id="strands"`) with one claim card per thematic strand, each containing:
   - Literature synthesis narrative
   - Mini-grid of key papers
   - Debate/open question box
4. Cross-cutting section (`id="crosscut"`) for integrative patterns across strands.
5. Frontier section (`id="frontier"`) for explicit future research directions.
6. Interactive strand filter toolbar for rapid thematic navigation.

## Bilingual Presentation

Default language mode is bilingual:

1. Keep technical symbols and formulas unchanged.
2. Keep `claim_text` parseable for guard checks.
3. Expose bilingual context in visible prose blocks.

## Visual Enhancements

1. Severity stripe color (`BLOCKING`, `MAJOR`) for quick triage.
2. Class filters (`Result`, `Numeric`, `Equation`, `Causal`, `Metadata`).
3. Search box to locate anchor/location text.
4. Dense evidence table for comparative mode.

## Guard Compatibility Checklist

1. Required section ids exist for selected template family.
2. Ledger ids and digest claim ids are 1:1 aligned.
3. Anchor text is displayed and machine-readable.
4. No extra `data-claim-id` cards unless ledger includes matching claim.

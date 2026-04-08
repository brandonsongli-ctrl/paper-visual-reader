# Anti-Hallucination Module v3 — Paper Visual Reader

Deterministic gate policy paired with `scripts/anti_hallucination_guard.py`.

## Severity and Gate Mapping

- `BLOCKING` -> gate `FAIL`
- `MAJOR` -> gate `FAIL`
- `MINOR` -> gate `WARN`
- `STYLE` -> informational

## Claim Decision Matrix

| Claim Class | Required Anchor | Typical Failure | Severity | Gate Action |
|---|---|---|---|---|
| `Result` | section/table/figure/page | unsupported finding or missing anchor | BLOCKING | fail |
| `Equation` | eq identifier + page | mismatch or source equation absent | BLOCKING | fail |
| `Numeric` | table/figure/page | untraceable number token | BLOCKING | fail |
| `Causal` | result + identification anchor | causality upgrade beyond source language | MAJOR | fail |
| `Mechanism` | model/data anchor | presented as proven with no support | MAJOR | fail |
| `Citation` | bibliography/citation anchor | citation token not in source | MAJOR | fail |
| `Speculation` | optional | speculation framed as fact | MINOR | warn |
| `Metadata` | title page/bibliography | wrong author/journal/year | MAJOR | fail |

## Fixed Thresholds

Equation similarity:

- PASS: `score >= 0.90`
- WARN: `0.75 <= score < 0.90`
- FAIL: `score < 0.75`

## Eight-Round Verification Protocol

### Round 1: Source Declaration

Each claim must have non-empty `source_location`.

### Round 2: Anchor Completeness and Syntax

Tier-A classes require non-empty anchor with location tokens (`§`, `p.`, `Table`, `Figure`, `Eq.`).

### Round 3: Numeric Traceability

Numeric tokens in Tier-A/Tier-B claims must be present in source text. Anchor-only numbers (`Section 2`, `p.8`) are ignored as noise.

### Round 4: Equation Alignment

Equation claims are aligned with source equations. Equation extraction prioritizes ledger claim text and avoids title/anchor contamination.

### Round 5: Causal Verb Calibration

If source uses hedged language (`suggests`, `consistent with`, `associated with`), digest must not use proof language (`proves`, `establishes`, `definitive evidence`).

### Round 6: Citation Existence

Citation claims must match source citation signals via both author-year and cite-key channels.

### Round 7: Cross-Claim Consistency

Detect inconsistent numeric statements across claims sharing anchor-class groups. Mode C also enforces claim-id and paper-tag ownership consistency.

### Round 8: Template Coverage

Enforce minimum claim coverage and required section IDs by template family.

### Round 9: Stylistic Consistency

Strictly enforce two core formatting constraints:
1. **Pronoun Matching**: If the source text predominantly uses singular author pronouns (I/my/me), the digest cannot use plural author pronouns (we/our/us). If the source uses plural, the digest cannot use singular.
2. **Em Dash Prohibition**: Em dashes (`—`) are strictly forbidden in digest claims unless the exact phrase containing the em dash is a verbatim, direct quote from the source text.

### Round 10: Notation Grounding (Structural Hallucinations)

The generated "Notation Glossary" within `.analysis-box.notation` elements is strict-parsed. 
If the AI defines a mathematical variable using structural keywords (`set`, `set of`, `space`, `space of`, `matrix`, `vector`), but that specific structural word does not exist *anywhere* in the source text, it triggers a BLOCKING FAIL. This prevents the LLM from substituting generic economic definitions (e.g. hallucinating "$A$ is a set of candidates") for context-specific variables (e.g. "$A$ is candidate A").

### Round 11: LaTeX Rendering Sanity Check

Detects corrupted LaTeX formulas caused by Python string escape interpretation:
- `\to` → `\t` (tab) + `o` — destroys arrows
- `\nabla` → `\n` (newline) + `abla` — destroys gradient symbols
- `\right` → `\r` (carriage return) + `ight` — destroys delimiters
- `\beta` → `\b` (backspace) + `eta` — destroys Greek letters

The guard scans all `$$ ... $$` and `$ ... $` blocks for tab, newline, carriage return, and backspace characters. Any match triggers a BLOCKING FAIL. Additionally, an odd count of single `$` delimiters triggers a MAJOR WARN for unmatched math delimiters.

### Round 12: Per-Claim Semantic Content Grounding

For each non-Metadata, non-Speculation claim, verify that text content is genuinely grounded in the source paper (not filler/fabricated text with correct HTML structure). Three sub-checks per claim:

1. **Token Overlap Ratio**: Content words (excluding stopwords) in the claim must overlap with source at >= 45% (PASS) or >= 30% (WARN). Below 30% triggers FAIL.
2. **4-gram Grounding Score**: Sliding 4-gram windows from claim content tokens checked against source. Below 12% triggers FAIL, below 25% triggers WARN.
3. **Sentence Similarity Floor**: Each claim sentence (>25 chars) must have at least one source sentence with similarity >= 0.35. Ungrounded sentences trigger FAIL.

Claims with fewer than 15 content tokens are exempt. Tier-A class failures are BLOCKING; others are MAJOR.

### Round 13: Raw Text Injection Detection

Detects when the digest is a raw copy-paste of source text rather than a visual digest. Measures 15-gram overlap between digest plain text and source text. Above 65% triggers MAJOR FAIL; above 40% triggers MINOR WARN.

### Round 14: Interpretation Density

Ensures the digest contains genuine interpretation content, not just structural wrappers around copied text. Checks:
1. Global ratio of interpretation-box/analysis-box/intuition content vs total words (threshold: 15%).
2. Per-card check: content cards (>80 words) must contain at least one interpretation element.

Only activates when the digest uses the interpretation-box convention.

### Round 15: Structural Diversity (Type-Token Ratio)

Computes type-token ratio (TTR) of digest visible text. Padded/repeated text produces very low TTR. Below 0.12 triggers MAJOR FAIL; below 0.20 triggers MINOR WARN. Only activates for digests with >= 100 words.

### Round 16: Content Volume Audit

Verifies that the digest visible-text word count (excluding HTML tags, scripts, styles) is at least 50% of the source paper word count. This is a dynamic hard floor scaled to the specific paper being processed. Thin, skeletal digests that omit most of the paper's content trigger BLOCKING FAIL and must be regenerated.

- Source word count: `len(source_text.split())`
- Digest word count: visible text after stripping `<script>`, `<style>`, and all HTML tags
- Activation threshold: source must have >= 200 words (tiny test fixtures are exempt)
- Threshold: digest words / source words >= 0.50
- Below 0.50: BLOCKING FAIL

## Mode C Requirements

- Non-metadata claims require explicit paper tag in `source_location`.
- `paper_id` should map one-to-one with source paper tag.
- `A_*` claims must map to Paper A; `B_*` claims must map to Paper B.
- Multiple paper tags in one claim are BLOCKING.

## Optional Strictness Controls

- `--strict`: WARN blocks delivery.
- `--fail-on-major`: MAJOR WARN/FAIL blocks delivery even when strict is off.
- `--require-min-claims`: enforce minimum extractive coverage.

## Output Policy

- PASS: deliver digest + audit artifacts.
- WARN: deliver only if strict is off and major override is off.
- FAIL: block and emit blocked report.

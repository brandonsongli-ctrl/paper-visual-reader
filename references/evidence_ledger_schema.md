# Evidence Ledger Schema — EvidenceLedgerV1 (v3 extension)

Use for `visual_digest_<paper>.evidence_ledger.json`.

## Canonical Object

```json
{
  "version": "EvidenceLedgerV1",
  "mode": "A",
  "source": "paper.pdf",
  "template_family": "empirical",
  "language": "bilingual",
  "claims": [
    {
      "claim_id": "R1",
      "claim_class": "Result",
      "claim_text": "Main finding summary.",
      "anchor": "Table 2, p.14",
      "source_location": "Main Paper §4.2",
      "severity": "BLOCKING",
      "confidence": 0.94,
      "status": "VERIFIED",
      "notes": "Matches baseline column.",
      "paper_id": "A",
      "paper_tag": "A",
      "tier": "A",
      "evidence_quote": "...",
      "numeric_tokens": ["1.25", "320"],
      "equation_fingerprint": "y_i=alpha+beta*x_i+epsilon_i",
      "anchor_type": "table",
      "source_excerpt": "Section 4 (p.14) ...",
      "source_hash": "sha256...",
      "bilingual": {
        "en": "Main finding summary.",
        "zh": "中文释义: Main finding summary."
      },
      "mode_tag": "A"
    }
  ]
}
```

## Required Claim Fields

- `claim_id` (string)
- `claim_class` (enum)
- `claim_text` (string)
- `anchor` (string; Tier-A cannot be empty)
- `source_location` (string)
- `severity` (enum)
- `confidence` (number, 0..1)
- `status` (enum)
- `notes` (string)

## Optional Claim Fields (v3)

- `paper_id` (string; recommended in Mode C)
- `paper_tag` (string; `A`/`B`...)
- `tier` (`A`/`B`/`C`)
- `evidence_quote` (string)
- `numeric_tokens` (string array)
- `equation_fingerprint` (string)
- `anchor_type` (`section|table|figure|equation|appendix`)
- `source_excerpt` (string)
- `source_hash` (string, usually SHA256)
- `bilingual` (object with `en` and `zh`)
- `mode_tag` (`A`/`B`/`C`)

## Enums

### claim_class

- `Result`
- `Equation`
- `Numeric`
- `Causal`
- `Mechanism`
- `Citation`
- `Speculation`
- `Metadata`

### severity

- `BLOCKING`
- `MAJOR`
- `MINOR`
- `STYLE`

### status

- `VERIFIED`
- `UNVERIFIED`
- `UNREADABLE`
- `SPECULATIVE`

## Tier-A Anchor Rule

Tier-A classes:

- `Result`
- `Equation`
- `Numeric`
- `Causal`
- `Citation`

Tier-A claims require non-empty anchors with concrete location tokens.

## Mode C Consistency Rule

For non-metadata claims in mode C:

- include explicit paper tag in `source_location`
- include `paper_id`
- keep `paper_id` and `paper_tag` aligned with source paper tag

## Validation Hints

- Keep `claim_id` unique in ledger.
- Keep `confidence` numeric and normalized.
- Avoid placeholder-only anchors.
- Keep `numeric_tokens` synchronized with claim text when present.

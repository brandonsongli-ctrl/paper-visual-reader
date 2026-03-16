# Blocked Delivery Report

## Summary

- Gate status: `{{GATE_STATUS}}`
- Strict mode: `{{STRICT_MODE}}`
- Fail-on-major: `{{FAIL_ON_MAJOR}}`
- Mode: `{{MODE}}`
- Template family: `{{TEMPLATE_FAMILY}}`
- Source: `{{SOURCE}}`
- Digest: `{{DIGEST}}`

Delivery is blocked. Final HTML is not releaseable.

## Error Codes

{{ERROR_CODES}}

## Blocking Reasons (Group A)

{{BLOCKING_REASONS}}

## Major Risk Reasons (Group B)

{{MAJOR_REASONS}}

## Minor Warnings (Group C)

{{MINOR_REASONS}}

## Round Buckets

{{ROUND_BUCKETS}}

## Required Remediation Plan

### Phase 1 — Hard failures

1. Resolve all Group A errors.
2. Re-verify anchors and source-location mapping.
3. Re-run guard after each correction batch.

### Phase 2 — Major distortions

1. Rewrite causal/mechanism language to match source strength.
2. Fix numeric/citation mismatches.
3. Re-run guard and check major count reaches zero.

### Phase 3 — Coverage quality

1. Ensure required template sections and minimum claim count are satisfied.
2. Ensure unreadable markers are correctly handled.

## Artifact Paths

- Ledger: `{{LEDGER}}`
- Guard report (MD): `{{REPORT_MD}}`
- Guard report (JSON): `{{REPORT_JSON}}`
- Blocked report: `{{BLOCKED_REPORT}}`

## Next Command

```bash
python3 scripts/anti_hallucination_guard.py \
  --source "{{SOURCE}}" \
  --digest "{{DIGEST}}" \
  --ledger "{{LEDGER}}" \
  --report "{{REPORT_MD}}" \
  --json-report "{{REPORT_JSON}}" \
  --blocked-report "{{BLOCKED_REPORT}}" \
  --mode {{MODE}} \
  --template-family {{TEMPLATE_FAMILY}} \
  --strict
```

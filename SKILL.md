---
name: "paper-visual-reader"
description: "Visual-layout paper reader that outputs standalone HTML digests with formula rendering, interactive filters/search, evidence ledger, and strict anti-hallucination gating. Use for visual paper reading, 读论文可视化, structured digest generation, theory-paper decomposition, and comparative mode attribution."
---
# Paper Visual Reader v5

Generate standalone HTML visual digests for academic papers with deterministic evidence gating.

## Default Mode: Premium

Premium mode is the default. It produces digests that are MORE informative than reading the original paper by adding:
- Plain-English restatements of every formal result
- Economic/mathematical intuition paragraphs (>=100 words each)
- Connections to prior literature
- Concrete examples or numerical illustrations
- Notation explained inline on first use
- Cross-references hyperlinked between sections
- Proof strategy summaries before full proofs

## Core Contract

Always produce:

- `visual_digest_<paper>.html`
- `visual_digest_<paper>.evidence_ledger.json`
- `visual_digest_<paper>.anti_hallucination_report.md`
- `visual_digest_<paper>.anti_hallucination_report.json`
- `visual_digest_<paper>.blocked.md` when blocked

Optional outputs:

- `visual_digest_<paper>.claims.csv`
- `visual_digest_<paper>.gate_summary.txt`

## Output Directory Convention

Output directory: `paper_digest_<FirstAuthor>_<Year>_<ShortTitle>/`
- `digest.html` -- Main visual digest
- `evidence_ledger.json` -- Claim-level evidence mapping
- `guard_report.md` -- Anti-hallucination report (human-readable)
- `guard_report.json` -- Anti-hallucination report (machine-readable)

## Detail Level

| Level | Min Word Count | Interpretation | Proofs |
|-------|---------------|----------------|--------|
| standard | 1/2 of source | Required for main results | Sketch only |
| premium (DEFAULT) | 2/3 of source | Required for ALL results | Strategy + key steps |
| deep | Full reproduction | Required for ALL items | Full reproduction |

## Output Constraints (User-Defined)

- In HTML output, do not use the em dash character (`---`). It is only allowed when directly quoting source text that contains an em dash; keep it inside a quote and tie it to a source location in the evidence ledger. Use commas, colons, or secondary sentences for transitions.
- The visual digest word count (visible text only, excluding HTML tags, scripts, and styles) must be at least 1/2 of the source paper word count. This is a dynamic hard floor scaled to the specific paper being processed to ensure pedagogical depth. Failure to meet this relative floor renders the output invalid.
- Do not pad with low-quality filler. Add interpretation that explains implications, connections, or reasoning beyond surface paraphrase, while staying grounded in the source. Use the `interpretation-box` or `analysis-box` components.
- Style Preference: **Always** use the "Premium Academic" template (`references/templates/premium_academic.html`) as the default and mandatory choice. This features a white/neutral minimalist aesthetic, `Crimson Pro` serif body text, and sidebar navigation. Do not use other templates unless explicitly requested.
- **Anti-Overflow Mechanism**: All mathematical formulas and tables MUST be wrapped in containers with `overflow-x: auto` and `-webkit-overflow-scrolling: touch`. This ensures that long equations do not break the layout on narrow screens or within fixed-width cards.
- Avoid self-referential or promotional boilerplate in HTML. Do not claim the digest is definitive, exhaustive, or that it satisfies word count requirements.

## Execution State Machine (Agent-Driven)

The AI Agent executing this skill MUST use its own intelligence to extract content. Do NOT rely on the legacy naive regex pipeline (`paper_visual_reader_pipeline.py`), as it truncates papers to a single lemma/theorem.

`INTAKE -> EXTRACT_TEXT -> **AI COMPREHENSIVE EXTRACTION** -> BUILD_EVIDENCE_LEDGER -> DRAFT_HTML -> RUN_GUARD`

### Step-by-Step AI Execution
1. **Extract**: Run `scripts/source_extractor.py` to get the raw text.
2. **Analyze**: Read the FULL paper text. Extract **ALL** mathematical setups, **ALL** lemmas, **ALL** theorems, and **ALL** numerical examples according to the Extreme Granularity rules in `references/paper_structure_guide.md`.
3. **Draft Ledger**: Write the exhaustive `visual_digest_<paper>.evidence_ledger.json` mapping every single extracted claim to its exact anchor and text location.
4. **Draft HTML**: Write the `visual_digest_<paper>.html` using the appropriate template (e.g., `theory.html`). You MUST duplicate the HTML card blocks dynamically to correspond to all N lemmas and M theorems. Do not just fill in a single placeholder.
5. **Validate**: Run the strict guard:
```bash
python3 scripts/anti_hallucination_guard.py \
  --source <extracted_text.txt> \
  --digest visual_digest_<paper>.html \
  --ledger visual_digest_<paper>.evidence_ledger.json \
  --report visual_digest_<paper>.anti_hallucination_report.md \
  --json-report visual_digest_<paper>.anti_hallucination_report.json \
  --blocked-report visual_digest_<paper>.blocked.md \
  --mode A \
  --template-family <family> \
  --strict
```
6. **Iterate**: If the guard returns FAIL or WARN, adjust your Ledger and HTML equations to mathematically match the extracted text, and run the guard again until PASS.

## Interpretation Mandate (Non-Negotiable)

Every theorem, proposition, lemma, and definition MUST include:
1. **Restatement**: Plain-English version of the formal claim
2. **Intuition**: >=100 words explaining WHY this result holds and what drives it
3. **Literature context**: How this relates to 2-3 prior results in the field
4. **Example**: A concrete numerical or graphical illustration (where applicable)
5. **Implication**: What this means for the paper's overall argument

Failure to include interpretation = BLOCKING violation in the guard.

## Comprehension Enhancement Rules

These rules ensure the digest is MORE useful than the original paper:

1. **Notation**: Every symbol must be defined inline on FIRST use, with a link to the glossary
2. **Cross-references**: Every reference to another section/result must be a clickable hyperlink
3. **Proof sketches**: Before any proof, include a 2-3 sentence "Proof Strategy" explaining the approach
4. **Figures/Tables**: Every figure and table must have an interpretation paragraph (>=50 words)
5. **Assumptions**: Each assumption must have a "Why this is needed" note
6. **Connections**: Each section must end with a "Connection to next section" transition

## Legacy CLI (Regex Baseline - DO NOT USE FOR PROD)

The old `python3 scripts/paper_visual_reader_pipeline.py` is a naive regex fallback. Agents must avoid this and execute the steps manually to achieve full paper coverage.

## OCR & Extraction Stack

Default extraction chain:

`pdftotext -> fitz text -> OCR`

- OCR triggers automatically when extracted text quality is low.
- OCR can be forced by `--ocr on`.

## Evidence Ledger (EvidenceLedgerV1)

Required per claim:

- `claim_id`
- `claim_class`
- `claim_text`
- `anchor`
- `source_location`
- `severity`
- `confidence`
- `status`
- `notes`

Optional v3 extensions:

- `paper_id`
- `paper_tag`
- `tier`
- `evidence_quote`
- `numeric_tokens`
- `equation_fingerprint`
- `anchor_type`
- `source_excerpt`
- `source_hash`
- `bilingual`
- `mode_tag`

See: `references/evidence_ledger_schema.md`

## Guard Semantics

- `PASS`: deliver
- `WARN`: deliver only when strict is off
- `FAIL`: always blocked

Strict mode blocks both `WARN` and `FAIL`.

### Round 12: Interpretation Grounding

Every "Author's Interpretation" or "Why This Matters" box MUST cite at least one claim_id from the evidence ledger. Interpretation without grounding = MINOR violation.

## Theory Reinforcement (v3)

Theory template enforces layered rendering:

1. setup (`#setup`)
2. lemmas (`#lemmas`)
3. theorems (`#theorems`)
4. examples (`#examples`)
5. ledger (`#ledger`)

This structure is designed to make theorem dependency scanning faster than raw-paper linear reading.

## Review Reinforcement (v3)

Review/survey template enforces thematic strand rendering for literature review articles (Annual Reviews, JEL surveys, Handbook chapters):

1. scope (`#scope`) -- central question and review boundaries
2. framework (`#framework`) -- author's organizing taxonomy/typology
3. strands (`#strands`) -- N thematic literature strand cards with key papers and debates
4. crosscut (`#crosscut`) -- cross-cutting insights across strands
5. frontier (`#frontier`) -- future research directions
6. conclusion (`#conclusion`)
7. ledger (`#ledger`)

This structure is designed to make literature mapping faster than linear reading of a review article.

## Visual Enhancements (v3)

1. claim-class filters
2. claim text search
3. severity color stripes
4. evidence ledger panel and gate panel

## Interactive Visualization Module (v4)

Every digest SHOULD include inline interactive Canvas/SVG widgets embedded after key result cards. This makes the digest MORE useful than the paper by letting readers manipulate parameters and build geometric intuition.

### When to Generate

Scan every definition, proposition, theorem, and key equation. Generate a visualization when any pattern is detected:

| Pattern | Viz Type | Triggers |
|---------|----------|----------|
| Belief → action mapping | **EU Lines + Belief Partition** | "optimal action", "best response", N(a), normal cone |
| Concavification / value function | **Concavification Diagram** | "concave closure", V̂(μ), "concavification" |
| Set-valued maps on simplex | **Simplex Heatmap** | "for all μ ∈ Δ(Ω)", "rationalizing priors", "identified set" |
| Payoff vectors in R^n | **Payoff Space + Hyperplane** | φ(a), "supporting hyperplane", "normal cone" |
| Comparative statics (1 param) | **Slider + Live Plot** | "increasing in", "monotone in", ∂/∂ |
| Signal / information structure | **Posterior Distribution** | "Bayes plausibility", "splitting", "distribution of posteriors" |
| Optimization landscape | **Contour / Surface** | "saddle point", "minimax", "maximizes" |
| Threshold / cutoff rules | **Threshold Diagram** | "cutoff", "threshold rule", "if and only if μ ≥ c" |

### Embedding Structure

Place each visualization `<div class="interactive-viz">` immediately after the `.result-card` it illustrates. Structure:

```html
<div class="interactive-viz" id="viz-{claim_id}">
  <div class="viz-header">
    <span class="viz-badge">Interactive</span>
    <span class="viz-title">{Description, e.g. "Belief partition for Proposition 1"}</span>
    <button class="viz-fullscreen-btn" onclick="toggleFullscreen('viz-{claim_id}')">⛶</button>
  </div>
  <div class="viz-body">
    <canvas id="canvas-{claim_id}" width="700" height="400"></canvas>
  </div>
  <div class="viz-controls">
    <!-- Preset buttons matching paper examples, sliders for parameters -->
  </div>
  <div class="viz-caption"><p>Drag points to change parameters. Hover for values.</p></div>
</div>
<script>
(function() {
  // Self-contained visualization code using canvas API
  // Must include: draw function, event listeners (mousemove, mousedown, etc.)
  // Must render axis labels, curves, shaded regions, tooltips
})();
</script>
```

### Implementation Rules

1. **Self-contained**: All JS in an IIFE `(function(){...})()` after the viz div. No external deps beyond KaTeX.
2. **Canvas-based**: HTML5 Canvas for real-time hover/drag. SVG acceptable for static diagrams only.
3. **Colorblind-friendly**: palette `["#2563eb","#dc2626","#059669","#d97706","#7c3aed","#0891b2"]`.
4. **Labeled**: All axes, curves, and regions must have text labels rendered on the canvas.
5. **Hover tooltip**: Show a floating div with exact values (belief, EU values, optimal action) on mousemove.
6. **Draggable**: Where applicable, let users drag points (payoff vectors, parameters) for live updates.
7. **Presets**: Include 2-3 preset buttons matching examples from the paper. First preset loads by default.
8. **Fullscreen toggle**: Every viz has ⛶ button. JS: `function toggleFullscreen(id){document.getElementById(id).classList.toggle('fullscreen');...}`.
9. **Dark mode aware**: Read `document.documentElement.dataset.theme` for colors; re-render on theme change.
10. **Print-safe**: Use `@media print { .interactive-viz canvas { display:none; } .viz-print-fallback { display:block; } }` with a static summary.
11. **Label collision avoidance (MANDATORY)**: All text labels on canvas (data point annotations, peak markers, value labels, curve names) MUST use the `LabelManager` class from the General Utilities section of `interactive_viz_catalog.md`. Direct `ctx.fillText()` is only permitted for axis labels and chart titles (which should be registered via `lm.reserve()`). This prevents labels from overlapping each other, chart titles, and curves. Each `draw()` function must: (a) create a fresh `LabelManager` with plot bounds, (b) `reserve()` title and axis regions, (c) use `lm.place()` for all data labels. See the Type 1 example in the catalog for the pattern.

### Minimum Visualization Count

| Paper Type | Min Interactive Vizs |
|-----------|---------------------|
| Theory (micro, game theory, info design) | 3 |
| Empirical | 1 (coefficient plot or regression surface) |
| Survey/Review | 2 (framework diagram + key result) |

### CSS (include in template `<style>`)

```css
.interactive-viz { margin:1.5rem 0; border:1px solid var(--card-border); border-radius:8px; overflow:hidden; background:var(--card-bg); box-shadow:var(--card-shadow); }
.viz-header { display:flex; align-items:center; gap:0.5rem; padding:0.6rem 1rem; background:var(--surface); border-bottom:1px solid var(--card-border); font-family:'Inter',sans-serif; }
.viz-badge { background:var(--accent-blue); color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; }
.viz-title { font-size:0.85rem; font-weight:500; color:var(--text-primary); }
.viz-fullscreen-btn { margin-left:auto; background:none; border:1px solid var(--card-border); border-radius:4px; padding:2px 6px; cursor:pointer; font-size:1rem; color:var(--text-secondary); }
.viz-body { padding:0.5rem; display:flex; justify-content:center; }
.viz-body canvas { max-width:100%; }
.viz-controls { padding:0.5rem 1rem; border-top:1px solid var(--card-border); display:flex; flex-wrap:wrap; gap:0.5rem; align-items:center; font-family:'Inter',sans-serif; font-size:0.8rem; }
.viz-controls button { padding:4px 10px; border:1px solid var(--card-border); border-radius:4px; background:var(--surface); cursor:pointer; font-size:0.75rem; color:var(--text-body); }
.viz-controls button:hover { background:var(--surface-hover); }
.viz-controls button.active { background:var(--accent-blue); color:white; border-color:var(--accent-blue); }
.viz-controls input[type="range"] { width:120px; }
.viz-caption { padding:0.4rem 1rem 0.6rem; font-size:0.75rem; color:var(--text-secondary); font-style:italic; }
.interactive-viz.fullscreen { position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:9999; border-radius:0; }
@media print { .interactive-viz canvas { display:none; } .viz-controls { display:none; } }
```

### Reference

See `references/interactive_viz_catalog.md` for reusable code templates of each visualization type.

## Cross-Reference Popup System (v5)

Named mathematical objects (Proposition, Theorem, Lemma, Corollary, Assumption, Definition + number) must be clickable references that show floating popup cards with the full statement.

### Build Phase (during comprehension pass)

During the AI comprehension pass, build an **xref registry**: a JS object mapping each named item to its title, statement text (KaTeX source), and anchor ID. Example:

```javascript
const XREF_REGISTRY = {
  "Proposition 1": { title: "Proposition 1", body: "For any prior $\\mu_0$, the ...", anchor: "prop-1" },
  "Theorem 2":     { title: "Theorem 2",     body: "The optimal signal ...",       anchor: "thm-2"  },
  // ...built from all named items extracted during comprehension
};
```

### Render Phase

1. **Auto-scan**: After HTML is assembled, scan all text nodes for patterns matching `(Proposition|Theorem|Lemma|Corollary|Assumption|Definition)\s+\d+(\.\d+)*`. Wrap each match in `<span class="xref-link" data-xref="Proposition 1">Proposition 1</span>`.
2. **Click handler**: On click, show a floating popup card positioned near the click target.
3. **Popup structure**:
   - Title header with blue background (`var(--accent-blue)`)
   - Statement body rendered with KaTeX
   - Close button (top-right)
   - "Scroll to statement" link that smooth-scrolls to the anchor
4. **Dismiss**: On Escape keypress or click outside the popup.
5. **Dark mode aware**: Popup colors read from CSS custom properties.

### CSS (include in template `<style>`)

```css
.xref-link { color: var(--accent-blue); cursor: pointer; text-decoration: underline; text-decoration-style: dotted; text-underline-offset: 2px; }
.xref-link:hover { text-decoration-style: solid; }
.xref-popup { position: fixed; z-index: 9500; max-width: 480px; min-width: 280px; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; box-shadow: 0 8px 30px rgba(0,0,0,0.18); overflow: hidden; animation: xref-fade-in 0.15s ease; }
.xref-popup-header { background: var(--accent-blue); color: white; padding: 10px 16px; font-family: 'Inter', sans-serif; font-size: 0.85rem; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }
.xref-popup-close { background: none; border: none; color: white; font-size: 1.2rem; cursor: pointer; padding: 0 4px; }
.xref-popup-body { padding: 16px 20px; font-size: 1rem; line-height: 1.7; color: var(--text-body); max-height: 300px; overflow-y: auto; }
.xref-popup-footer { padding: 8px 16px; border-top: 1px solid var(--card-border); text-align: right; }
.xref-popup-footer a { font-family: 'Inter', sans-serif; font-size: 0.78rem; color: var(--accent-blue); text-decoration: none; }
.xref-popup-footer a:hover { text-decoration: underline; }
@keyframes xref-fade-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
```

## Inline Proof Blocks (v5)

Proofs MUST appear as collapsible `<details>` blocks **inline** under their proposition, inside the same `.content-card`, immediately after the interpretation box. Proofs MUST NOT be placed in a separate appendix section.

### Structure

```html
<div class="content-card" data-claim-id="prop-1">
  <!-- ... proposition statement, interpretation-box ... -->
  <details class="inline-proof">
    <summary>Proof of Proposition 1</summary>
    <div class="details-content">
      <p><!-- Proof content with KaTeX math --></p>
    </div>
  </details>
</div>
```

### CSS (include in template `<style>`)

```css
.inline-proof { background: var(--details-bg); border: 1px solid var(--details-border); border-radius: 8px; margin-top: 16px; }
.inline-proof summary { font-family: 'Inter', sans-serif; font-size: 0.88rem; font-weight: 600; color: var(--accent-blue); cursor: pointer; padding: 12px 18px; list-style: none; display: flex; align-items: center; gap: 8px; }
.inline-proof summary::-webkit-details-marker { display: none; }
.inline-proof summary::before { content: '\25B6'; font-size: 0.6rem; transition: transform 0.2s ease; color: var(--accent-blue); }
.inline-proof[open] summary::before { transform: rotate(90deg); }
.inline-proof .details-content { padding: 4px 18px 18px; border-top: 1px solid var(--details-border); }
.inline-proof .details-content p { font-size: 1rem; margin-top: 12px; line-height: 1.8; }
```

### Mandate

- The "Extreme Granularity" rules in `references/paper_structure_guide.md` require proofs inline under their proposition as collapsible `<details>` blocks, NOT in a separate appendix.
- The theory template section structure (`#setup`, `#lemmas`, `#theorems`, `#examples`, `#ledger`) remains, but proofs live inside each result card rather than a separate proofs section.

## Scripts

- `scripts/source_extractor.py`: extraction and OCR fallback
- `scripts/claim_builder.py`: source-driven claim/placeholder generation
- `scripts/anti_hallucination_guard.py`: deterministic gate checker
- `scripts/paper_visual_reader_pipeline.py`: one-click pipeline
- `scripts/run_fixtures.py`: regression + e2e matrix

## References

1. `references/anti_hallucination_module.md`
2. `references/evidence_ledger_schema.md`
3. `references/blocked_report_template.md`
4. `references/paper_structure_guide.md`
5. `references/visual_output_templates.md`
6. `references/html_template.html`
7. `references/templates/theory.html`
8. `references/templates/empirical.html`
9. `references/templates/comparative.html`
10. `references/templates/review.html`
11. `references/templates/premium_academic.html`
12. `references/interactive_viz_catalog.md`

## Final Checklist

- [ ] Generated digest uses one template family
- [ ] Every Tier-A claim has valid anchor and source location
- [ ] Ledger passes schema checks
- [ ] Guard report and JSON report are generated
- [ ] Strict gate passes before final delivery
- [ ] Blocked report generated on blocked status
- [ ] HTML has no em dash characters except direct source quotes with ledger anchors
- [ ] Visible digest word count is at least 1/4 of the source paper word count
- [ ] Digest includes interpretation without low-quality filler or self-referential boilerplate
- [ ] Every theorem/proposition/lemma has Restatement + Intuition + Literature Context + Example + Implication
- [ ] Every symbol defined inline on first use with glossary link
- [ ] Every cross-reference is a clickable hyperlink
- [ ] Every proof preceded by Proof Strategy summary
- [ ] Every figure/table has interpretation paragraph (>=50 words)
- [ ] Every assumption has "Why this is needed" note
- [ ] Every section ends with "Connection to next section" transition
- [ ] Every interpretation box cites at least one claim_id (Round 12 compliance)
- [ ] Interactive visualizations meet minimum count for paper type (v4)
- [ ] Each visualization is self-contained (IIFE), canvas-based, with presets from paper examples
- [ ] Visualization CSS classes included in template style block
- [ ] Cross-reference popup system: all named math objects (Proposition/Theorem/Lemma/etc.) are clickable xref-links with popup cards (v5)
- [ ] Xref registry built from all named items during comprehension pass (v5)
- [ ] Proofs appear inline as collapsible `<details class="inline-proof">` blocks inside result cards, NOT in a separate appendix (v5)
- [ ] Playground visualization included for theory papers with click-to-draw and parameter sliders (v5)
- [ ] Canvas rendering uses DPR scaling, gradient fills, shadow dots, and hover tooltips (v5)

<!-- ANTI_HALLUCINATION_SKILL_PROFILE_V2:paper-visual-reader:7258e1ec1a2f -->
## Anti-Hallucination Module: paper-visual-reader

Profile: `fact_verification` | Strictness: `HARD` | Flow: `MULTI_LAYER_MULTI_PROCESS`

### Layer Stack (L1-L5)
1. Lock claim scope, jurisdiction, timeframe, and evidentiary burden.
2. Collect independent primary/authoritative sources for each claim class.
3. Cross-validate source consistency and provenance quality.
4. Run contradiction and misleading-context stress checks.
5. Publish only verdicts traceable to explicit source anchors.

### Multi-Process Verification Pipeline
1. Process A Claim Typing: atomic claims -> evidence standard assignment.
2. Process B Evidence Test: source retrieval -> credibility scoring -> conflict resolution.
3. Process C Verdict Gate: true/false/unverified labeling with rationale.

### Hard Block Conditions
- No verdict from a single weak or secondary source only.
- No extrapolation beyond source scope or timeframe.
- No certainty label when evidence remains conflicting.

### Legacy-Derived Controls
- 1. Ensure required template sections and minimum claim count are satisfied. (source:blocked_report_template.md) (source:SKILL.md) (source:SKILL.md) (source:SKILL.md) (`source:SKILL.md`)
- 1. Ensure required template sections and minimum claim count are satisfied. (source:blocked_report_template.md) (source:SKILL.md) (source:SKILL.md) (`source:SKILL.md`)
- FAIL: always blocked (source:SKILL.md) (source:SKILL.md) (source:SKILL.md) (source:SKILL.md) (`source:SKILL.md`)
- FAIL: always blocked (source:SKILL.md) (source:SKILL.md) (source:SKILL.md) (`source:SKILL.md`)
- FAIL: always blocked (source:SKILL.md) (source:SKILL.md) (`source:SKILL.md`)
- FAIL: always blocked (source:SKILL.md) (`source:SKILL.md`)
- 4. **Draft HTML**: Write the visual_digest_<paper>.html using the appropriate template (e.g., theory.html). You MUST duplicate the HTML card blocks dynamically to correspond to all N lemmas and M theorems. Do not just fill in a single placeholder. (`source:SKILL.md`)
- FAIL: always blocked (`source:SKILL.md`)

### Skill-Local Reachability Gate
- Before final release, verify referenced local resources are reachable and consistent with output claims.
- Check path: `scripts/source_extractor.py`
- Check path: `references/paper_structure_guide.md`
- Check path: `scripts/anti_hallucination_guard.py`
- Check path: `scripts/paper_visual_reader_pipeline.py`
- Check path: `references/evidence_ledger_schema.md`
- Check path: `scripts/claim_builder.py`
- Check path: `scripts/run_fixtures.py`
- Check path: `references/anti_hallucination_module.md`
- Check path: `references/blocked_report_template.md`
- Check path: `references/visual_output_templates.md`

### Mandatory Output Controls
- Attach source anchors and confidence for each verdict.
- Use `[UNVERIFIED]` where evidence is insufficient.
- Exclude blocked claims from synthesized conclusions.

<!-- INTEGRATED_LEGACY_BEGIN -->
## Integrated Legacy Trigger Coverage
The trigger aliases below are active routing rules for this skill.

- No dedicated trigger section found in legacy files; see full specs below.

## Integrated Legacy Workflow Coverage
The workflow branches below remain active parts of this skill execution contract.

### Alias: `SKILL`
Source: `_merged_variants/numeric_suffix_original/SKILL.md`
#### Multi-Process Verification Pipeline
1. Process A Claim Typing: atomic claims -> evidence standard assignment.
2. Process B Evidence Test: source retrieval -> credibility scoring -> conflict resolution.
3. Process C Verdict Gate: true/false/unverified labeling with rationale.

#### Skill-Local Reachability Gate
- Before final release, verify referenced local resources are reachable and consistent with output claims.
- Check path: `SKILL.md` self-contract only (no local auxiliary resources detected).

## Integrated Legacy Output Contracts
The output requirements below remain mandatory when matching corresponding alias intents.

### Alias: `SKILL`
Source: `_merged_variants/numeric_suffix_original/SKILL.md`
#### Mandatory Output Controls
- Attach source anchors and confidence for each verdict.
- Use `[UNVERIFIED]` where evidence is insufficient.
- Exclude blocked claims from synthesized conclusions.

## Integrated Legacy Full Specs (Non-loss)
Full legacy specs are embedded below to prevent functionality loss.

### Legacy Spec: `SKILL`
Source: `_merged_variants/numeric_suffix_original/SKILL.md`
# Paper Visual Reader v3

Generate standalone HTML visual digests for academic papers with deterministic evidence gating.

## Core Contract

Always produce:

- `visual_digest_<paper>.html`
- `visual_digest_<paper>.evidence_ledger.json`
- `visual_digest_<paper>.anti_hallucination_report.md`
- `visual_digest_<paper>.anti_hallucination_report.json`
- `visual_digest_<paper>.blocked.md` when blocked

Optional outputs:

- `visual_digest_<paper>.claims.csv`
- `visual_digest_<paper>.gate_summary.txt`

## Execution State Machine (Agent-Driven)

The AI Agent executing this skill MUST use its own intelligence to extract content. Do NOT rely on the legacy naive regex pipeline (`paper_visual_reader_pipeline.py`), as it truncates papers to a single lemma/theorem.

`INTAKE -> EXTRACT_TEXT -> **AI COMPREHENSIVE EXTRACTION** -> BUILD_EVIDENCE_LEDGER -> DRAFT_HTML -> RUN_GUARD`

### Step-by-Step AI Execution
1. **Extract**: Run `scripts/source_extractor.py` to get the raw text.
2. **Analyze**: Read the FULL paper text. Extract **ALL** mathematical setups, **ALL** lemmas, **ALL** theorems, and **ALL** numerical examples according to the Extreme Granularity rules in `references/paper_structure_guide.md`.
3. **Draft Ledger**: Write the exhaustive `visual_digest_<paper>.evidence_ledger.json` mapping every single extracted claim to its exact anchor and text location.
4. **Draft HTML**: Write the `visual_digest_<paper>.html` using the appropriate template (e.g., `theory.html`). You MUST duplicate the HTML card blocks dynamically to correspond to all N lemmas and M theorems. Do not just fill in a single placeholder.
5. **Validate**: Run the strict guard:
```bash
python3 scripts/anti_hallucination_guard.py \
  --source <extracted_text.txt> \
  --digest visual_digest_<paper>.html \
  --ledger visual_digest_<paper>.evidence_ledger.json \
  --report visual_digest_<paper>.anti_hallucination_report.md \
  --json-report visual_digest_<paper>.anti_hallucination_report.json \
  --blocked-report visual_digest_<paper>.blocked.md \
  --mode A \
  --template-family <family> \
  --strict
```
6. **Iterate**: If the guard returns FAIL or WARN, adjust your Ledger and HTML equations to mathematically match the extracted text, and run the guard again until PASS.

## Legacy CLI (Regex Baseline - DO NOT USE FOR PROD)

The old `python3 scripts/paper_visual_reader_pipeline.py` is a naive regex fallback. Agents must avoid this and execute the steps manually to achieve full paper coverage.

## OCR & Extraction Stack

Default extraction chain:

`pdftotext -> fitz text -> OCR`

- OCR triggers automatically when extracted text quality is low.
- OCR can be forced by `--ocr on`.

## Evidence Ledger (EvidenceLedgerV1)

Required per claim:

- `claim_id`
- `claim_class`
- `claim_text`
- `anchor`
- `source_location`
- `severity`
- `confidence`
- `status`
- `notes`

Optional v3 extensions:

- `paper_id`
- `paper_tag`
- `tier`
- `evidence_quote`
- `numeric_tokens`
- `equation_fingerprint`
- `anchor_type`
- `source_excerpt`
- `source_hash`
- `bilingual`
- `mode_tag`

See: `references/evidence_ledger_schema.md`

## Guard Semantics

- `PASS`: deliver
- `WARN`: deliver only when strict is off
- `FAIL`: always blocked

Strict mode blocks both `WARN` and `FAIL`.

## Theory Reinforcement (v3)

Theory template enforces layered rendering:

1. setup (`#setup`)
2. lemmas (`#lemmas`)
3. theorems (`#theorems`)
4. examples (`#examples`)
5. ledger (`#ledger`)

This structure is designed to make theorem dependency scanning faster than raw-paper linear reading.

## Visual Enhancements (v3)

1. claim-class filters
2. claim text search
3. severity color stripes
4. evidence ledger panel and gate panel

## Scripts

- `scripts/source_extractor.py`: extraction and OCR fallback
- `scripts/claim_builder.py`: source-driven claim/placeholder generation
- `scripts/anti_hallucination_guard.py`: deterministic gate checker
- `scripts/paper_visual_reader_pipeline.py`: one-click pipeline
- `scripts/run_fixtures.py`: regression + e2e matrix

## References

1. `references/anti_hallucination_module.md`
2. `references/evidence_ledger_schema.md`
3. `references/blocked_report_template.md`
4. `references/paper_structure_guide.md`
5. `references/visual_output_templates.md`
6. `references/html_template.html`
7. `references/templates/theory.html`
8. `references/templates/empirical.html`
9. `references/templates/comparative.html`

## Final Checklist

- [ ] Generated digest uses one template family
- [ ] Every Tier-A claim has valid anchor and source location
- [ ] Ledger passes schema checks
- [ ] Guard report and JSON report are generated
- [ ] Strict gate passes before final delivery
- [ ] Blocked report generated on blocked status

<!-- ANTI_HALLUCINATION_SKILL_PROFILE_V2:numeric_suffix_original:82d83b683544 -->
## Anti-Hallucination Module: numeric_suffix_original

Profile: `fact_verification` | Strictness: `HARD` | Flow: `MULTI_LAYER_MULTI_PROCESS`

### Layer Stack (L1-L5)
1. Lock claim scope, jurisdiction, timeframe, and evidentiary burden.
2. Collect independent primary/authoritative sources for each claim class.
3. Cross-validate source consistency and provenance quality.
4. Run contradiction and misleading-context stress checks.
5. Publish only verdicts traceable to explicit source anchors.

### Multi-Process Verification Pipeline
1. Process A Claim Typing: atomic claims -> evidence standard assignment.
2. Process B Evidence Test: source retrieval -> credibility scoring -> conflict resolution.
3. Process C Verdict Gate: true/false/unverified labeling with rationale.

### Hard Block Conditions
- No verdict from a single weak or secondary source only.
- No extrapolation beyond source scope or timeframe.
- No certainty label when evidence remains conflicting.

### Legacy-Derived Controls
- FAIL: always blocked (source:SKILL.md) (`source:SKILL.md`)
- 4. **Draft HTML**: Write the visual_digest_<paper>.html using the appropriate template (e.g., theory.html). You MUST duplicate the HTML card blocks dynamically to correspond to all N lemmas and M theorems. Do not just fill in a single placeholder. (`source:SKILL.md`)
- No journal-fit assertions based on unverified standards. (`source:SKILL.md`)
- FAIL: always blocked (`source:SKILL.md`)
- No unanchored methodological criticism or praise. (`source:SKILL.md`)
- Required per claim: (source:SKILL.md) (`source:SKILL.md`)
- Required per claim: (`source:SKILL.md`)
- Label unresolved claims as [UNVERIFIED] and isolate them from conclusions. (`source:SKILL.md`)

### Skill-Local Reachability Gate
- Before final release, verify referenced local resources are reachable and consistent with output claims.
- Check path: `SKILL.md` self-contract only (no local auxiliary resources detected).

### Mandatory Output Controls
- Attach source anchors and confidence for each verdict.
- Use `[UNVERIFIED]` where evidence is insufficient.
- Exclude blocked claims from synthesized conclusions.

<!-- INTEGRATED_LEGACY_END -->

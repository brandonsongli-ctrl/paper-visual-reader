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

- In HTML output, do not use the em dash character (`---`) or the en dash character (`--`, HTML entity `&ndash;`, Unicode `–`). Neither is allowed except when directly quoting source text that contains the character; keep it inside a quote and tie it to a source location in the evidence ledger. Use commas, colons, or secondary sentences for transitions.
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

## Common Failure Patterns (Guard Rework Prevention)

This section documents every failure mode that has caused guard rework, so that the first draft passes without iteration.

### R0: Evidence Ledger Enum Values

**Valid `claim_class` values** (case-sensitive):
`Result`, `Mechanism`, `Citation`, `Equation`, `Numeric`, `Causal`

**Valid `severity` values** (case-sensitive):
`BLOCKING`, `MAJOR`, `MINOR`

**Valid `status` values** (case-sensitive):
`VERIFIED`, `UNVERIFIED`, `DISPUTED`

Using any other string (e.g. `"result"`, `"minor"`, `"verified"`) triggers R0 BLOCKING.

### R2: Anchor Syntax for Tier-A Claims

All Tier-A claims (Result, Citation, Equation, Numeric, Causal) require `anchor` to match the pattern `§`, `p. N`, `pp. N-M`, `appendix`, `section`, or similar page/section reference. A bare claim-id like `"anchor": "THM1"` triggers R2 MAJOR.

**Correct:** `"anchor": "Section III.A, p. 1220"`
**Wrong:** `"anchor": "THM1"`

### R6: Citation Class Requires Author (Year) Token

Any claim with `claim_class: "Citation"` must contain an `Author (Year)` pattern in `claim_text`. If a citation has no author-year token, change its class to `"Mechanism"` or `"Result"` instead.

**Correct:** `"Kamenica and Gentzkow (2011) established..."` in claim_text
**Wrong:** Citation class with no author-year, e.g. `"FINRA rule 2241..."`

### R7: No Duplicate `data-claim-id` in HTML

Each claim_id must appear on exactly ONE element with `data-claim-id` in the HTML. Content cards and ledger cards must NOT share the same attribute. Use `data-ledger-id` on ledger panel cards and `data-claim-id` on content cards only.

**Wrong pattern:**
```html
<div class="content-card" data-claim-id="THM1">...</div>
...
<div class="ledger-card" data-claim-id="THM1">...</div>  <!-- duplicate! -->
```
**Correct pattern:**
```html
<div class="content-card" data-claim-id="THM1">...</div>
...
<div class="ledger-card" data-ledger-id="THM1">...</div>
```

### R9: No Standalone Pronoun "i" in HTML or Claim Text

The guard flags `\b(i|my|me)\b` in the full lowercased text of each claim card (claim_text + HTML card text). Common accidental triggers:

- **`i.e.`** — replace with `that is` everywhere
- **`(a, i)`** as an index variable — replace with `(a, n)` or `(a, k)` 
- **`Section I`** — replace with `Section 1` or `Introduction`
- **`i + k`** as formula — replace with `n + k`
- **`A type-$v_i$ agent`** — replace with `A type-$v_n$ agent`

Scan ALL interpretation boxes, proof blocks, and footnotes before submitting.

### R11: No JavaScript Template Literals `${...}` in Embedded Scripts

Any `${...}` inside `<script>` tags triggers R11 BLOCKING. Use string concatenation or pre-computed variables instead.

**Wrong:** `` `Value: ${x.toFixed(2)}` ``
**Correct:** `"Value: " + x.toFixed(2)`

### R12: N-gram Grounding — Claim Text Must Overlap Source

The guard computes 4-gram overlap between `claim_text` content tokens and source document content tokens. **≥25% = PASS, 12-25% = WARN (blocked in strict mode), <12% = FAIL.**

**Critical OCR artifact:** The source extractor (`pdftotext`) often produces math like `p^ < 1=2` with literal `<` and `>` characters. The guard's `content_tokens()` function applies `re.sub(r"<[^>]+>", " ", text)` BEFORE stripping non-alphanumerics — this treats any `<...>` in the OCR text as an HTML tag and deletes everything between them. This silently removes source phrases, causing many source 4-grams to be absent from `source_ngrams`.

**Consequence:** Paraphrased claim_texts that use math-heavy source phrases often score 0% because those source phrases were deleted by the OCR artifact.

**Remedy — Three rules:**
1. **Keep claim_text short** — fewer total claim 4-grams means each source match has higher weight. Aim for ≤12 non-stopword content tokens (yields ≤9 unique 4-grams).
2. **Use verbatim source phrases** — copy consecutive non-math runs of text from the source directly into claim_text. Plain-English passages and section headers survive the strip intact.
3. **Pre-verify before committing** — run the diagnostic script below to confirm overlap before writing the ledger:

```python
import re, json
STOPWORDS = {"a","an","the","and","or","but","in","on","at","to","for","of","with","by","from","is","are","was","were","be","been","being","have","has","had","do","does","did","will","would","shall","should","may","might","can","could","must","that","which","who","whom","this","these","those","it","its","as","if","then","than","so","not","no","nor","each","every","all","any","both","such","into","over","under","also","about","up","out","just","only","very","more","most","other","some","when","where","how","what","there","here","between","through","during","before","after","above","below","because","while","since","until","although","however","therefore","thus","hence","given","let","we","our","us","i","my","me","they","their","them","he","she","his","her","one","two","first"}

def content_tokens(text):
    t = re.sub(r"\\[a-zA-Z]+\*?(?:\{[^}]*\})?", " ", text)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\$\$?[^$]*\$\$?", " ", t)
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t)
    return [w.lower() for w in t.split() if len(w)>=2 and w.lower() not in STOPWORDS]

def ngrams(toks, n=4): return set(zip(*[toks[i:] for i in range(n)]))

source = open("extracted.txt", errors="replace").read()
sn = ngrams(content_tokens(source))

claim_text = "YOUR CLAIM TEXT HERE"
cn = ngrams(content_tokens(claim_text))
score = len(cn & sn) / len(cn) if cn else 0
print(f"{score:.1%}  matches: {sorted(cn & sn)[:5]}")
```

To find useful source 4-grams for a claim, scan `source_ngrams` for any 4-gram containing a key word:
```python
for g in sorted(sn):
    if "retention" in g:  # replace with your keyword
        print(g)
```

### R14: Interpretation Density ≥15%

At least 15% of HTML content cards must contain an interpretation or analysis box. The guard counts cards with class `interpretation-box` or `analysis-box`. **Use `<strong>` or `<span>` for labels inside these boxes** — do NOT nest a `<div>` as the first child, as that triggers incorrect density counting.

**Correct:**
```html
<div class="interpretation-box" data-claim-id="THM1">
  <strong>Author's Interpretation:</strong> This result means...
</div>
```

**Wrong:**
```html
<div class="interpretation-box" data-claim-id="THM1">
  <div class="label">Author's Interpretation:</div>  <!-- nested div breaks count -->
  This result means...
</div>
```

### R16: Word Count Floor

The visible word count of the HTML (text only, excluding tags, scripts, styles) must be **≥ 50% of the source document word count**. For a 15,830-word source paper, the minimum HTML word count is **7,915 words**.

Calculation: `source_word_count = len(source_text.split())`, then `floor = int(source_word_count * 0.5)`.

If the guard reports a word count violation, add more interpretation paragraphs to under-covered sections — do not pad with repeated boilerplate.

### Template Family Flag

The `--template-family` argument accepts exactly: `theory`, `review`, `premium_academic`.

**Do NOT use** `premium-academic` (hyphen instead of underscore) — it will not match and required sections will not be checked.

Theory template required section IDs: `#architecture`, `#setup`, `#lemmas`, `#theorems`, `#examples`, `#ledger`

Review template required section IDs: `#scope`, `#framework`, `#strands`, `#crosscut`, `#frontier`, `#conclusion`, `#ledger`

Every required section ID must appear as an HTML element `id` attribute in the digest.

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

## Right Context Panel (v5)

Every digest using the premium_academic template MUST include a `<aside id="right-panel">` element after `</main>`. Without it, `main`'s `max-width` creates a dead whitespace strip on the right side of the page on wide screens.

### Why It Is Required

The `body` uses `display:flex`. The sidebar is fixed-width (260px) and `main` has `flex:1` with `max-width:860px`. On screens wider than 1120px, the flex container has leftover space that stays blank white. The right panel fills this space as a third flex column.

### Layout Structure

```
<body display:flex>
  <nav id="sidebar" width:260px fixed>       <!-- TOC, paper meta -->
  <main flex:1 padding:0>
    <div class="main-inner" max-width:860px margin:auto>
      <!-- ALL content: header, sections, ledger -->
    </div>
  </main>
  <aside id="right-panel" width:220px fixed>  <!-- Context panel -->
</body>
```

**Critical**: `main` must have NO `max-width` — only the inner `.main-inner` wrapper constrains content width. This allows `main` to fill the full flex space while keeping text at a readable width.

### Required CSS

```css
main { flex: 1; padding: 0; min-width: 0; }
.main-inner { max-width: 860px; margin: 0 auto; padding: 2.5rem 2.5rem 4rem; }
#right-panel { width: 220px; min-width: 220px; height: 100vh; position: sticky; top: 0; overflow-y: auto; border-left: 1px solid var(--sidebar-border); background: var(--sidebar-bg); padding: 1.5rem 1rem 2rem; flex-shrink: 0; }
.rp-section { margin-bottom: 1.4rem; }
.rp-label { font-family: 'Inter', sans-serif; font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); margin-bottom: .45rem; padding-bottom: .35rem; border-bottom: 1px solid var(--sidebar-border); }
.rp-stats { list-style: none; padding: 0; }
.rp-stats li { font-family: 'Inter', sans-serif; font-size: .78rem; color: var(--text-secondary); padding: .26rem 0; display: flex; justify-content: space-between; align-items: baseline; }
.rp-stats .stat-value { font-weight: 600; color: var(--text-primary); text-align: right; max-width: 110px; }
.rp-current { font-family: 'Inter', sans-serif; font-size: .78rem; font-weight: 600; color: var(--accent-blue); padding: .45rem .65rem; background: var(--accent-blue-bg); border-radius: 5px; border-left: 3px solid var(--accent-blue); line-height: 1.4; }
.rp-contributions { list-style: none; padding: 0; }
.rp-contributions li { font-family: 'Inter', sans-serif; font-size: .75rem; color: var(--text-body); padding: .32rem 0 .32rem 14px; position: relative; border-bottom: 1px dotted var(--card-border); line-height: 1.45; }
.rp-contributions li:last-child { border-bottom: none; }
.rp-contributions li::before { content: ''; position: absolute; left: 0; top: 10px; width: 5px; height: 5px; border-radius: 50%; background: var(--accent-blue); }
@media (max-width: 1100px) { #right-panel { display: none; } }
@media (max-width: 900px) { #sidebar { display: none; } .main-inner { padding: 1.5rem; } }
```

### Required HTML Structure

```html
<aside id="right-panel">
  <!-- 1. Dynamic section indicator (updated by IntersectionObserver) -->
  <div class="rp-section">
    <div class="rp-label">Reading</div>
    <div class="rp-current" id="rp-current-section">Introduction</div>
  </div>

  <!-- 2. At-a-Glance stats (paper metadata) -->
  <div class="rp-section">
    <div class="rp-label">At a Glance</div>
    <ul class="rp-stats">
      <li>Type <span class="stat-value">{{PAPER_TYPE}}</span></li>
      <li>Year <span class="stat-value">{{YEAR}}</span></li>
      <li>Journal <span class="stat-value">{{JOURNAL_SHORT}}</span></li>
      <li>JEL <span class="stat-value">{{JEL_CODES}}</span></li>
    </ul>
  </div>

  <!-- 3. Structural count (theorems/propositions/lemmas) -->
  <div class="rp-section">
    <div class="rp-label">Structure</div>
    <ul class="rp-stats">
      <li>Theorems <span class="stat-value">{{N_THEOREMS}}</span></li>
      <li>Propositions <span class="stat-value">{{N_PROPOSITIONS}}</span></li>
      <li>Lemmas <span class="stat-value">{{N_LEMMAS}}</span></li>
      <li>Sections <span class="stat-value">{{N_SECTIONS}}</span></li>
    </ul>
  </div>

  <!-- 4. Key contributions (1 line each, ≤4 items) -->
  <div class="rp-section">
    <div class="rp-label">Contributions</div>
    <ul class="rp-contributions">
      <li>{{CONTRIBUTION_1}}</li>
      <li>{{CONTRIBUTION_2}}</li>
      <!-- ... -->
    </ul>
  </div>

  <!-- 5. Key notation quick-ref (symbol + one-word gloss) -->
  <div class="rp-section">
    <div class="rp-label">Key Notation</div>
    <ul class="rp-stats">
      <li>${{SYM_1}}$ <span class="stat-value">{{GLOSS_1}}</span></li>
      <!-- ... -->
    </ul>
  </div>
</aside>
```

### Dynamic Section Indicator JS

Add inside the existing IntersectionObserver callback (alongside the sidebar active-link logic):

```javascript
const SECTION_LABELS = {
  'abstract': 'Abstract', 'setup': 'Model Setup',
  'sec3': 'Section 3', /* fill from actual section IDs */
  'conclusion': 'Conclusion', 'ledger': 'Evidence Ledger'
};
const rpEl = document.getElementById('rp-current-section');
// Inside the observer callback:
if (e.isIntersecting && rpEl && SECTION_LABELS[id]) { rpEl.textContent = SECTION_LABELS[id]; }
```

### Checklist Items

- [ ] `<main>` has NO `max-width` (only `.main-inner` does)
- [ ] `<div class="main-inner">` wraps all content inside `<main>`
- [ ] `<aside id="right-panel">` present after `</main>`
- [ ] Right panel contains: Reading indicator, At-a-Glance, Structure, Contributions, Key Notation
- [ ] `@media (max-width: 1100px) { #right-panel { display: none; } }` present
- [ ] IntersectionObserver updates `#rp-current-section` on scroll

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
- [ ] HTML has no em dash (`---`) or en dash (`--`, `&ndash;`, `–`) except inside direct source quotes with ledger anchors
- [ ] R16 content volume audit: PASS (visible digest word count >= 1/2 of source paper word count)
- [ ] R17 interactive viz audit: PASS (theory/premium: >= 2 interactive-viz elements; review: >= 1)
- [ ] R18 static image audit: at least one `<img>` or `<svg>` element in the digest (soft requirement)
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
- [ ] Math rendering QA: all `\begin{cases/align/equation/array}` blocks wrapped in `\[...\]` or `\(...\)` or `$$...$$` delimiters; grep `\\begin{` and verify each has enclosing math delimiters (v5.1)
- [ ] Canvas sizing QA: all `setupCanvas` functions lock CSS display size (`c.style.width/height`) BEFORE setting internal DPR resolution (`c.width = rect.width * dpr`); canvas HTML dimensions coordinated with container `max-width` (v5.1)
- [ ] No `height: auto` on canvas elements without explicit `c.style.height` lock in JS (v5.1)
- [ ] R13 raw-text-injection check: PASS (<=40% 15-gram overlap with source)
- [ ] R14 interpretation-density check: PASS (interpretation boxes >=15% of digest words)
- [ ] R15 vocabulary-diversity check: PASS (TTR >=0.20)
- [ ] Right Context Panel: `<aside id="right-panel">` present after `</main>` (v5)
- [ ] Right panel contains: Reading indicator, At-a-Glance stats, Structure counts, Contributions, Key Notation (v5)
- [ ] `<main>` has NO `max-width`; content width constrained only by inner `.main-inner` wrapper (v5)
- [ ] `@media (max-width: 1100px) { #right-panel { display: none; } }` present in CSS (v5)
- [ ] IntersectionObserver updates `#rp-current-section` text on scroll (v5)

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

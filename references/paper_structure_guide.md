# Paper Structure Guide — By Economics Subfield

## Pure Theory (Game Theory, Mechanism Design, Contracts, Information Design)

**Typical Structure:**
1. Introduction (contribution, literature positioning)
2. Model (primitives, assumptions, timing)
3. Benchmark / Preliminary Results (known results restated in current notation)
4. Main Results (theorems, propositions)
5. Extensions (relaxing assumptions, alternative settings)
6. Discussion / Conclusion
7. Appendix (proofs)

**Visual Digest Focus:**
> [!IMPORTANT]
> **EXTREME GRANULARITY & FULL COVERAGE REQUIRED**: Do NOT group multiple lemmas or theorems into a single HTML card. You MUST generate a SEPARATE `<div class="card claim-card" data-claim-id="...">` block for EVERY individual mathematical primitive, EVERY key lemma, EVERY theorem/proposition, and EVERY numerical example.
> **DO NOT TRUNCATE OR SUMMARIZE.** If the paper has 8 Propositions and 3 Numerical Applications, you MUST generate 11 distinct cards. Full paper coverage is mandatory.

- **Context & Motivation**: Explicate the real-world or theoretical gap this paper aims to solve. Do NOT just jump into the setup.
- **Main Contributions**: A distilled list of the 3-4 absolute core achievements of the paper.
- **Literature Review & Citation Network**: Map out the 3-5 foundational papers this builds upon or contradicts. Create a clear structural map of where this sits in the literature.
- **Formal Setup**: Separate cards for State space, action space, agents, priors.
- **Assumptions**: Should be listed precisely — they drive everything.
- **Key Lemmas & Transitions**: Intermediate properties necessary for proofs. Provide the logical connective tissue explaining *why* we need this lemma before the main theorem.
- **Main Results (Theorems / Propositions)**: Formal statements. One card per theorem.
- **Numerical Examples**: Instantiations of the model for edge cases.
- **Conclusion & Broader Impact**: Synthesize what we learned and why this paper matters deeply.

> [!IMPORTANT]
> **INLINE PROOFS (v5)**: Proofs appear inline under their proposition as collapsible `<details class="inline-proof">` blocks, NOT in a separate appendix section. Each proof lives inside the same `.content-card` as its proposition, immediately after the interpretation box. This keeps the logical flow intact: statement, interpretation, then proof.

> [!IMPORTANT]
> **EXTREME DEPTH & SUPER-VERBOSITY REQUIRED**: Do NOT just dump the mathematical proposition. You MUST act as an expert economics professor delivering an in-depth, hour-long whiteboard lecture. Short summaries and bullet points for Intuition and Proof Logic are **STRICTLY FORBIDDEN**.
> 1. **Economic / Mathematical Intuition**: You MUST write a detailed, multi-paragraph (200+ words) explanation wrapping the concept. Explain the real-world friction, the incentives behind the math, and *why* this result matters in plain English.
> 2. **Proof Logic / Mechanism Sketch**: You MUST walk the reader step-by-step through the mathematical derivation. Do not just "sketch" the idea. Explain the logical chain—how limits are taken, why certain terms drop out, and how exactly equations substitute into one another to yield the final theorem. This should be a robust, multi-paragraph deductive breakdown bridging the gap between assumptions and the final result.
> 3. **Notation Glossary**: You MUST explicitly define every mathematical symbol used in the proposition formulas (e.g., $f$: fraction of honest candidates, $\beta$: ambition premium, etc.) in a dedicated bulleted list so the reader understands what the formula variables mean before diving into the proof logic. **CRITICAL: NEVER hallucinate that a variable is a "set", "space", "vector", or "matrix" unless the source text explicitly uses those exact structural terms. (e.g., do not say $A$ is the "set of candidates" if the text just says "candidate A").**

> [!WARNING]
> **MathJax Rendering**: Use full KaTeX delimiters `$$ ... $$` for all standalone equations inside the `<div class="math-block">` tags. Do not rely on the HTML template providing the `$$` for you.

> [!CAUTION]
> **LaTeX Escape Corruption (R11 Filter)**: When writing LaTeX to HTML files via Python scripts, ALWAYS use raw strings (`r"..."`) or double-escape backslashes. Python silently interprets `\to` as tab+o, `\nabla` as newline+abla, `\right` as carriage-return+ight, and `\beta` as backspace+eta. These corruptions destroy rendered formulas. The anti-hallucination guard will BLOCK any digest containing tab, newline, or carriage-return characters inside `$$ ... $$` math blocks.

> [!CAUTION]
> **Author Pronoun & Em-Dash Constraints (R9 Filter)**: 
> 1. You MUST legally match the author's singular/plural pronouns. If the author says "I build a model", you MUST NOT say "We build a model". 
> 2. You are STRICTLY FORBIDDEN from using em dashes (`—`) in your generated text unless it is a verbatim, exact string match from the original paper.

## Reduced-Form Empirical (DiD, RDD, IV, Event Study)

**Typical Structure:**
1. Introduction
2. Institutional Background / Context
3. Data
4. Empirical Strategy / Identification
5. Results
6. Robustness
7. Mechanisms (optional)
8. Conclusion

**Visual Digest Focus:**
- **Identification Strategy** table is critical
- **Data** summary should include source, N, T, sample restrictions
- **Main Table** coefficient + interpretation in economic terms
- **Robustness** summary: what survives, what doesn't

## Structural (DSGE, BLP, Auction Estimation)

**Typical Structure:**
1. Introduction
2. Model
3. Data
4. Estimation Strategy (GMM, ML, Simulated Methods)
5. Results
6. Counterfactuals / Policy Analysis
7. Conclusion

**Visual Digest Focus:**
- **Model** and **Estimation** are equally important
- **Counterfactuals** are often the main contribution
- Note: identification vs. estimation distinction

## Experimental (Lab, Field, Survey)

**Typical Structure:**
1. Introduction
2. Experimental Design
3. Hypotheses (often pre-registered)
4. Results
5. Discussion
6. Conclusion

**Visual Digest Focus:**
- **Design** table: arms, N, protocol
- **Hypotheses** listed explicitly
- **Treatment effects** with confidence intervals
- Note: pre-registered vs. exploratory analyses

## Review / Survey (Literature Review, Annual Review, Handbook Chapter)

**Typical Structure:**
1. Introduction (central question, scope)
2. Conceptual Framework / Taxonomy (organizing scheme)
3. Thematic Section 1 (literature strand with key papers)
4. Thematic Section 2 (literature strand with key papers)
5. ... (additional thematic sections)
6. Cross-Cutting Insights / Implications
7. Future Research Directions
8. Conclusion

**Visual Digest Focus:**

> [!IMPORTANT]
> **STRAND-LEVEL GRANULARITY REQUIRED**: Do NOT collapse the entire review into a single summary card. You MUST generate a SEPARATE thematic strand card for EVERY major section or subsection of the review. If the paper has 5 thematic sections, you MUST generate 5 distinct strand cards.

- **Scope & Central Question**: What question organizes the review? What is included vs. excluded?
- **Conceptual Framework / Taxonomy**: Extract the author's organizing scheme. Review articles almost always introduce a classification or typology that structures the discussion. Render it visually (taxonomy grid).
- **Thematic Strands**: One card per major literature theme. Each card should:
  - Synthesize the strand's key findings
  - List 3-5 most important papers with their core contributions
  - Identify open debates or conflicting findings within the strand
- **Cross-Cutting Insights**: Patterns or tensions that emerge from comparing across strands. This is the review's integrative contribution.
- **Research Frontier**: Explicit future research directions from the author — high-value signals.
- **Conclusion & Broader Impact**: Core takeaway from the review.

> [!IMPORTANT]
> **EXTREME DEPTH FOR STRAND CARDS**: For each thematic strand, do NOT just list paper names. You MUST synthesize what the strand's papers collectively show, identify the key mechanisms or findings, and highlight where papers agree or disagree with each other. Write multi-paragraph syntheses (150+ words per strand), not bullet-point lists.

## Working Papers vs. Published Papers

**Working Papers:**
- May have more speculative content — flag as "work in progress" claims
- Results may change in later versions
- Note version date prominently

**Published Papers:**
- Results are peer-reviewed — higher confidence
- Note journal and review process if relevant
- Check for online appendix / supplementary materials

## Multi-Part Papers (Main + Online Appendix)

When a paper has separate supplements:
- Build one unified Artifact A covering both
- In Reading Map (Artifact C), note which results require the appendix
- Cross-reference appendix proof locations in Artifact B

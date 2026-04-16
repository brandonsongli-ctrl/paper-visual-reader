#!/usr/bin/env python3
"""Deterministic anti-hallucination guard for paper-visual-reader v3."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

TIER_A_CLASSES = {"Result", "Equation", "Numeric", "Causal", "Citation"}
NUMERIC_CHECK_CLASSES = {"Result", "Numeric", "Causal", "Mechanism"}
ALLOWED_CLASSES = {
    "Result",
    "Equation",
    "Numeric",
    "Causal",
    "Mechanism",
    "Citation",
    "Speculation",
    "Metadata",
}
ALLOWED_SEVERITIES = {"BLOCKING", "MAJOR", "MINOR", "STYLE"}
ALLOWED_STATUSES = {"VERIFIED", "UNVERIFIED", "UNREADABLE", "SPECULATIVE"}

EQ_PASS_THRESHOLD = 0.30
EQ_WARN_THRESHOLD = 0.15

# Round 12: Semantic Content Grounding thresholds
TOKEN_OVERLAP_PASS = 0.45  # fraction of claim content tokens found in source
TOKEN_OVERLAP_WARN = 0.30
NGRAM_GROUNDING_PASS = 0.25  # fraction of claim 4-grams found in source
NGRAM_GROUNDING_WARN = 0.12
SENTENCE_SIM_FLOOR = 0.35  # min best-match similarity for any sentence
MIN_CLAIM_TOKENS_FOR_SEMANTIC = 15  # skip semantic check for very short claims

# Round 13: Bulk Duplication thresholds
DUPLICATION_TOKEN_THRESHOLD = 0.60  # flag if >60% tokens shared between claims
MIN_CLAIM_TOKENS_FOR_DEDUP = 20

# Round 14: Content Density thresholds
FILLER_STOPWORD_RATIO_MAX = 0.70  # flag if >70% of tokens are stopwords
UNIQUE_TOKEN_RATIO_MIN = 0.25  # flag if <25% of tokens are unique
MIN_CLAIM_TOKENS_FOR_DENSITY = 20

# Stopwords for semantic checks (academic English, compact set)
STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "may", "might", "can", "could", "must", "that",
    "which", "who", "whom", "this", "these", "those", "it", "its", "as",
    "if", "then", "than", "so", "not", "no", "nor", "each", "every",
    "all", "any", "both", "such", "into", "over", "under", "also",
    "about", "up", "out", "just", "only", "very", "more", "most", "other",
    "some", "when", "where", "how", "what", "there", "here", "between",
    "through", "during", "before", "after", "above", "below", "because",
    "while", "since", "until", "although", "however", "therefore", "thus",
    "hence", "given", "let", "we", "our", "us", "i", "my", "me", "they",
    "their", "them", "he", "she", "his", "her", "one", "two", "first",
})

STRONG_CAUSAL_VERBS = {
    "prove",
    "proves",
    "proved",
    "establish",
    "establishes",
    "established",
    "demonstrates conclusively",
    "definitive evidence",
}
HEDGED_VERBS = {
    "suggest",
    "suggests",
    "suggested",
    "consistent with",
    "associated with",
    "correlated with",
    "may",
    "might",
}

ANCHOR_PATTERN = re.compile(
    r"(§|\bp\.?\s*\d+\b|\bpp\.?\s*\d+\b|\btable\s*[ivx\d]+\b|\bfigure\s*[ivx\d]+\b|\beq\.?\s*\(?\d+\)?\b|\bappendix\b)",
    flags=re.IGNORECASE,
)

CITE_PATTERN = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\])?\s*(?:\[[^\]]*\])?\{([^}]*)\}")
AUTHOR_YEAR_PATTERN = re.compile(r"\b([A-Z][A-Za-z\-]+\s*\(\d{4}[a-z]?\))")
PAPER_TAG_PATTERN = re.compile(r"paper\s*([A-Za-z0-9]+)", flags=re.IGNORECASE)
GENERIC_CITE_KEY_PATTERN = re.compile(r"\b[a-z][a-z0-9_\-]{2,}\d{4}[a-z]?\b", flags=re.IGNORECASE)

REQUIRED_SECTIONS = {
    "theory": ["architecture", "setup", "lemmas", "theorems", "examples", "ledger"],
    "empirical": ["architecture", "method", "results", "critical", "ledger", "gate"],
    "comparative": ["architecture", "results", "ledger", "gate"],
}


@dataclass
class Finding:
    round_id: str
    check: str
    severity: str
    status: str
    claim_id: str
    code: str
    message: str
    source_span: str = ""


@dataclass
class EquationResult:
    claim_id: str
    equation_preview: str
    best_score: float
    best_match_preview: str
    status: str


class ClaimHTMLParser(HTMLParser):
    """Extract claim blocks carrying data-claim-id attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.claims: list[dict[str, str]] = []
        self.active_claims: list[dict[str, str | int | list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.depth += 1
        attr = {k: (v if v is not None else "") for k, v in attrs}
        if "data-claim-id" in attr:
            entry: dict[str, str | int | list[str]] = {
                "claim_id": attr.get("data-claim-id", "").strip(),
                "claim_class": attr.get("data-claim-class", "").strip(),
                "anchor": attr.get("data-anchor", "").strip(),
                "severity": attr.get("data-severity", "").strip(),
                "source_location": attr.get("data-source-location", "").strip(),
                "start_depth": self.depth,
                "text_parts": [],
            }
            self.active_claims.append(entry)

    def handle_data(self, data: str) -> None:
        compact = data.strip()
        if not compact:
            return
        for claim in self.active_claims:
            claim["text_parts"].append(compact)

    def handle_endtag(self, tag: str) -> None:
        self.depth -= 1
        still_active: list[dict[str, str | int | list[str]]] = []
        for claim in self.active_claims:
            start_depth = int(claim["start_depth"])
            if self.depth >= start_depth:
                still_active.append(claim)
            else:
                finalized = {
                    "claim_id": str(claim["claim_id"]),
                    "claim_class": str(claim["claim_class"]),
                    "anchor": str(claim["anchor"]),
                    "severity": str(claim["severity"]),
                    "source_location": str(claim["source_location"]),
                    "text": " ".join(str(x) for x in claim["text_parts"]).strip(),
                }
                self.claims.append(finalized)
        self.active_claims = still_active


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run anti-hallucination gate checks for paper visual digest.")
    parser.add_argument("--source", required=True, help="Source paper path (.pdf/.tex/.md/.txt).")
    parser.add_argument("--digest", required=True, help="Generated digest HTML path.")
    parser.add_argument("--ledger", required=True, help="Evidence ledger JSON path.")
    parser.add_argument("--report", required=True, help="Markdown report output path.")
    parser.add_argument("--json-report", required=True, help="JSON report output path.")
    parser.add_argument("--blocked-report", required=True, help="Blocked report output path.")
    parser.add_argument("--mode", choices=["A", "B", "C"], required=True, help="Execution mode.")
    parser.add_argument("--strict", action="store_true", help="Treat WARN as blocked delivery.")
    parser.add_argument("--template-family", choices=["theory", "empirical", "comparative"], help="Optional template family for coverage checks.")
    parser.add_argument("--emit-claim-csv", help="Optional CSV export path for merged claim table.")
    parser.add_argument("--fail-on-major", action="store_true", help="Block delivery on MAJOR WARN/FAIL even without strict mode.")
    parser.add_argument("--require-min-claims", type=int, default=1, help="Minimum claim count required for coverage checks.")
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() == ".pdf":
        if shutil.which("pdftotext") is None:
            raise RuntimeError("pdftotext is required for PDF input but is not installed.")
        result = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {result.stderr.strip()}")
        return result.stdout

    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_plain_text(html: str) -> str:
    """Remove script/style blocks and all HTML tags; return clean plain text."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_number(token: str) -> str:
    token = token.strip()
    if token.endswith("%"):
        token = token[:-1]
    return token.replace(",", "")


def extract_numbers(text: str) -> list[str]:
    tokens = re.findall(r"(?<![A-Za-z\\])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?", text)
    output: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = normalize_number(token)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def extract_anchor_noise_numbers(anchor: str, source_location: str) -> set[str]:
    noise = set(extract_numbers(anchor)) | set(extract_numbers(source_location))
    extra = re.findall(r"(?:section|sec\.?|table|figure|eq\.?|equation|appendix)\s*([a-z]?\d+)", f"{anchor} {source_location}", flags=re.IGNORECASE)
    for token in extra:
        token = token.strip().lower().lstrip("a")
        if token.isdigit():
            noise.add(token)
    return noise


def strip_anchor_and_location_text(claim_text: str, anchor: str, source_location: str) -> str:
    cleaned = claim_text
    for snippet in [anchor, source_location]:
        snippet = normalize_whitespace(snippet)
        if not snippet:
            continue
        cleaned = cleaned.replace(snippet, " ")
    return normalize_whitespace(cleaned)


def normalize_equation(eq: str) -> str:
    cleaned = re.sub(r"%.*", " ", eq)
    cleaned = re.sub(r"\\(label|tag)\{[^}]*\}", " ", cleaned)
    cleaned = cleaned.replace("\\left", " ").replace("\\right", " ")
    cleaned = cleaned.replace("\\!", " ").replace("\\,", " ").replace("\\;", " ").replace("\\:", " ")
    cleaned = cleaned.replace("\\quad", " ").replace("\\qquad", " ").replace("\\\\", " ")
    cleaned = re.sub(r"\\text\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"\\operatorname\{([^}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\*?", " ", cleaned)
    cleaned = cleaned.replace("{", " ").replace("}", " ").replace("&", " ")
    cleaned = re.sub(r"\s+", "", cleaned.lower())
    cleaned = re.sub(r"[^a-z0-9+\-*/=()_<>\[\].,^|:]", "", cleaned)
    return cleaned


def extract_equations(text: str) -> list[str]:
    patterns = [
        r"\\begin\{(?:equation\*?|align\*?|multline\*?|gather\*?)\}(.*?)\\end\{(?:equation\*?|align\*?|multline\*?|gather\*?)\}",
        r"\$\$(.*?)\$\$",
        r"\\\[(.*?)\\\]",
    ]
    equations: list[str] = []
    for pattern in patterns:
        equations.extend(re.findall(pattern, text, flags=re.DOTALL))

    inline = re.findall(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", text, flags=re.DOTALL)
    for eq in inline:
        compact = normalize_whitespace(eq)
        if len(compact) < 16:
            continue
        if not any(symbol in compact for symbol in ["=", "\\", "_", "^", "+", "-"]):
            continue
        equations.append(eq)

    for line in text.splitlines():
        compact = normalize_whitespace(line)
        if "=" not in compact:
            continue
        if len(compact) > 220:
            continue
        if not re.search(r"[A-Za-z]", compact):
            continue
        if compact.count("=") > 4:
            continue
        candidate = compact
        if ":" in candidate:
            candidate = candidate.split(":")[-1].strip()
        equations.append(normalize_whitespace(candidate))

    deduped: list[str] = []
    seen: set[str] = set()
    for eq in equations:
        norm = normalize_equation(eq)
        if len(norm) < 8:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        deduped.append(eq)
    return deduped


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def best_match(target: str, candidates: Iterable[str]) -> tuple[float, str]:
    best_score = 0.0
    best_candidate = ""
    for candidate in candidates:
        score = similarity(target, candidate)
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return best_score, best_candidate


def short(text: str, width: int = 110) -> str:
    one = normalize_whitespace(text)
    if len(one) <= width:
        return one
    return one[: width - 3] + "..."


def parse_digest_claims(digest_html: str) -> list[dict[str, str]]:
    parser = ClaimHTMLParser()
    parser.feed(digest_html)
    parser.close()
    return parser.claims


def parse_ledger(path: Path) -> tuple[str, list[dict[str, object]], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mode = ""
    template_family = ""
    if isinstance(payload, list):
        claims = payload
    elif isinstance(payload, dict):
        mode = str(payload.get("mode", "") or "")
        template_family = str(payload.get("template_family", "") or "")
        claims = payload.get("claims", [])
    else:
        raise ValueError("Ledger must be a JSON object or list")

    if not isinstance(claims, list):
        raise ValueError("Ledger claims must be a list")

    return mode, claims, template_family


def is_anchor_valid(anchor: str) -> bool:
    if not anchor.strip():
        return False
    return bool(ANCHOR_PATTERN.search(anchor))


def extract_source_citation_signals(source_text: str) -> set[str]:
    signals: set[str] = set()
    for match in AUTHOR_YEAR_PATTERN.findall(source_text):
        signals.add(normalize_whitespace(match).lower())

    for block in CITE_PATTERN.findall(source_text):
        for key in block.split(","):
            key = key.strip().lower()
            if key:
                signals.add(key)
    for key in GENERIC_CITE_KEY_PATTERN.findall(source_text):
        signals.add(key.lower())
    return signals


def extract_claim_citation_tokens(claim_text: str) -> set[str]:
    tokens: set[str] = set()
    for match in AUTHOR_YEAR_PATTERN.findall(claim_text):
        tokens.add(normalize_whitespace(match).lower())
    for block in CITE_PATTERN.findall(claim_text):
        for key in block.split(","):
            key = key.strip().lower()
            if key:
                tokens.add(key)
    for key in GENERIC_CITE_KEY_PATTERN.findall(claim_text):
        tokens.add(key.lower())
    return tokens


def section_exists(digest_html: str, section_id: str) -> bool:
    pattern = rf"id\s*=\s*['\"]{re.escape(section_id)}['\"]"
    return bool(re.search(pattern, digest_html, flags=re.IGNORECASE))


def build_blocked_report(template_text: str, replacements: dict[str, str]) -> str:
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def add_finding(
    findings: list[Finding],
    round_id: str,
    check: str,
    severity: str,
    status: str,
    claim_id: str,
    code: str,
    message: str,
    source_span: str = "",
) -> None:
    findings.append(
        Finding(
            round_id=round_id,
            check=check,
            severity=severity,
            status=status,
            claim_id=claim_id,
            code=code,
            message=message,
            source_span=source_span,
        )
    )


def tokenize_content(text: str) -> list[str]:
    """Tokenize text into lowercase word tokens, stripping LaTeX and HTML."""
    import unicodedata
    # Normalize Unicode ligatures (ﬁ→fi, ﬃ→ffi, ﬀ→ff, ﬂ→fl) so that
    # OCR-extracted source text and manually-written claim text produce
    # identical tokens for the same word.
    text = unicodedata.normalize("NFKD", text)
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\{[^}]*\})?", " ", text)  # strip LaTeX commands
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)  # strip HTML tags
    cleaned = re.sub(r"\$\$?[^$]*\$\$?", " ", cleaned)  # strip math blocks
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", cleaned)
    return [w.lower() for w in cleaned.split() if len(w) >= 2]


def content_tokens(text: str) -> list[str]:
    """Tokenize and remove stopwords."""
    return [t for t in tokenize_content(text) if t not in STOPWORDS]


def build_ngrams(tokens: list[str], n: int = 4) -> list[tuple[str, ...]]:
    """Build n-grams from a token list."""
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def split_sentences(text: str) -> list[str]:
    """Split text into sentences (rough heuristic)."""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\$\$?[^$]*\$\$?", " ", cleaned)
    sents = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    return [s.strip() for s in sents if len(s.strip()) > 20]


def aggregate_status(findings: list[Finding]) -> str:
    for f in findings:
        if f.status == "FAIL":
            return "FAIL"
    has_warn = any(f.status in {"WARN", "FAIL"} and f.severity in {"BLOCKING", "MAJOR", "MINOR"} for f in findings)
    if has_warn:
        return "WARN"
    return "PASS"


def findings_to_markdown(
    findings: list[Finding],
    status: str,
    blocked: bool,
    strict: bool,
    fail_on_major: bool,
    source: Path,
    digest: Path,
    ledger: Path,
    mode: str,
    template_family: str,
    equation_results: list[EquationResult],
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Anti-Hallucination Report",
        "",
        f"- Generated (UTC): {ts}",
        f"- Source: `{source}`",
        f"- Digest: `{digest}`",
        f"- Ledger: `{ledger}`",
        f"- Mode: `{mode}`",
        f"- Template family: `{template_family or '-'}" + "`",
        f"- Strict mode: `{strict}`",
        f"- Fail-on-major: `{fail_on_major}`",
        f"- Gate status: **{status}**",
        f"- Delivery blocked: **{blocked}**",
        "",
        "## Findings",
        "",
        "| Round | Check | Severity | Status | Claim | Code | Message | Source Span |",
        "|---|---|---|---|---|---|---|---|",
    ]

    if findings:
        for item in findings:
            lines.append(
                f"| {item.round_id} | {item.check} | {item.severity} | {item.status} | {item.claim_id or '-'} | {item.code} | {item.message} | {item.source_span or '-'} |"
            )
    else:
        lines.append("| - | - | - | PASS | - | - | No findings. | - |")

    lines.append("")
    lines.append("## Equation Alignment")
    lines.append("")
    lines.append("| Claim | Status | Score | Digest Equation | Best Source Match |")
    lines.append("|---|---|---:|---|---|")
    if equation_results:
        for eq in equation_results:
            lines.append(
                f"| {eq.claim_id} | {eq.status} | {eq.best_score:.3f} | {eq.equation_preview} | {eq.best_match_preview or '-'} |"
            )
    else:
        lines.append("| - | - | - | No equation checks run | - |")

    lines.append("")
    lines.append("## Policy")
    lines.append("")
    lines.append("- Tier-A missing anchors are BLOCKING.")
    lines.append("- BLOCKING/MAJOR failures force FAIL gate status.")
    lines.append("- In strict mode, WARN blocks delivery.")
    lines.append("- Fail-on-major enforces MAJOR warnings/failures as blocked delivery.")
    lines.append("")
    return "\n".join(lines)


def write_claim_csv(path: Path, merged_rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "claim_id",
        "claim_class",
        "anchor",
        "anchor_type",
        "severity",
        "status",
        "source_location",
        "paper_id",
        "paper_tag",
        "tier",
        "numeric_tokens",
        "source_excerpt",
        "source_hash",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in merged_rows:
            writer.writerow(
                {
                    "claim_id": row.get("claim_id", ""),
                    "claim_class": row.get("claim_class", ""),
                    "anchor": row.get("anchor", ""),
                    "anchor_type": row.get("anchor_type", ""),
                    "severity": row.get("severity", ""),
                    "status": row.get("status", ""),
                    "source_location": row.get("source_location", ""),
                    "paper_id": row.get("paper_id", ""),
                    "paper_tag": row.get("paper_tag", ""),
                    "tier": row.get("tier", ""),
                    "numeric_tokens": ";".join(str(x) for x in row.get("numeric_tokens", [])),
                    "source_excerpt": row.get("source_excerpt", ""),
                    "source_hash": row.get("source_hash", ""),
                }
            )


def main() -> int:
    args = parse_args()

    source_path = Path(args.source).expanduser().resolve()
    digest_path = Path(args.digest).expanduser().resolve()
    ledger_path = Path(args.ledger).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    json_path = Path(args.json_report).expanduser().resolve()
    blocked_report_path = Path(args.blocked_report).expanduser().resolve()

    findings: list[Finding] = []
    equation_results: list[EquationResult] = []

    try:
        source_text = read_text(source_path)
        digest_html = digest_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        print(f"[anti-hallucination] input error: {exc}", file=sys.stderr)
        return 1

    try:
        ledger_mode, ledger_claims_raw, ledger_template_family = parse_ledger(ledger_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[anti-hallucination] ledger error: {exc}", file=sys.stderr)
        return 1

    if ledger_mode and ledger_mode != args.mode:
        add_finding(findings, "R0", "mode_consistency", "MAJOR", "FAIL", "-", "R0-MODE-MISMATCH", f"Ledger mode={ledger_mode} differs from --mode {args.mode}")

    template_family = args.template_family or ledger_template_family
    if template_family and template_family not in REQUIRED_SECTIONS:
        add_finding(findings, "R0", "template_family", "MAJOR", "FAIL", "-", "R0-TEMPLATE-INVALID", f"Unsupported template_family={template_family}")

    digest_claims = parse_digest_claims(digest_html)
    digest_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for claim in digest_claims:
        claim_id = str(claim.get("claim_id", "") or "").strip()
        if claim_id:
            digest_by_id[claim_id].append(claim)

    for claim_id, entries in digest_by_id.items():
        if len(entries) > 1:
            add_finding(findings, "R7", "digest_uniqueness", "MAJOR", "FAIL", claim_id, "R7-DUPLICATE-CLAIM-ID", "Duplicate claim_id appears multiple times in digest HTML")

    ledger_claims: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for idx, raw in enumerate(ledger_claims_raw):
        if not isinstance(raw, dict):
            add_finding(findings, "R0", "ledger_format", "MAJOR", "FAIL", "-", "R0-LEDGER-NONOBJECT", f"claims[{idx}] is not an object")
            continue

        claim_id = str(raw.get("claim_id", "") or "").strip()
        claim_class = str(raw.get("claim_class", "") or "").strip()
        claim_text = str(raw.get("claim_text", "") or "").strip()
        anchor = str(raw.get("anchor", "") or "").strip()
        source_location = str(raw.get("source_location", "") or "").strip()
        severity = str(raw.get("severity", "") or "").strip()
        confidence = raw.get("confidence", "")
        status = str(raw.get("status", "") or "").strip()
        notes = str(raw.get("notes", "") or "").strip()

        paper_id = str(raw.get("paper_id", "") or "").strip()
        paper_tag = str(raw.get("paper_tag", "") or "").strip()
        tier = str(raw.get("tier", "") or "").strip()
        evidence_quote = str(raw.get("evidence_quote", "") or "").strip()
        equation_fingerprint = str(raw.get("equation_fingerprint", "") or "").strip()
        anchor_type = str(raw.get("anchor_type", "") or "").strip()
        source_excerpt = str(raw.get("source_excerpt", "") or "").strip()
        source_hash = str(raw.get("source_hash", "") or "").strip()
        mode_tag = str(raw.get("mode_tag", "") or "").strip()

        numeric_tokens_raw = raw.get("numeric_tokens", [])
        if isinstance(numeric_tokens_raw, list):
            numeric_tokens = [str(x) for x in numeric_tokens_raw]
        elif numeric_tokens_raw in (None, ""):
            numeric_tokens = []
        else:
            numeric_tokens = [str(numeric_tokens_raw)]

        if not claim_id:
            add_finding(findings, "R0", "ledger_required_fields", "MAJOR", "FAIL", "-", "R0-CLAIM-ID-MISSING", f"claims[{idx}] missing claim_id")
            continue

        if claim_id in seen_ids:
            add_finding(findings, "R0", "ledger_uniqueness", "MAJOR", "FAIL", claim_id, "R0-CLAIM-ID-DUP", "Duplicate claim_id in ledger")
            continue
        seen_ids.add(claim_id)

        if claim_class not in ALLOWED_CLASSES:
            add_finding(findings, "R0", "ledger_enum", "MAJOR", "FAIL", claim_id, "R0-CLASS-INVALID", f"Invalid claim_class={claim_class}")
        if severity not in ALLOWED_SEVERITIES:
            add_finding(findings, "R0", "ledger_enum", "MAJOR", "FAIL", claim_id, "R0-SEVERITY-INVALID", f"Invalid severity={severity}")
        if status not in ALLOWED_STATUSES:
            add_finding(findings, "R0", "ledger_enum", "MAJOR", "FAIL", claim_id, "R0-STATUS-INVALID", f"Invalid status={status}")

        try:
            conf_value = float(confidence)
            if conf_value < 0 or conf_value > 1:
                add_finding(findings, "R1", "confidence_range", "MAJOR", "FAIL", claim_id, "R1-CONFIDENCE-RANGE", "confidence must be in [0,1]")
        except Exception:  # noqa: BLE001
            add_finding(findings, "R1", "confidence_range", "MAJOR", "FAIL", claim_id, "R1-CONFIDENCE-TYPE", "confidence must be numeric")
            conf_value = 0.0

        ledger_claims.append(
            {
                "claim_id": claim_id,
                "claim_class": claim_class,
                "claim_text": claim_text,
                "anchor": anchor,
                "source_location": source_location,
                "severity": severity,
                "confidence": conf_value,
                "status": status,
                "notes": notes,
                "paper_id": paper_id,
                "paper_tag": paper_tag,
                "tier": tier,
                "evidence_quote": evidence_quote,
                "numeric_tokens": numeric_tokens,
                "equation_fingerprint": equation_fingerprint,
                "anchor_type": anchor_type,
                "source_excerpt": source_excerpt,
                "source_hash": source_hash,
                "mode_tag": mode_tag,
            }
        )

    digest_map: dict[str, dict[str, str]] = {}
    for claim_id, entries in digest_by_id.items():
        digest_map[claim_id] = entries[0]

    ledger_map = {str(c["claim_id"]): c for c in ledger_claims if c.get("claim_id")}

    for claim_id in sorted(ledger_map):
        if claim_id not in digest_map:
            add_finding(findings, "R0", "ledger_digest_alignment", "MAJOR", "FAIL", claim_id, "R0-LEDGER-MISSING-IN-DIGEST", "Claim present in ledger but missing in digest HTML")

    for claim_id in sorted(digest_map):
        if claim_id not in ledger_map:
            add_finding(findings, "R0", "ledger_digest_alignment", "MAJOR", "FAIL", claim_id, "R0-DIGEST-MISSING-IN-LEDGER", "Claim present in digest HTML but missing in ledger")

    for claim_id, ledger_claim in ledger_map.items():
        digest_claim = digest_map.get(claim_id)
        if not digest_claim:
            continue

        if ledger_claim["claim_class"] and digest_claim.get("claim_class") and ledger_claim["claim_class"] != digest_claim.get("claim_class"):
            add_finding(findings, "R0", "class_alignment", "MAJOR", "FAIL", claim_id, "R0-CLASS-MISMATCH", "claim_class mismatch between ledger and digest")

        if ledger_claim["anchor"] and digest_claim.get("anchor") and normalize_whitespace(str(ledger_claim["anchor"])) != normalize_whitespace(str(digest_claim.get("anchor", ""))):
            add_finding(findings, "R0", "anchor_alignment", "MAJOR", "FAIL", claim_id, "R0-ANCHOR-MISMATCH", "anchor mismatch between ledger and digest")

        if ledger_claim["source_location"] and digest_claim.get("source_location") and normalize_whitespace(str(ledger_claim["source_location"])) != normalize_whitespace(str(digest_claim.get("source_location", ""))):
            add_finding(findings, "R0", "source_location_alignment", "MAJOR", "WARN", claim_id, "R0-SOURCE-LOC-DIFF", "source_location differs between ledger and digest")

    # Round 1: source declaration
    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        if not str(claim["source_location"]).strip():
            add_finding(findings, "R1", "source_declaration", "BLOCKING", "FAIL", claim_id, "R1-SOURCE-LOCATION-MISSING", "source_location is required")

    # Mode C paper ownership checks
    if args.mode == "C":
        non_meta = [c for c in ledger_claims if str(c.get("claim_class")) != "Metadata"]
        with_paper_id = [c for c in non_meta if str(c.get("paper_id", "")).strip()]
        if non_meta and len(with_paper_id) != len(non_meta):
            add_finding(findings, "R7", "mode_c_paper_mapping", "MAJOR", "FAIL", "-", "R7-MODEC-PAPERID-MISSING", "Mode C non-metadata claims require paper_id")

        paper_tags_seen: set[str] = set()
        for claim in non_meta:
            claim_id = str(claim["claim_id"])
            location = str(claim["source_location"])
            tags = PAPER_TAG_PATTERN.findall(location)
            if not tags:
                add_finding(findings, "R1", "mode_c_attribution", "BLOCKING", "FAIL", claim_id, "R1-MODEC-TAG-MISSING", "Mode C claim missing explicit paper tag in source_location")
                continue
            if len(set(t.lower() for t in tags)) > 1:
                add_finding(findings, "R1", "mode_c_attribution", "BLOCKING", "FAIL", claim_id, "R1-MODEC-TAG-MULTI", "Multiple paper tags in one claim")
                continue
            tag = tags[0]
            paper_tags_seen.add(tag.lower())
            paper_id = str(claim.get("paper_id", "")).strip()
            if paper_id and paper_id.lower() != tag.lower():
                add_finding(findings, "R7", "mode_c_paper_mapping", "MAJOR", "FAIL", claim_id, "R7-MODEC-PAPERID-MISMATCH", f"paper_id={paper_id} differs from source tag={tag}")
            if claim_id.startswith("A_") and tag.lower() != "a":
                add_finding(findings, "R7", "mode_c_cross_ownership", "BLOCKING", "FAIL", claim_id, "R7-MODEC-CLAIMID-TAG-MISMATCH", "Claim id indicates Paper A but source tag is not A", source_span=location)
            if claim_id.startswith("B_") and tag.lower() != "b":
                add_finding(findings, "R7", "mode_c_cross_ownership", "BLOCKING", "FAIL", claim_id, "R7-MODEC-CLAIMID-TAG-MISMATCH", "Claim id indicates Paper B but source tag is not B", source_span=location)

        if template_family == "comparative" and not {"a", "b"}.issubset(paper_tags_seen):
            add_finding(findings, "R8", "template_coverage", "MAJOR", "FAIL", "-", "R8-MODEC-AB-MISSING", "Comparative mode should include both Paper A and Paper B claim ownership")

    # Round 2: anchor completeness
    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        claim_class = str(claim["claim_class"])
        ledger_anchor = str(claim["anchor"])
        digest_anchor = str(digest_map.get(claim_id, {}).get("anchor", ""))
        anchor = ledger_anchor or digest_anchor

        if claim_class in TIER_A_CLASSES:
            if not anchor.strip():
                add_finding(findings, "R2", "anchor_completeness", "BLOCKING", "FAIL", claim_id, "R2-ANCHOR-MISSING", "Tier-A claim missing anchor")
                continue
            if not is_anchor_valid(anchor):
                add_finding(findings, "R2", "anchor_syntax", "BLOCKING", "FAIL", claim_id, "R2-ANCHOR-SYNTAX", f"Anchor lacks location tokens: {anchor}")

    # Round 3: numeric traceability
    source_number_set = set(extract_numbers(source_text))
    merged_claim_rows: list[dict[str, object]] = []

    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        claim_class = str(claim["claim_class"])
        digest_text = str(digest_map.get(claim_id, {}).get("text", ""))
        claim_text = str(claim["claim_text"]).strip() or digest_text.strip()
        anchor = str(claim.get("anchor", ""))
        source_location = str(claim.get("source_location", ""))
        claim_text_for_numeric = strip_anchor_and_location_text(claim_text, anchor, source_location)
        detected_numbers = extract_numbers(claim_text_for_numeric)
        noise_numbers = extract_anchor_noise_numbers(anchor, source_location)
        detected_numbers = [num for num in detected_numbers if num not in noise_numbers]

        merged = dict(claim)
        if not merged.get("numeric_tokens"):
            merged["numeric_tokens"] = detected_numbers
        merged_claim_rows.append(merged)

        if claim_class not in NUMERIC_CHECK_CLASSES:
            continue
        for number in detected_numbers:
            if number not in source_number_set:
                sev = "BLOCKING" if claim_class in TIER_A_CLASSES else "MAJOR"
                add_finding(
                    findings,
                    "R3",
                    "numeric_traceability",
                    sev,
                    "FAIL",
                    claim_id,
                    "R3-NUMERIC-UNTRACEABLE",
                    f"Untraceable numeric token: {number}",
                    source_span=str(claim.get("anchor", "")),
                )

    # Round 4: equation alignment
    source_equations = extract_equations(source_text)
    source_norm = [normalize_equation(eq) for eq in source_equations]

    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        claim_class = str(claim["claim_class"])
        if claim_class != "Equation":
            continue

        digest_text = str(digest_map.get(claim_id, {}).get("text", ""))
        ledger_text = str(claim.get("claim_text", "")).strip()
        claim_text = ledger_text or digest_text.strip()
        digest_equations = extract_equations(claim_text)
        if not digest_equations and digest_text.strip():
            digest_equations = extract_equations(digest_text.strip())

        if not digest_equations:
            add_finding(findings, "R4", "equation_alignment", "BLOCKING", "FAIL", claim_id, "R4-EQUATION-MISSING", "No equation found in digest equation claim", source_span=str(claim.get("anchor", "")))
            continue

        if not source_norm:
            add_finding(findings, "R4", "equation_alignment", "BLOCKING", "FAIL", claim_id, "R4-SOURCE-EQUATION-MISSING", "No equations extracted from source", source_span=str(claim.get("source_location", "")))
            continue

        for eq in digest_equations:
            eq_norm = normalize_equation(eq)
            score, match = best_match(eq_norm, source_norm)
            if score < EQ_WARN_THRESHOLD:
                status = "FAIL"
                add_finding(findings, "R4", "equation_alignment", "BLOCKING", status, claim_id, "R4-EQUATION-FAIL", f"Equation similarity {score:.3f} below {EQ_WARN_THRESHOLD}", source_span=str(claim.get("anchor", "")))
            elif score < EQ_PASS_THRESHOLD:
                status = "WARN"
                add_finding(findings, "R4", "equation_alignment", "MAJOR", status, claim_id, "R4-EQUATION-WARN", f"Equation similarity {score:.3f} in warning band", source_span=str(claim.get("anchor", "")))
            else:
                status = "PASS"

            equation_results.append(
                EquationResult(
                    claim_id=claim_id,
                    equation_preview=short(eq),
                    best_score=round(score, 3),
                    best_match_preview=short(match),
                    status=status,
                )
            )

    # Round 5: causal calibration
    source_lower = source_text.lower()
    source_has_hedged = any(token in source_lower for token in HEDGED_VERBS)
    source_has_strong = any(token in source_lower for token in STRONG_CAUSAL_VERBS)

    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        claim_class = str(claim["claim_class"])
        if claim_class != "Causal":
            continue
        text = f"{claim['claim_text']} {digest_map.get(claim_id, {}).get('text', '')}".lower()
        claim_is_strong = any(token in text for token in STRONG_CAUSAL_VERBS)
        if claim_is_strong and source_has_hedged and not source_has_strong:
            add_finding(findings, "R5", "causal_calibration", "MAJOR", "FAIL", claim_id, "R5-CAUSAL-UPGRADE", "Digest uses strong causal proof language while source is hedged")

    # Round 6: citation existence
    source_signals = extract_source_citation_signals(source_text)
    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        if str(claim["claim_class"]) != "Citation":
            continue
        tokens = extract_claim_citation_tokens(str(claim["claim_text"]))
        if not tokens:
            add_finding(findings, "R6", "citation_existence", "MAJOR", "FAIL", claim_id, "R6-CITATION-TOKEN-MISSING", "Citation claim has no parseable citation token", source_span=str(claim.get("anchor", "")))
            continue
        if not any(token in source_signals for token in tokens):
            add_finding(findings, "R6", "citation_existence", "MAJOR", "FAIL", claim_id, "R6-CITATION-NOT-FOUND", "Citation token not found in source signals", source_span=str(claim.get("source_location", "")))

    # Round 7: cross-claim consistency
    anchor_class_map: dict[tuple[str, str, str], list[tuple[str, tuple[str, ...]]]] = defaultdict(list)
    for claim in merged_claim_rows:
        claim_id = str(claim.get("claim_id", ""))
        claim_class = str(claim.get("claim_class", ""))
        anchor = normalize_whitespace(str(claim.get("anchor", ""))).lower()
        paper_group = str(claim.get("paper_id", "")).strip().lower() if args.mode == "C" else ""
        numbers = tuple(sorted(str(x) for x in claim.get("numeric_tokens", []) if str(x)))
        if not anchor or not numbers:
            continue
        anchor_class_map[(anchor, claim_class, paper_group)].append((claim_id, numbers))

    for (anchor, claim_class, paper_group), entries in anchor_class_map.items():
        unique_sets = {nums for _, nums in entries}
        if len(entries) > 1 and len(unique_sets) > 1:
            claim_ids = ",".join(claim_id for claim_id, _ in entries)
            add_finding(
                findings,
                "R7",
                "cross_claim_consistency",
                "MAJOR",
                "FAIL",
                claim_ids,
                "R7-ANCHOR-NUMERIC-CONFLICT",
                f"Conflicting numeric statements under anchor={anchor} class={claim_class} group={paper_group or 'main'}",
            )

    # Round 8: template coverage
    min_claims = max(int(args.require_min_claims or 1), 1)
    if len(ledger_claims) < min_claims:
        add_finding(findings, "R8", "template_coverage", "MAJOR", "FAIL", "-", "R8-CLAIM-COUNT-LOW", f"Claim count {len(ledger_claims)} below required minimum {min_claims}")

    if template_family in REQUIRED_SECTIONS:
        for section_id in REQUIRED_SECTIONS[template_family]:
            if not section_exists(digest_html, section_id):
                add_finding(findings, "R8", "template_coverage", "MAJOR", "FAIL", "-", "R8-SECTION-MISSING", f"Required section id missing: {section_id}")

    # Round 9: Stylistic consistency (Pronouns and Em-dashes)
    source_lower = source_text.lower()

    singular_score = len(re.findall(r'\bi\b', source_lower)) + len(re.findall(r'\bmy\b', source_lower)) + len(re.findall(r'\bme\b', source_lower))
    plural_score = len(re.findall(r'\bwe\b', source_lower)) + len(re.findall(r'\bour\b', source_lower)) + len(re.findall(r'\bus\b', source_lower))

    enforce_singular = singular_score > plural_score * 2 and singular_score > 5
    enforce_plural = plural_score > singular_score * 2 and plural_score > 5

    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        claim_text = str(claim["claim_text"])
        digest_text = str(digest_map.get(claim_id, {}).get("text", ""))
        full_text = f"{claim_text} {digest_text}"
        full_text_lower = full_text.lower()

        claim_singular = bool(re.search(r'\b(i|my|me)\b', full_text_lower))
        claim_plural = bool(re.search(r'\b(we|our|us)\b', full_text_lower))

        if enforce_singular and claim_plural:
            add_finding(findings, "R9", "pronoun_match", "BLOCKING", "FAIL", claim_id, "R9-PRONOUN-PLURAL", "Source uses singular pronouns, but digest claim uses plural (we/our/us).")
        elif enforce_plural and claim_singular:
            add_finding(findings, "R9", "pronoun_match", "BLOCKING", "FAIL", claim_id, "R9-PRONOUN-SINGULAR", "Source uses plural pronouns, but digest claim uses singular (I/my/me).")

        dash_idx = full_text.find("—")
        while dash_idx != -1:
            start = max(0, dash_idx - 15)
            end = min(len(full_text), dash_idx + 15)
            snippet = full_text[start:end].strip()

            if snippet and snippet not in source_text:
                add_finding(findings, "R9", "em_dash_prohibited", "BLOCKING", "FAIL", claim_id, "R9-EM-DASH-NOT-VERBATIM", "Em dash used without verbatim matching the source text.")
                break

            dash_idx = full_text.find("—", dash_idx + 1)

    # Round 10: Notation Grounding (Structural Hallucinations)
    # Extract all notation logic from the digest and ensure the AI isn't projecting structural math properties (sets, spaces, vectors, matrices) that don't exist in the text.
    structural_keywords = ["set of", "set", "space of", "space", "matrix", "vector"]
    
    # 1. Find all notation boxes
    notation_pattern = re.compile(r'<div\s+class="[^"]*analysis-box\s+notation[^"]*"\s*>(.*?)</div>', re.IGNORECASE | re.DOTALL)
    for box_match in notation_pattern.finditer(digest_html):
        box_text = box_match.group(1)
        
        # Determine the parent claim ID by scanning backwards from the box match
        prefix_html = digest_html[:box_match.start()]
        claim_match = re.search(r'<article[^>]*data-claim-id="([^"]+)"', prefix_html)
        if not claim_match:
            claim_match = re.search(r'<div[^>]*data-claim-id="([^"]+)"', prefix_html)
        
        # Reverse search: get the LAST match before this box
        claim_id = "UNKNOWN"
        if claim_match:
            # Find all matches in prefix and take the last one
            all_claims = re.findall(r'<[^>]*data-claim-id="([^"]+)"', prefix_html)
            if all_claims:
                claim_id = all_claims[-1]
                
        # 2. Extract li items within this box
        li_pattern = re.compile(r'<li>\s*(.*?)\s*</li>', re.IGNORECASE | re.DOTALL)
        for li_match in li_pattern.finditer(box_text):
            li_text = li_match.group(1)
            # Remove LaTeX delimiters to avoid confusing the regex matcher
            li_text_clean = re.sub(r'\$\$?', '', li_text)
            li_lower = li_text_clean.lower()
            
            # We forbid vague structural math words in the notation glossary only when used without mathematical context.
            # If the li item contains math mode markers (\(, \), $, =), it is a legitimate math definition and is exempt.
            forbidden_notation_keywords = ["set {", "arbitrary set", "some space", "some matrix"]
            has_math_context = any(marker in li_text for marker in ["\\(", "\\)", "$", "="])

            for keyword in forbidden_notation_keywords:
                if keyword in li_lower and not has_math_context:
                    add_finding(
                        findings,
                        "R10",
                        "notation_grounding",
                        "BLOCKING",
                        "FAIL",
                        claim_id,
                        "R10-NOTATION-STRUCTURAL-HALLUCINATION",
                        f"Vague structural math terms are forbidden in the Notation Glossary without mathematical context. Found forbidden keyword: '{keyword}' in '{li_text_clean.strip()}'"
                    )

    # Round 11: LaTeX Rendering Sanity Check
    # Detect corrupted LaTeX inside math blocks caused by Python string escape
    # interpretation (e.g. \to → \t + o, \nabla → \n + abla, \right → \r + ight).
    math_block_pattern = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
    inline_math_pattern = re.compile(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', re.DOTALL)
    
    corrupt_chars = {
        '\t': '\\t (tab) — likely corrupted \\to, \\tau, \\theta, or \\text',
        '\n': '\\n (newline) — likely corrupted \\nabla, \\nu, or \\neq',
        '\r': '\\r (carriage return) — likely corrupted \\right or \\rho',
        '\x08': '\\b (backspace) — likely corrupted \\beta or \\bar',
    }
    
    all_math_spans = list(math_block_pattern.finditer(digest_html)) + list(inline_math_pattern.finditer(digest_html))
    
    for match in all_math_spans:
        math_content = match.group(1)
        for char, description in corrupt_chars.items():
            if char in math_content:
                # Find the nearest claim_id by scanning backwards
                prefix = digest_html[:match.start()]
                all_claims = re.findall(r'<[^>]*data-claim-id="([^"]+)"', prefix)
                claim_id = all_claims[-1] if all_claims else "GLOBAL"
                
                # Show a preview of the corrupted formula
                preview = math_content.strip()[:80].replace('\t', '<TAB>').replace('\n', '<NL>').replace('\r', '<CR>')
                add_finding(
                    findings,
                    "R11",
                    "latex_rendering",
                    "BLOCKING",
                    "FAIL",
                    claim_id,
                    "R11-LATEX-ESCAPE-CORRUPTION",
                    f"Math block contains {description}. Preview: {preview}"
                )

    # Also check for unmatched $ delimiters (odd count)
    dollar_count = digest_html.count('$')
    double_dollar_count = digest_html.count('$$')
    single_dollars = dollar_count - (double_dollar_count * 2)
    if single_dollars % 2 != 0:
        add_finding(
            findings,
            "R11",
            "latex_rendering",
            "MAJOR",
            "WARN",
            "GLOBAL",
            "R11-LATEX-UNMATCHED-DELIMITER",
            f"Odd number of single $ delimiters ({single_dollars}), likely unmatched math delimiter"
        )

    # Round 12: Per-claim Semantic Content Grounding
    # For each claim, verify that its text content is genuinely grounded in the
    # source paper, not filler/fabricated text that happens to have correct HTML
    # attributes.  Three sub-checks:
    #   (a) Token overlap ratio — content words in claim vs source
    #   (b) N-gram grounding — 4-gram windows from claim found in source
    #   (c) Sentence similarity floor — every sentence has a reasonable match
    # Uses ledger claim_text as primary (stripped of template chrome); falls back
    # to digest HTML text only when ledger text is empty.
    source_content_tokens_set = set(content_tokens(source_text))
    source_ngram_set: set[tuple[str, ...]] = set(build_ngrams(content_tokens(source_text), 4))

    # Template boilerplate patterns to strip before semantic analysis
    _template_noise = re.compile(
        r"(?:claim_id|data-claim-id|loc|source_location)\s*=\s*\S+|"
        r"(?:Notation Glossary|Key Foundation|Estimation Equation|Evidence Ledger)\b|"
        r"(?:EN|ZH|CN)\s*:|"
        r"(?:Paper [A-Z])\s*[§:]\s*\d+",
        flags=re.IGNORECASE,
    )

    def _clean_for_semantic(text: str) -> str:
        """Strip template chrome and metadata before semantic tokenization."""
        cleaned = _template_noise.sub(" ", text)
        # Strip anchor-like fragments
        cleaned = re.sub(r"§\s*\d+|p\.\s*\d+|Section\s+\d+", " ", cleaned, flags=re.IGNORECASE)
        return normalize_whitespace(cleaned)

    for claim in ledger_claims:
        claim_id = str(claim["claim_id"])
        claim_class = str(claim["claim_class"])

        # Skip metadata and speculation — not grounded the same way
        if claim_class in {"Metadata", "Speculation"}:
            continue

        # Prefer ledger claim_text (substantive content, no template chrome);
        # fall back to digest HTML text only if ledger is empty
        ledger_text = str(claim.get("claim_text", "")).strip()
        digest_text = str(digest_map.get(claim_id, {}).get("text", ""))
        raw_text = ledger_text if ledger_text else digest_text.strip()
        clean_text = _clean_for_semantic(raw_text)

        claim_ctokens = content_tokens(clean_text)
        if len(claim_ctokens) < MIN_CLAIM_TOKENS_FOR_SEMANTIC:
            continue

        # (a) Token overlap ratio
        overlap_count = sum(1 for t in claim_ctokens if t in source_content_tokens_set)
        token_overlap = overlap_count / len(claim_ctokens)

        if token_overlap < TOKEN_OVERLAP_WARN:
            sev = "BLOCKING" if claim_class in TIER_A_CLASSES else "MAJOR"
            add_finding(
                findings, "R12", "semantic_grounding", sev, "FAIL", claim_id,
                "R12-TOKEN-OVERLAP-FAIL",
                f"Token overlap with source is {token_overlap:.1%} (threshold: {TOKEN_OVERLAP_WARN:.0%}). "
                f"Claim content may not be grounded in source text.",
            )
        elif token_overlap < TOKEN_OVERLAP_PASS:
            add_finding(
                findings, "R12", "semantic_grounding", "MINOR", "WARN", claim_id,
                "R12-TOKEN-OVERLAP-WARN",
                f"Token overlap with source is {token_overlap:.1%} (pass: {TOKEN_OVERLAP_PASS:.0%}). "
                f"Some content words not found in source.",
            )

        # (b) N-gram grounding score
        claim_ngrams = build_ngrams(claim_ctokens, 4)
        if claim_ngrams:
            ngram_hits = sum(1 for ng in claim_ngrams if ng in source_ngram_set)
            ngram_score = ngram_hits / len(claim_ngrams)

            if ngram_score < NGRAM_GROUNDING_WARN:
                sev = "BLOCKING" if claim_class in TIER_A_CLASSES else "MAJOR"
                add_finding(
                    findings, "R12", "ngram_grounding", sev, "FAIL", claim_id,
                    "R12-NGRAM-FAIL",
                    f"4-gram grounding score {ngram_score:.1%} (threshold: {NGRAM_GROUNDING_WARN:.0%}). "
                    f"Claim phrasing diverges significantly from source.",
                )
            elif ngram_score < NGRAM_GROUNDING_PASS:
                add_finding(
                    findings, "R12", "ngram_grounding", "MINOR", "WARN", claim_id,
                    "R12-NGRAM-WARN",
                    f"4-gram grounding score {ngram_score:.1%} (pass: {NGRAM_GROUNDING_PASS:.0%}). "
                    f"Some phrasing not closely aligned with source.",
                )

        # (c) Sentence similarity floor (supplementary — MINOR severity only,
        # since legitimate paraphrasing and interpretation naturally diverge)
        claim_sentences = split_sentences(clean_text)
        if claim_sentences:
            source_sentences = split_sentences(source_text)
            if source_sentences:
                ungrounded_count = 0
                for sent in claim_sentences:
                    sent_norm = normalize_whitespace(sent).lower()
                    if len(sent_norm) < 30:
                        continue
                    best_sim = 0.0
                    for src_sent in source_sentences:
                        src_norm = normalize_whitespace(src_sent).lower()
                        sim = similarity(sent_norm, src_norm)
                        if sim > best_sim:
                            best_sim = sim
                        if best_sim > SENTENCE_SIM_FLOOR:
                            break  # fast exit once floor is met
                    if best_sim < SENTENCE_SIM_FLOOR:
                        ungrounded_count += 1
                # Only flag if majority of claim sentences are ungrounded
                total_checked = len([s for s in claim_sentences if len(normalize_whitespace(s)) >= 30])
                if total_checked > 0 and ungrounded_count > total_checked * 0.5:
                    add_finding(
                        findings, "R12", "sentence_grounding", "MINOR", "WARN", claim_id,
                        "R12-SENTENCE-UNGROUNDED",
                        f"{ungrounded_count}/{total_checked} sentences below similarity floor "
                        f"({SENTENCE_SIM_FLOOR}). Claim may contain substantial ungrounded content.",
                    )

    # Round 13: Raw text injection detection
    # Detect when large contiguous blocks from the source are pasted directly
    # into the digest without transformation, by measuring 15-gram overlap.
    digest_plain_text = extract_plain_text(digest_html)
    digest_words_r13 = digest_plain_text.lower().split()
    source_words_r13 = source_text.lower().split()
    N_R13 = 15
    source_ngrams_r13: set[tuple[str, ...]] = set()
    for i in range(len(source_words_r13) - N_R13 + 1):
        source_ngrams_r13.add(tuple(source_words_r13[i : i + N_R13]))
    if len(digest_words_r13) >= N_R13:
        total_r13 = len(digest_words_r13) - N_R13 + 1
        matched_r13 = sum(
            1
            for i in range(total_r13)
            if tuple(digest_words_r13[i : i + N_R13]) in source_ngrams_r13
        )
        ratio_r13 = matched_r13 / total_r13 if total_r13 > 0 else 0.0
        if ratio_r13 > 0.65:
            add_finding(
                findings,
                "R13",
                "raw_text_injection",
                "MAJOR",
                "FAIL",
                "-",
                "R13-RAW-TEXT-INJECTION",
                f"Raw text injection detected: {ratio_r13:.1%} of 15-gram windows are direct source copies (threshold: 65%). Digest appears to be source text dump, not a visual digest.",
            )
        elif ratio_r13 > 0.40:
            add_finding(
                findings,
                "R13",
                "raw_text_injection",
                "MINOR",
                "WARN",
                "-",
                "R13-RAW-TEXT-HIGH-OVERLAP",
                f"High source overlap: {ratio_r13:.1%} of 15-gram windows match source text directly (threshold: 40%). Consider adding more original interpretation.",
            )

    # Round 14: Interpretation density check
    # Ensure the digest contains genuine interpretation content, not just
    # structural wrappers around copied source text.
    interp_pattern = re.compile(
        r'<div\s[^>]*class="[^"]*(?:interpretation-box|analysis-box|intuition)[^"]*"[^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    interp_blocks = interp_pattern.findall(digest_html)
    interp_text = " ".join(extract_plain_text(block) for block in interp_blocks)
    interp_word_count = len(interp_text.split()) if interp_text.strip() else 0
    digest_total_word_count = len(digest_plain_text.split()) if digest_plain_text.strip() else 0

    # Only activate R14 density check when:
    # 1. The digest has enough words to evaluate density meaningfully (≥100 words).
    # 2. The digest already uses the interpretation-box convention at least somewhere
    #    (a digest that never uses this convention is exempt from the density check).
    R14_MIN_DIGEST_WORDS = 100
    # Compute digest_uses_interp_convention here so both sub-checks can share it.
    _interp_convention_pattern = re.compile(
        r'class="[^"]*(?:interpretation-box|analysis-box|intuition)[^"]*"',
        re.IGNORECASE,
    )
    digest_uses_interp_convention = bool(_interp_convention_pattern.search(digest_html))
    if digest_total_word_count >= R14_MIN_DIGEST_WORDS and digest_uses_interp_convention:
        interp_ratio = interp_word_count / digest_total_word_count
        if interp_ratio < 0.15:
            add_finding(
                findings,
                "R14",
                "interpretation_density",
                "MINOR",
                "WARN",
                "-",
                "R14-LOW-INTERPRETATION-DENSITY",
                f"Interpretation boxes contain only {interp_ratio:.1%} of total digest words (threshold: 15%). Digest may lack original analytical content.",
            )

    # Per-card interpretation check: each content-card with data-claim-class should
    # contain at least one interpretation element as a child.
    # This check only runs when the digest itself uses the interpretation-box convention
    # (i.e., at least one interpretation box exists anywhere in the document).
    # Digests that don't use this convention at all are exempt from per-card checks.
    # Per-card check reuses digest_uses_interp_convention computed above.
    if digest_uses_interp_convention:
        R14_MIN_CARD_WORDS = 80
        content_card_pattern = re.compile(
            r'<(?:div|article)\s[^>]*data-claim-class="[^"]*"[^>]*>(.*?)</(?:div|article)>',
            re.IGNORECASE | re.DOTALL,
        )
        for card_match in content_card_pattern.finditer(digest_html):
            card_html = card_match.group(0)
            card_plain = extract_plain_text(card_html)
            if len(card_plain.split()) < R14_MIN_CARD_WORDS:
                continue
            # Extract claim_id for reporting
            cid_match = re.search(r'data-claim-id="([^"]+)"', card_html, re.IGNORECASE)
            card_claim_id = cid_match.group(1) if cid_match else "-"
            if not _interp_convention_pattern.search(card_html):
                add_finding(
                    findings,
                    "R14",
                    "interpretation_density",
                    "MINOR",
                    "WARN",
                    card_claim_id,
                    "R14-CARD-MISSING-INTERPRETATION",
                    "Content card has no interpretation-box, analysis-box, or intuition element.",
                )

    # Round 15: Structural diversity / repetition padding detection
    # Compute type-token ratio (TTR) of the digest visible text.
    # Padded/repeated text produces a very low TTR.
    # Minimum word count guard: short digests inherently have high TTR, so
    # TTR-based padding detection only makes sense on longer texts.
    R15_MIN_DIGEST_WORDS = 100
    if len(digest_words_r13) >= R15_MIN_DIGEST_WORDS:
        unique_words_r15 = len(set(digest_words_r13))
        total_words_r15 = len(digest_words_r13)
        ttr = unique_words_r15 / total_words_r15
        if ttr < 0.12:
            add_finding(
                findings,
                "R15",
                "structural_diversity",
                "MAJOR",
                "FAIL",
                "-",
                "R15-VERY-LOW-TTR",
                f"Type-token ratio {ttr:.3f} is critically low (threshold: 0.12). Digest text appears heavily padded with repeated content.",
            )
        elif ttr < 0.20:
            add_finding(
                findings,
                "R15",
                "structural_diversity",
                "MINOR",
                "WARN",
                "-",
                "R15-LOW-TTR",
                f"Type-token ratio {ttr:.3f} is low (threshold: 0.20). Low vocabulary diversity suggests repetition or padding.",
            )

    # Round 16: Content Volume Audit
    # Verify digest visible-text word count is at least 1/2 of source paper word count.
    # This prevents thin, skeletal digests that omit most of the paper's content.
    # Uses source_text (raw extracted text) and digest_plain_text (HTML stripped).
    # Only activates for sources with >= 200 words (real papers); tiny test fixtures are exempt.
    source_word_count_r16 = len(source_text.split()) if source_text.strip() else 0
    digest_word_count_r16 = digest_total_word_count  # computed in R14 block
    R16_MIN_RATIO = 0.50
    R16_MIN_SOURCE_WORDS = 200
    if source_word_count_r16 >= R16_MIN_SOURCE_WORDS:
        volume_ratio = digest_word_count_r16 / source_word_count_r16
        if volume_ratio < R16_MIN_RATIO:
            add_finding(
                findings,
                "R16",
                "content_volume",
                "BLOCKING",
                "FAIL",
                "-",
                "R16-CONTENT-VOLUME-LOW",
                f"Digest word count ({digest_word_count_r16}) is {volume_ratio:.1%} of source ({source_word_count_r16}). "
                f"Minimum required: {R16_MIN_RATIO:.0%}. Digest is too thin and must be regenerated with more content.",
            )

    # Round 17: Interactive Visualization Count
    # Theory and premium digests must include a minimum number of interactive Canvas/SVG
    # visualizations to provide hands-on intuition beyond static prose.
    # Counts elements with class="interactive-viz" in the HTML.
    # Minimum thresholds by template family:
    #   theory: 2  (at least two core results need visual illustration)
    #   review: 1  (at least one framework or strand diagram)
    #   premium_academic: 2
    #   empirical/comparative: 1
    # Severity: WARN (blocks in strict mode) -- addable without full regeneration.
    import re as _re17
    r17_viz_count = len(_re17.findall(r'class=["\']interactive-viz["\']', digest_html))
    R17_MIN_VIZ = {"theory": 2, "review": 1, "premium_academic": 2, "empirical": 1, "comparative": 1}
    r17_threshold = R17_MIN_VIZ.get(template_family, 1)
    if r17_viz_count < r17_threshold:
        add_finding(
            findings,
            "R17",
            "interactive_viz_count",
            "MINOR",
            "WARN",
            "-",
            "R17-INTERACTIVE-VIZ-LOW",
            f"Digest contains {r17_viz_count} interactive-viz element(s); minimum recommended for '{template_family}' is {r17_threshold}. "
            f"Add Canvas/SVG visualizations after key result cards to improve reader comprehension.",
        )

    # Round 18: Static Image / Visualization Presence
    # Digest SHOULD include at least one visual element: either a static <img>, an inline
    # <svg>, OR a sufficient number of interactive Canvas vizzes (R17 passing).
    # Interactive Canvas visualizations are a superset of static images for comprehension,
    # so R18 only fires when BOTH static images are absent AND interactive vizzes are
    # below the R17 threshold. This avoids penalizing canvas-first digests.
    r18_img_count = len(_re17.findall(r'<img\b', digest_html, _re17.IGNORECASE))
    r18_svg_count = len(_re17.findall(r'<svg\b', digest_html, _re17.IGNORECASE))
    r18_has_visuals = (r18_img_count + r18_svg_count > 0) or (r17_viz_count >= r17_threshold)
    if not r18_has_visuals:
        add_finding(
            findings,
            "R18",
            "visual_presence",
            "MINOR",
            "WARN",
            "-",
            "R18-NO-VISUALS",
            f"Digest contains no static images (<img>/<svg>: {r18_img_count + r18_svg_count}) "
            f"and insufficient interactive visualizations ({r17_viz_count} < {r17_threshold} required). "
            "Add Canvas visualizations after key result cards or embed paper figures.",
        )

    # unreadable policy
    unreadable_claims = [c for c in ledger_claims if str(c.get("status")) == "UNREADABLE"]
    if unreadable_claims and "[UNREADABLE]" not in digest_html:
        add_finding(findings, "R2", "unreadable_marker", "BLOCKING", "FAIL", "-", "R2-UNREADABLE-MARKER-MISSING", "Ledger marks UNREADABLE but digest lacks [UNREADABLE] marker")

    for claim in unreadable_claims:
        claim_id = str(claim["claim_id"])
        if str(claim["claim_class"]) in TIER_A_CLASSES:
            text = str(claim["claim_text"]).lower()
            if "[unreadable]" not in text:
                add_finding(findings, "R2", "unreadable_assertion", "BLOCKING", "FAIL", claim_id, "R2-UNREADABLE-ASSERTION", "Tier-A UNREADABLE claim must be explicitly marked and not asserted as fact")

    status = aggregate_status(findings)

    major_warn_or_fail = any(f.severity == "MAJOR" and f.status in {"WARN", "FAIL"} for f in findings)
    blocked = status == "FAIL" or (status == "WARN" and args.strict)
    if args.fail_on_major and major_warn_or_fail:
        blocked = True

    md_report = findings_to_markdown(
        findings=findings,
        status=status,
        blocked=blocked,
        strict=args.strict,
        fail_on_major=args.fail_on_major,
        source=source_path,
        digest=digest_path,
        ledger=ledger_path,
        mode=args.mode,
        template_family=template_family,
        equation_results=equation_results,
    )
    report_path.write_text(md_report, encoding="utf-8")

    summary = {
        "blocking_fail": sum(1 for f in findings if f.severity == "BLOCKING" and f.status == "FAIL"),
        "major_fail": sum(1 for f in findings if f.severity == "MAJOR" and f.status == "FAIL"),
        "major_warn": sum(1 for f in findings if f.severity == "MAJOR" and f.status == "WARN"),
        "minor_warn": sum(1 for f in findings if f.severity == "MINOR" and f.status in {"WARN", "FAIL"}),
        "warnings": sum(1 for f in findings if f.status == "WARN"),
        "total_findings": len(findings),
        "claim_count": len(ledger_claims),
        "required_min_claims": min_claims,
    }

    payload = {
        "status": status,
        "strict": args.strict,
        "fail_on_major": args.fail_on_major,
        "blocked": blocked,
        "mode": args.mode,
        "template_family": template_family,
        "source": str(source_path),
        "digest": str(digest_path),
        "ledger": str(ledger_path),
        "summary": summary,
        "findings": [asdict(f) for f in findings],
        "equation_results": [asdict(e) for e in equation_results],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.emit_claim_csv:
        csv_path = Path(args.emit_claim_csv).expanduser().resolve()
        write_claim_csv(csv_path, merged_claim_rows)

    if blocked:
        template_path = Path(__file__).resolve().parents[1] / "references" / "blocked_report_template.md"
        try:
            template_text = template_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            template_text = "# Blocked Delivery Report\n\n{{BLOCKING_REASONS}}"

        blocking_reasons = [f"- [{f.claim_id}] {f.message}" for f in findings if f.severity == "BLOCKING" and f.status in {"FAIL", "WARN"}]
        major_reasons = [f"- [{f.claim_id}] {f.message}" for f in findings if f.severity == "MAJOR" and f.status in {"FAIL", "WARN"}]
        minor_reasons = [f"- [{f.claim_id}] {f.message}" for f in findings if f.severity == "MINOR" and f.status in {"FAIL", "WARN"}]

        round_buckets: dict[str, list[str]] = defaultdict(list)
        for f in findings:
            round_buckets[f.round_id].append(f"[{f.code}] {f.message}")
        round_lines = []
        for round_id in sorted(round_buckets):
            round_lines.append(f"- {round_id}")
            for msg in round_buckets[round_id]:
                round_lines.append(f"  - {msg}")

        codes = sorted({f.code for f in findings if f.status in {"FAIL", "WARN"}})

        rendered = build_blocked_report(
            template_text,
            {
                "GATE_STATUS": status,
                "STRICT_MODE": str(args.strict),
                "FAIL_ON_MAJOR": str(args.fail_on_major),
                "MODE": args.mode,
                "TEMPLATE_FAMILY": template_family or "-",
                "SOURCE": str(source_path),
                "DIGEST": str(digest_path),
                "LEDGER": str(ledger_path),
                "REPORT_MD": str(report_path),
                "REPORT_JSON": str(json_path),
                "BLOCKED_REPORT": str(blocked_report_path),
                "ERROR_CODES": "\n".join(f"- {code}" for code in codes) if codes else "- None",
                "BLOCKING_REASONS": "\n".join(blocking_reasons) if blocking_reasons else "- None",
                "MAJOR_REASONS": "\n".join(major_reasons) if major_reasons else "- None",
                "MINOR_REASONS": "\n".join(minor_reasons) if minor_reasons else "- None",
                "ROUND_BUCKETS": "\n".join(round_lines) if round_lines else "- None",
            },
        )
        blocked_report_path.write_text(rendered, encoding="utf-8")

    print(f"[anti-hallucination] status={status}")
    print(f"[anti-hallucination] blocked={blocked}")
    print(f"[anti-hallucination] markdown_report={report_path}")
    print(f"[anti-hallucination] json_report={json_path}")
    if args.emit_claim_csv:
        print(f"[anti-hallucination] claims_csv={Path(args.emit_claim_csv).expanduser().resolve()}")
    if blocked:
        print(f"[anti-hallucination] blocked_report={blocked_report_path}")

    if status == "FAIL":
        return 2
    if status == "WARN" and args.strict:
        return 3
    if status == "WARN" and args.fail_on_major and major_warn_or_fail:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

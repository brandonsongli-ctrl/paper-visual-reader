#!/usr/bin/env python3
"""One-click pipeline for paper-visual-reader v3."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_builder import (  # noqa: E402
    SourceBundle,
    build_claims,
    build_placeholder_map,
    detect_template_family,
)
from source_extractor import extract_source_text  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one-click paper visual reader pipeline.")

    parser.add_argument("--source", help="Source paper path (.pdf/.tex/.md/.txt).")
    parser.add_argument("--source-a", help="Mode C source A path.")
    parser.add_argument("--source-b", help="Mode C source B path.")

    parser.add_argument("--mode", choices=["A", "B", "C"], default="A", help="Digest mode.")
    parser.add_argument(
        "--template-family",
        choices=["auto", "theory", "empirical", "comparative"],
        default="auto",
        help="Template family selector.",
    )
    parser.add_argument("--language", choices=["en", "zh", "bilingual"], default="bilingual", help="Digest language mode.")

    parser.add_argument("--strict", dest="strict", action="store_true", default=True, help="Enable strict gate (default on).")
    parser.add_argument("--no-strict", dest="strict", action="store_false", help="Disable strict gate.")
    parser.add_argument("--fail-on-major", action="store_true", help="Block on MAJOR warnings even when strict is off.")

    parser.add_argument("--ocr", choices=["auto", "on", "off"], default="auto", help="OCR strategy.")
    parser.add_argument("--ocr-lang", default="eng", help="OCR language for tesseract.")
    parser.add_argument("--ocr-min-chars", type=int, default=600, help="Minimum characters before OCR fallback is skipped.")

    parser.add_argument("--out-dir", required=True, help="Output directory.")
    parser.add_argument("--paper-short", help="Optional output short name override.")
    parser.add_argument("--require-min-claims", type=int, help="Override minimum claim count for coverage check.")
    parser.add_argument("--emit-claim-csv", action="store_true", help="Emit claim CSV artifact.")

    return parser.parse_args()


def safe_slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("_")
    return slug or "paper"


def title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        compact = line.strip()
        if len(compact) >= 8:
            return compact[:140]
    return fallback


def render_template(template_text: str, mapping: dict[str, str]) -> str:
    thm_html = mapping.get("THM_LOOP_HTML", "")
    lemma_html = mapping.get("LEMMA_LOOP_HTML", "")
    
    if "{{THM_LOOP_HTML}}" in template_text:
        template_text = template_text.replace("{{THM_LOOP_HTML}}", thm_html)
    if "{{LEMMA_LOOP_HTML}}" in template_text:
        template_text = template_text.replace("{{LEMMA_LOOP_HTML}}", lemma_html)

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return mapping.get(key, f"[{key}]")

    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", repl, template_text)


def _resolve_mode_sources(args: argparse.Namespace) -> tuple[Path | None, Path | None, Path | None]:
    source = Path(args.source).expanduser().resolve() if args.source else None
    source_a = Path(args.source_a).expanduser().resolve() if args.source_a else None
    source_b = Path(args.source_b).expanduser().resolve() if args.source_b else None

    if args.mode in {"A", "B"} and not source:
        raise ValueError("--source is required for mode A/B")

    if args.mode == "C":
        dual = source_a is not None and source_b is not None
        if not dual and source is None:
            raise ValueError("Mode C requires --source OR both --source-a and --source-b")

    return source, source_a, source_b


def _bundle_from_extraction(label: str, source_path: Path, text: str) -> SourceBundle:
    return SourceBundle(label=label, source_path=source_path, text=text)


def main() -> int:
    args = parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        source, source_a, source_b = _resolve_mode_sources(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[pipeline] argument error: {exc}", file=sys.stderr)
        return 1

    extraction_notes: list[str] = []

    bundle_main: SourceBundle
    bundle_a: SourceBundle | None = None
    bundle_b: SourceBundle | None = None

    try:
        if args.mode == "C" and source_a and source_b:
            res_a = extract_source_text(source_a, ocr=args.ocr, ocr_lang=args.ocr_lang, ocr_min_chars=args.ocr_min_chars)
            res_b = extract_source_text(source_b, ocr=args.ocr, ocr_lang=args.ocr_lang, ocr_min_chars=args.ocr_min_chars)
            bundle_a = _bundle_from_extraction("A", source_a, res_a.text)
            bundle_b = _bundle_from_extraction("B", source_b, res_b.text)
            merged_text = f"Paper A source ({source_a.name}):\n{res_a.text}\n\nPaper B source ({source_b.name}):\n{res_b.text}".strip()
            synthetic_source = out_dir / "mode_c_merged_source.txt"
            synthetic_source.write_text(merged_text + "\n", encoding="utf-8")
            bundle_main = _bundle_from_extraction("MAIN", synthetic_source, merged_text)
            extraction_notes.extend([
                f"source_a_method={res_a.method}",
                f"source_a_chars={res_a.quality.char_count}",
                f"source_b_method={res_b.method}",
                f"source_b_chars={res_b.quality.char_count}",
            ])
        else:
            assert source is not None
            res = extract_source_text(source, ocr=args.ocr, ocr_lang=args.ocr_lang, ocr_min_chars=args.ocr_min_chars)
            bundle_main = _bundle_from_extraction("MAIN", source, res.text)
            extraction_notes.extend([
                f"source_method={res.method}",
                f"source_chars={res.quality.char_count}",
                f"source_score={res.quality.score:.2f}",
                f"source_attempts={','.join(res.attempts)}",
            ])
    except Exception as exc:  # noqa: BLE001
        print(f"[pipeline] source extraction error: {exc}", file=sys.stderr)
        return 1

    if not bundle_main.text.strip():
        print("[pipeline] extraction produced empty text", file=sys.stderr)
        return 1

    base_source_for_name = source or source_a or bundle_main.source_path
    paper_short = safe_slug(args.paper_short or base_source_for_name.stem)

    family = args.template_family
    if family == "auto":
        family = detect_template_family(bundle_main.text, args.mode)

    claims = build_claims(
        mode=args.mode,
        template_family=family,
        language=args.language,
        source_bundle=bundle_main,
        source_a=bundle_a,
        source_b=bundle_b,
    )

    paper_title = title_from_text(bundle_main.text, base_source_for_name.stem)

    placeholders = build_placeholder_map(
        paper_title=paper_title,
        paper_short=paper_short,
        mode=args.mode,
        family=family,
        claims=claims,
        strict=args.strict,
        gate_status="PENDING",
        language=args.language,
        source_a_name=(source_a.name if source_a else ""),
        source_b_name=(source_b.name if source_b else ""),
    )

    template_root = Path(__file__).resolve().parents[1] / "references"
    template_path = template_root / "templates" / f"{family}.html"
    if not template_path.exists():
        template_path = template_root / "html_template.html"
    template_text = template_path.read_text(encoding="utf-8")

    base = out_dir / f"visual_digest_{paper_short}"
    html_path = Path(str(base) + ".html")
    ledger_path = Path(str(base) + ".evidence_ledger.json")
    report_md = Path(str(base) + ".anti_hallucination_report.md")
    report_json = Path(str(base) + ".anti_hallucination_report.json")
    blocked_md = Path(str(base) + ".blocked.md")
    claims_csv = Path(str(base) + ".claims.csv")
    gate_summary = Path(str(base) + ".gate_summary.txt")
    extracted_source_txt = Path(str(base) + ".source_extracted.txt")

    html_path.write_text(render_template(template_text, placeholders), encoding="utf-8")

    ledger_source_value: object = str(bundle_main.source_path)
    if args.mode == "C" and source_a and source_b:
        ledger_source_value = {
            "source_a": str(source_a),
            "source_b": str(source_b),
            "merged_source": str(bundle_main.source_path),
        }

    ledger_payload = {
        "version": "EvidenceLedgerV1",
        "mode": args.mode,
        "source": ledger_source_value,
        "template_family": family,
        "language": args.language,
        "claims": claims,
    }
    ledger_path.write_text(json.dumps(ledger_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    guard_script = Path(__file__).with_name("anti_hallucination_guard.py")

    min_claims_default = {"theory": 4, "empirical": 5, "comparative": 4}
    require_min_claims = args.require_min_claims if args.require_min_claims is not None else min_claims_default.get(family, 3)

    extracted_source_txt.write_text(bundle_main.text + "\n", encoding="utf-8")
    guard_source = extracted_source_txt

    cmd = [
        sys.executable,
        str(guard_script),
        "--source",
        str(guard_source),
        "--digest",
        str(html_path),
        "--ledger",
        str(ledger_path),
        "--report",
        str(report_md),
        "--json-report",
        str(report_json),
        "--blocked-report",
        str(blocked_md),
        "--mode",
        args.mode,
        "--template-family",
        family,
        "--require-min-claims",
        str(require_min_claims),
    ]

    if args.strict:
        cmd.append("--strict")
    if args.fail_on_major:
        cmd.append("--fail-on-major")
    if args.emit_claim_csv:
        cmd.extend(["--emit-claim-csv", str(claims_csv)])

    result = subprocess.run(cmd, check=False)

    blocked = True
    status = "FAIL"
    if report_json.exists():
        payload = json.loads(report_json.read_text(encoding="utf-8"))
        blocked = bool(payload.get("blocked", True))
        status = str(payload.get("status", "FAIL"))

    draft_path = None
    if blocked and html_path.exists():
        draft_path = Path(str(base) + ".draft.html")
        html_path.replace(draft_path)
    elif not blocked:
        final_map = build_placeholder_map(
            paper_title=paper_title,
            paper_short=paper_short,
            mode=args.mode,
            family=family,
            claims=claims,
            strict=args.strict,
            gate_status=status,
            language=args.language,
            source_a_name=(source_a.name if source_a else ""),
            source_b_name=(source_b.name if source_b else ""),
        )
        html_path.write_text(render_template(template_text, final_map), encoding="utf-8")

    summary_lines = [
        f"mode={args.mode}",
        f"template_family={family}",
        f"language={args.language}",
        f"strict={args.strict}",
        f"fail_on_major={args.fail_on_major}",
        f"ocr={args.ocr}",
        f"ocr_lang={args.ocr_lang}",
        f"ocr_min_chars={args.ocr_min_chars}",
        f"status={status}",
        f"blocked={blocked}",
        f"ledger={ledger_path}",
        f"source_for_guard={guard_source}",
        f"report_md={report_md}",
        f"report_json={report_json}",
        f"blocked_md={blocked_md}",
    ]
    summary_lines.extend(extraction_notes)

    if draft_path:
        summary_lines.append(f"draft_html={draft_path}")
    else:
        summary_lines.append(f"final_html={html_path}")
    if args.emit_claim_csv:
        summary_lines.append(f"claims_csv={claims_csv}")

    gate_summary.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("[pipeline] completed")
    print(f"[pipeline] status={status} blocked={blocked}")
    print(f"[pipeline] summary={gate_summary}")

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

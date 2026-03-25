#!/usr/bin/env python3
"""Run regression fixture matrix and v3 e2e checks for paper-visual-reader."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_guard_case(root: Path, name: str, mode: str, expected_status: str, expected_rc: int, extra: list[str] | None = None) -> tuple[bool, str]:
    fixture_dir = root / "fixtures" / name
    out_prefix = Path("/tmp") / f"pvr3_guard_{name}"

    cmd = [
        sys.executable,
        str(root / "anti_hallucination_guard.py"),
        "--source",
        str(fixture_dir / "source.txt"),
        "--digest",
        str(fixture_dir / "digest.html"),
        "--ledger",
        str(fixture_dir / "ledger.json"),
        "--report",
        str(out_prefix.with_suffix(".md")),
        "--json-report",
        str(out_prefix.with_suffix(".json")),
        "--blocked-report",
        str(out_prefix.with_suffix(".blocked.md")),
        "--mode",
        mode,
    ]
    if extra:
        cmd.extend(extra)

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    json_file = out_prefix.with_suffix(".json")
    if not json_file.exists():
        return False, f"{name}: missing json report; rc={proc.returncode}; stderr={proc.stderr.strip()}"

    payload = json.loads(json_file.read_text(encoding="utf-8"))
    status = str(payload.get("status"))

    ok = proc.returncode == expected_rc and status == expected_status
    detail = f"guard::{name}: rc={proc.returncode} status={status} expected_rc={expected_rc} expected_status={expected_status}"
    return ok, detail


def run_pipeline_case(
    root: Path,
    case_name: str,
    mode: str,
    expected_status: str,
    expected_rc: int,
    source: Path | None = None,
    source_a: Path | None = None,
    source_b: Path | None = None,
    extra: list[str] | None = None,
) -> tuple[bool, str, dict[str, object]]:
    out_dir = Path("/tmp") / f"pvr3_pipe_{case_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(root / "paper_visual_reader_pipeline.py"),
        "--mode",
        mode,
        "--out-dir",
        str(out_dir),
        "--strict",
        "--template-family",
        "auto",
        "--language",
        "bilingual",
    ]

    if source is not None:
        cmd.extend(["--source", str(source)])
    if source_a is not None:
        cmd.extend(["--source-a", str(source_a)])
    if source_b is not None:
        cmd.extend(["--source-b", str(source_b)])
    if extra:
        cmd.extend(extra)

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)

    report_files = sorted(out_dir.glob("visual_digest_*.anti_hallucination_report.json"))
    if not report_files:
        return False, f"pipeline::{case_name}: missing report json rc={proc.returncode}; stderr={proc.stderr.strip()}", {}

    payload = json.loads(report_files[0].read_text(encoding="utf-8"))
    status = str(payload.get("status"))

    ok = proc.returncode == expected_rc and status == expected_status
    detail = f"pipeline::{case_name}: rc={proc.returncode} status={status} expected_rc={expected_rc} expected_status={expected_status}"
    return ok, detail, payload


def run_warn_strict_pair(root: Path) -> tuple[bool, list[str]]:
    fixture = root / "fixtures" / "pass_minimal"
    temp_digest = Path("/tmp/pvr3_warn_digest.html")
    src = (fixture / "digest.html").read_text(encoding="utf-8")
    temp_digest.write_text(src.replace("Main Paper §4", "Appendix A"), encoding="utf-8")

    base_cmd = [
        sys.executable,
        str(root / "anti_hallucination_guard.py"),
        "--source",
        str(fixture / "source.txt"),
        "--digest",
        str(temp_digest),
        "--ledger",
        str(fixture / "ledger.json"),
        "--report",
        "/tmp/pvr3_warn.md",
        "--json-report",
        "/tmp/pvr3_warn.json",
        "--blocked-report",
        "/tmp/pvr3_warn.blocked.md",
        "--mode",
        "A",
    ]

    normal = subprocess.run(base_cmd, check=False, capture_output=True, text=True)
    normal_payload = json.loads(Path("/tmp/pvr3_warn.json").read_text(encoding="utf-8"))

    strict_cmd = base_cmd + ["--strict"]
    strict_cmd[strict_cmd.index("/tmp/pvr3_warn.md")] = "/tmp/pvr3_warn_strict.md"
    strict_cmd[strict_cmd.index("/tmp/pvr3_warn.json")] = "/tmp/pvr3_warn_strict.json"
    strict_cmd[strict_cmd.index("/tmp/pvr3_warn.blocked.md")] = "/tmp/pvr3_warn_strict.blocked.md"
    strict = subprocess.run(strict_cmd, check=False, capture_output=True, text=True)
    strict_payload = json.loads(Path("/tmp/pvr3_warn_strict.json").read_text(encoding="utf-8"))

    checks = [
        f"warn_non_strict: rc={normal.returncode} status={normal_payload.get('status')} blocked={normal_payload.get('blocked')}",
        f"warn_strict: rc={strict.returncode} status={strict_payload.get('status')} blocked={strict_payload.get('blocked')}",
    ]

    ok = (
        normal.returncode == 0
        and str(normal_payload.get("status")) == "WARN"
        and bool(normal_payload.get("blocked")) is False
        and strict.returncode == 3
        and str(strict_payload.get("status")) == "WARN"
        and bool(strict_payload.get("blocked")) is True
    )

    return ok, checks


def compatibility_check(root: Path) -> tuple[bool, str]:
    fixture = root / "fixtures" / "pass_minimal"
    cmd = [
        sys.executable,
        str(root / "anti_hallucination_guard.py"),
        "--source",
        str(fixture / "source.txt"),
        "--digest",
        str(fixture / "digest.html"),
        "--ledger",
        str(fixture / "ledger.json"),
        "--report",
        "/tmp/pvr3_compat.md",
        "--json-report",
        "/tmp/pvr3_compat.json",
        "--blocked-report",
        "/tmp/pvr3_compat.blocked.md",
        "--mode",
        "A",
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    payload = json.loads(Path("/tmp/pvr3_compat.json").read_text(encoding="utf-8"))
    ok = proc.returncode == 0 and str(payload.get("status")) == "PASS"
    detail = f"compat_old_guard_cli: rc={proc.returncode} status={payload.get('status')}"
    return ok, detail


def make_scanned_pdf(path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (2400, 1200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = None
    for font_path in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_path, 52)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    y = 40
    lines = [
        "Section 3 (p.8) reports Table 1. The treatment coefficient is 1.25 with N = 320 and R2 = 0.41.",
        "Equation (1) in Section 4 (p.10): y_i = alpha + beta x_i + epsilon_i.",
        "The discussion suggests a positive effect under identifying assumptions.",
    ]
    for line in lines:
        draw.text((60, y), line, fill=(0, 0, 0), font=font)
        y += 120
    img.save(path, "PDF", resolution=300.0)


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []

    print("[fixtures] running guard regression matrix")
    guard_cases = [
        ("pass_minimal", "A", "PASS", 0),
        ("fail_missing_anchor", "A", "FAIL", 2),
        ("fail_equation_mismatch", "A", "WARN", 0),
        ("fail_numeric_untraceable", "A", "FAIL", 2),
        ("fail_causal_overclaim", "A", "FAIL", 2),
        ("pass_focus_minimal", "B", "PASS", 0),
        ("fail_focus_missing_anchor", "B", "FAIL", 2),
        ("fail_focus_unreadable_assertion", "B", "FAIL", 2),
        ("pass_mode_c_attributed", "C", "PASS", 0),
        ("fail_mode_c_cross_attribution", "C", "FAIL", 2),
        ("fail_mode_c_missing_paper_tag", "C", "FAIL", 2),
    ]

    for name, mode, expected_status, expected_rc in guard_cases:
        ok, detail = run_guard_case(root, name, mode, expected_status, expected_rc)
        print(detail)
        if not ok:
            failures.append(detail)

    ok_compat, compat_detail = compatibility_check(root)
    print(compat_detail)
    if not ok_compat:
        failures.append(compat_detail)

    ok_warn, warn_details = run_warn_strict_pair(root)
    for line in warn_details:
        print(line)
    if not ok_warn:
        failures.extend(warn_details)

    print("[fixtures] running pipeline e2e matrix")
    fixture_root = root / "fixtures"

    checks: list[tuple[bool, str]] = []

    ok, detail, payload = run_pipeline_case(
        root,
        "e2e_mode_a_pipeline_strict_pass",
        "A",
        "PASS",
        0,
        source=fixture_root / "pass_minimal" / "source.txt",
    )
    checks.append((ok, detail))

    ok_b, detail_b, _ = run_pipeline_case(
        root,
        "e2e_mode_b_pipeline_strict_pass",
        "B",
        "PASS",
        0,
        source=fixture_root / "pass_focus_minimal" / "source.txt",
    )
    checks.append((ok_b, detail_b))

    ok_c_single, detail_c_single, _ = run_pipeline_case(
        root,
        "e2e_mode_c_single_source_compat_pass",
        "C",
        "PASS",
        0,
        source=fixture_root / "pass_mode_c_attributed" / "source.txt",
    )
    checks.append((ok_c_single, detail_c_single))

    source_a = Path("/tmp/pvr3_mode_c_a.txt")
    source_b = Path("/tmp/pvr3_mode_c_b.txt")
    source_a.write_text("Paper A (2020) Section 2 (p.4) reports persistent institutions and associated effects.\n", encoding="utf-8")
    source_b.write_text("Paper B (2021) Section 3 (p.5) reports adaptive market responses and associated effects.\n", encoding="utf-8")
    ok_c_dual, detail_c_dual, _ = run_pipeline_case(
        root,
        "e2e_mode_c_dual_source_strict_pass",
        "C",
        "PASS",
        0,
        source_a=source_a,
        source_b=source_b,
    )
    checks.append((ok_c_dual, detail_c_dual))

    scanned_pdf = Path("/tmp/pvr3_scanned.pdf")
    make_scanned_pdf(scanned_pdf)
    ok_ocr, detail_ocr, _ = run_pipeline_case(
        root,
        "ocr_scanned_pdf_pass",
        "A",
        "PASS",
        0,
        source=scanned_pdf,
        extra=["--ocr", "on", "--ocr-lang", "eng", "--ocr-min-chars", "100"],
    )
    checks.append((ok_ocr, detail_ocr))

    # Regression checks for false positives.
    eq_fail_codes = {f.get("code") for f in payload.get("findings", []) if str(f.get("round_id")) == "R4"}
    eq_reg_ok = "R4-EQUATION-FAIL" not in eq_fail_codes
    checks.append((eq_reg_ok, f"equation_false_positive_regression: codes={sorted(eq_fail_codes)}"))

    r3_findings = [f for f in payload.get("findings", []) if str(f.get("round_id")) == "R3"]
    noise_ok = len(r3_findings) == 0
    checks.append((noise_ok, f"numeric_anchor_noise_regression: r3_findings={len(r3_findings)}"))

    mode_c_fail_ok, mode_c_fail_detail = run_guard_case(root, "fail_mode_c_cross_attribution", "C", "FAIL", 2)
    checks.append((mode_c_fail_ok, f"mode_c_cross_ownership_fail: {mode_c_fail_detail}"))

    for ok_case, detail in checks:
        print(detail)
        if not ok_case:
            failures.append(detail)

    summary = Path("/tmp/pvr3_fixture_summary.txt")
    summary_lines = [
        "paper-visual-reader v3 fixture summary",
        f"guard_cases={len(guard_cases)}",
        f"pipeline_checks={len(checks)}",
        f"compatibility_check={ok_compat}",
        f"warn_strict_pair={ok_warn}",
        f"failures={len(failures)}",
    ]
    summary.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"[fixtures] summary={summary}")

    if failures:
        print("[fixtures] FAILED")
        for line in failures:
            print(f"  - {line}")
        return 1

    print("[fixtures] PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Source extraction utilities for paper-visual-reader v3."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TextQuality:
    char_count: int
    line_count: int
    alpha_ratio: float
    digit_ratio: float
    score: float


@dataclass
class ExtractionResult:
    source_path: Path
    text: str
    method: str
    quality: TextQuality
    attempts: list[str]


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v]+", " ", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def assess_quality(text: str) -> TextQuality:
    compact = normalize_text(text)
    char_count = len(compact)
    line_count = max(1, len([line for line in compact.splitlines() if line.strip()]))
    letters = sum(1 for c in compact if c.isalpha())
    digits = sum(1 for c in compact if c.isdigit())
    alpha_ratio = (letters / char_count) if char_count else 0.0
    digit_ratio = (digits / char_count) if char_count else 0.0
    score = char_count * (0.6 + alpha_ratio) - (digit_ratio * 50.0)
    return TextQuality(
        char_count=char_count,
        line_count=line_count,
        alpha_ratio=alpha_ratio,
        digit_ratio=digit_ratio,
        score=score,
    )


def _extract_pdftotext(source_path: Path) -> str:
    if shutil.which("pdftotext") is None:
        return ""
    proc = subprocess.run(["pdftotext", str(source_path), "-"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return ""
    return normalize_text(proc.stdout)


def _extract_fitz_text(source_path: Path) -> str:
    try:
        import fitz  # type: ignore
    except Exception:
        return ""

    parts: list[str] = []
    try:
        doc = fitz.open(str(source_path))
        for page in doc:
            parts.append(page.get_text("text") or "")
        doc.close()
    except Exception:
        return ""
    return normalize_text("\n".join(parts))


def _extract_fitz_ocr(source_path: Path, ocr_lang: str) -> str:
    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        return ""
    try:
        import fitz  # type: ignore
    except Exception:
        return ""

    parts: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="pvr3_fitz_ocr_") as tmpdir:
            doc = fitz.open(str(source_path))
            for idx, page in enumerate(doc, start=1):
                png_file = Path(tmpdir) / f"fitz-{idx}.png"
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                pix.save(str(png_file))
                parts.append(_ocr_image_with_tesseract(png_file, ocr_lang, tesseract_cmd))
            doc.close()
    except Exception:
        return ""
    return normalize_text("\n".join(parts))


def _extract_pdftoppm_ocr(source_path: Path, ocr_lang: str) -> str:
    if shutil.which("pdftoppm") is None:
        return ""

    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        return ""

    texts: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pvr3_ocr_") as tmpdir:
        prefix = Path(tmpdir) / "page"
        proc = subprocess.run(
            ["pdftoppm", "-png", str(source_path), str(prefix)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return ""

        for png_file in sorted(Path(tmpdir).glob("page-*.png")):
            try:
                texts.append(_ocr_image_with_tesseract(png_file, ocr_lang, tesseract_cmd))
            except Exception:
                continue
    return normalize_text("\n".join(texts))


def _ocr_image_with_tesseract(image_path: Path, ocr_lang: str, tesseract_cmd: str) -> str:
    proc = subprocess.run(
        [tesseract_cmd, str(image_path), "stdout", "-l", ocr_lang, "--psm", "6"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout or ""


def extract_source_text(
    source_path: Path,
    ocr: str = "auto",
    ocr_lang: str = "eng",
    ocr_min_chars: int = 600,
) -> ExtractionResult:
    source_path = source_path.expanduser().resolve()
    attempts: list[str] = []

    if source_path.suffix.lower() != ".pdf":
        text = normalize_text(source_path.read_text(encoding="utf-8", errors="ignore"))
        quality = assess_quality(text)
        return ExtractionResult(source_path=source_path, text=text, method="plain_text", quality=quality, attempts=["plain_text"])

    candidates: list[tuple[str, str, TextQuality]] = []

    txt_pdft = _extract_pdftotext(source_path)
    attempts.append("pdftotext")
    if txt_pdft:
        candidates.append(("pdftotext", txt_pdft, assess_quality(txt_pdft)))

    txt_fitz = _extract_fitz_text(source_path)
    attempts.append("fitz_text")
    if txt_fitz:
        candidates.append(("fitz_text", txt_fitz, assess_quality(txt_fitz)))

    best_method = ""
    best_text = ""
    best_quality = TextQuality(0, 1, 0.0, 0.0, 0.0)
    if candidates:
        best_method, best_text, best_quality = max(candidates, key=lambda item: item[2].score)

    should_try_ocr = False
    if ocr == "on":
        should_try_ocr = True
    elif ocr == "auto":
        should_try_ocr = best_quality.char_count < ocr_min_chars

    if should_try_ocr:
        ocr_method = ""
        attempts.append("fitz_ocr")
        txt_ocr = _extract_fitz_ocr(source_path, ocr_lang=ocr_lang)
        if txt_ocr:
            ocr_method = "fitz_ocr"
        if not txt_ocr:
            attempts.append("pdftoppm_ocr")
            txt_ocr = _extract_pdftoppm_ocr(source_path, ocr_lang=ocr_lang)
            if txt_ocr:
                ocr_method = "pdftoppm_ocr"
        if txt_ocr:
            q_ocr = assess_quality(txt_ocr)
            if q_ocr.score >= best_quality.score:
                best_method, best_text, best_quality = ocr_method, txt_ocr, q_ocr

    return ExtractionResult(
        source_path=source_path,
        text=best_text,
        method=best_method or "pdf_empty",
        quality=best_quality,
        attempts=attempts,
    )

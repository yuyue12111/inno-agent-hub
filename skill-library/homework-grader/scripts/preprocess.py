"""
Preprocess homework submissions (docx/pdf/jpg/png) into IR JSON format.

Usage:
    python preprocess.py <input_dir> --output <output_dir> [--rubric <rubric.yaml>]
    python preprocess.py --help

This script scans an input directory for supported file types, extracts text
and metadata, optionally runs gate checks from a rubric, and writes one IR
JSON file per submission to the output directory.

Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import fitz  # PyMuPDF
import yaml
from docx import Document as DocxDocument
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_TEXT_EXTENSIONS = {".docx", ".pdf"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS

CJK_RANGES = (
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
    (0x20000, 0x2A6DF),  # CJK Unified Ideographs Extension B
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
    (0x2F800, 0x2FA1F),  # CJK Compatibility Ideographs Supplement
    (0x3000, 0x303F),    # CJK Symbols and Punctuation
    (0x3040, 0x309F),    # Hiragana
    (0x30A0, 0x30FF),    # Katakana
    (0xAC00, 0xD7AF),    # Hangul Syllables
)

REFERENCE_KEYWORDS = [
    "参考文献", "参考资料", "引用文献", "引用",
    "References", "Bibliography", "Works Cited",
    "references", "bibliography", "works cited",
]

EMPTY_THRESHOLD = 10  # word/char count below this → empty_submission

logger = logging.getLogger("preprocess")


# ---------------------------------------------------------------------------
# Data structures (immutable where feasible)
# ---------------------------------------------------------------------------

class Section(NamedTuple):
    """A document section parsed from headings."""
    heading: str
    level: int
    text: str


@dataclass(frozen=True)
class TextMetadata:
    """Extracted metadata for a text document."""
    word_count: int
    paragraph_count: int
    heading_count: int
    has_references: bool
    language: str


@dataclass(frozen=True)
class ImageMetadata:
    """Extracted metadata for an image file."""
    width: int
    height: int
    file_size_bytes: int
    color_mode: str


@dataclass(frozen=True)
class GateResult:
    """Result of a single gate check."""
    gate_id: str
    gate_name: str
    passed: bool
    details: str
    on_fail: str


@dataclass
class ProcessingLogEntry:
    """A single entry in the processing log."""
    step: str
    status: str  # success | warning | error | skipped
    duration_ms: int = 0
    message: str = ""


@dataclass
class ProcessingContext:
    """Mutable accumulator for processing a single file."""
    log: list[ProcessingLogEntry] = field(default_factory=list)
    gate_results: list[GateResult] = field(default_factory=list)

    def add_log(
        self,
        step: str,
        status: str,
        duration_ms: int = 0,
        message: str = "",
    ) -> None:
        self.log.append(ProcessingLogEntry(
            step=step, status=status,
            duration_ms=duration_ms, message=message,
        ))


# ---------------------------------------------------------------------------
# CJK / language helpers
# ---------------------------------------------------------------------------

def _is_cjk_char(char: str) -> bool:
    """Return True if the character falls within a CJK Unicode range."""
    cp = ord(char)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def _cjk_ratio(text: str) -> float:
    """Return the ratio of CJK characters to total non-whitespace characters."""
    non_ws = [ch for ch in text if not ch.isspace()]
    if not non_ws:
        return 0.0
    cjk_count = sum(1 for ch in non_ws if _is_cjk_char(ch))
    return cjk_count / len(non_ws)


def detect_language(text: str) -> str:
    """Heuristic language detection: CJK ratio > 0.3 → zh-CN, else en."""
    return "zh-CN" if _cjk_ratio(text) > 0.3 else "en"


def count_words(text: str, language: str) -> int:
    """Count words appropriate to the detected language.

    CJK (zh-CN): count characters excluding whitespace and punctuation.
    Alphabetic (en): count whitespace-separated tokens.
    """
    if language == "zh-CN":
        return sum(
            1 for ch in text
            if not ch.isspace()
            and unicodedata.category(ch)[0] not in ("P", "S", "Z")
        )
    return len(text.split())


# ---------------------------------------------------------------------------
# Text extraction — DOCX
# ---------------------------------------------------------------------------

def _docx_heading_level(paragraph) -> int | None:
    """Return heading level (1-6) for a paragraph, or None if not a heading."""
    style_name: str = paragraph.style.name or ""
    if style_name.startswith("Heading"):
        try:
            return int(style_name.split()[-1])
        except (ValueError, IndexError):
            return None
    return None


def extract_docx(file_path: Path) -> tuple[str, list[Section]]:
    """Extract full Markdown text and sections from a .docx file.

    Raises on password-protected or corrupted files.
    """
    doc = DocxDocument(str(file_path))
    md_lines: list[str] = []
    sections: list[Section] = []
    current_heading: str = ""
    current_level: int = 0
    current_body_lines: list[str] = []

    def _flush_section() -> None:
        if current_heading or current_body_lines:
            body = "\n\n".join(
                line for line in current_body_lines if line.strip()
            )
            sections.append(Section(
                heading=current_heading,
                level=current_level if current_level > 0 else 1,
                text=body,
            ))

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        level = _docx_heading_level(para)
        if level is not None:
            # Flush the previous section
            _flush_section()
            current_heading = text
            current_level = level
            current_body_lines = []
            md_lines.append(f"{'#' * level} {text}")
        else:
            current_body_lines.append(text)
            md_lines.append(text)

    # Flush the last section
    _flush_section()

    # If no headings were found, split on double newlines into one section
    if not any(s.heading for s in sections) and md_lines:
        full = "\n\n".join(md_lines)
        sections = [Section(heading="", level=1, text=full)]

    full_text = "\n\n".join(md_lines)
    return full_text, sections


# ---------------------------------------------------------------------------
# Text extraction — PDF
# ---------------------------------------------------------------------------

def extract_pdf(file_path: Path) -> tuple[str, list[Section]]:
    """Extract full text and sections from a .pdf file using PyMuPDF.

    Raises on password-protected or corrupted files.
    """
    doc = fitz.open(str(file_path))

    if doc.is_encrypted:
        doc.close()
        raise PermissionError(f"PDF is password-protected: {file_path.name}")

    all_blocks: list[str] = []
    for page in doc:
        blocks = page.get_text("blocks")  # list of (x0, y0, x1, y1, text, …)
        for block in blocks:
            text = block[4].strip() if isinstance(block[4], str) else ""
            if text:
                all_blocks.append(text)
    doc.close()

    # Heuristic heading detection: short lines (<80 chars) that look like
    # headings (e.g. start with Chinese numbering "一、" or "第X章" or are
    # ALL CAPS or start with a number followed by a period).
    heading_patterns = [
        re.compile(r"^[一二三四五六七八九十]+[、．.]"),   # Chinese numbering
        re.compile(r"^第.{1,3}[章节部分]"),              # 第X章/节
        re.compile(r"^\d+(\.\d+)*\s+\S"),               # 1. / 1.1 / 2.3.1
        re.compile(r"^[A-Z][A-Z\s]{3,}$"),              # ALL CAPS HEADING
        re.compile(r"^(Abstract|Introduction|Conclusion|References|"
                   r"参考文献|摘要|引言|结论|总结)", re.IGNORECASE),
    ]

    md_lines: list[str] = []
    sections: list[Section] = []
    current_heading: str = ""
    current_level: int = 0
    current_body_lines: list[str] = []

    def _flush() -> None:
        nonlocal current_heading, current_level, current_body_lines
        if current_heading or current_body_lines:
            body = "\n\n".join(
                line for line in current_body_lines if line.strip()
            )
            sections.append(Section(
                heading=current_heading,
                level=current_level if current_level > 0 else 1,
                text=body,
            ))

    def _is_heading(text: str) -> bool:
        if len(text) > 80:
            return False
        return any(p.search(text) for p in heading_patterns)

    def _guess_level(text: str) -> int:
        """Guess heading level from numbering depth."""
        m = re.match(r"^(\d+(?:\.\d+)*)", text)
        if m:
            return min(m.group(1).count(".") + 1, 6)
        return 1

    for block_text in all_blocks:
        if _is_heading(block_text):
            _flush()
            current_heading = block_text
            current_level = _guess_level(block_text)
            current_body_lines = []
            md_lines.append(f"{'#' * current_level} {block_text}")
        else:
            current_body_lines.append(block_text)
            md_lines.append(block_text)

    _flush()

    if not any(s.heading for s in sections) and md_lines:
        full = "\n\n".join(md_lines)
        sections = [Section(heading="", level=1, text=full)]

    full_text = "\n\n".join(md_lines)
    return full_text, sections


# ---------------------------------------------------------------------------
# Image metadata extraction
# ---------------------------------------------------------------------------

def extract_image_metadata(file_path: Path) -> ImageMetadata:
    """Open an image with Pillow and extract metadata."""
    with Image.open(file_path) as img:
        img.verify()  # detect corruption early
    # Re-open after verify (verify can close the file)
    with Image.open(file_path) as img:
        width, height = img.size
        mode = img.mode
    size_bytes = file_path.stat().st_size
    return ImageMetadata(
        width=width,
        height=height,
        file_size_bytes=size_bytes,
        color_mode=mode,
    )


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_text_metadata(full_text: str, sections: list[Section]) -> TextMetadata:
    """Derive metadata from extracted text content."""
    language = detect_language(full_text)
    word_count = count_words(full_text, language)
    paragraphs = [p for p in full_text.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)
    heading_count = sum(1 for s in sections if s.heading)
    has_references = any(kw in full_text for kw in REFERENCE_KEYWORDS)
    return TextMetadata(
        word_count=word_count,
        paragraph_count=paragraph_count,
        heading_count=heading_count,
        has_references=has_references,
        language=language,
    )


# ---------------------------------------------------------------------------
# Gate checks (non-LLM only)
# ---------------------------------------------------------------------------

def run_keyword_gate(
    gate: dict[str, Any],
    full_text: str,
) -> GateResult:
    """Execute a keyword gate check."""
    params = gate.get("parameters", {})
    keywords: list[str] = params.get("keywords", [])
    min_count: int = params.get("min_count", 1)
    text_lower = full_text.lower()

    matched = [kw for kw in keywords if kw.lower() in text_lower]
    passed = len(matched) >= min_count

    if passed:
        details = (
            f"Found {len(matched)} of required {min_count} keywords: "
            f"{matched}"
        )
    else:
        details = (
            f"Missing required keywords. Found {len(matched)} of "
            f"{min_count}: {matched}"
        )

    return GateResult(
        gate_id=gate["id"],
        gate_name=gate.get("name", gate["id"]),
        passed=passed,
        details=details,
        on_fail=gate.get("on_fail", "warn"),
    )


def run_length_gate(
    gate: dict[str, Any],
    full_text: str,
    language: str,
) -> GateResult:
    """Execute a length gate check."""
    params = gate.get("parameters", {})
    min_words: int = params.get("min_words", 0)
    max_words: int = params.get("max_words", float("inf"))  # type: ignore[assignment]
    wc = count_words(full_text, language)
    passed = min_words <= wc <= max_words

    details = f"Word count: {wc} (required: {min_words}-{max_words})"

    return GateResult(
        gate_id=gate["id"],
        gate_name=gate.get("name", gate["id"]),
        passed=passed,
        details=details,
        on_fail=gate.get("on_fail", "warn"),
    )


def run_structure_gate(
    gate: dict[str, Any],
    sections: list[Section],
    source_files: list[str],
) -> GateResult:
    """Execute a structure gate check."""
    params = gate.get("parameters", {})
    required_sections: list[str] = params.get("required_sections", [])
    required_files: list[str] = params.get("required_files", [])

    missing: list[str] = []

    if required_sections:
        heading_texts = [s.heading.lower().strip() for s in sections]
        for req in required_sections:
            req_lower = req.lower().strip()
            # Fuzzy: check if any heading contains the required section name
            found = any(req_lower in h for h in heading_texts)
            if not found:
                missing.append(req)

    if required_files:
        file_names = [Path(f).name for f in source_files]
        for pattern in required_files:
            from fnmatch import fnmatch
            found = any(fnmatch(fn, pattern) for fn in file_names)
            if not found:
                missing.append(f"file:{pattern}")

    passed = len(missing) == 0
    if passed:
        details = "All required sections/files present"
    else:
        details = f"Missing: {missing}"

    return GateResult(
        gate_id=gate["id"],
        gate_name=gate.get("name", gate["id"]),
        passed=passed,
        details=details,
        on_fail=gate.get("on_fail", "warn"),
    )


def run_gate_checks(
    rubric: dict[str, Any],
    full_text: str,
    sections: list[Section],
    language: str,
    source_files: list[str],
) -> list[GateResult]:
    """Run all non-LLM gate checks defined in the rubric.

    Custom gates (requiring LLM) are skipped at preprocessing time.
    """
    gates = rubric.get("gates", [])
    results: list[GateResult] = []

    for gate in gates:
        method = gate.get("check_method", "")

        if method == "keyword":
            results.append(run_keyword_gate(gate, full_text))
        elif method == "length":
            results.append(run_length_gate(gate, full_text, language))
        elif method == "structure":
            results.append(run_structure_gate(gate, sections, source_files))
        elif method == "custom":
            # Custom gates require an LLM call — skip during preprocessing
            results.append(GateResult(
                gate_id=gate["id"],
                gate_name=gate.get("name", gate["id"]),
                passed=True,  # Deferred
                details="Custom gate deferred to scoring phase (requires LLM)",
                on_fail=gate.get("on_fail", "warn"),
            ))
            logger.info(
                "Skipped custom gate %s (requires LLM)", gate["id"]
            )
        else:
            logger.warning("Unknown gate check_method '%s' for gate %s",
                           method, gate.get("id", "?"))

    return results


# ---------------------------------------------------------------------------
# IR assembly
# ---------------------------------------------------------------------------

def build_text_ir(
    student_id: str,
    source_files: list[str],
    full_text: str,
    sections: list[Section],
    metadata: TextMetadata,
    gate_results: list[GateResult],
    processing_log: list[ProcessingLogEntry],
) -> dict[str, Any]:
    """Assemble an IR JSON dict for a text submission."""
    return {
        "student_id": student_id,
        "submission_type": "text",
        "source_files": source_files,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "word_count": metadata.word_count,
            "paragraph_count": metadata.paragraph_count,
            "heading_count": metadata.heading_count,
            "has_references": metadata.has_references,
            "language": metadata.language,
        },
        "content": {
            "full_text": full_text,
            "sections": [
                {"heading": s.heading, "level": s.level, "text": s.text}
                for s in sections
            ],
        },
        "gate_results": [
            {
                "gate_id": g.gate_id,
                "gate_name": g.gate_name,
                "passed": g.passed,
                "details": g.details,
                "on_fail": g.on_fail,
            }
            for g in gate_results
        ],
        "processing_log": [
            {
                "step": e.step,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "message": e.message,
            }
            for e in processing_log
        ],
    }


def build_image_ir(
    student_id: str,
    source_files: list[str],
    image_entries: list[dict[str, Any]],
    total_size_mb: float,
    resolutions: list[str],
    gate_results: list[GateResult],
    processing_log: list[ProcessingLogEntry],
) -> dict[str, Any]:
    """Assemble an IR JSON dict for an image submission."""
    return {
        "student_id": student_id,
        "submission_type": "image",
        "source_files": source_files,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "image_count": len(image_entries),
            "resolutions": resolutions,
            "total_size_mb": round(total_size_mb, 2),
        },
        "content": {
            "images": image_entries,
        },
        "gate_results": [
            {
                "gate_id": g.gate_id,
                "gate_name": g.gate_name,
                "passed": g.passed,
                "details": g.details,
                "on_fail": g.on_fail,
            }
            for g in gate_results
        ],
        "processing_log": [
            {
                "step": e.step,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "message": e.message,
            }
            for e in processing_log
        ],
    }


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------

def _timed(func, *args, **kwargs) -> tuple[Any, int]:
    """Run *func* and return (result, elapsed_ms)."""
    t0 = time.monotonic()
    result = func(*args, **kwargs)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    return result, elapsed_ms


def process_text_file(
    file_path: Path,
    student_id: str,
    rubric: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Process a single .docx or .pdf file into an IR dict.

    Returns None if the file cannot be processed.
    """
    ctx = ProcessingContext()
    ext = file_path.suffix.lower()
    source_files = [f"raw/{file_path.name}"]

    # --- Step 1: Format detection ---
    if ext not in SUPPORTED_TEXT_EXTENSIONS:
        ctx.add_log("format_detection", "error",
                     message=f"Unsupported extension: {ext}")
        logger.error("Unsupported text extension '%s' for %s", ext, file_path.name)
        return None
    ctx.add_log("format_detection", "success", message=f"Detected {ext}")

    # --- Step 2: Text extraction ---
    try:
        if ext == ".docx":
            (full_text, sections), dur = _timed(extract_docx, file_path)
        else:
            (full_text, sections), dur = _timed(extract_pdf, file_path)
        ctx.add_log("text_extraction", "success", duration_ms=dur)
    except PermissionError as exc:
        ctx.add_log("text_extraction", "error",
                     message=f"Protected file: {exc}")
        logger.error("Password-protected file: %s", file_path.name)
        return _build_error_ir(
            student_id, source_files, "protected_file",
            str(exc), ctx.log,
        )
    except Exception as exc:
        ctx.add_log("text_extraction", "error",
                     message=f"Extraction failed: {exc}")
        logger.error("Failed to extract %s: %s", file_path.name, exc)
        return _build_error_ir(
            student_id, source_files, "corrupted_file",
            str(exc), ctx.log,
        )

    # --- Step 3: Metadata extraction ---
    metadata, dur = _timed(extract_text_metadata, full_text, sections)
    ctx.add_log("metadata_extraction", "success", duration_ms=dur)

    # --- Step 3b: Empty check ---
    if metadata.word_count < EMPTY_THRESHOLD:
        ctx.add_log("empty_check", "warning",
                     message=f"word_count={metadata.word_count} < {EMPTY_THRESHOLD}")
        logger.warning("Empty submission: %s (word_count=%d)",
                        file_path.name, metadata.word_count)
        return _build_error_ir(
            student_id, source_files, "empty_submission",
            f"Word count {metadata.word_count} below threshold {EMPTY_THRESHOLD}",
            ctx.log,
        )
    ctx.add_log("empty_check", "success",
                 message=f"word_count={metadata.word_count}")

    # --- Step 4: Gate checks ---
    gate_results: list[GateResult] = []
    if rubric is not None:
        gate_results, dur = _timed(
            run_gate_checks, rubric, full_text, sections,
            metadata.language, source_files,
        )
        ctx.add_log("gate_checks", "success", duration_ms=dur,
                     message=f"{len(gate_results)} gates evaluated")
    else:
        ctx.add_log("gate_checks", "skipped", message="No rubric provided")

    # --- Step 5: Build IR ---
    ir = build_text_ir(
        student_id=student_id,
        source_files=source_files,
        full_text=full_text,
        sections=sections,
        metadata=metadata,
        gate_results=gate_results,
        processing_log=ctx.log,
    )
    return ir


def process_image_file(
    file_path: Path,
    student_id: str,
) -> dict[str, Any] | None:
    """Process a single image file (.jpg/.png) into an IR dict.

    Returns None if the image cannot be processed.
    """
    ctx = ProcessingContext()
    source_files = [f"raw/{file_path.name}"]

    # --- Step 1: Validate and extract metadata ---
    try:
        img_meta, dur = _timed(extract_image_metadata, file_path)
        ctx.add_log("image_validation", "success", duration_ms=dur,
                     message=f"{img_meta.width}x{img_meta.height} {img_meta.color_mode}")
    except Exception as exc:
        ctx.add_log("image_validation", "error",
                     message=f"Image unreadable: {exc}")
        logger.error("Failed to read image %s: %s", file_path.name, exc)
        return _build_error_ir(
            student_id, source_files, "corrupted_file",
            str(exc), ctx.log,
        )

    # --- Step 2: Build image entry with placeholder ---
    resolution = f"{img_meta.width}x{img_meta.height}"
    size_mb = img_meta.file_size_bytes / (1024 * 1024)
    image_entry = {
        "file": f"raw/{file_path.name}",
        "description": "Vision API analysis required",
        "type": "",
        "visual_elements": "",
        "extracted_text": "",
        "design_observations": "",
    }
    ctx.add_log("content_placeholder", "success",
                 message="Placeholder set; Vision API analysis required")

    # --- Step 3: Build IR ---
    ir = build_image_ir(
        student_id=student_id,
        source_files=source_files,
        image_entries=[image_entry],
        total_size_mb=size_mb,
        resolutions=[resolution],
        gate_results=[],
        processing_log=ctx.log,
    )
    return ir


def _build_error_ir(
    student_id: str,
    source_files: list[str],
    error_type: str,
    error_message: str,
    log_entries: list[ProcessingLogEntry],
) -> dict[str, Any]:
    """Build a minimal IR for submissions that failed preprocessing."""
    return {
        "student_id": student_id,
        "submission_type": "text",
        "source_files": source_files,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "word_count": 0,
            "paragraph_count": 0,
            "heading_count": 0,
            "has_references": False,
            "language": "",
            "error_type": error_type,
            "error_message": error_message,
        },
        "content": {
            "full_text": "",
            "sections": [],
        },
        "gate_results": [],
        "processing_log": [
            {
                "step": e.step,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "message": e.message,
            }
            for e in log_entries
        ],
    }


# ---------------------------------------------------------------------------
# Batch orchestration
# ---------------------------------------------------------------------------

def generate_student_id(index: int) -> str:
    """Generate an anonymous student ID: anon-001, anon-002, etc."""
    return f"anon-{index:03d}"


def load_rubric(rubric_path: Path) -> dict[str, Any] | None:
    """Load and return the rubric dict from a YAML file, or None on failure."""
    try:
        with open(rubric_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        rubric = data.get("rubric", data)
        logger.info("Loaded rubric: %s", rubric.get("id", rubric_path.name))
        return rubric
    except Exception as exc:
        logger.error("Failed to load rubric %s: %s", rubric_path, exc)
        return None


def collect_files(input_dir: Path) -> list[Path]:
    """Collect all supported files from the input directory (non-recursive)."""
    files = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return files


def run_batch(
    input_dir: Path,
    output_dir: Path,
    rubric_path: Path | None = None,
) -> None:
    """Main entry point: preprocess all files in input_dir, write IR to output_dir."""
    # --- Setup ---
    output_dir.mkdir(parents=True, exist_ok=True)

    rubric: dict[str, Any] | None = None
    if rubric_path is not None:
        rubric = load_rubric(rubric_path)
        if rubric is None:
            logger.warning("Proceeding without rubric (load failed)")

    # --- Collect files ---
    files = collect_files(input_dir)
    if not files:
        logger.warning("No supported files found in %s", input_dir)
        logger.info("Supported extensions: %s",
                     ", ".join(sorted(SUPPORTED_EXTENSIONS)))
        return

    logger.info("Found %d supported file(s) in %s", len(files), input_dir)

    # --- Process ---
    success_count = 0
    fail_count = 0

    for idx, file_path in enumerate(files, start=1):
        student_id = generate_student_id(idx)
        ext = file_path.suffix.lower()
        logger.info("[%d/%d] Processing %s → %s",
                     idx, len(files), file_path.name, student_id)

        ir: dict[str, Any] | None = None

        if ext in SUPPORTED_TEXT_EXTENSIONS:
            ir = process_text_file(file_path, student_id, rubric)
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            ir = process_image_file(file_path, student_id)

        if ir is not None:
            out_path = output_dir / f"{student_id}.json"
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(ir, f, ensure_ascii=False, indent=2)
                success_count += 1
                logger.info("  → Wrote %s", out_path.name)
            except OSError as exc:
                fail_count += 1
                logger.error("  → Failed to write %s: %s", out_path.name, exc)
        else:
            fail_count += 1
            logger.error("  → Failed to process %s", file_path.name)

    # --- Summary ---
    total = len(files)
    logger.info("=" * 60)
    logger.info("Preprocessing complete")
    logger.info("  Total files:  %d", total)
    logger.info("  Successful:   %d", success_count)
    logger.info("  Failed:       %d", fail_count)
    logger.info("  Output dir:   %s", output_dir.resolve())
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess homework submissions (docx/pdf/jpg/png) into IR JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python preprocess.py ./raw --output ./ir\n"
            "  python preprocess.py ./raw --output ./ir --rubric rubric.yaml\n"
            "  python preprocess.py ./raw --output ./ir --rubric rubric.yaml --verbose\n"
        ),
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing submission files (.docx, .pdf, .jpg, .png)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        dest="output_dir",
        help="Directory to write IR JSON files",
    )
    parser.add_argument(
        "--rubric", "-r",
        type=Path,
        default=None,
        help="Path to rubric YAML file for gate checks",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug-level logging",
    )
    return parser.parse_args(argv)


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(args.verbose)

    input_dir: Path = args.input_dir
    if not input_dir.is_dir():
        logger.error("Input directory does not exist: %s", input_dir)
        raise SystemExit(1)

    rubric_path: Path | None = args.rubric
    if rubric_path is not None and not rubric_path.is_file():
        logger.error("Rubric file does not exist: %s", rubric_path)
        raise SystemExit(1)

    run_batch(
        input_dir=input_dir,
        output_dir=args.output_dir,
        rubric_path=rubric_path,
    )


if __name__ == "__main__":
    main()

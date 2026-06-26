#!/usr/bin/env python3
"""Batch scoring orchestrator for the homework-grader Skill.

Scores preprocessed IR files against a Rubric using the Claude API.
Supports real-time (Messages API) and batch (Batch API) modes with
progress tracking, resume, anti-position-bias randomization, and
per-item error isolation.

Usage:
    python batch_score.py <workspace_dir> --rubric <rubric.yaml> \\
        [--mode real-time|batch] [--workers 5] [--resume]

Examples:
    # Real-time mode, 5 concurrent workers
    python batch_score.py workspace/research-methods-20260315 \\
        --rubric rubric.yaml

    # Batch API mode (50% cost discount)
    python batch_score.py workspace/research-methods-20260315 \\
        --rubric rubric.yaml --mode batch

    # Resume an interrupted batch
    python batch_score.py workspace/research-methods-20260315 \\
        --rubric rubric.yaml --resume
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
import yaml

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-5-20250514"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 4096
DEFAULT_WORKERS = 5
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 2.0
BATCH_POLL_INTERVAL_S = 60

# Pricing per million tokens (Claude Sonnet 4.5, as of 2026-02)
INPUT_PRICE_PER_MTOK = 3.0
OUTPUT_PRICE_PER_MTOK = 15.0

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RubricCriterion:
    """A single scoring dimension from the Rubric."""

    criterion_id: str
    name: str
    weight: float
    scale: list[int]
    description: str
    scoring_guidance: str
    anchors: dict[int, str]
    evidence_type: str


@dataclass(frozen=True)
class RubricThresholds:
    accept: float
    reject: float
    review: list[float]


@dataclass(frozen=True)
class CommentGuidelines:
    tone: str
    language: str
    length_range: list[int]
    required_sections: list[str]
    prohibited_patterns: list[str]


@dataclass(frozen=True)
class Rubric:
    """Parsed and validated Rubric."""

    id: str
    name: str
    version: float
    criteria: list[RubricCriterion]
    thresholds: RubricThresholds
    comment_guidelines: CommentGuidelines


@dataclass
class FailedItem:
    id: str
    error: str
    attempts: int
    last_attempt: str = ""


@dataclass
class Progress:
    """Batch progress checkpoint — single source of truth for state."""

    batch_id: str
    rubric_id: str
    mode: str
    started_at: str
    last_updated: str
    total: int
    completed: int = 0
    failed: int = 0
    pending: int = 0
    completed_ids: list[str] = field(default_factory=list)
    failed_ids: list[FailedItem] = field(default_factory=list)
    pending_ids: list[str] = field(default_factory=list)
    processing_order: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoringResult:
    """Result from scoring a single submission."""

    student_id: str
    score_data: dict[str, Any]
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Rubric loading and validation
# ---------------------------------------------------------------------------


def load_rubric(path: Path) -> Rubric:
    """Load and validate a Rubric YAML file.

    Returns a validated Rubric dataclass. Raises ValueError on
    validation failure.
    """
    if not path.exists():
        raise FileNotFoundError(f"Rubric file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rubric_data = raw.get("rubric")
    if rubric_data is None:
        raise ValueError("YAML must contain a top-level 'rubric' key")

    # Required metadata
    rubric_id = rubric_data.get("id", "")
    rubric_name = rubric_data.get("name", "")
    rubric_version = rubric_data.get("version", 1.0)
    if not rubric_id:
        raise ValueError("Rubric must have a non-empty 'id'")

    # Criteria
    criteria_raw = rubric_data.get("criteria", {})
    if not criteria_raw:
        raise ValueError("Rubric must have at least one criterion")

    criteria: list[RubricCriterion] = []
    weight_sum = 0.0
    for cid, cdata in criteria_raw.items():
        weight = cdata.get("weight", 0.0)
        weight_sum += weight
        scale = cdata.get("scale", [1, 2, 3, 4, 5])
        anchors = {int(k): str(v) for k, v in cdata.get("anchors", {}).items()}

        # Validate anchors cover all scale values
        missing_anchors = [s for s in scale if s not in anchors]
        if missing_anchors:
            raise ValueError(
                f"Criterion '{cid}': missing anchors for scale values {missing_anchors}"
            )

        criteria.append(
            RubricCriterion(
                criterion_id=cid,
                name=cdata.get("name", cid),
                weight=weight,
                scale=scale,
                description=cdata.get("description", ""),
                scoring_guidance=cdata.get("scoring_guidance", ""),
                anchors=anchors,
                evidence_type=cdata.get("evidence_type", "observation"),
            )
        )

    # Validate weights sum
    if abs(weight_sum - 1.0) > 0.001:
        raise ValueError(
            f"Criteria weights must sum to 1.0 (got {weight_sum:.4f})"
        )

    # Thresholds
    thresholds_raw = rubric_data.get("thresholds", {})
    thresholds = RubricThresholds(
        accept=thresholds_raw.get("accept", 3.0),
        reject=thresholds_raw.get("reject", 1.5),
        review=thresholds_raw.get("review", [1.5, 3.0]),
    )
    if thresholds.accept <= thresholds.reject:
        raise ValueError("thresholds.accept must be greater than thresholds.reject")

    # Comment guidelines
    cg_raw = rubric_data.get("comment_guidelines", {})
    comment_guidelines = CommentGuidelines(
        tone=cg_raw.get("tone", "constructive, specific"),
        language=cg_raw.get("language", "zh-CN"),
        length_range=cg_raw.get("length_range", [200, 400]),
        required_sections=cg_raw.get(
            "required_sections", ["strengths", "weaknesses", "suggestions"]
        ),
        prohibited_patterns=cg_raw.get("prohibited_patterns", []),
    )

    logger.info(
        "Rubric loaded: %s (v%.1f) — %d criteria",
        rubric_id,
        rubric_version,
        len(criteria),
    )
    return Rubric(
        id=rubric_id,
        name=rubric_name,
        version=rubric_version,
        criteria=criteria,
        thresholds=thresholds,
        comment_guidelines=comment_guidelines,
    )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SCORING_SYSTEM_PROMPT = """\
You are a meticulous homework evaluator. You score student submissions strictly \
according to the provided Rubric. You never invent criteria beyond what the \
Rubric defines.

### Anti-Bias Directives

1. **Length ≠ Quality** — Do NOT award higher scores because a submission is \
long. A concise, well-argued answer is equal to or better than a verbose one. \
Irrelevant padding should lower the score, not raise it.

2. **Tone ≠ Accuracy** — Do NOT assume confident or academic-sounding language \
is correct. Evaluate claims against evidence. A hedged statement backed by \
data is worth more than an assertive claim without support.

3. **Relevance filter** — For each dimension, ONLY content directly relevant \
to that dimension's criteria contributes to the score. Off-topic elaboration \
earns ZERO credit.

4. **Evidence before score** — For every dimension, you MUST first quote or \
describe evidence from the submission, THEN reason about which anchor it \
matches, THEN assign the score. Reversing this order is forbidden.

5. **Independent dimensions** — Score each dimension on its own merits. A high \
score on one dimension must not inflate another."""

COMMENT_SYSTEM_PROMPT_TEMPLATE = """\
You are a constructive academic mentor writing feedback for a student's \
homework submission. Your comments must be specific, evidence-based, and \
actionable. You write in {language}.

### Rules

1. **Three required sections**: strengths, weaknesses, suggestions.
2. **No vague praise** — Every positive remark must cite a concrete element \
from the work.
3. **No vague criticism** — Every critique must name the exact problem and \
where it occurs.
4. **Actionable suggestions** — Each suggestion must be something the student \
can concretely do in their next assignment.
5. **Length**: {min_length}–{max_length} characters.
6. **Tone**: {tone}
7. **Prohibited patterns**: {prohibited}"""


def build_scoring_user_prompt(
    rubric: Rubric,
    student_id: str,
    submission_content: str,
    submission_type: str,
) -> str:
    """Build the user prompt for scoring a single submission."""
    # Rubric dimensions section
    dimensions_text = ""
    for c in rubric.criteria:
        anchor_rows = "\n".join(
            f"| {score} | {c.anchors[score]} |" for score in sorted(c.anchors, reverse=True)
        )
        dimensions_text += f"""
#### {c.name} (weight: {c.weight})

**Description**: {c.description}
**Scoring Guidance**: {c.scoring_guidance}

| Score | Anchor |
|-------|--------|
{anchor_rows}

**Evidence type**: {c.evidence_type}
"""

    # JSON output format — dimension template
    dim_json_example = json.dumps(
        {
            "criterion_id": "<criterion key>",
            "criterion_name": "<criterion name>",
            "weight": 0.0,
            "score": "<1-5>",
            "evidence": "<quoted text or observation>",
            "reasoning": "<chain-of-thought>",
            "improvement": "<specific suggestion>",
            "confidence": "<0.0-1.0>",
        },
        ensure_ascii=False,
        indent=6,
    )

    return f"""## Rubric

**Rubric ID**: {rubric.id}
**Rubric Name**: {rubric.name}

### Dimensions
{dimensions_text}
---

## Student Submission

**Student ID**: {student_id}
**Submission type**: {submission_type}

{submission_content}

---

## Scoring Instructions

For **each** dimension listed above, produce the following in strict order:

1. **Evidence** — Quote the student's own words (if evidence_type = quote) or \
describe your observation (if evidence_type = observation / metric). If no \
relevant content exists, state "No relevant evidence found."
2. **Reasoning** — Compare the evidence against anchor descriptions. Explain \
which anchor level it matches and why. Note any borderline considerations.
3. **Score** — An integer from 1 to 5.
4. **Improvement** — One specific, actionable suggestion the student could \
follow next time.
5. **Confidence** — A float from 0.0 to 1.0 indicating how confident you are \
in this score.

After scoring all dimensions:

6. **Weighted Total** — Calculate: Σ(weight × score) rounded to 2 decimal places.
7. **Overall Confidence** — The mean of per-dimension confidence values, \
rounded to 2 decimal places.

## Output Format

Respond with **only** the following JSON (no markdown fences, no commentary):

{{
  "student_id": "{student_id}",
  "rubric_id": "{rubric.id}",
  "dimension_scores": [
    {dim_json_example}
  ],
  "weighted_total": <float>,
  "overall_confidence": <float>
}}"""


def build_comment_user_prompt(
    rubric: Rubric,
    score_data: dict[str, Any],
) -> str:
    """Build the user prompt for comment generation."""
    student_id = score_data.get("student_id", "")
    weighted_total = score_data.get("weighted_total", 0.0)

    # Determine grade
    if weighted_total >= rubric.thresholds.accept:
        grade = "accept"
    elif weighted_total < rubric.thresholds.reject:
        grade = "reject"
    else:
        grade = "review"

    # Per-dimension section
    dim_lines = []
    for dim in score_data.get("dimension_scores", []):
        dim_lines.append(
            f"- **{dim.get('criterion_name', '?')}** ({dim.get('weight', 0)}): "
            f"{dim.get('score', 0)}/5\n"
            f"  - Evidence: {dim.get('evidence', '')}\n"
            f"  - Reasoning: {dim.get('reasoning', '')}\n"
            f"  - Improvement: {dim.get('improvement', '')}"
        )
    dim_text = "\n".join(dim_lines)

    return f"""## Scoring Results

**Student ID**: {student_id}
**Weighted Total**: {weighted_total} / 5.0
**Grade**: {grade}

### Per-Dimension Scores

{dim_text}

---

## Task

Based on the scoring results above, write a student-facing comment with these \
sections:

### [Strengths]
Highlight the 1-2 dimensions where the student performed best. Reference \
specific content from their submission (use the evidence field). Explain WHY \
this is good work, not just THAT it is good.

### [Weaknesses]
Address the 1-2 dimensions with the lowest scores. Describe the specific gap \
between what was submitted and what a higher-scoring submission would contain. \
Be direct but respectful.

### [Suggestions]
Provide 2-3 concrete, prioritized improvement actions. Each should be \
achievable in the student's next assignment. Order by impact (most important \
first).

## Output Format

Return **only** the following JSON (no markdown fences):

{{
  "strengths": "<strengths paragraph>",
  "weaknesses": "<weaknesses paragraph>",
  "suggestions": "<suggestions paragraph>",
  "full_text": "<all three sections combined as a single natural-language comment>"
}}"""


def build_comment_system_prompt(rubric: Rubric) -> str:
    """Build the system prompt for comment generation."""
    cg = rubric.comment_guidelines
    return COMMENT_SYSTEM_PROMPT_TEMPLATE.format(
        language=cg.language,
        min_length=cg.length_range[0] if cg.length_range else 200,
        max_length=cg.length_range[1] if len(cg.length_range) > 1 else 400,
        tone=cg.tone,
        prohibited="; ".join(cg.prohibited_patterns) if cg.prohibited_patterns else "None",
    )


# ---------------------------------------------------------------------------
# Response parsing and validation
# ---------------------------------------------------------------------------


def extract_json_from_response(text: str) -> dict[str, Any]:
    """Parse JSON from Claude's response, stripping markdown fences if present."""
    cleaned = text.strip()

    # Remove markdown code fences if present
    if cleaned.startswith("```"):
        # Find end of opening fence line
        first_newline = cleaned.index("\n")
        # Find closing fence
        last_fence = cleaned.rfind("```")
        if last_fence > first_newline:
            cleaned = cleaned[first_newline + 1 : last_fence].strip()

    return json.loads(cleaned)


def validate_scoring_response(
    data: dict[str, Any],
    rubric: Rubric,
) -> list[str]:
    """Validate a scoring response against the Rubric.

    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []

    # Check dimension_scores present
    dims = data.get("dimension_scores")
    if not isinstance(dims, list) or len(dims) == 0:
        errors.append("Missing or empty dimension_scores")
        return errors

    # Check all criteria present
    expected_ids = {c.criterion_id for c in rubric.criteria}
    found_ids = {d.get("criterion_id", "") for d in dims}
    missing = expected_ids - found_ids
    if missing:
        errors.append(f"Missing criteria in response: {missing}")

    # Validate each dimension
    for dim in dims:
        cid = dim.get("criterion_id", "?")
        score = dim.get("score")
        if not isinstance(score, int) or score < 1 or score > 5:
            errors.append(f"Criterion '{cid}': score must be integer 1-5 (got {score})")
        confidence = dim.get("confidence")
        if confidence is not None and (
            not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1
        ):
            errors.append(
                f"Criterion '{cid}': confidence must be 0.0-1.0 (got {confidence})"
            )

    # Validate weighted_total
    wt = data.get("weighted_total")
    if wt is not None:
        # Recompute for verification
        expected_wt = 0.0
        for dim in dims:
            cid = dim.get("criterion_id", "")
            score = dim.get("score", 0)
            # Find weight from rubric
            for rc in rubric.criteria:
                if rc.criterion_id == cid:
                    expected_wt += rc.weight * score
                    break
        expected_wt = round(expected_wt, 2)
        if abs(float(wt) - expected_wt) > 0.1:
            errors.append(
                f"weighted_total mismatch: response={wt}, computed={expected_wt}"
            )
            # Fix it — use computed value
            data["weighted_total"] = expected_wt

    return errors


def validate_comment_response(data: dict[str, Any]) -> list[str]:
    """Validate a comment generation response."""
    errors: list[str] = []
    for key in ("strengths", "weaknesses", "suggestions"):
        val = data.get(key)
        if not val or not isinstance(val, str):
            errors.append(f"Missing or empty '{key}' in comment response")
    return errors


# ---------------------------------------------------------------------------
# IR file loading
# ---------------------------------------------------------------------------


def load_ir_file(path: Path) -> dict[str, Any]:
    """Load and return an IR JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_submission_content(ir: dict[str, Any]) -> str:
    """Extract submission content from an IR record for the scoring prompt."""
    content = ir.get("content", {})

    # Prefer full_text for text submissions
    full_text = content.get("full_text", "")
    if full_text:
        return full_text

    # Fall back to sections
    sections = content.get("sections", [])
    if sections:
        parts = []
        for section in sections:
            heading = section.get("heading", "")
            level = section.get("level", 2)
            text = section.get("text", "")
            prefix = "#" * level
            parts.append(f"{prefix} {heading}\n\n{text}")
        return "\n\n".join(parts)

    # Image descriptions
    images = content.get("images", [])
    if images:
        parts = []
        for i, img in enumerate(images, 1):
            desc = img.get("description", "")
            extracted = img.get("extracted_text", "")
            parts.append(f"[Image {i}]\n{desc}")
            if extracted:
                parts.append(f"Extracted text: {extracted}")
        return "\n\n".join(parts)

    # Transcript
    transcript = content.get("transcript", "")
    if transcript:
        return transcript

    return "(No content extracted)"


# ---------------------------------------------------------------------------
# Score file writing (atomic)
# ---------------------------------------------------------------------------


def save_score_file(scores_dir: Path, student_id: str, data: dict[str, Any]) -> None:
    """Atomically write a score JSON file.

    Writes to a temporary file first, then renames to ensure data
    integrity if the process is interrupted.
    """
    scores_dir.mkdir(parents=True, exist_ok=True)
    target = scores_dir / f"{student_id}.json"

    # Write to temp file in the same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(scores_dir), suffix=".tmp", prefix=f"{student_id}_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Atomic rename (same filesystem)
        os.replace(tmp_path, str(target))
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    logger.debug("Saved score: %s", target)


# ---------------------------------------------------------------------------
# Progress file management
# ---------------------------------------------------------------------------


def load_progress(path: Path) -> Progress | None:
    """Load progress.json if it exists."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # Reconstruct FailedItem objects
    failed_items = []
    for fi in raw.get("failed_ids", []):
        if isinstance(fi, dict):
            failed_items.append(
                FailedItem(
                    id=fi.get("id", ""),
                    error=fi.get("error", ""),
                    attempts=fi.get("attempts", 0),
                    last_attempt=fi.get("last_attempt", ""),
                )
            )

    return Progress(
        batch_id=raw.get("batch_id", ""),
        rubric_id=raw.get("rubric_id", ""),
        mode=raw.get("mode", "real-time"),
        started_at=raw.get("started_at", ""),
        last_updated=raw.get("last_updated", ""),
        total=raw.get("total", 0),
        completed=raw.get("completed", 0),
        failed=raw.get("failed", 0),
        pending=raw.get("pending", 0),
        completed_ids=raw.get("completed_ids", []),
        failed_ids=failed_items,
        pending_ids=raw.get("pending_ids", []),
        processing_order=raw.get("processing_order", []),
        stats=raw.get("stats", {}),
    )


def save_progress(path: Path, progress: Progress) -> None:
    """Save progress.json atomically."""
    progress.last_updated = _now_iso()
    data = asdict(progress)
    # Convert FailedItem dataclasses to dicts (asdict handles this)

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix="progress_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def classify_grade(weighted_total: float, thresholds: RubricThresholds) -> str:
    """Classify a weighted total into accept/review/reject."""
    if weighted_total >= thresholds.accept:
        return "accept"
    if weighted_total < thresholds.reject:
        return "reject"
    return "review"


def compute_percentile(weighted_total: float) -> int:
    """Map 1-5 weighted total to 40-100 percentile scale."""
    return round((weighted_total - 1) / 4 * 60 + 40)


def determine_review_flag(
    overall_confidence: float,
    gate_status: dict[str, Any],
) -> str:
    """Determine the review flag for a scored submission."""
    if overall_confidence < 0.6:
        return "low_confidence"
    if not gate_status.get("all_passed", True):
        has_flag = any(
            not g.get("passed", True) and g.get("on_fail") == "flag"
            for g in gate_status.get("details", [])
        )
        if has_flag:
            return "gate_warning"
    return "none"


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    batch_mode: bool,
) -> float:
    """Estimate USD cost for a set of tokens."""
    discount = 0.5 if batch_mode else 1.0
    cost = (
        input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOK
        + output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOK
    ) * discount
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Real-time scoring engine
# ---------------------------------------------------------------------------


async def score_one_submission(
    client: anthropic.AsyncAnthropic,
    model: str,
    rubric: Rubric,
    ir: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> ScoringResult:
    """Score a single submission: scoring call + comment call.

    Uses the semaphore for concurrency control. Retries with exponential
    backoff on transient failures.
    """
    student_id = ir.get("student_id", "unknown")
    submission_type = ir.get("submission_type", "text")
    content_text = get_submission_content(ir)

    total_input_tokens = 0
    total_output_tokens = 0
    start_ms = time.monotonic_ns() // 1_000_000

    # --- Step 1: Scoring call ---
    scoring_user_prompt = build_scoring_user_prompt(
        rubric, student_id, content_text, submission_type
    )

    score_data = await _call_with_retry(
        client=client,
        model=model,
        system_prompt=SCORING_SYSTEM_PROMPT,
        user_prompt=scoring_user_prompt,
        semaphore=semaphore,
        context=f"scoring {student_id}",
    )
    total_input_tokens += score_data["_input_tokens"]
    total_output_tokens += score_data["_output_tokens"]

    # Parse and validate scoring response
    score_json = extract_json_from_response(score_data["_text"])
    validation_errors = validate_scoring_response(score_json, rubric)
    if validation_errors:
        logger.warning(
            "Validation issues for %s: %s", student_id, "; ".join(validation_errors)
        )

    # --- Step 2: Comment generation call ---
    comment_system = build_comment_system_prompt(rubric)
    comment_user = build_comment_user_prompt(rubric, score_json)

    comment_data = await _call_with_retry(
        client=client,
        model=model,
        system_prompt=comment_system,
        user_prompt=comment_user,
        semaphore=semaphore,
        context=f"comment {student_id}",
    )
    total_input_tokens += comment_data["_input_tokens"]
    total_output_tokens += comment_data["_output_tokens"]

    comment_json = extract_json_from_response(comment_data["_text"])
    comment_errors = validate_comment_response(comment_json)
    if comment_errors:
        logger.warning(
            "Comment validation issues for %s: %s",
            student_id,
            "; ".join(comment_errors),
        )

    # --- Step 3: Assemble final score record ---
    weighted_total = score_json.get("weighted_total", 0.0)
    overall_confidence = score_json.get("overall_confidence", 0.0)

    gate_status = {
        "all_passed": all(
            g.get("passed", True) for g in ir.get("gate_results", [])
        ),
        "details": ir.get("gate_results", []),
    }

    duration_ms = time.monotonic_ns() // 1_000_000 - start_ms

    final_record = {
        "student_id": student_id,
        "rubric_id": rubric.id,
        "scored_at": _now_iso(),
        "gate_status": gate_status,
        "dimension_scores": score_json.get("dimension_scores", []),
        "weighted_total": weighted_total,
        "percentile_score": compute_percentile(weighted_total),
        "grade": classify_grade(weighted_total, rubric.thresholds),
        "overall_confidence": overall_confidence,
        "review_flag": determine_review_flag(overall_confidence, gate_status),
        "comment": {
            "strengths": comment_json.get("strengths", ""),
            "weaknesses": comment_json.get("weaknesses", ""),
            "suggestions": comment_json.get("suggestions", ""),
            "full_text": comment_json.get("full_text", ""),
        },
        "metadata": {
            "model": model,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "duration_ms": duration_ms,
        },
    }

    return ScoringResult(
        student_id=student_id,
        score_data=final_record,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        duration_ms=duration_ms,
    )


async def _call_with_retry(
    client: anthropic.AsyncAnthropic,
    model: str,
    system_prompt: str,
    user_prompt: str,
    semaphore: asyncio.Semaphore,
    context: str,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """Call the Claude Messages API with retry and exponential backoff.

    Returns a dict with _text, _input_tokens, _output_tokens keys.
    """
    backoff = INITIAL_BACKOFF_S
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            async with semaphore:
                response = await client.messages.create(
                    model=model,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    temperature=DEFAULT_TEMPERATURE,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

            # Extract text content
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            return {
                "_text": text_content,
                "_input_tokens": response.usage.input_tokens,
                "_output_tokens": response.usage.output_tokens,
            }

        except anthropic.RateLimitError as exc:
            retry_after = _parse_retry_after(exc)
            logger.warning(
                "[%s] Rate limited (attempt %d). Waiting %.1fs...",
                context,
                attempt,
                retry_after,
            )
            await asyncio.sleep(retry_after)
            last_error = exc
            # Do not count rate limits against max_retries
            continue

        except (anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
            logger.warning(
                "[%s] Transient error (attempt %d/%d): %s. Retrying in %.1fs...",
                context,
                attempt,
                max_retries,
                exc,
                backoff,
            )
            last_error = exc
            await asyncio.sleep(backoff)
            backoff *= 2

        except anthropic.APIStatusError as exc:
            if exc.status_code == 529:
                # Overloaded — treat like rate limit
                logger.warning(
                    "[%s] API overloaded (attempt %d). Waiting %.1fs...",
                    context,
                    attempt,
                    backoff,
                )
                last_error = exc
                await asyncio.sleep(backoff)
                backoff *= 2
            else:
                raise

    raise RuntimeError(
        f"[{context}] All {max_retries} retries exhausted. Last error: {last_error}"
    )


def _parse_retry_after(exc: anthropic.RateLimitError) -> float:
    """Extract Retry-After seconds from a rate limit error."""
    # Try to get the retry-after header from the response
    try:
        if hasattr(exc, "response") and exc.response is not None:
            retry_after = exc.response.headers.get("retry-after")
            if retry_after:
                return float(retry_after)
    except (ValueError, AttributeError):
        pass
    return 30.0  # Default wait


async def run_realtime_mode(
    workspace: Path,
    rubric: Rubric,
    model: str,
    workers: int,
    resume: bool,
) -> None:
    """Execute real-time scoring mode."""
    ir_dir = workspace / "ir"
    scores_dir = workspace / "scores"
    progress_path = workspace / "progress.json"

    # Discover IR files
    ir_files = sorted(ir_dir.glob("*.json"))
    all_ids = [p.stem for p in ir_files]
    id_to_path = {p.stem: p for p in ir_files}

    if not all_ids:
        logger.error("No IR files found in %s", ir_dir)
        return

    logger.info("Found %d IR files in %s", len(all_ids), ir_dir)

    # Resume or initialize progress
    progress: Progress
    if resume and progress_path.exists():
        loaded = load_progress(progress_path)
        if loaded is not None:
            progress = loaded
            logger.info(
                "Resuming batch: %d completed, %d failed, %d pending",
                progress.completed,
                progress.failed,
                progress.pending,
            )
        else:
            resume = False

    if not resume:
        # Randomize order (anti-position-bias)
        processing_order = list(all_ids)
        random.shuffle(processing_order)

        progress = Progress(
            batch_id=workspace.name,
            rubric_id=rubric.id,
            mode="real-time",
            started_at=_now_iso(),
            last_updated=_now_iso(),
            total=len(all_ids),
            pending=len(all_ids),
            pending_ids=list(processing_order),
            processing_order=list(processing_order),
        )

    # Determine which IDs to process
    completed_set = set(progress.completed_ids)
    failed_map = {fi.id: fi for fi in progress.failed_ids}

    to_process: list[str] = []
    for sid in progress.processing_order:
        if sid in completed_set:
            continue
        if sid in failed_map and failed_map[sid].attempts >= MAX_RETRIES:
            continue
        if sid in id_to_path:
            to_process.append(sid)

    logger.info("Submissions to process: %d", len(to_process))

    if not to_process:
        logger.info("Nothing to process — batch complete")
        _print_summary(progress, batch_mode=False)
        return

    # Initialize API client
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(workers)

    # Accumulate stats for summary
    total_input_tokens = 0
    total_output_tokens = 0

    # Process each submission
    for sid in to_process:
        ir_path = id_to_path.get(sid)
        if ir_path is None:
            logger.warning("IR file not found for %s — skipping", sid)
            continue

        try:
            ir = load_ir_file(ir_path)

            # Check if gate failed with on_fail=fail
            gate_failed = False
            for gate in ir.get("gate_results", []):
                if not gate.get("passed", True) and gate.get("on_fail") == "fail":
                    gate_failed = True
                    break

            if gate_failed:
                logger.info("Skipping %s — gate FAILED (on_fail=fail)", sid)
                _record_failure(
                    progress, sid, "Gate check failed (on_fail=fail)", 0
                )
                save_progress(progress_path, progress)
                continue

            result = await score_one_submission(
                client=client,
                model=model,
                rubric=rubric,
                ir=ir,
                semaphore=semaphore,
            )

            # Save score file atomically
            save_score_file(scores_dir, sid, result.score_data)

            # Update progress
            progress.completed_ids.append(sid)
            if sid in progress.pending_ids:
                progress.pending_ids.remove(sid)
            progress.completed = len(progress.completed_ids)
            progress.pending = len(progress.pending_ids)

            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens

            # Update running stats
            progress.stats = {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cost_usd": estimate_cost(
                    total_input_tokens, total_output_tokens, batch_mode=False
                ),
            }

            save_progress(progress_path, progress)

            logger.info(
                "[%d/%d] Scored %s — weighted_total=%.2f (%dms)",
                progress.completed,
                progress.total,
                sid,
                result.score_data.get("weighted_total", 0),
                result.duration_ms,
            )

        except Exception as exc:
            logger.error("Failed to score %s: %s", sid, exc, exc_info=True)
            attempt_count = failed_map.get(sid, FailedItem(sid, "", 0)).attempts + 1
            _record_failure(progress, sid, str(exc), attempt_count)
            save_progress(progress_path, progress)

    # Final save
    save_progress(progress_path, progress)
    _print_summary(progress, batch_mode=False)


def _record_failure(
    progress: Progress,
    student_id: str,
    error: str,
    attempts: int,
) -> None:
    """Record a failure in the progress tracker."""
    # Remove from pending if present
    if student_id in progress.pending_ids:
        progress.pending_ids.remove(student_id)

    # Update or add failed item
    existing = None
    for fi in progress.failed_ids:
        if fi.id == student_id:
            existing = fi
            break

    if existing is not None:
        existing.error = error
        existing.attempts = attempts
        existing.last_attempt = _now_iso()
    else:
        progress.failed_ids.append(
            FailedItem(
                id=student_id,
                error=error,
                attempts=attempts,
                last_attempt=_now_iso(),
            )
        )

    progress.failed = len(progress.failed_ids)
    progress.pending = len(progress.pending_ids)


# ---------------------------------------------------------------------------
# Batch API mode
# ---------------------------------------------------------------------------


async def run_batch_mode(
    workspace: Path,
    rubric: Rubric,
    model: str,
    resume: bool,
) -> None:
    """Execute Batch API scoring mode."""
    ir_dir = workspace / "ir"
    scores_dir = workspace / "scores"
    progress_path = workspace / "progress.json"

    # Discover IR files
    ir_files = sorted(ir_dir.glob("*.json"))
    all_ids = [p.stem for p in ir_files]
    id_to_path = {p.stem: p for p in ir_files}

    if not all_ids:
        logger.error("No IR files found in %s", ir_dir)
        return

    logger.info("Found %d IR files in %s", len(all_ids), ir_dir)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Check for existing batch to resume
    progress: Progress | None = None
    if resume and progress_path.exists():
        progress = load_progress(progress_path)

    # If resuming with an existing batch_id that started Batch API
    if progress is not None and progress.mode == "batch" and progress.stats.get("api_batch_id"):
        api_batch_id = progress.stats["api_batch_id"]
        logger.info("Resuming Batch API poll for batch %s", api_batch_id)
    else:
        # Build new batch
        processing_order = list(all_ids)
        random.shuffle(processing_order)

        # Filter out gate-failed submissions
        to_process: list[str] = []
        gate_failed_ids: list[str] = []
        for sid in processing_order:
            ir_path = id_to_path.get(sid)
            if ir_path is None:
                continue
            ir = load_ir_file(ir_path)
            gate_failed = any(
                not g.get("passed", True) and g.get("on_fail") == "fail"
                for g in ir.get("gate_results", [])
            )
            if gate_failed:
                gate_failed_ids.append(sid)
                logger.info("Skipping %s — gate FAILED (on_fail=fail)", sid)
            else:
                to_process.append(sid)

        if not to_process:
            logger.info("No submissions to process after gate filtering")
            return

        # Build JSONL requests
        jsonl_lines: list[str] = []
        for sid in to_process:
            ir_path = id_to_path[sid]
            ir = load_ir_file(ir_path)
            submission_type = ir.get("submission_type", "text")
            content_text = get_submission_content(ir)

            user_prompt = build_scoring_user_prompt(
                rubric, sid, content_text, submission_type
            )

            request_body = {
                "custom_id": sid,
                "params": {
                    "model": model,
                    "max_tokens": DEFAULT_MAX_TOKENS,
                    "temperature": DEFAULT_TEMPERATURE,
                    "system": SCORING_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            }
            jsonl_lines.append(json.dumps(request_body, ensure_ascii=False))

        logger.info("Built %d batch requests", len(jsonl_lines))

        # Create batch via API
        jsonl_content = "\n".join(jsonl_lines)

        batch = client.messages.batches.create(
            requests=[json.loads(line) for line in jsonl_lines]
        )
        api_batch_id = batch.id
        logger.info("Batch created: %s", api_batch_id)

        # Initialize progress
        progress = Progress(
            batch_id=workspace.name,
            rubric_id=rubric.id,
            mode="batch",
            started_at=_now_iso(),
            last_updated=_now_iso(),
            total=len(all_ids),
            pending=len(to_process),
            pending_ids=to_process,
            processing_order=processing_order,
            stats={"api_batch_id": api_batch_id},
        )

        # Record gate-failed items
        for sid in gate_failed_ids:
            _record_failure(progress, sid, "Gate check failed (on_fail=fail)", 0)

        save_progress(progress_path, progress)

    # Poll for batch completion
    assert progress is not None
    api_batch_id = progress.stats.get("api_batch_id", "")
    logger.info("Polling batch %s (interval: %ds)...", api_batch_id, BATCH_POLL_INTERVAL_S)

    while True:
        batch_status = client.messages.batches.retrieve(api_batch_id)
        status = batch_status.processing_status

        logger.info(
            "Batch %s status: %s (counts: %s)",
            api_batch_id,
            status,
            {
                "processing": batch_status.request_counts.processing,
                "succeeded": batch_status.request_counts.succeeded,
                "errored": batch_status.request_counts.errored,
            },
        )

        if status == "ended":
            break

        await asyncio.sleep(BATCH_POLL_INTERVAL_S)

    # Download and process results
    logger.info("Batch completed. Processing results...")

    async_client = anthropic.AsyncAnthropic(api_key=api_key)
    comment_semaphore = asyncio.Semaphore(5)

    scored_count = 0
    failed_count = 0

    for result in client.messages.batches.results(api_batch_id):
        custom_id = result.custom_id

        if result.result.type == "succeeded":
            try:
                # Extract text from the message response
                message = result.result.message
                text_content = ""
                for block in message.content:
                    if block.type == "text":
                        text_content += block.text

                score_json = extract_json_from_response(text_content)
                validation_errors = validate_scoring_response(score_json, rubric)
                if validation_errors:
                    logger.warning(
                        "Validation issues for %s: %s",
                        custom_id,
                        "; ".join(validation_errors),
                    )

                # Generate comment via real-time call
                comment_system = build_comment_system_prompt(rubric)
                comment_user = build_comment_user_prompt(rubric, score_json)

                comment_result = await _call_with_retry(
                    client=async_client,
                    model=model,
                    system_prompt=comment_system,
                    user_prompt=comment_user,
                    semaphore=comment_semaphore,
                    context=f"comment {custom_id}",
                )
                comment_json = extract_json_from_response(comment_result["_text"])

                # Load IR for gate_results
                ir_path = id_to_path.get(custom_id)
                ir = load_ir_file(ir_path) if ir_path else {}
                gate_status = {
                    "all_passed": all(
                        g.get("passed", True) for g in ir.get("gate_results", [])
                    ),
                    "details": ir.get("gate_results", []),
                }

                weighted_total = score_json.get("weighted_total", 0.0)
                overall_confidence = score_json.get("overall_confidence", 0.0)

                final_record = {
                    "student_id": custom_id,
                    "rubric_id": rubric.id,
                    "scored_at": _now_iso(),
                    "gate_status": gate_status,
                    "dimension_scores": score_json.get("dimension_scores", []),
                    "weighted_total": weighted_total,
                    "percentile_score": compute_percentile(weighted_total),
                    "grade": classify_grade(weighted_total, rubric.thresholds),
                    "overall_confidence": overall_confidence,
                    "review_flag": determine_review_flag(
                        overall_confidence, gate_status
                    ),
                    "comment": {
                        "strengths": comment_json.get("strengths", ""),
                        "weaknesses": comment_json.get("weaknesses", ""),
                        "suggestions": comment_json.get("suggestions", ""),
                        "full_text": comment_json.get("full_text", ""),
                    },
                    "metadata": {
                        "model": model,
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                        "duration_ms": 0,
                    },
                }

                save_score_file(scores_dir, custom_id, final_record)
                progress.completed_ids.append(custom_id)
                if custom_id in progress.pending_ids:
                    progress.pending_ids.remove(custom_id)
                scored_count += 1

            except Exception as exc:
                logger.error("Failed to process result for %s: %s", custom_id, exc)
                _record_failure(progress, custom_id, str(exc), 1)
                failed_count += 1
        else:
            # Error result from Batch API
            error_msg = str(getattr(result.result, "error", "Unknown batch error"))
            logger.error("Batch API error for %s: %s", custom_id, error_msg)
            _record_failure(progress, custom_id, error_msg, 1)
            failed_count += 1

    progress.completed = len(progress.completed_ids)
    progress.pending = len(progress.pending_ids)
    save_progress(progress_path, progress)

    logger.info("Batch results processed: %d scored, %d failed", scored_count, failed_count)
    _print_summary(progress, batch_mode=True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _print_summary(progress: Progress, batch_mode: bool) -> None:
    """Log a batch completion summary."""
    logger.info("=" * 60)
    logger.info("BATCH SCORING SUMMARY")
    logger.info("=" * 60)
    logger.info("Batch ID:   %s", progress.batch_id)
    logger.info("Rubric:     %s", progress.rubric_id)
    logger.info("Mode:       %s", progress.mode)
    logger.info("Total:      %d", progress.total)
    logger.info("Completed:  %d", progress.completed)
    logger.info("Failed:     %d", progress.failed)
    logger.info("Pending:    %d", progress.pending)

    # Average score
    if progress.completed > 0:
        scores_dir_guess = None
        # We cannot easily re-read scores here, so use stats if available
        cost = progress.stats.get("total_cost_usd", 0)
        logger.info("Est. cost:  $%.4f", cost)

    if progress.failed_ids:
        logger.info("-" * 60)
        logger.info("FAILED SUBMISSIONS:")
        for fi in progress.failed_ids:
            if isinstance(fi, FailedItem):
                logger.info(
                    "  %s — %s (attempts: %d)", fi.id, fi.error, fi.attempts
                )
            elif isinstance(fi, dict):
                logger.info(
                    "  %s — %s (attempts: %d)",
                    fi.get("id", "?"),
                    fi.get("error", "?"),
                    fi.get("attempts", 0),
                )

    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch-score preprocessed homework submissions against a Rubric.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # Real-time scoring with default 5 workers
  python batch_score.py workspace/batch-001 --rubric my-rubric.yaml

  # Batch API mode (50%% cost discount, results in ≤24h)
  python batch_score.py workspace/batch-001 --rubric my-rubric.yaml --mode batch

  # Resume an interrupted run
  python batch_score.py workspace/batch-001 --rubric my-rubric.yaml --resume
""",
    )
    parser.add_argument(
        "workspace",
        type=Path,
        help="Workspace directory (must contain ir/ subdirectory with IR JSON files)",
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        required=True,
        help="Path to the Rubric YAML file",
    )
    parser.add_argument(
        "--mode",
        choices=["real-time", "batch"],
        default="real-time",
        help="Processing mode: real-time (Messages API) or batch (Batch API). "
        "Default: real-time",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers for real-time mode. Default: {DEFAULT_WORKERS}",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted batch from progress.json checkpoint",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the scoring model (default: env SCORING_MODEL or "
        f"{DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=BATCH_POLL_INTERVAL_S,
        help=f"Batch API poll interval in seconds. Default: {BATCH_POLL_INTERVAL_S}",
    )
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> None:
    """Async entry point."""
    workspace: Path = args.workspace
    rubric_path: Path = args.rubric
    mode: str = args.mode
    workers: int = args.workers

    # Resolve model
    model = args.model or os.environ.get("SCORING_MODEL", DEFAULT_MODEL)

    # Validate workspace
    ir_dir = workspace / "ir"
    if not ir_dir.is_dir():
        logger.error("IR directory not found: %s", ir_dir)
        sys.exit(1)

    # Ensure output directories exist
    (workspace / "scores").mkdir(parents=True, exist_ok=True)
    (workspace / "logs").mkdir(parents=True, exist_ok=True)

    # Add file handler for logging
    log_file = workspace / "logs" / "scoring.log"
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logging.getLogger().addHandler(file_handler)

    # Load and validate rubric
    try:
        rubric = load_rubric(rubric_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Rubric error: %s", exc)
        sys.exit(1)

    logger.info(
        "Starting batch scoring — mode=%s, model=%s, workers=%d",
        mode,
        model,
        workers,
    )

    # Update poll interval if provided
    global BATCH_POLL_INTERVAL_S
    BATCH_POLL_INTERVAL_S = args.poll_interval

    if mode == "real-time":
        await run_realtime_mode(
            workspace=workspace,
            rubric=rubric,
            model=model,
            workers=workers,
            resume=args.resume,
        )
    else:
        await run_batch_mode(
            workspace=workspace,
            rubric=rubric,
            model=model,
            resume=args.resume,
        )


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()

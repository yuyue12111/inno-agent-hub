#!/usr/bin/env python3
"""Calibration analysis: compare AI scores against teacher-scored samples.

Computes Cohen's κ (weighted), Spearman ρ per dimension, and MAD.
Generates a calibration report in Markdown format.

Usage:
    python calibrate.py <workspace_dir> --rubric <rubric.yaml>
                                        --samples <samples_dir>
                                        [--output <report.md>]

Calibration samples directory should contain JSON files with teacher scores
in the same schema as scoring output (student_id, dimension_scores, weighted_total).
File names should match: {student_id}-teacher.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy import stats as scipy_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

KAPPA_THRESHOLD = 0.70
RHO_THRESHOLD = 0.80
MAD_THRESHOLD = 0.50


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DimensionScore:
    criterion_id: str
    criterion_name: str
    score: int
    weight: float


@dataclass(frozen=True)
class SampleScores:
    student_id: str
    dimensions: tuple[DimensionScore, ...]
    weighted_total: float


@dataclass(frozen=True)
class DimensionAnalysis:
    criterion_name: str
    teacher_mean: float
    ai_mean: float
    spearman_rho: float
    rho_pvalue: float
    passed: bool
    bias_direction: str


@dataclass(frozen=True)
class SampleComparison:
    student_id: str
    teacher_total: float
    ai_total: float
    difference: float
    largest_deviation_dim: str
    deviation_detail: str


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_sample_scores(path: Path) -> SampleScores | None:
    """Load a score JSON file into SampleScores."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        dims = tuple(
            DimensionScore(
                criterion_id=d.get("criterion_id", ""),
                criterion_name=d.get("criterion_name", ""),
                score=int(d.get("score", 0)),
                weight=float(d.get("weight", 0)),
            )
            for d in data.get("dimension_scores", [])
        )
        return SampleScores(
            student_id=data.get("student_id", path.stem),
            dimensions=dims,
            weighted_total=float(data.get("weighted_total", 0)),
        )
    except (json.JSONDecodeError, OSError, KeyError, ValueError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None


def find_paired_samples(
    samples_dir: Path,
    scores_dir: Path,
) -> list[tuple[SampleScores, SampleScores]]:
    """Find paired teacher and AI scores for the same students."""
    pairs = []
    for teacher_path in sorted(samples_dir.glob("*-teacher.json")):
        student_id = teacher_path.stem.replace("-teacher", "")
        ai_path = scores_dir / f"{student_id}.json"
        if not ai_path.exists():
            logger.warning(
                "No AI score found for calibration sample %s", student_id
            )
            continue
        teacher = load_sample_scores(teacher_path)
        ai = load_sample_scores(ai_path)
        if teacher and ai:
            pairs.append((teacher, ai))
    logger.info("Found %d paired calibration samples", len(pairs))
    return pairs


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_weighted_kappa(
    teacher_scores: list[int],
    ai_scores: list[int],
    min_score: int = 1,
    max_score: int = 5,
) -> float:
    """Compute quadratic-weighted Cohen's kappa."""
    n_categories = max_score - min_score + 1
    # Build confusion matrix
    confusion = np.zeros((n_categories, n_categories), dtype=float)
    for t, a in zip(teacher_scores, ai_scores):
        confusion[t - min_score][a - min_score] += 1

    n = len(teacher_scores)
    if n == 0:
        return 0.0

    # Normalize
    confusion /= n

    # Marginals
    row_marginals = confusion.sum(axis=1)
    col_marginals = confusion.sum(axis=0)

    # Expected matrix
    expected = np.outer(row_marginals, col_marginals)

    # Quadratic weight matrix
    weights = np.zeros((n_categories, n_categories), dtype=float)
    for i in range(n_categories):
        for j in range(n_categories):
            weights[i][j] = (i - j) ** 2 / (n_categories - 1) ** 2

    # Kappa
    observed = (weights * confusion).sum()
    expected_val = (weights * expected).sum()

    if expected_val == 0:
        return 1.0 if observed == 0 else 0.0

    return 1.0 - observed / expected_val


def compute_spearman(
    teacher_scores: list[int],
    ai_scores: list[int],
) -> tuple[float, float]:
    """Compute Spearman rank correlation."""
    if len(teacher_scores) < 3:
        return 0.0, 1.0
    try:
        result = scipy_stats.spearmanr(teacher_scores, ai_scores)
        rho = float(result.statistic) if not np.isnan(result.statistic) else 0.0
        pvalue = float(result.pvalue) if not np.isnan(result.pvalue) else 1.0
        return rho, pvalue
    except Exception:
        return 0.0, 1.0


def compute_mad(teacher_scores: list[float], ai_scores: list[float]) -> float:
    """Compute Mean Absolute Difference."""
    if not teacher_scores:
        return 0.0
    diffs = [abs(t - a) for t, a in zip(teacher_scores, ai_scores)]
    return sum(diffs) / len(diffs)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_dimensions(
    pairs: list[tuple[SampleScores, SampleScores]],
) -> list[DimensionAnalysis]:
    """Analyze per-dimension agreement."""
    # Collect scores by dimension
    dim_teacher: dict[str, list[int]] = {}
    dim_ai: dict[str, list[int]] = {}
    dim_names: dict[str, str] = {}

    for teacher, ai in pairs:
        teacher_dims = {d.criterion_id: d for d in teacher.dimensions}
        ai_dims = {d.criterion_id: d for d in ai.dimensions}
        for cid in teacher_dims:
            if cid in ai_dims:
                dim_names[cid] = teacher_dims[cid].criterion_name
                dim_teacher.setdefault(cid, []).append(teacher_dims[cid].score)
                dim_ai.setdefault(cid, []).append(ai_dims[cid].score)

    analyses = []
    for cid in dim_teacher:
        t_scores = dim_teacher[cid]
        a_scores = dim_ai[cid]
        t_mean = sum(t_scores) / len(t_scores)
        a_mean = sum(a_scores) / len(a_scores)
        rho, pvalue = compute_spearman(t_scores, a_scores)
        passed = rho >= RHO_THRESHOLD

        if a_mean > t_mean + 0.2:
            direction = "AI higher"
        elif a_mean < t_mean - 0.2:
            direction = "AI lower"
        else:
            direction = "Aligned"

        analyses.append(DimensionAnalysis(
            criterion_name=dim_names.get(cid, cid),
            teacher_mean=round(t_mean, 2),
            ai_mean=round(a_mean, 2),
            spearman_rho=round(rho, 3),
            rho_pvalue=round(pvalue, 4),
            passed=passed,
            bias_direction=direction,
        ))

    return analyses


def analyze_samples(
    pairs: list[tuple[SampleScores, SampleScores]],
) -> list[SampleComparison]:
    """Analyze per-sample agreement."""
    comparisons = []
    for teacher, ai in pairs:
        diff = round(ai.weighted_total - teacher.weighted_total, 2)

        # Find largest per-dimension deviation
        teacher_dims = {d.criterion_id: d for d in teacher.dimensions}
        ai_dims = {d.criterion_id: d for d in ai.dimensions}
        max_dev = 0
        max_dim = ""
        max_detail = ""
        for cid, td in teacher_dims.items():
            if cid in ai_dims:
                dev = abs(ai_dims[cid].score - td.score)
                if dev > max_dev:
                    max_dev = dev
                    max_dim = td.criterion_name
                    max_detail = f"{td.score}→{ai_dims[cid].score}"

        comparisons.append(SampleComparison(
            student_id=teacher.student_id,
            teacher_total=round(teacher.weighted_total, 2),
            ai_total=round(ai.weighted_total, 2),
            difference=diff,
            largest_deviation_dim=max_dim,
            deviation_detail=max_detail,
        ))

    return comparisons


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    rubric_id: str,
    rubric_version: float,
    model_id: str,
    kappa: float,
    mad: float,
    dim_analyses: list[DimensionAnalysis],
    sample_comparisons: list[SampleComparison],
) -> str:
    """Generate a Markdown calibration report."""
    kappa_pass = kappa >= KAPPA_THRESHOLD
    mad_pass = mad <= MAD_THRESHOLD
    all_dim_pass = all(d.passed for d in dim_analyses)
    overall_pass = kappa_pass and mad_pass and all_dim_pass

    lines = [
        "# Calibration Report",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Rubric | {rubric_id} |",
        f"| Rubric Version | {rubric_version} |",
        f"| Calibration Date | {datetime.now(timezone.utc).strftime('%Y-%m-%d')} |",
        f"| Calibration Samples | {len(sample_comparisons)} |",
        f"| Model Used | {model_id} |",
        f"| **Overall Result** | **{'PASS' if overall_pass else 'FAIL'}** |",
        "",
        "## Agreement Metrics",
        "",
        "| Metric | Value | Threshold | Result |",
        "|--------|-------|-----------|--------|",
        f"| Weighted Cohen's κ | {kappa:.3f} | ≥ {KAPPA_THRESHOLD} | {'✅' if kappa_pass else '❌'} |",
        f"| Mean Absolute Difference (MAD) | {mad:.3f} | ≤ {MAD_THRESHOLD} | {'✅' if mad_pass else '❌'} |",
        "",
        "## Per-Dimension Analysis",
        "",
        "| Dimension | Teacher Mean | AI Mean | Spearman ρ | Threshold | Result | Bias Direction |",
        "|-----------|-------------|---------|------------|-----------|--------|----------------|",
    ]

    for d in dim_analyses:
        lines.append(
            f"| {d.criterion_name} | {d.teacher_mean} | {d.ai_mean} "
            f"| {d.spearman_rho} | ≥ {RHO_THRESHOLD} "
            f"| {'✅' if d.passed else '❌'} | {d.bias_direction} |"
        )

    lines.extend([
        "",
        "## Sample-Level Comparison",
        "",
        "| Sample | Teacher Total | AI Total | Difference | Largest Deviation |",
        "|--------|--------------|----------|------------|-------------------|",
    ])

    for s in sample_comparisons:
        lines.append(
            f"| {s.student_id} | {s.teacher_total} | {s.ai_total} "
            f"| {s.difference:+.2f} | {s.largest_deviation_dim} ({s.deviation_detail}) |"
        )

    lines.extend(["", "## Recommendations", ""])

    if overall_pass:
        lines.extend([
            "- Calibration successful. AI scoring is aligned with teacher standards.",
            "- Proceed to batch scoring with confidence.",
            "- Re-calibrate if the Rubric is modified.",
        ])
    else:
        if not kappa_pass:
            lines.append(
                f"- **Overall κ**: {kappa:.3f} (below {KAPPA_THRESHOLD}). "
                "Review all anchor descriptions for clarity and distinctiveness."
            )
        if not mad_pass:
            direction = "over" if mad > 0 else "under"
            lines.append(
                f"- **MAD**: {mad:.3f} (above {MAD_THRESHOLD}). "
                f"Systematic {direction}-scoring detected. "
                "Adjust anchor language to correct directional bias."
            )
        for d in dim_analyses:
            if not d.passed:
                lines.append(
                    f"- **{d.criterion_name}**: ρ = {d.spearman_rho} "
                    f"(below {RHO_THRESHOLD}). "
                    "Differentiate adjacent anchor descriptions more clearly."
                )

    lines.extend([
        "",
        "---",
        "",
        "*Generated by homework-grader calibration protocol*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run calibration analysis: AI scores vs teacher scores.",
    )
    parser.add_argument("workspace", type=Path, help="Workspace directory")
    parser.add_argument("--rubric", type=Path, required=True, help="Rubric YAML file")
    parser.add_argument(
        "--samples",
        type=Path,
        default=None,
        help="Calibration samples directory (default: workspace/calibration-samples/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output report path (default: workspace/reports/calibration-report.md)",
    )
    args = parser.parse_args()

    workspace: Path = args.workspace
    scores_dir = workspace / "scores"
    samples_dir = args.samples or (workspace / "calibration-samples")
    output_path = args.output or (workspace / "reports" / "calibration-report.md")

    # Load Rubric metadata
    rubric_id = "unknown"
    rubric_version = 1.0
    try:
        with open(args.rubric, encoding="utf-8") as f:
            rubric_data = yaml.safe_load(f)
        rubric_obj = rubric_data.get("rubric", rubric_data)
        rubric_id = rubric_obj.get("id", "unknown")
        rubric_version = rubric_obj.get("version", 1.0)
    except Exception as exc:
        logger.warning("Could not load Rubric metadata: %s", exc)

    # Find paired samples
    pairs = find_paired_samples(samples_dir, scores_dir)
    if len(pairs) < 3:
        logger.error(
            "Need at least 3 paired samples for calibration, found %d", len(pairs)
        )
        sys.exit(1)

    # Compute overall metrics
    all_teacher = []
    all_ai = []
    teacher_totals = []
    ai_totals = []
    for teacher, ai in pairs:
        teacher_totals.append(teacher.weighted_total)
        ai_totals.append(ai.weighted_total)
        teacher_dims = {d.criterion_id: d for d in teacher.dimensions}
        ai_dims = {d.criterion_id: d for d in ai.dimensions}
        for cid in teacher_dims:
            if cid in ai_dims:
                all_teacher.append(teacher_dims[cid].score)
                all_ai.append(ai_dims[cid].score)

    kappa = compute_weighted_kappa(all_teacher, all_ai)
    mad = compute_mad(teacher_totals, ai_totals)

    # Dimension analysis
    dim_analyses = analyze_dimensions(pairs)

    # Sample comparisons
    sample_comparisons = analyze_samples(pairs)

    # Generate report
    import os
    model_id = os.environ.get("SCORING_MODEL", "claude-sonnet-4-5-20250514")
    report = generate_report(
        rubric_id=rubric_id,
        rubric_version=rubric_version,
        model_id=model_id,
        kappa=kappa,
        mad=mad,
        dim_analyses=dim_analyses,
        sample_comparisons=sample_comparisons,
    )

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Print summary
    overall_pass = (
        kappa >= KAPPA_THRESHOLD
        and mad <= MAD_THRESHOLD
        and all(d.passed for d in dim_analyses)
    )
    status = "PASS" if overall_pass else "FAIL"
    logger.info(
        "Calibration %s — κ=%.3f, MAD=%.3f, %d/%d dimensions passed",
        status,
        kappa,
        mad,
        sum(1 for d in dim_analyses if d.passed),
        len(dim_analyses),
    )
    logger.info("Report saved to %s", output_path)

    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Score distribution analysis and bias detection.

Analyzes a batch of scoring results for:
- Distribution statistics (mean, SD, skewness, kurtosis)
- Score concentration anomalies
- Length bias (word count vs score correlation)
- Position bias (processing order vs score correlation)
- Dimension coupling (inter-dimension correlation)

Usage:
    python stats.py <workspace_dir> [--output <report.md>]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats as scipy_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

LENGTH_BIAS_THRESHOLD = 0.3
POSITION_BIAS_THRESHOLD = 0.2
DIMENSION_COUPLING_THRESHOLD = 0.9
SKEWNESS_THRESHOLD = 1.0
CONCENTRATION_THRESHOLD = 0.4
SD_LOW_THRESHOLD = 0.3
SD_HIGH_THRESHOLD = 2.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoreRecord:
    student_id: str
    weighted_total: float
    percentile: int
    confidence: float
    word_count: int
    dimension_scores: dict[str, int]  # criterion_id → score


def load_scores(workspace: Path) -> list[ScoreRecord]:
    """Load score JSONs from workspace/scores/."""
    scores_dir = workspace / "scores"
    records = []
    if not scores_dir.exists():
        logger.error("Scores directory not found: %s", scores_dir)
        return records

    for path in sorted(scores_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            dim_scores = {
                d.get("criterion_id", f"dim_{i}"): int(d.get("score", 0))
                for i, d in enumerate(data.get("dimension_scores", []))
            }

            # Try to get word count from IR file
            word_count = 0
            student_id = data.get("student_id", path.stem)
            ir_path = workspace / "ir" / f"{student_id}.json"
            if ir_path.exists():
                with open(ir_path, encoding="utf-8") as f:
                    ir_data = json.load(f)
                word_count = ir_data.get("metadata", {}).get("word_count", 0)

            percentile = data.get("percentile_score", 0)
            if percentile == 0:
                wt = data.get("weighted_total", 0)
                percentile = round((wt - 1) / 4 * 60 + 40) if wt > 0 else 40

            records.append(ScoreRecord(
                student_id=student_id,
                weighted_total=float(data.get("weighted_total", 0)),
                percentile=percentile,
                confidence=float(data.get("overall_confidence", 0)),
                word_count=word_count,
                dimension_scores=dim_scores,
            ))
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Skipping %s: %s", path.name, exc)

    logger.info("Loaded %d score records", len(records))
    return records


def load_processing_order(workspace: Path) -> list[str]:
    """Load processing order from progress.json."""
    progress_path = workspace / "progress.json"
    if progress_path.exists():
        try:
            with open(progress_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("processing_order", [])
        except (json.JSONDecodeError, OSError):
            pass
    return []


# ---------------------------------------------------------------------------
# Distribution analysis
# ---------------------------------------------------------------------------

@dataclass
class DistributionStats:
    n: int
    mean: float
    std: float
    median: float
    min_val: float
    max_val: float
    skewness: float
    kurtosis: float
    score_distribution: dict[str, int]  # grade → count
    concentration_warning: bool
    sd_warning: str  # "", "too_low", "too_high"
    skewness_warning: bool


def analyze_distribution(records: list[ScoreRecord]) -> DistributionStats:
    """Compute distribution statistics on weighted totals."""
    totals = np.array([r.weighted_total for r in records])
    percentiles = np.array([r.percentile for r in records])

    n = len(totals)
    mean = float(np.mean(totals))
    std = float(np.std(totals, ddof=1)) if n > 1 else 0.0
    median = float(np.median(totals))
    skewness = float(scipy_stats.skew(totals)) if n > 2 else 0.0
    kurtosis = float(scipy_stats.kurtosis(totals)) if n > 3 else 0.0

    # Grade distribution
    grade_counts = {"优": 0, "良": 0, "中": 0, "及格": 0, "不及格": 0}
    for p in percentiles:
        if p >= 90:
            grade_counts["优"] += 1
        elif p >= 80:
            grade_counts["良"] += 1
        elif p >= 70:
            grade_counts["中"] += 1
        elif p >= 60:
            grade_counts["及格"] += 1
        else:
            grade_counts["不及格"] += 1

    # Concentration check (any integer score > 40%)
    int_scores = np.round(totals).astype(int)
    concentration_warning = False
    if n > 0:
        for score_val in range(1, 6):
            count = np.sum(int_scores == score_val)
            if count / n > CONCENTRATION_THRESHOLD:
                concentration_warning = True
                break

    # SD check
    sd_warning = ""
    if std < SD_LOW_THRESHOLD:
        sd_warning = "too_low"
    elif std > SD_HIGH_THRESHOLD:
        sd_warning = "too_high"

    return DistributionStats(
        n=n,
        mean=round(mean, 3),
        std=round(std, 3),
        median=round(median, 3),
        min_val=round(float(np.min(totals)), 2),
        max_val=round(float(np.max(totals)), 2),
        skewness=round(skewness, 3),
        kurtosis=round(kurtosis, 3),
        score_distribution=grade_counts,
        concentration_warning=concentration_warning,
        sd_warning=sd_warning,
        skewness_warning=abs(skewness) >= SKEWNESS_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Bias detection
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BiasResult:
    bias_type: str
    metric: str
    value: float
    p_value: float
    threshold: float
    detected: bool
    details: str


def detect_length_bias(records: list[ScoreRecord]) -> BiasResult | None:
    """Check for correlation between word count and total score."""
    word_counts = [r.word_count for r in records]
    totals = [r.weighted_total for r in records]

    # Skip if no word count data
    if not any(w > 0 for w in word_counts):
        return None

    valid = [(w, t) for w, t in zip(word_counts, totals) if w > 0]
    if len(valid) < 5:
        return None

    wc, sc = zip(*valid)
    result = scipy_stats.spearmanr(wc, sc)
    rho = float(result.statistic) if not np.isnan(result.statistic) else 0.0
    pval = float(result.pvalue) if not np.isnan(result.pvalue) else 1.0
    detected = abs(rho) > LENGTH_BIAS_THRESHOLD and pval < 0.05

    return BiasResult(
        bias_type="Length Bias",
        metric="Spearman ρ(word_count, weighted_total)",
        value=round(rho, 4),
        p_value=round(pval, 4),
        threshold=LENGTH_BIAS_THRESHOLD,
        detected=detected,
        details=(
            f"{'Significant' if detected else 'No significant'} correlation "
            f"between submission length and score (ρ={rho:.3f}, p={pval:.4f})"
        ),
    )


def detect_position_bias(
    records: list[ScoreRecord],
    processing_order: list[str],
) -> BiasResult | None:
    """Check for correlation between processing order and score."""
    if len(processing_order) < 5:
        return None

    order_map = {sid: idx for idx, sid in enumerate(processing_order)}
    pairs = [
        (order_map[r.student_id], r.weighted_total)
        for r in records
        if r.student_id in order_map
    ]
    if len(pairs) < 5:
        return None

    orders, scores = zip(*pairs)
    result = scipy_stats.spearmanr(orders, scores)
    rho = float(result.statistic) if not np.isnan(result.statistic) else 0.0
    pval = float(result.pvalue) if not np.isnan(result.pvalue) else 1.0
    detected = abs(rho) > POSITION_BIAS_THRESHOLD and pval < 0.05

    return BiasResult(
        bias_type="Position Bias",
        metric="Spearman ρ(processing_order, weighted_total)",
        value=round(rho, 4),
        p_value=round(pval, 4),
        threshold=POSITION_BIAS_THRESHOLD,
        detected=detected,
        details=(
            f"{'Significant' if detected else 'No significant'} correlation "
            f"between processing order and score (ρ={rho:.3f}, p={pval:.4f})"
        ),
    )


def detect_dimension_coupling(
    records: list[ScoreRecord],
) -> list[BiasResult]:
    """Check for excessive correlation between dimension pairs."""
    if len(records) < 5:
        return []

    # Collect all dimension IDs
    all_dims = set()
    for r in records:
        all_dims.update(r.dimension_scores.keys())
    dim_list = sorted(all_dims)

    if len(dim_list) < 2:
        return []

    # Build score arrays
    dim_arrays: dict[str, list[int]] = {d: [] for d in dim_list}
    for r in records:
        for d in dim_list:
            dim_arrays[d].append(r.dimension_scores.get(d, 0))

    results = []
    for i, d1 in enumerate(dim_list):
        for d2 in dim_list[i + 1:]:
            result = scipy_stats.spearmanr(dim_arrays[d1], dim_arrays[d2])
            rho = float(result.statistic) if not np.isnan(result.statistic) else 0.0
            pval = float(result.pvalue) if not np.isnan(result.pvalue) else 1.0
            detected = abs(rho) > DIMENSION_COUPLING_THRESHOLD

            if detected:
                results.append(BiasResult(
                    bias_type="Dimension Coupling",
                    metric=f"Spearman ρ({d1}, {d2})",
                    value=round(rho, 4),
                    p_value=round(pval, 4),
                    threshold=DIMENSION_COUPLING_THRESHOLD,
                    detected=True,
                    details=(
                        f"High correlation between {d1} and {d2} "
                        f"(ρ={rho:.3f}). Dimensions may not be independent."
                    ),
                ))

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    dist: DistributionStats,
    biases: list[BiasResult],
    dim_means: dict[str, float],
    confidence_stats: dict[str, Any],
) -> str:
    """Generate a Markdown statistics report."""
    lines = [
        "# Score Distribution & Bias Analysis Report",
        "",
        "## Distribution Statistics",
        "",
        "| Metric | Value | Status |",
        "|--------|-------|--------|",
        f"| N (submissions) | {dist.n} | — |",
        f"| Mean (weighted total) | {dist.mean} | {'⚠️' if dist.mean < 2.5 or dist.mean > 3.5 else '✅'} |",
        f"| Standard Deviation | {dist.std} | {'⚠️ ' + dist.sd_warning if dist.sd_warning else '✅'} |",
        f"| Median | {dist.median} | — |",
        f"| Min / Max | {dist.min_val} / {dist.max_val} | — |",
        f"| Skewness | {dist.skewness} | {'⚠️ |skew| ≥ 1.0' if dist.skewness_warning else '✅'} |",
        f"| Kurtosis | {dist.kurtosis} | — |",
        f"| Concentration warning | {'⚠️ Yes' if dist.concentration_warning else '✅ No'} | — |",
        "",
        "## Grade Distribution",
        "",
        "| Grade | Count | Percentage |",
        "|-------|-------|------------|",
    ]

    for grade, count in dist.score_distribution.items():
        pct = count / dist.n * 100 if dist.n > 0 else 0
        lines.append(f"| {grade} | {count} | {pct:.1f}% |")

    lines.extend([
        "",
        "## Per-Dimension Means",
        "",
        "| Dimension | Mean Score |",
        "|-----------|------------|",
    ])

    for name, mean in dim_means.items():
        lines.append(f"| {name} | {mean:.2f} |")

    lines.extend([
        "",
        "## Confidence Statistics",
        "",
        f"- Mean confidence: {confidence_stats.get('mean', 0):.2f}",
        f"- Low confidence (<0.6): {confidence_stats.get('low_count', 0)} "
        f"({confidence_stats.get('low_pct', 0):.1f}%)",
        f"- Medium confidence (0.6-0.8): {confidence_stats.get('med_count', 0)} "
        f"({confidence_stats.get('med_pct', 0):.1f}%)",
        f"- High confidence (≥0.8): {confidence_stats.get('high_count', 0)} "
        f"({confidence_stats.get('high_pct', 0):.1f}%)",
        "",
        "## Bias Detection",
        "",
        "| Bias Type | Metric | Value | Threshold | Detected |",
        "|-----------|--------|-------|-----------|----------|",
    ])

    if not biases:
        lines.append("| (no bias checks performed) | — | — | — | — |")
    else:
        for b in biases:
            status = "⚠️ Yes" if b.detected else "✅ No"
            lines.append(
                f"| {b.bias_type} | {b.metric} | {b.value} | {b.threshold} | {status} |"
            )

    # Detected biases detail
    detected = [b for b in biases if b.detected]
    if detected:
        lines.extend(["", "### Detected Bias Details", ""])
        for b in detected:
            lines.append(f"- **{b.bias_type}**: {b.details}")

    # Recommendations
    lines.extend(["", "## Recommendations", ""])
    warnings = []
    if dist.sd_warning == "too_low":
        warnings.append(
            "Score variance is very low — AI may not be distinguishing quality levels. "
            "Review Rubric anchor descriptions for distinctiveness."
        )
    if dist.sd_warning == "too_high":
        warnings.append(
            "Score variance is very high — check for scoring inconsistency. "
            "Review calibration metrics."
        )
    if dist.skewness_warning:
        direction = "low scores" if dist.skewness > 0 else "high scores"
        warnings.append(
            f"Distribution is skewed toward {direction}. "
            "Investigate whether this reflects student quality or scoring bias."
        )
    if dist.concentration_warning:
        warnings.append(
            "Over 40% of scores are concentrated at a single level. "
            "Check Rubric granularity — anchors may need finer distinction."
        )
    for b in detected:
        warnings.append(f"{b.bias_type} detected: {b.details}")

    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- No issues detected. Score distribution and bias checks are within normal ranges.")

    lines.extend(["", "---", "", "*Generated by homework-grader stats analysis*"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze score distributions and detect bias.",
    )
    parser.add_argument("workspace", type=Path, help="Workspace directory")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output report path (default: workspace/reports/statistics.md)",
    )
    args = parser.parse_args()

    workspace: Path = args.workspace
    output_path = args.output or (workspace / "reports" / "statistics.md")

    # Load data
    records = load_scores(workspace)
    if not records:
        logger.error("No score records found")
        sys.exit(1)

    processing_order = load_processing_order(workspace)

    # Distribution analysis
    dist = analyze_distribution(records)

    # Per-dimension means
    dim_totals: dict[str, list[int]] = {}
    dim_names: dict[str, str] = {}
    for r in records:
        for cid, score in r.dimension_scores.items():
            dim_totals.setdefault(cid, []).append(score)
    # Try to get human-readable names from first record
    for path in sorted((workspace / "scores").glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for d in data.get("dimension_scores", []):
                cid = d.get("criterion_id", "")
                cname = d.get("criterion_name", cid)
                if cid:
                    dim_names[cid] = cname
            break
        except Exception:
            pass

    dim_means = {
        dim_names.get(cid, cid): round(sum(scores) / len(scores), 2)
        for cid, scores in dim_totals.items()
        if scores
    }

    # Confidence stats
    confidences = [r.confidence for r in records]
    n = len(confidences)
    conf_stats = {
        "mean": sum(confidences) / n if n else 0,
        "low_count": sum(1 for c in confidences if c < 0.6),
        "low_pct": sum(1 for c in confidences if c < 0.6) / n * 100 if n else 0,
        "med_count": sum(1 for c in confidences if 0.6 <= c < 0.8),
        "med_pct": sum(1 for c in confidences if 0.6 <= c < 0.8) / n * 100 if n else 0,
        "high_count": sum(1 for c in confidences if c >= 0.8),
        "high_pct": sum(1 for c in confidences if c >= 0.8) / n * 100 if n else 0,
    }

    # Bias detection
    biases: list[BiasResult] = []
    length_bias = detect_length_bias(records)
    if length_bias:
        biases.append(length_bias)
    position_bias = detect_position_bias(records, processing_order)
    if position_bias:
        biases.append(position_bias)
    coupling = detect_dimension_coupling(records)
    biases.extend(coupling)

    # Generate report
    report = generate_report(dist, biases, dim_means, conf_stats)

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Summary
    detected_count = sum(1 for b in biases if b.detected)
    logger.info(
        "Stats complete: N=%d, mean=%.2f, SD=%.2f, biases_detected=%d",
        dist.n, dist.mean, dist.std, detected_count,
    )
    logger.info("Report saved to %s", output_path)


if __name__ == "__main__":
    main()

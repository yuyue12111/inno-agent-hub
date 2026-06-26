# Quality Control Framework

This document details the three-layer quality control architecture, calibration
protocol, distribution analysis, and system maturity model for the
homework-grader Skill.

---

## Three-Layer Architecture

Quality control operates at three stages of the grading pipeline. Each layer
catches different classes of problems.

```
Layer 1: Gate QC          Layer 2: Scoring QC         Layer 3: Audit QC
(before scoring)          (during scoring)            (after batch)

File integrity            CoT enforcement             Calibration (κ, ρ)
Format validation         Evidence requirement        Distribution checks
Content gates             Anti-bias prompts           Bias detection
Academic integrity        Score range validation      Confidence filtering
                          Weight calculation check    Human review routing
```

### Layer 1: Gate Quality Control (Pre-Scoring)

Gate QC prevents wasted resources by filtering out submissions that are
incomplete, corrupt, or violate basic requirements before they reach the
scoring engine.

| Check | Method | Action on Failure |
|-------|--------|-------------------|
| File exists and readable | OS file check | Mark as `missing` |
| File format matches expected | Extension + magic bytes | Mark as `format_error` |
| Text extraction succeeds | python-docx / PyMuPDF | Mark as `extraction_error` |
| Content non-empty | `word_count > threshold` | Mark as `empty_submission` |
| Rubric gates | Execute each gate in order | Per `on_fail`: fail/flag/warn |

**Gate execution order matters.** Gates are processed sequentially as listed in
the Rubric. A `fail` gate stops all further processing. `flag` and `warn`
gates record their result and continue.

### Layer 2: Scoring Quality Control (During Scoring)

These controls are embedded in the scoring prompt and output validation. They
operate on every single submission.

| Control | Implementation | Verification |
|---------|---------------|--------------|
| Chain-of-Thought | Prompt requires evidence→reasoning→score order | Check `reasoning` field is non-empty |
| Evidence citation | Prompt requires direct quotes or observations | Check `evidence` field is non-empty |
| Score range | Schema requires integer 1-5 | Validate against `criterion.scale` |
| Weight arithmetic | `weighted_total = Σ(weight × score)` | Recompute and verify (tolerance ±0.01) |
| Anti-bias directives | Five directives in system prompt | Embedded (not verifiable post-hoc) |
| Confidence self-assessment | Prompt requests 0-1 confidence per dimension | Check value exists and is in range |

**Output validation**: After each scoring response, verify:
1. JSON parses correctly
2. All criteria from the Rubric are present in the output
3. Scores are within the defined scale
4. Weighted total arithmetic is correct
5. Evidence and reasoning fields are populated

If validation fails, retry up to 2 times with the same input. If all retries
fail, mark the submission for manual scoring.

### Layer 3: Audit Quality Control (Post-Batch)

After an entire batch is scored, run global checks to catch systemic issues
that single-submission checks cannot detect.

| Check | Tool | Threshold | Remediation |
|-------|------|-----------|-------------|
| Calibration | `scripts/calibrate.py` | κ ≥ 0.70, ρ ≥ 0.80/dim, MAD ≤ 0.5 | Adjust Rubric anchors |
| Distribution | `scripts/stats.py` | \|skewness\| < 1.0, no >40% at one score | Spot-check extremes |
| Length bias | `scripts/stats.py` | \|ρ(words, score)\| ≤ 0.3 | Adjust prompt |
| Position bias | `scripts/stats.py` | \|ρ(order, score)\| ≤ 0.2 | Already randomized; investigate |
| Dimension coupling | `scripts/stats.py` | Pairwise \|ρ\| < 0.9 | Review dimension independence |
| Confidence | Filter on scores | ≤ 20% below 0.6 | Manual review flagged items |

---

## Calibration Protocol

Calibration validates that AI scoring aligns with teacher standards. It is the
single most important quality check.

### When to Calibrate

| Trigger | Sample Size | Level |
|---------|-------------|-------|
| First use of a new Rubric | 10-15 samples (L2) | Full calibration |
| Routine batch grading | 3-5 samples (L1) | Quick calibration |
| Rubric version change | 5-10 samples | Re-calibration |
| Semester boundary | 10-15 samples (L2) | Extended calibration |
| Metrics degrading over time | 10-15 samples | Diagnostic calibration |

### Calibration Sample Requirements

Samples must:
- Cover the full quality range: at least 1 good, 1 medium, 1 poor
- Include edge cases (borderline accept/reject) when using L2
- Be scored by the teacher with per-dimension scores (not just totals)
- Include brief rationale for each dimension score (for comparing reasoning)

### Metrics

#### Weighted Cohen's Kappa (κ_w)

Measures overall agreement adjusted for chance agreement. Weighted kappa is
used because scores are ordinal (a 1-point disagreement is less severe than a
3-point disagreement).

```
Interpretation:
  κ < 0.20     Poor agreement
  0.20 - 0.40  Fair
  0.41 - 0.60  Moderate
  0.61 - 0.80  Substantial
  0.81 - 1.00  Near-perfect

Threshold: κ_w ≥ 0.70 (substantial agreement)
```

#### Spearman's ρ (per dimension)

Measures rank-order correlation between teacher and AI scores for each scoring
dimension. This catches cases where the AI gets relative ordering wrong even if
absolute scores are close.

```
Threshold: ρ ≥ 0.80 per dimension
```

A dimension with ρ < 0.80 indicates the AI is not reliably distinguishing
quality levels for that specific criterion. The most common fix is to
differentiate adjacent anchor descriptions more clearly.

#### Mean Absolute Difference (MAD)

Detects systematic scoring drift — is the AI consistently scoring higher or
lower than the teacher?

```
MAD = mean(|AI_score - teacher_score|) across all samples and dimensions

Threshold: MAD ≤ 0.5
```

A high MAD with acceptable κ suggests the AI understands quality ordering but
has a systematic offset. Adjust anchor language to shift the distribution.

### Calibration Failure Response

| Failure Pattern | Diagnosis | Action |
|----------------|-----------|--------|
| κ < 0.70, all ρ low | Fundamental misalignment | Review entire Rubric; consider re-writing anchors |
| κ ≥ 0.70 but specific dim ρ < 0.80 | Dimension-specific confusion | Sharpen that dimension's anchor distinctions |
| MAD > 0.5, positive | AI scores too high | Add stricter language to high-score anchors |
| MAD > 0.5, negative | AI scores too low | Verify anchors aren't overly demanding |
| Good metrics but high variance on edge cases | Borderline handling | Add intermediate guidance in scoring_guidance field |

---

## Distribution Analysis

After a batch is scored, distribution analysis checks whether the score
distribution is reasonable.

### Expected Characteristics

For a typical university course with heterogeneous student quality:

| Metric | Expected Range | Warning Signal |
|--------|---------------|----------------|
| Mean (weighted total) | 2.5 - 3.5 | Outside this range |
| Standard deviation | 0.5 - 1.5 | < 0.3 (compressed) or > 2.0 (polarized) |

> **Note**: The "Expected Range" is the typical healthy zone for a heterogeneous
> class. The "Warning Signal" thresholds (0.3 / 2.0) trigger automated alerts in
> `scripts/stats.py`. Values between (e.g., SD = 0.4 or SD = 1.8) are outside
> the typical range but do not trigger automated warnings — they may warrant a
> manual spot-check.
| Skewness | \|value\| < 1.0 | High positive = too many low scores; high negative = too many high |
| Score concentration | No single score > 40% | > 40% at any one integer score |

### Diagnostic Actions

- **Mean too high** (> 3.5): Check if anchors are too lenient. Sample high-scoring submissions.
- **Mean too low** (< 2.5): Check if anchors are too strict. Sample low-scoring submissions.
- **SD too low** (< 0.3): AI cannot distinguish quality levels. Sharpen anchor descriptions.
- **SD too high** (> 2.0): Possible inconsistency. Check calibration metrics.
- **High skewness**: Investigate whether it reflects real student quality or scoring bias.

---

## Confidence-Based Routing

The confidence score attached to each evaluation determines the review workflow.

### Confidence Factors

Confidence is computed per-dimension and then averaged:

| Factor | Effect on Confidence |
|--------|---------------------|
| Clear anchor match (submission obviously fits one level) | Higher |
| Abundant evidence found in submission | Higher |
| Borderline between two adjacent anchors | Lower |
| Sparse or ambiguous submission content | Lower |
| Dimension requires subjective judgment | Lower |

### Routing Rules

| Confidence Range | Label | Action |
|-----------------|-------|--------|
| ≥ 0.80 | Trusted | No review needed |
| 0.60 - 0.79 | Suggested | Spot-check recommended (teacher samples ~10%) |
| < 0.60 | Required | Must be reviewed by teacher |

### Monitoring the Review Rate

The target is ≤ 20% of submissions requiring mandatory review (confidence
< 0.6). Suggested reviews (0.6-0.79) are at the teacher's discretion and do
not count toward this target. If the mandatory review rate exceeds this
threshold:

1. Check if specific dimensions are driving low confidence
2. Examine whether anchors for those dimensions are ambiguous
3. Consider adding `scoring_guidance` with more explicit instructions
4. Re-calibrate after Rubric adjustments

---

## System Maturity Model

The grading system matures through three stages as confidence in AI scoring
accuracy grows.

### Stage 1: Trial Run

- **Calibration**: L2 (≥ 10 teacher-scored samples)
- **Review rate**: Expect 30-50% manual review
- **Automation**: Low — AI scores are suggestions, teacher confirms all
- **Duration**: First 1-2 batches with a new Rubric
- **Goal**: Establish baseline metrics, tune anchors

### Stage 2: Regular Operation

- **Calibration**: L1 (3-5 samples per batch)
- **Review rate**: Target ≤ 20%
- **Automation**: Medium — teacher reviews only flagged items
- **Duration**: After baseline established, ongoing
- **Goal**: Efficient grading with quality safeguards

### Stage 3: Mature Operation

- **Calibration**: L1 routine + periodic L2 spot-checks
- **Review rate**: Target ≤ 10%
- **Automation**: High — minimal teacher intervention
- **Duration**: After multiple successful batches with stable metrics
- **Goal**: Scalable grading at consistent quality

### Advancement Criteria

| From → To | Requirement |
|-----------|-------------|
| Trial → Regular | κ ≥ 0.70 and all ρ ≥ 0.80 for 2 consecutive batches |
| Regular → Mature | κ ≥ 0.75, review rate ≤ 15%, no bias alerts for 3+ batches |
| Any → Trial (regression) | κ drops below 0.65, or major Rubric change |

---

## Continuous Improvement Log

After each batch, record findings in a structured improvement log:

```yaml
improvement_log:
  - date: "YYYY-MM-DD"
    batch: "course-assignment-batch-N"
    rubric_version: "X.Y"
    metrics:
      kappa: 0.XX
      dimension_rho: { dim1: 0.XX, dim2: 0.XX }
      mad: 0.XX
      review_rate: 0.XX
    issues:
      - description: "What was observed"
        diagnosis: "Root cause"
        action: "What was changed"
        result: "Outcome after change"
    rubric_changes:
      - "List of anchor/weight/gate modifications"
    next_version: "X.Y+1 if changed"
```

This log feeds back into the PDCA Act phase and informs Plan for the next cycle.

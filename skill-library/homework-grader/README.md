# Homework Grader

A Rubric-driven AI grading system built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill. Score student submissions against structured rubrics with Chain-of-Thought reasoning, built-in bias mitigation, and a PDCA quality cycle.

## What It Does

- **Rubric-driven scoring**: Define criteria, weights, and anchor descriptions in YAML. The AI scores strictly against your standards — never inventing its own.
- **Chain-of-Thought**: Every score requires evidence citation → reasoning → score. Research shows this improves reliability by 15-25% vs direct scoring.
- **Bias mitigation**: Five anti-bias controls (length, authority, verbosity, position, self-enhancement) embedded in every scoring interaction.
- **Gate checks**: Pre-scoring validation (keyword, structure, length, custom) filters incomplete submissions before they consume API tokens.
- **Batch processing**: Score hundreds of submissions with progress tracking, checkpoint/resume, and cost control. Supports both real-time (Messages API) and async (Batch API at 50% cost).
- **Calibration**: Compare AI scores against teacher-scored samples using Cohen's κ, Spearman ρ, and MAD metrics.
- **Excel export**: Three-sheet workbook with grade table, class statistics, and detailed scoring records.
- **Multimodal**: Text (docx/pdf), image (jpg/png via Claude Vision), and mixed submissions.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- Python ≥ 3.10 (for preprocessing and batch scripts)
- An Anthropic API key (`ANTHROPIC_API_KEY` environment variable)

## Installation

### As a Claude Code Skill

1. Copy the `homework-grader/` directory to your Claude Code skills location:

```bash
# Example: copy to your project or global skills directory
cp -r homework-grader/ ~/.claude/skills/homework-grader/
```

2. Install Python dependencies (needed only for batch processing and Excel export):

```bash
pip install -r homework-grader/scripts/requirements.txt
```

### Standalone

Clone this repository and install dependencies:

```bash
git clone https://github.com/your-org/homework-grader.git
cd homework-grader
pip install -r scripts/requirements.txt
```

## Quick Start

### 1. Create a Rubric

Copy the template and fill in your criteria:

```bash
cp templates/rubric.yaml.tmpl my-rubric.yaml
# Edit my-rubric.yaml with your dimensions, weights, and anchors
```

Or ask Claude to help:

```
> Create a rubric for a marketing strategy report with 4 dimensions
```

### 2. Validate

```
> VALIDATE my-rubric.yaml
```

Checks: weights sum to 1.0, all anchors present, thresholds consistent, gates well-formed.

### 3. Score a Single Submission

```
> SCORE student-report.docx against my-rubric.yaml
```

Claude reads the file, runs gate checks, scores each dimension with evidence and reasoning, generates a structured comment, and outputs a JSON result.

### 4. Batch Score

For many submissions, use the Python scripts:

```bash
# Preprocess submissions to IR format
python scripts/preprocess.py workspace/raw/ --output workspace/ir/ --rubric my-rubric.yaml

# Score all (real-time mode for < 50 submissions)
python scripts/batch_score.py workspace/ --rubric my-rubric.yaml --mode real-time

# Or use Batch API for large batches (50% cost savings)
python scripts/batch_score.py workspace/ --rubric my-rubric.yaml --mode batch
```

### 5. Export to Excel

```bash
python scripts/export_excel.py workspace/ --mapping workspace/student-mapping.csv
```

Produces a three-sheet Excel workbook in `workspace/reports/grades.xlsx`.

## How It Works

### PDCA Quality Cycle

Every grading batch follows four phases:

1. **Plan** — Define Rubric, prepare calibration samples, configure gates
2. **Do** — Preprocess submissions, run AI scoring with CoT, generate comments
3. **Check** — Calibrate against teacher scores (κ ≥ 0.70), check distributions, detect bias
4. **Act** — Review flagged items, refine Rubric, export final grades

### Scoring Protocol

For each submission, each Rubric dimension is scored independently:

1. **Evidence**: Quote from the submission or describe observation
2. **Reasoning**: Compare evidence against anchor descriptions
3. **Score**: Assign 1-5 based on reasoning (never reversed)
4. **Improvement**: One actionable suggestion
5. **Confidence**: 0-1 self-assessment of scoring certainty

Scores are aggregated: `weighted_total = Σ(weight × score)`, then mapped to a percentile (40-100) and grade level.

### Grade Mapping

| Weighted Total | Percentile | Grade |
|---------------|------------|-------|
| 5.0 | 100 | 优 (Excellent) |
| 4.0 | 85 | 良 (Good) |
| 3.0 | 70 | 中 (Satisfactory) |
| 2.0 | 55 | 及格 (Pass) |
| 1.0 | 40 | 不及格 (Fail) |

## Creating Rubrics

A Rubric YAML defines everything the AI needs to score submissions. See `templates/rubric.yaml.tmpl` for the full template.

### Minimal Example

```yaml
rubric:
  id: my-course-essay-v1.0
  name: "Essay Grading Rubric"
  version: 1.0

  criteria:
    argument_quality:
      name: "Argument Quality"
      weight: 0.40
      scale: [1, 2, 3, 4, 5]
      description: "Clarity and strength of the central argument"
      scoring_guidance: "Look for a clear thesis, logical structure, and evidence"
      anchors:
        5: "Clear thesis; logical argument chain; strong evidence; addresses counterarguments"
        4: "Clear thesis; mostly logical; adequate evidence"
        3: "Thesis present but underdeveloped; some logical gaps"
        2: "Thesis unclear; weak logic; minimal evidence"
        1: "No identifiable thesis or argument"
      evidence_type: quote

    writing_quality:
      name: "Writing Quality"
      weight: 0.30
      scale: [1, 2, 3, 4, 5]
      description: "Grammar, style, and clarity of writing"
      scoring_guidance: "Assess readability, grammar, and academic tone"
      anchors:
        5: "Excellent prose; no grammar errors; engaging academic style"
        4: "Good writing; minor errors; appropriate tone"
        3: "Adequate writing; some errors; inconsistent tone"
        2: "Poor writing; many errors; hard to follow"
        1: "Incomprehensible or extremely poorly written"
      evidence_type: observation

    research_depth:
      name: "Research Depth"
      weight: 0.30
      scale: [1, 2, 3, 4, 5]
      description: "Quality and breadth of sources used"
      scoring_guidance: "Count and evaluate the sources cited"
      anchors:
        5: "5+ credible sources; well-integrated; current literature"
        4: "3-4 credible sources; mostly well-used"
        3: "1-2 sources; superficial use"
        2: "Sources present but unreliable or irrelevant"
        1: "No sources cited"
      evidence_type: quote

  thresholds:
    accept: 3.0
    reject: 1.5
    review: [1.5, 3.0]
```

### Tips for Effective Rubrics

- **Make anchors distinguishable**: Adjacent levels (3 vs 4) should have clear, observable differences
- **Use specific language**: "2+ credible sources" is better than "adequate research"
- **Include scoring_guidance**: Tell the AI what to look for — this dramatically improves consistency
- **Weight thoughtfully**: Weights reflect what matters most in the assignment
- **Keep gates practical**: Use `on_fail: flag` (continue scoring with warning) more often than `on_fail: fail` (skip scoring entirely)

## Batch Processing

### Workspace Structure

```
workspace/my-batch/
├── raw/                    # Original submission files
├── ir/                     # Preprocessed IR files
├── scores/                 # Scoring results
├── reports/                # Excel, calibration report
├── logs/                   # Processing logs
├── progress.json           # Checkpoint for resume
└── student-mapping.csv     # Anon ID ↔ real student info
```

### Cost Estimate

Using Claude Sonnet with Batch API (50% discount):

| Batch Size | Estimated Cost |
|-----------|---------------|
| 50 | ~$0.80 |
| 100 | ~$1.60 |
| 500 | ~$8.00 |

### Resume After Interruption

```bash
python scripts/batch_score.py workspace/my-batch/ --rubric my-rubric.yaml --resume
```

The script reads `progress.json` and continues from where it left off.

## Quality Control

### Calibration

Before trusting AI scores, calibrate against teacher-scored samples:

1. Score 3-5 submissions yourself (covering good/medium/poor quality)
2. Save as `{student_id}-teacher.json` in a calibration directory
3. Run calibration:

```bash
python scripts/calibrate.py workspace/ --rubric my-rubric.yaml --samples calibration-samples/
```

**Pass criteria**: Cohen's κ ≥ 0.70, Spearman ρ ≥ 0.80 per dimension, MAD ≤ 0.5.

### Distribution & Bias Analysis

After a batch:

```bash
python scripts/stats.py workspace/
```

Checks for length bias, position bias, dimension coupling, score concentration, and distributional anomalies.

## Examples

The `examples/` directory contains four complete Rubric YAMLs covering common course types:

| Example | Course | Modality |
|---------|--------|----------|
| `research-paper-rubric.yaml` | Research Methods | Text |
| `video-project-rubric.yaml` | Digital Media Production | Mixed (video + text) |
| `marketing-plan-rubric.yaml` | Marketing Fundamentals | Mixed (text + images) |
| `technical-report-rubric.yaml` | Environmental Science | Text |

## FAQ

**Q: Can I use this without the Python scripts?**
Yes. SKILL.md contains the complete scoring protocol. Claude can read a Rubric YAML and a submission file, then score it directly in conversation. Scripts are accelerators for batch processing and Excel export.

**Q: What model should I use?**
Claude Sonnet for routine scoring (best cost/quality balance). Claude Opus for calibration verification or when scoring complex submissions that require deeper reasoning.

**Q: How do I handle image submissions?**
The preprocessing pipeline uses Claude Vision to generate structured descriptions of images. These descriptions become the "submission content" that the scoring engine evaluates. Set `submission_type: image` or `mixed` in your Rubric.

**Q: What if calibration fails?**
Review the calibration report for which dimensions are misaligned. Usually the fix is to sharpen anchor descriptions — make adjacent levels (e.g., 3 vs 4) more distinguishable. Then re-calibrate.

**Q: Is student data sent to the API?**
Student names and IDs are never sent. All submissions are anonymized during preprocessing. The `student-mapping.csv` file (linking anonymous IDs to real identities) stays local and is only used during Excel export.

**Q: Can I customize the comment language?**
Yes. Set `comment_guidelines.language` in your Rubric YAML to any language code (e.g., `zh-CN`, `en`, `ja`). The AI generates comments in that language.

## References

| Document | Content |
|----------|---------|
| `references/evaluation-methodology.md` | Scoring theory, CoT, confidence calibration |
| `references/bias-mitigation.md` | Five bias types and countermeasures |
| `references/quality-control-framework.md` | Three-layer QC, calibration protocol |
| `references/multimodal-pipeline.md` | IR format, processing pipelines |
| `references/batch-processing-guide.md` | Batch modes, workspace, cost estimation |

## License

MIT

# Batch Processing Guide

This document covers the two processing modes, workspace organization, progress
tracking, checkpoint/resume, cost estimation, and operational procedures.

---

## Processing Modes

The homework-grader supports two modes for scoring submissions. Choose based on
batch size and urgency.

### Real-Time Mode (Messages API)

- **API**: Claude Messages API (synchronous)
- **Best for**: < 50 submissions, or when results are needed immediately
- **Latency**: ~30-60 seconds per text submission; ~60-120 seconds for image
- **Concurrency**: Configurable (default 5 workers), limited by API rate limits
- **Cost**: Full API pricing

```
Workflow:
  1. Load submission list, randomize order
  2. Initialize worker pool (N concurrent workers)
  3. Each worker:
     a. Pick next pending submission from queue
     b. Load IR file
     c. Build scoring prompt (system + Rubric + content)
     d. Call Messages API
     e. Parse response, validate output
     f. Save score JSON to workspace/scores/
     g. Update progress.json
  4. On error: retry with exponential backoff (max 3 attempts)
  5. On completion: log summary statistics
```

### Batch Mode (Batch API)

- **API**: Claude Batch API (asynchronous, results within 24 hours)
- **Best for**: ≥ 50 submissions with no urgency
- **Cost**: 50% discount vs real-time pricing
- **Max batch size**: 10,000 requests per batch

```
Workflow:
  1. Load submission list, randomize order
  2. Build JSONL request file:
     - One line per submission
     - Each line: { custom_id, method, url, body: { model, system, messages } }
  3. Upload JSONL to Batch API
  4. Poll batch status (interval: 60 seconds)
     - pending → in_progress → ended
  5. Download results file
  6. Parse each result, save score JSONs
  7. Handle failures:
     - Collect failed request IDs
     - Optionally retry via real-time mode
```

### Mode Selection Guide

| Factor | Real-Time | Batch |
|--------|-----------|-------|
| Submissions < 50 | ✅ Recommended | Possible but slower |
| Submissions ≥ 50 | Expensive | ✅ Recommended |
| Results needed in < 1 hour | ✅ Only option | ❌ |
| Budget constrained | ❌ Full price | ✅ 50% discount |
| Need progress visibility | ✅ Per-item tracking | Batch-level only |

---

## Workspace Organization

Every batch creates an isolated workspace directory. This ensures batches don't
interfere with each other and supports clean resume/retry.

```
workspace/
└── {batch-id}/                    # Format: {course}-{date} or custom name
    ├── raw/                       # Original submission files
    │   ├── anon-001.docx
    │   ├── anon-002.pdf
    │   └── ...
    ├── ir/                        # Preprocessed IR JSON files
    │   ├── anon-001.json
    │   ├── anon-002.json
    │   └── ...
    ├── scores/                    # Scoring result JSON files
    │   ├── anon-001.json
    │   ├── anon-002.json
    │   └── ...
    ├── reports/                   # Output reports
    │   ├── grades.xlsx
    │   ├── calibration-report.md
    │   └── statistics.md
    ├── logs/                      # Processing logs
    │   ├── preprocess.log
    │   ├── scoring.log
    │   └── errors.log
    ├── progress.json              # Batch progress checkpoint
    └── student-mapping.csv        # Anon ID ↔ real identity
```

### Batch ID Convention

Recommended format: `{course-slug}-{YYYYMMDD}`

Examples:
- `research-methods-20260315`
- `media-production-20260401`
- `env-science-20260420`

---

## Progress Tracking

The `progress.json` file is the single source of truth for batch state. It is
updated after every submission is processed.

### Schema

```json
{
  "batch_id": "research-methods-20260315",
  "rubric_id": "research-methods-case-analysis-v1.0",
  "rubric_version": 1.0,
  "mode": "real-time",
  "started_at": "2026-03-15T10:00:00",
  "last_updated": "2026-03-15T10:45:00",
  "total": 80,
  "completed": 45,
  "failed": 2,
  "pending": 33,
  "completed_ids": ["anon-001", "anon-002", "..."],
  "failed_ids": [
    {
      "id": "anon-015",
      "error": "API timeout after 3 retries",
      "attempts": 3,
      "last_attempt": "2026-03-15T10:32:00"
    }
  ],
  "pending_ids": ["anon-046", "anon-047", "..."],
  "processing_order": ["anon-023", "anon-057", "..."],
  "stats": {
    "avg_duration_ms": 45000,
    "avg_input_tokens": 6500,
    "avg_output_tokens": 2800,
    "total_cost_usd": 0.72
  }
}
```

---

## Checkpoint and Resume

### How Resume Works

When a batch is interrupted (user stops, network failure, process crash):

1. Read `progress.json`
2. Skip all `completed_ids` — their score files already exist
3. For `failed_ids`: retry if `attempts < max_retries` (default 3)
4. Continue processing `pending_ids`
5. Preserve original `processing_order` for position bias analysis

### Resume Command

```
BATCH resume workspace/{batch-id}
```

The Skill detects `progress.json` exists, loads state, and continues.

### Data Integrity

- Score files are written atomically (write to temp file, then rename)
- `progress.json` is updated after each successful write
- If a crash occurs between writing a score and updating progress, the score
  file exists but progress doesn't reflect it — the resume logic detects this
  and skips the already-scored submission

---

## Error Handling

### Error Classification

| Error Type | Retryable | Max Retries | Backoff |
|------------|-----------|-------------|---------|
| API timeout | Yes | 3 | Exponential: 2s, 4s, 8s |
| Rate limit (429) | Yes | Unlimited | Wait for `Retry-After` header |
| Invalid JSON response | Yes | 2 | Immediate |
| Score out of range | Yes | 1 | Immediate |
| File read error | No | 0 | — |
| API authentication error | No | 0 | — |

### Error Isolation

**Critical principle**: A failure in one submission must never affect others.

- Each submission is processed independently
- Errors are caught per-submission and logged
- Failed submissions are recorded in `progress.json` with error details
- The batch continues with remaining submissions
- A final error report lists all failures for manual resolution

### Error Report

After batch completion, generate an error summary:

```
Batch Error Report: research-methods-20260315
═══════════════════════════════════════════

Total: 80  |  Completed: 76  |  Failed: 4

Failed Submissions:
  anon-015  API timeout (3 retries exhausted)
  anon-032  Empty submission (word_count = 0)
  anon-041  Gate FAILED: G-001 (no references found, on_fail=fail)
  anon-067  JSON parse error (2 retries exhausted)

Action Required:
  - anon-015: Retry manually or check submission file
  - anon-032: Contact student about empty submission
  - anon-041: Scores skipped per gate policy — record as incomplete
  - anon-067: Score manually
```

---

## Cost Estimation

### Per-Submission Cost Model

```
Cost = (input_tokens × input_price + output_tokens × output_price) × discount

Where:
  input_tokens  ≈ system_prompt (~1000) + rubric (~2000) + content (variable)
  output_tokens ≈ per_dimension (~500) × num_dimensions + comment (~400)
  discount      = 1.0 (real-time) or 0.5 (Batch API)
```

### Typical Costs (Claude Sonnet, Batch API)

| Submission Type | Input Tokens | Output Tokens | Cost/Item | 100 Items | 500 Items |
|----------------|-------------|---------------|-----------|-----------|-----------|
| Short text (< 2000 words) | ~5,000 | ~2,500 | ~$0.013 | ~$1.30 | ~$6.50 |
| Medium text (2000-5000 words) | ~7,000 | ~2,900 | ~$0.016 | ~$1.60 | ~$8.00 |
| Long text (> 5000 words) | ~12,000 | ~3,000 | ~$0.020 | ~$2.00 | ~$10.00 |
| Image (per image) | ~2,000 + image | ~2,500 | ~$0.015 | ~$1.50 | ~$7.50 |
| Mixed (text + 2 images) | ~10,000 + images | ~3,000 | ~$0.025 | ~$2.50 | ~$12.50 |

*Prices based on Claude Sonnet at $1.50/MTok input, $7.50/MTok output, with 50% Batch discount.*

### Budget Planning

For a typical course:

```
Budget = submissions × cost_per_item × overhead_factor

Where:
  overhead_factor = 1.2  (accounts for retries, calibration, re-runs)

Example:
  80 students × $0.016 × 1.2 = $1.54
  500 students × $0.016 × 1.2 = $9.60
```

### Cost Tracking

The `progress.json` file tracks actual token usage and cost per batch. After
completion, the total cost is included in the statistics report.

---

## Operational Procedures

### Pre-Batch Checklist

- [ ] Rubric validated (`VALIDATE rubric.yaml`)
- [ ] Calibration samples prepared (3-5 teacher-scored)
- [ ] Submission files collected in `workspace/{id}/raw/`
- [ ] Student mapping file created (`student-mapping.csv`)
- [ ] API key configured (`ANTHROPIC_API_KEY` environment variable)
- [ ] Sufficient API quota for batch size

### Batch Execution

```bash
# Preprocess all submissions
python scripts/preprocess.py workspace/{batch-id}/raw/ \
  --output workspace/{batch-id}/ir/

# Run calibration first
python scripts/calibrate.py workspace/{batch-id}/ \
  --rubric rubric.yaml \
  --samples calibration-samples/

# If calibration passes, run batch scoring
python scripts/batch_score.py workspace/{batch-id}/ \
  --rubric rubric.yaml \
  --mode batch

# Generate statistics
python scripts/stats.py workspace/{batch-id}/

# Export to Excel
python scripts/export_excel.py workspace/{batch-id}/ \
  --mapping workspace/{batch-id}/student-mapping.csv \
  --output workspace/{batch-id}/reports/grades.xlsx
```

### Post-Batch Checklist

- [ ] Review calibration report (κ, ρ thresholds met)
- [ ] Check distribution statistics (no anomalies)
- [ ] Review bias detection results
- [ ] Manually review flagged submissions (confidence < 0.6)
- [ ] Export final grades to Excel
- [ ] Archive workspace for records

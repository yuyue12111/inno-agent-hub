# Example Rubrics

This directory contains four example Rubric YAML files demonstrating different
course types and modalities. Use them as starting points for your own Rubrics.

## Examples

| File | Course | Modality | Dimensions | Notes |
|------|--------|----------|------------|-------|
| `research-paper-rubric.yaml` | Research Methods | Text (docx/pdf) | 4 (analysis, data, strategy, writing) | Case analysis report with references gate |
| `video-project-rubric.yaml` | Digital Media Production | Mixed (mp4 + docx) | 4 (creativity, production, strategy, data) | Video + creation report, dual-file gate |
| `marketing-plan-rubric.yaml` | Marketing Fundamentals | Mixed (docx + images) | 4 (strategy, target, execution, visual) | Marketing plan with visual design assessment |
| `technical-report-rubric.yaml` | Environmental Science | Text (docx/pdf) | 4 (accuracy, compliance, risk, recommendations) | Technical report with standards citation gate |

## How to Use

1. Copy the example closest to your course type
2. Modify dimensions, weights, and anchors to fit your requirements
3. Adjust gates for your submission expectations
4. Update `comment_guidelines` for your preferred feedback language and tone
5. Validate with `VALIDATE your-rubric.yaml`

## Validation Checklist

Before using any Rubric, verify:

- [ ] All `criteria.*.weight` values sum to 1.0
- [ ] Every score in `scale` (1-5) has a corresponding anchor description
- [ ] Anchors for adjacent scores (e.g., 3 vs 4) are clearly distinguishable
- [ ] `thresholds.accept > thresholds.reject`
- [ ] `thresholds.review` equals `[reject, accept]`
- [ ] Gate `on_fail` values are valid (`fail`, `flag`, or `warn`)
- [ ] `comment_guidelines.language` matches your students' language

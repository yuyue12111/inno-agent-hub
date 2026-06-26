# Bias Mitigation Reference

> Reference for the homework-grader Skill. Five bias types in LLM-based
> scoring: definition, manifestation, mitigation (prompt / system / detection),
> and detection metrics.
>
> **Related files**: `SKILL.md` Anti-Bias Rules, `templates/scoring-prompt.md`
> Anti-Bias Directives, `references/quality-control-framework.md` Bias Monitoring.

---

## Mitigation Layers

| Layer | Where | Timing |
|-------|-------|--------|
| **Prompt-level** | Scoring system prompt | During scoring |
| **System-level** | Pipeline architecture + Rubric design | Before/during scoring |
| **Detection** | Post-batch statistical checks | After scoring |

All three layers are necessary. Prompts reduce bias magnitude. System design
prevents trigger conditions. Detection catches what leaks through.

---

## 1. Length Bias

**Definition**: LLMs assign higher scores to longer submissions regardless of
quality. Likely originates from RLHF training where human raters prefer longer
model outputs.

**Manifestation**: Padded 3,000-word submissions outscore concise 1,200-word
submissions addressing the same points. Verbose introductions and repetitive
summaries receive implicit credit. Short precise answers get lower confidence
scores, triggering unnecessary review. The bias compounds across dimensions.

**Prompt-level**: Inject Fragment 1 (Length != Quality). Explicitly instruct
that longer is not better, padding should lower scores, conciseness is valued.

**System-level**:
- Rubric anchors: mention conciseness at levels 4-5, verbosity at levels 1-2
- Do NOT pass word count to the scoring prompt (record in IR metadata only)
- Use the length gate to flag excessively long submissions for review

**Detection**: Spearman rho(word_count, weighted_total) across all submissions.

| rho Range | Interpretation | Action |
|-----------|---------------|--------|
| \|rho\| <= 0.3 | Acceptable | None |
| 0.3 < \|rho\| <= 0.5 | Moderate | Spot-check 5 shortest + 5 longest |
| \|rho\| > 0.5 | Strong bias | Re-run with strengthened directives |

**Alert threshold**: \|rho\| > 0.3 AND p < 0.05. Also compute per dimension to
isolate which dimension drives the correlation.

---

## 2. Authority Bias

**Definition**: LLMs assign higher scores to confident, academic-sounding
language even when claims are unsupported. Originates from training on academic
corpora where authoritative tone correlates with quality.

**Manifestation**: "Research conclusively demonstrates..." (no citation) scores
higher than "Based on Table 2, it appears..." (with evidence). Jargon-heavy
text beats plain-language text with equivalent understanding. Copy-pasted
textbook definitions without analysis receive credit for "sounding right."

**Prompt-level**: Inject Fragment 2 (Tone != Accuracy). Instruct that confident
language does not equal correctness. Hedged + data outranks assertive + no data.

**System-level**:
- Set `evidence_type: quote` on content dimensions to force evidence extraction
- Frame high anchors around demonstrated understanding, not language quality
- Add fact-check guidance to `scoring_guidance`: "Confident but unsupported
  claims do not merit high scores"
- Separate writing-quality and content-quality into distinct dimensions

**Detection**: No simple numeric proxy. Relies on calibration sample design:
- Include a calibration pair: Sample A (hedged + evidence) vs Sample B
  (assertive + no evidence). Teacher scores A higher; if AI scores B higher,
  authority bias is confirmed.
- Check per-dimension divergence on content dimensions (analysis depth, data
  application) — divergence there (not on writing quality) signals this bias.
- **Metric**: MAD between AI and teacher on authority-test pair. MAD > 1.0
  warrants prompt revision.

---

## 3. Verbosity Bias

**Definition**: LLMs fail to penalize detailed but irrelevant content. Unlike
length bias (total word count), verbosity bias is about **relevance** — the LLM
treats volume of detail as positive even when it does not address the question.

**Manifestation**: 800 words of general industry background receive implicit
credit on "Analysis Depth." Off-topic tangents go unpenalized. Many strategies
discussed (most irrelevant) inflate "Strategy Feasibility." Restating the same
point in different words is treated as additional evidence.

**Prompt-level**: Inject Fragment 3 (Relevance Filter). Only content relevant to
the current dimension counts. Off-topic = zero credit. Restatement = one piece
of evidence, not multiple.

**System-level**:
- Rubric anchors: "focused and relevant, no filler" at levels 4-5; "includes
  substantial off-topic content" at levels 1-2
- Use `scoring_guidance` to define relevance scope per dimension
- Redundancy flag: scorer notes when only one point is restated in multiple ways
- Avoid catch-all "effort" dimensions that reward volume

**Detection**: Spearman rho(word_count, dimension_score) computed **per
dimension**. A non-volume dimension (e.g., "Strategy Feasibility") showing
\|rho\| > 0.3 AND p < 0.05 indicates verbosity bias. Also spot-check
submissions with low on-topic content ratios — high scores despite low relevance
confirms the filter is failing.

---

## 4. Position Bias

**Definition**: Scores influenced by processing order within a batch. Manifests
as score drift: later submissions scored more harshly or leniently as the LLM
anchors to earlier submissions rather than absolute Rubric standards.

**Manifestation**: First submissions set an implicit reference point; subsequent
submissions scored relative to them. Score means shift as processing progresses.
Alphabetical processing order creates name-correlated bias — an equity concern.

**Prompt-level**: Inject Fragment 4 (Independent Scoring). Score against Rubric
only, not against other submissions. No curve, no distribution expectations.

**System-level**:
- **Stateless scoring (critical)**: one independent API call per submission.
  Never score multiple submissions in a single conversation.
- **Randomized processing order**: shuffle before processing.
- **No conversation accumulation**: each call gets only Rubric + one submission.
- **Batch API preference**: Anthropic Batch API processes requests independently
  by design, providing architectural protection.

**Detection**: Spearman rho(processing_order, weighted_total).

**Alert threshold**: \|rho\| > 0.2 AND p < 0.05. Stricter than length bias
(0.2 vs 0.3) because no legitimate reason for order-quality correlation exists.

Secondary: split batch into quartiles by processing order. Compare means.
Monotonic trend suggests drift.

---

## 5. Self-Enhancement Bias

**Definition**: LLMs score AI-generated content more favorably than equivalent
human-written content. LLM outputs share statistical properties with the
scorer's generation patterns (fluent structure, balanced paragraphs, smooth
transitions), which the scorer implicitly recognizes as "good writing."

**Manifestation**: AI-generated submissions get higher writing quality scores.
Factually shallow but stylistically polished AI text receives inflated scores.
Most pronounced on subjective dimensions (writing quality, organization), least
on objective dimensions (data accuracy, factual claims).

**Prompt-level**: Inject Fragment 5 (Content Over Form). Substance of arguments
over polish of prose. Smooth transitions are not evidence of understanding.
Generic polished text should score lower on analytical dimensions than rough but
specific text showing genuine engagement.

**System-level**:
- **AI detection gate (V2)**: custom gate flagging probable AI generation
  (`on_fail: flag` — proceeds to scoring but marked for teacher review)
- **Calibration sample**: include one known AI-generated sample, teacher-scored.
  If AI scorer rates it significantly higher (MAD > 1.0), bias is present.
- **Anchors rewarding specificity**: high levels require personal observations,
  references to class discussions, original data — elements AI text lacks
- **Neutral prompt language**: use "evidence-supported" not "well-written"

**Detection**:
- Calibration pair: one human, one AI-generated, same teacher-assigned level.
  AI score > human score by >= 0.5 weighted points indicates bias.
- Per-dimension divergence: subjective dimensions are the usual suspects.
- Batch-level: if AI detection gate deployed, compare mean scores of flagged vs
  non-flagged submissions. Higher flagged mean (t-test, p < 0.05) confirms bias
  at scale.

---

## Anti-Bias Prompt Library

Canonical prompt fragments for injection into the scoring system prompt.

### Fragment 1: Length != Quality
```
ANTI-BIAS DIRECTIVE — LENGTH:
Do NOT award higher scores because a submission is long. A concise, well-argued
answer is equal to or better than a verbose one. Irrelevant padding, repetition,
and off-topic elaboration should LOWER the score. If a short submission addresses
all anchor criteria, it deserves the corresponding score regardless of word count.
```

### Fragment 2: Tone != Accuracy
```
ANTI-BIAS DIRECTIVE — AUTHORITY:
Do NOT assume confident, academic-sounding language is correct. A hedged statement
backed by data ("Based on Table 2, it appears...") is worth MORE than an
unsupported assertion ("Research conclusively shows..."). If a claim lacks
supporting evidence, treat it as unsubstantiated regardless of how confidently
it is stated.
```

### Fragment 3: Relevance Filter
```
ANTI-BIAS DIRECTIVE — RELEVANCE:
For each dimension, ONLY content directly relevant to that dimension's criteria
contributes to the score. Off-topic elaboration earns ZERO credit. If a submission
contains 1000 words but only 200 are relevant, score based on those 200 words.
Restating the same point in different words counts as ONE piece of evidence.
```

### Fragment 4: Independent Scoring
```
ANTI-BIAS DIRECTIVE — POSITION:
Score this submission against the Rubric anchors only. Do NOT compare it to any
other submission. Do NOT adjust scores based on expected class distributions.
Each submission is evaluated in isolation. There is no curve.
```

### Fragment 5: Content Over Form
```
ANTI-BIAS DIRECTIVE — SELF-ENHANCEMENT:
Score based on substance of arguments, not polish of prose. Smooth transitions and
balanced paragraph lengths are NOT evidence of understanding. Look for specific,
concrete evidence of the student's own thinking: original examples, references to
specific data, application of concepts to the particular case. Generic polished
text should score LOWER on analytical dimensions than rough but specific text
demonstrating genuine engagement.
```

### Fragment 6: Evidence Before Score
```
ANTI-BIAS DIRECTIVE — PROCESS:
For every dimension, follow this exact order:
1. FIND evidence — quote or describe what the submission contains.
2. REASON — compare the evidence against each anchor level.
3. ASSIGN score — the integer follows from the reasoning.
Reversing this order (deciding a score first, then finding justification) is
FORBIDDEN.
```

### Fragment 7: Independent Dimensions
```
ANTI-BIAS DIRECTIVE — DIMENSION INDEPENDENCE:
Score each dimension on its own merits. A high score on one dimension does NOT
mean another should also be high. Each dimension has its own anchors and evidence.
Evaluate them independently.
```

### Combining Fragments

| Fragment | When to Include | Rationale |
|----------|----------------|-----------|
| 1 (Length) | Always | Most common LLM scoring bias |
| 2 (Authority) | Always | Impactful on content dimensions |
| 3 (Relevance) | Always | Prevents verbosity bias at dimension level |
| 4 (Position) | Batch mode only | Irrelevant for single-submission scoring |
| 5 (Self-Enhancement) | When AI-generated submissions suspected | Adds prompt length; omit if unneeded |
| 6 (Process) | Always | Structural guard against all biases |
| 7 (Dimension Independence) | Always | Prevents halo effect |

---

## Detection Summary

| Bias | Metric | Threshold | Action |
|------|--------|-----------|--------|
| Length | rho(word_count, weighted_total) | \|rho\| > 0.3, p < 0.05 | Strengthen Fragment 1, revise anchors |
| Authority | MAD on calibration pair | MAD > 1.0 | Strengthen Fragment 2, add fact-check guidance |
| Verbosity | rho(word_count, dim_score) per dimension | \|rho\| > 0.3, p < 0.05 on non-volume dims | Strengthen Fragment 3, revise scoring_guidance |
| Position | rho(order, weighted_total) | \|rho\| > 0.2, p < 0.05 | Verify stateless scoring, re-randomize |
| Self-Enhancement | Calibration pair gap | gap >= 0.5 weighted points | Strengthen Fragment 5, reward specificity |

---

## Implementation Checklist

- [ ] Scoring prompt includes Fragments 1, 2, 3, 6, 7 (minimum set)
- [ ] Fragment 4 included if batch mode
- [ ] Fragment 5 included if AI-generated submissions suspected
- [ ] Rubric anchors mention conciseness at level 4-5 (anti-length)
- [ ] Rubric anchors mention evidence over assertion (anti-authority)
- [ ] Rubric scoring_guidance specifies relevance scope per dimension (anti-verbosity)
- [ ] Scoring architecture is stateless (one API call per submission)
- [ ] Processing order is randomized
- [ ] Calibration set includes authority-test pair
- [ ] Calibration set includes AI-generated sample (if applicable)
- [ ] Post-batch `scripts/stats.py` configured with thresholds above
- [ ] Teacher reviews detection report before grades are finalized

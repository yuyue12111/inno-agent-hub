# Evaluation Methodology

> Reference document for the homework-grader Skill. Covers the evaluation
> engine's theoretical foundations, scoring protocol design, and calibration
> strategy in depth. For the operational scoring protocol, see `SKILL.md` Section
> "Scoring Protocol". For bias-specific countermeasures, see
> `references/bias-mitigation.md`.

---

## Why Direct Scoring

The evaluation engine uses **Direct Scoring** (also called absolute scoring or
criterion-referenced scoring) rather than Pairwise Comparison. This is not an
arbitrary choice; it follows directly from the nature of the task.

### Two Paradigms in LLM-as-Judge Evaluation

There are two mainstream paradigms for using LLMs as evaluators:

| Paradigm | How It Works | Best For |
|----------|-------------|----------|
| **Direct Scoring** | Each item is scored independently against a fixed rubric with defined anchors | Tasks with objective, pre-defined criteria |
| **Pairwise Comparison** | Two items are compared side-by-side; the model selects which is better | Subjective preference judgments (e.g., "which response is more helpful?") |

### Why Direct Scoring Is Right for Homework Grading

Homework grading has objective criteria. A Rubric defines exactly what a score of
3 looks like versus a score of 4, across every dimension. The teacher has
established the standard before any student submits work. This is the defining
condition for Direct Scoring:

1. **Criteria exist before evaluation**. The Rubric is written during the Plan
   phase, not discovered during scoring. Each anchor description is an objective
   reference point.

2. **Absolute standards matter more than relative rankings**. A student earning a
   3 on "Analysis Depth" means they meet the 3-level anchor criteria, regardless
   of how other students performed. Two students can both earn a 5, or all
   students can earn a 2. Grades are not a zero-sum game.

3. **Consistency across batches**. When 500 submissions are scored across hours
   or days, Direct Scoring produces consistent results because the reference
   standard (the Rubric) is invariant. Pairwise Comparison would require
   O(n^2) comparisons and introduce ordering effects.

4. **Traceability**. Every score can be traced to a specific anchor match. This
   makes score justification, teacher review, and calibration straightforward.
   With Pairwise Comparison, individual absolute scores must be inferred from
   win/loss records, losing direct traceability.

### When Pairwise Comparison Would Be Appropriate

Pairwise Comparison is the right choice when:

- There are no pre-defined criteria (e.g., "which of these two essays do you
  prefer?")
- The evaluation is inherently subjective and comparative (e.g., creative
  writing style preference, chatbot response helpfulness)
- You need to build a ranking rather than assign absolute scores

None of these conditions apply to rubric-driven homework grading.

---

## 1-5 Likert Scale

### Why Five Points

The evaluation engine uses a 5-point integer Likert scale (1, 2, 3, 4, 5) for
every scoring dimension. The choice of five points balances two competing
demands: **granularity** (enough resolution to distinguish quality levels) and
**reliability** (consistent scores across repeated evaluations).

**Fewer points (3-point scale)**:

- Higher inter-rater agreement, but too coarse for meaningful feedback.
- Collapses "good" and "excellent" into one bucket. Teachers lose the ability
  to distinguish solid work from outstanding work.
- Insufficient for weighted aggregation: a 3-point scale mapped to percentiles
  yields large jumps between grade levels.

**More points (7-point or 10-point scale)**:

- Greater theoretical granularity, but research on LLM judges shows diminishing
  reliability. The model struggles to consistently distinguish between, say, a
  6 and a 7 on a 10-point scale, because the anchor descriptions for adjacent
  points become too similar.
- Requires more elaborate anchor descriptions. For 10 points, you need 10
  distinct, clearly differentiable anchors per dimension per rubric. This is
  impractical for typical course rubrics.
- Human inter-rater reliability also drops with finer scales, making calibration
  against teacher scores harder.

**Five points** hits the sweet spot:

- Each point maps to a recognizable quality level (Poor / Below Average /
  Adequate / Good / Excellent).
- Anchor descriptions at 5 levels can be made clearly distinct from each other.
- LLM judges show better inter-rater reliability on 5-point scales than on
  finer scales, because the model has fewer ambiguous boundary decisions.
- The scale maps cleanly to a 40-100 percentile range (see "Score Aggregation"
  below), which aligns with standard Chinese academic grading conventions.

### Integer-Only Scores

Scores are constrained to integers. The model is never asked to produce 3.5 or
4.2 for a single dimension. Fractional values introduce false precision: the
model cannot reliably distinguish 3.4 from 3.6 on a single dimension. Granularity
comes from **weighted aggregation across multiple dimensions**, not from
fractional dimension scores.

---

## Chain-of-Thought Scoring

### Why CoT Is Mandatory

Chain-of-Thought (CoT) reasoning is not optional in the evaluation engine. Every
scoring interaction requires the model to reason before assigning a score.
Research on LLM-as-Judge systems shows that requiring explicit reasoning before
scoring improves inter-rater reliability by approximately **15-25%** compared to
direct score generation without justification.

The mechanism is straightforward: when the model must articulate its reasoning,
it is forced to engage with the evidence and anchor descriptions rather than
pattern-matching to a "likely" score. This reduces several failure modes:

- **Score anchoring**: Without CoT, the model may anchor to a default score
  (often 3 or 4) and insufficiently adjust. With CoT, the model must explain
  why the submission does or does not meet each anchor level, producing more
  differentiated scores.

- **Halo effect**: Without CoT, a strong impression from one aspect of the
  submission can inflate scores across all dimensions. With CoT, the model must
  find dimension-specific evidence for each score, breaking the halo.

- **Inconsistency**: Without CoT, the same submission scored twice may receive
  different scores because the model's internal reasoning path varies.
  With CoT, the explicit reasoning chain constrains the output, improving
  test-retest consistency.

### The Protocol: Evidence, Reasoning, Score

The scoring protocol enforces a strict three-step order for each dimension:

```
Step 1: EVIDENCE    Find and cite content from the submission relevant to
                    this dimension. If evidence_type is "quote", copy the
                    student's exact words. If "observation", describe what
                    is observed. If no relevant content exists, state
                    "No relevant evidence found."

Step 2: REASONING   Compare the evidence against each anchor description.
                    Identify which level the evidence matches. Explain why
                    it does not meet the next level up. Note borderline
                    cases explicitly.

Step 3: SCORE       Assign an integer 1-5 that follows from the reasoning.
```

This order is enforced in the scoring prompt, validated in the output (the
`evidence` and `reasoning` fields must be non-empty), and checked during
calibration.

### Why Reversing the Order Undermines Reliability

If the model assigns a score first and then constructs reasoning, it falls into
**confirmation bias**: the reasoning becomes a post-hoc justification for a
pre-determined score rather than an honest evaluation of evidence. The model
will selectively cite evidence that supports the already-chosen score and
downplay or ignore contradictory evidence.

This is analogous to a human grader who writes "4" first and then looks for
reasons to justify it, rather than reading the submission carefully and arriving
at a score. The former process is less reliable and less fair.

Empirically, LLM judges that produce scores before reasoning show:

- Higher variance across repeated evaluations of the same submission
- Weaker agreement with human raters
- Stronger length and tone biases (because the initial score is more influenced
  by surface features)

For these reasons, the scoring prompt explicitly states: "Reversing this order
is forbidden," and output validation checks that the `reasoning` field contains
substantive anchor comparison rather than generic affirmation.

### Practical Example

Here is what good CoT scoring looks like for a single dimension:

```json
{
  "criterion_id": "analysis_depth",
  "criterion_name": "Analysis Depth",
  "weight": 0.30,
  "evidence": "The student applies Porter's Five Forces to analyze the
    competitive landscape of the regional retail market (paragraph 3)
    and references Kotler's Marketing Mix framework to explain the
    company's positioning strategy (paragraph 5). Data from the National
    Bureau of Statistics (2024) is cited to support the analysis.",
  "reasoning": "The submission demonstrates multi-level analysis using two
    theoretical frameworks with data support. This matches the anchor for
    score 4: 'applies 1-2 theoretical frameworks; has data support; shows
    some original insight.' It does not reach score 5 because the original
    insight is limited -- the student describes the frameworks' application
    but does not synthesize them into a novel strategic recommendation.",
  "score": 4,
  "improvement": "Synthesize the Porter and Kotler analyses into a unified
    strategic insight, rather than presenting them as parallel discussions.",
  "confidence": 0.85
}
```

Notice: evidence is cited first, reasoning compares against anchors, and the
score follows logically. The improvement suggestion is specific and actionable.

---

## Prompt Engineering for Scoring

### Prompt Architecture Overview

The scoring prompt follows a two-message structure (system + user) with
structured JSON output. Each element serves a specific purpose in ensuring
reliable, unbiased evaluation.

### System Prompt: Role and Anti-Bias Directives

The system prompt establishes two things:

1. **Role definition**: "You are a meticulous homework evaluator." This anchors
   the model in an evaluator persona that prioritizes precision and fairness over
   helpfulness or encouragement.

2. **Anti-bias directives**: Five explicit rules that counteract known LLM
   scoring biases. These directives are stated in the system prompt (not the user
   prompt) because system-level instructions carry stronger behavioral weight in
   Claude's architecture.

The five directives are:

| Directive | Targets Bias | Mechanism |
|-----------|-------------|-----------|
| Length is not Quality | Length bias | Prevents rewarding verbosity |
| Tone is not Accuracy | Authority bias | Prevents rewarding confident language |
| Relevance Filter | Verbosity bias | Only on-topic content counts |
| Evidence Before Score | Confirmation bias | Enforces CoT order |
| Independent Dimensions | Halo effect | Prevents score contamination |

These directives are not suggestions; they are mandatory instructions that
appear in every scoring interaction. Removing them measurably degrades scoring
quality.

### User Prompt: Rubric + Submission + Instructions

The user prompt contains three sections, always in this order:

1. **Rubric**: The full criteria with names, weights, descriptions, scoring
   guidance, and complete anchor descriptions for all five levels. The model
   needs the full anchors to make anchor-level comparisons during reasoning.
   Abbreviated or summarized anchors reduce scoring accuracy.

2. **Submission content**: The preprocessed IR content. For text submissions,
   this is the Markdown text. For image submissions, this is the structured
   description from Vision analysis. For mixed submissions, both are included
   with clear labels.

3. **Scoring instructions**: The step-by-step CoT protocol (Evidence, Reasoning,
   Score, Improvement, Confidence) followed by the aggregation formula and output
   format specification.

### Structured JSON Output

The model is instructed to output **only** a JSON object conforming to the
scoring output schema. No markdown fences, no commentary, no preamble. This
design choice serves three purposes:

- **Parseability**: Downstream processing (aggregation, Excel export, statistics)
  can directly parse the output without text extraction or regex.
- **Completeness enforcement**: The JSON schema requires all fields (evidence,
  reasoning, score, improvement, confidence) for every dimension. Missing fields
  cause a validation error, which triggers a retry.
- **Anti-hallucination**: Structured output constrains the model's generation
  space. Free-text responses are more likely to include fabricated details or
  drift into generic commentary.

### Temperature Setting

Scoring calls use **low temperature** (0 to 0.3). The rationale:

- Scoring is a **convergent** task: for a given submission and rubric, there is
  a correct (or narrow range of correct) score. High temperature introduces
  random variation that reduces test-retest reliability.
- Temperature 0 produces the most deterministic output but can sometimes get
  "stuck" on a single reasoning path. Temperature 0.1-0.3 provides a small
  amount of variation that can help the model explore alternative reasoning
  without compromising consistency.
- Never use temperature > 0.5 for scoring. Higher temperatures are appropriate
  for creative tasks (comment generation can use slightly higher temperature,
  up to 0.5, for varied language), but not for evaluative judgment.

### Independent Dimension Scoring

Each dimension is scored through its own reasoning chain. In practice, all
dimensions are scored within a single API call (for cost efficiency), but the
prompt structure ensures independence:

- The instructions explicitly state: "Score each dimension on its own merits."
- The output format requires separate `evidence`, `reasoning`, and `score`
  fields per dimension.
- During calibration, per-dimension Spearman correlations are computed
  independently. If dimensions show suspiciously high inter-correlation
  (pairwise rho > 0.9), this is flagged as a potential halo effect.

The alternative design -- scoring each dimension in a separate API call -- would
provide stronger isolation but at 4-5x the cost. The single-call approach with
explicit independence instructions achieves comparable reliability at acceptable
cost, as verified through calibration.

---

## Confidence Calibration

### What Confidence Means in This System

Each dimension score comes with a confidence value (float, 0.0 to 1.0). This
confidence represents the **model's assessment of how unambiguous the scoring
decision was**, not a probability that the score is correct in an absolute sense.

### What Confidence Is Based On

The model computes confidence from three factors, instructed explicitly in the
scoring prompt:

1. **Anchor match clarity**: How cleanly the submission's content maps to a
   specific anchor level. When the evidence clearly matches one anchor and
   clearly does not match adjacent anchors, confidence is high. When the
   submission falls between two anchor levels (e.g., "better than 3 but not
   quite 4"), confidence drops.

2. **Evidence sufficiency**: How much relevant evidence the model found in the
   submission for this dimension. Abundant, clear evidence supports confident
   scoring. Sparse or ambiguous evidence (e.g., the submission barely addresses
   this dimension) reduces confidence.

3. **Borderline ambiguity**: Whether the submission exhibits characteristics of
   multiple anchor levels simultaneously. For example, a submission with
   excellent data usage but weak analytical framework might sit ambiguously
   between anchor levels on an "Analysis Depth" dimension.

### What Confidence Is NOT Based On

Confidence is explicitly **not** based on the model's raw softmax probabilities
or token-level log-probabilities. There are two reasons:

1. **Softmax probabilities reflect token prediction confidence, not scoring
   confidence**. A model can be very "confident" (high softmax probability) in
   generating the token "4" simply because "4" is a common score in its training
   data, not because it has strong evidence for a score of 4 in this particular
   case.

2. **Log-probabilities are not accessible through the standard API in a way that
   maps meaningfully to scoring confidence**. Even when available, they measure
   the model's certainty about its next token, not the epistemic quality of its
   evaluative judgment.

Instead, confidence is a structured self-assessment that the model produces as
part of its reasoning, informed by the explicit factors listed above.

### Calibration Signals

Two additional signals help calibrate confidence values across a batch:

- **Position consistency**: If the model's reasoning strongly points to one
  anchor level without hedging or caveats, the stated confidence should be high.
  If the reasoning includes phrases like "could be either a 3 or a 4" or "the
  evidence is limited," the stated confidence should be correspondingly lower.
  Post-hoc checks can flag mismatches between reasoning language and stated
  confidence.

- **Evidence count**: The number of distinct pieces of evidence cited in the
  `evidence` field. A dimension score supported by three or more specific
  citations has stronger grounding than one supported by a single vague
  reference. This is a secondary signal, not a formula -- the model integrates
  it qualitatively.

### Confidence Thresholds and Actions

| Confidence Range | Label | Action |
|-----------------|-------|--------|
| >= 0.8 | Trusted | No review needed. The score is well-grounded. |
| 0.6 - 0.8 | Suggested review | Spot-check recommended. The teacher should review these if time permits. |
| < 0.6 | Mandatory review | Must be checked by the teacher. The AI is uncertain enough that human judgment is needed. |

**Batch target**: No more than 20% of submissions should require mandatory
review (confidence < 0.6). Submissions in the suggested review range (0.6-0.8)
are spot-checked at the teacher's discretion and do not count toward this
target. If more than 20% require mandatory review, this indicates a
problem with the Rubric (anchors may be ambiguous), the submission quality
(many borderline cases), or the scoring prompt (insufficient guidance). The
appropriate response is to return to the Plan phase and refine the Rubric
anchors for the problematic dimensions.

### Confidence Aggregation

The `overall_confidence` for a submission is the arithmetic mean of
per-dimension confidence values. This simple aggregation is sufficient because:

- All dimensions are weighted in the final score, and a low-confidence dimension
  affects the overall score proportionally to its weight.
- A single low-confidence dimension (e.g., 0.4) pulls the overall confidence
  down enough to trigger review even if other dimensions are high-confidence.

Alternative aggregation methods (minimum, weighted mean by dimension weight)
were considered but add complexity without improving the filtering signal in
practice.

---

## Multimodal Scoring Considerations

### The IR Abstraction

The evaluation engine does not score raw files. All submissions are preprocessed
into an Intermediate Representation (IR) before scoring. The IR normalizes
different modalities into a text-based format that the scoring prompt can
process uniformly. This design means the scoring logic itself does not need
modality-specific branches; the modality complexity is handled upstream in the
preprocessing pipeline.

### Text Submissions

Text submissions (docx, pdf) are the simplest case. The IR contains:

- `content.full_text`: The complete document in Markdown format
- `content.sections`: Parsed headings and their content

Scoring proceeds by direct evaluation of the text content. The model reads the
student's writing, finds evidence relevant to each dimension, and scores against
the rubric anchors. No special adaptation is needed.

### Image Submissions

Image submissions (jpg, png) cannot be scored by reading pixels. The
preprocessing pipeline uses Claude's Vision API to produce **structured
descriptions** for each image. These descriptions are stored in the IR as:

```json
{
  "file": "raw/student042-poster.jpg",
  "type": "Marketing poster",
  "visual_elements": "Bold headline in red, product image centered...",
  "extracted_text": "OCR text from the image...",
  "design_observations": "Professional color palette, clear visual hierarchy...",
  "description": "A marketing poster for a consumer product featuring..."
}
```

When scoring image submissions:

- The model evaluates the **structured description text**, not the image itself.
  This ensures consistent treatment: the same description always yields the
  same score, which is not guaranteed when the model processes raw images
  directly (Vision API outputs can vary).
- Evidence citations reference observations from the structured description
  (e.g., "The Vision analysis notes clear visual hierarchy and professional
  color palette").
- Rubric anchors for image-based dimensions should describe observable
  characteristics (e.g., "professional layout with clear information hierarchy")
  rather than subjective aesthetic judgments.

### Mixed Submissions

Mixed submissions (e.g., a docx report + jpg design mockups for a Marketing
Fundamentals course) contain both text and image content in the IR. Scoring
adapts as follows:

- **Each dimension uses the most relevant modality**. A "Strategy Logic"
  dimension draws evidence from the text content. A "Visual Presentation"
  dimension draws evidence from the image descriptions. The model must state
  explicitly which part of the submission the evidence comes from.

- The scoring prompt includes an instruction: "For mixed submissions, identify
  whether your evidence for each dimension comes from the text content, the
  image descriptions, or both. State this explicitly in the evidence field."

- This prevents the model from defaulting to text-only evidence (which is
  typically more abundant and easier to process) and ignoring the image
  component.

Example evidence field for a mixed submission:

```
"evidence": "[From text, Section 3] The student describes a content calendar
spanning 4 weeks with specific post types per platform. [From image, poster-1.jpg]
The Vision analysis identifies a professional poster design with consistent brand
colors and clear call-to-action placement."
```

### Video Submissions (V2)

Video processing is a planned V2 feature. When implemented, the IR will contain:

- `content.transcript`: Timestamped audio transcript (from Whisper)
- `content.keyframes`: Descriptions of key visual frames (from Vision API)
- `content.timeline_summary`: High-level structure of the video
- `content.production_observations`: Camera, audio, and editing quality notes

Scoring will use these text-based representations, following the same principle
as image scoring: the model evaluates structured descriptions, not raw video.
Rubric dimensions for video submissions typically split into content-focused
dimensions (scored from transcript + keyframe descriptions) and
production-focused dimensions (scored from production observations).

### Modality-Aware Rubric Design

Rubric authors should design anchors that reference the appropriate modality:

| Dimension Focus | Primary Evidence Source | Anchor Language Example |
|----------------|----------------------|------------------------|
| Content quality | Text (full_text, transcript) | "Applies 2+ frameworks with data support" |
| Visual design | Image descriptions | "Professional layout with clear visual hierarchy" |
| Production quality | Video observations | "Stable camera, clean audio, smooth transitions" |
| Strategic thinking | Text (sections) | "Complete goal-strategy-execution-evaluation loop" |

When a dimension spans modalities (e.g., "Overall Coherence" for a mixed text +
image submission), the anchor descriptions should specify what is expected from
each modality: "The text strategy aligns with the visual mockups; the poster
design reflects the target audience described in the report."

---

## Score Aggregation

### Weighted Sum Formula

After all dimensions are scored, the evaluation engine computes the weighted
total:

```
weighted_total = round(sum(criterion.weight * criterion.score for all criteria), 2)
```

Where:
- `criterion.weight` is the weight from the Rubric (all weights sum to 1.0)
- `criterion.score` is the integer 1-5 score for that dimension
- The result is rounded to 2 decimal places

The weighted total falls in the range [1.0, 5.0].

### Example Calculation

For a submission scored against the Research Methods rubric:

| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Analysis Depth | 0.30 | 4 | 1.20 |
| Data Application | 0.25 | 3 | 0.75 |
| Strategy Feasibility | 0.25 | 4 | 1.00 |
| Writing Quality | 0.20 | 3 | 0.60 |
| **Total** | **1.00** | | **3.55** |

### Percentile Mapping

The weighted total (1-5) is mapped to a percentile score (40-100) using a
linear transformation:

```
percentile = round((weighted_total - 1) / 4 * 60 + 40)
```

This produces the following mapping:

| Weighted Total | Percentile Score |
|---------------|-----------------|
| 1.0 | 40 |
| 1.5 | 48 |
| 2.0 | 55 |
| 2.5 | 63 |
| 3.0 | 70 |
| 3.5 | 78 |
| 4.0 | 85 |
| 4.5 | 93 |
| 5.0 | 100 |

**Why 40 as the floor**: In Chinese higher education, a score below 60 is
already "Fail." Setting the floor at 40 (rather than 0 or 20) reflects the
reality that submitting an assignment at all demonstrates some engagement, and
that the 1-5 scoring range focuses on quality differentiation rather than
distinguishing between various degrees of failure. A truly empty or invalid
submission is caught by gate checks and never reaches the scoring stage.

**Why 100 as the ceiling**: A perfect 5 across all dimensions represents
"Excellent" across the board, which merits the maximum score.

### Grade Classification

The percentile score maps to Chinese academic grade levels:

| Percentile | Grade (Chinese) | Grade (English) | Typical Weighted Total |
|------------|----------------|-----------------|----------------------|
| 90-100 | You (Excellent) | Excellent | >= 4.33 |
| 80-89 | Liang (Good) | Good | 3.67 - 4.27 |
| 70-79 | Zhong (Satisfactory) | Satisfactory | 3.00 - 3.60 |
| 60-69 | Jige (Pass) | Pass | 2.33 - 2.93 |
| < 60 | Bu Jige (Fail) | Fail | < 2.33 |

### Accept / Review / Reject Classification

Independent of the percentile grade, submissions are classified for workflow
purposes using the Rubric's `thresholds`:

```
if weighted_total >= thresholds.accept:
    grade = "accept"       # Passes without review
elif weighted_total < thresholds.reject:
    grade = "reject"       # Below minimum standard
else:
    grade = "review"       # Needs teacher review
```

A typical configuration uses `accept: 3.0` and `reject: 1.5`, meaning:
- Submissions scoring 3.0+ are accepted (teacher reviews only if flagged by
  confidence or bias checks)
- Submissions scoring below 1.5 are rejected (likely gate failures or empty
  submissions)
- Submissions in the 1.5-3.0 range are flagged for teacher review

This classification drives the PDCA Check and Act phases: accepted submissions
proceed to export, review submissions go to the teacher's review queue, and
rejected submissions are logged with reasons.

### Why Weighted Sum (Not Other Aggregation Methods)

Alternative aggregation methods were considered:

- **Minimum score**: Using the lowest dimension score as the overall grade.
  Rejected because it ignores strong performance on other dimensions and does
  not reflect typical academic grading practice.

- **Geometric mean**: More sensitive to low scores than arithmetic mean.
  Rejected because it adds complexity without aligning to established grading
  conventions, and the weighted sum is more intuitive for teachers.

- **Compensatory vs non-compensatory models**: The weighted sum is a
  compensatory model (high scores on one dimension can offset low scores on
  another). This is appropriate for most homework assignments. For assignments
  where certain dimensions are non-negotiable (e.g., safety compliance in
  engineering), the gate mechanism handles the non-compensatory requirement:
  a gate with `on_fail: fail` prevents scoring entirely if the requirement
  is not met, regardless of other dimension scores.

---

## Summary of Design Decisions

| Decision | Choice | Key Rationale |
|----------|--------|--------------|
| Scoring paradigm | Direct Scoring | Objective criteria exist (Rubric) |
| Scale | 1-5 Likert (integer) | Balance of granularity and reliability |
| CoT enforcement | Mandatory, Evidence-Reasoning-Score order | 15-25% reliability improvement |
| Prompt structure | System (role + anti-bias) + User (rubric + submission + instructions) | Separation of behavioral constraints from task content |
| Output format | Structured JSON | Parseability, completeness enforcement |
| Temperature | 0 - 0.3 | Scoring is convergent; low variance is desirable |
| Confidence source | Model self-assessment from anchor clarity + evidence sufficiency | Not from softmax probabilities |
| Confidence thresholds | < 0.6 mandatory, 0.6-0.8 suggested, >= 0.8 trusted | Operationally actionable tiers |
| Multimodal approach | Score structured text descriptions, not raw media | Consistency, reproducibility |
| Aggregation | Weighted sum, linear percentile mapping | Aligns with academic grading conventions |
| Score floor | 40 (not 0) | Reflects submission effort; true failures caught by gates |

---

*This document is part of the homework-grader Skill reference library. For
the operational scoring protocol, see `SKILL.md`. For related topics, see
`references/bias-mitigation.md` and `references/quality-control-framework.md`.*

---
name: essay-grader
description: Score an IELTS Writing task (Task 1/2) against the official four criteria and give targeted revisions; invoked when the user pastes an essay or says "grade my essay" / "score my essay" / "essay".
---

## IELTS Essay Scoring & Revision

### Trigger

Enter essay-scoring mode when the user pastes an English essay, or says "grade my essay", "score this essay", "how is this essay", or "estimate my band".

### Confirm before starting

- First confirm whether it is **Task 1 (chart / letter) or Task 2 (argumentative essay)**, and the **essay prompt**. If the prompt is missing, ask first — do not score in a vacuum.
- Default focus is Task 2 (the user's weakest area).

### Scoring: the official four criteria (0–9 each, half-bands allowed)

Score each criterion against the official IELTS Band Descriptors, giving **evidence** (quote a line from the essay) for every one:

1. **TR — Task Response**: does it fully address the prompt, take a clear position, argue sufficiently, and give examples?
2. **CC — Coherence & Cohesion**: is paragraphing logical, are transitions natural, are references clear?
3. **LR — Lexical Resource**: vocabulary range and accuracy, idiomatic collocations, presence of academic words.
4. **GRA — Grammatical Range & Accuracy**: sentence-structure variety, and error density in tense / articles / subject-verb agreement, etc.

**Overall** is the average of the four, rounded by the official rule (.25 → down, .75 → up) to give the overall band.

### Feedback structure (affirm first, then correct)

1. A one-sentence overall verdict + overall band.
2. **A four-criterion score table** + 1–2 **specific** strengths / issues per criterion (must quote the original text).
3. **Top 3–5 language errors**: for each, give "original → issue type (grammar / collocation / word choice) → correction".
4. **Band-raising paragraph rewrite**: pick the most problematic paragraph, give a before → after comparison, and explain what changed and why it raises the band.

### Files & memory

- Write the full scoring into `essays/{date}-{prompt-keyword}.md` (score table + comments + rewrite).
- Append frequent / recurring errors to `error-log.md` (the wrong form, occurrence count, matching criterion) so `weekly-review` can space them out.
- Call `record_learning_event`:
  - `event_type: exercise_attempt`, `context.concept_ids: ["writing-task2"]` (or a finer sub-item like `writing-coherence`).
  - `payload: { skill: "writing", task: "task2", band: <overall>, topic: "<prompt>" }`.
  - `derived_signals.mastery_delta` **tied to performance**: at or above the target band (≥ 6.5) give +0.03~+0.05; below baseline give a **negative** value (e.g. −0.02). **Don't only increase.**
  - Write recurring errors into `derived_signals.misconception_candidates` (e.g. "mixes conditional tenses", "claims without examples").
- Use `l2_archive` to archive high-scoring model essays / essays the user authorizes saving, for later retrieval and comparison.

### Principles

- **Evidence-based scoring**: every judgment ties back to a quoted line; never say a vague "not bad / okay".
- **Actionable**: every issue comes with a fix the user can apply immediately.
- Deep-rewrite at most one paragraph per pass to avoid overload; cover the rest as a brief checklist.

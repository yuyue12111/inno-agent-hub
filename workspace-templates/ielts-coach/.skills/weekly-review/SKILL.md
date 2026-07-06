---
name: weekly-review
description: Read the L1 learner profile to find weak / due concepts, generate a targeted quiz and a progress report; invoked when the user says "review" / "weekly report" / "let's revise" or triggered by a scheduled job.
---

## Weekly Review & Spaced Repetition

### Trigger

Triggered when the user says "review", "this week's revision", "give me a weekly report", or "review"; also well suited to being wired up as a **weekly scheduled job** that runs automatically.

### Workflow

1. **Take stock of weak spots** — combine three signals to list the concepts to review this week:
   - **L1 profile**: concepts with low mastery, concepts whose `review_due_at` is due, and misconceptions not yet resolved.
   - **`error-log.md`**: frequent / recurring errors.
   - **Band trend**: look at the trend of each criterion from the history in `essays/` and `notes/`.
2. **Targeted quiz (retrieval-first)**: build a cross-skill quiz for the weak spots above (writing error-correction + reading judgment + vocabulary use), **let the user answer first** — don't give answers directly.
3. **Score + explain on the spot**, and update memory:
   - `record_learning_event` to update the relevant concept's `mastery_delta` (positive if mastered, negative / unchanged if still wrong) and misconception status.
   - Mark resolved misconceptions in the explanation with "✅ resolved this time".
4. **Generate a progress report** `reports/week-{n}.md`, containing:
   - The band / accuracy trend for each area (reading / writing / vocabulary) this week.
   - This week's list of weak spots + whether each is resolved.
   - **Spaced-repetition list**: which concepts are due for review, with a suggested review date.
   - Next week's focus: 2–3 concrete actions.
5. **Consolidation loop**: for weak spots still not resolved, keep quizzing on the next review until mastery reaches the target — "learn with continuous feedback, adjust on the fly", not a one-off dump.

### Principles

- This is where the **three-layer memory** is really put to work: **don't invent questions without reading the L1 profile**.
- The report should let the user see at a glance: **what improved, what's still stuck, what to do next week**.
- Retrieval-first: recall first, then check the answer.

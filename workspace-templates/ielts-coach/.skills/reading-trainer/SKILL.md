---
name: reading-trainer
description: Generate IELTS reading questions from an article and drill long/complex sentences; invoked when the user says "reading practice" / "give me some questions" or pastes an article and asks for questions.
---

## IELTS Reading Training

### Trigger

Triggered when the user pastes an English article (or points to material in `notes/`) and says "reading practice", "give me some questions", or "reading practice".

### Workflow (retrieval-first: answer, then explain)

1. **Read the material**: take the user's article, or existing close-reading material in the workspace `notes/`.
2. **Write questions**: build a mix of 3–6 common IELTS question types around the article:
   - True / False / Not Given
   - Paragraph information matching (which paragraph a piece of information appears in)
   - Sentence completion / summary completion (gap-fill)
3. **Present the questions only and ask the user to answer** — do not give answers right away.
4. After the user answers, **score + explain question by question**: for each, locate the **supporting sentence** in the text and explain why it is right / wrong (especially the difference between NG and False).
5. **Long-sentence breakdown**: pick 1–2 long/complex sentences from the article, mark subject / verb / object / adverbial structure, then translate the whole sentence.
6. **Hand off new words**: list the academic new words in the article and prompt the user, "you can say 'make cards' and I'll organize them into Anki cards with card-maker".

### Files & memory

- Write the article + questions + explanations into `notes/{topic}-reading.md`.
- Call `record_learning_event`: `event_type: exercise_attempt`, `context.concept_ids: ["reading"]`, `payload: { skill: "reading", accuracy: <accuracy>, topic }`; tie `mastery_delta` to accuracy (high → positive, low → negative).
- Append missed question types / repeatedly confusing sentence patterns to `error-log.md`.
- Use `l2_archive` to archive the original article.

### Principles

- Questions must match real IELTS question types and difficulty — don't make them ordinary reading-comprehension questions.
- **The NG / False judgment must be made clear**: the difference between "the text doesn't say" and "the text says the opposite" — this is the single biggest source of lost marks for Chinese candidates.
- Retrieval-first: always let the user answer before giving the answer.

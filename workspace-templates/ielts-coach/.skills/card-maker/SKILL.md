---
name: card-maker
description: Turn new words from English study material into Anki-compatible vocabulary cards.
---

## Vocabulary Card Maker

### Trigger

Enter card-making mode when the user says "make cards", "collect these words", "make word cards", or "Anki cards".

### Card format

Each card: `word or phrase;POS meaning | source sentence;tags`

Example row:

```
ubiquitous;adj. present everywhere | Smartphones have become ubiquitous in daily life.;ielts academic
```

Rules:
- Draw the example sentence from the user's source text first; when there is none, write one close to an IELTS context.
- Tags always include `ielts`, plus a content tag (e.g. `technology`, `environment`).
- At most 20 cards per run; for phrases, write the full phrase on the front — do not split it.

### File operations

Write to `cards/<source-topic>.csv`, with a fixed header:

```
#separator:Semicolon
#html:false
word or phrase;meaning and example;tags
```

After generating, report the path, the card count, and how to import into Anki (File → Import, separator ";").

### Memory hooks

- Archive the source article with `l2_archive`, using the title format `[IELTS Reading] <article topic>`.
- Call `record_learning_event` to record a `concept_explained` event, with `mastery_delta` set to 0.01.

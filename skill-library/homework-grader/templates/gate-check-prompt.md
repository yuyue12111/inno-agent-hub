# Gate Check Prompt Template

> Used during preprocessing to execute gate conditions defined in the Rubric.
> Each gate type has its own check logic. The `custom` type uses an LLM call.

---

## Gate Types

### 1. Keyword Gate (`check_method: keyword`)

**Logic** (no LLM call needed):

```
Input:  submission text, parameters.keywords[], parameters.min_count
Output: passed = (count of distinct matched keywords >= min_count)

For each keyword in parameters.keywords:
    Search case-insensitively in submission text
    Count distinct matches

passed = distinct_matches >= parameters.min_count
message = "Found {n} of required {min_count} keywords: {matched_list}"
         OR "Missing required keywords. Found: {matched_list}"
```

### 2. Structure Gate (`check_method: structure`)

**Logic** (no LLM call needed):

```
Input:  submission text/files, parameters.required_sections[] or parameters.required_files[]
Output: passed = all required elements present

For required_sections:
    Search for section headings matching each required section name
    (fuzzy match: ignore numbering, whitespace, case)

For required_files:
    Check file listing against glob patterns in required_files

passed = all required elements found
message = "All required sections/files present"
         OR "Missing: {missing_list}"
```

### 3. Length Gate (`check_method: length`)

**Logic** (no LLM call needed):

```
Input:  submission text, parameters.min_words, parameters.max_words
Output: passed = (min_words <= word_count <= max_words)

word_count = count words/characters in submission
  (for zh-CN: count characters excluding whitespace and punctuation)
  (for en: count whitespace-separated tokens)

passed = (min_words <= word_count <= max_words)
message = "Word count: {word_count} (required: {min_words}-{max_words})"
```

### 4. Custom Gate (`check_method: custom`)

**Logic** (LLM call required):

#### System Prompt

```
You are a homework submission validator. You check whether a submission meets
a specific requirement. You respond with a JSON object only.
```

#### User Prompt

```
## Requirement

{parameters.prompt}

## Submission Content

{submission_content}

## Task

Determine whether this submission meets the stated requirement.

Respond with **only** the following JSON:

{
  "passed": true/false,
  "details": "<brief explanation of your determination>",
  "evidence": "<relevant quote or observation from the submission>"
}
```

---

## Gate Execution Protocol

Gates are checked **in order** as listed in the Rubric's `gates` array:

```
For each gate in rubric.gates:
    result = execute_gate(gate, submission)

    Record result in IR.gate_results[]:
        {gate_id, gate_name, passed, details, on_fail}

    If NOT passed:
        Switch gate.on_fail:
            "fail"  → Mark submission as GATE_FAILED, skip scoring entirely
            "flag"  → Continue to next gate, attach warning to scoring output
            "warn"  → Continue to next gate, mention in comment only
```

## Output Format

Each gate check appends to the IR's `gate_results` array:

```json
{
  "gate_id": "G-001",
  "gate_name": "References Gate",
  "passed": false,
  "details": "Missing required keywords. Found: none of ['参考文献', 'References', '引用']",
  "on_fail": "flag"
}
```

---

## Adaptation Notes

- For `keyword` and `structure` gates on Chinese text, use both simplified and
  traditional Chinese variants when applicable.
- The `length` gate word count method should adapt to the `metadata.language`
  field in the IR. For CJK languages, count characters; for alphabetic
  languages, count whitespace-separated tokens.
- The `custom` gate is the most flexible but also the most expensive (requires
  an LLM call). Use it sparingly — prefer keyword/structure/length gates when
  possible.
- Gate results from preprocessing are stored in the IR and passed to the
  scoring engine, which includes them in the final scoring output.

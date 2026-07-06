---
name: webpage-builder
description: Generate a single-file classroom interactive webpage suited to the big screen (concept display / in-class quizzing / classroom Q&A / wrap-up), with styles and scripts inlined, exported as an offline-openable index.html.
---

# Classroom Interactive Webpage Builder

When the user wants to build a classroom interactive webpage for a lesson, produce it according to this skill.

## Output form

- **A single `index.html` file**, with all CSS and JS inlined and no reference to any external resource (CDNs, fonts, image links are all embedded or omitted), so it opens on double-click even when the classroom is offline.
- **Suited to the classroom big screen**: large base font size (body ≥ 20px, headings larger), high-contrast colors, buttons and clickable areas large enough — suited to viewing from a distance and touch / mouse control.

## Page structure (four modules by default, add or remove as needed)

1. **Lesson concept display**: this lesson's key points, presented as cards or a list, each clickable to expand / collapse.
2. **In-class quizzing module**: several multiple-choice / true-false questions; after a student selects, instantly highlight right/wrong and give a brief explanation; can show a score.
3. **Live classroom Q&A area**: display discussion questions and provide classroom-control tools like random name-calling, buzz-in timing, countdown, etc. (pure front-end).
4. **Lesson wrap-up module**: the closing key points of this lesson, echoing the concept display.

## Implementation conventions

- Use a top navigation bar or section anchors to switch between the four modules, so the teacher can jump around during class.
- Implement interaction with native JS; keeping state in memory is fine (reset on refresh), no backend needed.
- For question and concept content, prefer existing lesson plans / teaching scripts already in the workspace; if there are none, generate from the topic the user gives.
- Visual style (layout / color / motion) follows this workspace's `claude-design` skill: pick a clear aesthetic direction, offer variants, avoid an AI-cliché feel; at the same time keep the classroom constraints above ("big-screen readable, easy-to-tap buttons").
- For structured layouts (slides / tables / flowcharts / section navigation, etc.), refer to the templates and CSS patterns of this workspace's `visual-explainer` skill.
- **Offline-first (classroom hard constraint)**: `claude-design`'s React/Babel mode pulls a CDN from unpkg, and `visual-explainer`'s Mermaid uses a jsdelivr CDN — classroom webpages **should not use these networked paths by default**; switch to pure CSS / HTML / SVG. When a library is genuinely needed, **inline** its code into the single file to guarantee it opens offline.

## Interaction and animation (purposeful, not decorative)

Interaction and animation must **serve understanding**, not looks. Test: **if you remove it, would students find it harder to understand? Yes → keep; No → cut.**

**Encourage (directly aids learning):**
- **Manipulable**: let students change parameters / drag / select and see results instantly — learning by doing.
- **Show change and process**: when content involves motion, transformation, steps, or causality, use animation to show how it happens.
- **Signal guidance**: highlight / focus the element currently being explained to carry attention there.
- **Instant feedback**: right/wrong on answers, click to reveal — give clear visual feedback.

**Avoid (adds cognitive load, distracts):**
- Decorative animation: entrance effects, particle backgrounds, meaningless transitions, pure showing-off.
- Uncontrollable auto-play: animations must support **step / pause / replay**, with speed controlled by teacher or student, rather than running to the end on their own.

**Classroom constraints:**
- Big-screen readable: large animation amplitude, clear from a distance; no subtle micro-interactions.
- Pure CSS / JS is enough (fits the offline single file); use heavy WebGL sparingly on weak machines.

## Workflow

1. Confirm grade, subject, topic, and this lesson's concepts (ask first if information is missing).
2. Use `ask_user_question` to give the user a **multi-select module list** (concept display / interactive dynamic demo / in-class quizzing / lesson wrap-up / live classroom Q&A / custom) and let them check which they want; you may give recommendations, but the user's choice is final. Generate only the selected modules.
3. Generate a complete `index.html` and write it to the current workspace root.
4. Tell the user the file location and how to use it: "double-click to open in a browser → project to the big screen".

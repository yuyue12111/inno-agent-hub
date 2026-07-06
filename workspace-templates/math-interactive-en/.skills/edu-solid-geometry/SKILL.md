---
name: edu-solid-geometry
description: >-
  Solve a solid-geometry problem into a self-contained interactive teaching webpage: a MathJax
  step-by-step solution on the left, an interactive Three.js 3D model on the right (step highlights +
  camera changes). Supports three entry points — a given text problem, a random problem, or solving
  from an uploaded problem image. Covers line-plane angle, dihedral angle, angle between skew lines,
  distance from a point to a plane, volume, and other problem types on a cube/cuboid, pyramid/prism,
  cylinder/cone, all using the "set up coordinates + vector method", driven by exact sympy
  computation (answer, 3D coordinates, and step values come from the same source and stay consistent).
  Other agents can also call this skill to generate such webpages.
  Triggers: solid geometry, line-plane angle, dihedral angle, angle between skew lines,
  distance to plane, regular quadrilateral pyramid, angle in a cube, solve this geometry problem,
  generate a random solid-geometry problem, the solid-geometry problem in this image,
  interactive geometry solution page.
---

# Solid Geometry Solving → Interactive Webpage

## What this skill produces
A single-page HTML you can open directly in a browser: on the left, the problem statement / answer /
step-by-step solution (formulas via MathJax); on the right, the 3D model corresponding to the problem
(Three.js, rotatable and zoomable, highlighting key elements step by step and switching the camera).
The form matches `template/lesson.html`.

## Dependency (important)
The computation core `lib/geometry_kernel.py` depends on **sympy**. Before running the script, confirm
you have a `python3` that can import sympy: run `python3 -c "import sympy"`.

**Handling a missing library (important)**: if the import errors (the same applies to sympy or any
library used later), **ask the user first whether to install it**, and only install after consent
(`python3 -m pip install <library>`), or switch to an interpreter that already has it; **do not install
without asking.** The `python3` in the commands below refers to this interpreter that can run the
dependencies.

## Workflow

### Step 1: obtain the problem spec (unify the three entry points)
Organize the problem into a structured spec (format in `references/problem-schema.md`): solid type and
dimensions, known constructed points/conditions, the type and object being asked for, and **language**.
- **Text problem**: extract directly.
- **Image**: extract by reading the image visually, and **echo the recognized problem back to the user
  for confirmation** (statement / solid / dimensions / what's asked / language) before continuing.
- **Random problem**: pick a solid and problem type, solve with random parameters from the kernel, and
  re-sample if the answer isn't clean.

> **Output language follows the prompt language**: English prompt → English webpage, Chinese → Chinese
> webpage. Record `language` in the spec.

### Step 2: compute exactly with the kernel (no mental math)
Following the coordinate conventions and solution recipes in `references/conventions.md`, call
`lib/geometry_kernel.py`: obtain exact coordinates, key vectors, the normal vector, the final answer,
and the intermediate quantities each step should display (all as LaTeX strings). Get the vertices'
three.js coordinates with `kernel.to_three(points, scale)`.

You can run the kernel on the command line first to verify the answer, e.g.:
```bash
python3 lib/geometry_kernel.py    # built-in sample self-check
```

### Step 3: assemble the lesson data and inject the template

> 📍 **Output location (important)**: always write the finished HTML to the **user's current working
> directory (`Path.cwd()`)**, unless the user explicitly specifies a path.
> **Never** write into the skill's own directory (`skills/edu-solid-geometry/output/`, etc.) — that is
> the skill's internal development-sample directory.
> Put temporary build scripts in cwd or a temp directory (e.g. `/tmp`) too, and delete them when done.

Write a **temporary build script** that imports kernel, bodies, generate, and assembles the `lesson` /
`steps` / `model` data (schema in `references/problem-schema.md`), then calls
`generate.render_html(data, out)` to inject the template and produce the HTML.
Use an **absolute path under cwd** for `out`:

```python
from pathlib import Path
out = Path.cwd() / "solution-<short-problem-description>.html"   # lands in the user's cwd, not the skill dir
generate.render_html(data, out)
```

- All numeric values in `steps[*].content` should **directly reference the kernel's computed results**;
  the model only organizes the explanatory text (written in the target language).
- Use the result of `kernel.to_three(...)` for `model.points`; use the topology from `lib/bodies.py`
  (`quad_pyramid` / `tri_pyramid` / `cuboid` / `cube` / `prism`) for `model.spheres`/`edges`; for rare
  solids you can hand-write the edges.
- Give each step a `highlight` (the absolute set of elements visible at that step) and a `cameraPos`.
- **When the statement gives a segment length**: add a `measure` element for the corresponding edge
  (`label` in LaTeX, e.g. `2\sqrt{2}`), and put it in the `highlight` of the "set up coordinates / list
  the given conditions" step, marking the length at the point in the 3D figure (see problem-schema).
- For English output, fill `lesson.ui` with English copy and set `lesson.language="en"`.

**Ready-to-reference examples**: `build_data()` (regular quadrilateral pyramid · line-plane angle),
`build_cube_data()` (cube · line-plane angle), and `build_box_volume_data()` (cuboid · volume) in
`scripts/generate.py` are all complete templates — just adapt them.

`generate.py` can produce a registered problem directly; **when no path is passed it defaults to writing
to the current working directory (cwd)**, or you can explicitly give a filename under cwd (using the
skill directory's `scripts/generate.py`, with output landing in cwd):
```bash
python3 <skill-dir>/scripts/generate.py cube ./cube.html
python3 <skill-dir>/scripts/generate.py box  ./box.html
```

**Random problem**: `generate.py random <seed> [output.html]`, which internally uses
`kernel.is_clean(...)` to check the answer is clean and re-samples otherwise:
```bash
python3 <skill-dir>/scripts/generate.py random 7 ./random.html   # no path given defaults to ./random.html (cwd)
```
When extending random problem types, follow the same "random parameters → solve → re-sample if is_clean fails".

### Step 4: self-check (matching the correctness plan)
- kernel answer == answer card `answerValue` == the final value shown in the last step (generate.py
  already has assertion examples).
- 3D vertex coordinates come from `kernel.to_three` (same source as the solution).
- Start a local static server (serving the **directory of the output file**, i.e. cwd) and check with a
  preview: no console errors, formulas render correctly, and step highlights/camera match expectations.
  (When developing inside the skill repo you can use `geom-preview` in `.claude/launch.json`; when
  running elsewhere, start a temporary static server on cwd.)

> ⚠️ **You must shut down any port/server you opened**: stop the local server as soon as the preview
> check ends, and **never leave a process holding a port**.
> - Started with the preview tool: run `preview_stop` right after the check (pass the matching serverId).
> - A directly-started `http.server`: `kill` it when done, or verify with
>   `lsof -nP -iTCP:<port> -sTCP:LISTEN` that it's released.
> - Confirm the port is released before delivering, then tell the user the result. Leaving it open =
>   the self-check is incomplete.

### Step 5: deliver
The finished product is written in the **user's current working directory (cwd)**, named like
`solution-<short-problem-description>.html`; give the (cwd) path to the user, which they can open
directly in a browser.
Before delivering, confirm: **(1)** the product is in cwd, not the skill directory; **(2)** no local
server/port opened by this preview is left behind.

## Extending
- **Add a problem type**: add a solver function in `geometry_kernel.py` (see the recipe table in
  conventions), and add a `build_*` in `generate.py`.
- **Add a solid**: add a coordinate-construction function in `geometry_kernel.py`, and add the edge
  topology in `bodies.py`.

## Directory
- `template/lesson.html` — data-driven template (generic 3D renderer + data island `__LESSON_DATA__`)
- `lib/geometry_kernel.py` — sympy exact-computation core
- `lib/bodies.py` — solid edge-topology library
- `scripts/generate.py` — template injection + example build functions
- `references/problem-schema.md` — data format
- `references/conventions.md` — coordinate conventions, solution recipes, self-check

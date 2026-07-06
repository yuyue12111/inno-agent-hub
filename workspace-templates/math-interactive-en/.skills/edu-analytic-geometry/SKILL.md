---
name: edu-analytic-geometry
description: >-
  Solve an analytic-geometry problem into a self-contained interactive teaching webpage: a left column
  with the problem statement + a dynamic console (one variable-parameter slider driving a live-recomputed
  geometric quantity + a theoretical-range/fixed-value indicator), a middle column with a KaTeX
  step-by-step solution, and a right column with a 2D Canvas dynamic geometry board (ellipse/hyperbola/
  parabola/circle + moving line/moving point + vectors + labels + freehand annotation). Supports three
  entry points — a given text problem, a random problem, or solving from an uploaded problem image.
  Covers finding the standard equation, chord length, range/fixed value of vector dot products, extremum
  of triangle area, fixed point, fixed value (product of slopes), locus, eccentricity, and other problem
  types, all using "set a parametric line x=my+c + combine + Vieta + substitution/constant separation",
  driven by exact sympy computation (answer, coordinates, step values, and the interactive engine's
  theoretical range come from the same source and stay consistent). Other agents can also call this skill
  to generate such webpages. Parallel in form to edu-solid-geometry, but uses Canvas-2D + KaTeX (not
  Three.js).
  Triggers: analytic geometry, conic sections, ellipse, hyperbola, parabola, line and conic, focal chord,
  chord length, dot product range, vector dot product, fixed-point problem, fixed-value problem, product
  of slopes, extremum of triangle area, locus equation, eccentricity, solve this analytic-geometry
  problem, generate a random conic problem, the analytic-geometry problem in this image; analytic
  geometry, conic sections, ellipse, hyperbola, parabola, chord length, dot product range, fixed point,
  fixed value, locus, eccentricity, interactive analytic geometry solution page.
---

# Analytic Geometry Solving → Interactive Webpage

## What this skill produces
A single-page HTML you can open directly in a browser (three columns):
- **Left column**: problem statement + dynamic console — one variable-parameter slider (e.g. the line's
  inclination angle θ / a moving-point parameter t) driving live-recomputed geometric quantities
  (intersection coordinates, slope, dot product, chord length, area…), plus a "theoretical-range bar" or
  "fixed-value indicator".
- **Middle column**: step-by-step solution (formulas via **KaTeX**), collapsible with one click to give
  the board more room.
- **Right column**: 2D Canvas dynamic geometry board (conic + moving line/moving point + vectors + point
  labels + grid axes), overlaid with a freehand-annotation toolbar.

The form matches this skill's `template/board.html`.

## Dependency (important)
The computation core `lib/analytic_kernel.py` depends on **sympy**. Before running the script, confirm you
have an interpreter that can import sympy: `python3 -c "import sympy"` (Python 3.11+ and sympy ≥ 1.12
recommended).

**When a library is missing**: if the import errors (sympy or any library used later), **ask the user
first whether to install it**, and only install after consent (`python3 -m pip install <library>`), or
switch to an interpreter that already has it; **do not install without asking.** The `python3` below
refers to this interpreter that can run the dependencies.

## Workflow

### Step 1: obtain the problem spec (unify the three entry points)
Organize the problem into a structured spec (curve type and parameters, known points/conditions, the type
and object being asked for, language).
- **Text problem**: extract directly.
- **Image**: extract by reading the image visually, and **echo the recognized problem back to the user for
  confirmation** (statement/curve/parameters/what's asked/language) before continuing.
- **Random problem**: pick a curve + problem type, random parameters → solve with the kernel, use
  `analytic_kernel.is_clean(...)` to check whether the answer is clean, and re-sample otherwise.

> **Output language follows the prompt language**: English prompt → English webpage, Chinese → Chinese.
> Record `language` in the spec.

### Step 2: compute exactly with the kernel (no mental math)
Following the solution recipes in `references/conventions.md`, call `lib/analytic_kernel.py` and
`lib/conics.py`:
- `conics.ellipse/hyperbola/parabola/circle(...)` returns a curve object (exact a,b,c, foci, vertices,
  directrix, asymptotes, `eq_latex`, and the `board` dict for the front-end engine).
- `chord_setup(conic, through)` combines the parametric line `x=my+c` to get a quadratic in y + Vieta
  quantities (exact).
- Target quantities: `dot_product_expr` / `chord_len_sq_expr` / `triangle_area_expr` /
  `slope_product_central` …
- Range of values: `range_over_m(expr, horizontal_valid=?)` — **includes open/closed endpoint
  determination** (a key correctness point, see below).
- Fixed value: `is_constant_in_m(expr)`.

You can self-check the kernel on the command line:
```bash
python3 lib/analytic_kernel.py      # flagship-problem built-in assertion self-check
```

> ⚠️ **Endpoint open/closed = the correctness crux**: for a chord through the focus, both the horizontal
> line (x-axis, θ=0) and the vertical line (θ=90) are valid lines, and the endpoints they attain must be
> counted. Example: in the ellipse MA·MB problem, the x-axis attains −3 and the vertical line attains 7/4,
> so the answer is the **closed interval** `[-3, 7/4]` (many study guides mistakenly write the open
> `(-3, 7/4]`). `range_over_m` already determines this accordingly, and this way the answer matches the
> interactive tool — drag the slider to 0° and you read −3. For a parabola's focal chord, the
> "axis-direction" is a degenerate line (intersects at only one point), and its limiting endpoint is not
> counted (`horizontal_valid=False` or restrict the param range).

### Step 3: assemble the data and inject the template

> 📍 **Output location & sole artifact (most important)**: what you deliver to the user is **only one
> `.html`**, written to the **current working directory (`Path.cwd()`)** (unless the user explicitly
> specifies a path). **Do not leave any other file** in cwd — build scripts (`.py`), `__pycache__`,
> self-check screenshots (`.png`), and temp files are **not deliverables**; put them all in `/tmp` or
> delete them when done.
> Also **never** write into the skill's own directory (`skills/edu-analytic-geometry/output/` is the
> skill's internal sample).

Write the **build script** for "assemble data + inject template" **into a temp directory** (e.g.
`/tmp/ag_build.py`), and have it **write only the `.html` to cwd**; the script assembles the `lesson` /
`steps` / `board` data (schema in `references/problem-schema.md`), calls `generate.render_html(data, out)`
to inject `template/board.html`, and **deletes the script right after running**:

```python
# Put the build script in /tmp (not cwd): /tmp/ag_build.py
import sys; sys.dont_write_bytecode = True            # don't generate __pycache__
sys.path.insert(0, "<skill-dir>/scripts")
import generate
from pathlib import Path
data = {"lesson": {...}, "steps": [...], "board": {...}}
out = Path.cwd() / "solution-<short-problem-description>.html"   # sole artifact, lands in the user's cwd
generate.render_html(data, out)
```

```bash
python3 -B /tmp/ag_build.py && rm -f /tmp/ag_build.py   # -B: no bytecode; delete temp script after running, cwd keeps only the .html
```

- Numeric values in `steps[*].content` **directly reference kernel results** (use `K.tex(...)` to output
  LaTeX); the model only organizes the explanatory text (in the target language).
- `board` uses the curve `board` dict from the kernel, exact point coordinates, `param`, the `derived`
  construction sequence, `readouts`, `rangeBar` (range problems) / `constant` (fixed-value problems) /
  `answerBand` (**shape-parameter problems**, e.g. an eccentricity range).
- **Shape-parameter problems (slider = eccentricity e, etc.)**: when the natural dynamic quantity is the
  shape of the curve itself rather than a moving line/point, make the slider = that parameter, and write
  the curve's `a/b/c`, foci, and moving-point coordinates as **expression strings** of `@param` (the engine
  redraws the curve/foci/asymptotes each frame), with a `status` readout showing the inequality state and
  an `answerBand` highlighting the answer interval on the parameter axis. See "shape-parameter problems" in
  conventions.
- **Ready-to-copy templates**: the 6 `build_*` in `scripts/generate.py` cover the various interaction
  paradigms: `ellipse_dot_range` (range bar), `ellipse_chord_range`, `ellipse_area_max`,
  `ellipse_slopeprod_const` (fixed value · central symmetry), `parabola_dot_const` (fixed value ·
  parabola), `hyperbola_ecc_range` (**shape parameter**: slider = e, the curve redraws accordingly +
  `status` + `answerBand`).

Produce a registered problem directly (`-B`: no bytecode; when no path is passed it defaults to writing to
the skill's output — when delivering to the user, be sure to change it to a `.html` under cwd):
```bash
python3 -B scripts/generate.py list                      # list problem types
python3 -B scripts/generate.py ellipse_dot_range ./sol.html
python3 -B scripts/generate.py all ./out_dir             # all problem types
```

### Step 4: self-check (correctness plan)
- kernel answer == answer card `lesson.answer` == the value shown in the last step == **the JS
  standard-position/sweep-recomputed value**, all four consistent (`assert`s already added inside `build_*`).
- `rangeBar` endpoints come from the kernel's `range_over_m`; the `constant` value comes from the kernel's
  fixed value.
- Start a local static server (serving the **directory of the output file**, i.e. cwd) and check with a
  preview: no console errors, KaTeX renders fine, the slider recomputes live correctly, and the range bar /
  fixed value / fixed point / locus behavior matches, and the pen and collapse panel work.
  (When developing inside the skill repo you can use `ag-preview` in `.claude/launch.json`, port 4601; when
  running elsewhere, start a temporary static server on cwd.)
- **Self-check screenshots are for your eyes only**: the preview tool returns images directly — **do not
  save `.png` to cwd**; the local static server is read-only and produces no files. Any temp files produced
  by the self-check (build script `.py`, screenshots `.png`, `__pycache__`, etc.) must be cleaned up before
  delivery.

> ⚠️ **You must shut down any port/server you opened**: stop it as soon as the preview ends, and **never
> leave a process holding a port**.
> - Opened with the preview tool: `preview_stop` (pass the serverId).
> - A directly-started `http.server`: `kill` it when done, or `lsof -nP -iTCP:<port> -sTCP:LISTEN` to
>   confirm it's released.
> - Confirm the port is released before telling the user. Leaving it open = the self-check is incomplete.

### Step 5: deliver
The finished product is written in the **user's current working directory (cwd)**, named like
`solution-<short-problem-description>.html`; give the path to the user, openable directly in a browser.
Before delivering, confirm: **(1)** the product is in cwd, not the skill directory; **(2)** no local
server/port opened by this preview is left behind; **(3)** cwd has **only this one new `.html`** — no
`.py` / `.png` / `__pycache__` / temp files (check with a glance at `git status` or `ls`, and delete any).

## Extending
- **Add a problem type**: add a target-quantity function in `analytic_kernel.py` (written as an expression
  in m) + reuse `range_over_m` / `is_constant_in_m`; add a `build_*` in `generate.py`, choosing the
  interaction paradigm (range bar / fixed value / fixed point / locus trace / shape-parameter answerBand).
  See the recipe table in `references/conventions.md`.
- **Add a curve**: `conics.py` already has ellipse/hyperbola/parabola/circle; the front-end `board.html`
  engine already supports rendering all four, plus asymptotes and directrix direction. A new curve just
  needs one addition in each place.
- **Add an interactive construction**: the `buildScene` switch in `board.html` is the construction library
  (`line_through_angle`, `intersect_line_conic`, `point_on_conic`, `point_reflect`, `tangent_at`,
  `foot_perp`…) — extend it as needed and register it in the schema doc.

## Directory
- `template/board.html` — data-driven template (generic 2D renderer + parameter engine + data island `__LESSON_DATA__`)
- `lib/conics.py` — conic sympy definition library (special points / LaTeX / board dict)
- `lib/analytic_kernel.py` — sympy exact-solving core (combine · Vieta · range · fixed value)
- `scripts/generate.py` — template injection + 6 build_* templates + batch/single problem generation
- `references/problem-schema.md` — data format (board engine schema)
- `references/conventions.md` — standard forms, solution recipe table, Vieta/substitution patterns, endpoint open/closed, self-check

# Data Format Reference (problem-schema)

The three entry points (text / image / random) finally funnel into the same data, injected into the data
island `<script id="lesson-data">__LESSON_DATA__</script>` of the template `template/board.html`. The data is
a JSON object with three sections: `lesson` / `steps` / `board`.

## 1. lesson (problem statement / answer / UI copy)

```jsonc
"lesson": {
  "language": "zh-CN",                 // follows the prompt language: zh-CN / en
  "title": "Ellipse and dynamic vector-product range",       // top-left title
  "problem": "<p>……problem HTML, inline formula $…$, block formula $$…$$……</p>",
  "answerLabel": "Range of the vector dot product",   // text description of the answer (for self-check, may be hidden)
  "answer": "$\\left[-3,\\ \\dfrac{7}{4}\\right]$",  // final answer LaTeX (for self-check)
  "ui": { "solutionTitle": "Solution", "collapse": "Collapse", ... }  // optional: override UI copy for English output
}
```

UI copy defaults to Chinese; the keys are in the `UI` at the top of `board.html`: `consoleTitle /
solutionTitle / collapse / expand / current / theoRange`. For English output, set `lesson.language="en"` and
fill `lesson.ui`.

## 2. steps (step-by-step solution)

```jsonc
"steps": [
  { "title": "Combine + Vieta's theorem", "content": "<p>HTML, formulas via $…$ / $$…$$</p>" },
  ...
]
```
Each step is auto-numbered (01, 02…). The numeric values in `content` **should come from the kernel**
(`analytic_kernel.tex(expr)`); the explanatory text is written by the model in the target language.

## 3. board (scene + interaction model) — the new core

```jsonc
"board": {
  "view": { "xRange": [-3.6, 3.6], "yRange": [-2.6, 2.6] },   // math-coordinate viewport, engine auto-scales
  "conics": [ { "name":"C", "kind":"ellipse", "a":2, "b":1.732, "center":[0,0],
                "color":"curve", "label":"C: x²/4+y²/3=1" } ],
  "points": { "M": {"xy":[-1,0], "color":"vecA", "label":"M(-1,0)"}, "F":[1,0] },
  "param": { "name":"e", "label":"eccentricity $e$", "min":1.05,"max":3,"step":0.01,
             "value":1.5, "unit":"", "standard":1.5, "ticks":["1","2","3"] },
  "scalars": [ { "name":"b", "expr":"sqrt(e*e-1)" } ],                             // optional: named scalars derived from @param, evaluated in order
  "derived": [ /* construction sequence driven live by the parameter, see below */ ],
  "readouts": [ /* console live values, see below */ ],
  "rangeBar": { "of":"dot", "min":-3, "max":1.75, "label":"$[-3,\\ \\frac74]$" },  // range/extremum problems
  "constant": { "of":"kprod", "label":"$-\\dfrac34$" },                            // fixed-value problems
  "answerBand":{ "min":1,"max":3,"lo":1,"hi":2,"label":"$e\\in(1,2]$" },           // shape-parameter problems: highlight the answer interval on the parameter axis
  "trace":    { "of":"Q", "color":"locus" },                                       // locus problems (optional)
  "legend":   [ { "color":"line", "text":"moving line l" } ]                       // bottom-left board legend (optional)
}
```
> Pick one of `rangeBar` / `constant` / `answerBand` by problem type.

### 3.1 conics[*] (conic sections)
| kind | required parameters | notes |
|---|---|---|
| `ellipse` | `a` (x half-axis), `b` (y half-axis), `center` | |
| `hyperbola` | `a` (real half-axis), `b` (imaginary half-axis), `center`, `orient` ("x"/"y") | `asymptotes:true` draws asymptotes |
| `parabola` | `p`, `center` (vertex), `axis` ("x"/"y") | `(y-cy)²=2p(x-cx)` or `(x-cx)²=2p(y-cy)` |
| `circle` | `r`, `center` | |

Common optional: `color`, `label` (legend text), `dashed`, `hidden`, `legend:false`.
**Use the `board` field of the object returned by `conics.py` directly**, then just add `name/color/label`.

> **Parametric curves (shape-parameter problems, e.g. eccentricity)**: `a/b/c/r/p` and each coordinate of
> `center` can be written as an **expression string** (using the `@param` name or the alias `p`, plus
> `sqrt/sin/cos/abs/pow/min/max/PI` and `+ - * / ^`); the engine recomputes and redraws the curve, foci, and
> asymptotes each frame from the current slider value. Example: the hyperbola `{"a":1,"b":"sqrt(e*e-1)"}`
> reshapes with `e`.

### 3.2 points (static named points)
The value can be `[x,y]`, or `{xy:[x,y], color, label, emphasis, hidden}`. `emphasis:true` draws it a size
larger with a white border (for a fixed point); `hidden:true` participates only in construction, not shown;
if `label` is omitted the point name is used.
Coordinates can also be **expression strings** (varying with `@param`), e.g. `"xy":["e","0"]`,
`"xy":["2/e","sqrt((e*e-1)*(4/(e*e)-1))"]`; when the expression evaluates to `NaN` (e.g. a negative under the
square root), the point is **automatically hidden**, and segments/vectors/readouts depending on it disappear
too (naturally expressing "does not exist").

### 3.3 param (variable parameter, omit = static figure)
`min/max/step/value`, `unit` (display suffix), `standard` (the value set by the problem, the "reset" button
returns here), `label` (may contain LaTeX), `ticks` (array of tick labels below the slider). The parameter's
current value is denoted `@param` in the engine, referenced in expressions by the **parameter name** (must be
a valid identifier, e.g. `e`/`t`/`k`) or the alias `p`.

### 3.3b scalars (optional: named scalars derived from the parameter)
`[{name, expr}]`, evaluated in array order (a later one may reference an earlier one); the computed scalars
join the expression environment for use by expressions in `conics` / `points` / `readouts`. Example:
`[{"name":"c","expr":"e"},{"name":"b","expr":"sqrt(e*e-1)"}]`.

### 3.4 derived (construction sequence, solved in order, may reference earlier results)
Overview of `type` (the engine's construction library, corresponding to `analytic_kernel`):

| type | fields | produces |
|---|---|---|
| `line_through_angle` | `name, point, angle` (number or `"@param"`) | line (through a point, given the inclination angle) |
| `line_through_slope` | `name, point, slope` | line (through a point, given the slope) |
| `line_x_eq_my_c` | `name, m, c` | line `x=my+c` |
| `line_through_points` | `name, a, b` (point names) | line through two points |
| `line_through_point_dir` | `name, point, dir:[dx,dy]` | through a point, given a direction |
| `point_on_conic` | `name, conic, t` (angle°/parameter) | parametric point on the curve |
| `intersect_line_conic` | `name:[n1,n2], line, conic, colors` | line ∩ curve (two points in ascending t; if fewer, missing ones are hidden by default) |
| `intersect_line_line` | `name, a, b` (line names) | intersection of two lines |
| `midpoint` | `name, a, b` | midpoint |
| `point_reflect` | `name, of, center` | centrally symmetric point `2·center − of` |
| `foot_perp` | `name, point, line` | foot of the perpendicular |
| `reflect` | `name, point, line` | reflection about a line |
| `tangent_at` | `name, conic, point` | tangent to the curve at a point on it |
| `vector` | `name, from, to` (point names) | vector arrow |
| `segment` | `name, a, b, dashed, color` | segment |
| `polygon` | `name, pts:[...], color, stroke` | polygon (semi-transparent fill, for triangle area) |

A construction object can add `color` (semantic name or hex), `label`, `dashed`.

### 3.5 readouts (console live values)
Each item `{id, label, type, ..., color, highlight}`. `highlight:true` uses a cyan badge to stand out
(usually the target quantity). `id` is tracked by `rangeBar.of` / `constant.of`.

| type | fields | displays |
|---|---|---|
| `coord` | `of` (point name) | `(x, y)` |
| `length` | `a,b` (points) or `of` (vector name) | length |
| `distance` | `a,b` (points) | distance between two points |
| `dot` | `a,b` (vector names) | dot product |
| `slope` | `of` (line name) | slope (shows "does not exist" for vertical) |
| `slope_product` | `a,b` (line names) | product of slopes |
| `area_triangle` | `pts:[p,q,r]` | triangle area |
| `distance_point_line` | `point, line` | distance from a point to a line |
| `expr` | `expr` (expression), `digits` | numeric value of the expression (can use `@param`/scalars, e.g. the semi-focal distance `c`) |
| `status` | `expr, op, rhs, okText, badText` | inequality state: `expr op rhs` (op∈ `< <= > >= ==`) holds → green "satisfied", otherwise red "not satisfied" |

### 3.6 rangeBar / constant / answerBand / trace
- `rangeBar` (range, extremum problems): `of` tracks the `id` of a **scalar** readout, `min/max` are the
  theoretical-range floats given by the kernel, `label` is the interval LaTeX (with `$…$`). The pointer moves
  between min–max with the current value.
- `constant` (fixed-value problems): `of` tracks a readout, `label` is the fixed-value LaTeX (with `$…$`),
  displaying "constant ≡ …".
- `answerBand` (**shape-parameter problems**, e.g. an eccentricity range): draws `[min,max]` on the
  **parameter axis**, highlights the answer sub-interval `[lo,hi]`, the pointer = current parameter value,
  `label` is the answer LaTeX (with `$…$`). Used for problems like "find the range of e", where the slider
  itself is the answer variable.
- `trace` (locus problems): `of` is the name of some `derived` point; the engine samples over the full param
  range and traces that point's path (you can overlay the kernel's locus equation as a `conics` curve for
  comparison).

### 3.7 semantic color names (COLORS)
`curve` (gold · main curve) · `curve2` (pink · secondary curve) · `line` (cyan · moving line) · `line2` (sky
blue) · `aux` (gray auxiliary) · `asymptote` · `directrix` · `ptA` (red) · `ptB` (blue) · `point` (light
gray) · `given` (purple) · `fixed` (emerald · fixed point) · `vecA` (red) · `vecB` (blue) · `vec` (amber) ·
`locus` · `area` (cyan semi-transparent). You can also write hex directly.

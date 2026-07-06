# Conventions and Solution Recipes

## 1. Coordinate system and curve standard forms
Analytic geometry uses **math plane coordinates** directly (x right, y up), with no need for the z↔y axis
swap of solid geometry. The front-end engine maps math coordinates `(x,y)` to the screen:
`sx = offX + x·scale`, `sy = offY − y·scale` (y flipped). `scale` self-fits to the `view` viewport and does
not affect values.

Standard coordinate setup in `conics.py` (center/vertex at the origin by default):
- `ellipse(a, b)` — `x²/a² + y²/b² = 1`, a=x half-axis, b=y half-axis; foci on the major axis,
  `c=√|a²−b²|`.
- `hyperbola(a, b, orient)` — `orient='x'`: `x²/a²−y²/b²=1`; `'y'`: `y²/a²−x²/b²=1`. a=real half-axis,
  b=imaginary half-axis, `c=√(a²+b²)`, asymptote slopes `±b/a` (x orientation).
- `parabola(p, axis)` — `axis='x'`: `y²=2px`, focus `(p/2,0)`, directrix `x=−p/2`; `'y'`: `x²=2py`.
- `circle(center, r)` — `(x−h)²+(y−k)²=r²`.

## 2. Core pattern: set a parametric line + combine + Vieta
**Prefer `x = m·y + c`** (rather than `y = kx + b`): it naturally includes the vertical line (`m=0`),
avoiding the "slope does not exist" case; the horizontal line corresponds to `m→∞` (dragging the front-end
slider to θ=0° is exactly this case). Through a fixed point `(x₀,y₀)`, `c = x₀ − m·y₀`.

`chord_setup(conic, through)` substitutes `x=my+c` into the curve, gets a quadratic in y, and returns the
exact `A,B,C` coefficients, `ysum=−B/A`, `yprod=C/A`, and the discriminant `disc`. From the Vieta
quantities, write the target quantity as an expression in m:
- `x₁+x₂ = m·ysum + 2c`, `x₁x₂ = m²·yprod + m·c·ysum + c²`.

## 3. Solution recipes (query.type → kernel → interaction paradigm)

| query.type | kernel function / formula | interaction paradigm |
|---|---|---|
| `standard_equation` (find the standard equation) | solve a,b,c (or h,k,r) from eccentricity/point/focus | static labels |
| `chord_length` (chord length, range) | `chord_len_sq_expr`, `|AB|²=(1+m²)[ysum²−4·yprod]` | moving line + range bar |
| `dot_product` (dot product, range/fixed value) | `dot_product_expr` + `range_over_m`/`is_constant_in_m` | moving line + range bar/fixed value |
| `triangle_area` (area, extremum) | `triangle_area_expr=½·|AB|·d`, substitute to find the extremum | moving line + range bar |
| `slope_product` (product of slopes, fixed value) | `slope_product_central` (central symmetry), etc. | moving point + fixed value |
| `fixed_value` (fixed value) | write the target as an m-expression → `is_constant_in_m` | moving parameter + fixed value |
| `fixed_point` (fixed point) | for the parametric line, set "coefficient of the parameter term = 0" and solve for the fixed point | moving parameter + moving line through the fixed point (`emphasis`) |
| `locus` (locus) | set the moving point `(x,y)`, eliminate the parameter to get the equation | drag the driving point + `trace` to draw the path + overlay the equation |
| `tangent` (tangent) | discriminant=0 / point-tangent form (`tangent_at`) | static / moving tangent point |
| `eccentricity` (eccentricity, value/range) | `e=c/a` + condition inequality (e.g. `ecc_range_focal_ratio`) | **slider = e** · curve reshapes + `status` + `answerBand` |

Helpers: `tex(expr)` (LaTeX output), `fnum(expr)` (float), `is_clean(expr)` (checks cleanness for random
problems), `interval_latex(lo,hi,lo_closed,hi_closed)`.

### Shape-parameter problems (the slider drives the curve directly, e.g. an eccentricity range)
For some problems the natural dynamic quantity is not a "moving line/point" but the curve's own **shape
parameter** (most commonly the eccentricity e). In that case make the **slider = that parameter**, and write
the curve's `a/b/c`, foci, and moving-point coordinates as **expression strings** of that parameter (schema
3.1/3.2/3.3b); the engine recomputes and redraws the curve, foci, and asymptotes each frame. The accompanying
pattern:
- Fix one scale (e.g. take `a=1`, then `c=e`, `b="sqrt(e*e-1)"`), and express the rest as expressions;
- Use a `status` readout to show existence / whether the inequality holds (e.g. P exists on the right branch
  ⇔ `e≤2`); points where the expression evaluates to `NaN` are **automatically hidden**, intuitively showing
  "does not exist";
- Use `answerBand` to highlight the answer interval on the parameter axis (endpoints given by the kernel, e.g.
  `ecc_range_focal_ratio(3)` → `e∈(1,2]`).
See `build_hyperbola_ecc_range` in `generate.py` for an example.

## 4. Endpoint open/closed determination (the correctness crux)
`range_over_m(expr, horizontal_valid=True)` finds the range over m∈ℝ and determines whether endpoints are
open/closed:
- Collect the values at stationary points, at `m=0` (vertical line, always valid), and the limit at `m→±∞`
  (horizontal line);
- Whether an endpoint is "closed" = whether it is attained by some **actually valid line**.
- `horizontal_valid=True`: the horizontal line is also a valid chord (e.g. a chord of an ellipse through an
  interior point), so its limiting endpoint is **counted (closed)**.
  Example: for the ellipse `MA·MB`, the x-axis attains −3 and the vertical line attains 7/4 → **`[-3, 7/4]`**
  (do not write the open `(-3, 7/4]`).
- `horizontal_valid=False`: the horizontal/degenerate line is invalid or degenerates the figure (e.g. `△OAB`
  collinear with area 0, a parabola focal chord whose axis direction intersects at only one point), so that
  limiting endpoint is **not counted (open)**. Example: `△OAB` area `(0, 3/2]`.

**This also guarantees the answer matches the interactive tool**: when the slider can be dragged to the θ
corresponding to an endpoint, the readout should exactly equal the answer's endpoint value.

## 5. Correctness self-check (required)
- The answer computed by the kernel == answer card `lesson.answer` == the value shown in the last step ==
  **the front-end JS standard-position/sweep-recomputed value**, all four consistent; each `build_*` in
  `scripts/generate.py` already has a built-in `assert` — add assertions for new problem types the same way.
- `rangeBar` endpoints come from `range_over_m`; the `constant` value comes from `is_constant_in_m`/the
  corresponding kernel function.
- Random problems: compare against the standard answer at kernel generation time.
- After generating, start a local static server and check with a preview: no console errors, KaTeX renders
  correctly, the slider recomputes live correctly, the range bar / fixed value / fixed point / locus behavior
  matches, and the pen and collapse panel work. **Always close the port after previewing.**

## 6. Viewport (view) rules of thumb
Leave about 10–15% margin around the main body of the curve: for an ellipse `xRange≈[-1.8a,1.8a]`; for a
parabola leave more room in the opening direction (e.g. `y²=4x` uses `xRange:[-2,7]`); when a hyperbola
includes asymptotes, don't make the viewport too large or the curve looks too flat. The `param` range must
avoid degenerate values (a parabola focal chord avoids the axis direction θ≈0/180; a central-symmetry slope
product avoids the parameter where the moving point coincides with the fixed point).

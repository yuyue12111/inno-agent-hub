# Conventions and Solution Recipes

## 1. Coordinate systems and mapping

**Math coordinates (z-axis up)** are the coordinates used for solving and formula display; **three.js
coordinates (y-axis up)** are the coordinates used for rendering.

Mapping (`geometry_kernel.to_three`): `three = (x, z, y) * scale`. `scale` only affects appearance, not the
solution values.

Standard coordinate setup for each solid (see `geometry_kernel.py`):
- `regular_quad_pyramid(base_edge, height)` — the base center $O$ is the origin, diagonal $AC$ on the $x$
  axis, $BD$ on the $y$ axis, apex $P$ on the $z$ axis. Half-diagonal $d = a/\sqrt2$.
- `cuboid(lx, ly, lz)` / `cube(edge)` — vertex $A$ is the origin, $AB$ along $x$, $AD$ along $y$, $AA_1$
  along $z$.
- New solid: add a function in the kernel that returns `{name: V(x,y,z)}`; add the corresponding edge
  topology in `bodies.py`.

## 2. Solution recipes (query.type → kernel function)

Everything asked for goes through "set up coordinates + vector method", with values computed exactly by the
kernel — **no mental math**.

| query.type | Formula | kernel function |
|---|---|---|
| `line_plane_angle` | $\sin\theta = \dfrac{|\vec v\cdot\vec n|}{|\vec v||\vec n|}$ | `line_plane_angle_sin(v, n)` |
| `line_line_angle` | $\cos\theta = \dfrac{|\vec{d_1}\cdot\vec{d_2}|}{|\vec{d_1}||\vec{d_2}|}$ | `line_line_angle_cos(d1, d2)` |
| `dihedral` | cosine of the angle between the two half-planes' normals (mind the sign / obtuse vs acute) | use `normal_from_points` + the cosine formula |
| `point_plane_distance` | $d = \dfrac{|(P-P_0)\cdot\vec n|}{|\vec n|}$ | `point_plane_distance(P, P0, n)` |
| `volume` | by the solid's volume formula | (add to the kernel as needed) |

Helpers: `midpoint(a,b)`, `normal_from_points(p,q,r)` (cross product), `simplify_vec(v)` (reduce to the
simplest integer-coefficient direction, used for the "simplify to n=…" display), `tex(expr)` / `tex_vec(v)`
(LaTeX output).

## 3. Steps and camera

- Typical 4 steps: set up coordinates → find key vectors → find the normal/direction → substitute into the
  formula to get the answer.
- Each step's `highlight` gives the elements that should be visible at that step (an absolute set); a common
  rhythm: set-up highlights the axes → progressively reveal the key lines, planes, and normal vector.
- Each step's `cameraPos` gives a viewpoint that clearly shows the current focus (three coordinates);
  `target` is usually the solid's center.

## 4. Rendering-element suggestions

- The key line (the line asked about) uses the `emphasis` color and `depthTest:false` (always visible).
- Auxiliary lines (diagonals, projections) use the `aux` color + `dashed`.
- The plane asked about uses `plane` (semi-transparent). The normal vector uses `arrow` + the `normal` color.
- Axes use `axes`, generally shown only during the set-up step.

## 5. Correctness self-check (required)

- The answer computed by the kernel must be consistent across all three of "answer card `answerValue`" and
  "the final value shown in the last step".
- 3D vertex coordinates must come from `kernel.to_three` (same source as the solution); do not hand-fill
  coordinates separately.
- Random problems: compare against the standard answer at kernel generation time.
- After generating, it's recommended to start a local server and check with a preview: no console errors,
  formulas render correctly, and step highlights and camera match expectations.

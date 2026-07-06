# Data Format Reference (problem-schema)

The three entry points (text / image / random) all funnel into the same **problem spec**, then shared by
computation and rendering.

## 1. problem spec (structured problem, the intermediate product of entry-point unification)

```jsonc
{
  "language": "zh-CN",            // follows the prompt language: zh-CN / en / ...
  "body": "regular_quad_pyramid", // solid type, see conventions.md
  "dims": { "base_edge": 2, "height": 1 },  // solid dimension parameters
  "givens": [                     // extra constructed points / conditions
    { "name": "E", "kind": "midpoint", "of": ["P", "C"] }
  ],
  "query": {                      // what's asked
    "type": "line_plane_angle",   // see the solution recipes in conventions.md
    "line": ["B", "E"],
    "plane": ["P", "A", "C"]
  }
}
```

> Image entry: **echo the recognized spec back to the user for confirmation** (statement, solid, dimensions,
> what's asked, language) before continuing.
> Random entry: the kernel reverse-generates the spec (random parameters → solve → re-sample if the answer
> isn't clean), and it carries the standard answer.

## 2. lesson data (the final data injected into the template `__LESSON_DATA__`)

The template `template/lesson.html` reads a JSON object with three parts: `lesson` / `steps` / `model`.

```jsonc
{
  "lesson": {
    "language": "zh-CN",
    "meta": "Interactive solution · line-plane angle",    // small tag at the top
    "title": "……problem statement……",
    "answerLabel": "……text description of the answer……",
    "answerValue": "$\\frac{2\\sqrt{22}}{11}$",  // LaTeX, with $…$
    "ui": { /* optional: override UI copy, see multilingual below */ }
  },
  "steps": [
    {
      "title": "step title",
      "content": "<p>HTML paragraph, inline formula $…$, display formula $$…$$</p>",
      "highlight": ["Line_BE", "Plane_PAC"],   // the toggleable elements that should be "visible" this step (absolute set)
      "cameraPos": { "x": 4, "y": 4.5, "z": 4 } // this step's camera position (three coordinates)
    }
  ],
  "model": {
    "points": { "P": [0, 1.5, 0], "A": [2.12, 0, 0] },  // three coordinates (y up), from kernel.to_three
    "spheres": ["P", "A", "B", "C", "D", "E"],           // points that get a small sphere + label
    "edges": [                                            // always-visible skeleton edges
      { "a": "A", "b": "B" },
      { "a": "D", "b": "A", "dashed": true },             // dashed line
      { "a": "B", "b": "D", "color": "aux", "dashed": true, "name": "Line_BD" } // named so it can be highlighted
    ],
    "elements": {                                         // toggleable named elements, hidden by default
      "Line_BE":  { "type": "line",  "a": "B", "b": "E", "color": "emphasis", "depthTest": false },
      "Plane_PAC":{ "type": "plane", "pts": ["P", "A", "C"] },         // 3 or 4 points
      "Normal_Vector": { "type": "arrow", "origin": "O", "dir": [0,0,1], "length": 1.5, "color": "normal" },
      "Axis":     { "type": "axes",  "size": 3 }
    },
    "target": [0, 0.45, 0],        // OrbitControls look-at point (three coordinates)
    "initialCamera": [5, 4, 5]     // initial camera position
  }
}
```

### Element types (model.elements[*].type)
- `line` — needs `a`, `b` (point names); `color` (a semantic color name); `dashed`; `depthTest:false` means
  always drawn on top.
- `plane` — needs `pts` (3 or 4 point names).
- `arrow` — needs `origin` (point name or coordinates), `dir` (three direction vector), `length`, `color`.
- `axes` — needs `size`.
- `measure` — segment-length label: at the midpoint of the two points `a`, `b`, offset toward the outside of
  the solid, place a **MathJax** length label.
  - `a`, `b`: the segment endpoints (point names).
  - `label`: the LaTeX for the length (without `$`), e.g. `"2"`, `"2\\sqrt{2}"`, `"\\frac{\\sqrt3}{2}"`.
  - `offset`: optional, the outward offset (default 0.24), to avoid covering the edge.
  - **When to use**: when the statement gives a segment length (a given condition), add a `measure` for the
    corresponding edge, and put its key in the `highlight` of the "set up coordinates / list the given
    conditions" step. Like other elements, its visibility is controlled by the per-step `highlight`.
  - **Master toggle**: as long as any `measure` exists, a "Length labels: on/off" button automatically
    appears in the top-left of the 3D canvas, toggling all length labels on/off with one click (overlaid on
    the per-step highlight). No extra data needed. For English output, set the `measureToggleOn` /
    `measureToggleOff` copy in `lesson.ui`.

### Semantic color names (COLORS)
`frame` (skeleton gray) · `aux` (auxiliary light gray) · `emphasis` (emphasis magenta) · `normal` (normal-vector red) · `plane` (plane blue) · `point` (vertex dark blue)

### highlight rules
Each step's `highlight` is the **complete list of toggleable elements that should be visible at that step**
(an absolute set, not incremental). Skeleton edges and vertex spheres are always visible and need not be
listed.

### Moving-point drag + live values (model.draggable, optional)
Let a moving point drag along a constraint segment, updating dependent points and figures in tandem, and
display real geometric quantities live (computed in **math coordinates**). You must also provide `model.scale`
and `model.mathPoints` (each point's math coordinates, as a numeric array).

```jsonc
"model": {
  "scale": 1.4,                       // consistent with the scale used by kernel.to_three
  "mathPoints": { "A1": [2,0,2], "C1": [0,2,2], "P": [0.5,1.5,2], "C": [0,2,0], "B1": [0,0,2], "A": [2,0,0] },
  "draggable": {
    "point": "P",                     // the dragged point (drawn as a larger emphasis-color sphere)
    "along": ["A1", "C1"],            // constraint-segment endpoints (point names)
    "t": 0.75,                        // the parameter t∈[0,1] at the position set by the problem (e.g. A1P=3PC1 -> 0.75)
    "standardLabel": "Standard position A₁P=3PC₁",
    "dependent": [ { "name": "D", "kind": "midpoint", "of": ["P", "C"] } ], // dependent points recomputed as the point moves
    "readouts": [                     // live values (computed in math coordinates)
      { "label": "Volume of tetrahedron B₁-APC", "type": "volume_tetra", "pts": ["B1","A","P","C"] },
      { "label": "Length of A₁P", "type": "length", "pts": ["A1","P"] }
    ]
  }
}
```
- readout `type` supports: `volume_tetra` (4 points), `length` (2 points), `line_plane_angle_sin` (`line`: 2
  points, `plane`: 3 points).
- Dragging near `t` shows "Standard position ✓". The exact symbolic solution in the problem steps still
  corresponds to that standard position.

### Multilingual (lesson.ui, optional)
The template has a built-in Chinese `defaultUI` fallback. For English output, put the UI copy into
`lesson.ui` (keys are in the `defaultUI` of `template/lesson.html`), e.g.
`previous/next/finish/stepTemplate/sceneLabel/...`, and set `lesson.language` to `en`. `steps.content` and
`title` are written by the model in the target language. LaTeX like `answerValue` is language-independent.

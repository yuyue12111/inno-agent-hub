#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate.py — inject structured lesson data into template/lesson.html and produce a single-page HTML.

All data is driven by the deterministic computation in lib/geometry_kernel.py:
coordinates, vectors, and the final answer are all exact sympy results, so the 3D coordinates and the
solution values share the same source and are strictly consistent.

Dependency: sympy. Run with a python3 that can import sympy (if missing: python3 -m pip install sympy):
    python3 scripts/generate.py [output-path.html]
"""

import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "template" / "lesson.html"
PLACEHOLDER = "__LESSON_DATA__"

sys.path.insert(0, str(SKILL_DIR / "lib"))
import geometry_kernel as gk  # noqa: E402
import bodies  # noqa: E402


def _centroid(three_points):
    names = list(three_points)
    n = len(names)
    return [sum(three_points[k][i] for k in names) / n for i in range(3)]


def render_html(data: dict, out_path: Path) -> Path:
    """Inject the data as JSON into the template placeholder and write out the html."""
    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise RuntimeError(f"placeholder {PLACEHOLDER} not found in the template")
    payload = json.dumps(data, ensure_ascii=False)
    html = template.replace(PLACEHOLDER, payload)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def build_cube_data() -> dict:
    """Cube ABCD-A1B1C1D1 (edge length 1), find the sine of the angle between line A1C and the base ABCD.

    The solid topology comes from bodies.cuboid, and the vertex coordinates and answer come from geometry_kernel (same source).
    """
    sol = gk.solve_cube_line_plane_angle(edge=1, scale=2)
    mp = sol["math_points"]
    v = sol["vals"]
    ans = sol["answer_latex"]
    tp = sol["three_points"]

    topo = bodies.cuboid()  # spheres + 12 edges
    center = _centroid(tp)

    model = {
        "target": center,
        "initialCamera": [6, 5, 7],
        "points": tp,
        "spheres": topo["spheres"],
        "edges": topo["edges"],
        "elements": {
            "Line_A1C": {"type": "line", "a": "A1", "b": "C", "color": "emphasis", "depthTest": False},
            "Plane_ABCD": {"type": "plane", "pts": ["A", "B", "C", "D"]},
            "Normal_Vector": {"type": "arrow", "origin": "A", "dir": [0, 1, 0], "length": 1.6, "color": "normal"},
            "Axis": {"type": "axes", "size": 2.6},
        },
    }

    lesson = {
        "language": "en",
        "meta": "Interactive solution · line-plane angle",
        "title": "In the cube ABCD-A₁B₁C₁D₁ with edge length 1, find the sine of the angle between line A₁C and the base ABCD",
        "answerLabel": "Sine of the angle between line A₁C and the base ABCD",
        "answerValue": f"${ans}$",
    }

    steps = [
        {
            "title": "Set up a spatial rectangular coordinate system",
            "content": (
                r"<p>Take vertex $A$ as the origin, with $AB$, $AD$, $AA_1$ as the $x$, $y$, $z$ axes respectively.</p>"
                r"<p>Since the edge length is $1$, the key point coordinates are:</p>"
                r"$$A" + mp["A"] + r", C" + mp["C"] + r", A_1" + mp["A1"] + r"$$"
            ),
            "highlight": ["Axis"],
            "cameraPos": {"x": 6, "y": 5, "z": 7},
        },
        {
            "title": "Find the direction vector of line A₁C",
            "content": (
                r"<p>The direction vector of line $A_1C$ is:</p>"
                r"$$\vec{A_1C} = C - A_1 = " + v["A1C"] + r"$$"
            ),
            "highlight": ["Line_A1C"],
            "cameraPos": {"x": 5, "y": 4, "z": 8},
        },
        {
            "title": "Determine the normal vector of the base ABCD",
            "content": (
                r"<p>The base $ABCD$ lies in the plane $z = 0$, so its normal vector points straight up:</p>"
                r"$$\vec{n} = " + v["n_simpl"] + r"$$"
            ),
            "highlight": ["Line_A1C", "Plane_ABCD", "Normal_Vector"],
            "cameraPos": {"x": 4, "y": 6, "z": 5},
        },
        {
            "title": "Solve using the vector formula",
            "content": (
                r"<p>Let the angle between line $A_1C$ and the base be $\theta$.</p>"
                r"<p>Line-plane angle formula: $\sin\theta = \dfrac{|\vec{A_1C} \cdot \vec{n}|}{|\vec{A_1C}|\,|\vec{n}|}$</p>"
                r"<p>Compute the dot product and magnitudes:</p>"
                r"$$\vec{A_1C} \cdot \vec{n} = " + v["dot"] + r", \quad |\vec{A_1C}| = " + v["norm_line"] + r"$$"
                r"<p>Substitute into the formula:</p>"
                r"$$\sin\theta = " + v["sin"] + r"$$"
                r"<p>Therefore, the sine of the angle between line $A_1C$ and the base $ABCD$ is $" + ans + r"$.</p>"
            ),
            "highlight": ["Line_A1C", "Plane_ABCD", "Normal_Vector"],
            "cameraPos": {"x": 5, "y": 5, "z": 6},
        },
    ]

    return {"lesson": lesson, "steps": steps, "model": model, "_answer": ans}


def build_data(base_edge=2, height=1) -> dict:
    """Regular quadrilateral pyramid P-ABCD (E the midpoint of PC), line-plane angle; base edge and height can be parameterized (for random problems).

    All numeric values come from geometry_kernel; the text steps only organize those values into an explanation.
    """
    sol = gk.solve_pyramid_line_plane_angle(base_edge=base_edge, height=height, scale=1.5)
    mp = sol["math_points"]   # LaTeX of the math coordinates, e.g. "(\\sqrt{2}, 0, 0)"
    v = sol["vals"]           # LaTeX of each step's intermediate quantities
    ans = sol["answer_latex"]
    diag_tex = gk.tex(gk.sp.sympify(base_edge) * gk.sqrt(2))
    half_tex = gk.tex(gk.sp.sympify(base_edge) * gk.sqrt(2) / 2)

    # ---- 3D model: vertex coordinates come from the kernel (same source as the solution); topology/highlights declared here ----
    model = {
        "target": [0, 0.45, 0],
        "initialCamera": [5, 4, 5],
        "points": sol["three_points"],
        "spheres": ["O", "P", "A", "B", "C", "D", "E"],
        "edges": [
            {"a": "A", "b": "B"},
            {"a": "B", "b": "C"},
            {"a": "C", "b": "D"},
            {"a": "D", "b": "A", "dashed": True},
            {"a": "P", "b": "A"},
            {"a": "P", "b": "B"},
            {"a": "P", "b": "C"},
            {"a": "P", "b": "D"},
            {"a": "A", "b": "C", "color": "aux", "dashed": True},
            {"a": "B", "b": "D", "color": "aux", "dashed": True, "name": "Line_BD"},
        ],
        "elements": {
            "Line_BE": {"type": "line", "a": "B", "b": "E", "color": "emphasis", "depthTest": False},
            "Plane_PAC": {"type": "plane", "pts": ["P", "A", "C"]},
            "Normal_Vector": {"type": "arrow", "origin": "O", "dir": [0, 0, 1], "length": 1.5, "color": "normal"},
            "Axis": {"type": "axes", "size": 3},
            # segment-length labels (given conditions: base edge, diagonal, height)
            "Len_AB": {"type": "measure", "a": "A", "b": "B", "label": str(base_edge)},
            "Len_AC": {"type": "measure", "a": "A", "b": "C", "label": diag_tex},
            "Len_PO": {"type": "measure", "a": "P", "b": "O", "label": str(height)},
        },
    }

    lesson = {
        "language": "en",
        "meta": "Interactive solution · line-plane angle",
        "title": f"In the regular quadrilateral pyramid P-ABCD with base edge {base_edge} and height {height}, E is the midpoint of PC; find the sine of the angle between line BE and plane PAC",
        "answerLabel": "Sine of the angle between line BE and plane PAC",
        "answerValue": f"${ans}$",
    }

    # ---- step text: numeric slots are filled by the kernel's computed results (no mental math) ----
    steps = [
        {
            "title": "Set up a spatial rectangular coordinate system",
            "content": (
                r"<p>First, we need to set up a suitable spatial rectangular coordinate system to quantify the geometric elements.</p>"
                r"<p>Take the center $O$ of the square base $ABCD$ as the origin $(0,0,0)$.</p>"
                r"<p>Let the base diagonal $AC$ be on the $x$-axis, $BD$ on the $y$-axis, and the apex $P$ on the $z$-axis.</p>"
                r"<p>Since the base edge is $" + str(base_edge) + r"$, the two diagonals have length $" + diag_tex + r"$, and the half-diagonal has length $" + half_tex + r"$. So the key point coordinates are:</p>"
                r"$$A" + mp["A"] + r", C" + mp["C"] + r"$$"
                r"$$B" + mp["B"] + r", D" + mp["D"] + r"$$"
                r"$$P" + mp["P"] + r"$$"
                r"<p>This makes the relationship $AC \perp BD$ more evident.</p>"
            ),
            "highlight": ["Axis", "Len_AB", "Len_AC", "Len_PO"],
            "cameraPos": {"x": 5, "y": 4, "z": 5},
        },
        {
            "title": "Compute the midpoint E and the vector BE",
            "content": (
                r"<p>It is given that $E$ is the midpoint of the lateral edge $PC$.</p>"
                r"<p>Using the midpoint coordinate formula: $E = \frac{P + C}{2}$</p>"
                r"$$P" + mp["P"] + r", C" + mp["C"] + r"$$"
                r"$$E = " + v["E"] + r"$$"
                r"<p>Next compute the direction vector $\vec{BE}$ of line $BE$:</p>"
                r"$$\vec{BE} = E - B = " + v["BE"] + r"$$"
            ),
            "highlight": ["Line_BE"],
            "cameraPos": {"x": 3, "y": 3, "z": 6},
        },
        {
            "title": "Determine the normal vector of plane PAC",
            "content": (
                r"<p>We need to find the angle between line $BE$ and plane $PAC$.</p>"
                r"<p>Observe the features of the solid:</p>"
                r"<ul>"
                r"<li>The base $ABCD$ is a square, and its diagonals are perpendicular, i.e. $AC \perp BD$.</li>"
                r"<li>The projection of the apex $P$ onto the base is the center $O$, so $PO \perp AC$.</li>"
                r"</ul>"
                r"<p>Since $AC \perp BD$ and $AC \perp PO$, the line $BD \perp$ plane $PAC$.</p>"
                r"<p>Therefore, the normal vector $\vec{n}$ of plane $PAC$ is the direction of $\vec{BD}$:</p>"
                r"$$\vec{n} = " + v["n"] + r"$$"
                r"<p>Simplify to take $\vec{n} = " + v["n_simpl"] + r"$.</p>"
            ),
            "highlight": ["Line_BE", "Plane_PAC", "Normal_Vector"],
            "cameraPos": {"x": 4, "y": 5, "z": 2},
        },
        {
            "title": "Solve using the vector formula",
            "content": (
                r"<p>Let the angle between line $BE$ and plane $PAC$ be $\theta$.</p>"
                r"<p>By the line-plane angle formula: $\sin\theta = \dfrac{|\vec{BE} \cdot \vec{n}|}{|\vec{BE}|\,|\vec{n}|}$</p>"
                r"<p>Vector data:</p>"
                r"<ul>"
                r"<li>$\vec{BE} = " + v["BE"] + r"$</li>"
                r"<li>$\vec{n} = " + v["n_simpl"] + r"$</li>"
                r"</ul>"
                r"<p>Compute the dot product and magnitudes:</p>"
                r"$$\vec{BE} \cdot \vec{n} = " + v["dot"] + r", \quad |\vec{BE}| = " + v["norm_BE"] + r"$$"
                r"<p>Substitute into the formula:</p>"
                r"$$\sin\theta = " + v["sin"] + r"$$"
                r"<p>Therefore, the sine of the angle between line $BE$ and plane $PAC$ is $" + ans + r"$.</p>"
            ),
            "highlight": ["Line_BE", "Plane_PAC", "Normal_Vector"],
            "cameraPos": {"x": 4, "y": 4.5, "z": 4},
        },
    ]

    return {"lesson": lesson, "steps": steps, "model": model, "_answer": ans}


def build_box_volume_data(lx=3, ly=4, lz=5) -> dict:
    """Cuboid ABCD-A1B1C1D1 with given length, width, height; find the volume. Demonstrates end-to-end generation for a non-angle problem type."""
    V = gk.volume_box(lx, ly, lz)
    pts = gk.cuboid(lx, ly, lz)
    scale = 3.0 / max(lx, ly, lz)
    tp = gk.to_three(pts, scale=scale)
    topo = bodies.cuboid()
    center = _centroid(tp)
    ans = gk.tex(V)

    model = {
        "target": center,
        "initialCamera": [center[0] + 5, center[1] + 4, center[2] + 6],
        "points": tp,
        "spheres": topo["spheres"],
        "edges": topo["edges"],
        "elements": {
            "Edge_L": {"type": "line", "a": "A", "b": "B", "color": "emphasis"},
            "Edge_W": {"type": "line", "a": "A", "b": "D", "color": "emphasis"},
            "Edge_H": {"type": "line", "a": "A", "b": "A1", "color": "emphasis"},
            "Axis": {"type": "axes", "size": max(tp_span(tp), 2.5)},
        },
    }
    lesson = {
        "language": "en",
        "meta": "Interactive solution · volume",
        "title": f"The cuboid ABCD-A₁B₁C₁D₁ has length, width, and height {lx}, {ly}, {lz}; find its volume",
        "answerLabel": "Volume of the cuboid",
        "answerValue": f"${ans}$",
    }
    steps = [
        {
            "title": "Identify the length, width, and height",
            "content": (
                r"<p>Set up a coordinate system with vertex $A$ as the origin; the three edges from $A$ are the length, width, and height:</p>"
                r"<ul>"
                r"<li>length $AB = " + str(lx) + r"$</li>"
                r"<li>width $AD = " + str(ly) + r"$</li>"
                r"<li>height $AA_1 = " + str(lz) + r"$</li>"
                r"</ul>"
            ),
            "highlight": ["Edge_L", "Edge_W", "Edge_H", "Axis"],
            "cameraPos": {"x": center[0] + 5, "y": center[1] + 4, "z": center[2] + 6},
        },
        {
            "title": "Apply the cuboid volume formula",
            "content": (
                r"<p>The volume of a cuboid equals length × width × height:</p>"
                r"$$V = AB \times AD \times AA_1$$"
            ),
            "highlight": ["Edge_L", "Edge_W", "Edge_H"],
            "cameraPos": {"x": center[0] + 4, "y": center[1] + 5, "z": center[2] + 5},
        },
        {
            "title": "Substitute and evaluate",
            "content": (
                r"$$V = " + str(lx) + r" \times " + str(ly) + r" \times " + str(lz) + r" = " + ans + r"$$"
                r"<p>So the volume of this cuboid is $" + ans + r"$.</p>"
            ),
            "highlight": ["Edge_L", "Edge_W", "Edge_H"],
            "cameraPos": {"x": center[0] + 5, "y": center[1] + 4, "z": center[2] + 5},
        },
    ]
    return {"lesson": lesson, "steps": steps, "model": model, "_answer": ans}


def tp_span(three_points):
    xs = [three_points[k][i] for k in three_points for i in range(3)]
    return max(abs(x) for x in xs) + 0.5


def build_random_data(seed=0) -> dict:
    """Random problem: randomly pick a problem type and parameters, solve, re-sample if the answer isn't clean, and return renderable data.

    Currently covers: cuboid volume, regular quadrilateral pyramid line-plane angle. Extend more problem types with the same resample pattern.
    """
    import random
    rng = random.Random(seed)
    kind = rng.choice(["box_volume", "pyramid_lpa"])

    if kind == "box_volume":
        lx, ly, lz = (rng.randint(2, 6) for _ in range(3))
        return build_box_volume_data(lx, ly, lz)

    # pyramid line-plane angle: re-sample until the answer is clean
    for _ in range(50):
        a = rng.choice([2, 4, 6])
        h = rng.randint(1, 4)
        sol = gk.solve_pyramid_line_plane_angle(base_edge=a, height=h)
        if gk.is_clean(sol["_exact"]["sin_theta"]):
            return build_data(base_edge=a, height=h)
    # fallback
    return build_box_volume_data()


PROBLEMS = {
    "pyramid": build_data,
    "cube": build_cube_data,
    "box": build_box_volume_data,
}


def main():
    args = list(sys.argv[1:])
    problem = "pyramid"
    out = None
    seed = 0
    for a in args:
        if a in PROBLEMS or a == "random":
            problem = a
        elif a.isdigit():
            seed = int(a)
        else:
            out = Path(a)
    if out is None:
        # default to writing to the "user's current working directory" (cwd), not the skill's own directory
        out = Path.cwd() / f"{problem}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build_random_data(seed) if problem == "random" else PROBLEMS[problem]()

    # --- self-check: the answer shown in the final step must equal the answer card's answer (both the kernel's computed result) ---
    final_step = data["steps"][-1]["content"]
    assert data["_answer"] in final_step, "the final step does not contain the computed answer"
    data.pop("_answer", None)

    render_html(data, out)
    print(f"generated: {out}")


if __name__ == "__main__":
    main()

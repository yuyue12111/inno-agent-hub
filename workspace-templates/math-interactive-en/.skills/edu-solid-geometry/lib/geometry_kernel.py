#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geometry_kernel.py — solid-geometry deterministic computation core (based on exact sympy symbolic algebra).

Design goal: coordinates, vectors, and the final answer are all computed exactly by this module,
with radicals auto-simplified, eliminating mental-math errors. The same set of coordinates feeds
both the solution text and the 3D rendering, guaranteeing that "figure, solution, answer" are
strictly consistent.

Dependency: sympy (pip install sympy).

Coordinate convention (math coordinates, z-axis up):
  - What the statement/formulas display is this set of math coordinates.
  - 3D rendering coordinates use the three.js convention (y-axis up): three = (x, z, y) * scale.
"""

import sympy as sp

sqrt = sp.sqrt


# ===================== Basic utilities =====================

def V(*comps):
    """Construct a column vector (sympy.Matrix)."""
    if len(comps) == 1 and isinstance(comps[0], (list, tuple)):
        comps = comps[0]
    return sp.Matrix([sp.sympify(c) for c in comps])


def midpoint(a, b):
    return (a + b) / 2


def normal_from_points(p, q, r):
    """Find the normal vector from three points on a plane (cross product); returns the unsimplified vector."""
    return (q - p).cross(r - p)


def simplify_vec(v):
    """Reduce a vector by a common factor to the simplest integer-coefficient direction (only for the 'simplify to n=...' display)."""
    v = sp.Matrix([sp.simplify(c) for c in v])
    nonzero = [c for c in v if c != 0]
    if not nonzero:
        return v
    g = nonzero[0]
    for c in nonzero[1:]:
        g = sp.gcd(g, c)
    if g != 0:
        cand = sp.simplify(v / g)
        # adopt it if the reduced result is still an integer vector
        if all(c.is_rational for c in cand):
            return cand
    return v


def line_plane_angle_sin(line_dir, normal):
    """Sine of the line-plane angle: sinθ = |v·n| / (|v||n|), exactly simplified."""
    v = line_dir
    n = normal
    s = sp.Abs(v.dot(n)) / (v.norm() * n.norm())
    return sp.simplify(s)


def line_line_angle_cos(d1, d2):
    """Cosine of the angle between skew lines: cosθ = |d1·d2| / (|d1||d2|)."""
    return sp.simplify(sp.Abs(d1.dot(d2)) / (d1.norm() * d2.norm()))


def point_plane_distance(point, plane_point, normal):
    """Distance from a point to a plane: |(P - P0)·n| / |n|."""
    return sp.simplify(sp.Abs((point - plane_point).dot(normal)) / normal.norm())


def dihedral_cos(A, B, C, D):
    """Cosine of the dihedral angle C-AB-D: take a vector in each half-plane perpendicular to the edge AB, then find the angle between them.

    AB is the edge, C is in one face, D is in the other. Returns the signed exact cosine
    (positive = acute dihedral angle, negative = obtuse dihedral angle).
    """
    u = B - A

    def perp(P):
        w = P - A
        return w - (w.dot(u) / u.dot(u)) * u

    v1, v2 = perp(C), perp(D)
    return sp.simplify(v1.dot(v2) / (v1.norm() * v2.norm()))


def dihedral_cos_from_normals(n1, n2):
    """Find the dihedral-angle cosine from the two half-plane normals (the sign depends on the normals' orientation, usually paired with a geometric acute/obtuse judgment)."""
    return sp.simplify(n1.dot(n2) / (n1.norm() * n2.norm()))


# ===================== Volume =====================

def volume_box(lx, ly, lz):
    return sp.simplify(sp.sympify(lx) * sp.sympify(ly) * sp.sympify(lz))


def volume_prism(base_area, height):
    return sp.simplify(sp.sympify(base_area) * sp.sympify(height))


def volume_pyramid(base_area, height):
    return sp.simplify(sp.Rational(1, 3) * sp.sympify(base_area) * sp.sympify(height))


def volume_tetra(A, B, C, D):
    """Tetrahedron volume = |(AB × AC) · AD| / 6."""
    return sp.simplify(sp.Abs((B - A).cross(C - A).dot(D - A)) / 6)


# ===================== LaTeX output =====================

def tex(expr):
    return sp.latex(sp.simplify(expr))


def is_clean(expr, max_ops=7, max_radicand=60):
    """Judge whether the answer is "clean": low complexity after simplification, at most small-integer radicals, no nested radicals.

    Used for random problems: after solving with random parameters, re-sample if the answer isn't clean.
    """
    e = sp.radsimp(sp.nsimplify(sp.simplify(expr)))
    if e.has(sp.zoo, sp.nan, sp.oo) or e.free_symbols:
        return False
    if sp.count_ops(e) > max_ops:
        return False
    for p in e.atoms(sp.Pow):
        if p.exp == sp.Rational(1, 2):
            rad = p.base
            if not (rad.is_Integer and 0 <= int(rad) <= max_radicand):
                return False
            if rad.atoms(sp.Pow):  # nested radical
                return False
    return True


def tex_vec(v):
    return "(" + ", ".join(sp.latex(sp.simplify(c)) for c in v) + ")"


# ===================== Solid construction library (math coordinates) =====================

def regular_quad_pyramid(base_edge, height):
    """Regular quadrilateral pyramid P-ABCD: the base center O is the origin, diagonal AC on the x-axis, BD on the y-axis, apex P on the z-axis.

    Returns {name: sympy column vector} (math coordinates).
    """
    a = sp.sympify(base_edge)
    h = sp.sympify(height)
    d = sp.simplify(a / sqrt(2))  # half-diagonal = a√2/2
    return {
        "O": V(0, 0, 0),
        "A": V(d, 0, 0),
        "C": V(-d, 0, 0),
        "B": V(0, d, 0),
        "D": V(0, -d, 0),
        "P": V(0, 0, h),
    }


def cuboid(lx, ly, lz):
    """Cuboid ABCD-A1B1C1D1: A at the origin, AB along x, AD along y, AA1 along z."""
    lx, ly, lz = sp.sympify(lx), sp.sympify(ly), sp.sympify(lz)
    return {
        "A": V(0, 0, 0), "B": V(lx, 0, 0), "C": V(lx, ly, 0), "D": V(0, ly, 0),
        "A1": V(0, 0, lz), "B1": V(lx, 0, lz), "C1": V(lx, ly, lz), "D1": V(0, ly, lz),
    }


def cube(edge):
    """Cube (a special case of the cuboid)."""
    return cuboid(edge, edge, edge)


def regular_tetrahedron(edge=2 * sqrt(2)):
    """Regular tetrahedron ABCD (with the default edge length 2√2 the coordinates are integers). Returns {name: math vector}."""
    base = {
        "A": V(1, 1, 1),
        "B": V(1, -1, -1),
        "C": V(-1, 1, -1),
        "D": V(-1, -1, 1),
    }
    k = sp.simplify(sp.sympify(edge) / (2 * sqrt(2)))  # scale to the target edge length
    return {name: sp.simplify(k * v) for name, v in base.items()}


# ===================== Math coordinates -> three.js coordinates =====================

def to_three(points, scale=1.5):
    """{name: math vector} -> {name: [x, y, z] floats (three.js: y up)}."""
    s = sp.Float(scale)
    out = {}
    for name, p in points.items():
        mx, my, mz = p[0], p[1], p[2]
        three = (mx * s, mz * s, my * s)  # three = (x, z, y) * scale
        out[name] = [float(c) for c in three]
    return out


# ===================== Concrete problem solving (line-plane angle sample) =====================

def solve_pyramid_line_plane_angle(base_edge=2, height=1, scale=1.5):
    """Regular quadrilateral pyramid P-ABCD, E the midpoint of PC, find the sine of the angle between line BE and plane PAC.

    Returns all the data needed to assemble the webpage: exact answer, math coordinates, three coordinates, and each step's intermediate quantities (LaTeX).
    """
    pts = regular_quad_pyramid(base_edge, height)
    pts["E"] = midpoint(pts["P"], pts["C"])

    BE = pts["E"] - pts["B"]
    n = normal_from_points(pts["P"], pts["A"], pts["C"])  # normal vector of plane PAC
    n_simpl = simplify_vec(n)

    sin_theta = line_plane_angle_sin(BE, n)

    dot = BE.dot(n_simpl)
    norm_BE = sp.sqrt(sum(c**2 for c in BE))

    return {
        "answer_latex": tex(sin_theta),
        "math_points": {k: tex_vec(v) for k, v in pts.items()},
        "three_points": to_three(pts, scale=scale),
        "vals": {
            "E": tex_vec(pts["E"]),
            "BE": tex_vec(BE),
            "n": tex_vec(n),
            "n_simpl": tex_vec(n_simpl),
            "dot": tex(dot),
            "norm_BE": tex(sp.simplify(norm_BE)),
            "sin": tex(sin_theta),
        },
        "_exact": {"sin_theta": sin_theta},  # for self-check comparison
    }


def solve_cube_line_plane_angle(edge=1, scale=2):
    """Cube ABCD-A1B1C1D1 (edge length a), find the sine of the angle between line A1C and the base ABCD."""
    pts = cube(edge)
    line = pts["C"] - pts["A1"]                                   # direction vector A1C
    n = normal_from_points(pts["A"], pts["B"], pts["D"])          # normal vector of base ABCD
    n_simpl = simplify_vec(n)

    sin_theta = line_plane_angle_sin(line, n)
    dot = line.dot(n_simpl)
    norm_line = sp.sqrt(sum(c**2 for c in line))

    return {
        "answer_latex": tex(sin_theta),
        "math_points": {k: tex_vec(v) for k, v in pts.items()},
        "three_points": to_three(pts, scale=scale),
        "vals": {
            "A1C": tex_vec(line),
            "n": tex_vec(n),
            "n_simpl": tex_vec(n_simpl),
            "dot": tex(dot),
            "norm_line": tex(sp.simplify(norm_line)),
            "sin": tex(sin_theta),
        },
        "_exact": {"sin_theta": sin_theta},
    }


if __name__ == "__main__":
    sol = solve_pyramid_line_plane_angle()
    expected = 2 * sqrt(22) / 11
    got = sol["_exact"]["sin_theta"]
    ok = sp.simplify(got - expected) == 0
    print("answer (LaTeX):", sol["answer_latex"])
    print("E:", sol["vals"]["E"])
    print("BE:", sol["vals"]["BE"])
    print("normal n:", sol["vals"]["n"], "-> simplified", sol["vals"]["n_simpl"])
    print("|BE|:", sol["vals"]["norm_BE"])
    print("three coordinate E:", sol["three_points"]["E"])
    print("reproduce 2√22/11 :", "PASS" if ok else "FAIL")
    assert ok, "line-plane angle answer does not match the expected 2√22/11"

    sol2 = solve_cube_line_plane_angle()
    exp2 = sqrt(3) / 3
    ok2 = sp.simplify(sol2["_exact"]["sin_theta"] - exp2) == 0
    print("cube A1C-base:", sol2["answer_latex"], "reproduce √3/3 :", "PASS" if ok2 else "FAIL")
    assert ok2, "cube line-plane angle answer does not match the expected √3/3"

    print("\n--- self-check of the four solver types ---")

    # angle between skew lines: A1C and AB in a cube (cos = √3/3)
    cb = cube(1)
    cos_ll = line_line_angle_cos(cb["C"] - cb["A1"], cb["B"] - cb["A"])
    ok_ll = sp.simplify(cos_ll - sqrt(3) / 3) == 0
    print("skew lines A1C·AB cos =", tex(cos_ll), "(expected √3/3)", "PASS" if ok_ll else "FAIL")
    assert ok_ll

    # distance from a point to a plane: A1 to base ABCD in a cube (= 1)
    n_base = normal_from_points(cb["A"], cb["B"], cb["D"])
    dist = point_plane_distance(cb["A1"], cb["A"], n_base)
    ok_d = sp.simplify(dist - 1) == 0
    print("distance A1 to base ABCD =", tex(dist), "(expected 1)", "PASS" if ok_d else "FAIL")
    assert ok_d

    # dihedral angle: regular tetrahedron C-AB-D (cos = 1/3)
    tet = regular_tetrahedron()
    cos_dih = dihedral_cos(tet["A"], tet["B"], tet["C"], tet["D"])
    ok_dih = sp.simplify(cos_dih - sp.Rational(1, 3)) == 0
    print("regular tetrahedron dihedral cos =", tex(cos_dih), "(expected 1/3)", "PASS" if ok_dih else "FAIL")
    assert ok_dih

    # volume: regular tetrahedron with edge 2√2 -> volume 8/3; check pyramid/box
    vol_tet = volume_tetra(tet["A"], tet["B"], tet["C"], tet["D"])
    ok_v = sp.simplify(vol_tet - sp.Rational(8, 3)) == 0
    print("regular tetrahedron (edge 2√2) volume =", tex(vol_tet), "(expected 8/3)", "PASS" if ok_v else "FAIL")
    assert ok_v
    assert volume_box(2, 3, 4) == 24 and volume_pyramid(4, 3) == 4
    print("volume box(2,3,4)=24, pyramid(4,3)=4 PASS")

    print("\nall self-checks passed ✅")

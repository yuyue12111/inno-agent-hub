#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analytic_kernel.py — analytic-geometry sympy exact-solving core.

Design philosophy (single source of truth): the answer, coordinates, step values, and the front-end
interactive engine's "theoretical range" are all derived from the exact sympy results here, eliminating
mental math and inconsistency.

Core pattern: a parametric line x = m·y + c (c determined by "through a fixed point"), substituted into
the conic to get a quadratic in y; Vieta's theorem gives y1+y2, y1·y2 (exact), from which the target
quantity (dot product / chord length / area / slope product…) is written as an expression in m, then
range_over_m finds its range of values (including open/closed endpoint determination).

Geometric meaning of m: the line x=my+c has slope 1/m, i.e. m=cotθ (θ the inclination angle).
 - m=0  → vertical line (θ=90°)
 - m→∞ → horizontal line (θ=0°, dragging the front-end slider to 0° is exactly this case)
"""
import sympy as sp
import conics
from conics import x, y

m = sp.symbols('m', real=True)
u = sp.symbols('u', nonnegative=True)     # u = m^2


# ---------------- General utilities ----------------
def tex(e):
    return sp.latex(sp.nsimplify(sp.simplify(e)))


def fnum(e):
    return float(sp.N(e))


def is_clean(e):
    """Whether the answer is "clean" (a rational number or simplest radical form), used to filter random problems."""
    e = sp.nsimplify(sp.simplify(e))
    return e.is_rational or (e.free_symbols == set() and sp.simplify(e - sp.nsimplify(e)) == 0)


def interval_latex(lo, hi, lo_closed, hi_closed):
    lb = '[' if lo_closed else '('
    rb = ']' if hi_closed else ')'
    lo_s = r'-\infty' if lo == -sp.oo else tex(lo)
    hi_s = r'+\infty' if hi == sp.oo else tex(hi)
    return r"%s%s,\ %s%s" % (lb, lo_s, hi_s, rb)


# ---------------- Parametric line ∩ conic + Vieta ----------------
def chord_setup(conic, through):
    """The line x = m·y + c through the point `through`, combined with `conic` → a quadratic in y. Returns the Vieta quantities, etc."""
    x0, y0 = sp.nsimplify(through[0]), sp.nsimplify(through[1])
    c = x0 - m * y0
    sub = sp.expand(conic['implicit'].subs(x, m * y + c))
    num = sp.numer(sp.together(sub))
    poly = sp.Poly(num, y)
    coeffs = poly.all_coeffs()
    if len(coeffs) != 3:
        raise ValueError(f"combining did not yield a quadratic in y: {poly}")
    A, B, C = coeffs
    return {
        'm': m, 'c': c, 'A': A, 'B': B, 'C': C, 'poly': poly,
        'ysum': sp.simplify(-B / A), 'yprod': sp.simplify(C / A),
        'disc': sp.simplify(B**2 - 4 * A * C),
    }


def _xy_from_y(cs, M=None):
    """Give x1+x2, x1x2 from the Vieta quantities (used to turn the target quantity into an expression in m)."""
    ys, yp = cs['ysum'], cs['yprod']
    xs = m * ys + 2 * cs['c']                 # x1+x2
    xp = m**2 * yp + m * cs['c'] * ys + cs['c']**2   # x1·x2
    return sp.simplify(xs), sp.simplify(xp)


# ---------------- Target quantities (written as expressions in m) ----------------
def dot_product_expr(conic, through, M):
    """The dot product MA·MB, with M as the vertex and A, B as the intersections, as an expression in m."""
    cs = chord_setup(conic, through)
    ys, yp = cs['ysum'], cs['yprod']
    xs, xp = _xy_from_y(cs)
    Mx, My = sp.nsimplify(M[0]), sp.nsimplify(M[1])
    # (x1-Mx)(x2-Mx)+(y1-My)(y2-My) = xp - Mx*xs + Mx^2 + yp - My*ys + My^2
    expr = xp - Mx * xs + Mx**2 + yp - My * ys + My**2
    return sp.simplify(expr), cs


def chord_len_sq_expr(conic, through):
    """The chord length squared |AB|^2 as an expression in m. |AB|^2=(1+m^2)[(y1+y2)^2-4y1y2]."""
    cs = chord_setup(conic, through)
    expr = (1 + m**2) * (cs['ysum']**2 - 4 * cs['yprod'])
    return sp.simplify(expr), cs


def triangle_area_expr(conic, through, vertex):
    """The area of △(vertex,A,B) = 1/2·|AB|·d(vertex,l). Returns the area as an expression in m."""
    cs = chord_setup(conic, through)
    chord = sp.sqrt((1 + m**2) * (cs['ysum']**2 - 4 * cs['yprod']))
    # line x - m y - c = 0, distance from a point to the line d=|vx - m vy - c|/sqrt(1+m^2)
    vx, vy = sp.nsimplify(vertex[0]), sp.nsimplify(vertex[1])
    d = sp.Abs(vx - m * vy - cs['c']) / sp.sqrt(1 + m**2)
    return sp.simplify(sp.Rational(1, 2) * chord * d), cs


# ---------------- Range of values (key: includes open/closed endpoint determination) ----------------
def range_over_m(expr, horizontal_valid=True):
    """The range of the target quantity expr(m) over m∈ℝ; horizontal_valid=True means the horizontal
    line (m→∞) is also a valid line (e.g. a chord of an ellipse through an interior point), so its
    limiting value is also attained (endpoint closed).

    Returns dict: lo,hi (sympy), lo_closed,hi_closed, latex, lo_f,hi_f (float), argmax/argmin.
    """
    g = sp.simplify(expr)
    cand = []   # (value, attained?)

    # stationary points
    dg = sp.together(sp.diff(g, m))
    for r in sp.solve(sp.numer(dg), m):
        if r.is_real:
            cand.append((sp.simplify(g.subs(m, r)), True))
    # m=0 (vertical line, always valid)
    cand.append((sp.simplify(g.subs(m, 0)), True))
    # m→±∞ (horizontal line)
    Lp = sp.limit(g, m, sp.oo)
    cand.append((sp.simplify(Lp), bool(horizontal_valid) and Lp.is_finite))

    finite = [(v, a) for (v, a) in cand if v.is_finite]
    lo_val = min(finite, key=lambda t: fnum(t[0]))[0]
    hi_val = max(finite, key=lambda t: fnum(t[0]))[0]
    # unboundedness determination
    hi = sp.oo if (Lp == sp.oo or any((not v.is_finite and v == sp.oo) for v, _ in cand)) else hi_val
    lo = -sp.oo if (Lp == -sp.oo) else lo_val
    lo_closed = (lo != -sp.oo) and any(a for (v, a) in cand if sp.simplify(v - lo) == 0)
    hi_closed = (hi != sp.oo) and any(a for (v, a) in cand if sp.simplify(v - hi) == 0)
    return {
        'lo': lo, 'hi': hi, 'lo_closed': lo_closed, 'hi_closed': hi_closed,
        'lo_f': (None if lo == -sp.oo else fnum(lo)),
        'hi_f': (None if hi == sp.oo else fnum(hi)),
        'latex': interval_latex(lo, hi, lo_closed, hi_closed),
    }


# ---------------- Fixed value (independent of m) ----------------
def is_constant_in_m(expr):
    e = sp.simplify(expr)
    return sp.simplify(sp.diff(e, m)) == 0, sp.simplify(e.subs(m, 0))


def slope_product_central(conic, P):
    """P is a fixed point on the curve, A is a moving point on the curve, B is A's reflection about the center.
    Returns k_PA·k_PB (should be the fixed value -b²/a², independent of A's position)."""
    t = sp.symbols('t', real=True)
    cx, cy = conic['center']
    if conic['kind'] == 'ellipse':
        A = (cx + conic['a'] * sp.cos(t), cy + conic['b'] * sp.sin(t))
    else:
        raise ValueError("slope_product_central currently supports the ellipse")
    B = (2 * cx - A[0], 2 * cy - A[1])
    Px, Py = sp.nsimplify(P[0]), sp.nsimplify(P[1])
    kA = (A[1] - Py) / (A[0] - Px)
    kB = (B[1] - Py) / (B[0] - Px)
    prod = sp.simplify(sp.trigsimp(kA * kB))
    return prod


# ---------------- Eccentricity range (shape-parameter problem) ----------------
def ecc_range_focal_ratio(k):
    """A P exists on the right branch of the hyperbola with |PF₁| = k|PF₂| (k>1); find the range of e.

    Right-branch focal radii: |PF₁|−|PF₂|=2a and |PF₂|≥c−a. From k|PF₂|−|PF₂|=2a we get |PF₂|=2a/(k−1),
    and substituting into |PF₂|≥c−a gives e ≤ (k+1)/(k−1); also e>1. So e ∈ (1, (k+1)/(k−1)].
    Returns dict: lo,hi,lo_closed,hi_closed,lo_f,hi_f,latex,k.
    """
    k = sp.nsimplify(k)
    if k <= 1:
        raise ValueError("k must be > 1")
    hi = sp.simplify((k + 1) / (k - 1))
    lo = sp.Integer(1)
    return {
        'lo': lo, 'hi': hi, 'lo_closed': False, 'hi_closed': True,
        'lo_f': 1.0, 'hi_f': fnum(hi),
        'latex': interval_latex(lo, hi, False, True), 'k': k,
    }


# =====================================================================
# Self-check: flagship problem (ellipse x²/4+y²/3=1, M(-1,0), chord through F(1,0), MA·MB range)
# =====================================================================
if __name__ == "__main__":
    E = conics.ellipse(2, sp.sqrt(3))
    print("ellipse:", E['eq_latex'], " foci", E['foci'])

    expr, cs = dot_product_expr(E, (1, 0), (-1, 0))
    print("\nquadratic coefficients (A,B,C):", cs['A'], cs['B'], cs['C'])
    print("Vieta y1+y2 =", cs['ysum'], " y1y2 =", cs['yprod'])
    print("MA·MB(m) =", expr, "=", sp.simplify(expr.rewrite(sp.Add)))
    print("simplified:", sp.apart(expr, m))

    rg = range_over_m(expr, horizontal_valid=True)
    print("\nrange:", rg['latex'], " floats:", rg['lo_f'], rg['hi_f'],
          " closed:", rg['lo_closed'], rg['hi_closed'])
    assert rg['lo_f'] == -3.0 and abs(rg['hi_f'] - 1.75) < 1e-12, "flagship range should be [-3, 7/4]"
    assert rg['lo_closed'] and rg['hi_closed'], "both ends should be closed (horizontal line attains -3, vertical line attains 7/4)"
    print("\n✅ flagship self-check passed: MA·MB ∈", rg['latex'])

    # chord-length (through focus) range self-check: the ellipse latus rectum 2b²/a=3 is the shortest, the major axis 2a=4 is the longest
    cl2, _ = chord_len_sq_expr(E, (1, 0))
    rgc = range_over_m(cl2, horizontal_valid=True)
    print("chord length² range:", rgc['latex'], "→ chord length ∈ [",
          sp.sqrt(rgc['lo']), ",", sp.sqrt(rgc['hi']), "]")

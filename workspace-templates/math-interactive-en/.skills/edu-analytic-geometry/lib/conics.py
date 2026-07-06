#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conics.py — sympy exact-definition library for conic sections.

Each constructor returns a dict containing:
  kind / center / half-axes (a,b) or r / p ...  —— geometric parameters (sympy exact)
  c, foci, vertices, ecc, asymptotes, directrix —— special quantities (by curve type)
  implicit  : implicit expression in x,y = 0
  eq_latex  : standard-equation LaTeX
  board     : dict injected into the front-end engine board.conics[*] (floats)

Convention: a = x-direction half-axis, b = y-direction half-axis (ellipse); for a hyperbola
a=real half-axis, b=imaginary half-axis + orient.
Most exam problems have the center at the origin, so this focuses on the origin; the circle
supports an arbitrary center.
"""
import sympy as sp

x, y = sp.symbols('x y', real=True)


def _f(e):
    """sympy exact quantity → float."""
    return float(sp.N(e))


def _sq_latex(e):
    """Write a^2 as clean LaTeX as possible (integers shown directly)."""
    e = sp.nsimplify(e)
    return sp.latex(sp.simplify(e))


def _term(numer_latex, denom):
    """Fraction term: collapse to the numerator itself when the denominator is 1 (x^2/1 → x^2)."""
    denom = sp.simplify(sp.nsimplify(denom))
    if denom == 1:
        return numer_latex
    return r"\frac{%s}{%s}" % (numer_latex, _sq_latex(denom))


def ellipse(a, b, center=(0, 0)):
    """Ellipse (x-cx)^2/a^2 + (y-cy)^2/b^2 = 1. a=x half-axis, b=y half-axis. Foci on the major axis."""
    a, b = sp.nsimplify(a), sp.nsimplify(b)
    cx, cy = sp.nsimplify(center[0]), sp.nsimplify(center[1])
    if a == b:
        raise ValueError("a==b is a circle, use circle()")
    if a > b:                       # foci on the x-axis
        c = sp.sqrt(a**2 - b**2)
        foci = {'F1': (cx - c, cy), 'F2': (cx + c, cy)}
        ecc = c / a
        verts = {'A1': (cx - a, cy), 'A2': (cx + a, cy), 'B1': (cx, cy - b), 'B2': (cx, cy + b)}
    else:                           # foci on the y-axis
        c = sp.sqrt(b**2 - a**2)
        foci = {'F1': (cx, cy - c), 'F2': (cx, cy + c)}
        ecc = c / b
        verts = {'A1': (cx, cy - b), 'A2': (cx, cy + b), 'B1': (cx - a, cy), 'B2': (cx + a, cy)}
    implicit = (x - cx)**2 / a**2 + (y - cy)**2 / b**2 - 1
    if cx == 0 and cy == 0:
        eq_latex = r"%s+%s=1" % (_term("x^2", a**2), _term("y^2", b**2))
    else:
        eq_latex = r"\frac{(x-%s)^2}{%s}+\frac{(y-%s)^2}{%s}=1" % (
            sp.latex(cx), _sq_latex(a**2), sp.latex(cy), _sq_latex(b**2))
    return {
        'kind': 'ellipse', 'a': a, 'b': b, 'c': c, 'center': (cx, cy),
        'foci': foci, 'vertices': verts, 'ecc': ecc,
        'implicit': implicit, 'eq_latex': eq_latex,
        'board': {'kind': 'ellipse', 'a': _f(a), 'b': _f(b), 'center': [_f(cx), _f(cy)]},
    }


def hyperbola(a, b, center=(0, 0), orient='x'):
    """Hyperbola. orient='x': (x)^2/a^2-(y)^2/b^2=1 (foci on the x-axis); 'y' is the reverse. a=real half-axis, b=imaginary half-axis."""
    a, b = sp.nsimplify(a), sp.nsimplify(b)
    cx, cy = sp.nsimplify(center[0]), sp.nsimplify(center[1])
    c = sp.sqrt(a**2 + b**2)
    if orient == 'x':
        foci = {'F1': (cx - c, cy), 'F2': (cx + c, cy)}
        verts = {'A1': (cx - a, cy), 'A2': (cx + a, cy)}
        implicit = (x - cx)**2 / a**2 - (y - cy)**2 / b**2 - 1
        asym = (b / a, -b / a)
        eq_latex = r"%s-%s=1" % (_term("x^2", a**2), _term("y^2", b**2))
    else:
        foci = {'F1': (cx, cy - c), 'F2': (cx, cy + c)}
        verts = {'A1': (cx, cy - a), 'A2': (cx, cy + a)}
        implicit = (y - cy)**2 / a**2 - (x - cx)**2 / b**2 - 1
        asym = (a / b, -a / b)
        eq_latex = r"%s-%s=1" % (_term("y^2", a**2), _term("x^2", b**2))
    return {
        'kind': 'hyperbola', 'a': a, 'b': b, 'c': c, 'center': (cx, cy), 'orient': orient,
        'foci': foci, 'vertices': verts, 'ecc': c / a, 'asymptote_slopes': asym,
        'implicit': implicit, 'eq_latex': eq_latex,
        'board': {'kind': 'hyperbola', 'a': _f(a), 'b': _f(b), 'center': [_f(cx), _f(cy)],
                  'orient': orient, 'asymptotes': True},
    }


def parabola(p, vertex=(0, 0), axis='x'):
    """Parabola. axis='x': (y-cy)^2=2p(x-cx) (opening follows the sign of p); 'y': (x-cx)^2=2p(y-cy)."""
    p = sp.nsimplify(p)
    cx, cy = sp.nsimplify(vertex[0]), sp.nsimplify(vertex[1])
    if axis == 'x':
        focus = (cx + p / 2, cy)
        directrix = ('x', cx - p / 2)         # directrix x = cx - p/2
        implicit = (y - cy)**2 - 2 * p * (x - cx)
        eq_latex = (r"y^2=%s x" % sp.latex(2 * p)) if (cx == 0 and cy == 0) else \
                   (r"(y-%s)^2=%s(x-%s)" % (sp.latex(cy), sp.latex(2 * p), sp.latex(cx)))
    else:
        focus = (cx, cy + p / 2)
        directrix = ('y', cy - p / 2)
        implicit = (x - cx)**2 - 2 * p * (y - cy)
        eq_latex = (r"x^2=%s y" % sp.latex(2 * p)) if (cx == 0 and cy == 0) else \
                   (r"(x-%s)^2=%s(y-%s)" % (sp.latex(cx), sp.latex(2 * p), sp.latex(cy))
                    )
    return {
        'kind': 'parabola', 'p': p, 'vertex': (cx, cy), 'axis': axis,
        'focus': focus, 'directrix': directrix,
        'implicit': implicit, 'eq_latex': eq_latex,
        'board': {'kind': 'parabola', 'p': _f(p), 'center': [_f(cx), _f(cy)], 'axis': axis},
    }


def circle(center, r):
    """Circle (x-cx)^2+(y-cy)^2=r^2."""
    cx, cy = sp.nsimplify(center[0]), sp.nsimplify(center[1])
    r = sp.nsimplify(r)
    implicit = (x - cx)**2 + (y - cy)**2 - r**2
    if cx == 0 and cy == 0:
        eq_latex = r"x^2+y^2=%s" % _sq_latex(r**2)
    else:
        eq_latex = r"(x-%s)^2+(y-%s)^2=%s" % (sp.latex(cx), sp.latex(cy), _sq_latex(r**2))
    return {
        'kind': 'circle', 'center': (cx, cy), 'r': r,
        'implicit': implicit, 'eq_latex': eq_latex,
        'board': {'kind': 'circle', 'r': _f(r), 'center': [_f(cx), _f(cy)]},
    }


if __name__ == "__main__":
    e = ellipse(2, sp.sqrt(3))
    print("ellipse:", e['eq_latex'], "| foci", e['foci'], "| e =", e['ecc'])
    h = hyperbola(1, sp.sqrt(3))
    print("hyperbola:", h['eq_latex'], "| foci", h['foci'], "| asym", h['asymptote_slopes'])
    pa = parabola(2)
    print("parabola:", pa['eq_latex'], "| focus", pa['focus'], "| directrix", pa['directrix'])
    print("circle:", circle((0, 0), 2)['eq_latex'])

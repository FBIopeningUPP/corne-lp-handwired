"""Generative 'topographic' ripples: contour lines of (distance to some shapes + slow noise).

Used on the carry case: the lines flow around the keycaps on the lid and ripple out from the
signature under the tray, like rings in water. Deterministic (seeded), so every build matches.
"""
import numpy as np
import shapely
from contourpy import contour_generator
from scipy.ndimage import distance_transform_edt
from shapely.geometry import LineString
from shapely.ops import unary_union


def ripples(obstacles, region, spacing=2.0, width=0.6, amp=2.6, seed=7, res=0.25, first=1.2):
    x0, y0, x1, y1 = region.bounds
    xs = np.arange(x0 - 2, x1 + 2, res); ys = np.arange(y0 - 2, y1 + 2, res)
    X, Y = np.meshgrid(xs, ys)
    inside = shapely.contains_xy(obstacles, X, Y)
    d = distance_transform_edt(~inside) * res
    rng = np.random.default_rng(seed)
    n = np.zeros_like(X)
    for _ in range(5):                      # a few slow waves in random directions
        k = rng.uniform(1 / 70, 1 / 26); a = rng.uniform(0, np.pi); ph = rng.uniform(0, 2 * np.pi)
        n += np.sin(2 * np.pi * k * (X * np.cos(a) + Y * np.sin(a)) + ph)
    f = d + amp * n / 2.2 * np.clip(d / 6, 0, 1)      # rings hug the shapes, then start to wander
    gen = contour_generator(xs, ys, f)
    lines = []
    for lv in np.arange(first, f.max(), spacing):
        for seg in gen.lines(lv):
            if len(seg) > 4:
                lines.append(LineString(seg).simplify(0.04))
    g = unary_union([l.buffer(width / 2, quad_segs=3) for l in lines])
    g = g.intersection(region).difference(obstacles.buffer(0.6))
    return unary_union([p for p in getattr(g, "geoms", [g]) if p.area > 2.0])   # no crumbs

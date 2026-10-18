"""Finishing details on the base: engraving, interleaved feet pockets, power-switch finger dip.

All geometry is 2D (shapely) in the left half's frame; case.py and step.py cut it.

Feet: every base gets the same 10 shallow pockets. The left half sticks its 5 feet in set A,
the right half in set B. Stacked for the bag (bases together), each foot drops into an
empty pocket of the other half, so the bases still sit flat and the magnets touch.
"""
import os
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

FOOT_D, FOOT_DEPTH = 8.4, 0.5      # for 8 x 1 mm self-adhesive silicone feet
N_FEET = 5
TEXT_DEPTH = 0.3
NOTCH_DEPTH = 0.4
FONT = FontProperties(family="DejaVu Sans", weight="bold")


HERE = os.path.dirname(os.path.abspath(__file__))
SIGN_FONT = FontProperties(fname=os.path.join(HERE, "fonts", "mr-dafoe.ttf"))      # autograph brush script
LINE_FONT = FontProperties(fname=os.path.join(HERE, "fonts", "yellowtail.ttf"))    # small cursive line


def _script(s, size, font):
    """a whole string as one outline (keeps the joins of cursive letters), even-odd filled"""
    tp = TextPath((0, 0), s, size=size, prop=font)
    rings = [Polygon(p) for p in tp.to_polygons() if len(p) >= 3]
    rings = [r for r in rings if r.is_valid or r.buffer(0).area > 0]
    # nonzero fill: a counter (hole) belongs to the smallest outline that holds it; overlapping
    # strokes of neighbouring letters stay solid instead of cancelling out
    outer = [r for r in rings if r.exterior.is_ccw is False]
    holes = [r for r in rings if r.exterior.is_ccw is True]
    if not outer:                       # font wound the other way round
        outer, holes = holes, outer
    shapes = []
    for o in outer:
        ob = o.buffer(0)
        mine = [h.buffer(0) for h in holes if ob.contains(h.representative_point())
                and min((oo.buffer(0).area for oo in outer if oo.buffer(0).contains(h.representative_point())),
                        default=0) == ob.area]
        shapes.append(ob.difference(unary_union(mine)) if mine else ob)
    return unary_union(shapes)


def _swoosh(x0, x1, y):
    """hand-drawn underline: dips under the name, kicks up past the last letter, tapered ends"""
    P = np.array([[x0 + 0.04 * (x1 - x0), y - 0.6], [x0 + 0.42 * (x1 - x0), y - 3.6],
                  [x0 + 0.90 * (x1 - x0), y - 1.6], [x1 + 4.5, y + 3.2]])
    t = np.linspace(0, 1, 120)[:, None]
    c = ((1 - t) ** 3) * P[0] + 3 * ((1 - t) ** 2) * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]
    d = np.gradient(c, axis=0); n = np.stack([-d[:, 1], d[:, 0]], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
    w = (0.22 + 0.62 * np.sin(np.pi * t[:, 0]) ** 1.4)          # half-width, mm
    left, right = c + n * w[:, None], c - n * w[:, None]
    return Polygon(np.vstack([left, right[::-1]])).buffer(0)


def _label(side):
    name = _script("Corne", 15.0, SIGN_FONT)
    nb = name.bounds
    sw = _swoosh(nb[0], nb[2], nb[1] - 0.4)
    line = _script(("left" if side == "left" else "right") + " \u00b7 zmk \u00b7 42", 5.4, LINE_FONT)
    lb = line.bounds
    line = affinity.translate(line, nb[2] - lb[2] + 1.0, nb[1] - 5.6 - lb[3])   # tucked under the swoosh, right side
    g = unary_union([name, sw, line]).buffer(0.10)              # +0.2 mm stroke: prints fully with a 0.4 nozzle
    x0, y0, x1, y1 = g.bounds
    return affinity.translate(g, -(x0 + x1) / 2, -(y0 + y1) / 2)    # centred on (0, 0)


def base_details(C):
    B = C.BASE_CH
    screws = [Point(p).buffer(C.SCREW_HEAD / 2 + 1.0) for p in C.SCREWS]
    mags = [Point(p).buffer(C.MAG_D / 2 + 1.0) for p in C.MAGNETS]
    busy = unary_union(screws + mags + [C.BATT_RECT.buffer(1.2), Point(C.RST_C).buffer(4.0)])   # nothing engraved under the thin battery floor

    # --- engraving: biggest clear spot near the middle of the key area ---
    lab = _label("left")
    w, h = lab.bounds[2] - lab.bounds[0], lab.bounds[3] - lab.bounds[1]
    room = C.outer.buffer(-(B + 3.0))
    target = Point(45.0, -16.0)
    best = None
    for cx in np.arange(10, 100, 0.5):
        for cy in np.arange(-60, 10, 0.5):
            r = box(cx - w / 2 - 1.5, cy - h / 2 - 1.5, cx + w / 2 + 1.5, cy + h / 2 + 1.5)
            if room.contains(r) and not r.intersects(busy):
                d = Point(cx, cy).distance(target)
                if best is None or d < best[0]:
                    best = (d, (cx, cy))
    tcx, tcy = best[1]
    # read from below: mirror x for the left base (in this top-view frame)
    text_left = affinity.translate(affinity.scale(_label("left"), -1, 1, origin=(0, 0)), tcx, tcy)
    # right base is mirrored as a whole later, so its text goes in un-mirrored here
    text_right = affinity.translate(_label("right"), tcx, tcy)
    text_zone = box(tcx - w / 2 - 1.5, tcy - h / 2 - 1.5, tcx + w / 2 + 1.5, tcy + h / 2 + 1.5)

    # --- feet: 4 well-spread spots (A) + a partner spot for each (B) ---
    keep = unary_union([busy, text_zone])
    ok = C.outer.buffer(-(FOOT_D / 2 + B + 0.8)).difference(keep.buffer(FOOT_D / 2 + 0.6))
    x0, y0, x1, y1 = ok.bounds
    cands = [Point(x, y) for x in np.arange(x0, x1, 0.5) for y in np.arange(y0, y1, 0.5) if ok.contains(Point(x, y))]
    from shapely.geometry import MultiPoint
    cen = C.outer.centroid
    A = [max(cands, key=lambda p: p.distance(cen))]
    A.append(max(cands, key=lambda p: p.distance(A[0])))
    while len(A) < N_FEET:      # greedily grow the support area (no corner left to rock on)
        A.append(max(cands, key=lambda p: MultiPoint(A + [p]).convex_hull.area))
    Bs = []
    for a in A:
        pool = [p for p in cands if all(p.distance(q) >= FOOT_D + 1.5 for q in A + Bs)]
        near = [p for p in pool if p.distance(a) <= FOOT_D + 4.0] or pool
        Bs.append(max(near, key=lambda p: MultiPoint(Bs + [p]).convex_hull.area if len(Bs) >= 2
                      else p.distance(cen)))      # stay out in the corner, like its partner
    feet_A = [(round(p.x, 2), round(p.y, 2)) for p in A]
    feet_B = [(round(p.x, 2), round(p.y, 2)) for p in Bs]
    pockets = unary_union([Point(p).buffer(FOOT_D / 2, 64) for p in feet_A + feet_B])
    return dict(text_left=text_left, text_right=text_right,
                feet_A=feet_A, feet_B=feet_B, foot_pockets=pockets, text_center=(tcx, tcy))

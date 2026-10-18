"""Case style options. Each style turns the same key/bay/trackpad layout into an outline.

    python3 styles.py   -> out/case_styles.png (comparison sheet)
"""
import os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity
import case as C
import layout as L

U = L.U
caps = unary_union([Polygon(L.key_rect(k, U, U)) for k in C.keys])
thumb_big = Polygon(L.key_rect(C.keys[-1], U, U)).buffer(C.MARGIN, join_style=2)
lobe = Point(*C.TP_CENTER).buffer(C.TP_D / 2 + 1.4, 128)
main_block = unary_union([Polygon(L.key_rect(k, U, U)) for k in C.keys if k[4] < 3])
thumbs = unary_union([Polygon(L.key_rect(k, U, U)) for k in C.keys if k[4] == 3])


def round_(p, r):
    return p.buffer(-r, join_style=1).buffer(r, join_style=1)


def fill_notches(p, r):
    return p.buffer(r, join_style=1).buffer(-r, join_style=1)


STYLES = {
    "slab": dict(
        name="A · Slab",
        blurb="Current design. Clean diagonal inner edge, small chamfer. Balanced and sturdy.",
        edge=("chamfer", 0.8), wall=2.0,
        inner=lambda: round_(fill_notches(unary_union(
            [caps.buffer(C.MARGIN, join_style=2), C.BAY,
             unary_union([C.BAY, thumb_big, lobe]).convex_hull]), 6), 2)),
    "contour": dict(
        name="B · Contour",
        blurb="Hugs the column stagger like a classic Corne. Smallest footprint, lightest print.",
        edge=("chamfer", 0.4), wall=1.6,
        inner=lambda: round_(fill_notches(unary_union(
            [caps.buffer(0.6, join_style=2), C.BAY, lobe.buffer(-0.4),
             unary_union([C.BAY.buffer(-3), lobe.buffer(-6)]).convex_hull]), 2.5), 1.5)),
    "pebble": dict(
        name="C · Pebble",
        blurb="Big soft curves and a rounded edge. Feels like a smooth stone in the hand and the bag.",
        edge=("round", 1.8), wall=2.4,
        inner=lambda: round_(fill_notches(unary_union(
            [caps.buffer(C.MARGIN + 0.5, join_style=2), C.BAY, lobe,
             unary_union([C.BAY, thumb_big, lobe]).convex_hull]), 16), 9)),
    "faceted": dict(
        name="D · Faceted",
        blurb="Straight cuts and sharp 45° bevels. Angular and techy, like a stealth jet.",
        edge=("bevel", 1.4), wall=2.0,
        inner=lambda: round_(unary_union(
            [main_block.buffer(C.MARGIN, join_style=2).convex_hull,
             unary_union([thumbs, C.BAY, lobe, Polygon(L.key_rect(C.keys[14], U, U))])
             .buffer(C.MARGIN, join_style=2).convex_hull]), 0.6).simplify(0.8)),
}

def _rr(p, r):  # rounded version of a polygon's minimum rotated rectangle
    return p.minimum_rotated_rectangle.buffer(-r, join_style=2).buffer(r, join_style=1)

MINIMAL = {
    "frameless": dict(
        name="E · Frameless",
        blurb="Case stops 1 mm past the keycaps. Thin walls, straight sides. Keys do all the talking.",
        edge=("chamfer", 0.3), wall=1.4,
        inner=lambda: round_(fill_notches(unary_union(
            [caps.buffer(0.2, join_style=2), C.BAY.buffer(-0.8), lobe.buffer(-0.8),
             unary_union([C.BAY.buffer(-3), lobe.buffer(-6)]).convex_hull]), 3.5), 1.0)),
    "monolith": dict(
        name="F · Monolith",
        blurb="One clean shape per half, no notches. A single smooth outline, soft 5 mm corners.",
        edge=("chamfer", 0.4), wall=1.8,
        inner=lambda: round_(unary_union([caps.buffer(C.MARGIN, join_style=2), C.BAY, lobe])
                             .convex_hull, 5)),
    "block": dict(
        name="G · Block",
        blurb="Two plain rounded rectangles: keys and thumbs. Calm, architectural, very easy to read.",
        edge=("chamfer", 0.4), wall=1.8,
        inner=lambda: unary_union([
            _rr(unary_union([main_block, C.BAY]).buffer(C.MARGIN, join_style=2), 3),
            _rr(unary_union([thumbs, lobe]).buffer(C.MARGIN, join_style=2), 3)])),
    "floating": dict(
        name="H · Floating",
        blurb="Thin top plate overhangs a body tucked 1.5 mm in. The shadow line makes it look like it hovers.",
        edge=("undercut", 1.5), wall=2.9,
        inner=lambda: round_(fill_notches(unary_union(
            [caps.buffer(0.2, join_style=2), C.BAY.buffer(-0.8), lobe.buffer(-0.8),
             unary_union([C.BAY.buffer(-3), lobe.buffer(-6)]).convex_hull]), 3.5), 1.0)),
}
STYLES.update(MINIMAL)

from shapely.geometry import box as _box
def _bbox(g, pad):
    x0, y0, x1, y1 = g.bounds
    return _box(x0 - pad, y0 - pad, x1 + pad, y1 + pad)

everything = unary_union([caps, C.BAY, lobe])
SIMPLE = {
    "box": dict(
        name="I · Box",
        blurb="A plain rounded rectangle. Flat walls, 4 mm corners. Nothing else.",
        edge=("chamfer", 0.4), wall=1.8,
        inner=lambda: round_(_bbox(everything, C.MARGIN), 4)),
    "lbox": dict(
        name="J · Step",
        blurb="Two straight boxes, keys and thumbs, joined into one simple stepped shape.",
        edge=("chamfer", 0.4), wall=1.8,
        inner=lambda: round_(fill_notches(unary_union([
            _bbox(unary_union([main_block, C.BAY]), C.MARGIN),
            _bbox(unary_union([thumbs, lobe]), C.MARGIN)]), 4), 4)),
    "softbox": dict(
        name="K · Soft box",
        blurb="The same rectangle with big 14 mm corners. Friendly, simple, pocketable.",
        edge=("round", 1.2), wall=1.8,
        inner=lambda: round_(_bbox(everything, C.MARGIN + 1), 14)),
}
STYLES.update(SIMPLE)


def outlines(style):
    s = STYLES[style]
    inner = s["inner"]()
    join = 1 if s["edge"][0] != "bevel" else 2
    outer = inner.buffer(s["wall"], join_style=join)
    return inner, outer


def draw_half(ax, outer, mirror, dx, color, edge, pad=False):
    tf = (lambda g: affinity.translate(affinity.scale(g, -1, 1, origin=(0, 0)), dx, 0)) if mirror \
        else (lambda g: g)
    o = tf(outer)
    ax.add_patch(MPoly(np.array(o.exterior.coords), fc=color, ec="#1d1d1f", lw=1.1, zorder=1))
    # inner line shows where the edge treatment starts
    ins = o.buffer(-edge[1] * 1.6, join_style=1 if edge[0] != "bevel" else 2)
    for g in getattr(ins, "geoms", [ins]):
        ax.plot(*g.exterior.xy, color="#00000030", lw=.8, zorder=2)
    for k in C.keys:
        cap = tf(Polygon(L.key_rect(k, 17.6, 17.6)))
        ax.add_patch(MPoly(np.array(cap.exterior.coords), fc="#2b2b2e", ec="#111", lw=.5, zorder=3))
        inner_cap = cap.buffer(-1.6, join_style=2)
        ax.add_patch(MPoly(np.array(inner_cap.exterior.coords), fc="#38383c", ec="none", zorder=4))
    w = tf(C.WIN_RECT)
    ax.add_patch(MPoly(np.array(w.exterior.coords), fc="#0b0d10", ec="#000", lw=.6, zorder=3))
    if pad:
        t = tf(C.TP_DISC)
        ax.add_patch(MPoly(np.array(t.exterior.coords), fc="#1a1a1c", ec="#000", lw=.8, zorder=3))


def draw_profile(ax, edge, wall, x0, y0, color):
    """small cross-section of the outer edge, 4x scale"""
    s = 4.0
    H, B = C.H, C.BOTTOM_T
    kind, e = edge
    if kind == "undercut":
        pl = C.PLATE_T
        pts = [(x0 - 14 * s, y0 + H * s), (x0 + wall * s, y0 + H * s),
               (x0 + wall * s, y0 + (H - pl) * s), (x0 + (wall - e) * s, y0 + (H - pl) * s),
               (x0 + (wall - e) * s, y0 - B * s), (x0 + (wall - e - 1.4) * s, y0 - B * s),
               (x0 + (wall - e - 1.4) * s, y0 + (H - pl) * s), (x0 - 14 * s, y0 + (H - pl) * s)]
        ax.add_patch(MPoly(np.array(pts), fc=color, ec="#1d1d1f", lw=.8, zorder=5))
        return
    if kind == "round":
        t = np.linspace(0, np.pi / 2, 12)
        top = [(x0 + (wall - e + e * np.sin(a)) * s, y0 + (H - e + e * np.cos(a)) * s) for a in t]
    else:
        top = [(x0 + (wall - e) * s, y0 + H * s), (x0 + wall * s, y0 + (H - e) * s)]
    pts = [(x0, y0 - B * s), (x0 + wall * s, y0 - B * s), (x0 + wall * s, y0)] + \
          [(x0 + wall * s, y0 + (H - (e if kind != "round" else e)) * s)] + top[::-1] + \
          [(x0 - 14 * s, y0 + H * s), (x0 - 14 * s, y0 + (H - C.PLATE_T) * s), (x0, y0 + (H - C.PLATE_T) * s)]
    ax.add_patch(MPoly(np.array(pts), fc=color, ec="#1d1d1f", lw=.8, zorder=5))


if __name__ == "__main__":
    import sys
    sheet = sys.argv[1] if len(sys.argv) > 1 else "minimal"
    keys4 = {"first": ["slab", "contour", "pebble", "faceted"], "minimal": list(MINIMAL),
             "simple": list(SIMPLE)}[sheet]
    colors = {"slab": "#d9d4c8", "contour": "#cfd8dc", "pebble": "#e8d8c8", "faceted": "#c9c9cf",
              "frameless": "#e9e9e6", "monolith": "#dcdcd8", "block": "#e4e1da", "floating": "#ebeae6",
              "box": "#e6e5e1", "lbox": "#e6e5e1", "softbox": "#e6e5e1"}
    rows = 2 if len(keys4) > 3 else 1
    cols = 2 if len(keys4) > 3 else len(keys4)
    fig, axes = plt.subplots(rows, cols, figsize=(15, 9.6) if rows == 2 else (22, 5.4),
                             facecolor="#f5f3ee", squeeze=False)
    for ax, key in zip(axes.flat, keys4):
        s = STYLES[key]
        inner, outer = outlines(key)
        b = outer.bounds
        gap = 18
        dx = 2 * b[2] + gap
        if s["edge"][0] == "undercut":   # shadow under the floating plate
            for m, d in ((False, 0), (True, dx)):
                sh = affinity.translate(outer, 1.2, -1.8)
                if m:
                    sh = affinity.translate(affinity.scale(sh, -1, 1, origin=(0, 0)), d, 0)
                ax.add_patch(MPoly(np.array(sh.exterior.coords), fc="#00000022", ec="none", zorder=0))
        draw_half(ax, outer, False, 0, colors[key], s["edge"])
        draw_half(ax, outer, True, dx, colors[key], s["edge"], pad=True)
        w, d = b[2] - b[0], b[3] - b[1]
        ax.text(b[0], b[3] + 26, s["name"], fontsize=15, fontweight="bold", color="#1d1d1f")
        ax.text(b[0], b[3] + 17, s["blurb"], fontsize=9, color="#444")
        ax.text(b[0], b[3] + 9, f"each half {w:.0f} × {d:.0f} mm  ·  {outer.area/100:.0f} cm² footprint  ·  "
                f"edge: {s['edge'][1]} mm {s['edge'][0]}", fontsize=8.5, color="#555")
        px0 = dx / 2 + 30
        draw_profile(ax, s["edge"], s["wall"], px0, b[1] - 46, colors[key])
        ax.text(px0 - 60, b[1] - 44, "edge profile, 4× size →", fontsize=7.5, color="#666")
        ax.set_xlim(b[0] - 6, dx - b[0] + 6)
        ax.set_ylim(b[1] - 56, b[3] + 32)
        ax.set_aspect("equal"); ax.axis("off")
    plt.tight_layout(pad=1.5)
    name = {"first": "case_styles.png", "minimal": "case_styles_minimal.png",
            "simple": "case_styles_simple.png"}[sheet]
    plt.savefig(os.path.join(C.OUT, name), dpi=130, facecolor="#f5f3ee")
    print(name, "written")

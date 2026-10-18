"""Both bases seen from underneath: engraving, feet (which pocket gets a foot), magnets, screws."""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from shapely import affinity
import case as C
import details as DT

D = C.DETAILS
PAPER, BASE, INK = "#fbfaf7", "#d8d2c6", "#222"
fig, axes = plt.subplots(1, 2, figsize=(15, 5.6), facecolor=PAPER)


def fill(ax, g, **kw):
    for p in getattr(g, "geoms", [g]):
        ax.fill(*p.exterior.xy, **kw)
        for r in p.interiors:
            ax.fill(*r.xy, color=BASE)


for ax, side in zip(axes, ("left", "right")):
    # flipping a half over mirrors it: the left base shows mirrored, the right one (already a
    # mirror of the left frame) shows in the plain left-frame orientation
    if side == "left":
        M = lambda g: affinity.scale(g, -1, 1, origin=(0, 0)); P = lambda x, y: (-x, y)
    else:
        M = lambda g: g; P = lambda x, y: (x, y)
    fill(ax, M(C.outer), color=BASE, ec=INK, lw=1.2)
    text = D["text_left"] if side == "left" else D["text_right"]
    fill(ax, M(text), color="#6b6559")
    mine = D["feet_A"] if side == "left" else D["feet_B"]
    for p in D["feet_A"] + D["feet_B"]:
        has = p in mine
        ax.add_patch(Circle(P(*p), DT.FOOT_D / 2, fc="#2b2b2b" if has else BASE, ec="#555", lw=1, ls="-" if has else "--"))
        if has:
            ax.text(*P(*p), "foot", ha="center", va="center", color="w", fontsize=6.5)
    for p in C.MAGNETS:
        ax.add_patch(Circle(P(*p), C.MAG_D / 2, fc="#b9bec4", ec="#666"))
    for p in C.SCREWS:
        ax.add_patch(Circle(P(*p), C.SCREW_HEAD / 2, fc="#9a9fa6", ec="#555"))
        ax.add_patch(Circle(P(*p), 0.6, fc="#555"))
    ax.set_title(f"{side.upper()} base, seen from underneath  ·  foot in the dark pockets, dashed ones stay empty",
                 fontsize=9.5)
    ax.set_aspect("equal"); ax.axis("off")
plt.tight_layout()
plt.savefig(os.path.join(C.IMG_DIR, "bases_underneath.png"), dpi=150, facecolor=PAPER)
print("bases_underneath.png written")

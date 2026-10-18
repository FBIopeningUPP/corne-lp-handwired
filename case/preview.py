"""Drawings: top view of a half, both halves snapped, and a section through the bay."""
import os, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from shapely.geometry import Polygon
from shapely import affinity
import case as C
import layout as L

g = C.GEOM
INK, PAPER, CASE, HOLE = "#222", "#fbfaf7", "#e7e2d8", "#2b2b2b"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})

def fill(ax, poly, **kw):
    for p in getattr(poly, "geoms", [poly]):
        ax.fill(*p.exterior.xy, **kw)

def label(ax, poly, text, color="w", dy=0, size=7):
    ax.text(poly.centroid.x, poly.centroid.y + dy, text, ha="center", va="center", color=color, fontsize=size)

# ---------------- 1. top view of the left half, see-through ----------------
fig, ax = plt.subplots(figsize=(10, 7.4), facecolor=PAPER)
fill(ax, g["outer"], color=CASE, ec=INK, lw=1.3)
fill(ax, g["inner"], color="#f4f1ea", ec="#9a958b", lw=0.6, ls="--")
for h, k in zip(g["holes"], g["keys"]):
    fill(ax, h, color=HOLE)
    ax.text(k[0], k[1], f"R{k[4]}C{k[5]}", color="#ddd", ha="center", va="center", fontsize=6)
fill(ax, g["batt"], color="#d9a441", alpha=.95)
fill(ax, g["mcu"], color="#2f5d8a", alpha=.80)
fill(ax, g["oled"], color="#3c3c3c", alpha=.85)
fill(ax, g["win"], color="#7fe0ff", alpha=.9)
fill(ax, g["sw"], color="#b03a2e")
label(ax, g["win"], "OLED\nwindow", color="#033", size=6.5)
mcu = g["mcu"]
ax.text(mcu.centroid.x, mcu.centroid.y + 4, "SuperMini", ha="center", va="center",
        fontsize=6.5, color="w")
ax.annotate("USB-C", (C.mcu_cx, g["outer"].bounds[3] - 4), (C.mcu_cx, g["outer"].bounds[3] + 6),
            ha="center", fontsize=7, arrowprops=dict(arrowstyle="->", lw=.8))
ax.annotate("power switch\n(side wall)", (g["sw"].bounds[2], g["sw"].centroid.y),
            (g["outer"].bounds[2] + 4, g["sw"].centroid.y + 2), fontsize=6.5, ha="left", va="center",
            arrowprops=dict(arrowstyle="->", lw=.7))
fill(ax, C.RST_RECT, color="#8d939b", ec="#222", lw=.5)
ax.annotate("reset button\n(pinhole in base)", (C.RST_RECT.bounds[2], C.RST_C[1]), (g["outer"].bounds[2] + 4, C.RST_C[1] - 9), fontsize=6.5,
            ha="left", va="center", arrowprops=dict(arrowstyle="->", lw=.7))
fill(ax, g["tp"], color="#9b7fd1", alpha=.9)
label(ax, g["tp"], "Cirque\n23 mm\n(right half)", size=6.5)
for (x, y) in g["magnets"]:
    ax.add_patch(Circle((x, y), C.MAG_D / 2, color="#4a4a4a"))
    ax.add_patch(Circle((x, y), C.MAG_D / 2 - 1.2, color="#bdbdbd"))
mx, my = g["magnets"][0]
ax.annotate("magnet (in base)", (mx, my), (mx + 2, my - 14), fontsize=6.5,
            arrowprops=dict(arrowstyle="->", lw=.7))
for (x, y) in g["bosses"]:
    ax.add_patch(Circle((x, y), C.BOSS_D / 2, color="#c0392b", alpha=.75))
    ax.add_patch(Circle((x, y), C.SCREW_PILOT / 2, color="w"))
for (x, y) in g["posts"]:
    ax.add_patch(Circle((x, y), C.POST_D / 2, color="#c0392b", alpha=.75))
    ax.add_patch(Circle((x, y), C.SCREW_PILOT / 2, color="w"))
b = g["outer"].bounds
ax.set_title(f"Left half (see-through) · {b[2]-b[0]:.0f} × {b[3]-b[1]:.0f} mm · "
             f"{C.H + C.BOTTOM_T:.1f} mm tall without keycaps", fontsize=10, color=INK, pad=28)
ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(b[0] - 4, b[2] + 22)
plt.tight_layout(); plt.savefig(os.path.join(C.IMG_DIR, "top_view.png"), dpi=150, facecolor=PAPER)

# ---------------- 2. halves snapped together ----------------
fig, ax = plt.subplots(figsize=(11, 4.6), facecolor=PAPER)
x_join = g["outer"].bounds[2] + 6
right = lambda p: affinity.translate(affinity.scale(p, -1, 1, origin=(0, 0)), 2 * x_join, 0)
for part in (lambda p: p, right):
    fill(ax, part(g["outer"]), color=CASE, ec=INK, lw=1.2)
    for k in g["keys"]:
        fill(ax, part(Polygon(L.key_rect(k, 17.4, 17.4))), color="#fdfdfb", ec="#8d877b", lw=.7)
    fill(ax, part(g["win"]), color="#7fe0ff")
fill(ax, right(g["tp"]), color="#9b7fd1")
ax.set_title(f"In use, {2 * (x_join - g['outer'].bounds[0]):.0f} mm across (halves can sit at any distance)", fontsize=10)
ax.set_aspect("equal"); ax.axis("off")
plt.tight_layout(); plt.savefig(os.path.join(C.IMG_DIR, "in_use.png"), dpi=150, facecolor=PAPER)

# ---------------- 3. sections through the bay (y-z), one per column ----------------
fig, axes = plt.subplots(3, 1, figsize=(10, 8.6), facecolor=PAPER)

def section(m, xcut):
    s_ = m.translate([-xcut, 0, 0]).rotate([0, 90, 0]).slice(0.0)
    return [np.array(poly) for poly in s_.to_polygons()]

def box_yz(ax, rect, z0, z1, color, text="", tc="w"):
    y0, y1 = rect.bounds[1], rect.bounds[3]
    ax.add_patch(Rectangle((y0, z0), y1 - y0, z1 - z0, color=color, alpha=.92))
    if text:
        ax.text((y0 + y1) / 2, (z0 + z1) / 2, text, ha="center", va="center", fontsize=6.5, color=tc)

def case_cut(ax, xcut, title):
    for m, col in [(C.shell, "#cfc8b9"), (C.bottom, "#9d968a")]:
        for poly in section(m, xcut):
            ax.fill(poly[:, 1], poly[:, 0], color=col, ec=INK, lw=.6)
    ax.set_xlim(min(g["sw"].bounds[1], g["batt"].bounds[1]) - 6, g["outer"].bounds[3] + 4); ax.set_ylim(-C.BOTTOM_T - 1.5, C.H + 1.5)
    ax.set_aspect("equal"); ax.axis("off"); ax.set_title(title, fontsize=9.5, loc="left")

ax = axes[0]
case_cut(ax, C.mcu_cx + 2.0, f"Through the OLED + SuperMini  ·  shell {C.H:.1f} mm + base {C.BOTTOM_T:.1f} mm = {C.H + C.BOTTOM_T:.1f} mm")
box_yz(ax, g["mcu"], C.MCU_RAIL, C.MCU_RAIL + 1.0, "#2f5d8a")
ax.text(g["mcu"].centroid.y, C.MCU_RAIL + 0.5, "SuperMini on 1 mm rails", ha="center", va="center", fontsize=6, color="w")
ax.add_patch(Rectangle((g["mcu"].bounds[3] - 7.4, C.MCU_RAIL + 1.0), 8.2, 3.2, color="#666"))
ax.text(g["mcu"].bounds[3] - 3.3, C.MCU_RAIL + 2.6, "USB-C", ha="center", fontsize=6, color="w")
zg = C.H - C.BEZEL_T
box_yz(ax, g["glass"], zg - C.GLASS_T, zg, "#1b1b1b", "OLED glass")
y0, y1 = g["oled"].bounds[1], g["oled"].bounds[3]
ax.add_patch(Rectangle((y0, zg - C.GLASS_T - C.OLED_PCB_T), y1 - y0, C.OLED_PCB_T, color="#3b5e3b"))

ax = axes[1]
case_cut(ax, g["batt"].centroid.x, "Through the battery (under the thumb lobe)")
box_yz(ax, g["batt"], 0, C.BATT_T, "#d9a441", "LiPo WLY450838, 120 mAh")

# switch: cut across the case at the switch (x-z plane)
ax = axes[2]
for m, col in [(C.shell, "#cfc8b9"), (C.bottom, "#9d968a")]:
    for poly in [np.array(q) for q in m.translate([0, -C.SW_YC, 0]).rotate([-90, 0, 0]).slice(0.0).to_polygons()]:
        ax.fill(poly[:, 0], poly[:, 1], color=col, ec=INK, lw=.6)
x0 = C.SW_FACE - C.SW_BODY_D
ax.add_patch(Rectangle((x0, C.SW_Z0), C.SW_BODY_D, C.SW_BODY_H, color="#2b2b2b"))
ax.text(x0 + C.SW_BODY_D / 2, C.SW_ZC, "SS-12D06", ha="center", va="center", fontsize=6, color="w")
ax.add_patch(Rectangle((C.SW_FACE, C.SW_ZC - C.SW_KNOB_W / 2), C.SW_KNOB_L, C.SW_KNOB_W, color="#555"))
ax.add_patch(Rectangle((x0 - C.SW_PIN_L, C.SW_ZC - 0.25), C.SW_PIN_L, 0.5, color="#c9a227"))
ax.text(x0 - C.SW_PIN_L - 0.3, C.SW_ZC, "pins", ha="right", va="center", fontsize=6)
gx0, gx1 = g["oled"].bounds[0], g["oled"].bounds[2]
zg = C.H - C.BEZEL_T
ax.add_patch(Rectangle((gx0, zg - C.GLASS_T - C.OLED_PCB_T), gx1 - gx0, C.OLED_PCB_T, color="#3b5e3b"))
ax.text(gx1 - 3, zg - C.GLASS_T - 0.5, "OLED", ha="right", va="center", fontsize=6, color="w")
ax.annotate("knob sticks out ~2 mm", (C.SW_XOUT, C.SW_ZC), (C.SW_XOUT + 3, C.SW_ZC + 2.5),
            fontsize=6.5, arrowprops=dict(arrowstyle="->", lw=.7))
ax.set_xlim(gx1 - 14, C.SW_XOUT + 16); ax.set_ylim(-C.BOTTOM_T - 1, C.H + 1.5)
ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Across the power switch (inner side wall on the right)", fontsize=9.5, loc="left")
plt.tight_layout(); plt.savefig(os.path.join(C.IMG_DIR, "section.png"), dpi=170, facecolor=PAPER)
print("drawings written")

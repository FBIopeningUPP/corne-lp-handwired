"""Wiring diagrams.

  docs/images/diagrams/wiring_matrix.png    key matrix schematic (the same for both halves)
  docs/images/diagrams/wiring_left.png      everything in the left half, seen from UNDERNEATH (the way you solder it)
  docs/images/diagrams/wiring_right.png     same for the right half (adds the trackpad)
  docs/images/diagrams/supermini_pinout.png the board as you hold it (components up, USB-C at the top) with every pad named
  docs/wiring_guide.pdf                     all four, one per page, for printing

Pads are named the way the SuperMini nRF52840 prints them (006, 022, 111, ...), with the
ZMK / Pro Micro name next to them (D1, D4, D14, ...).
"""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Polygon as MPoly
import case as C

plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]
BG, INK, MUTED, CASE = "#fbfaf7", "#1d1d1f", "#6b6b70", "#ece8df"

# ---------------- signals ----------------
ROW_COL = ["#d1342f", "#e8851a", "#2e9d4a", "#8a4fd0"]
COL_COL = ["#1f5fa8", "#2b78c9", "#3c93d9", "#18a0b8", "#0e8f8f", "#3a6fd8"]
ROWS = [("R0", "D4", "022"), ("R1", "D5", "024"), ("R2", "D6", "100"), ("R3", "D7", "011")]
COLS = [("C0", "D21", "031"), ("C1", "D20", "029"), ("C2", "D19", "002"),
        ("C3", "D18", "115"), ("C4", "D15", "113"), ("C5", "D14", "111")]
OLED = [("GND", "GND", "#222"), ("VCC", "VCC", "#c0392b"), ("SCL", "020", "#c77d00"), ("SDA", "017", "#b8860b")]
TP = [("1 SCK", "104"), ("2 MISO", "008"), ("3 SS", "006"), ("4 DR", "010"), ("5 MOSI", "106"),
      ("11 GND", "GND"), ("12 VDD", "VCC")]
TP_COL = "#7b3fbf"

# SuperMini pads, components up, USB-C at the top. u = mm right of centre, v = mm down from the USB edge
LEFT_COL = ["B-", "006", "008", "GND", "GND", "017", "020", "022", "024", "100", "011", "104", "106"]
RIGHT_COL = ["B+", "RAW", "GND", "RST", "VCC", "031", "029", "002", "115", "113", "111", "010", "009"]
DNAME = {"006": "D1", "008": "D0", "017": "D2", "020": "D3", "022": "D4", "024": "D5", "100": "D6",
         "011": "D7", "104": "D8", "106": "D9", "031": "D21", "029": "D20", "002": "D19", "115": "D18",
         "113": "D15", "111": "D14", "010": "D16", "009": "D10"}
PITCH, HALF_W, V0 = 2.54, 7.62, 1.6
BOARD_W, BOARD_L = 18.0, 33.0


def pads_local():
    out = {}
    for i, n in enumerate(LEFT_COL):
        out.setdefault(n, []).append((-HALF_W, V0 + i * PITCH))
    for i, n in enumerate(RIGHT_COL):
        out.setdefault(n, []).append((HALF_W, V0 + i * PITCH))
    return out


PADS = pads_local()


def legend_block(ax, x, y, lines, size=8.2):
    for t, c, bold in lines:
        if t == "":
            y -= 2.2; continue
        ax.text(x, y, t, fontsize=size, color=c, fontweight="bold" if bold else "normal", va="top")
        y -= 4.6 if bold else 4.2
    return y


# ---------------- 1. matrix schematic ----------------
def matrix(ax):
    ax.set_facecolor(BG)
    dx, dy = 26, 22
    x0, y0 = 20, 0
    for c, (cn, d, silk) in enumerate(COLS):
        x = x0 + c * dx
        top, bot = y0 + 10, y0 - 3 * dy - 8 if c >= 3 else y0 - 2 * dy - 8
        ax.plot([x, x], [top, bot], color=COL_COL[c], lw=2.4, solid_capstyle="round")
        ax.text(x, top + 3, f"{cn}", ha="center", fontsize=11, fontweight="bold", color=COL_COL[c])
        ax.text(x, top + 9.5, f"{silk}", ha="center", fontsize=10, color=INK, fontweight="bold")
        ax.text(x, top + 15, f"{d}", ha="center", fontsize=8.5, color=MUTED)
    for r, (rn, d, silk) in enumerate(ROWS):
        y = y0 - r * dy - 12
        xa = x0 - 6 if r < 3 else x0 + 3 * dx - 6
        xb = x0 + 5 * dx + 16
        ax.plot([xa, xb], [y, y], color=ROW_COL[r], lw=2.4, solid_capstyle="round")
        ax.text(xb + 3, y, f"{rn}  →  {silk}", va="center", fontsize=11, fontweight="bold", color=ROW_COL[r])
        ax.text(xb + 3, y - 5, f"{d}", va="center", fontsize=8.5, color=MUTED)
        for c in range(6):
            if r == 3 and c < 3:
                continue
            x = x0 + c * dx
            yk = y0 - r * dy
            # switch: column wire -> pin A, pin B -> diode -> row wire
            ax.plot([x, x + 5], [yk, yk], color=COL_COL[c], lw=1.4)
            ax.add_patch(FancyBboxPatch((x + 5, yk - 4.5), 10, 9, boxstyle="round,pad=0.6", fc="#fff", ec="#888", lw=1))
            ax.text(x + 10, yk + 0.2, "SW", ha="center", va="center", fontsize=6.5, color=MUTED)
            ax.plot([x + 15, x + 18], [yk, yk], color=INK, lw=1.4)
            ax.plot([x + 18, x + 18], [yk, yk - 3.5], color=INK, lw=1.4)
            # diode: triangle pointing down (anode at the switch), bar = band = cathode at the row
            ax.add_patch(MPoly([[x + 15.8, yk - 3.5], [x + 20.2, yk - 3.5], [x + 18, yk - 7.2]], closed=True, fc=INK, ec=INK))
            ax.plot([x + 15.6, x + 20.4], [yk - 7.4, yk - 7.4], color=INK, lw=2.2)
            ax.plot([x + 18, x + 18], [yk - 7.4, y], color=INK, lw=1.4)
            ax.plot([x + 18], [y], "o", ms=4, color=ROW_COL[r])
            ax.plot([x], [yk], "o", ms=4, color=COL_COL[c])
    ax.text(x0 - 6, y0 - 3 * dy - 22,
            "Same wiring on both halves. C0 is the outer pinky column on each half; the 3 thumb keys sit on R3 under C3, C4, C5.\n"
            "Each key: column wire → switch pin, other switch pin → diode → row wire.  Diode band (cathode) toward the ROW.  "
            "1N4148 diodes.", fontsize=8.8, color=INK, va="top", linespacing=1.6)
    # diode inset
    ix, iy = x0 + 5 * dx + 44, y0 - 66
    ax.add_patch(Rectangle((ix - 2, iy - 7), 26, 20, fc="#fff", ec="#ccc"))
    ax.add_patch(Rectangle((ix + 4, iy), 12, 4, fc="#e9a000" if False else "#d36f2a", ec="none"))
    ax.add_patch(Rectangle((ix + 13.5, iy), 2.5, 4, fc="#222", ec="none"))
    ax.plot([ix, ix + 4], [iy + 2, iy + 2], color="#999", lw=1.4); ax.plot([ix + 16, ix + 22], [iy + 2, iy + 2], color="#999", lw=1.4)
    ax.text(ix + 11, iy + 9.5, "1N4148", ha="center", fontsize=7.5, color=INK)
    ax.text(ix + 21, iy - 4, "band → row", ha="right", fontsize=7.5, color=INK)
    ax.text(ix, iy - 4, "switch", ha="left", fontsize=7.5, color=MUTED)
    ax.set_title("Key matrix (col2row): 4 rows × 6 columns, 21 keys per half", fontsize=13, pad=14, color=INK)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(x0 - 14, x0 + 5 * dx + 74); ax.set_ylim(y0 - 3 * dy - 34, y0 + 26)


# ---------------- 2. full wiring per half (underside view) ----------------
def signals(side):
    """pad -> (label, colour) for one half"""
    m = {}
    for i, (n, d, sk) in enumerate(ROWS): m[sk] = (f"{n} row", ROW_COL[i])
    for i, (n, d, sk) in enumerate(COLS): m[sk] = (f"{n} column", COL_COL[i])
    m.update({"017": ("OLED SDA", "#b8860b"), "020": ("OLED SCL", "#c77d00"),
              "VCC": ("OLED VCC" + (" + pad VDD" if side == "right" else ""), "#c0392b"),
              "GND": ("OLED GND" + (" / pad GND" if side == "right" else ""), "#222"),
              "B+": ("switch outer pin", "#d1342f"), "B-": ("battery −", "#222"),
              "RST": ("reset button", "#5b6068")})
    if side == "right":
        m.update({"104": ("pad 1 SCK", TP_COL), "008": ("pad 2 MISO", TP_COL), "006": ("pad 3 SS", TP_COL),
                  "010": ("pad 4 DR", TP_COL), "106": ("pad 5 MOSI", TP_COL)})
    return m


def board_back(ax, side):
    """the SuperMini as you see it while wiring (from its back), enlarged, every pad named"""
    sig = signals(side)
    s = 3.0
    ax.set_facecolor(BG)
    ax.add_patch(FancyBboxPatch((-BOARD_W / 2 * s, -BOARD_L * s), BOARD_W * s, BOARD_L * s, boxstyle="round,pad=0.6",
                                fc="#23262b", ec="#111"))
    ax.add_patch(Rectangle((-4.5 * s, -0.6 * s), 9 * s, 1.4 * s, fc="#c3c8cf", ec="#777"))
    ax.text(0, 2.2 * s, "USB-C end (toward the back wall)", ha="center", fontsize=8, color=MUTED)
    ax.text(0, -BOARD_L / 2 * s, "SuperMini\nseen from its back\n(components face\nthe OLED)", ha="center", va="center",
            fontsize=7, color="#bbb")
    for col_names, u in ((LEFT_COL, -HALF_W), (RIGHT_COL, HALF_W)):
        vx = -u * s                                  # from the back: columns swap
        right = vx > 0
        for i, n in enumerate(col_names):
            y = -(V0 + i * PITCH) * s
            what, colr = sig.get(n, ("", "#b5b5b5"))
            ax.add_patch(Circle((vx, y), 0.95 * s, fc=colr if what else "#6d6d6d", ec="#d4a93c", lw=1.2))
            lab = n + (f" ({DNAME[n]})" if n in DNAME else "")
            t1 = f"{lab}   {what or '—'}" if right else f"{what or '—'}   {lab}"
            ax.text(vx + (1.9 if right else -1.9) * s, y, t1, ha="left" if right else "right", va="center",
                    fontsize=7.6, color=colr if what else "#999", fontweight="bold" if what else "normal")
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-BOARD_W * s * 2.3, BOARD_W * s * 2.3); ax.set_ylim(-(BOARD_L + 3) * s, 5 * s)


def half(ax, side):
    fl = -1 if side == "left" else 1                 # underside view: view_x = fl * x (left-half frame)
    V = lambda x, y: (fl * x, y)
    mcx, board_top = C.mcu_cx, C.mcu_top
    PV = lambda u, v: (fl * mcx - u, board_top - v)
    ax.set_facecolor(BG)
    xs, ys = C.outer.exterior.xy
    ax.fill([fl * x for x in xs], ys, color=CASE, ec="#555", lw=1, zorder=0)

    def wire(pts, col, lw=1.6, ls="-", z=5):
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=lw, ls=ls, zorder=z, solid_capstyle="round")

    def stub(p, text, col, dx=0, dy=0, ha="center", va="center", size=6.4):
        ax.text(p[0] + dx, p[1] + dy, text, ha=ha, va=va, fontsize=size, color=col, fontweight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.18", fc=BG, ec="none", alpha=.85))

    # components
    bx, by = C.BATT_RECT.exterior.xy
    ax.fill([fl * x for x in bx], by, color="#e7b54a", alpha=.6, ec="#b8862a", lw=1, zorder=1)
    bcx, bcy = C.BATT_C
    ox0, oy0, ox1, oy1 = C.OLED_RECT.bounds
    ax.add_patch(Rectangle((min(fl * ox0, fl * ox1), oy0), ox1 - ox0, oy1 - oy0, fc="none", ec="#2a5a3c", lw=1.1, ls="--", zorder=2))
    if side == "right":
        tx, ty = C.TP_CENTER
        ax.add_patch(Circle(V(tx, ty), C.TP_D / 2, fc="#d9caef", ec=TP_COL, lw=1, alpha=.55, zorder=1))
    bxv = fl * mcx
    ax.add_patch(Rectangle((bxv - BOARD_W / 2, board_top - BOARD_L), BOARD_W, BOARD_L, fc="#23262b", ec="#111", zorder=3))
    ax.add_patch(Rectangle((bxv - 4.5, board_top - 0.3), 9, 1.4, fc="#b9bec5", ec="#777", zorder=3))
    for n, locs in PADS.items():
        for (u, v) in locs:
            ax.add_patch(Circle(PV(u, v), 0.75, fc="#d4a93c", ec="none", zorder=4))
    ax.text(bxv, board_top - BOARD_L / 2, "SuperMini\n(OLED sits\non top)", ha="center", va="center", color="#ddd", fontsize=5.6, zorder=4)
    sx0, sy0, sx1, sy1 = C.SW_RECT.bounds
    ax.add_patch(Rectangle((min(fl * sx0, fl * sx1), sy0), abs(sx1 - sx0), sy1 - sy0, fc="#333", ec="none", zorder=3))

    # keys and the matrix
    pos = {}
    for k in C.keys:
        x, y, r, wu, row, col = k
        cx, cy = V(x, y); pos[(row, col)] = (cx, cy)
        ax.add_patch(FancyBboxPatch((cx - 6.5, cy - 6.5), 13, 13, boxstyle="round,pad=0.4", fc="#fff", ec="#aaa", lw=.7, zorder=1))
        ax.text(cx, cy + 3, f"R{row}C{col}", ha="center", fontsize=5.4, color="#999", zorder=2)
        ax.plot([cx - 3], [cy - 1.5], "o", ms=3.2, color=COL_COL[col], zorder=6)
        ax.plot([cx + 3], [cy - 1.5], "o", ms=3.2, color="#333", zorder=6)
        ax.plot([cx + 3, cx + 3], [cy - 1.5, cy - 6.5], color="#333", lw=.9, zorder=5)
        ax.add_patch(Rectangle((cx + 2, cy - 5.8), 2, 3, color="#444", zorder=6))
        ax.add_patch(Rectangle((cx + 2, cy - 5.8), 2, 0.7, color="#ddd", zorder=7))
    edge_x = bxv - fl * (BOARD_W / 2 + 4)            # where row wires stop, just before the board
    for r, (rn, d, sk) in enumerate(ROWS):
        pts = sorted([(p[0] + 3, p[1] - 6.5) for (rr, c), p in pos.items() if rr == r], key=lambda q: fl * q[0])
        wire(pts, ROW_COL[r], 2.1)
        end = pts[-1]
        tgt = PV(-HALF_W, V0 + LEFT_COL.index(sk) * PITCH)
        wire([end, (end[0] + fl * 4, end[1]), (tgt[0], tgt[1])], ROW_COL[r], 1.3, (0, (3, 1.5)))
        stub(end, f"{rn} → {sk}", ROW_COL[r], dx=fl * 7, dy=-2.6)
    for c, (cn, d, sk) in enumerate(COLS):
        pts = sorted([(p[0] - 3, p[1] - 1.5) for (rr, cc), p in pos.items() if cc == c], key=lambda q: -q[1])
        wire(pts, COL_COL[c], 1.8)
        top = pts[0]
        lane = C.inner_top - 0.6 - c * 0.9
        tgt = PV(HALF_W, V0 + RIGHT_COL.index(sk) * PITCH)
        wire([top, (top[0], lane), (tgt[0] - fl * (1.6 + 0.0), lane), (tgt[0] - fl * 1.6, tgt[1]), tgt], COL_COL[c], 1.1, (0, (3, 1.5)))
        stub((top[0], C.inner_top + 2.2), f"{cn} → {sk}", COL_COL[c])

    # OLED pins (header end, toward the thumbs)
    for i, (nm, sk, colr) in enumerate(OLED):
        p = V(C.oled_cx + (i - 1.5) * 2.54, oy0 + 1.6)
        ax.plot(*p, "s", ms=3.6, color=colr, zorder=7)
    stub(V((ox0 + ox1) / 2, oy0 - 3.2), "OLED pins: GND→GND  VCC→VCC  SCL→020  SDA→017", "#2a5a3c", size=5.2)
    # battery & switch
    bl = min(C.BATT_RECT.exterior.coords, key=lambda q: fl * q[0])
    stub(V(*bl), "LiPo 120 mAh: + → switch middle pin,  − → B−", "#7a5512", dx=-fl * 1, dy=-5.5, ha="right" if fl > 0 else "left", size=5.4)
    stub(V(C.SW_FACE - C.SW_BODY_D / 2, sy0 - 2.2), "switch: outer pin → B+", "#d1342f", size=5.4)
    # rescue reset button (face-down on the base, under the pinhole)
    rx0, ry0, rx1, ry1 = C.RST_RECT.bounds
    ax.add_patch(Rectangle((min(fl * rx0, fl * rx1), ry0), abs(rx1 - rx0), ry1 - ry0, fc="#5b6068", ec="#222", lw=.6, zorder=3))
    stub(V(C.RST_C[0], ry0 - 1.0), "reset button: one leg → RST, other → GND", "#5b6068", size=5.2)
    # trackpad pins
    if side == "right":
        import math
        tx, ty = C.TP_CENTER
        for i, (nm, sk) in enumerate(TP):
            ang = math.radians(118 + i * 14)
            p = V(tx + (C.TP_D / 2 - 1.8) * math.cos(ang), ty + (C.TP_D / 2 - 1.8) * math.sin(ang))
            ax.plot(*p, "o", ms=2.8, color=TP_COL, zorder=7)
        stub(V(tx + 1, ty - 1), "Cirque pad (back):\n1 SCK→104  2 MISO→008\n3 SS→006  4 DR→010\n5 MOSI→106  11 GND→GND\n12 VDD→VCC (never B+)",
             TP_COL, size=5.3)

    b = C.outer.bounds
    ax.text(min(fl * b[0], fl * b[2]), b[1] - 5,
            "Seen from underneath, plate face-down: the way you solder. Solid = wires along the keys, dashed = runs to the board "
            "(keep them flat along the back wall and beside the battery, never over it).\n"
            "Pad names are as printed on your SuperMini. 30 AWG silicone wire. Solder the trackpad and OLED wires first, then the "
            "matrix.", fontsize=7.4, color=MUTED, va="top", linespacing=1.6)
    ax.set_title(f"{side.upper()} half: complete wiring, seen from underneath", fontsize=13, color=INK, pad=10)
    ax.set_aspect("equal"); ax.axis("off")
    xa, xb = min(fl * b[0], fl * b[2]), max(fl * b[0], fl * b[2])
    ax.set_xlim(xa - 4, xb + 4); ax.set_ylim(b[1] - 16, b[3] + 8)


# ---------------- 3. pinout ----------------
def pinout(ax):
    ax.set_facecolor(BG)
    used = {}
    for n, d, s in ROWS: used[s] = (f"{n} row", ROW_COL[int(n[1])])
    for i, (n, d, s) in enumerate(COLS): used[s] = (f"{n} column", COL_COL[i])
    used.update({"017": ("OLED SDA", "#b8860b"), "020": ("OLED SCL", "#c77d00"), "VCC": ("OLED + pad 3.3 V", "#c0392b"),
                 "GND": ("GND", "#222"), "B+": ("battery + (via switch)", "#d1342f"), "B-": ("battery −", "#222"),
                 "104": ("pad SCK (right)", TP_COL), "106": ("pad MOSI (right)", TP_COL), "008": ("pad MISO (right)", TP_COL),
                 "006": ("pad SS (right)", TP_COL), "010": ("pad DR (right)", TP_COL), "009": ("free", "#aaa"),
                 "RAW": ("not used", "#aaa"), "RST": ("reset button", "#5b6068")})
    s = 3.2
    ax.add_patch(FancyBboxPatch((-BOARD_W / 2 * s, -BOARD_L * s), BOARD_W * s, BOARD_L * s, boxstyle="round,pad=0.8", fc="#23262b", ec="#111"))
    ax.add_patch(Rectangle((-4.5 * s, -7.0 * s), 9 * s, 7.4 * s, fc="#c3c8cf", ec="#777"))
    ax.text(0, -3.3 * s, "USB-C", ha="center", va="center", fontsize=8, color=INK)
    ax.text(0, 2.6 * s, "USB-C is flush with this edge, on the component side", ha="center", fontsize=8.5, color=INK)
    ax.add_patch(Rectangle((-3 * s, -19 * s), 6 * s, 6 * s, fc="#111", ec="#444"))
    ax.text(0, -16 * s, "nRF52840", ha="center", va="center", color="#999", fontsize=7)
    for side, names in ((-1, LEFT_COL), (1, RIGHT_COL)):
        for i, n in enumerate(names):
            x, y = side * HALF_W * s, -(V0 + i * PITCH) * s
            what, colr = used.get(n, ("", "#aaa"))
            ax.add_patch(Circle((x, y), 0.95 * s, fc="#d4a93c", ec="none"))
            label = f"{n}" + (f" · {DNAME[n]}" if n in DNAME else "")
            ax.text(x + side * 2.2 * s, y + 0.55 * s, label, ha="left" if side > 0 else "right", va="center", fontsize=8.5,
                    color=INK, fontweight="bold")
            ax.text(x + side * 2.2 * s, y - 0.75 * s, what, ha="left" if side > 0 else "right", va="center", fontsize=7.5, color=colr)
    for j, n in enumerate(("101", "102", "107")):
        x, y = (j - 1) * 2.54 * s, -(BOARD_L - 2.2) * s
        ax.add_patch(Circle((x, y), 0.8 * s, fc="#d4a93c", ec="none"))
        ax.text(x, y + 1.8 * s, n, ha="center", fontsize=7, color="#bbb")
    ax.text(0, -(BOARD_L + 4.2) * s, "middle pads: free", ha="center", fontsize=7.5, color=MUTED)
    ax.set_title("SuperMini nRF52840: components up, USB-C at the top (as in the shop photo)", fontsize=12, color=INK, pad=10)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-BOARD_W * s * 1.9, BOARD_W * s * 1.9); ax.set_ylim(-(BOARD_L + 8) * s, 6 * s)


if __name__ == "__main__":
    pages = []
    for name, fn, size in (("wiring_matrix", matrix, (13, 8)), ("wiring_left", "left", (18, 9.0)),
                           ("wiring_right", "right", (18, 9.0)), ("supermini_pinout", pinout, (10, 10))):
        if isinstance(fn, str):
            fig, (ax, ax2) = plt.subplots(1, 2, figsize=size, facecolor=BG, gridspec_kw={"width_ratios": [2.3, 1.25]})
            half(ax, fn); board_back(ax2, fn)
        else:
            fig, ax = plt.subplots(figsize=size, facecolor=BG)
            fn(ax)
        fig.tight_layout()
        fig.savefig(os.path.join(C.IMG_DIR, name + ".png"), dpi=170, facecolor=BG)
        pages.append(fig)
    with PdfPages(os.path.join(C.DOCS_DIR, "wiring_guide.pdf")) as pdf:
        for f in pages:
            pdf.savefig(f, facecolor=BG)
    print("wiring diagrams written")

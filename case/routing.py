"""3D wire routing + diode placement for both halves (for the viewer and a clearance check).

Everything is in the shared case frame (left half's top view, z = 0 on the base's inner floor).
The right half is the mirror image: its switches, OLED, reset button... are mirrored here, but its
SuperMini is the same board (not mirrored), so its pad columns swap sides.

    python3 routing.py      -> clearance report (wire vs posts, pins, bosses, battery, switch, board...)

Heights (mm over the base floor):
    switch bottoms 4.15 (plate top 6.7 - 2.55), centre posts down to 0.9, pin tips 1.75
    column wires 3.75 (pressed against the switch bottoms), diodes 3.1, row wires 2.45
    SuperMini board 1.0-2.0 (on its rails), OLED board from 3.5 up, plate underside 4.7
"""
import math
import numpy as np
from shapely.geometry import Point, LineString, Polygon
import case as C
import layout as L
import wiring as W

R_W = 0.3                         # 30 AWG silicone, ~0.6 mm over the insulation
Z_SWB = C.H - 2.55                # switch bottom (KS-33 STEP)
Z_COL, Z_DIO, Z_ROW = 3.75, 3.1, 2.45
PIN_COL, PIN_DIO = (-4.4, -4.7), (2.6, -5.75)       # KS-33 pins, pins toward you (STEP model)
DIO_A, DIO_K, ROW_Y = -6.45, -9.15, -9.6             # diode body from/to (local y), row wire y
BOARD_TOP = C.MCU_RAIL + 1.0
MCX, MTOP = C.mcu_cx, C.mcu_top
BOARD_X0, BOARD_X1 = MCX - 9.0, MCX + 9.0             # the 18 mm board inside its 18.4 mm pocket
BOARD_Y0 = MTOP - 33.0
RAIL_END = C.mcu_top - 9.0                            # rails stop here: under-board crossings above it


def kxy(k, dx, dy, sgn):
    a = math.radians(k[2])
    x, y = sgn * dx, dy                               # right half: mirror the switch, then the key's turn
    return (k[0] + x * math.cos(a) - y * math.sin(a), k[1] + x * math.sin(a) + y * math.cos(a))


def pad(name, side, i=0):
    u, v = W.PADS[name][i]
    return (MCX + (u if side == "left" else -u), MTOP - v)


def near_side(x):
    return x < MCX


class Lanes:
    """vertical runs along one board edge: interval colouring into (x, z) tracks"""
    def __init__(self, side_sign):
        self.s = side_sign                            # -1: near (toward the keys), +1: far
        self.used = []                                # (track, ymin, ymax)

    def track(self, j):                               # 4 x-positions beside the board edge x 4 heights
        x = MCX + self.s * (9.45 + 0.66 * (j // 4))
        z = 1.25 + 0.68 * (j % 4)
        return x, z

    def take(self, y0, y1):
        lo, hi = min(y0, y1) - 0.8, max(y0, y1) + 0.8
        j = 0
        while any(t == j and not (hi < a or lo > b) for t, a, b in self.used):
            j += 1
        self.used.append((j, lo, hi))
        return self.track(j)


def avoid(pts, circles, skip=()):
    """push a polyline (x, y, z) around circular keep-outs [(x, y, r)] by inserting detour points"""
    pts = [list(p) for p in pts]
    for i, p in enumerate(pts[1:-1], 1):              # bend points inside a keep-out: push them out
        for (cx, cy, r) in circles:
            v = np.array(p[:2]) - (cx, cy); d = np.linalg.norm(v)
            if d < r and not any(np.hypot(p[0] - sk[0], p[1] - sk[1]) < 0.05 for sk in skip):
                v = v / d if d > 1e-6 else np.array([0.0, 1.0])
                pts[i][0], pts[i][1] = cx + v[0] * (r + 0.15), cy + v[1] * (r + 0.15)
    for _ in range(60):
        changed = False
        for i in range(len(pts) - 1):
            a, b = np.array(pts[i][:2]), np.array(pts[i + 1][:2])
            ab = b - a; L2 = float(ab @ ab) or 1e-9
            for (cx, cy, r) in circles:
                c = np.array([cx, cy])
                if any(np.hypot(*(c - np.array(sk))) < 0.05 for sk in skip):
                    continue
                t = float(np.clip((c - a) @ ab / L2, 0, 1))
                q = a + t * ab
                d = np.linalg.norm(q - c)
                if d < r and 0.02 < t < 0.98:
                    n = (q - c) / d if d > 1e-6 else np.array([-ab[1], ab[0]]) / math.sqrt(L2)
                    np_ = c + n * (r + 0.15)
                    z = pts[i][2] + (pts[i + 1][2] - pts[i][2]) * t
                    pts.insert(i + 1, [float(np_[0]), float(np_[1]), z])
                    changed = True
                    break
            if changed:
                break
        if not changed:
            return pts
    return pts


def build(side):
    sgn = 1 if side == "left" else -1
    wires, diodes = [], []
    rows = {r: [] for r in range(4)}
    cols = {c: [] for c in range(6)}
    for k in C.keys:
        x, y, rot, wu, r, c = k
        pa = kxy(k, *PIN_DIO, sgn)
        a0 = kxy(k, PIN_DIO[0], DIO_A, sgn); k0 = kxy(k, PIN_DIO[0], DIO_K, sgn)
        rw = kxy(k, PIN_DIO[0], ROW_Y, sgn)
        diodes.append({"a": [*a0, Z_DIO], "k": [*k0, Z_DIO], "key": f"R{r}C{c}"})
        # diode leads: anode to the switch pin, cathode down to the row wire
        wires.append({"n": f"diode lead R{r}C{c}", "c": "#9aa0a6", "r": 0.22,
                      "p": [[*pa, Z_DIO + 0.3], [*a0, Z_DIO]]})
        wires.append({"n": f"diode lead R{r}C{c}", "c": "#9aa0a6", "r": 0.22,
                      "p": [[*k0, Z_DIO], [*rw, Z_ROW]]})
        rows[r].append(rw)
        cols[c].append((kxy(k, *PIN_COL, sgn), y))

    near, far = Lanes(-1), Lanes(+1)
    keep = [(b[0], b[1], C.BOSS_D / 2 + 0.4) for b in C.BOSSES] + [(k[0], k[1], 2.55 + 0.4) for k in C.keys]
    pins = [(*kxy(k, *off, sgn), 0.75) for k in C.keys for off in (PIN_COL, PIN_DIO)]

    def to_pad(pts, name, i=0, z_from=None, cross_y=None):
        """from the last point (somewhere on the key side / below the board) to a pad"""
        px, py = pad(name, side, i)
        x, y, z = pts[-1]
        if near_side(px):
            lx, lz = near.take(y, py)
            pts += [[lx, y, lz], [lx, py, lz]]
        else:
            if cross_y is not None:                   # key side -> under the board's top end -> far edge
                nx, nz = near.take(y, cross_y)
                fx, fz = far.take(cross_y, py)
                pts += [[nx, y, nz], [nx, cross_y, nz], [BOARD_X0 - 0.4, cross_y, 0.45],
                        [BOARD_X1 + 0.4, cross_y, 0.45], [fx, cross_y, fz], [fx, py, fz]]
            else:
                fx, fz = far.take(y, py)
                pts += [[fx, y, fz], [fx, py, fz]]
        # hop over the board edge onto the pad (soldered from the top; the rails are under the pads)
        lx_, _, lz_ = pts[-1]
        pts += [[lx_, py, BOARD_TOP + 0.45], [px + (0.9 if px < MCX else -0.9), py, BOARD_TOP + 0.4],
                [px, py, BOARD_TOP + 0.15]]
        return pts


    # ---- rows: along the cathodes, then to the board ----
    for r in range(4):
        rn, d, silk = W.ROWS[r]
        pts = sorted(rows[r], key=lambda p: p[0])
        p = [[*pts[0], Z_ROW]]
        for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):   # step up inside the lower key's column
            if y2 - y1 > 0.5:
                p.append([x1 + 5.5, y2, Z_ROW])
            elif y1 - y2 > 0.5:
                p.append([x2 - 5.5, y1, Z_ROW])
            p.append([x2, y2, Z_ROW])
        last = p[-1]
        x, y = last[0], last[1]
        if r == 1:                                   # around the screw boss beside the board
            p += [[102.6, y, Z_ROW], [102.6, -23.6, Z_ROW]]
        elif r == 2:                                 # up the corridor between R2C5 and the battery's end
            p += [[101.5, y, 1.8], [101.5, -23.0, 1.8]]
        elif r == 3:
            p += [[100.6, y + 3.5, 1.2], [100.6, -23.6, 1.2]]
        p = avoid(p, keep + pins)
        px = pad(silk, side)[0]
        wires.append({"n": f"{rn} row → {silk}", "c": W.ROW_COL[r], "p": p})
        run = to_pad([p[-1][:]], silk, cross_y=None if near_side(px) else [9.3, 8.5, 7.7, 6.9][r])
        wires.append({"n": f"{rn} run → {silk} ({d})", "c": W.ROW_COL[r], "p": run, "dash": True})

    # ---- columns: up the column, north lane to the bay ----
    tops = {}
    for c in range(6):
        cn, d, silk = W.COLS[c]
        pts = [q for q, _ in sorted(cols[c], key=lambda t: -t[1])]
        wires.append({"n": f"{cn} column → {silk}", "c": W.COL_COL[c],
                      "p": avoid([[*q, Z_COL] for q in pts], keep + pins, skip=pts)})
        tops[c] = pts[0]
    r0 = {k[5]: k[1] for k in C.keys if k[4] == 0}
    kx = {k[5]: k[0] for k in C.keys if k[4] == 0}
    for c in range(6):
        cn, d, silk = W.COLS[c]
        ly = lambda col: r0[col] + 6.4 - 0.65 * c
        x0, y0 = tops[c]
        p = [[x0, y0, Z_COL], [x0, ly(c), Z_COL]]
        for col in range(c, 6):
            if col > c:
                p.append([kx[col] - 6.0, ly(col), Z_COL])
            p.append([kx[col] + 6.0, ly(col), Z_COL])
        yb = r0[5] + 6.4 - 0.65 * c
        p.append([C.bay_x0 - 1.5, yb, Z_COL])
        px = pad(silk, side)[0]
        p = avoid(p, keep + pins, skip=[tops[c]])
        run = to_pad(p, silk, cross_y=None if near_side(px) else yb)
        wires.append({"n": f"{cn} run → {silk} ({d})", "c": W.COL_COL[c], "p": run, "dash": True})

    # ---- below the board: OLED, reset button, battery + switch, trackpad ----
    # tracks across the board's bottom end (under the OLED: z <= 2.9) and just below it
    on_board = [(y, z) for y in (-20.25, -20.7) for z in (2.35, 2.9)]          # over the board's end
    off_board = [(-21.55, z) for z in (0.7, 1.3, 1.9, 2.5, 3.1)]               # just past its edge
    low = [(y, z) for y in (-22.0, -22.45) for z in (0.7, 1.3, 1.9, 2.5, 3.1)]   # beside the reset button
    slots = on_board + off_board + low
    used = []

    def slot_for(x0, x1, far_side):
        lo, hi = min(x0, x1) - 0.5, max(x0, x1) + 0.5
        cand = (off_board + on_board) if far_side else (low + off_board + on_board)
        for s in cand:                                # far: stay above the power switch (y > -21.9)
            if not any(t == s and not (hi < a or lo > b) for t, a, b in used):
                used.append((s, lo, hi)); return s
        raise RuntimeError("out of tracks under the board end")

    def from_below(name, col, path, padname, i=0):
        """path ends just below the board (y ~ -22); cross over the board end, then lanes"""
        px, py = pad(padname, side, i)
        x = path[-1][0]
        tx = (MCX - 9.35) if near_side(px) else (MCX + 9.35)
        sy, sz = slot_for(x, tx, not near_side(px))
        path = path + [[x, sy, sz]]
        lanes = near if near_side(px) else far
        lx, lz = lanes.take(sy, py)
        path += [[lx, sy, sz], [lx, sy, lz], [lx, py, lz], [lx, py, BOARD_TOP + 0.45],
                 [px + (0.9 if px < MCX else -0.9), py, BOARD_TOP + 0.4], [px, py, BOARD_TOP + 0.15]]
        wires.append({"n": name, "c": col, "p": path, "dash": True})

    oy = C.OLED_RECT.bounds[1] + 1.6
    for i, (nm, sk, colr) in enumerate(W.OLED):
        ox = C.oled_cx + sgn * (i - 1.5) * 2.54
        padname, idx = (sk, 0) if sk != "GND" else ("GND", 0)
        from_below(f"OLED {nm} → {sk}", colr, [[ox, oy, 3.45], [ox, oy, 3.0], [ox, -22.2, 3.0]], padname, idx)
    # reset button legs (3 x 6 mm switch lying face-down; legs at its short ends)
    rx, ry = C.RST_C
    legs = [(rx - sgn * 3.6, ry), (rx + sgn * 3.6, ry)]
    from_below("reset button → RST", "#5b6068", [[legs[1][0], ry, 1.3], [legs[1][0], -22.4, 2.0]], "RST")
    from_below("reset button → GND", "#222", [[legs[0][0], ry, 1.3], [legs[0][0], -22.6, 2.0]], "GND", 1)
    # battery: protection-board end toward the SuperMini, tabs on that end
    bc = list(C.BATT_RECT.exterior.coords)[:4]
    e0, e1 = sorted(bc, key=lambda q: q[0])[:2]                 # the two corners of the near end
    tabp = [e0[0] + (e1[0] - e0[0]) * 0.33, e0[1] + (e1[1] - e0[1]) * 0.33]
    tabn = [e0[0] + (e1[0] - e0[0]) * 0.66, e0[1] + (e1[1] - e0[1]) * 0.66]
    sw_x = C.SW_FACE - C.SW_BODY_D - C.SW_PIN_L                 # switch pin tips
    # + : battery -> switch middle pin
    nrm = np.array([-(e1[1] - e0[1]), e1[0] - e0[0]]); nrm /= np.linalg.norm(nrm)
    if nrm[0] > 0:
        nrm = -nrm                                  # outward from the battery's end
    wires.append({"n": "battery + → switch middle pin", "c": "#d1342f",
                  "p": [[*tabp, 2.0], [*(np.array(tabp) + 0.9 * nrm), 1.2], [104.0, -34.4, 1.2], [sw_x - 0.9, -34.4, 1.2],
                        [sw_x - 0.9, C.SW_YC, 1.2], [sw_x, C.SW_YC, 2.1]]})
    # switch outer pin -> B+
    from_below("switch outer pin → B+", "#d1342f",
               [[sw_x, C.SW_YC + 2.0, 2.1], [sw_x - 0.35, C.SW_YC + 2.0, 1.2], [sw_x - 0.35, -22.3, 1.2]], "B+")
    # - : battery -> B- (up the corridor beside the battery end, under the board's top end)
    px, py = pad("B-", side)
    tn = np.array(tabn) + 0.9 * nrm
    p = [[*tabn, 2.0], [*tn, 1.4], [102.4, tn[1], 0.7], [102.4, -23.4, 0.7]]
    lx, lz = near.take(-23.4, py - 1.2)
    p += [[lx, -23.4, lz], [lx, py - 1.2, lz], [lx, py - 1.2, 0.45]]
    p += [[px, py - 1.2, 0.45], [px, py, 0.6]]           # slides under the board's top end to the pad's underside
    wires.append({"n": "battery − → B−", "c": "#222", "p": p, "dash": True})

    if side == "right":
        tx, ty = C.TP_CENTER
        names = W.TP
        for j, (nm, sk) in enumerate(names):
            a = math.radians(98 + j * 5.0)
            sx, sy = tx + 9.6 * math.cos(a), ty + 9.6 * math.sin(a)
            corr, cz = 121.05 + 0.32 * (j // 3), 2.0 + 0.58 * (j % 3)     # corridor: OLED wires | switch pins
            path = [[sx, sy, C.H - C.TP_T - 0.05], [sx, sy, cz], [sx, -33.7 + 0.3 * (j % 3), cz],
                    [corr, -33.7 + 0.3 * (j % 3), cz], [corr, -22.3, cz]]
            padname = {"GND": "GND", "VCC": "VCC"}.get(sk, sk)
            from_below(f"trackpad {nm} → {sk}", W.TP_COL, path, padname, 2 if sk == "GND" else 0)
    return {"wires": wires, "diodes": diodes}


# ---------------- clearance check ----------------
def obstacles(side):
    sgn = 1 if side == "left" else -1
    obs = []                                                    # (name, 2D shape, zlo, zhi)
    for k in C.keys:
        obs.append((f"post R{k[4]}C{k[5]}", Point(k[0], k[1]).buffer(2.55), 0.9, Z_SWB))
        for nm, off in (("pinA", PIN_DIO), ("pinB", PIN_COL)):
            obs.append((f"{nm} R{k[4]}C{k[5]}", Point(*kxy(k, *off, sgn)).buffer(0.3), 1.75, Z_SWB))
    for b in C.BOSSES:
        obs.append(("boss", Point(b).buffer(C.BOSS_D / 2), 0, C.CAVITY + 0.1))
    obs.append(("battery", C.BATT_RECT, -0.5, C.BATT_T - C.BATT_RECESS))
    obs.append(("power switch", C.SW_RECT, C.SW_Z0, C.SW_Z0 + C.SW_BODY_H))
    obs.append(("reset button", C.RST_RECT, 0, C.RST_H))
    obs.append(("OLED board", C.OLED_RECT, 3.5, C.CAVITY))
    obs.append(("SuperMini", Polygon([(BOARD_X0, BOARD_Y0), (BOARD_X1, BOARD_Y0), (BOARD_X1, MTOP), (BOARD_X0, MTOP)]),
                C.MCU_RAIL, BOARD_TOP))
    for s in (-1, 1):
        rx = MCX + s * (C.MCU_W / 2 - 1.4)
        obs.append(("rail", Polygon([(rx - 0.6, MTOP - C.MCU_L + 1.5), (rx + 0.6, MTOP - C.MCU_L + 1.5),
                                     (rx + 0.6, MTOP - 9), (rx - 0.6, MTOP - 9)]), 0, C.MCU_RAIL))
    obs.append(("USB-C", Polygon([(MCX - 4.5, MTOP - 7.4), (MCX + 4.5, MTOP - 7.4), (MCX + 4.5, MTOP), (MCX - 4.5, MTOP)]),
                BOARD_TOP, BOARD_TOP + 3.2))
    if side == "right":
        obs.append(("trackpad", Point(*C.TP_CENTER).buffer(C.TP_D / 2), C.H - C.TP_T - 0.6, C.H))
    return obs


def sample(p, step=0.25):
    out = []
    for a, b in zip(p[:-1], p[1:]):
        a, b = np.array(a), np.array(b)
        n = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)]
    return out


def check(side, data):
    obs = obstacles(side)
    inner = C.inner.buffer(-R_W)
    bad = []
    for w in data["wires"]:
        if "diode lead" in w["n"]:
            continue
        verts = [np.array(v) for v in w["p"]]
        tp = w["n"].startswith("trackpad")
        r = w.get("r", R_W)
        pts = sample(w["p"])
        ends = (np.array(w["p"][0]), np.array(w["p"][-1]))
        for q in pts:
            if min(np.linalg.norm(q - e) for e in ends) < 1.0:   # its own solder joints
                continue
            if q[2] < r - 0.05 or q[2] > C.CAVITY - r + 0.05 and not (w["n"].startswith("trackpad") and q[2] > 4):
                bad.append((w["n"], "z out of the cavity", tuple(np.round(q, 1)))); break
            if not inner.contains(Point(q[0], q[1])):
                bad.append((w["n"], "outside the case", tuple(np.round(q, 1)))); break
            hit = None
            for nm, shp, z0, z1 in obs:
                if nm.startswith("pin") and min(np.linalg.norm(q[:2] - v[:2]) for v in verts) < 1.0:
                    continue                          # soldered to that pin
                if tp and nm == "trackpad":
                    continue
                if q[2] + r > z0 and q[2] - r < z1 and shp.distance(Point(q[0], q[1])) < r:
                    hit = nm; break
            if hit:
                bad.append((w["n"], hit, tuple(np.round(q, 1)))); break
    for d in data["diodes"]:
        a, k = np.array(d["a"]), np.array(d["k"])
        for q in [a + (k - a) * t for t in np.linspace(0, 1, 8)]:
            for nm, shp, z0, z1 in obs:
                if nm.startswith("pin") and nm.endswith(d["key"]):
                    continue
                if q[2] + 0.9 > z0 and q[2] - 0.9 < z1 and shp.distance(Point(q[0], q[1])) < 0.9:
                    bad.append(("diode " + d["key"], nm, tuple(np.round(q, 1)))); break
    return bad


if __name__ == "__main__":
    for side in ("left", "right"):
        d = build(side)
        bad = check(side, d)
        n = len([w for w in d["wires"] if "diode" not in w["n"]])
        L_ = sum(np.linalg.norm(np.diff(np.array(w["p"]), axis=0), axis=1).sum() for w in d["wires"])
        print(f"{side}: {n} wires, {len(d['diodes'])} diodes, {L_ / 1000:.2f} m of wire, {len(bad)} clashes")
        for b in bad:
            print("   ", b)


def wire_clash(data, min_gap=0.5):
    """pairs of different wires closer than min_gap (centre to centre minus radii) away from joints"""
    from scipy.spatial import cKDTree
    ws = [w for w in data["wires"]]
    S = [np.array(sample(w["p"], 0.2)) for w in ws]
    V = [np.array(w["p"]) for w in ws]
    out = []
    trees = [cKDTree(s) for s in S]
    for i in range(len(ws)):
        for j in range(i + 1, len(ws)):
            if ws[i]["c"] == ws[j]["c"] and ws[i]["n"].split()[0] == ws[j]["n"].split()[0]:
                continue                                # same signal (row wire + its run, etc.)
            if "diode" in ws[i]["n"] or "diode" in ws[j]["n"]:
                continue
            d, k = trees[j].query(S[i])
            lim = ws[i].get("r", R_W) + ws[j].get("r", R_W) + 0.02
            for a, (dd, kk) in enumerate(zip(d, k)):
                if dd < lim:
                    q = S[i][a]
                    if min(np.linalg.norm(q - v) for v in np.vstack([V[i], V[j]])) < 1.2:
                        continue
                    out.append((ws[i]["n"], ws[j]["n"], tuple(np.round(q, 1)))); break
    return out


if __name__ == "__main__":
    for side in ("left", "right"):
        c = wire_clash(build(side))
        print(side, "wire-wire touches:", len(c))
        for x in c[:40]:
            print("   ", x)

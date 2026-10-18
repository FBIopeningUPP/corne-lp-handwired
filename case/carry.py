"""Carry case: a two-piece click-shut shell for the halves stacked back-to-back (bag mode).

The halves snap together base-to-base on their magnets, keycaps facing out. The case is a
tray (holds the bottom half, keys down) and a lid (over the top half, keys up). They meet
exactly at the seam between the two bases. A 1 mm lip rises 3 mm out of the tray; the lid's
skirt slides over it, and 8 short bumps on the lip click into matching pockets in the skirt.

Frame: the left half's case coordinates (top view of the left half, base outer face at
z = -BOTTOM_T). The stack's footprint is the left outline, because the right half is its
mirror and lies flipped over it.

    python3 carry.py      -> ../print/carry-case/*.stl, ../cad/carry_*.step + bumper_*.step,
                             ../viewer/carry_tray.bin, ../viewer/carry_lid.bin
"""
import math, os
import numpy as np
from shapely.geometry import Point, Polygon, box, LineString
from shapely.ops import unary_union
from shapely import affinity
import trimesh

import case as C
import layout as LY
import step as S
import details as DT
import topo
from OCP.gp import gp_Pnt, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

# ---------------- parameters (mm) ----------------
import clp
CAP_TOP  = clp.CAP_TOP   # tallest keycap top above the plate's top face (CLP Tilt 7 1.5u: 11.45)
ABOVE    = 0.3     # case face stands this much above the keycap tops (keys sit in windows, never pressed)
CAP_CLR  = 0.3     # keycap -> window edge
GAP      = 0.5     # keyboard outline -> case inner wall
SKIN     = 1.2     # top / bottom skin
LIP_T    = 1.0     # tray lip thickness
SLIDE    = 0.15    # lip <-> skirt clearance
SKIRT_T  = 1.25    # lid skirt thickness over the lip
WALL     = LIP_T + SLIDE + SKIRT_T          # 2.4 everywhere else
LIP_H    = 3.0     # how far the lip rises above the seam
BUMP_P   = 0.40    # bump stands out of the lip  -> 0.25 mm snap interference after SLIDE
BUMP_TIP = 0.6     # flat on the bump's crest (height)
BUMP_L   = 10.0    # bump length along the wall
BUMP_Z   = 1.5     # bump centre above the seam
N_BUMPS  = 8
POCKET_X = 0.15    # pocket is this much bigger than the bump all round
EDGE_R   = 1.6     # rounded outer edges (face side)
NOTCH_W, NOTCH_H, NOTCH_D = 16.0, 2.2, 1.0   # fingernail notch in the tray just under the seam
SIGN_SIZE, SIGN_DEPTH = 21.0, 0.4    # cursive signature under the tray

CAP_W, CAP_R = 17.4, 2.0
WIN_PAD = 1.0                        # Blip window: OLED window + this all round
PANE_T, PANE_PAD = 0.6, 1.4          # optional clear pane (0.5 mm acrylic / clear PETG), glued in from inside
EAR_OUT, EAR_W, EAR_T = 8.5, 16.0, 3.2     # strap ear on the tray, flush with its bottom
SLOT_W, SLOT_L = 3.0, 10.0
# --- open-face "bumper" version: keys stay visible, a rim stands just above the keycaps ---
RIM      = ABOVE   # rim above the keycap tops
FLANGE_IN, FLANGE_T, FLANGE_CLR = 1.6, 1.2, 0.15   # inward flange resting on each half's plate rim
TOPO_D = 0.4                         # ripple lines (lid margins + whole tray bottom)
RIB_W, RIB_D, RIB_PITCH = 0.6, 0.4, 1.6    # grip ribs round the side walls

SEAM = -C.BOTTOM_T
HALF = C.BOTTOM_T + C.H + CAP_TOP                   # one half, base face -> keycap tops
DEPTH = HALF + ABOVE - SKIN                         # cavity depth per side: skin wraps the top 0.9 mm of the caps
OUT = C.CARRY_DIR
STEP_DIR = C.STEP_DIR
VIEWER = C.VIEWER_DIR

# ---------------- 2D ----------------
# power-switch knobs (both halves land on the same x, y) stick ~2 mm out of the side wall
_ky = C.SW_SLOT_Y + 0.8
KNOB = box(C.SW_XOUT - 1.0, C.SW_YC - _ky, C.SW_XOUT + 2.0 + 0.6, C.SW_YC + _ky)
cav = unary_union([C.outer.buffer(GAP, join_style=1), KNOB])
cav = cav.buffer(2.0, join_style=1).buffer(-2.0, join_style=1)      # blend the knob bay in
lip_out = cav.buffer(LIP_T, join_style=1)
skirt_in = cav.buffer(LIP_T + SLIDE, join_style=1)
outer = cav.buffer(WALL, join_style=1).buffer(2.0, join_style=1).buffer(-2.0, join_style=1).simplify(0.03)   # round the concave corners too     # fewer edges: OpenCascade can round them

ring = list(lip_out.exterior.coords)
line = LineString(ring)
PER = line.length


def frame_at(s, d=3.0):
    """point, unit tangent, outward normal on the lip's outer face at arc length s"""
    p = line.interpolate(s % PER)
    a, b = line.interpolate((s - d) % PER), line.interpolate((s + d) % PER)
    t = np.array([b.x - a.x, b.y - a.y]); t /= np.linalg.norm(t)
    n = np.array([t[1], -t[0]])
    if cav.contains(Point(p.x + n[0] * (LIP_T + 0.5), p.y + n[1] * (LIP_T + 0.5))):
        n = -n
    return np.array([p.x, p.y]), t, n


def straightness(s):
    """worst turn (deg) across a bump's length"""
    _, t0, _ = frame_at(s - BUMP_L / 2, 1.0)
    _, t1, _ = frame_at(s + BUMP_L / 2, 1.0)
    _, tm, _ = frame_at(s, 1.0)
    ang = lambda u, v: math.degrees(math.acos(max(-1, min(1, float(u @ v)))))
    return max(ang(t0, tm), ang(tm, t1))


# finger notch: middle of the longest straight run along the front (south-ish) edge
cands = np.arange(0, PER, 1.0)
straight = np.array([straightness(s) < 4 for s in cands])
best, run = None, 0
for i in range(len(cands)):
    if straight[i]:
        run += 1
        p, t, n = frame_at(cands[i])
        if n[1] < -0.7 and (best is None or run > best[0]) and not KNOB.buffer(20).contains(Point(*p)):
            best = (run, cands[i] - run / 2)
    else:
        run = 0
NOTCH_S = best[1]
notch_p, _, notch_n = frame_at(NOTCH_S)

# bumps: on straight runs, spread round the outline, clear of the knob bay and the notch
keep_out = unary_union([KNOB.buffer(BUMP_L / 2 + 4), Point(*notch_p).buffer(NOTCH_W / 2 + BUMP_L / 2 + 3)])
ok = [s for s in cands if straightness(s) < 6 and not keep_out.contains(Point(*frame_at(s)[0]))]
bumps = [max(ok, key=lambda s: frame_at(s)[0][0] - frame_at(s)[0][1])]       # start: a far corner
arc = lambda a, b: min(abs(a - b), PER - abs(a - b))
while len(bumps) < N_BUMPS:
    bumps.append(max(ok, key=lambda s: min(arc(s, b) for b in bumps)))
bumps.sort()


# ---------------- unique bits ----------------
def rrect(cx, cy, w, h, ang, r):
    return Polygon(LY.rect(cx, cy, w - 2 * r, h - 2 * r, ang)).buffer(r, quad_segs=8)


# ghost key layout: the outline of every keycap of the half that sits under the lid
# Each window is the CLP cap's own crown: everything of the cap above 1.2 mm under its top (or
# above the skin, for a cap tall enough to reach it), plus CAP_CLR. Low caps never touch the skin.
Z_SKIN = CAP_TOP + ABOVE - SKIN                     # skin's underside over the plate
caps = [clp.footprint(k, min(clp.top(k) - 1.2, Z_SKIN)) for k in C.keys]
KEY_WIN = unary_union([c.buffer(CAP_CLR, join_style=1) for c in caps])     # every keycap gets a window
KEY_WIN = KEY_WIN.buffer(0.5, join_style=1).buffer(-0.5, join_style=1)  # webs under 1 mm would print badly: merge

# Blip window right over the left OLED
wx0, wy0, wx1, wy1 = C.WIN_RECT.bounds
wcx, wcy = (wx0 + wx1) / 2, (wy0 + wy1) / 2
WIN_HOLE = rrect(wcx, wcy, wx1 - wx0 + 2 * WIN_PAD, wy1 - wy0 + 2 * WIN_PAD, 0, 1.6)
WIN_FRAME = WIN_HOLE.buffer(0.9, join_style=1)                           # 0.4 mm deep bezel step on the face
PANE = WIN_HOLE.buffer(PANE_PAD, join_style=1)

# strap ear: off the outer (pinky) end, at the middle of its straight run
_xe = outer.bounds[0]
_ys = [y for y in np.arange(outer.bounds[1], outer.bounds[3], 0.5)
       if LineString([(_xe - 1, y), (_xe + 3, y)]).intersects(outer) and
       min(c[0] for c in LineString([(_xe - 1, y), (_xe + 40, y)]).intersection(outer).coords) < _xe + 0.3]
EAR_Y = (min(_ys) + max(_ys)) / 2
EAR = rrect(_xe - EAR_OUT / 2 + 1.5, EAR_Y, EAR_OUT + 3, EAR_W, 0, 4.0)
SLOT = rrect(_xe - EAR_OUT + 3.6, EAR_Y, SLOT_W, SLOT_L, 0, SLOT_W / 2 - 0.01)


FACE = outer.buffer(-(EDGE_R + 1.2), join_style=1)
def place_signature(avoid):
    """biggest cursive 'Corne' that fits the face clear of the windows (ends up in the thumb lobe)"""
    import shapely
    room = FACE.buffer(-1.0).difference(avoid.buffer(1.6))
    shapely.prepare(room)
    for size in np.arange(SIGN_SIZE, 6.0, -1.0):
        name = DT._script("Corne", size, DT.SIGN_FONT)
        nb = name.bounds
        g = unary_union([name, DT._swoosh(nb[0], nb[2], nb[1] - 0.04 * size)]).buffer(0.12)
        c = g.centroid
        for ang in (0, 15, -15, 30, -30, 45, -45, 60, -60, 90):
            hull = affinity.rotate(g.convex_hull, ang, origin=c)
            hx, hy = hull.centroid.x, hull.centroid.y
            r_in = min(hull.bounds[2] - hull.bounds[0], hull.bounds[3] - hull.bounds[1]) / 2
            core = room.buffer(-r_in * 0.9)
            if core.is_empty:
                continue
            xs = np.arange(core.bounds[0], core.bounds[2], 0.75); ys = np.arange(core.bounds[1], core.bounds[3], 0.75)
            X, Y = np.meshgrid(xs, ys)
            ok = shapely.contains_xy(core, X, Y)
            for cx, cy in zip(X[ok], Y[ok]):
                if room.contains(affinity.translate(hull, cx - hx, cy - hy)):
                    return affinity.translate(affinity.rotate(g, ang, origin=c), cx - hx, cy - hy), size
    return None, 0


OPEN = unary_union([KEY_WIN, WIN_FRAME])
SIGN, SIGN_PT = place_signature(OPEN)
LID_TOPO = topo.ripples(unary_union([OPEN, SIGN.buffer(1.5)]), FACE, seed=7)
TRAY_TOPO = topo.ripples(unary_union([OPEN, SIGN.buffer(1.5), SLOT.buffer(2.0)]), FACE, seed=11)
# keep the ripples off the rounded bottom edge (slivers there broke the STL mesh)
TRAY_TOPO = unary_union([g for g in getattr(TRAY_TOPO.intersection(outer.buffer(-(EDGE_R + 0.4), join_style=1)), "geoms", [TRAY_TOPO])
                         if g.area > 2.0])
_sc = SIGN.envelope.centroid
SIGN_UNDER = affinity.scale(SIGN, -1, 1, origin=_sc)       # same spot under the tray, reads from below


def ribs(z_lo, z_hi):
    """grip ribs: shallow grooves all the way round the outside wall"""
    band = outer.difference(outer.buffer(-RIB_D, join_style=1))
    n = int((z_hi - z_lo - RIB_W) // RIB_PITCH) + 1
    z0 = (z_lo + z_hi) / 2 - (n - 1) * RIB_PITCH / 2
    return [S.prism(band, z0 + i * RIB_PITCH - RIB_W / 2, z0 + i * RIB_PITCH + RIB_W / 2) for i in range(n)]


# ---------------- solids ----------------
def wedge(s, grow=0.0):
    """bump: trapezoid section (45° flanks, so it cams in and out), extruded along the wall"""
    p, t, n = frame_at(s)
    L = BUMP_L + 2 * grow
    base_in = -0.3                                   # buried in the lip for a clean union
    tip = BUMP_P + grow
    zc = SEAM + BUMP_Z
    hb = BUMP_TIP / 2 + BUMP_P + grow + 0.3          # half height at the buried base (45°)
    ht = BUMP_TIP / 2 + grow
    prof = [(base_in, -hb), (tip, -ht), (tip, ht), (base_in, hb)]
    o = p - t * L / 2
    mp = BRepBuilderAPI_MakePolygon()
    for (nn, zz) in prof:
        q = o + n * nn
        mp.Add(gp_Pnt(float(q[0]), float(q[1]), float(zc + zz)))
    mp.Close()
    f = BRepBuilderAPI_MakeFace(mp.Wire(), True).Face()
    return BRepPrimAPI_MakePrism(f, gp_Vec(float(t[0] * L), float(t[1] * L), 0.0)).Shape()


def build_tray():
    z0 = SEAM - DEPTH - SKIN
    body = S.prism(outer, z0, SEAM)
    body = S.round_face_edges(body, z0, EDGE_R)
    ear = S.round_face_edges(S.prism(EAR, z0, z0 + EAR_T), z0 + EAR_T, 1.0)    # the cavity cut trims its inner end
    body = S.fuse_all([body, ear])
    body = S.cut_all(body, [S.prism(SLOT, z0 - 1, z0 + EAR_T + 1),
                            S.prism(KEY_WIN, z0 - 1, z0 + SKIN + 1),
                            S.prism(WIN_HOLE, z0 - 1, z0 + SKIN + 1),
                            S.prism(WIN_FRAME, z0 - 1, z0 + 0.4),
                            S.prism(PANE, z0 + SKIN - PANE_T, z0 + SKIN + 0.01),
                            S.prism(SIGN_UNDER, z0 - 1, z0 + SIGN_DEPTH),
                            S.prism(TRAY_TOPO, z0 - 1, z0 + TOPO_D)]
                     + ribs(z0 + EAR_T + 0.8, SEAM - NOTCH_H - 0.8))
    body = S.fuse_all([body, S.prism(lip_out, SEAM - 0.5, SEAM + LIP_H)])
    body = S.fuse_all([body] + [wedge(s) for s in bumps])
    body = S.cut_all(body, [S.prism(cav, SEAM - DEPTH, SEAM + LIP_H + 1)])
    # fingernail notch just below the lid's rim
    p, t, n = notch_p, None, notch_n
    nb = Point(*p).buffer(NOTCH_W / 2, 48)
    nb = affinity.scale(nb, 1.0, 1.0)
    notch = nb.intersection(outer.difference(outer.buffer(-NOTCH_D, join_style=1)))
    body = S.cut_all(body, [S.prism(notch, SEAM - NOTCH_H, SEAM + 0.01)])
    return S.clean(body)


def signature(mirror=False):
    name = DT._script("Corne", SIGN_SIZE, DT.SIGN_FONT)
    nb = name.bounds
    g = unary_union([name, DT._swoosh(nb[0], nb[2], nb[1] - 0.5)]).buffer(0.12)
    x0, y0, x1, y1 = g.bounds
    w, h = x1 - x0, y1 - y0
    room = outer.buffer(-(EDGE_R + 4))
    best = None
    for cx in np.arange(10, 120, 0.5):
        for cy in np.arange(-60, 5, 0.5):
            r = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if room.contains(r):
                d = math.hypot(cx - 52, cy + 24)
                if best is None or d < best[0]:
                    best = (d, cx, cy)
    g = affinity.translate(g, best[1] - (x0 + x1) / 2, best[2] - (y0 + y1) / 2)
    return affinity.scale(g, -1, 1, origin=(best[1], best[2])) if mirror else g   # read from below


def build_lid():
    z1 = SEAM + DEPTH + SKIN
    body = S.prism(outer, SEAM, z1)
    body = S.round_face_edges(body, z1, EDGE_R)
    body = S.cut_all(body, [S.prism(cav, SEAM - 1, SEAM + DEPTH),
                            S.prism(skirt_in, SEAM - 1, SEAM + LIP_H + 0.2)]
                     + [wedge(s, POCKET_X) for s in bumps]
                     + [S.prism(KEY_WIN, SEAM + DEPTH - 1, z1 + 1),
                        S.prism(SIGN, z1 - SIGN_DEPTH, z1 + 1),
                        S.prism(WIN_HOLE, SEAM + DEPTH - 1, z1 + 1),
                        S.prism(WIN_FRAME, z1 - 0.4, z1 + 1),
                        S.prism(PANE, SEAM + DEPTH - 0.01, SEAM + DEPTH + PANE_T),
                        S.prism(LID_TOPO, z1 - TOPO_D, z1 + 1)]
                     + ribs(SEAM + LIP_H + 1.2, z1 - EDGE_R - 0.8))
    return S.clean(body)


def build_bumper(top):
    """open frame for one side of the stack: wall + rim above the keycaps, a flange that rests on
    the plate's edge (1.6 mm, clear of every keycap), and the same click lip / pockets at the seam"""
    plate = C.H if top else 2 * SEAM - C.H              # plate top face of the half on this side
    zr = SEAM + HALF + RIM if top else SEAM - HALF - RIM
    zlo, zhi = (SEAM, zr) if top else (zr, SEAM)
    body = S.prism(outer, zlo, zhi)
    body = S.round_face_edges(body, zr, 1.0)                                   # soft rim
    f0, f1 = (plate + FLANGE_CLR, plate + FLANGE_CLR + FLANGE_T) if top else \
             (plate - FLANGE_CLR - FLANGE_T, plate - FLANGE_CLR)
    opening = C.outer.buffer(-FLANGE_IN, join_style=1)
    if not top:
        ear = S.round_face_edges(S.prism(EAR, zr, zr + EAR_T), zr + EAR_T, 1.0)
        body = S.fuse_all([body, ear, S.prism(lip_out, SEAM - 0.5, SEAM + LIP_H)] + [wedge(s) for s in bumps])
    cuts = [S.prism(cav, zlo - 1, f0), S.prism(cav, f1, zhi + 1 + (0 if top else LIP_H)),
            S.prism(opening, zlo - 1, zhi + 1)]
    if top:
        cuts += [S.prism(skirt_in, SEAM - 1, SEAM + LIP_H + 0.2)] + [wedge(s, POCKET_X) for s in bumps]
        cuts += ribs(SEAM + LIP_H + 1.2, zr - 1.8)
    else:
        cuts += [S.prism(SLOT, zr - 1, zr + EAR_T + 1)]
        notch = Point(*notch_p).buffer(NOTCH_W / 2, 48).intersection(
            outer.difference(outer.buffer(-NOTCH_D, join_style=1)))
        cuts += [S.prism(notch, SEAM - NOTCH_H, SEAM + 0.01)]
        cuts += ribs(zr + EAR_T + 0.8, SEAM - NOTCH_H - 0.8)
    return S.clean(S.cut_all(body, cuts))


def to_trimesh(shape):
    """watertight STL mesh (shared edges) via OpenCascade's own writer"""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    import tempfile
    BRepMesh_IncrementalMesh(shape, 0.02, False, 0.2, True)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.stl")
        StlAPI_Writer().Write(shape, p)
        m = trimesh.load(p)
    m.merge_vertices(digits_vertex=4)
    if not m.is_watertight:            # rare tessellation crack (a few edges): close it
        import meshfix
        m = meshfix.close_cracks(m)
    return m


if __name__ == "__main__":
    os.makedirs(STEP_DIR, exist_ok=True)
    import sys
    names = sys.argv[1:] or ["carry_tray", "carry_lid", "bumper_bottom", "bumper_top"]
    build = {"carry_tray": build_tray, "carry_lid": build_lid,
             "bumper_bottom": lambda: build_bumper(False), "bumper_top": lambda: build_bumper(True)}
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.ShapeFix import ShapeFix_Shape
    for nm in names:
        sh = build[nm]()
        if not BRepCheck_Analyzer(sh).IsValid():       # tiny boolean slivers: let OpenCascade heal them
            fx = ShapeFix_Shape(sh); fx.Perform(); sh = fx.Shape()
        S.write_step(sh, nm)
    from OCP.STEPControl import STEPControl_Reader
    flips = {"carry_tray": False, "carry_lid": True, "bumper_bottom": False, "bumper_top": True}
    for nm, flip in ((n, flips[n]) for n in names):
        rd = STEPControl_Reader(); rd.ReadFile(os.path.join(STEP_DIR, nm + ".step")); rd.TransferRoots()
        sh = rd.OneShape()             # mesh what the STEP holds (the in-memory compound double-counts)
        m = to_trimesh(sh)
        print(f"{nm}: watertight={m.is_watertight} vol={m.volume/1000:.1f} cm3")
        if flip:   # print face-down
            m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation(-m.bounds[0])
        m.export(os.path.join(OUT, nm + ".stl"))
        S.write_viewer_mesh(sh, os.path.join(VIEWER, nm + ".bin"))
    b = outer.bounds
    print(f"bumper: {b[2]-b[0]:.1f} x {b[3]-b[1]:.1f} x {2 * (HALF + RIM):.1f} mm")
    print(f"carry case: {b[2]-b[0]:.1f} x {b[3]-b[1]:.1f} x {2 * (DEPTH + SKIN):.1f} mm, "
          f"seam at {SEAM}, bumps at {[round(s) for s in bumps]} of {PER:.0f} mm, notch at {NOTCH_S:.0f}")

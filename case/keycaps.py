"""3D-printable low-profile keycaps for Gateron KS-33 (Low Profile 2.0) switches.

KS-33 has a (short) MX-style cross stem, so the caps use an MX cross socket. Everything that
depends on your switch and printer is a parameter at the top; print keycap_stem_test.stl
first and set STEM_TOL from the slug that pushes on firmly without cracking.

    python3 keycaps.py  ->  out/keycaps/
        keycap_1u.stl, keycap_1u_homing.stl, keycap_1u5.stl     single caps (print face-down)
        keycap_stem_test.stl                                    5 sockets, 0.04-0.20 mm looser
        keycaps_left_set.stl, keycaps_right_set.stl             a whole half laid out, face-down
"""
import math, os
import numpy as np
from manifold3d import Manifold, CrossSection
from shapely.geometry import box
from shapely.geometry.polygon import orient
import trimesh
import case as C

# ---------------- parameters (mm) ----------------
U1 = (17.4, 17.4)            # matches the case (19.05 mm pitch, 1.65 mm between caps)
U15 = (17.4, 26.9)           # big thumb key
CAP_H = 3.2                  # total height (the carry case is built around this)
TAPER = 0.45                 # each side gets this much smaller from skirt to top
R_BOT, R_TOP = 2.2, 1.9      # corner radius at the skirt / at the top
EDGE_R = 0.8                 # rounded top edge
WALL = 1.0                   # skirt wall
TOP_T = 1.4                  # top slab
STEM_D = 5.6                 # socket tube outside diameter
STEM_GAP = 0.3               # tube stops this far above the skirt edge (clears the switch top)
SOCKET_LEFT = 0.6            # plastic left above the bottom of the cross socket
CROSS_L, CROSS_W = 4.05, 1.20    # MX cross, nominal
STEM_TOL = 0.12              # added to both cross sizes; tune with the stem test
HOMING = (6.0, 0.9, 0.35)    # engraved bar on F and J: length, width, depth
OUT = os.path.join(C.OUT, "keycaps")


def rrect(w, h, r, cx=0.0, cy=0.0):
    r = max(0.05, min(r, w / 2 - 0.01, h / 2 - 0.01))
    return box(cx - w / 2 + r, cy - h / 2 + r, cx + w / 2 - r, cy + h / 2 - r).buffer(r, quad_segs=10)


def xs(poly):
    return CrossSection([list(orient(poly, 1).exterior.coords)[:-1]])


def slab(poly, z0, z1):
    return xs(poly).extrude(z1 - z0).translate([0, 0, z0])


def body(w, h):
    """outer shell: tapered rounded rectangle with a rounded top edge (built as a hull of slices)"""
    sl = []
    n = 14
    for i in range(n + 1):
        z = CAP_H * i / n
        t = z / CAP_H
        d = TAPER * t
        # quarter-round over the last EDGE_R of height
        if z > CAP_H - EDGE_R:
            a = (z - (CAP_H - EDGE_R)) / EDGE_R
            d += EDGE_R - math.sqrt(max(EDGE_R ** 2 - (EDGE_R * a) ** 2, 0))
        p = rrect(w - 2 * d, h - 2 * d, R_BOT + (R_TOP - R_BOT) * t - (d - TAPER * t))
        sl.append(slab(p, min(z, CAP_H - 0.01), min(z, CAP_H - 0.01) + 0.01))
    # extra slices inside the rounded edge for a smooth curve
    for k in range(1, 6):
        a = k / 6
        z = CAP_H - EDGE_R + EDGE_R * math.sin(a * math.pi / 2)
        d = TAPER * (z / CAP_H) + EDGE_R - EDGE_R * math.cos(a * math.pi / 2)
        sl.append(slab(rrect(w - 2 * d, h - 2 * d, R_TOP - (d - TAPER)), z - 0.005, z + 0.005))
    return Manifold.batch_hull(sl)


def cavity(w, h):
    top = CAP_H - TOP_T
    sl = []
    for z in (-0.01, top):
        t = max(z, 0) / CAP_H
        d = TAPER * t + WALL
        sl.append(slab(rrect(w - 2 * d, h - 2 * d, max(0.4, R_BOT - WALL)), z, z + 0.01))
    return Manifold.batch_hull(sl)


def cross(tol, z0, z1):
    L, W = CROSS_L + tol, CROSS_W + tol
    return slab(box(-L / 2, -W / 2, L / 2, W / 2), z0, z1) + slab(box(-W / 2, -L / 2, W / 2, L / 2), z0, z1)


def keycap(size=U1, homing=False, tol=None):
    tol = STEM_TOL if tol is None else tol
    w, h = size
    cap = body(w, h) - cavity(w, h)
    tube = Manifold.cylinder(CAP_H - TOP_T - STEM_GAP + 0.01, STEM_D / 2, STEM_D / 2, 48).translate([0, 0, STEM_GAP])
    cap = cap + tube
    cap = cap - cross(tol, STEM_GAP - 0.01, CAP_H - SOCKET_LEFT)
    if homing:
        L, Wd, D = HOMING
        cap = cap - slab(rrect(L, Wd, Wd / 2 - 0.01, 0, -h * 0.22), CAP_H - D, CAP_H + 0.1)
    return cap


def stem_test():
    """5 round slugs on a bar; slug i is STEM_TOL-ish 0.04*(i+1) looser; i+1 notches mark it"""
    parts = []
    for i in range(5):
        tol = 0.04 * (i + 1)
        x = i * 10.0
        slug = Manifold.cylinder(CAP_H, 3.8, 3.8, 48).translate([x, 0, 0])
        slug = slug - cross(tol, STEM_GAP - 0.01, CAP_H - SOCKET_LEFT)
        for j in range(i + 1):
            slug = slug - slab(box(x - 2.4 + j * 1.2, -4.0, x - 1.9 + j * 1.2, -3.2), -0.1, 0.8)
        parts.append(slug)
    parts.append(slab(box(-2, 3.0, 42, 5.0), 0, 1.2))
    return Manifold.batch_boolean(parts, __import__("manifold3d").OpType.Add)


def face_down(m):
    """flip so the top face is on the bed (smooth, crisp top; socket prints straight up)"""
    return m.rotate([180, 0, 0]).translate([0, 0, CAP_H])


def layout(side):
    caps = []
    i = 0
    for k in C.keys:
        x, y, r, wu, row, col = k
        size = U15 if wu > 1 else U1
        m = keycap(size, homing=(row == 1 and col == 4))
        gx, gy = (i % 6) * 21.0, (i // 6) * (31.0 if False else 21.0)
        caps.append((m, size))
        i += 1
    out, x, y, rowh = [], 0.0, 0.0, 0.0
    for m, (w, h) in caps:
        if x + w > 6 * 20.5:
            x, y = 0.0, y + rowh + 3.0
            rowh = 0.0
        out.append(face_down(m).translate([x + w / 2, y + h / 2, 0]))
        x += w + 3.0
        rowh = max(rowh, h)
    return Manifold.batch_boolean(out, __import__("manifold3d").OpType.Add)


def export(m, name):
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts))
    tm.apply_translation([-tm.bounds[0][0], -tm.bounds[0][1], -tm.bounds[0][2]])
    tm.export(os.path.join(OUT, name + ".stl"))
    print(f"{name:22s} {m.status().name:8s} {m.volume() / 1000:6.2f} cm3  "
          f"{tm.extents[0]:.1f} x {tm.extents[1]:.1f} x {tm.extents[2]:.1f} mm  watertight={tm.is_watertight}")
    return tm


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    export(face_down(keycap(U1)), "keycap_1u")
    export(face_down(keycap(U1, homing=True)), "keycap_1u_homing")
    export(face_down(keycap(U15)), "keycap_1u5")
    export(stem_test(), "keycap_stem_test")
    for side in ("left", "right"):
        export(layout(side), f"keycaps_{side}_set")
    print(f"engagement {CAP_H - SOCKET_LEFT - STEM_GAP:.1f} mm, cross {CROSS_L + STEM_TOL:.2f} x {CROSS_W + STEM_TOL:.2f} mm")

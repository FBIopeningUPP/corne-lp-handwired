"""STEP export: rebuilds the case parts as true B-rep solids with OpenCascade.

Uses the same 2D geometry and parameters as case.py (outline, holes, bosses, magnets...)
so the STEP files match the STLs, but with a real top-edge chamfer and clean faces
you can open and edit in Fusion 360, Onshape, FreeCAD, SolidWorks, etc.

    pip install cadquery-ocp
    python3 step.py        -> ../cad/*.step, viewer meshes, and the final printable STLs in ../print/
"""
import os
from OCP.gp import gp_Pnt, gp_Vec, gp_Dir, gp_Ax2, gp_Trsf, gp_Ax1
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace,
                                BRepBuilderAPI_Transform)
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeCone
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
from OCP.collections import List_TopoDS_Shape as TopTools_ListOfShape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from shapely.geometry import box, Polygon, Point
from shapely.geometry.polygon import orient
import case as C

OUT = C.STEP_DIR


# ---------------- primitives ----------------
def _wire(coords, z):
    mp = BRepBuilderAPI_MakePolygon()
    pts = list(coords)[:-1]
    for x, y in pts:
        mp.Add(gp_Pnt(float(x), float(y), float(z)))
    mp.Close()
    return mp.Wire()


def _faces(poly, z):
    out = []
    for p in getattr(poly, "geoms", [poly]):
        p = orient(p.simplify(0.005), 1)
        mf = BRepBuilderAPI_MakeFace(_wire(p.exterior.coords, z), True)
        for ring in p.interiors:
            w = _wire(ring.coords, z)
            mf.Add(w)          # orient() already made this ring clockwise
        out.append(mf.Face())
    return out


def fuse_all(shapes):
    shapes = [s for s in shapes if s is not None]
    if len(shapes) == 1:
        return shapes[0]
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(shapes[0])
    for s in shapes[1:]:
        tools.Append(s)
    op = BRepAlgoAPI_Fuse()
    op.SetArguments(args); op.SetTools(tools); op.SetFuzzyValue(1e-5); op.Build()
    return op.Shape()


def cut_all(base, tools_):
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(base)
    for t in tools_:
        tools.Append(t)
    op = BRepAlgoAPI_Cut()
    op.SetArguments(args); op.SetTools(tools); op.SetFuzzyValue(1e-5); op.Build()
    return op.Shape()


def prism(poly, z0, z1):
    return fuse_all([BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, z1 - z0)).Shape() for f in _faces(poly, z0)])


def cyl(x, y, d, z0, z1):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1)), d / 2, z1 - z0).Shape()


def cone(x, y, d0, d1, z0, z1):
    return BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1)), d0 / 2, d1 / 2, z1 - z0).Shape()


def chamfer_face_edges(shape, z, dist):
    """chamfer every edge of the planar face lying at height z (the visible top/bottom outline)"""
    mk = BRepFilletAPI_MakeChamfer(shape)
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    target = None
    while exp.More():
        f = TopoDS.Face(exp.Current())
        s = BRepAdaptor_Surface(f)
        if s.GetType() == GeomAbs_Plane and abs(s.Plane().Location().Z() - z) < 1e-6 \
                and abs(abs(s.Plane().Axis().Direction().Z()) - 1) < 1e-9:
            target = f
            break
        exp.Next()
    e = TopExp_Explorer(target, TopAbs_EDGE)
    while e.More():
        mk.Add(dist, dist, TopoDS.Edge(e.Current()), target)
        e.Next()
    mk.Build()
    return mk.Shape()


def round_face_edges(shape, z, r):
    """quarter-round every edge of the planar face at height z; falls back to a chamfer"""
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    target = None
    while exp.More():
        f = TopoDS.Face(exp.Current())
        s = BRepAdaptor_Surface(f)
        if s.GetType() == GeomAbs_Plane and abs(s.Plane().Location().Z() - z) < 1e-6 \
                and abs(abs(s.Plane().Axis().Direction().Z()) - 1) < 1e-9:
            target = f
            break
        exp.Next()
    try:
        mk = BRepFilletAPI_MakeFillet(shape)
        e = TopExp_Explorer(target, TopAbs_EDGE)
        while e.More():
            mk.Add(r, TopoDS.Edge(e.Current()))
            e.Next()
        mk.Build()
        if mk.IsDone() and BRepCheck_Analyzer(mk.Shape()).IsValid():
            return mk.Shape()
    except Exception:
        pass
    print("  (fillet failed, using a chamfer)")
    return chamfer_face_edges(shape, z, r * 0.6)


def move(shape, dx=0, dy=0, dz=0):
    t = gp_Trsf(); t.SetTranslation(gp_Vec(dx, dy, dz))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def clean(shape):
    u = ShapeUpgrade_UnifySameDomain(shape, True, True, True)
    u.Build()
    return u.Shape()


def volume(shape):
    p = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, p)
    return p.Mass()


# ---------------- parts (mirrors case.py step for step) ----------------
def build_shell(trackpad):
    H, CAV = C.H, C.CAVITY
    body = prism(C.outer, 0, H)
    body = round_face_edges(body, H, C.EDGE_CH)

    cuts = [prism(C.inner, -1, CAV)]
    cuts += [prism(h, CAV - 1, H + 1) for h in C.holes]
    cuts += [prism(p, CAV - 1, H - C.LIP) for p in C.pockets]
    if C.CAP_RECESS > 0:
        cuts.append(prism(C.CAP_RECESS_POLY, H - C.CAP_RECESS, H + 1))     # keycap travel recess
    # OLED: glass pocket, window with a small 45 deg lead-in
    cuts.append(prism(C.GLASS_RECT.buffer(0.15, join_style=2), CAV - 1, H - C.BEZEL_T))
    cuts.append(prism(C.WIN_RECT, H - C.BEZEL_T - 1, H + 1))
    cuts.append(prism(C.WIN_RECT.buffer(0.4, join_style=2), H - 0.4, H + 1))
    # USB-C slot open at the top with a rounded bottom
    w = C.USB_SLOT_W
    y0, y1 = C.inner_top - 3, C.inner_top + C.WALL + 3
    zb = C.slot_bottom + 2.0
    cuts.append(prism(box(C.mcu_cx - w / 2, y0, C.mcu_cx + w / 2, y1), zb, H + 1))
    # rounded bottom: half-ellipse drawn in the x/z plane, extruded along y
    from shapely import affinity
    ell = affinity.translate(affinity.scale(Point(0, 0).buffer(1.0, 64), w / 2, 2.0), C.mcu_cx, zb)
    face = _faces(ell, 0)[0]                      # (x, y=z_value) in the XY plane
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 3.141592653589793 / 2)
    face = TopoDS.Face(BRepBuilderAPI_Transform(face, t, True).Shape())   # now lies in XZ, y = 0
    cuts.append(move(BRepPrimAPI_MakePrism(face, gp_Vec(0, y1 - y0, 0)).Shape(), 0, y0, 0))
    if C.USB_TOP + 0.3 > CAV:
        cuts.append(prism(box(C.mcu_cx - 4.9, C.mcu_top - 8.0, C.mcu_cx + 4.9, C.inner_top + 0.1),
                          CAV - 1, C.USB_TOP + 0.3))
    if trackpad:
        cuts.append(prism(C.TP_DISC, H - C.TP_T, H + 1))
        cuts.append(prism(Point(*C.TP_CENTER).buffer(C.TP_D / 2 - C.TP_LEDGE, 128), CAV - 1, H))

    # power switch: knob slot through the side wall + ON bar
    kh = C.SW_KNOB_W / 2 + 0.25
    cuts.append(prism(box(C.SW_FACE - 0.5, C.SW_YC - C.SW_SLOT_Y, C.SW_XOUT + 6, C.SW_YC + C.SW_SLOT_Y),
                      C.SW_ZC - kh, C.SW_ZC + kh))
    cuts.append(prism(box(C.SW_MARK_X - 0.3, C.SW_MARK_Y - 0.35, C.SW_MARK_X + 1, C.SW_MARK_Y + 0.35),
                      C.SW_MARK_Z - 0.9, C.SW_MARK_Z + 0.9))
    shell = cut_all(body, cuts)

    # screw bosses (clipped to the outline), then pilot holes
    bosses = []
    for (x, y) in C.BOSSES:
        disc = Point(x, y).buffer(C.BOSS_D / 2, 64).intersection(C.outer.buffer(-0.01)).difference(C.SW_BODY.buffer(0.15))
        bosses.append(prism(disc, 0, CAV + 0.1))
    bosses += [cyl(x, y, C.POST_D, 0, CAV + 0.1) for (x, y) in C.POSTS]
    shell = fuse_all([shell] + bosses)
    shell = cut_all(shell, [cyl(x, y, C.INSERT_HOLE, -1, C.INSERT_DEPTH) for (x, y) in C.SCREWS]
                    + [prism(p, CAV, H - C.LIP) for p in C.pockets])
    return clean(shell)


def build_bottom(sx=1):
    """sx=-1 builds the right base directly from mirrored 2D geometry (cleaner than mirroring a solid)"""
    from shapely import affinity
    F = (lambda g: g) if sx == 1 else (lambda g: affinity.scale(g, xfact=-1, yfact=1, origin=(0, 0)))
    P = lambda x, y: (sx * x, y)
    B = C.BOTTOM_T
    body = prism(F(C.outer), -B, 0)
    body = round_face_edges(body, -B, C.BASE_CH)
    adds = []
    adds.append(prism(F(C.SW_CRADLE), 0, 1.8))                        # power switch cradle
    adds.append(prism(F(C.RST_CRADLE), 0, C.RST_WALL_H))             # rescue reset switch cradle
    for side in (-1, 1):
        rx = C.mcu_cx + side * (C.MCU_W / 2 - 1.4)
        adds.append(prism(F(box(rx - 0.6, C.mcu_top - C.MCU_L + 1.5, rx + 0.6, C.mcu_top - 9.0)), 0, C.MCU_RAIL))
    body = fuse_all([body] + adds)
    cuts = []
    for (x, y) in C.SCREWS:
        cuts.append(cyl(*P(x, y), C.SCREW_CLR, -B - 1, 1))
        # start 0.3 mm below the face (same 90 deg cone, just extended) so no sliver faces form
        cuts.append(cone(*P(x, y), C.SCREW_HEAD, C.SCREW_CLR, -B - 0.01, -B + 1.0))
    cuts += [cyl(*P(x, y), C.MAG_D, -B - 0.01, 0.01) for (x, y) in C.MAGNETS]
    cuts.append(cyl(*P(*C.RST_C), C.RST_PIN_D, -B - 1, 1))                                  # reset pinhole
    cuts.append(cone(*P(*C.RST_C), C.RST_PIN_D + 1.6, C.RST_PIN_D, -B - 0.01, -B + 0.5))     # funnel
    cuts.append(prism(F(C.BATT_RECT.buffer(0.3, join_style=2)), -C.BATT_RECESS, 0.01))   # battery dip
    import details as DT
    D = C.DETAILS
    cuts.append(prism(F(D["foot_pockets"]), -B - 1, -B + DT.FOOT_DEPTH))
    cuts.append(prism(F(D["text_left"] if sx == 1 else D["text_right"]), -B - 1, -B + DT.TEXT_DEPTH))
    return clean(cut_all(body, cuts))


def build_fit_test():
    pt = C.PLATE_T
    test = prism(box(0, 0, 4 * 19.05, 19.05), 0, pt)
    W, D, k = 4 * 19.05, 19.05, 1.2       # skirt as four bars (avoids a face with a hole)
    bars = [box(0, 0, W, k), box(0, D - k, W, D), box(0, 0, k, D), box(W - k, 0, W, D)]
    test = fuse_all([test] + [prism(bb, -C.CAVITY, 0.01) for bb in bars])
    cuts = []
    for i, s in enumerate((13.8, 13.9, 14.0, 14.1)):
        cx = 19.05 * (i + 0.5)
        cuts.append(prism(box(cx - s / 2, 9.525 - s / 2, cx + s / 2, 9.525 + s / 2), -1, pt + 1))
        cuts.append(prism(box(cx - C.POCKET / 2, 9.525 - C.POCKET / 2, cx + C.POCKET / 2, 9.525 + C.POCKET / 2),
                          -1, pt - C.LIP))
        for j in range(i + 1):
            cuts.append(prism(box(cx - 4 + 2.2 * j, -0.5, cx - 3 + 2.2 * j, 1.0), pt - 0.6, pt + 1))
    from shapely.ops import unary_union
    isl = unary_union([box(19.05 * (i + 0.5) - C.ISLAND / 2, 9.525 - C.ISLAND / 2, 19.05 * (i + 0.5) + C.ISLAND / 2, 9.525 + C.ISLAND / 2)
                       for i in range(4)])
    if C.CAP_RECESS > 0:
        cuts.append(prism(box(1.2, 1.2, W - 1.2, D - 1.2).difference(isl), pt - C.CAP_RECESS, pt + 1))   # keycap travel recess
    return clean(cut_all(test, cuts))


def write_step(shape, name):
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    w = STEPControl_Writer()
    w.Transfer(shape, STEPControl_AsIs)
    path = os.path.join(OUT, f"{name}.step")
    w.Write(path)
    ok = BRepCheck_Analyzer(shape).IsValid()
    print(f"{name:20s} valid={ok}  {volume(shape)/1000:6.2f} cm3  -> {os.path.basename(path)}")
    return path


def mirror(shape):
    from OCP.ShapeFix import ShapeFix_Shape
    t = gp_Trsf(); t.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)))
    m = BRepBuilderAPI_Transform(shape, t, True).Shape()
    if not BRepCheck_Analyzer(m).IsValid():
        fx = ShapeFix_Shape(m); fx.Perform(); m = fx.Shape()
    return m


if __name__ == "__main__":
    shell_l = build_shell(trackpad=False)
    shell_r = mirror(build_shell(trackpad=True))
    bottom_l = build_bottom()
    bottom_r = build_bottom(sx=-1)
    parts = {"shell_left": shell_l, "shell_right": shell_r, "bottom_left": bottom_l,
             "bottom_right": bottom_r, "switch_fit_test": build_fit_test()}
    for n, s in parts.items():
        write_step(s, n)

    # assembly: both halves as they sit on the desk (right half shifted over)
    gap = 2 * (C.outer.bounds[2] + 6)
    comp = TopoDS_Compound(); bb = BRep_Builder(); bb.MakeCompound(comp)
    for s in (shell_l, bottom_l, move(shell_r, gap), move(bottom_r, gap)):
        bb.Add(comp, s)
    write_step(comp, "assembly_both_halves")


# ---------------- viewer meshes from the B-rep (clean chamfers) ----------------
def tessellate(shape, lin=0.04, ang=0.25):
    """triangles in case coordinates, faces kept separate (sharp edges stay sharp)"""
    import numpy as np
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopAbs import TopAbs_REVERSED
    BRepMesh_IncrementalMesh(shape, lin, False, ang, True)
    verts, tris, base = [], [], 0
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            tr = loc.Transformation()
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(tr)
                verts.append((p.X(), p.Y(), p.Z()))
            rev = face.Orientation() == TopAbs_REVERSED
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get()
                tris.append((base + a - 1, base + c - 1, base + b - 1) if rev else (base + a - 1, base + b - 1, base + c - 1))
            base += tri.NbNodes()
        exp.Next()
    return np.array(verts), np.array(tris, dtype=np.uint32)


def write_viewer_mesh(shape, path):
    import struct, numpy as np
    v, t = tessellate(shape)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    if np.einsum("ij,ij->i", a, np.cross(b, c)).sum() < 0:   # inside-out after mirroring
        t = t[:, [0, 2, 1]]
    q = np.round(np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1) * 100).astype(np.int16)
    with open(path, "wb") as f:
        f.write(struct.pack("<II", len(q), len(t)))
        f.write(q.tobytes())
        if len(q) < 65536:
            f.write(t.astype(np.uint16).tobytes())
        else:
            if len(q) % 2:
                f.write(b"\0\0")
            f.write(t.astype(np.uint32).tobytes())
    vol = np.einsum("ij,ij->i", v[t[:, 0]], np.cross(v[t[:, 1]], v[t[:, 2]])).sum() / 6000
    print(f"viewer mesh {os.path.basename(path)}: vol {vol:.2f} cm3, {len(q)} verts, {len(t)} tris, {os.path.getsize(path)/1024:.0f} KB")


if __name__ == "__main__":
    vdir = C.VIEWER_DIR
    for n in ("shell_left", "shell_right", "bottom_left", "bottom_right"):
        write_viewer_mesh(parts[n], os.path.join(vdir, n + ".bin"))

    # printable STLs straight from the solids: watertight, true fillets (replaces case.py's versions)
    import math, tempfile, trimesh
    from OCP.STEPControl import STEPControl_Reader
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    for n, flip in (("shell_left", True), ("shell_right", True), ("bottom_left", False), ("bottom_right", False),
                    ("switch_fit_test", True)):
        rd = STEPControl_Reader(); rd.ReadFile(os.path.join(C.STEP_DIR, n + ".step")); rd.TransferRoots()
        sh = rd.OneShape()
        BRepMesh_IncrementalMesh(sh, 0.02, False, 0.2, True)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.stl"); StlAPI_Writer().Write(sh, p); m = trimesh.load(p)
        m.merge_vertices(digits_vertex=4)
        if flip:   # plate side on the bed
            m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation(-m.bounds[0])
        dest = os.path.join(C.TEST_DIR, "1_switch_strip.stl") if n == "switch_fit_test" else os.path.join(C.KB_DIR, n + ".stl")
        m.export(dest)
        print(f"{os.path.basename(dest)} from STEP: watertight={m.is_watertight} {m.volume / 1000:.2f} cm3")

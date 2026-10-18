"""CLP keycaps (vvhg1/clp-keycaps, GPL v3) on the Corne LP: which cap goes where, and how tall.

    import clp
    clp.assign(key)        -> (model, turn_deg)   model name in keycaps/clp/<model>.stl
    clp.top(key)           -> cap top above the plate's top face (mm)
    clp.CAP_TOP            -> tallest cap on the board (the carry case is built around it)
    clp.footprint(key, z)  -> keycap outline (case frame) of everything above height z over the plate
    python3 clp.py         -> table + ../print/keycaps/ (Orca 3MF plate + one file per cap) + viewer meshes

Caps sit on the switch (checked against the KS-33 STEP model): the KS-33 cross stands in a round
well whose floor is 3.0 mm over the plate, and a cap's round stem drops into it and stops on the floor.
Stock CLP (made for full-height MX) would sit 2.45 mm up, and its shell would hit the KS-33's wide top
housing after only 1.3 mm of the 3.2 mm travel (it actuates at 1.7). So the print files use a KS-33
version: the same caps, with the round stem made STEM_EXT longer (it pokes 1.55 mm below the skirt).
That lifts every cap 2.1 mm: full travel with 0.2 mm to spare, and the skirt never reaches the plate.
"""
import os, math, zipfile, functools
import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union
from shapely import affinity
import layout as L

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "keycaps", "clp")
WELL_FLOOR = 3.0        # KS-33: floor of the well round the cross stem, over the plate (at rest)
SOCKET_LIFT = 0.55      # stock CLP: stem bottom above the skirt edge
STEM_EXT = 2.1          # KS-33 version: round stem made this much longer (downward)
SEAT = WELL_FLOOR - SOCKET_LIFT + STEM_EXT      # skirt edge over the plate (4.55)
TRAVEL = 3.2            # KS-33 total travel

# model, how many, where (name, file stem)
MODELS = {
    "saddle":        ("Saddle",        "home row (all but index)"),
    "saddle_homing": ("Saddle Homing", "home row index (F / J)"),
    "tilt7":         ("Tilt 7",        "top row as printed, bottom row turned 180"),
    "thumb":         ("Thumb",         "two inner thumb keys"),
    "tilt7_1u5":     ("Tilt 7 1.5u",   "big outer thumb key"),
}


def assign(k):
    """(model, extra turn in degrees) for one key (x, y, rot, wu, row, col) of a half"""
    _, _, _, wu, row, col = k
    if row == 3:
        return ("tilt7_1u5", 0) if wu > 1 else ("thumb", 0)
    if row == 1:
        return ("saddle_homing", 0) if col == 4 else ("saddle", 0)
    if row == 0:
        return ("tilt7", 0)            # low edge toward you
    return ("tilt7", 180)              # bottom row: low edge toward the home row


@functools.lru_cache(None)
def raw(model):
    """stock CLP mesh (two shells: cap + stem)"""
    return trimesh.load(os.path.join(SRC, model + ".stl"))


@functools.lru_cache(None)
def mesh(model):
    """KS-33 version: the stock cap untouched, plus a STEM_EXT extension of its round stem (same
    cross socket all the way through) below the stem's bottom. One solid."""
    import manifold3d as m3
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient
    def M(t):
        t = t.copy(); t.merge_vertices()
        return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
    parts = raw(model).split(only_watertight=False)
    stem = min(parts, key=lambda p: p.volume); cap = max(parts, key=lambda p: p.volume)
    z0 = float(stem.bounds[0][2])
    loops = sorted((Polygon(e[:, :2]) for e in stem.section(plane_origin=[0, 0, z0 + 1.0], plane_normal=[0, 0, 1]).discrete),
                   key=lambda q: -q.area)
    ring = orient(Polygon(loops[0].buffer(-0.01, join_style=2).exterior.coords,
                          [loops[1].buffer(0.01, join_style=2).exterior.coords]), 1)   # tube + cross socket (no coincident walls)
    cs = m3.CrossSection([list(ring.exterior.coords)[:-1]] + [list(i.coords)[:-1] for i in ring.interiors])
    ext = cs.extrude(STEM_EXT + 0.3).translate([0, 0, z0 - STEM_EXT]).to_mesh()
    ext = trimesh.Trimesh(np.asarray(ext.vert_properties)[:, :3], np.asarray(ext.tri_verts))
    # three closed shells that overlap (like the stock CLP files): every slicer merges them
    return trimesh.util.concatenate([cap, stem, ext])


def placed(k):
    """the cap mesh in case coordinates (z = 0 at the plate's top face)"""
    model, turn = assign(k)
    m = mesh(model).copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(k[2] + turn), [0, 0, 1]))
    m.apply_translation([k[0], k[1], SEAT])
    return m


def top(k):
    return SEAT + float(mesh(assign(k)[0]).bounds[1][2])


def footprint(k, z):
    """outline of the part of the cap that rises above z (plate frame), or None"""
    m = placed(k)
    v = m.vertices[m.vertices[:, 2] >= z]
    if len(v) < 3:
        return None
    return MultiPoint([tuple(p) for p in v[:, :2]]).convex_hull


CAP_TOP = None   # filled below (needs layout keys)
try:
    _keys = L.all_keys()
    CAP_TOP = max(top(k) for k in _keys)
except Exception:
    pass


# ---------------- print package ----------------
def _model_xml(objs):
    f = lambda v: ("%.5f" % v).rstrip("0").rstrip(".")
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n<resources>\n']
    for oid, name, m in objs:
        out.append(f'<object id="{oid}" name="{name}" type="model"><mesh><vertices>\n')
        out.append("".join(f'<vertex x="{f(a)}" y="{f(b)}" z="{f(c)}"/>\n' for a, b, c in m.vertices))
        out.append("</vertices><triangles>\n")
        out.append("".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in m.faces))
        out.append("</triangles></mesh></object>\n")
    out.append("</resources>\n")
    return out


def write_3mf(path, objs, items):
    """objs: [(id, name, trimesh)], items: [(id, x, y)] -> generic 3MF (copies become instances in Orca)"""
    x = _model_xml(objs)
    x.append("<build>\n" + "".join(f'<item objectid="{o}" transform="1 0 0 0 1 0 0 0 1 {a:.3f} {b:.3f} 0"/>\n'
                                   for o, a, b in items) + "</build>\n</model>\n")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", "".join(x))


PRINT_ANGLE = 70.0      # stand each cap on a side edge (CLP README: 60-80 deg)


def print_pose(model):
    m = mesh(model).copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(PRINT_ANGLE), [0, 1, 0]))
    b = m.bounds
    m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    return m


def counts():
    c = {}
    for k in L.all_keys():
        c[assign(k)[0]] = c.get(assign(k)[0], 0) + 2      # both halves
    return c


if __name__ == "__main__":
    import json, struct
    keys = L.all_keys()
    cnt = counts()
    print(f"seat {SEAT:.2f} mm, tallest cap top {CAP_TOP:.2f} mm over the plate")
    for mdl, (nm, where) in MODELS.items():
        print(f"  {nm:14s} x{cnt.get(mdl, 0):2d}  top {SEAT + mesh(mdl).bounds[1][2]:5.2f}  {where}")
    ks = os.path.join(HERE, "..", "keycaps", "clp_ks33"); os.makedirs(ks, exist_ok=True)
    for mdl in MODELS:
        m = mesh(mdl); m.export(os.path.join(ks, mdl + ".stl"))
        print(f"  KS-33 {mdl}: watertight={m.is_watertight} bodies={m.body_count} z {m.bounds[0][2]:.2f}..{m.bounds[1][2]:.2f}")
    out = os.path.join(HERE, "..", "print", "keycaps"); os.makedirs(out, exist_ok=True)
    order = ["saddle", "saddle_homing", "thumb", "tilt7", "tilt7_1u5"]
    objs, items, row, k, PX, PY, COLS = [], [], 0, 0, 17.0, 23.0, 8
    rows = {}
    for oid, mdl in enumerate(order, 1):
        m = print_pose(mdl)
        objs.append((oid, f"{MODELS[mdl][0]} - {MODELS[mdl][1]}", m))
        if m.extents[1] > 20 and k:
            row += 1; k = 0
        for i in range(cnt[mdl]):
            if k and k % COLS == 0:
                row += 1; k = 0
            items.append([oid, k * PX, row]); k += 1
            rows[row] = max(rows.get(row, 0), m.extents[1] + 5)
    ys, acc = {}, 0.0
    for r in sorted(rows):
        ys[r] = acc + rows[r] / 2; acc += rows[r]
    W = (COLS - 1) * PX
    items = [(o, 128 - W / 2 + x, 128 + acc / 2 - ys[r]) for o, x, r in items]
    write_3mf(os.path.join(out, "Corne-LP_CLP-keycaps_42pcs.3mf"), objs, items)
    single = os.path.join(out, "all-42-caps"); os.makedirs(single, exist_ok=True)
    for f in os.listdir(single):
        os.remove(os.path.join(single, f))
    tags = {"saddle": "1_home-saddle", "saddle_homing": "2_index-homing", "tilt7": "3_top-bottom-tilt7",
            "thumb": "4_thumb-inner", "tilt7_1u5": "5_thumb-outer-1.5u"}
    for mdl in order:
        tmp = os.path.join(out, "_one.3mf")
        write_3mf(tmp, [(1, tags[mdl], mesh(mdl))], [(1, 0, 0)])
        data = open(tmp, "rb").read(); os.remove(tmp)
        for i in range(cnt[mdl]):
            open(os.path.join(single, f"{tags[mdl]}_{i + 1:02d}.3mf"), "wb").write(data)
    print("print package:", len(items), "caps on the plate,", len(os.listdir(single)), "single files")

    # viewer: one light mesh per model (key-local, three.js axes: x, z_up -> y, -y -> z), skirt edge at 0
    V = os.path.join(HERE, "..", "viewer")
    for mdl in MODELS:
        m = mesh(mdl).copy()
        target = 3000 if mdl != "tilt7_1u5" else 4000
        try:
            m = m.simplify_quadric_decimation(face_count=target)
        except Exception as e:
            print("decimation skipped:", e)
        p = np.asarray(m.vertices); t = np.asarray(m.faces, dtype=np.uint32)
        q = np.round(np.stack([p[:, 0], p[:, 2], -p[:, 1]], 1) * 100).astype(np.int16)
        with open(os.path.join(V, f"cap_{mdl}.bin"), "wb") as fh:
            fh.write(struct.pack("<II", len(q), len(t))); fh.write(q.tobytes())
            fh.write(t.astype(np.uint16 if len(q) < 65536 else np.uint32).tobytes())
        print(f"  viewer cap_{mdl}: {len(t)} tris")

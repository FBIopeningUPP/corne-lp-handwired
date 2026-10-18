"""Check every CLP cap against the KS-33 STEP model (ref/ks33.step): how far each cap can travel before
its shell touches the switch housing, flange or plate. KS-33 travel is 3.2 mm.

    python3 ks33_check.py
Model frame: the switch's 15 mm flange bottom (= plate top) is at z = 2.55; the cross stands in a well
whose floor is at 5.55 (3.0 over the plate); the slider top is at 8.55 (6.0 over the plate).
"""
import os, tempfile
import numpy as np, trimesh, manifold3d as m3
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
import clp

PLATE_TOP = 2.55
HERE = os.path.dirname(os.path.abspath(__file__))


def M(t):
    t = t.copy(); t.merge_vertices()
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def solids():
    rd = STEPControl_Reader(); rd.ReadFile(os.path.join(HERE, "..", "ref", "ks33.step")); rd.TransferRoots()
    ex = TopExp_Explorer(rd.OneShape(), TopAbs_SOLID); out = []
    with tempfile.TemporaryDirectory() as d:
        while ex.More():
            s = ex.Current(); BRepMesh_IncrementalMesh(s, 0.02, False, 0.2, True)
            p = os.path.join(d, "s.stl"); StlAPI_Writer().Write(s, p)
            t = trimesh.load(p); t.apply_translation([0, 0, -PLATE_TOP]); out.append(t); ex.Next()
    return out


if __name__ == "__main__":
    S = sorted(solids(), key=lambda t: -t.volume)          # bottom housing, top housing, slider, ...
    bottom, top = M(S[0]), M(S[1])
    plate = m3.Manifold.cube([40, 40, 2.0], True).translate([0, 0, -1.0])
    well = m3.Manifold.cylinder(10, 2.85, 2.85, 64).translate([0, 0, -3])   # the stem rides inside the slider's well
    print(f"cap seat {clp.SEAT:.2f} mm over the plate, travel {clp.TRAVEL} mm")
    for mdl in clp.MODELS:
        cap = M(clp.mesh(mdl)) - well
        hits = {}
        for nm, ob in (("top housing", top), ("bottom housing/flange", bottom), ("plate", plate)):
            free = 0.0
            for tr in np.arange(0, 5.0, 0.02):
                if (cap.translate([0, 0, clp.SEAT - tr]) ^ ob).volume() > 1e-3:
                    break
                free = tr
            hits[nm] = round(free, 2)
        first = min(hits.values())
        print(f"  {mdl:14s} free travel {first:.2f} mm  {'OK' if first >= clp.TRAVEL else 'TOO SHORT'}  {hits}")

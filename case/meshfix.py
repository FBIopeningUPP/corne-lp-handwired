"""close small boundary loops (tessellation cracks) with a fan around the loop centroid"""
import numpy as np, trimesh
from trimesh.grouping import group_rows


def close_cracks(m, max_len=20.0):
    m.merge_vertices(digits_vertex=4)
    if m.is_watertight:
        return m
    e = m.edges_sorted; g = group_rows(e, require_count=1)
    # directed boundary edges (as they appear in faces)
    de = m.edges[g]
    nxt = {a: b for a, b in de}
    verts, faces = list(m.vertices), list(m.faces)
    seen = set()
    for start in list(nxt):
        if start in seen: continue
        loop, v = [], start
        while v not in seen and v in nxt:
            seen.add(v); loop.append(v); v = nxt[v]
        if len(loop) < 3: continue
        pts = m.vertices[loop]
        if np.linalg.norm(pts.max(0) - pts.min(0)) > max_len: continue
        c = len(verts); verts.append(pts.mean(0))
        for i in range(len(loop)):           # reversed winding: the patch faces out like its neighbours
            faces.append([loop[(i + 1) % len(loop)], loop[i], c])
    out = trimesh.Trimesh(np.array(verts), np.array(faces), process=True)
    trimesh.repair.fix_normals(out)
    return out

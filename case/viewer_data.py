"""Export meshes + layout data for the 3D viewer (../viewer/).

Coordinates are converted to three.js style: x right, y up, z toward you  (x, z_case, -y_case).
Mesh files: uint32 nverts, uint32 ntris, int16 positions (0.01 mm), indices (uint16 if nverts < 65536).
"""
import json, os, re, struct
import numpy as np
import case as C
import layout as L

V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "viewer")
os.makedirs(V, exist_ok=True)


def write_mesh(m, name):
    mesh = m.to_mesh()
    p = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    t = np.asarray(mesh.tri_verts).astype(np.uint32)
    q = np.stack([p[:, 0], p[:, 2], -p[:, 1]], 1)
    qi = np.round(q * 100).astype(np.int16)
    with open(os.path.join(V, name + ".bin"), "wb") as f:
        f.write(struct.pack("<II", len(qi), len(t)))
        f.write(qi.tobytes())
        if len(qi) < 65536:                   # uint16 indices (all parts fit)
            f.write(t.astype(np.uint16).tobytes())
        else:
            if len(qi) % 2:
                f.write(b"\0\0")
            f.write(t.astype(np.uint32).tobytes())
    return os.path.getsize(os.path.join(V, name + ".bin"))


# The viewer's meshes come from step.py (tessellated B-rep, clean chamfers).
# write_mesh() stays as a fallback: run with --stl-meshes if OpenCascade isn't installed.
import sys
sizes = {}
if "--stl-meshes" in sys.argv:
    sizes = {
        "shell_left": write_mesh(C.shell, "shell_left"),
        "shell_right": write_mesh(C.shell_tp.mirror([1, 0, 0]), "shell_right"),
        "bottom_left": write_mesh(C.bottom, "bottom_left"),
        "bottom_right": write_mesh(C.bottom.mirror([1, 0, 0]), "bottom_right"),
    }

def rect(r):
    x0, y0, x1, y1 = r.bounds
    return [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]

data = {
    "H": C.H, "bottomT": C.BOTTOM_T, "plateT": C.PLATE_T, "bezelT": C.BEZEL_T, "glassT": C.GLASS_T,
    "battT": C.BATT_T, "oledPcbT": C.OLED_PCB_T, "outer": [round(v, 3) for v in C.outer.bounds],
    "keys": [[round(k[0], 3), round(k[1], 3), k[2], k[3], k[4], k[5]] for k in C.keys],
    "mcu": rect(C.MCU_RECT), "batt": rect(C.BATT_RECT), "battBox": [round(C.BATT_C[0], 2), round(C.BATT_C[1], 2), C.BATT_W, C.BATT_L, C.BATT_ANG, C.BATT_RECESS], "oled": rect(C.OLED_RECT),
    "glass": rect(C.GLASS_RECT), "win": rect(C.WIN_RECT), "sw": rect(C.SW_RECT),
    "tp": [C.TP_CENTER[0], C.TP_CENTER[1], C.TP_D, C.TP_T],
    "magnets": C.MAGNETS, "magD": C.MAG_D - 0.2, "magT": C.MAG_T - 0.1,
    "bosses": C.SCREWS, "usbTop": C.inner_top, "mcuRail": C.MCU_RAIL, "swPed": C.SW_PED,
    "swH": C.SW_BODY_H, "swKnob": [C.SW_FACE, C.SW_FACE + C.SW_KNOB_L, C.SW_YC, C.SW_ZC, C.SW_KNOB_W],
}

# Blip sprites + font straight from the firmware header
hdr = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "zmk-config", "src", "sprites.h")).read()
frames = {}
for m in re.finditer(r"\[BLIP_(\w+)\] = \{([^}]*)\}", hdr):
    frames[m.group(1)] = [int(b, 16) for b in re.findall(r"0x[0-9a-f]{2}", m.group(2))]
order = re.search(r"enum blip_frame \{([^}]*)\}", hdr).group(1)
order = [s.strip().replace("BLIP_", "") for s in order.split(",") if s.strip() and "COUNT" not in s]
font = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"\{'(.)', 0x([0-9a-f]{4})\}", hdr)}
import carry as _K
data["carry"] = {"below": round(_K.ABOVE, 2), "size": [round(v, 1) for v in
                 (_K.outer.bounds[2] - _K.outer.bounds[0], _K.outer.bounds[3] - _K.outer.bounds[1], 2 * (_K.DEPTH + _K.SKIN))]}
data["outline"] = [[round(x, 1), round(y, 1)] for x, y in C.outer.simplify(0.3).exterior.coords]   # contact shadow
data["carry"]["outline"] = [[round(x, 1), round(y, 1)] for x, y in _K.outer.simplify(0.3).exterior.coords]
import clp as _clp
import routing as _rt
def _r(v): return [round(float(t), 2) for t in v]
data["wiring"] = {}
for _side in ("left", "right"):
    _w = _rt.build(_side)
    data["wiring"][_side] = {"wires": [{"n": w["n"], "c": w["c"], "p": [_r(q) for q in w["p"]], **({"r": w["r"]} if "r" in w else {})}
                                       for w in _w["wires"]],
                             "diodes": [{"a": _r(d["a"]), "k": _r(d["k"])} for d in _w["diodes"]]}
data["swBottom"] = round(C.H - 2.55, 2)          # KS-33 bottom over the base floor
data["rst"] = [C.RST_C[0], C.RST_C[1], C.RST_ANG, C.RST_W, C.RST_L]   # rescue reset tact switch
data["capTop"] = round(_clp.CAP_TOP, 2)          # tallest CLP cap top over the plate
data["capSeat"] = round(_clp.SEAT, 2)            # skirt edge over the plate
data["capModels"] = [list(_clp.assign(k)) for k in C.keys]   # per key: [model, extra turn deg]
data["sprites"] = {k: frames[k] for k in order}
data["spriteOrder"] = order
data["font"] = font

with open(os.path.join(V, "data.js"), "w") as f:
    f.write("window.CORNE = " + json.dumps(data, separators=(",", ":")) + ";\n")
print({k: f"{v/1024:.0f} KB" for k, v in sizes.items()}, "data.js",
      f"{os.path.getsize(os.path.join(V, 'data.js'))/1024:.0f} KB")

"""Test-print kit: print this before the full case (about 25 min, ~6 g).

    python3 testkit.py -> ../print/test-kit/test_kit.3mf (+ STLs; run case.py or step.py first for the strip)
      1  switch strip   4 plate holes 13.8 / 13.9 / 14.0 / 14.1 (1-4 notches): pick the one a KS-33 clicks into
                        firmly, set HOLE in case.py; the skirt is as deep as the case, so trimmed pins must clear the table
      2  coupon         magnet holes 6.0 / 6.2 / 6.4 (1-3 notches) in a 1 mm floor like the base,
                        heat-set insert bosses with 2.8 / 3.0 / 3.2 holes (1-3 notches) like the shell,
                        the reset pinhole + cradle exactly as in the base
      3  CLP Saddle     one keycap, standing at 70 deg: check it pushes onto a KS-33 stem firmly
"""
import os
import numpy as np, trimesh
from shapely.geometry import box, Point
import case as C
import clp

OUT = C.TEST_DIR


def coupon():
    W, Dp = 62.0, 24.0
    m = C.prism(box(0, 0, W, Dp), -C.BOTTOM_T, 0)
    cut = []
    # magnets (through the 1 mm floor, glue flush), notches on the front edge
    for i, d in enumerate((6.0, 6.2, 6.4)):
        x = 6 + i * 9.0
        cut.append(C.cyl(x, 7.0, d, -2, 1))
        for j in range(i + 1):
            cut.append(C.prism(box(x - 2.0 + j * 1.4, -0.1, x - 1.4 + j * 1.4, 0.8), -2, 1))
    # heat-set insert bosses (same boss and depth as the shell)
    bosses = []
    for i, d in enumerate((2.8, 3.0, 3.2)):
        x = 6 + i * 9.0
        bosses.append(C.cyl(x, 17.0, C.BOSS_D, 0, C.INSERT_DEPTH + 0.6))
        cut.append(C.cyl(x, 17.0, d, 0.6, C.INSERT_DEPTH + 1))
        for j in range(i + 1):
            cut.append(C.prism(box(x - 2.0 + j * 1.4, Dp - 0.8, x - 1.4 + j * 1.4, Dp + 0.1), -2, 1))
    for b in bosses:
        m = m + b
    # reset: cradle + pinhole + funnel, same as the base
    rx, ry = 48.0, 12.0
    from shapely import affinity
    cr = affinity.translate(affinity.rotate(C.RST_CRADLE, 0, origin=C.RST_C), rx - C.RST_C[0], ry - C.RST_C[1])
    m = m + C.prism(cr, 0, C.RST_WALL_H)
    cut.append(C.cyl(rx, ry, C.RST_PIN_D, -2, 1))
    cut.append(C.cyl(rx, ry, C.RST_PIN_D + 1.6, -C.BOTTOM_T - 0.01, -C.BOTTOM_T + 0.5, d2=C.RST_PIN_D))
    for c in cut:
        m = m - c
    return m


def tm(man):
    t = C.to_trimesh(man); t.apply_translation(-t.bounds[0]); return t


if __name__ == "__main__":
    strip = trimesh.load(os.path.join(OUT, "1_switch_strip.stl"))
    cp = tm(coupon())
    cap = clp.print_pose("saddle")
    for n, t in (("1_switch_strip", strip), ("2_coupon_magnet_insert_reset", cp), ("3_clp_saddle_cap", cap)):
        print(f"{n:32s} watertight={t.is_watertight} {t.extents.round(1)}")
        t.export(os.path.join(OUT, n + ".stl"))
    # one plate: strip and coupon flat, cap standing; centred on a 256 bed (press A for others)
    def at(t, x, y):
        t = t.copy(); t.apply_translation([-t.bounds[0][0], -t.bounds[0][1], -t.bounds[0][2]]); return t, x, y
    objs = [(1, "Switch fit strip (13.8-14.1)", strip), (2, "Coupon: magnets / inserts / reset", cp), (3, "CLP Saddle cap", cap)]
    pl = [(1, 90, 150), (2, 90, 120), (3, 175, 135)]
    objs2 = []
    for oid, name, t in objs:
        t = t.copy(); t.apply_translation(-t.bounds[0]); objs2.append((oid, name, t))
    clp.write_3mf(os.path.join(OUT, "test_kit.3mf"), objs2, pl)
    print("->", OUT)

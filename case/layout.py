"""Corne-style 3x6+3 key layout (left half), in mm.

All case geometry is derived from this file, so tweaking a column
offset here moves the plate hole, case wall and screw bosses together.
"""
import math

U = 19.05  # key pitch. Gateron low-profile keycaps fit standard 19.05 spacing.

# Corne column stagger (in units, +up). Pinky columns low, middle finger highest.
COL_STAGGER = [0.0, 0.0, 0.25, 0.375, 0.25, 0.125]

def main_keys():
    """(x, y, rot_deg, width_u, row, col) for the 18 main keys."""
    keys = []
    for col in range(6):
        for row in range(3):
            x = col * U
            y = -(row * U) + COL_STAGGER[col] * U
            keys.append((x, y, 0.0, 1.0, row, col))
    return keys

def thumb_keys():
    """Corne thumb cluster: two 1u keys + one 1.5u key turned on its side."""
    base_y = -3 * U + COL_STAGGER[3] * U - 0.3 * U
    return [
        (3.5 * U,  base_y,               0.0,  1.0, 3, 3),
        (4.55 * U, base_y - 0.08 * U,  -12.0,  1.0, 3, 4),
        (5.68 * U, base_y - 0.30 * U,  -26.0,  1.5, 3, 5),
    ]

def all_keys():
    return main_keys() + thumb_keys()

def rect(cx, cy, w, h, rot_deg):
    """Corners of a w x h rectangle centred at (cx, cy), rotated."""
    a = math.radians(rot_deg)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for dx, dy in [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]:
        pts.append((cx + dx*ca - dy*sa, cy + dx*sa + dy*ca))
    return pts

def key_rect(k, w=U, h=U):
    x, y, r, wu, *_ = k
    # 1.5u thumb is long along Y (stood on its side), like the Corne.
    if wu != 1.0:
        return rect(x, y, w, h * wu, r)
    return rect(x, y, w, h, r)

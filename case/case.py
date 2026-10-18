"""Corne LP Wireless: 3D-printable case for a handwired, split, low-profile Corne.

Two printed parts per half:
  shell  - switch plate + walls + OLED bezel in one piece (print plate side DOWN)
  bottom - 1.0 mm base (magnets, feet pockets, reset pinhole), screwed to the shell

Everything lives inside: a SuperMini nRF52840 on rails under a 0.91" OLED, a 120 mAh
LiPo under the thumb lobe, a slide power switch in the side wall, a Cirque 23 mm
trackpad (right half), and 4 magnets per half in the base so the halves stack
back-to-back (keycaps out) for your bag.

Run:  python3 case.py      -> STLs in ../print/keyboard/ (+ the switch fit strip in ../print/test-kit/)
      python3 preview.py   -> drawings in ../docs/images/diagrams/
"""
import math, os, sys
import numpy as np
from shapely.geometry import Polygon, Point, box, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from manifold3d import Manifold, CrossSection
import trimesh
import layout as L

# ======================= parameters (mm) =======================
# --- switches (Gateron KS-33 low profile) ---
HOLE      = 14.0   # plate cut-out; print the test kit (print/test-kit/) first and pick 13.8-14.1
POCKET    = 15.6   # relief under the lip so the switch clips can spring out
LIP       = 1.2    # KS-33 clips are made for a 1.2 mm plate
PLATE_T   = 2.0    # printed plate (1.2 lip + 0.8 stiffening)
CAVITY    = 4.7    # 7.7 mm total: 5.5 mm under the plate lip for KS-33 + diodes + 30 AWG silicone wire
# --- shell / base ---
WALL      = 2.0
MARGIN    = 1.0    # keycap edge -> inner wall
BOTTOM_T  = 1.0
EDGE_CH   = 1.0    # rounded top edge (radius)
BASE_CH   = 0.5    # rounded bottom edge of the base (radius): it reads thinner than it is
SMOOTH    = 6.0    # fills notches in the outline
# --- screws: M2 countersunk (DIN 965) into M2 x 4 mm heat-set brass inserts ---
INSERT_HOLE  = 3.0   # set to your insert's outer diameter - 0.2 (measure it; knurled M2 x 4 are 3.2-3.5)
INSERT_DEPTH = 4.7   # 4 mm insert seated 0.3 mm deep (room for the screw head's tip) + 0.4 for melt
BOSS_D, SCREW_CLR, SCREW_HEAD = 5.4, 2.3, 3.9   # DIN 965 M2 head is 3.8
SCREW_PILOT = INSERT_HOLE   # (drawings)
N_SCREWS  = 7
# --- electronics ---
MCU_W, MCU_L   = 18.4, 33.4   # SuperMini nRF52840 (18 x 33) + clearance
USB_SETBACK    = 0.8          # board edge -> back wall: the USB-C front is about flush with the board edge (checked on photos)
BATT_W, BATT_L = 8.8, 39.8    # WLY450838 LiPo (4.5 x 8 x 38, 120 mAh, Robu, in stock): fits up to 39.3 mm incl. its protection board
BATT_T         = 4.5
BATT_RECESS    = 0.5          # the battery sits in a 0.5 mm dip in the base (0.5 mm floor under it)
OLED_W, OLED_L = 12.4, 38.4   # 0.91" SSD1306 128x32 module PCB + clearance
GLASS_W, GLASS_L, GLASS_T = 12.0, 30.6, 1.6
OLED_PCB_T     = 1.2          # Robu 0.91" module (ER-OLEDM0.91 datasheet): PCB 38 x 12 x 1.2, glass 30 x 11.5
OLED_OFFSET    = 9.5          # back wall -> top of OLED module (clears the USB-C receptacle under it)
GLASS_INSET    = 0.8          # module end -> glass
BEZEL_T        = PLATE_T - GLASS_T   # skin over the glass (0.4)
WIN_W, WIN_L   = 8.4, 26.0    # visible window (active area is ~5.6 x 22.4)
# --- power switch: XKB SS-12D06L4 through-hole slide switch, lying on its side against the
#     straight part of the inner side wall; its 4 mm knob sticks out 2 mm through the wall ---
SW_BODY_L = 8.9    # along the wall   (8.6 frame + clearance)
SW_BODY_D = 3.6    # along the knob   (3.5 frame + clearance)
SW_BODY_H = 3.9    # vertical         (~3.6 frame + clearance; must stay under CAVITY)
SW_KNOB_L, SW_KNOB_W, SW_TRAVEL, SW_PIN_L = 4.0, 1.5, 2.0, 2.5   # "L4" = 4 mm knob
SW_Z0 = 0.15
SW_PED = SW_Z0     # (viewer)
MCU_RAIL       = 1.0          # SuperMini rides on two rails: room for the battery wires to its B+/B- pads
USB_SLOT_W     = 11.5
# --- magnets: 4 per half in the base, 6 x 1 mm N52 discs ---
MAG_D, MAG_T   = 6.2, 1.0     # 6 x 1 mm discs glued flush into through-holes in the 1.0 mm base
N_MAGNETS      = 4
# --- Cirque GlidePoint TM023023-2024-002 (23.2 mm, SPI) ---
TP_D, TP_T     = 23.2, 0.9       # overlay + PCB
TP_LEDGE       = 0.7

U = L.U
H = CAVITY + PLATE_T                  # shell height
# ======================= where files go =======================
ROOT       = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KB_DIR     = os.path.join(ROOT, "print", "keyboard")      # shells + bases
CARRY_DIR  = os.path.join(ROOT, "print", "carry-case")    # carry case + bumper
TEST_DIR   = os.path.join(ROOT, "print", "test-kit")      # fit tests
CAPS_DIR   = os.path.join(ROOT, "print", "keycaps")       # CLP keycap print package
STEP_DIR   = os.path.join(ROOT, "cad")                    # STEP solids
DOCS_DIR   = os.path.join(ROOT, "docs")
IMG_DIR    = os.path.join(DOCS_DIR, "images", "diagrams") # drawings
VIEWER_DIR = os.path.join(ROOT, "viewer")
for _d in (KB_DIR, CARRY_DIR, TEST_DIR, CAPS_DIR, STEP_DIR, IMG_DIR):
    os.makedirs(_d, exist_ok=True)
keys = L.all_keys()

# ======================= electronics bay =======================
col5_top  = L.COL_STAGGER[5] * U + U / 2
inner_top = col5_top + MARGIN                  # inside face of the back wall in the bay
bay_x0    = 5 * U + U / 2 + MARGIN
# Original look, slimmest stack:
#   the OLED window, USB-C port, outline and trackpad stay exactly where they were;
#   the SuperMini rides on 1 mm rails directly under the OLED (nothing stacked on it),
#   and the battery moves to the open floor of the bay below the board.
BAY_W     = 23.0
bay_x1    = bay_x0 + BAY_W
mcu_cx    = bay_x0 + 11.0
oled_cx   = mcu_cx
BAY_BOTTOM = -40.0
BAY       = box(bay_x0, BAY_BOTTOM, bay_x1, inner_top)

mcu_top   = inner_top - USB_SETBACK
MCU_RECT  = box(mcu_cx - MCU_W/2, mcu_top - MCU_L, mcu_cx + MCU_W/2, mcu_top)
oled_top  = inner_top - OLED_OFFSET
OLED_RECT = box(oled_cx - OLED_W/2, oled_top - OLED_L, oled_cx + OLED_W/2, oled_top)
glass_top = oled_top - GLASS_INSET
GLASS_RECT = box(oled_cx - GLASS_W/2, glass_top - GLASS_L, oled_cx + GLASS_W/2, glass_top)
gcy       = glass_top - GLASS_L / 2
WIN_RECT  = box(oled_cx - WIN_W/2, gcy - WIN_L/2, oled_cx + WIN_W/2, gcy + WIN_L/2)

# ======================= 2D outlines =======================
caps  = unary_union([Polygon(L.key_rect(k, U, U)) for k in keys])
# Bay blends into the big thumb key so the inner edge runs straight, then follows the thumb.
thumb_big = Polygon(L.key_rect(keys[-1], U, U)).buffer(MARGIN, join_style=2)
bay_blend = unary_union([BAY, thumb_big]).convex_hull   # compact: lobe stays a round bump
core = unary_union([caps.buffer(MARGIN, join_style=2), BAY, bay_blend])
TP_CENTER = (131.5, -44.5)
TP_DISC   = Point(*TP_CENTER).buffer(TP_D / 2 + 0.2, 128)
tp_lobe   = Point(*TP_CENTER).buffer(TP_D / 2 + 1.4, 128)
inner = unary_union([core, tp_lobe])
inner = inner.buffer(SMOOTH, join_style=1).buffer(-SMOOTH, join_style=1)
inner = inner.buffer(-2, join_style=1).buffer(2, join_style=1)
outer = inner.buffer(WALL, join_style=1)

# Battery: a long thin cell under the thumb/trackpad lobe (4.8 mm free under the pad's back).
# Kept off the OLED board entirely (its board hangs to 3.7 mm). Searched: clear of the switch housings (+ wiring room), the SuperMini and
# the power switch's spot under it, inside the outline as designed (it never bulges).
import shapely as _shp
from shapely import affinity as _aff
_sw_keep = unary_union([Polygon(L.rect(k[0], k[1], 14.6 + 1.0, 14.6 + 1.0, k[2])) for k in keys])   # housing + 0.5 for wires
_pswitch = box(bay_x1 - SW_BODY_D - SW_PIN_L - 2.5, MCU_RECT.bounds[1] - 0.6 - SW_BODY_L - 1.0, inner.bounds[2] + 5, MCU_RECT.bounds[1])
_free = inner.buffer(-0.4).difference(unary_union([_sw_keep, MCU_RECT.buffer(0.6), OLED_RECT.buffer(0.6), _pswitch]))   # OLED board hangs low under the plate
_shp.prepare(_free)
_best = None
_core = _free.buffer(-BATT_W / 2 + 0.05); _shp.prepare(_core)        # candidate centres only
_X, _Y = np.meshgrid(np.arange(TP_CENTER[0] - 30, TP_CENTER[0] + 10, 0.5), np.arange(TP_CENTER[1] - 25, TP_CENTER[1] + 25, 0.5))
_ok = _shp.contains_xy(_core, _X, _Y)
for _ang in np.arange(0, 180, 2.5):
    _r0 = _aff.rotate(box(-BATT_W / 2, -BATT_L / 2, BATT_W / 2, BATT_L / 2), _ang, origin=(0, 0))
    for _x, _y in zip(_X[_ok], _Y[_ok]):
        _r = _aff.translate(_r0, _x, _y)
        if _free.contains(_r):
            _score = (0.0, Point(_x, _y).distance(Point(*TP_CENTER)))
            if _best is None or _score < _best[0]:
                _best = (_score, _r, float(_ang), (float(_x), float(_y)))
BATT_RECT, BATT_ANG, BATT_C = _best[1], _best[2], _best[3]
if False:                                             # (outline is never re-shaped: re-smoothing made the lobe lumpy)
    inner = unary_union([inner, BATT_RECT.buffer(0.4, join_style=2)])
    inner = inner.buffer(SMOOTH, join_style=1).buffer(-SMOOTH, join_style=1)
    inner = inner.buffer(-2, join_style=1).buffer(2, join_style=1)
    outer = inner.buffer(WALL, join_style=1)
def _x_at(poly, y):
    seg = LineString([(bay_x0, y), (bay_x1 + 30, y)]).intersection(poly)
    return max(c[0] for g in getattr(seg, "geoms", [seg]) for c in g.coords)

# Power switch: just below the SuperMini, body pressed against the inner side wall (the wall is
# straight there). Slide down until body and pins clear the battery, trackpad and OLED.
_tp_keep = Point(*TP_CENTER).buffer(TP_D / 2 + 0.5)
SW_YC = MCU_RECT.bounds[1] - 0.6 - SW_BODY_L / 2
while True:
    ys = np.linspace(SW_YC - SW_BODY_L / 2, SW_YC + SW_BODY_L / 2, 9)
    SW_FACE = min(_x_at(inner, y) for y in ys)         # body touches the wall's inside face
    SW_XOUT = _x_at(outer, SW_YC)                      # outside face at the knob
    SW_RECT = box(SW_FACE - SW_BODY_D, SW_YC - SW_BODY_L / 2, SW_FACE, SW_YC + SW_BODY_L / 2)
    _pins = box(SW_FACE - SW_BODY_D - SW_PIN_L, SW_YC - 2.6, SW_FACE - SW_BODY_D, SW_YC + 2.6)
    if (not SW_RECT.intersects(_tp_keep) and not SW_RECT.intersects(OLED_RECT)
            and not unary_union([SW_RECT, _pins]).intersects(BATT_RECT.buffer(0.4))
            and SW_FACE <= min(_x_at(inner, y) for y in ys)):
        break
    SW_YC -= 0.5
SW_ZC = SW_Z0 + SW_BODY_H / 2
sw_cx, sw_cy = SW_RECT.centroid.x, SW_RECT.centroid.y

holes   = [Polygon(L.rect(k[0], k[1], HOLE, HOLE, k[2])) for k in keys]
pockets = [Polygon(L.rect(k[0], k[1], POCKET, POCKET, k[2])) for k in keys]

# Keycap travel: a CLP cap's skirt sits 2.45 mm over the plate and the KS-33 travels 3.2 mm, so the
# plate top drops CAP_RECESS under every cap. Each switch keeps a raised ISLAND (its 15 mm flange sits
# on it; the 15.6 clip relief is underneath), and the skirt (16.2 mm inside) moves down round it.
CAP_RECESS = 0.0              # 0: not needed with the KS-33 CLP caps (they ride 2.1 mm higher); 1.0 for stock low caps
ISLAND     = 15.6
CAP_FOOT   = (18.0, 27.5)     # CLP 1u / 1.5u
_capr = unary_union([Polygon(L.rect(k[0], k[1], CAP_FOOT[0] + 0.6, (CAP_FOOT[1] if k[3] > 1 else CAP_FOOT[0]) + 0.6, k[2]))
                     for k in keys])
_capr = _capr.buffer(0.6, join_style=2).buffer(-0.6, join_style=2)          # no thin ridges between caps
ISLANDS = unary_union([Polygon(L.rect(k[0], k[1], ISLAND, ISLAND, k[2])) for k in keys])
CAP_RECESS_POLY = _capr.difference(ISLANDS).intersection(inner.buffer(-0.6, join_style=1))

# ======================= screw bosses =======================
# Each insert needs ~1 mm of plastic all round. Bosses may run into the outer wall and are
# trimmed around switch bodies, so screws can sit in the rim around the keys, not only in
# open corners. Constraints are on the insert hole itself:
SW_BODY = unary_union([Polygon(L.rect(k[0], k[1], 14.6, 14.6, k[2])) for k in keys])
_hole_r = INSERT_HOLE / 2
_bad = unary_union([SW_BODY.buffer(_hole_r + 1.0),                       # wall to switch body
                    unary_union(pockets).buffer(_hole_r + 0.6),          # wall to clip relief (top 0.5 mm only)
                    unary_union([r.buffer(BOSS_D / 2 + 0.5) for r in (MCU_RECT, BATT_RECT, OLED_RECT, SW_RECT, TP_DISC)])])
_fits = outer.buffer(-(SCREW_HEAD / 2 + BASE_CH + 0.2))                   # countersink clear of the bottom bevel
allowed = _fits.difference(_bad)
minx, miny, maxx, maxy = allowed.bounds
cands = [Point(x, y) for x in np.arange(minx, maxx, 0.25) for y in np.arange(miny, maxy, 0.25)
         if allowed.contains(Point(x, y))]
c = outer.centroid
bosses = [max(cands, key=lambda p: p.distance(c))]
while len(bosses) < N_SCREWS:
    bosses.append(max(cands, key=lambda p: min(p.distance(b) for b in bosses)))
BOSSES = [(round(b.x, 2), round(b.y, 2)) for b in bosses]

# Slim posts where four keys meet on the (unstaggered) pinky columns, so the base is
# clamped on that side too. They clear the 14 mm switch housings by 0.3 mm.
POST_D = 4.4
_housing = unary_union([Polygon(L.rect(k[0], k[1], 14.0, 14.0, k[2])) for k in keys])
POSTS = []
# (no posts between keys: a heat-set insert needs more wall than the gap between switches has)
SCREWS = BOSSES + POSTS

# Magnets: spread out, clear of screws, electronics and switch bodies (both halves use
# the same local spots, so flipping one half onto the other lines them up).
# Switch pins and diodes sit near each key's centre; corners between keys are free
# down at base level, so magnets may go there.
pin_zone = [Polygon(L.rect(k[0], k[1], 10.0, 10.0, k[2])) for k in keys]
mag_keep = unary_union([p.buffer(MAG_D/2 + 1.2) for p in pin_zone]
                       + [r.buffer(MAG_D/2 + 1.0) for r in (BATT_RECT, MCU_RECT, SW_RECT, TP_DISC)]
                       + [Point(b).buffer(BOSS_D/2 + MAG_D/2 + 1.0) for b in BOSSES + POSTS])
mag_ok = inner.buffer(-(MAG_D/2 + 0.6)).difference(mag_keep)
mx0, my0, mx1, my1 = mag_ok.bounds
mc = [Point(x, y) for x in np.arange(mx0, mx1, 0.5) for y in np.arange(my0, my1, 0.5)
      if mag_ok.contains(Point(x, y))]
mag = [min(mc, key=lambda p: (p.x, -p.y))]
while len(mag) < N_MAGNETS:
    mag.append(max(mc, key=lambda p: min(p.distance(m) for m in mag)))
MAGNETS = [(round(m.x, 2), round(m.y, 2)) for m in mag]

# Rescue reset: a 3 x 6 x 2.5 mm 2-pin tact switch lies face-down on the base (wired RST <-> GND);
# a paperclip through a 1.4 mm pinhole presses it. Double-press = UF2 bootloader, even if the
# firmware is broken. Spot: open floor near the SuperMini, clear of everything.
RST_W, RST_L, RST_H = 3.6, 6.4, 2.6     # switch + clearance (body 3 x 6, 2.5 tall)
RST_PIN_D, RST_WALL, RST_WALL_H = 1.4, 0.8, 1.6
_rst_keep = unary_union([BATT_RECT.buffer(1.0), MCU_RECT.buffer(0.8), SW_RECT.buffer(1.0), _pins.buffer(0.6), _sw_keep]
                        + [Point(b).buffer(BOSS_D / 2 + 1.0) for b in BOSSES]
                        + [Point(m).buffer(MAG_D / 2 + 1.0) for m in MAGNETS])
_rst_ok = inner.buffer(-1.0).difference(_rst_keep)
_rst_best = None
for _ang in (0.0, 90.0):
    _r0 = _aff.rotate(box(-RST_W / 2 - RST_WALL, -RST_L / 2 - 2.0, RST_W / 2 + RST_WALL, RST_L / 2 + 2.0), _ang, origin=(0, 0))  # + legs and wires
    for _x in np.arange(mcu_cx - 25, mcu_cx + 25, 0.5):
        for _y in np.arange(MCU_RECT.bounds[1] - 30, MCU_RECT.bounds[3], 0.5):
            if _rst_ok.contains(_aff.translate(_r0, _x, _y)):
                _d = Point(_x, _y).distance(Point(mcu_cx, MCU_RECT.bounds[1]))
                if _rst_best is None or _d < _rst_best[0]:
                    _rst_best = (_d, _x, _y, _ang)
RST_C, RST_ANG = (round(float(_rst_best[1]), 2), round(float(_rst_best[2]), 2)), _rst_best[3]
RST_RECT = _aff.translate(_aff.rotate(box(-RST_W / 2, -RST_L / 2, RST_W / 2, RST_L / 2), RST_ANG, origin=(0, 0)), *RST_C)
_rw = _aff.rotate(unary_union([box(-RST_W / 2 - RST_WALL, -RST_L / 2 + 0.8, -RST_W / 2, RST_L / 2 - 0.8),
                               box(RST_W / 2, -RST_L / 2 + 0.8, RST_W / 2 + RST_WALL, RST_L / 2 - 0.8)]), RST_ANG, origin=(0, 0))
RST_CRADLE = _aff.translate(_rw, *RST_C)    # two side walls; the ends stay open for the legs

# ======================= helpers =======================
def xs(poly):
    """shapely (Multi)Polygon, holes allowed -> manifold CrossSection"""
    contours = []
    for p in getattr(poly, "geoms", [poly]):
        p = orient(p, 1)
        contours.append(list(p.exterior.coords)[:-1])
        contours += [list(r.coords)[:-1] for r in p.interiors]
    return CrossSection(contours)

def prism(poly, z0, z1):
    return xs(poly).extrude(z1 - z0).translate([0, 0, z0])

def cyl(x, y, d, z0, z1, d2=None, seg=48):
    return Manifold.cylinder(z1 - z0, d/2, (d2 or d)/2, seg).translate([x, y, z0])

def chamfered_prism(poly, z0, z1, top_ch=0.0, bot_ch=0.0, steps=4):
    body = prism(poly, z0 + bot_ch, z1 - top_ch)
    for i in range(steps):
        f = (i + 0.5) / steps
        if top_ch:
            zz = z1 - top_ch + top_ch * i / steps
            body += prism(poly.buffer(-top_ch * f, join_style=1), zz, zz + top_ch / steps)
        if bot_ch:
            zz = z0 + bot_ch * i / steps
            body += prism(poly.buffer(-bot_ch * (1 - f), join_style=1), zz, zz + bot_ch / steps)
    return body

def rounded_prism(poly, z0, z1, top_r=0.0, bot_r=0.0, steps=6):
    """prism with quarter-round edges, built from thin offset layers (prints as a smooth fillet)"""
    body = prism(poly, z0 + bot_r, z1 - top_r)
    for i in range(steps):
        t = (i + 0.5) / steps
        if top_r:
            inset = top_r - math.sqrt(max(top_r ** 2 - (top_r * t) ** 2, 0))
            zz = z1 - top_r + top_r * i / steps
            body += prism(poly.buffer(-inset, join_style=1), zz, zz + top_r / steps)
        if bot_r:
            inset = bot_r - math.sqrt(max(bot_r ** 2 - (bot_r * (1 - t)) ** 2, 0))
            zz = z0 + bot_r * i / steps
            body += prism(poly.buffer(-inset, join_style=1), zz, zz + bot_r / steps)
    return body

def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts))

# ======================= shell =======================
shell = rounded_prism(outer, 0, H, top_r=EDGE_CH, steps=8) - prism(inner, -1, CAVITY)

for h in holes:
    shell -= prism(h, CAVITY - 1, H + 1)
for p in pockets:
    shell -= prism(p, CAVITY - 1, H - LIP)

# keycap travel recess round every switch island (off by default)
if CAP_RECESS > 0:
    shell -= prism(CAP_RECESS_POLY, H - CAP_RECESS, H + 1)

# OLED: glass sits up against a 0.6 mm bezel, window shows the active area.
shell -= prism(GLASS_RECT.buffer(0.15, join_style=2), CAVITY - 1, H - BEZEL_T)
for i in range(3):   # small stepped chamfer around the window
    g = 0.25 * (i + 1)
    shell -= prism(WIN_RECT.buffer(g * 0.8, join_style=1), H - BEZEL_T + BEZEL_T * i / 3, H + 1)
shell -= prism(WIN_RECT.buffer(0.0, join_style=1), H - BEZEL_T - 1, H + 1)

# Screw bosses (edge) and posts (between keys); re-cut the clip pockets over the posts
for (x, y) in BOSSES:
    boss = (cyl(x, y, BOSS_D, 0, CAVITY + 0.1) ^ prism(outer.buffer(-0.01), -1, H)) - prism(SW_BODY.buffer(0.15), -1, H)
    shell = shell + boss - cyl(x, y, INSERT_HOLE, -1, INSERT_DEPTH)
for (x, y) in POSTS:
    shell = shell + cyl(x, y, POST_D, 0, CAVITY + 0.1) - cyl(x, y, INSERT_HOLE, -1, INSERT_DEPTH)
for p in pockets:
    shell -= prism(p, CAVITY, H - LIP)

# USB-C slot: open at the top so any cable's plug fits. Rounded bottom.
usb_z = MCU_RAIL + 1.0 + 1.6            # rails + board + half the receptacle
slot_bottom = usb_z - 3.4
usb_slot = box(mcu_cx - USB_SLOT_W/2, inner_top - 3, mcu_cx + USB_SLOT_W/2, inner_top + WALL + 3)
shell -= prism(usb_slot, slot_bottom + 2.0, H + 1)
shell -= (Manifold.cylinder(WALL + 6, 2.0, 2.0, 32).rotate([-90, 0, 0])
          .translate([0, inner_top - 3, 0]).scale([USB_SLOT_W / 4.0, 1, 1])
          .translate([mcu_cx, 0, slot_bottom + 2.0]))

# Trackpad (right half only): pad drops in from the top onto a thin ledge.

# Pocket under the plate over the USB-C receptacle (it stands 3.2 mm off the board)
USB_TOP = MCU_RAIL + 1.0 + 3.2
if USB_TOP + 0.3 > CAVITY:          # only needed when the cavity is shallower than the USB-C stack
    shell -= prism(box(mcu_cx - 4.9, mcu_top - 8.0, mcu_cx + 4.9, inner_top + 0.1), CAVITY - 1, USB_TOP + 0.3)
# Power switch: knob slot through the side wall, and one small ON bar above its north end
_kh = SW_KNOB_W / 2 + 0.25
SW_SLOT_Y = SW_TRAVEL / 2 + _kh
shell -= prism(box(SW_FACE - 0.5, SW_YC - SW_SLOT_Y, SW_XOUT + 6, SW_YC + SW_SLOT_Y), SW_ZC - _kh, SW_ZC + _kh)
SW_MARK_Y = SW_YC + 2.4
SW_MARK_X = _x_at(outer, SW_MARK_Y)
SW_MARK_Z = SW_ZC + 2.4
shell -= prism(box(SW_MARK_X - 0.3, SW_MARK_Y - 0.35, SW_MARK_X + 1, SW_MARK_Y + 0.35),
               SW_MARK_Z - 0.9, SW_MARK_Z + 0.9)                                        # ON: bar

shell_tp = shell - prism(TP_DISC, H - TP_T, H + 1) - prism(Point(*TP_CENTER).buffer(TP_D/2 - TP_LEDGE, 128), CAVITY - 1, H)

# ======================= bottom plate =======================
bottom = rounded_prism(outer, -BOTTOM_T, 0, bot_r=BASE_CH, steps=4)
for (x, y) in SCREWS:
    bottom -= cyl(x, y, SCREW_CLR, -BOTTOM_T - 1, 1)
    bottom -= cyl(x, y, SCREW_HEAD, -BOTTOM_T - 0.01, -BOTTOM_T + 1.0, d2=SCREW_CLR)
# Power switch cradle: end walls take the push of the knob, corner stubs hold the back
_x0, _y0, _x1, _y1 = SW_RECT.bounds
SW_CRADLE = unary_union([box(_x0 - 1.0, _y1, _x1, _y1 + 1.0), box(_x0 - 1.0, _y0 - 1.0, _x1, _y0),
                         box(_x0 - 1.0, _y1 - 1.0, _x0, _y1), box(_x0 - 1.0, _y0, _x0, _y0 + 1.0)])
bottom += prism(SW_CRADLE, 0, 1.8)
# SuperMini rails along its long edges (USB end left open)
for side in (-1, 1):
    rx = mcu_cx + side * (MCU_W / 2 - 1.4)
    bottom += prism(box(rx - 0.6, mcu_top - MCU_L + 1.5, rx + 0.6, mcu_top - 9.0), 0, MCU_RAIL)
# Rescue reset: cradle walls + pinhole
bottom += prism(RST_CRADLE, 0, RST_WALL_H)
bottom -= cyl(RST_C[0], RST_C[1], RST_PIN_D, -BOTTOM_T - 1, 1)
bottom -= cyl(RST_C[0], RST_C[1], RST_PIN_D + 1.6, -BOTTOM_T - 0.01, -BOTTOM_T + 0.5, d2=RST_PIN_D)   # funnel for the pin
# Battery dip: the cell sits 0.5 mm into the base
bottom -= prism(BATT_RECT.buffer(0.3, join_style=2), -BATT_RECESS, 0.01)
# Magnet pockets: raised pad inside, pocket opens on the bottom face (sits flush)
for (x, y) in MAGNETS:
    bottom -= cyl(x, y, MAG_D, -BOTTOM_T - 0.01, 0.01)
# Finishing details: finger dip at the switch, ON arrow, feet pockets (engraving is per side)
import details as _DT
DETAILS = _DT.base_details(sys.modules[__name__])
bottom -= prism(DETAILS["foot_pockets"], -BOTTOM_T - 1, -BOTTOM_T + _DT.FOOT_DEPTH)
bottom_left = bottom - prism(DETAILS["text_left"], -BOTTOM_T - 1, -BOTTOM_T + _DT.TEXT_DEPTH)
bottom_right_frame = bottom - prism(DETAILS["text_right"], -BOTTOM_T - 1, -BOTTOM_T + _DT.TEXT_DEPTH)

# ======================= fit test =======================
# A strip of 4 switch holes with a skirt as deep as the case's cavity: if a clicked-in switch,
# with its pins trimmed, sits without touching the table, it fits in the case.
test = prism(box(0, 0, 4 * 19.05, 19.05), 0, PLATE_T)
test += prism(box(0, 0, 4 * 19.05, 19.05).difference(box(1.2, 1.2, 4 * 19.05 - 1.2, 19.05 - 1.2)), -CAVITY, 0)
for i, s in enumerate((13.8, 13.9, 14.0, 14.1)):
    cx = 19.05 * (i + 0.5)
    test -= prism(box(cx - s/2, 9.525 - s/2, cx + s/2, 9.525 + s/2), -1, PLATE_T + 1)
    test -= prism(box(cx - POCKET/2, 9.525 - POCKET/2, cx + POCKET/2, 9.525 + POCKET/2), -1, PLATE_T - LIP)
    for j in range(i + 1):   # notches on the edge = which size (1 notch = 13.8)
        test -= prism(box(cx - 4 + 2.2 * j, -0.5, cx - 3 + 2.2 * j, 1.0), PLATE_T - 0.6, PLATE_T + 1)

# same keycap-travel recess as the case (when it's on)
if CAP_RECESS > 0:
  test -= prism(box(1.2, 1.2, 4 * 19.05 - 1.2, 19.05 - 1.2).difference(unary_union(
    [box(19.05 * (i + 0.5) - ISLAND / 2, 9.525 - ISLAND / 2, 19.05 * (i + 0.5) + ISLAND / 2, 9.525 + ISLAND / 2) for i in range(4)])),
    PLATE_T - CAP_RECESS, PLATE_T + 1)

# ======================= export =======================
def export(m, name, flip=False, folder=KB_DIR):
    tm = to_trimesh(m)
    if flip:
        tm.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    tm.apply_translation(-tm.bounds[0])
    tm.export(os.path.join(folder, f"{name}.stl"))
    print(f"{name:16s} {m.status().name:8s} {m.volume()/1000:5.1f} cm3  "
          f"{tm.extents[0]:.1f} x {tm.extents[1]:.1f} x {tm.extents[2]:.1f} mm")

if __name__ == "__main__":
    export(shell, "shell_left", flip=True)
    export(shell_tp.mirror([1, 0, 0]), "shell_right", flip=True)
    export(bottom_left, "bottom_left")
    export(bottom_right_frame.mirror([1, 0, 0]), "bottom_right")
    print("feet A (left):", DETAILS["feet_A"], " feet B (right):", DETAILS["feet_B"])
    export(test, "1_switch_strip", flip=True, folder=TEST_DIR)
    b = outer.bounds
    print(f"half: {b[2]-b[0]:.1f} x {b[3]-b[1]:.1f} mm, total height {H + BOTTOM_T:.1f} mm (no keycaps)")
    print("bosses:", BOSSES, "posts:", POSTS)
    print("magnets:", MAGNETS)
    print("reset pinhole:", RST_C, "switch turned", RST_ANG)

GEOM = dict(outer=outer, inner=inner, holes=holes, bosses=BOSSES, keys=keys,
            mcu=MCU_RECT, batt=BATT_RECT, oled=OLED_RECT, glass=GLASS_RECT, win=WIN_RECT,
            sw=SW_RECT, magnets=MAGNETS, tp=TP_DISC, bay_x1=bay_x1, usb=usb_slot, H=H, tp_center=TP_CENTER, usb_top=USB_TOP, posts=POSTS)

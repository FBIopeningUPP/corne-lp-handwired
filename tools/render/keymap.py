"""Draw the keymap as an SVG for the README, to scale, from the real layout.

    python3 keymap.py   -> ../../docs/images/keymap.svg

Key positions and the case outline come from viewer/data.js (made by case/viewer_data.py),
legends from zmk-config/config/corne_lp.keymap. Each key shows its BASE legend in the middle,
NUM bottom-left (blue) and SYM bottom-right (orange); ADJ is listed underneath.
"""
import json
import math
import os
import re
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "docs", "images", "keymap.svg")

D = json.loads(re.sub(r"^window\.CORNE = ", "", open(os.path.join(ROOT, "viewer", "data.js")).read().strip()).rstrip(";"))
KEYMAP = open(os.path.join(ROOT, "zmk-config", "config", "corne_lp.keymap")).read()

LABEL = {
    "TAB": "Tab", "BSPC": "⌫", "LCTRL": "Ctrl", "LSHFT": "Shift", "SEMI": ";", "SQT": "'", "COMMA": ",", "DOT": ".",
    "FSLH": "/", "ESC": "Esc", "LGUI": "Gui", "SPACE": "Space", "RET": "Enter", "RALT": "Alt",
    "LEFT": "←", "DOWN": "↓", "UP": "↑", "RIGHT": "→", "HOME": "Home", "END": "End", "PG_UP": "PgUp", "PG_DN": "PgDn",
    "C_PREV": "⏮", "C_PP": "⏯", "C_NEXT": "⏭", "C_VOL_DN": "Vol−", "C_VOL_UP": "Vol+", "C_MUTE": "Mute",
    "EXCL": "!", "AT": "@", "HASH": "#", "DOLLAR": "$", "PRCNT": "%", "CARET": "^", "AMPS": "&", "ASTRK": "*",
    "LPAR": "(", "RPAR": ")", "GRAVE": "`", "MINUS": "-", "EQUAL": "=", "LBKT": "[", "RBKT": "]", "BSLH": "\\",
    "TILDE": "~", "UNDER": "_", "PLUS": "+", "LBRC": "{", "RBRC": "}", "PIPE": "|",
}
LAYER_NAME = {"LOWER": "NUM", "RAISE": "SYM", "ADJ": "ADJ"}


def label(b):
    p = b.split()
    k = p[0]
    if k == "&kp":
        n = p[1]
        return LABEL.get(n, n[1:] if re.fullmatch(r"N\d", n) else n)
    if k == "&mo":
        return LAYER_NAME.get(p[1], p[1])
    if k == "&mkp":
        return {"MB1": "L-click", "MB2": "R-click", "MB3": "M-click"}[p[1]]
    if k == "&bt":
        return "BT clr" if p[1] == "BT_CLR" else f"BT {int(p[2]) + 1}"
    return {"&trans": "", "&caps_word": "Aa", "&bootloader": "Boot", "&sys_reset": "Reset", "&soft_off": "Off"}.get(k, k)


def layers():
    out = []
    for name, body in re.findall(r'display-name = "(\w+)";.*?bindings = <(.*?)>;', KEYMAP, re.S):
        body = "\n".join(l for l in body.splitlines() if not l.strip().startswith("//"))
        toks = re.findall(r"&\w+(?:\s+(?!&)[\w]+)*", body)
        assert len(toks) == 42, (name, len(toks))
        out.append((name, [label(t) for t in toks]))
    return out


def binding_index(side, row, col):
    """matrix (half, row, col with col 0 = outer pinky) -> index into a 42-key bindings list"""
    if row < 3:
        return row * 12 + (col if side == "L" else 11 - col)
    return 36 + (col - 3 if side == "L" else 8 - col)


LAYERS = layers()
BASE, NUM, SYM, ADJ = (dict(LAYERS)[n] for n in ("BASE", "NUM", "SYM", "ADJ"))

# ---------------- geometry ----------------
S = 4.2                               # px per mm
U = 19.05
CAP = 17.4
x0, y0, x1, y1 = D["outer"]
GAP = 34                              # mm between the halves
PAD = 14
HALF_W = x1 - x0
W = (2 * HALF_W + GAP + 2 * PAD) * S
H_KEYS = (y1 - y0 + 2 * PAD) * S
LEGEND_H = 120
H = H_KEYS + LEGEND_H


def to_svg(side, x, y):
    if side == "L":
        X = PAD + (x - x0)
    else:
        X = PAD + HALF_W + GAP + (x1 - x)
    return X * S, (PAD + (y1 - y)) * S


def path(side, pts):
    return "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in (to_svg(side, x, y) for x, y in pts)) + " Z"


parts = []
add = parts.append
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
    f'font-family="Inter, -apple-system, Segoe UI, Helvetica, Arial, sans-serif">')
add("""<style>
.bg{fill:#f6f3ee}.case{fill:#e4ddcf;stroke:#cfc6b4;stroke-width:2}.cap{fill:#fdfcfa;stroke:#d8d2c6;stroke-width:1.5}
.mod{fill:#2a2b30;stroke:#2a2b30}.acc{fill:#e5532a;stroke:#e5532a}.t{fill:#1d1d1f;font-weight:600;text-anchor:middle;dominant-baseline:central}
.mod+.t,.acc+.t{fill:#fff}.n{fill:#3f6b85;font-size:13px;font-weight:600}.s{fill:#c8431f;font-size:13px;font-weight:600;text-anchor:end}
.mod~.n,.mod~.s{fill:#c9cbd0}.acc~.n,.acc~.s{fill:#fff}.oled{fill:#101114}.pad{fill:#2a2b30}
.lg{font-size:17px;fill:#55555a}.lgb{font-size:17px;font-weight:700}
</style>""")
add(f'<rect class="bg" width="{W:.0f}" height="{H:.0f}" rx="28"/>')

for side in ("L", "R"):
    add(f'<path class="case" d="{path(side, D["outline"])}"/>')
    wx0, wy0, wx1, wy1 = D["win"]
    (ax, ay), (bx, by) = to_svg(side, wx0, wy1), to_svg(side, wx1, wy0)
    add(f'<rect class="oled" x="{min(ax, bx):.1f}" y="{ay:.1f}" width="{abs(bx - ax):.1f}" height="{by - ay:.1f}" rx="3"/>')
    if side == "R":
        tx, ty, td, _ = D["tp"]
        cx, cy = to_svg(side, tx, ty)
        add(f'<circle class="pad" cx="{cx:.1f}" cy="{cy:.1f}" r="{td / 2 * S:.1f}"/>')
    for kx, ky, rot, wu, row, col in D["keys"]:
        i = binding_index(side, row, col)
        base, num, sym = BASE[i], NUM[i], SYM[i]
        cx, cy = to_svg(side, kx, ky)
        a = -rot if side == "L" else rot
        w, h = CAP * S, (CAP + (wu - 1) * U) * S
        cls = "cap acc" if (row, col) in ((1, 4),) else "cap mod" if col == 0 or row == 3 else "cap"
        fs = 26 if len(base) <= 2 else 20 if len(base) <= 5 else 17
        add(f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({a:.1f})">')
        add(f'<rect class="{cls}" x="{-w / 2:.1f}" y="{-h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="11"/>')
        add(f'<text class="t" y="-6" font-size="{fs}">{escape(base)}</text>')
        if num and num != base:
            add(f'<text class="n" x="{-w / 2 + 9:.1f}" y="{h / 2 - 10:.1f}">{escape(num)}</text>')
        if sym and sym != base:
            add(f'<text class="s" x="{w / 2 - 9:.1f}" y="{h / 2 - 10:.1f}">{escape(sym)}</text>')
        add("</g>")

# legend
ly = H_KEYS + 34
add(f'<text x="{PAD * S:.0f}" y="{ly:.0f}" class="lg"><tspan class="lgb" fill="#1d1d1f">BASE</tspan> centre  ·  '
    f'<tspan class="lgb" fill="#3f6b85">NUM</tspan> bottom-left (hold NUM)  ·  '
    f'<tspan class="lgb" fill="#c8431f">SYM</tspan> bottom-right (hold SYM)  ·  tap the trackpad to click</text>')
adj = [a for a in ADJ if a]
add(f'<text x="{PAD * S:.0f}" y="{ly + 38:.0f}" class="lg"><tspan class="lgb" fill="#1d1d1f">ADJ</tspan> (hold NUM + SYM): '
    f'{escape(", ".join(dict.fromkeys(adj)))}</text>')
add("</svg>")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(parts) + "\n")
print(f"keymap.svg {W:.0f} x {H:.0f} px, layers: {', '.join(n for n, _ in LAYERS)}")

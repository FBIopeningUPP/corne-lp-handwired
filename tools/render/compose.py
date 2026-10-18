"""Turn the raw renders into the README images.

    python3 compose.py     raw/*.png -> ../../docs/images/renders/
        <shot>.jpg          each shot, 2400 px wide (small enough for GitHub, sharp on retina)
        colorways.jpg       the six cw_* tiles in a labelled 3 x 2 sheet
        turntable.gif       raw/turntable/*.png as a looping spin (optional: node render.mjs turntable)

Needs Pillow (pip install pillow).
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "images", "renders"))
os.makedirs(OUT, exist_ok=True)

COLORWAYS = [  # (raw tile, label, case filament, keycaps)
    ("cw_bone", "Bone", "Bone PLA", "chalk + ink, signal accents"),
    ("cw_graphite", "Graphite", "Graphite PLA", "ink + smoke, signal accents"),
    ("cw_sage", "Sage", "Sage PLA", "chalk + moss, mustard homing"),
    ("cw_glacier", "Glacier", "Glacier PETG", "frost + deep blue"),
    ("cw_lilac", "Lilac", "Lilac PLA", "chalk + plum, butter homing"),
    ("cw_signal", "Signal", "Signal orange PETG", "ink + chalk"),
]


def font(size, bold=False):
    for f in (("Inter-SemiBold.otf" if bold else "Inter-Regular.otf"), ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")):
        hits = glob.glob(f"/usr/share/fonts/**/{f}", recursive=True) + glob.glob(f"/Library/Fonts/{f}") + glob.glob(f"C:/Windows/Fonts/{f}")
        if hits:
            return ImageFont.truetype(hits[0], size)
    return ImageFont.load_default(size)


def save_jpg(im, name, width=2400):
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    path = os.path.join(OUT, name)
    im.convert("RGB").save(path, "JPEG", quality=87, optimize=True, progressive=True, subsampling=0)
    print(f"  {name:18s} {im.width} x {im.height}  {os.path.getsize(path) / 1024:.0f} KB")


def shots():
    for p in sorted(glob.glob(os.path.join(RAW, "*.png"))):
        name = os.path.splitext(os.path.basename(p))[0]
        if not name.startswith("cw_"):
            save_jpg(Image.open(p), name + ".jpg")


def colorways():
    tiles = [(Image.open(os.path.join(RAW, t + ".png")), lab, case, caps) for t, lab, case, caps in COLORWAYS
             if os.path.exists(os.path.join(RAW, t + ".png"))]
    if len(tiles) != len(COLORWAYS):
        print("  colorways.jpg     skipped (render the cw_* shots first)")
        return
    W, H, COLS = 800, 450, 3
    sheet = Image.new("RGB", (W * COLS, H * 2), "#e9e6e0")
    d = ImageDraw.Draw(sheet)
    f1, f2 = font(30, bold=True), font(19)
    for i, (im, lab, case, caps) in enumerate(tiles):
        x, y = (i % COLS) * W, (i // COLS) * H
        sheet.paste(im.resize((W, H), Image.LANCZOS), (x, y))
        d.text((x + 28, y + 24), lab, font=f1, fill="#1d1d1f")
        d.text((x + 28, y + 62), f"{case} · {caps}", font=f2, fill="#55555a")
    for c in range(1, COLS):                       # hairlines between tiles
        d.line([(c * W, 0), (c * W, 2 * H)], fill="#d6d2ca", width=2)
    d.line([(0, H), (COLS * W, H)], fill="#d6d2ca", width=2)
    save_jpg(sheet, "colorways.jpg")


def turntable(width=720, ms=70):
    frames = sorted(glob.glob(os.path.join(RAW, "turntable", "*.png")))
    if not frames:
        print("  turntable.gif     skipped (render the turntable shot first)")
        return
    ims = [Image.open(f).convert("RGB") for f in frames]
    ims = [im.resize((width, round(im.height * width / im.width)), Image.LANCZOS) for im in ims]
    # one shared palette for every frame: no flicker, smaller file
    strip = Image.new("RGB", (ims[0].width, ims[0].height * 4))
    for k, im in enumerate(ims[:: max(1, len(ims) // 4)][:4]):
        strip.paste(im, (0, k * ims[0].height))
    pal = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG) for im in ims]
    path = os.path.join(OUT, "turntable.gif")
    q[0].save(path, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True, disposal=1)
    print(f"  turntable.gif      {ims[0].width} x {ims[0].height}, {len(q)} frames  {os.path.getsize(path) / 1024:.0f} KB")


INK, BONE, SIGNAL, MUTED = "#f3efe7", "#e4ddcf", "#e5532a", "#9b9a97"


def content_box(im, thresh=70):
    """bounding box of the (bright) keyboard on the dark hero render"""
    g = im.convert("L").point(lambda v: 255 if v > thresh else 0)
    return g.getbbox()


def banner(width=2400):
    """the README header: hero render with the name and tagline set above the keyboard"""
    src = os.path.join(RAW, "hero.png")
    if not os.path.exists(src):
        print("  banner.jpg        skipped (render the hero shot first)")
        return
    im = Image.open(src).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = content_box(im)
    text_h = round(H * 0.30)
    top = max(0, y0 - text_h)
    crop = im.crop((0, top, W, min(H, y1 + round(H * 0.05))))
    if y0 - text_h < 0:                       # not enough sky above the keyboard: extend it
        pad = crop.crop((0, 0, W, 1)).resize((W, text_h - y0))     # stretch the top row: keeps the vignette
        full = Image.new("RGB", (W, pad.height + crop.height)); full.paste(pad, (0, 0)); full.paste(crop, (0, pad.height)); crop = full
    d = ImageDraw.Draw(crop)
    s = W / 3200
    title, sub = font(round(176 * s), bold=True), font(round(54 * s))
    chip = font(round(36 * s), bold=True)
    cx = W // 2
    y = round(text_h * 0.22)
    d.text((cx, y), "Corne LP", font=title, fill=INK, anchor="mt")
    y += round(214 * s)
    d.text((cx, y), "Handwired · wireless · 7.7 mm thin · a robot on each screen", font=sub, fill=MUTED, anchor="mt")
    # spec chips
    chips = ["42 KEYS", "ZMK", "nRF52840", "KS-33 LOW PROFILE", "CIRQUE TRACKPAD"]
    pad_x, gap, ch = round(28 * s), round(18 * s), round(70 * s)
    widths = [d.textlength(c, font=chip) + 2 * pad_x for c in chips]
    x = cx - (sum(widths) + gap * (len(chips) - 1)) / 2
    y += round(110 * s)
    for c, w in zip(chips, widths):
        acc = c == "42 KEYS"
        d.rounded_rectangle((x, y, x + w, y + ch), radius=ch // 2, fill=SIGNAL if acc else None,
                            outline=SIGNAL if acc else "#4a4b50", width=max(2, round(3 * s)))
        d.text((x + w / 2, y + ch / 2), c, font=chip, fill="#ffffff" if acc else BONE, anchor="mm")
        x += w + gap
    save_jpg(crop, "banner.jpg", width)


def stats(width=2400):
    """a strip of big numbers for the README"""
    items = [("7.7", "mm", "table to plate"), ("42", "keys", "Corne 3×6 + 3"), ("~4", "days", "per charge"),
             ("0", "PCBs", "wired by hand"), ("2", "robots", "one per OLED")]
    W, H = 2400, 360
    im = Image.new("RGB", (W, H), "#141518")
    d = ImageDraw.Draw(im)
    big, unit, lab = font(150, bold=True), font(46, bold=True), font(34)
    cw = W / len(items)
    for i, (n, u, l) in enumerate(items):
        cx = cw * i + cw / 2
        nw, uw = d.textlength(n, font=big), d.textlength(" " + u, font=unit)
        x = cx - (nw + uw) / 2
        d.text((x, 190), n, font=big, fill=SIGNAL if i == 0 else INK, anchor="ls")
        d.text((x + nw, 190), " " + u, font=unit, fill=BONE, anchor="ls")
        d.text((cx, 262), l, font=lab, fill=MUTED, anchor="mt")
        if i:
            d.line([(cw * i, 80), (cw * i, H - 80)], fill="#2b2c31", width=2)
    path = os.path.join(OUT, "stats.png")
    im.save(path, optimize=True)
    print(f"  stats.png          {W} x {H}  {os.path.getsize(path) / 1024:.0f} KB")


if __name__ == "__main__":
    print("->", os.path.relpath(OUT))
    shots()
    banner()
    stats()
    colorways()
    turntable()

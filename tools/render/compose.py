"""Turn the raw renders into the README images.

    python3 compose.py     raw/*.png -> ../../docs/images/renders/
        <shot>.jpg          each shot, 2400 px wide (small enough for GitHub, sharp on retina)
        colorways.jpg       the six cw_* tiles in a labelled 3 x 2 sheet
        turntable.gif       raw/turntable/*.png as a looping spin

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


if __name__ == "__main__":
    print("->", os.path.relpath(OUT))
    shots()
    colorways()
    turntable()

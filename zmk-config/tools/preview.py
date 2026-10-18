"""Turn tools/sim output into an animated GIF that looks like the two OLEDs.

    cc -O2 -Isrc tools/sim.c src/ui_core.c -o /tmp/sim && /tmp/sim > /tmp/frames.bin
    python3 tools/preview.py /tmp/frames.bin oled_preview.gif
"""
import sys
from PIL import Image, ImageDraw

W, H, S = 32, 128, 4          # portrait size, pixel scale
src, dst = sys.argv[1], sys.argv[2]
data = open(src, "rb").read()
fsz = W * H // 8
n = len(data) // (2 * fsz)

LIT, OFF, BEZEL, CASE = (226, 246, 255), (8, 10, 14), (24, 24, 28), (231, 226, 216)

def panel(buf):
    im = Image.new("RGB", (W * S, H * S), OFF)
    d = ImageDraw.Draw(im)
    for y in range(H):
        for x in range(W):
            if buf[y * 4 + x // 8] & (0x80 >> (x % 8)):
                d.rectangle([x * S, y * S, x * S + S - 2, y * S + S - 2], fill=LIT)
    return im

frames = []
pad, gap = 22, 40
for i in range(0, n, 1):
    left = data[(2 * i) * fsz:(2 * i + 1) * fsz]
    right = data[(2 * i + 1) * fsz:(2 * i + 2) * fsz]
    canvas = Image.new("RGB", (2 * W * S + 2 * pad * 2 + gap, H * S + 2 * pad + 18), CASE)
    d = ImageDraw.Draw(canvas)
    for j, buf in enumerate((left, right)):
        x0 = pad + j * (W * S + 2 * pad + gap)
        d.rounded_rectangle([x0 - 8, pad - 8, x0 + W * S + 7, pad + H * S + 7], 6, fill=BEZEL)
        canvas.paste(panel(buf), (x0, pad))
        d.text((x0 + W * S // 2 - 14, pad + H * S + 6), "LEFT" if j == 0 else "RIGHT", fill=(90, 85, 75))
    frames.append(canvas)
frames[0].save(dst, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True)
print(f"{len(frames)} frames -> {dst}")

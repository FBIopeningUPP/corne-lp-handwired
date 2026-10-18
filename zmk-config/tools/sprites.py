"""Generate src/sprites.h: Blip the robot (32x42 portrait sprites) + a 3x5 pixel font.

Edit the drawing code below, run `python3 tools/sprites.py`, rebuild.
Pixels are 1 = lit.
"""
import os
from PIL import Image, ImageDraw

W, H = 32, 42
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "src", "sprites.h")

def base(eyes="open", hands="rest", mouth="smile", antenna="on", sweat=False):
    im = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(im)
    # keyboard: little trapezoid with key dots
    d.polygon([(4, 33), (27, 33), (30, 41), (1, 41)], outline=1)
    for ry, (x0, x1) in zip((35, 37, 39), ((6, 25), (5, 26), (4, 27))):
        for x in range(x0, x1 + 1, 3):
            d.point((x, ry), 1)
    # body
    d.rounded_rectangle([10, 21, 21, 31], radius=3, fill=1)
    d.line([(13, 25), (18, 25)], fill=0)            # chest light
    # head
    d.ellipse([5, 4, 26, 21], fill=1)
    # antenna
    d.line([(15, 1), (15, 4)], fill=1); d.line([(16, 1), (16, 4)], fill=1)
    if antenna == "on":
        d.rectangle([14, 0, 17, 1], fill=1)
    elif antenna == "spark":
        d.rectangle([14, 0, 17, 1], fill=1)
        for p in [(12, 0), (19, 0), (13, 2), (18, 2)]:
            d.point(p, 1)
    # eyes (drawn in black on the white head)
    if eyes == "open":
        d.rectangle([10, 9, 12, 14], fill=0); d.rectangle([19, 9, 21, 14], fill=0)
        d.point((10, 9), 1); d.point((19, 9), 1)    # sparkle
    elif eyes == "blink":
        d.line([(10, 13), (12, 13)], fill=0); d.line([(19, 13), (21, 13)], fill=0)
    elif eyes == "focus":
        d.line([(9, 9), (12, 11)], fill=0); d.line([(22, 9), (19, 11)], fill=0)   # brows
        d.rectangle([10, 12, 12, 14], fill=0); d.rectangle([19, 12, 21, 14], fill=0)
    elif eyes == "sleep":
        d.line([(9, 12), (12, 13)], fill=0); d.line([(22, 12), (19, 13)], fill=0)
    # mouth
    if mouth == "smile":
        d.line([(14, 17), (17, 17)], fill=0); d.point((13, 16), 0); d.point((18, 16), 0)
    elif mouth == "open":
        d.rectangle([14, 16, 17, 18], fill=0)
    elif mouth == "flat":
        d.line([(14, 17), (17, 17)], fill=0)
    # arms + hands
    left_y, right_y = {"rest": (31, 31), "a": (33, 28), "b": (28, 33)}[hands]
    d.line([(10, 24), (7, left_y - 1)], fill=1); d.line([(21, 24), (24, right_y - 1)], fill=1)
    d.rectangle([5, left_y - 1, 9, left_y + 1], fill=1)
    d.rectangle([22, right_y - 1, 26, right_y + 1], fill=1)
    # pressed key flash under the hand that is down
    if hands == "a":
        d.rectangle([5, 35, 9, 36], fill=1)
    if hands == "b":
        d.rectangle([22, 35, 26, 36], fill=1)
    if sweat:
        d.point((28, 6), 1); d.line([(27, 7), (29, 7)], fill=1); d.line([(27, 8), (29, 8)], fill=1); d.point((28, 9), 1)
    return im

FRAMES = {
    "IDLE":   base(),
    "BLINK":  base(eyes="blink"),
    "TYPE_A": base(hands="a", mouth="flat"),
    "TYPE_B": base(hands="b", mouth="flat"),
    "FAST_A": base(eyes="focus", hands="a", mouth="open", antenna="spark", sweat=True),
    "FAST_B": base(eyes="focus", hands="b", mouth="open", antenna="spark", sweat=True),
    "SLEEP":  base(eyes="sleep", mouth="flat", antenna="off"),
}

# 3x5 font, rows top->bottom, '#' = lit
FONT = {
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", ".##", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "-": ["...", "...", "###", "...", "..."], "+": ["...", ".#.", "###", ".#.", "..."],
    "%": ["#.#", "..#", ".#.", "#..", "#.#"], " ": ["...", "...", "...", "...", "..."],
}

def pack(im):
    """row-major, 4 bytes per 32px row, MSB = leftmost pixel"""
    out = []
    for y in range(im.height):
        for bx in range(0, W, 8):
            b = 0
            for i in range(8):
                if im.getpixel((bx + i, y)):
                    b |= 0x80 >> i
            out.append(b)
    return out

lines = ["/* Generated by tools/sprites.py - do not edit by hand */",
         "#pragma once", "#include <stdint.h>", "",
         f"#define SPRITE_W {W}", f"#define SPRITE_H {H}", ""]
lines.append("enum blip_frame { " + ", ".join(f"BLIP_{k}" for k in FRAMES) + ", BLIP_COUNT };")
lines.append(f"static const uint8_t blip_frames[BLIP_COUNT][{W * H // 8}] = {{")
for k, im in FRAMES.items():
    data = pack(im)
    lines.append(f"    [BLIP_{k}] = {{")
    for i in range(0, len(data), 16):
        lines.append("        " + ", ".join(f"0x{b:02x}" for b in data[i:i + 16]) + ",")
    lines.append("    },")
lines.append("};\n")
lines.append("/* 3x5 font: 15 bits, bit 14 = top-left, row-major */")
lines.append("struct glyph { char c; uint16_t bits; };")
lines.append("static const struct glyph font3x5[] = {")
for ch, rows in FONT.items():
    bits = 0
    for r in rows:
        for c in r:
            bits = (bits << 1) | (c == "#")
    lines.append(f"    {{'{ch}', 0x{bits:04x}}},")
lines.append("};")
open(OUT, "w").write("\n".join(lines) + "\n")

# contact sheet for checking the art
sheet = Image.new("1", ((W + 4) * len(FRAMES), H), 0)
for i, im in enumerate(FRAMES.values()):
    sheet.paste(im, (i * (W + 4), 0))
sheet.resize((sheet.width * 6, sheet.height * 6), Image.NEAREST).save(
    os.path.join(HERE, "sprites_sheet.png"))
print("wrote", OUT)

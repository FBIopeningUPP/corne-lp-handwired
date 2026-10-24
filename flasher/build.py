"""Bundle the firmware into the web flasher.

    python3 flasher/build.py  ->  flasher/dist/index.html  (site/build.py publishes it at /flasher/)
The page embeds the three .uf2 files, so it also works opened straight from disk in Chrome or Edge.
"""
import base64, datetime, json, os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FWDIR = os.path.join(ROOT, "firmware")

FIRMWARE = {
    "left": dict(name="Left half", short="left half", file="corne_lp_left-nice_nano_v2.uf2",
                 note="Central: talks to your computer, runs the left OLED.",
                 after="Flash the right half next, then power both together."),
    "right": dict(name="Right half", short="right half", file="corne_lp_right-nice_nano_v2.uf2",
                  note="Peripheral: links to the left half, runs the trackpad.",
                  after="Power both halves together: they pair with each other by themselves."),
    "reset": dict(name="Settings reset", short="settings reset", file="settings_reset-nice_nano_v2.uf2",
                  note="Wipes pairings. Use on both boards if the halves won't connect.",
                  after="Now flash the left or right firmware back onto this board."),
}


def uf2_ok(data):
    n = len(data) // 512
    for i in range(n):
        m0, m1, flags, addr, size, bno, nb, fam = struct.unpack("<8I", data[i * 512:i * 512 + 32])
        if m0 != 0x0A324655 or m1 != 0x9E5D5157 or fam != 0xADA52840 or bno != i or nb != n:
            return False
    return n > 0 and len(data) % 512 == 0


def page(template_body, title_extra=""):
    head, body = template_body.split("</style>", 1)
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n" + head + "</style>\n</head>\n<body>\n"
            + body + "\n</body>\n</html>\n")


if __name__ == "__main__":
    fw = {}
    stamp = None
    for k, meta in FIRMWARE.items():
        p = os.path.join(FWDIR, meta["file"])
        data = open(p, "rb").read()
        assert uf2_ok(data), f"{meta['file']} is not a valid nRF52840 UF2"
        fw[k] = dict(meta, size=len(data), blocks=len(data) // 512, b64=base64.b64encode(data).decode())
        if k == "left":
            stamp = datetime.datetime.fromtimestamp(os.path.getmtime(p))
    build = f"ZMK v0.3 · nice_nano_v2 · built {stamp:%d %b %Y}"
    src = open(os.path.join(HERE, "template.html")).read()
    src = src.replace("/*FW*/null", json.dumps(fw)).replace("/*BUILD*/null", json.dumps(build))
    out = os.path.join(HERE, "dist"); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "index.html"), "w").write(page(src))
    print("flasher:", os.path.getsize(os.path.join(out, "index.html")) // 1024, "KB;", build)

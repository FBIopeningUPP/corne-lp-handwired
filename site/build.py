"""Assemble the GitHub Pages site into _site/.

    pip install markdown
    python3 site/build.py          then open _site/index.html (or: python3 -m http.server -d _site)

  _site/index.html                landing page (site/index.html)
  _site/images/                   renders, diagrams, keymap, Blip (docs/images, minus the style-option sheets)
  _site/viewer/index.html         the interactive 3D viewer (viewer/dist/index.html)
  _site/build-guide/index.html    docs/build-guide.md as a web page
  _site/wiring_guide.pdf          docs/wiring_guide.pdf
  _site/corne-lp-print-files.zip  everything in print/

The GitHub Actions workflow (.github/workflows/pages.yml) runs this and publishes _site/.
"""
import os
import re
import shutil
import sys
import zipfile

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "_site")
REPO = "https://github.com/FBIopeningUPP/corne-lp-handwired"


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(ROOT, src), dst)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corne LP build guide</title>
<meta name="description" content="Parts, printing, wiring, assembly and firmware for the Corne LP, a handwired wireless 7.7 mm split keyboard.">
<style>
:root{{--bg:#121316;--card:#1a1b1f;--line:#2b2c31;--fg:#e9e6df;--mut:#9b9a97;--sig:#e5532a;--bone:#e4ddcf}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 Inter,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}}
nav{{position:sticky;top:0;z-index:10;background:rgba(18,19,22,.85);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}}
nav div{{width:min(860px,100% - 40px);margin:0 auto;display:flex;align-items:center;gap:6px;height:56px}}
nav b{{margin-right:auto;font-size:17px}}nav b span{{color:var(--sig)}}
nav a{{text-decoration:none;color:var(--mut);font-size:14px;padding:6px 10px;border-radius:8px}}nav a:hover{{color:var(--fg);background:#ffffff0d}}
article{{width:min(860px,100% - 40px);margin:0 auto;padding:36px 0 90px}}
h1{{font-size:clamp(34px,6vw,54px);letter-spacing:-.03em;line-height:1.05;margin:.2em 0 .3em}}
h2{{font-size:30px;letter-spacing:-.02em;margin:2.2em 0 .5em;padding-top:.6em;border-top:1px solid var(--line)}}
h3{{font-size:20px;margin:1.8em 0 .4em;color:var(--bone)}}
a{{color:#ff8a63}}a:hover{{color:#ffb095}}
img{{max-width:100%;height:auto;border-radius:12px}}
table{{width:100%;border-collapse:collapse;margin:1.2em 0;font-size:14.5px;display:block;overflow-x:auto}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--mut);font-weight:600;white-space:nowrap}}
code{{background:#ffffff12;padding:2px 6px;border-radius:6px;font-size:.88em}}
pre{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;overflow-x:auto;line-height:1.5}}pre code{{background:none;padding:0}}
hr{{display:none}}
li{{margin:.3em 0}}
p[align=center]{{text-align:center}}
</style></head><body>
<nav><div><b>Corne <span>LP</span></b><a href="../">Home</a><a href="../viewer/">3D viewer</a><a href="{repo}">GitHub</a></div></nav>
<article>
{body}
</article></body></html>
"""


def fix_links(html):
    def rewrite(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://", "#", "mailto:", "data:")):
            return m.group(0)
        new = url
        if url.startswith("images/style-options"):
            new = f"{REPO}/tree/main/docs/{url}"
        elif url.startswith("images/"):
            new = "../" + url
        elif url == "../README.md":
            new = "../"
        elif url == "wiring_guide.pdf":
            new = "../wiring_guide.pdf"
        elif url.startswith("../"):
            new = f"{REPO}/tree/main/{url[3:]}"
        return f'{attr}="{new}"'
    return re.sub(r'\b(href|src)="([^"]*)"', rewrite, html)


def build_guide():
    src = open(os.path.join(ROOT, "docs", "build-guide.md"), encoding="utf-8").read()
    html = markdown.markdown(src, extensions=["tables", "fenced_code", "toc", "sane_lists"],
                             extension_configs={"toc": {"toc_depth": "2-3"}})
    html = fix_links(html)
    html = html.replace('<a href="../">← back to the README</a>', '<a href="../">← back to the home page</a>')
    dst = os.path.join(OUT, "build-guide", "index.html")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8").write(PAGE.format(body=html, repo=REPO))
    return html


def zip_print_files():
    dst = os.path.join(OUT, "corne-lp-print-files.zip")
    base = os.path.join(ROOT, "print")
    n = 0
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for d, _, files in os.walk(base):
            for f in sorted(files):
                p = os.path.join(d, f)
                z.write(p, os.path.join("corne-lp-print-files", os.path.relpath(p, base)))
                n += 1
    return n, os.path.getsize(dst)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    copy("site/index.html", os.path.join(OUT, "index.html"))
    shutil.copytree(os.path.join(ROOT, "docs", "images"), os.path.join(OUT, "images"),
                    ignore=shutil.ignore_patterns("style-options"))
    copy("viewer/dist/index.html", os.path.join(OUT, "viewer", "index.html"))
    copy("docs/wiring_guide.pdf", os.path.join(OUT, "wiring_guide.pdf"))
    build_guide()
    n, size = zip_print_files()
    total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
    print(f"_site ready: {total / 1e6:.1f} MB (print-files zip: {n} files, {size / 1e6:.1f} MB)")


if __name__ == "__main__":
    sys.exit(main())

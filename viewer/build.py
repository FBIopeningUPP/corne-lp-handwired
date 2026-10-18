"""Inline data.js into index.html -> dist/index.html (+ copies the mesh files)."""
import os, re, shutil
H = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(H, "dist"); os.makedirs(D, exist_ok=True)
data = open(os.path.join(H, "data.js")).read().strip()
data = re.sub(r"^window\.CORNE = ", "", data).rstrip(";")
import base64, json
d = json.loads(data)
d["meshes"] = {f[:-4]: base64.b64encode(open(os.path.join(H, f), "rb").read()).decode()
               for f in sorted(os.listdir(H)) if f.endswith(".bin")}
data = json.dumps(d, separators=(",", ":"))
page = open(os.path.join(H, "index.html")).read().replace("/*DATA*/null", data)
open(os.path.join(D, "index.html"), "w").write(page)
for f in os.listdir(D):
    if f.endswith(".bin"):
        os.remove(os.path.join(D, f))
print("dist ready:", sorted(os.listdir(D)))

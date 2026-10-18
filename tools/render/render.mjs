// Studio renders of the Corne LP for the README.
//
// Drives the real 3D viewer (viewer/dist/index.html) in headless Chromium, so every picture is
// made from the same meshes you print. Run from this folder:
//
//   npm install                  three.js + Playwright (then `npx playwright install chromium` if you have no Chromium)
//   node render.mjs              every shot -> raw/*.png
//   node render.mjs hero top     just those shots
//   python3 compose.py           raw/ -> ../../docs/images/renders/ (JPEGs, colourway sheet, turntable GIF)
//
// Rendering happens in software WebGL (SwiftShader), so no GPU is needed.
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const RAW = path.join(HERE, "raw");
const THREE_DIR = path.join(HERE, "node_modules", "three");
fs.mkdirSync(RAW, { recursive: true });

/* ---------- tiny static server: the repo at /, three.js at /three/ ---------- */
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split("?")[0]);
  const file = url.startsWith("/three/") ? path.join(THREE_DIR, url.slice(7)) : path.join(ROOT, url);
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
    res.end(buf);
  });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;

/* ---------- colourways ---------- */
// keycaps: col 0 = outer pinky column (mods), row 3 = thumbs, accents by "row,col" per half
const CW = {
  bone:     { case: "#e4ddcf", alpha: "#f1eee7", mod: "#2a2b30", thumb: "#2a2b30", accent: "#e5532a", accents: { left: ["1,4"], right: ["1,4", "2,0"] } },
  graphite: { case: "#3a3c41", alpha: "#26272b", mod: "#9a9da3", thumb: "#9a9da3", accent: "#e5532a", accents: { left: ["1,4"], right: ["1,4", "2,0"] } },
  sage:     { case: "#a3b39a", alpha: "#f1eee7", mod: "#4c5a48", thumb: "#4c5a48", accent: "#e8b04a", accents: { left: ["1,4"], right: ["1,4"] } },
  glacier:  { case: "#b9d3df", alpha: "#f4f6f7", mod: "#3f6b85", thumb: "#3f6b85", accent: "#e5532a", accents: { left: ["1,4"], right: ["1,4"] } },
  lilac:    { case: "#b8a6d6", alpha: "#f1eee7", mod: "#5b4a7a", thumb: "#5b4a7a", accent: "#f2c14e", accents: { left: ["1,4"], right: ["1,4"] } },
  signal:   { case: "#e5532a", alpha: "#1f2024", mod: "#efede8", thumb: "#efede8", accent: "#efede8", accents: { left: [], right: [] } },
};

/* ---------- shots ---------- */
// cam: [polar deg from straight up, azimuth deg, distance mm, target [x, y, z]] (three.js axes, y up).
// "fit" framing zooms to the model afterwards, so distance mostly sets how strong the perspective is.
const TILE = { theme: "light", cam: [48, -14, 700, [0, 0, 6]], size: 1600 };
const SHOTS = {
  hero:      { cw: "bone", theme: "dark", cam: [56, -18, 640, [0, 0, 6]], demo: 11000 },
  top:       { cw: "bone", theme: "light", cam: [0.01, 0, 760, [0, 0, 6]], demo: 4000 },
  profile:   { cw: "graphite", theme: "light", cam: [79, -34, 420, [0, 4, 6]], demo: 3000 },
  closeup:   { cw: "bone", theme: "dark", cam: [50, -42, 250, [-12, 4, -6]], demo: 8000, frame: "seen" },
  exploded:  { cw: "bone", theme: "light", mode: "exploded", cam: [62, -22, 820, [0, 40, 6]] },
  xray:      { cw: "graphite", theme: "dark", mode: "xray", cam: [40, -10, 700, [0, 0, 6]] },
  wiring:    { cw: "bone", theme: "dark", wiring: true, cam: [176, 0, 760, [0, 0, 6]] },
  underside: { cw: "bone", theme: "light", cam: [140, -25, 700, [0, 0, 6]] },
  bag:       { cw: "bone", theme: "light", mode: "bag", cam: [62, -30, 520, [0, 14, 0]] },
  carry:     { cw: "bone", theme: "light", mode: "bag", carry: "full", carryColor: "#3d4148", cam: [58, -30, 520, [0, 14, 0]] },
  bumper:    { cw: "bone", theme: "light", mode: "bag", carry: "bumper", carryColor: "#e5532a", cam: [58, -30, 520, [0, 14, 0]] },
  cw_bone:     { ...TILE, cw: "bone" },
  cw_graphite: { ...TILE, cw: "graphite" },
  cw_sage:     { ...TILE, cw: "sage" },
  cw_glacier:  { ...TILE, cw: "glacier" },
  cw_lilac:    { ...TILE, cw: "lilac" },
  cw_signal:   { ...TILE, cw: "signal" },
  // a slow orbit while Blip types: frames -> raw/turntable/, compose.py makes the GIF
  turntable: { cw: "bone", theme: "dark", cam: [58, 0, 640, [0, 0, 6]], demo: 2500, frames: 60, size: 900 },
};

const want = process.argv.slice(2);
const names = want.length ? want : Object.keys(SHOTS);
for (const n of names) if (!SHOTS[n]) { console.error(`unknown shot "${n}". Shots: ${Object.keys(SHOTS).join(" ")}`); process.exit(1); }

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
// Reduced motion: the viewer snaps between views instead of easing (software WebGL draws only a few
// frames a second, so eased transitions would take ages). Half pixel ratio keeps the live view cheap;
// snapshots render at their own size.
const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 0.5, reducedMotion: "reduce" });
page.on("pageerror", (e) => console.error("  page error:", e.message));
await page.addInitScript((base) => {
  const ex = (p) => `${base}/three/examples/jsm/${p}`;
  window.__CORNE_TEST = {
    urls: [`${base}/three/build/three.module.js`, ex("controls/OrbitControls.js"), ex("environments/RoomEnvironment.js"),
      ex("geometries/RoundedBoxGeometry.js"), ex("utils/BufferGeometryUtils.js")],
    importmap: { imports: { three: `${base}/three/build/three.module.js` } },
  };
  try { localStorage.clear(); } catch (e) {}
}, BASE);
console.log("loading viewer…");
await page.goto(`${BASE}/viewer/dist/index.html`, { timeout: 180000 });
await page.waitForFunction(() => window.__R && window.__R.ready(), null, { timeout: 180000 });
await page.addStyleTag({ content: ".rail,.brand,.typebar,.toast{display:none!important}" });

/** put the scene in the state a shot asks for */
async function stage(s) {
  await page.evaluate(({ s, cw }) => {
    document.documentElement.setAttribute("data-theme", s.theme || "light");
    const R = window.__R;
    R.setDemo(false);
    R.setMode(s.mode || "assembled");
    if (s.carry) { R.setCase(true); R.setCaseStyle(s.carry); } else R.setCase(false);
    if (s.wiring) R.setWiring(true);
    for (const k in R.vis) R.vis[k] = !(s.wiring && (k === "base" || k === "magnets"));
    R.M.shell.color.set(cw.case);
    R.M.base.color.set(cw.case).multiplyScalar(0.92);
    if (s.carryColor) R.M.carry.color.set(s.carryColor);
    for (const side of ["left", "right"]) for (const [rc, cap] of R.keyMeshes[side]) {
      const [row, col] = rc.split(",").map(Number);
      cap.material.color.set((cw.accents[side] || []).includes(rc) ? cw.accent : row === 3 ? cw.thumb : col === 0 ? cw.mod : cw.alpha);
    }
    if (s.demo) R.setDemo(true);
  }, { s, cw: CW[s.cw] });
}

/** camera on a sphere round the target; also cancels any preset glide the viewer started */
async function aim(cam) {
  await page.evaluate((cam) => {
    const R = window.__R, T = R.THREE, [ph, th, d, t] = cam;
    R.controls.dispatchEvent({ type: "start" });      // stops camera tweens + turntable
    R.controls.target.set(...t);
    const v = new T.Vector3().setFromSpherical(new T.Spherical(d, T.MathUtils.degToRad(ph), T.MathUtils.degToRad(th)));
    R.camera.position.copy(R.controls.target).add(v);
    R.controls.update();
  }, cam);
}

/** keys at rest, no typing glow, then render in the same tick (Blip keeps his typing frame) */
async function snap(s, file) {
  const out = await page.evaluate((o) => {
    const R = window.__R;
    for (const side of ["left", "right"]) for (const cap of R.keyMeshes[side].values()) {
      cap.userData.press = 0; cap.userData.glow = 0; cap.position.y = cap.userData.rest; cap.material.emissive.setRGB(0, 0, 0);
    }
    const wpm = R.screens.left.meter.wpm;
    return window.__corneSnap(o).then((url) => ({ url, wpm }));
  }, { frame: s.frame || "fit", shape: s.shape || "16:9", size: String(s.size || 3200), bg: "studio", shadow: "on" });
  fs.writeFileSync(file, Buffer.from(out.url.split(",")[1], "base64"));
  return out.wpm;
}

const t0 = Date.now();
for (const n of names) {
  const s = SHOTS[n], t1 = Date.now();
  await stage(s);
  await page.waitForTimeout(600);                 // mode / case / wiring changes land
  await aim(s.cam);
  await page.waitForTimeout(s.demo || 1200);      // Blip gets typing; shadows and textures settle
  if (s.frames) {
    const dir = path.join(RAW, n); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
    const [ph, th0, d, t] = s.cam;
    for (let i = 0; i < s.frames; i++) {
      await aim([ph, th0 + (360 * i) / s.frames, d, t]);
      await page.waitForTimeout(120);
      await snap({ ...s, frame: "seen" }, path.join(dir, `${String(i).padStart(3, "0")}.png`));
    }
    console.log(`  ${n}/ ${s.frames} frames  (${((Date.now() - t1) / 1000).toFixed(0)} s)`);
  } else {
    const wpm = await snap(s, path.join(RAW, `${n}.png`));
    console.log(`  ${n}.png${s.demo ? `  Blip at ${wpm} WPM` : ""}  (${((Date.now() - t1) / 1000).toFixed(0)} s)`);
  }
}
await browser.close();
server.close();
console.log(`done in ${((Date.now() - t0) / 1000).toFixed(0)} s -> tools/render/raw/ (next: python3 compose.py)`);

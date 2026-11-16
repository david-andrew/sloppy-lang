// Web pages: what they keep after starting and what the runtime allocates each frame, in headless
// Chromium (Playwright's, or Chrome on the PATH; none: only the checks without a browser).
//  1. a big module (a 16 MB file embedded): the single page starts and keeps neither its base64
//     text nor the bytes (a 20 MB module once left ~70 MB of JavaScript heap behind); built with
//     --wasm-file, the page and module.wasm beside it start over http (compiled while they
//     download), and a page opened from disk says what to do instead
//  2. tests/web/busy.jo, a frame of a game (shapes, text, sound playing): the runtime makes no
//     typed array, view, copy, TextDecoder or TextEncoder, media query or gamepad list per frame
//     (a view of wasm memory per call, a copy per chunk of sound, ... once were), and its sampled
//     JavaScript allocations stay small; and few numbers cross from the module to JavaScript as
//     objects made each call: a 64-bit int arrives as a BigInt and a float as a heap number (a
//     GL offset and the uniforms' floats once did, ~560 a frame in examples/aces; time() once
//     returned a float, ~24 a frame there)
//  3. tests/web/lazy_shaders.jo: a shader is linked at its first draw, or by warm_up_shaders
//     (oldest first), not when made (linking took a phone ~60 ms a program, ~50 of them before a
//     game's first frame); with KHR_parallel_shader_compile (here a stand-in for it: headless
//     Chromium's SwiftShader has none) every program starts linking when made, and no status that
//     waits for a link is asked before the browser says it is done, except at a first draw
//     A shader made with warm = false waits for no warm-up until warm_up_later queues it, and one
//     made again from the same source is the program made before (a game's view rebuilt for a new
//     game linked its shaders again during play); tests/web/lazy_shaders3d.jo: the library queues
//     its 3D shaders only while their feature is on (no shadow or instanced programs linked with
//     shadows off and no instanced 3D draw)
//  4. a page playing a tone: served cross-origin isolated, its sound goes to the audio thread
//     through a shared ring, with no message per chunk; served as GitHub Pages serves it (no
//     SharedArrayBuffer), a message per chunk and none back; both reach the output
// usage: node tools/webperfcheck.mjs [path/to/sloppy]
import { spawn, spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdtempSync, rmSync, statSync, mkdirSync } from "node:fs";
import { createServer } from "node:http";
import { join, dirname, extname, basename } from "node:path";
import { tmpdir, homedir } from "node:os";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const sloppy = process.argv[2] || join(root, "bin", process.platform === "win32" ? "sloppy.exe" : "sloppy");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;
const expect = (what, ok, got) => {
  if (ok) console.log(`ok   ${what} (${got})`);
  else { failed++; console.log(`FAIL ${what}: ${got}`); }
};

// the browser
let chrome = null, shell = true;
const pw = join(homedir(), ".cache", "ms-playwright");
if (existsSync(pw)) for (const d of readdirSync(pw).sort()) if (d.startsWith("chromium_headless_shell")) {
  for (const sub of readdirSync(join(pw, d))) { const p = join(pw, d, sub, "chrome-headless-shell"); if (existsSync(p)) chrome = p; }
}
if (!chrome) for (const n of ["google-chrome", "chromium", "chromium-browser"]) {
  const r = spawnSync("which", [n], { encoding: "utf8" });
  if (r.status === 0 && r.stdout.trim()) { chrome = r.stdout.trim(); shell = false; break; }
}

const tmp = mkdtempSync(join(tmpdir(), "sloppy-webperf-"));
const env = { ...process.env, SLOPPY_LIB: join(root, "lib") };
const build = (src, out, ...more) => {
  const r = spawnSync(sloppy, ["build", src, "--target", "wasm", "-o", out, ...more], { env, encoding: "utf8" });
  if (r.status !== 0) { console.log(r.stdout + r.stderr); throw new Error("could not build " + src); }
};

// ---- the pages ----
// (a big module: a 16 MB file of noise embedded, as a game's assets are)
const bigDir = join(tmp, "bigsrc");
mkdirSync(bigDir);
const pad = Buffer.alloc(16 << 20);
let x = 2463534242;
for (let i = 0; i < pad.length; i += 4) { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; pad.writeUInt32LE(x, i); }
writeFileSync(join(bigDir, "pad.bin"), pad);
writeFileSync(join(bigDir, "big.jo"), `window("big", 320, 200)
pad = embed("pad.bin")
t = 0.0
update = (dt: f64):
    global t
    t += dt
draw = ():
    clear(rgb(0.1, 0.1, 0.2))
    circle(vec2(160.0 + 100.0 * cos(t), 100.0), 10.0, WHITE)
if pad.len() == 7: print("odd")
`);
build(join(bigDir, "big.jo"), join(tmp, "big.html"));
mkdirSync(join(tmp, "split"));
build(join(bigDir, "big.jo"), join(tmp, "split", "big.html"), "--wasm-file");
build(join(root, "tests", "web", "busy.jo"), join(tmp, "busy.html"));
build(join(root, "tests", "web", "lazy_shaders.jo"), join(tmp, "lazy_shaders.html"));
build(join(root, "tests", "web", "lazy_shaders3d.jo"), join(tmp, "lazy_shaders3d.html"));
writeFileSync(join(tmp, "tone.jo"), `window("tone", 160, 100)
beep = tone(440.0, 0.5, volume = 0.5)
id = -1
update = (dt: f64):
    global id
    if id < 0: id = play(beep, looping = true)
draw = (): clear(rgb(0.1, 0.1, 0.2))
`);
build(join(tmp, "tone.jo"), join(tmp, "tone.html"));

// ---- without a browser: the pages' form ----
const single = readFileSync(join(tmp, "big.html"), "utf8");
const m = /<script type="([^"]*)" id="sloppy-wasm">([^<]*)<\/script>/.exec(single);
expect("the single page holds its module as text in a script element that is not run", m && m[1] !== "text/javascript" && !/SLOPPY_WASM =/.test(single), m ? `type ${m[1]}, ${(m[2].length / 1e6).toFixed(1)} MB of base64` : "no such element");
const splitPage = readFileSync(join(tmp, "split", "big.html"), "utf8");
const s = /id="sloppy-wasm" data-src="big\.wasm\?v=([0-9a-f]+)"><\/script>/.exec(splitPage);
const wasmFile = existsSync(join(tmp, "split", "big.wasm")) ? readFileSync(join(tmp, "split", "big.wasm")) : null;
expect("--wasm-file: a small page that names big.wasm beside it, with the module's hash", s && wasmFile && splitPage.length < 400000, s ? `page ${(splitPage.length / 1e3).toFixed(0)} KB, v=${s[1]}` : "no data-src");
expect("--wasm-file: the same module as in the single page", m && wasmFile && Buffer.from(m[2], "base64").equals(wasmFile), wasmFile ? `${(wasmFile.length / 1e6).toFixed(1)} MB` : "no big.wasm");

if (!chrome) {
  console.log("(no browser: the pages were not run)");
  rmSync(tmp, { recursive: true, force: true });
  console.log(failed ? `${failed} failed` : "web performance: all checks passed");
  process.exit(failed ? 1 : 0);
}

// ---- in the browser ----
// (under /iso/: the same files with the headers that make a page cross-origin isolated, so that
// it may have SharedArrayBuffer)
const server = createServer((q, r) => {
  let path = decodeURIComponent(new URL(q.url, "http://x").pathname);
  const iso = path.startsWith("/iso/");
  if (iso) path = path.slice(4);
  const f = join(tmp, path);
  if (!f.startsWith(tmp) || !existsSync(f) || statSync(f).isDirectory()) { r.writeHead(404); r.end(); return; }
  r.writeHead(200, { "content-type": { ".html": "text/html", ".wasm": "application/wasm" }[extname(f)] || "application/octet-stream",
    ...(iso ? { "cross-origin-opener-policy": "same-origin", "cross-origin-embedder-policy": "require-corp" } : {}) });
  r.end(readFileSync(f));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const http = `http://127.0.0.1:${server.address().port}`;

// what the page's runtime makes, counted (a hook run before the page's own scripts); frames
// counted at each animation frame, and the first one's time once "loading…" is gone
const hook = `(() => {
  const n = window.__made = {};
  const count = (k) => { n[k] = (n[k] || 0) + 1; };
  for (const k of ["ArrayBuffer", "DataView", "Uint8Array", "Int8Array", "Uint16Array", "Int16Array", "Uint32Array", "Int32Array", "Float32Array", "Float64Array", "TextDecoder", "TextEncoder"]) {
    const C = window[k];
    window[k] = new Proxy(C, { construct(t, a, nt) { count(k); return Reflect.construct(t, a, nt === window[k] ? t : nt); } });
  }
  const TA = Object.getPrototypeOf(Uint8Array.prototype);
  for (const k of ["slice", "subarray"]) { const f = TA[k]; TA[k] = function (...a) { count(k); return f.apply(this, a); }; }
  const mm = window.matchMedia; window.matchMedia = function (q) { count("matchMedia"); return mm.call(this, q); };
  if (navigator.getGamepads) { const g = navigator.getGamepads; navigator.getGamepads = function () { count("getGamepads"); return g.call(this); }; }
  const pm = MessagePort.prototype.postMessage; MessagePort.prototype.postMessage = function (...a) { count("audio chunks"); return pm.apply(this, a); };
  const cs = WebAssembly.compileStreaming; if (cs) WebAssembly.compileStreaming = function (...a) { count("compileStreaming"); return cs.apply(this, a); };
  window.__frames = 0; window.__ttf = 0;
  const raf = window.requestAnimationFrame.bind(window);
  const tick = () => { window.__frames++; if (!window.__ttf && !document.getElementById("sloppy-loading")) window.__ttf = performance.now(); };
  window.requestAnimationFrame = (f) => raf((t) => { f(t); tick(); });
})();`;

// (a module's function imports: each one's parameter and result types, from its type and import
// sections)
const importSigs = (b) => {
  let p = 8;
  const uleb = () => { let r = 0, s = 0, x; do { x = b[p++]; r += (x & 0x7f) * 2 ** s; s += 7; } while (x & 0x80); return r; };
  const name = () => { const n = uleb(); const t = b.subarray(p, p + n).toString(); p += n; return t; };
  const types = [], sigs = {};
  while (p < b.length) {
    const id = b[p++], size = uleb(), end = p + size;
    if (id === 1) for (let n = uleb(); n > 0; n--) {
      p++;
      const ps = []; for (let k = uleb(); k > 0; k--) ps.push(b[p++]);
      const rs = []; for (let k = uleb(); k > 0; k--) rs.push(b[p++]);
      types.push({ ps, rs });
    }
    else if (id === 2) for (let n = uleb(); n > 0; n--) { name(); const f = name(); if (b[p++] !== 0) break; sigs[f] = types[uleb()]; }
    if (id >= 2) break;
    p = end;
  }
  return sigs;
};
// (the calls of each import, counted: a hook of its own, as the counting allocates)
const countHook = `(() => {
  const c = window.__calls = {};
  const wrap = (imp) => {
    const env = {};
    for (const k in imp.env) { const f = imp.env[k]; env[k] = typeof f !== "function" ? f : function () { c[k] = (c[k] || 0) + 1; return f.apply(this, arguments); }; }
    return { ...imp, env };
  };
  const I = WebAssembly.instantiate, C = WebAssembly.Instance;
  WebAssembly.instantiate = (b, imp) => I(b, wrap(imp));
  WebAssembly.Instance = function (m, imp) { return new C(m, wrap(imp)); };
})();`;

async function browse(url, work, more = "") {
  const dir = mkdtempSync(join(tmp, "profile-"));
  const flags = ["--no-sandbox", "--mute-audio", "--enable-unsafe-swiftshader", "--enable-precise-memory-info", "--autoplay-policy=no-user-gesture-required",
    "--remote-debugging-port=0", `--user-data-dir=${dir}`, "--window-size=400,300"];
  if (!shell) flags.unshift("--headless=new");
  const b = spawn(chrome, [...flags, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
  let err = "";
  b.stderr.on("data", (d) => { err += d; });
  try {
    const t0 = Date.now();
    while (!/DevTools listening on (ws:\S+)/.test(err)) { if (Date.now() - t0 > 20000) throw new Error("the browser did not start"); await sleep(50); }
    const port = new URL(err.match(/DevTools listening on (ws:\S+)/)[1]).port;
    const target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page");
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((r) => ws.addEventListener("open", r));
    let id = 0;
    const waits = {};
    ws.addEventListener("message", (e) => { const msg = JSON.parse(e.data); if (msg.id && waits[msg.id]) waits[msg.id](msg.result || msg.error); });
    const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
    const ev = async (e) => { const r = await send("Runtime.evaluate", { expression: e, returnByValue: true }); return r.result ? r.result.value : undefined; };
    await send("Page.enable");
    await send("Page.addScriptToEvaluateOnNewDocument", { source: hook });
    if (more) await send("Page.addScriptToEvaluateOnNewDocument", { source: more });
    await send("Page.navigate", { url });
    // (until the first frame, or the page's log shows an error)
    const t1 = Date.now();
    let first = null;
    while (Date.now() - t1 < 60000) {
      first = await ev("[window.__ttf, (document.getElementById('log') || {}).textContent || '']");
      if (first && (first[0] || /error/.test(first[1]))) break;
      await sleep(50);
    }
    const r = await work({ send, ev, ttf: first ? first[0] : 0, log: first ? first[1] : "" });
    ws.close();
    return r;
  } finally {
    b.kill();
    await sleep(300);
    rmSync(dir, { recursive: true, force: true });
  }
}

// (what is kept, not garbage waiting to be collected: collected first)
const heapAfter = async (c) => { await sleep(500); await c.send("HeapProfiler.collectGarbage"); return (await c.ev("performance.memory.usedJSHeapSize")) / 1e6; };
const text = (m[2].length / 1e6).toFixed(0);
await browse("file://" + join(tmp, "big.html"), async (c) => {
  expect("the single page with a 16 MB file in it starts", c.ttf > 0, c.ttf ? `first frame at ${c.ttf.toFixed(0)} ms` : "no frame: " + c.log.slice(0, 300));
  const heap = await heapAfter(c);
  expect(`it keeps neither its ${text} MB of text nor the module's bytes`, c.ttf > 0 && heap < 8, `JavaScript heap ${heap.toFixed(1)} MB after its first frame, garbage collected`);
  expect("the text's element is gone from the page", !(await c.ev("!!document.getElementById('sloppy-wasm')")), "");
});
await browse(http + "/split/big.html", async (c) => {
  const made = await c.ev("window.__made");
  expect("--wasm-file: the page starts over http, compiling the module while it downloads", c.ttf > 0 && made.compileStreaming === 1, c.ttf ? `first frame at ${c.ttf.toFixed(0)} ms` : "no frame: " + c.log.slice(0, 300));
  const heap = await heapAfter(c);
  expect("--wasm-file: and keeps little", c.ttf > 0 && heap < 8, `JavaScript heap ${heap.toFixed(1)} MB after its first frame, garbage collected`);
});
await browse("file://" + join(tmp, "split", "big.html"), async (c) => {
  expect("--wasm-file: a page opened from disk says what to do instead", /without --wasm-file/.test(c.log), c.log.slice(0, 120));
});
await browse("file://" + join(tmp, "busy.html"), async (c) => {
  expect("the busy page starts", c.ttf > 0, c.ttf ? `first frame at ${c.ttf.toFixed(0)} ms` : "no frame: " + c.log.slice(0, 300));
  await sleep(2000);
  const m0 = await c.ev("window.__made"), f0 = await c.ev("window.__frames");
  await c.send("HeapProfiler.enable");
  await c.send("HeapProfiler.startSampling", { samplingInterval: 256, includeObjectsCollectedByMajorGC: true, includeObjectsCollectedByMinorGC: true });
  await sleep(4000);
  const prof = (await c.send("HeapProfiler.stopSampling")).profile;
  const m1 = await c.ev("window.__made"), frames = (await c.ev("window.__frames")) - f0;
  const per = {};
  // (what is made once a second, as the frame pacing's figures are sorted, is not per frame)
  for (const k of Object.keys(m1)) if (k !== "audio chunks" && (m1[k] - (m0[k] || 0)) > 0.2 * frames) per[k] = (m1[k] - (m0[k] || 0)) / Math.max(frames, 1);
  const chunks = (m1["audio chunks"] || 0) - (m0["audio chunks"] || 0);
  expect(`no typed array, copy, coder, media query or gamepad list made per frame (${frames} frames, ${chunks} chunks of sound)`, frames > 20 && Object.keys(per).length === 0,
    Object.keys(per).length ? Object.entries(per).map(([k, v]) => `${k} ${v.toFixed(2)} a frame`).join(", ") : "none");
  // (the page's own functions' allocations: not the module's numbers handed to JavaScript, made
  // in the wasm-to-JavaScript wrappers)
  let bytes = 0;
  const walk = (n) => { if (n.callFrame.url.endsWith("busy.html")) bytes += n.selfSize; for (const k of n.children) walk(k); };
  walk(prof.head);
  const kb = bytes / Math.max(frames, 1) / 1e3;
  expect("the runtime's own JavaScript allocations each frame are small", frames > 20 && kb < 2, `${kb.toFixed(2)} KB a frame, sampled`);
});
// (the module's numbers handed to JavaScript each frame that arrive as objects made for the call:
// i64 a BigInt, f32 and f64 a heap number unless a small integer)
const busyPage = readFileSync(join(tmp, "busy.html"), "utf8");
const busySigs = importSigs(Buffer.from(/id="sloppy-wasm">([^<]*)</.exec(busyPage)[1], "base64"));
await browse("file://" + join(tmp, "busy.html"), async (c) => {
  await sleep(1500);
  const c0 = await c.ev("window.__calls"), f0 = await c.ev("window.__frames");
  await sleep(2000);
  const c1 = await c.ev("window.__calls"), frames = (await c.ev("window.__frames")) - f0;
  const boxed = [];
  let total = 0;
  for (const k of Object.keys(c1)) {
    const sig = busySigs[k];
    if (!sig) continue;
    const n = sig.ps.filter((t) => t === 0x7e || t === 0x7d || t === 0x7c).length;
    const per = n * (c1[k] - (c0[k] || 0)) / Math.max(frames, 1);
    if (per > 0) { boxed.push([k, per]); total += per; }
  }
  boxed.sort((a, b) => b[1] - a[1]);
  expect(`few 64-bit ints and floats handed to JavaScript each frame (BigInts and heap numbers; ${frames} frames)`, frames > 20 && total <= 6,
    `${total.toFixed(1)} a frame` + (boxed.length ? ": " + boxed.slice(0, 4).map(([k, v]) => `${k} ${v.toFixed(1)}`).join(", ") : ""));
}, countHook);
// (the page's programs, by the shader functions in them: their links, statuses asked and completion
// asked, in order with the page's lines. `fake`: a stand-in KHR_parallel_shader_compile whose links
// are not done the first time asked)
const lazyHook = (fake) => `(() => {
  const ev = window.__lz = [];
  const P = WebGL2RenderingContext.prototype;
  const tagOf = new Map(), progOf = new Map(), asked = new Map();
  const tag = (o) => tagOf.get(o) || "";
  const ss = P.shaderSource; P.shaderSource = function (s, src) { const m = /lz_(first|second|third|fourth|fifth)_fs/.exec(src); if (m) tagOf.set(s, m[1]); return ss.call(this, s, src); };
  const at = P.attachShader; P.attachShader = function (p, s) { if (tag(s)) { tagOf.set(p, tag(s)); progOf.set(s, p); } return at.call(this, p, s); };
  const lp = P.linkProgram; P.linkProgram = function (p) { if (tag(p)) ev.push(["link", tag(p)]); return lp.call(this, p); };
  const gp = P.getProgramParameter; P.getProgramParameter = function (p, k) {
    if (k === 0x91B1 && ${fake}) { const n = (asked.get(p) || 0) + 1; asked.set(p, n); if (tag(p)) ev.push(["done?", tag(p), n > 1]); return n > 1; }
    if (k === 0x91B1 && tag(p)) ev.push(["done?", tag(p), null]);
    if (k === this.LINK_STATUS && tag(p)) ev.push(["status", tag(p)]);
    return gp.call(this, p, k);
  };
  const gs = P.getShaderParameter; P.getShaderParameter = function (s, k) { if (k === this.COMPILE_STATUS && tag(s)) ev.push(["status", tag(s)]); return gs.call(this, s, k); };
  if (${fake}) { const ge = P.getExtension; P.getExtension = function (n) { return n === "KHR_parallel_shader_compile" ? { COMPLETION_STATUS_KHR: 0x91B1 } : ge.call(this, n); }; }
  const log = console.log; console.log = function (...a) { const t = a.join(" "); if (/^lazy /.test(t)) ev.push(["log", t]); return log.apply(this, a); };
})();`;
for (const fake of [false, true]) {
  const how = fake ? "with parallel compiling" : "without parallel compiling";
  await browse("file://" + join(tmp, "lazy_shaders.html"), async (c) => {
    let ev = [];
    for (let t = Date.now(); Date.now() - t < 20000; await sleep(50)) {
      ev = (await c.ev("window.__lz")) || [];
      if (ev.some((e) => e[0] === "log" && /^lazy drawn fourth/.test(e[1]))) break;
    }
    const at = (line) => ev.findIndex((e) => e[0] === "log" && e[1].startsWith(line));
    const lines = ev.filter((e) => e[0] === "log").map((e) => e[1]);
    const links = (before) => ev.slice(0, before < 0 ? 0 : before).filter((e) => e[0] === "link").map((e) => e[1]).join(",");
    const made = at("lazy made"), first = at("lazy drawn first"), one = at("lazy warm one"), all = at("lazy warm all"), last = at("lazy drawn second");
    const again = at("lazy again"), later = at("lazy warm later"), end = at("lazy drawn fourth");
    const ok = made >= 0 && first > made && one > first && all > one && last > all && again > last && later > again && end > later;
    expect(`${how}: the page's shaders are made, drawn, warmed up and drawn`, ok && lines.join("|") ===
      ["lazy made 3", "lazy drawn first 255,0,0 pending 2", `lazy warm one ${fake ? 2 : 1}`, "lazy warm all 0", "lazy drawn second 0,255,0 third 0,0,255 pending 0",
       "lazy again 1 1 drawn 0,255,0 pending 1", "lazy warm later 0", "lazy drawn fourth 255,255,0 fifth 0,255,255 pending 0"].join("|"), lines.join(" | ") || c.log.slice(0, 300));
    if (!fake) {
      expect("a shader is linked at its first draw, not when made", ok && links(made) === "" && links(first) === "first", `made: [${links(made)}], first drawn: [${links(first)}]`);
      expect("warm_up_shaders links the oldest waiting first, then all", ok && links(one) === "first,second" && links(all) === "first,second,third", `one: [${links(one)}], all: [${links(all)}]`);
    } else {
      const early = ev.slice(0, one).filter((e) => e[0] === "status" && e[1] !== "first");
      const polled = ev.slice(0, one).filter((e) => e[0] === "done?").map((e) => e[1]);
      expect("with parallel compiling: every program queued starts linking when made", ok && links(made) === "first,second,third", `made: [${links(made)}]`);
      expect("a limited warm-up asks no status before the link is done", ok && early.length === 0 && polled.includes("second") && polled.includes("third"),
        early.length ? `asked early: ${early.map((e) => e[1]).join(",")}` : `completion asked of ${[...new Set(polled)].join(",")}`);
    }
    // (warm = false: left out of the warm-ups until queued by warm_up_later or made again with
    // warm; made again from the same source: the program made before, not linked again)
    expect(`${how}: a shader made with warm = false waits for no warm-up, and one made again links nothing`,
      ok && links(again) === (fake ? "first,second,third,fourth" : "first,second,third") && links(later) === "first,second,third,fourth" && links(ev.length) === "first,second,third,fourth,fifth",
      `before made again: [${links(again)}], after warm_up_later's warm-up: [${links(later)}], in all: [${links(ev.length)}]`);
  }, lazyHook(fake));
}
// (every program's links, by its stages' shader functions, in order with the page's lines)
const linkHook = `(() => {
  const ev = window.__lk = [];
  const P = WebGL2RenderingContext.prototype, fn = new Map(), stages = new Map();
  const ss = P.shaderSource; P.shaderSource = function (s, src) { const m = /sloppy shader: (\\w+)/.exec(src); if (m) fn.set(s, m[1]); return ss.call(this, s, src); };
  const at = P.attachShader; P.attachShader = function (p, s) { const l = stages.get(p) || []; l.push(fn.get(s) || "?"); stages.set(p, l); return at.call(this, p, s); };
  const lp = P.linkProgram; P.linkProgram = function (p) { ev.push(["link", (stages.get(p) || []).join("+")]); return lp.call(this, p); };
  const log = console.log; console.log = function (...a) { const t = a.join(" "); if (/^lazy3d /.test(t)) ev.push(["log", t]); return log.apply(this, a); };
})();`;
await browse("file://" + join(tmp, "lazy_shaders3d.html"), async (c) => {
  let ev = [];
  for (let t = Date.now(); Date.now() - t < 20000; await sleep(50)) {
    ev = (await c.ev("window.__lk")) || [];
    if (ev.some((e) => e[0] === "log" && /^lazy3d done/.test(e[1]))) break;
  }
  const lines = ev.filter((e) => e[0] === "log").map((e) => e[1]);
  const links = ev.filter((e) => e[0] === "link").map((e) => e[1]);
  const twice = links.filter((l, i) => links.indexOf(l) !== i);
  const unused = links.filter((l) => /shadow|_inst/.test(l));
  expect("3D with shadows off and no instanced 3D draw: no shadow or instanced program queued or linked", lines.join("|") ===
    ["lazy3d start pending 4", "lazy3d pending 0", "lazy3d warm all 0", "lazy3d made again pending 0", "lazy3d done pending 0"].join("|") && unused.length === 0 && links.some((l) => /^lit_vs\+/.test(l)),
    `${lines.join(" | ") || c.log.slice(0, 300)}; linked: ${links.join(", ")}`);
  expect("a view made again (its shaders, meshes and instance buffers) links no program twice", lines.length === 5 && twice.length === 0 &&
    links.filter((l) => /^vw_vs\+/.test(l)).length === 2, twice.length ? `linked again: ${twice.join(", ")}` : `${links.length} programs, each once`);
}, linkHook);
// (the sound going out: an analyser fed what the page's worklet gives the speakers)
const tapHook = `(() => {
  const c = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (d, ...a) {
    if (typeof AudioWorkletNode !== "undefined" && this instanceof AudioWorkletNode && d instanceof AudioDestinationNode) {
      const an = this.context.createAnalyser(); an.fftSize = 2048; c.call(this, an); window.__tap = an;
    }
    return c.call(this, d, ...a);
  };
})();`;
const level = "(() => { const a = window.__tap; if (!a) return 0; const d = new Float32Array(a.fftSize); a.getFloatTimeDomainData(d); let m = 0; for (const x of d) m = Math.max(m, Math.abs(x)); return m; })()";
for (const [where, path, want] of [["cross-origin isolated", "/iso/tone.html", "ring"], ["not isolated (as on GitHub Pages)", "/tone.html", "messages"]]) {
  await browse(http + path, async (c) => {
    await sleep(1500);
    const how = await c.ev("sloppy.audioPath()");
    const m0 = await c.ev("window.__made"), t0 = Date.now();
    await sleep(2000);
    const m1 = await c.ev("window.__made"), secs = (Date.now() - t0) / 1000;
    const per = ((m1["audio chunks"] || 0) - (m0["audio chunks"] || 0)) / secs;
    const loud = await c.ev(level);
    if (want === "ring") expect(`${where}: sound through a shared ring, no message per chunk`, how === "ring" && per === 0 && loud > 0.1, `${how}, ${per.toFixed(1)} messages a second, level ${loud.toFixed(2)}`);
    else expect(`${where}: sound by messages, one a chunk`, how === "messages" && per > 10 && per < 60 && loud > 0.1, `${how}, ${per.toFixed(1)} messages a second, level ${loud.toFixed(2)}`);
  }, tapHook);
}
server.close();
rmSync(tmp, { recursive: true, force: true });
console.log(failed ? `${failed} failed` : "web performance: all checks passed");
process.exit(failed ? 1 : 0);

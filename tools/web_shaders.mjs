// Link the library programs and the unused-240-row regression through real Chromium/ANGLE.
// The static webglbudget.py gate enforces portable limits; getParameter is never spoofed.
// usage: node tools/web_shaders.mjs chrome page.html workdir
import { spawn } from "node:child_process";
const [chrome, page, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--mute-audio",
  "--remote-debugging-port=0", `--user-data-dir=${dir}/shaders`, "--window-size=128,128", "about:blank"],
  { stdio: ["ignore", "ignore", "pipe"] });
let err = "", ws, failed = 0;
b.stderr.on("data", (d) => { err += d; });
const expect = (what, ok, detail = "") => {
  console.log(`${ok ? "ok  " : "FAIL"} ${what}${detail ? ": " + detail : ""}`);
  if (!ok) failed++;
};
try {
  const start = Date.now();
  while (!/DevTools listening on (ws:\S+)/.test(err)) {
    if (Date.now() - start > 15000) throw Error("no browser: " + err);
    await sleep(50);
  }
  const port = new URL(err.match(/DevTools listening on (ws:\S+)/)[1]).port;
  const target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((x) => x.type === "page");
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const waits = new Map(), lines = [], errors = [];
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (waits.has(msg.id)) { waits.get(msg.id)(msg); waits.delete(msg.id); }
    if (msg.method === "Runtime.consoleAPICalled") lines.push(msg.params.args.map((a) => a.value).join(" "));
    if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
  });
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (expression) => {
    const reply = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (reply.result?.exceptionDetails) throw Error(reply.result.exceptionDetails.exception?.description);
    return reply.result?.result.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Page.addScriptToEvaluateOnNewDocument", { source: `
    window.shaderLinks = [];
    window.shaderPrograms = new Map();
    const original = WebGL2RenderingContext.prototype.linkProgram;
    WebGL2RenderingContext.prototype.linkProgram = function(p) {
      original.call(this, p);
      const sources = this.getAttachedShaders(p).map(s => this.getShaderSource(s));
      const uniforms = [];
      if (this.getProgramParameter(p, this.LINK_STATUS)) {
        for (let i = 0; i < this.getProgramParameter(p, this.ACTIVE_UNIFORMS); i++) {
          const u = this.getActiveUniform(p, i); uniforms.push({name:u.name, size:u.size});
        }
      }
      shaderPrograms.set(p, sources.join(" "));
      shaderLinks.push({ok:this.getProgramParameter(p, this.LINK_STATUS), sources, uniforms});
      window.shaderGL = this;
    };
    // Read within the draw call, before the browser discards the default framebuffer.
    const draw = WebGL2RenderingContext.prototype.drawArrays;
    WebGL2RenderingContext.prototype.drawArrays = function(...args) {
      draw.apply(this, args);
      const pixel = new Uint8Array(4);
      this.readPixels(this.drawingBufferWidth >> 1, this.drawingBufferHeight >> 1, 1, 1, this.RGBA, this.UNSIGNED_BYTE, pixel);
      window.shaderPixel = Array.from(pixel);
      const sources = shaderPrograms.get(this.getParameter(this.CURRENT_PROGRAM)) || "";
      if (/f_budget_fs_/.test(sources)) window.budgetPixel = Array.from(pixel);
      if (/f_nested_budget_fs_/.test(sources)) window.nestedBudgetPixel = Array.from(pixel);
    };
  ` });
  await send("Page.navigate", { url: "file://" + page });
  const until = async (marker) => {
    const start = Date.now();
    while (!lines.some((l) => l.includes(marker))) {
      if (errors.length) throw Error(errors.join("\n"));
      if (Date.now() - start > 20000) throw Error("no " + marker + ": " + lines.join("\n"));
      await sleep(50);
    }
  };
  await until("shader startup ready");
  await sleep(300);
  const startup = await ev("shaderLinks");
  expect("ordinary lighting, PBR, sky, post, particles and palette link", startup.length >= 14 && startup.every((p) => p.ok), `${startup.length} programs`);
  expect("skeletal programs are lazy", !startup.some((p) => p.sources.some((s) => /uniform[^;]*\[192\]/.test(s))));
  expect("unused 240-row field is absent", startup.some((p) => p.sources.some((s) => /f_budget_fs_/.test(s))) && !startup.some((p) => p.sources.some((s) => /\[240\]/.test(s))));
  expect("independent color uniform uploads and draws green", JSON.stringify(await ev("budgetPixel")) === "[0,255,0,255]", JSON.stringify(await ev("budgetPixel")));
  expect("nested paths, uniform arrays, ordinary copies and mutable helpers draw green", JSON.stringify(await ev("nestedBudgetPixel")) === "[0,255,0,255]", JSON.stringify(await ev("nestedBudgetPixel")));
  console.log("ANGLE limits: " + JSON.stringify(await ev(`(() => {
    const g = shaderGL; return Object.fromEntries(["MAX_VERTEX_UNIFORM_VECTORS", "MAX_FRAGMENT_UNIFORM_VECTORS", "MAX_VARYING_VECTORS", "MAX_TEXTURE_IMAGE_UNITS", "MAX_VERTEX_ATTRIBS"].map(k => [k,g.getParameter(g[k])]));
  })()`)));
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "s", code: "KeyS" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "s", code: "KeyS" });
  await until("shader skin ready");
  const all = await ev("shaderLinks");
  expect("first skin load links four skeletal programs", all.length === startup.length + 4 && all.every((p) => p.ok), `${all.length - startup.length} new programs`);
  const skin = all.filter((p) => p.sources.some((s) => /uniform[^;]*\[192\]/.test(s)));
  expect("all 64 joints remain active in vertices", skin.length === 4 && skin.every((p) => p.uniforms.some((u) => u.size === 192)));
  expect("no fragment declares bones", all.every((p) => p.sources.filter((s) => !/gl_Position\s*=/.test(s)).every((s) => !/\[192\]/.test(s))));
  const diagnostics = await ev(`(() => {
    const buffer = new ArrayBuffer(8192), bytes = new Uint8Array(buffer), enc = new TextEncoder();
    const layer = sloppy.extra.find(x => x.imports?.toString().includes("glCreateProgramFrom"));
    const imports = layer.imports(() => ({buffer}), () => ({}));
    imports.__web_gpu_init();
    const proto = WebGL2RenderingContext.prototype;
    const shaderLog = proto.getShaderInfoLog, programLog = proto.getProgramInfoLog;
    proto.getShaderInfoLog = () => ""; proto.getProgramInfoLog = () => "";
    const vs = "#version 300 es\\n// sloppy shader: diagnostic_vertex\\nprecision highp float;\\nout vec2 mismatch;\\nvoid main(){mismatch=vec2(1);gl_Position=vec4(0,0,0,1);}";
    const fs = "#version 300 es\\n// sloppy shader: diagnostic_fragment\\nprecision highp float;\\nin vec3 mismatch;\\nout vec4 color;\\nvoid main(){color=vec4(mismatch,1);}";
    const reports = [];
    try {
      for (const v of [vs, vs.replace("void main", "broken main")]) {
        const vb = enc.encode(v), fb = enc.encode(fs); bytes.set(vb, 0); bytes.set(fb, 4096);
        try { imports.glCreateProgramFrom(0, vb.length, 4096, fb.length); reports.push("unexpected success"); }
        catch (e) { reports.push(e.message); }
      }
    } finally { proto.getShaderInfoLog = shaderLog; proto.getProgramInfoLog = programLog; }
    return reports;
  })()`);
  expect("empty link and compile logs retain shader identities and GPU limits", diagnostics.length === 2 &&
    diagnostics[0].startsWith("link error") && diagnostics[1].startsWith("shader compile error") &&
    diagnostics.every((s) => ["diagnostic_vertex", "diagnostic_fragment", "--- vertex ---", "--- fragment ---", "--- program ---",
      "(empty driver log)", "MAX_FRAGMENT_UNIFORM_VECTORS=", "--- vertex source ---", "--- fragment source ---"].every((x) => s.includes(x))));
  expect("no browser exceptions", !errors.length, errors.join("\n"));
} catch (e) {
  failed++; console.error("FAIL shader page: " + e.stack);
} finally {
  ws?.close(); b.kill();
}
process.exit(failed ? 1 : 0);

// A page's picture in headless Chromium (WebGL2 through ANGLE's SwiftShader), after it has drawn
// for a while: written as a PNG for webtest.py to compare with a render scene's reference. Fails
// on a browser exception or a WebGL error the browser reports (a feedback loop, say).
// usage: node tools/web_render.mjs chrome page.html out.png width height workdir
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
const [chrome, page, out, width, height, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--mute-audio",
  "--remote-debugging-port=0", `--user-data-dir=${dir}/render`, `--window-size=${width},${height}`, "about:blank"],
  { stdio: ["ignore", "ignore", "pipe"] });
let err = "", ws, failed = 0;
b.stderr.on("data", (d) => { err += d; });
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
  const waits = new Map(), problems = [];
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (waits.has(msg.id)) { waits.get(msg.id)(msg); waits.delete(msg.id); }
    if (msg.method === "Runtime.exceptionThrown") problems.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
    if (msg.method === "Runtime.consoleAPICalled") {
      const text = msg.params.args.map((a) => a.value).join(" ");
      if (/WebGL|panic/.test(text)) problems.push(text);
    }
    if (msg.method === "Log.entryAdded" && /WebGL|GL_INVALID|[Ff]eedback/.test(msg.params.entry.text)) problems.push(msg.params.entry.text);
  });
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  await send("Runtime.enable");
  await send("Log.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: +width, height: +height, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: "file://" + page });
  await sleep(2500);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(out, Buffer.from(shot.result.data, "base64"));
  if (problems.length) { failed++; console.log("FAIL " + page + ": " + problems.join("\n")); }
} catch (e) {
  failed++; console.error("FAIL " + page + ": " + e.stack);
} finally {
  ws?.close(); b.kill();
}
process.exit(failed ? 1 : 0);

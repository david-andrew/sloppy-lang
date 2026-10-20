// A web page (tests/web/audio_clock.jo) with sound: the audio clock read each frame for a few
// seconds after a click starts it, against a straight line (smooth, never back, at the speed of
// time), the output's latency, and key presses timed from the events. The page runs in headless
// Chromium, driven over its DevTools protocol.
// usage: node tools/web_audio.mjs chrome page.html workdir
import { spawn } from "node:child_process";

const [chrome, page, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;

const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${dir}/audio`, "--window-size=400,300", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
let err = "";
b.stderr.on("data", (d) => { err += d; });
const t0 = Date.now();
while (!/DevTools listening on (ws:\S+)/.test(err)) { if (Date.now() - t0 > 15000) throw new Error("no browser"); await sleep(50); }
const port = new URL(err.match(/DevTools listening on (ws:\S+)/)[1]).port;
const target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((x) => x.type === "page");
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const waits = {}, lines = [];
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waits[msg.id]) waits[msg.id](msg.result || msg.error);
  if (msg.method === "Runtime.consoleAPICalled") lines.push(msg.params.args.map((a) => a.value).join(" "));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result.value;
const said = (what) => lines.filter((l) => l.startsWith(what + ":")).map((l) => l.slice(what.length + 1));
const expect = (what, ok, got) => {
  if (ok) console.log(`ok   ${what} (${got})`);
  else { failed++; console.log(`FAIL ${what}: ${got}`); }
};
try {
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Page.navigate", { url: "file://" + page });
  const t1 = Date.now();
  while (Date.now() - t1 < 15000) { await sleep(100); if (await ev("!!document.getElementById('sloppy-canvas') && document.readyState === 'complete'")) break; }
  await sleep(500);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: 100, y: 100, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 100, y: 100, button: "left", clickCount: 1 });
  await sleep(4000);
  for (let k = 0; k < 3; k++) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "d", code: "KeyD" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "d", code: "KeyD" });
    await sleep(150);
  }
  const pts = said("clock").map((l) => l.split(":").map(Number));
  // (from a second after it starts: the clock has its first reports by then)
  const t = pts.filter((p) => p[1] > 1.0);
  expect("the clock runs once a click starts the sound", t.length > 60, `${pts.length} frames read it, ${t.length} after its first second`);
  if (t.length > 60) {
    let back = 0;
    for (let i = 1; i < t.length; i++) if (t[i][1] < t[i - 1][1]) back++;
    expect("it never goes back", back === 0, `${back} times`);
    // a straight line through (time, audio_time)
    const n = t.length, mx = t.reduce((s, p) => s + p[0], 0) / n, my = t.reduce((s, p) => s + p[1], 0) / n;
    let sxy = 0, sxx = 0;
    for (const p of t) { sxy += (p[0] - mx) * (p[1] - my); sxx += (p[0] - mx) ** 2; }
    const slope = sxy / sxx;
    let ss = 0, worst = 0;
    for (const p of t) { const r = p[1] - (my + slope * (p[0] - mx)); ss += r * r; worst = Math.max(worst, Math.abs(r)); }
    const std = Math.sqrt(ss / n);
    expect("at the speed of time", Math.abs(slope - 1) < 0.01, `slope ${slope.toFixed(4)}`);
    expect("smooth: under 1 ms off a straight line", std < 0.001, `std ${(std * 1000).toFixed(3)} ms, worst ${(worst * 1000).toFixed(3)} ms`);
    const lat = t[t.length - 1][2];
    expect("a latency the page reports", lat > 0.005 && lat < 0.5, `${(lat * 1000).toFixed(1)} ms`);
  }
  const presses = said("press").map((l) => l.split(":").map(Number));
  expect("presses counted, each timed from its event, before the frame that sees it", presses.length === 3 && presses.every((p) => p[0] === 1 && p[1] >= 0 && p[1] < 0.1),
    JSON.stringify(presses.map((p) => [p[0], +(p[1] * 1000).toFixed(2)])));
} finally {
  ws.close();
  b.kill();
}
process.exit(failed ? 1 : 0);

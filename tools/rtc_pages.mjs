// WebRTC between two web pages (tests/net/invite_page.jo, built for the web), each in a
// browser of its own (Chromium over its DevTools protocol, Firefox over WebDriver BiDi, by the
// path's name): one invites, the other joins with the code, and the reply comes back after
// REPLY_DELAY ms (a player pasting it in a while later: a page must not give up meanwhile).
// usage: node tools/rtc_pages.mjs inviter-browser joiner-browser page.html workdir
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
const [browserA, browserB, page, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(f, ms, what) { const t0 = Date.now(); while (Date.now() - t0 < ms) { const v = f(); if (v) return v; await sleep(50); } throw new Error("timed out waiting for " + what); }
let firefox = false;
// (Firefox: headless, it has no WebGL; on a display of its own, from Xvfb, it has)
async function xvfb() {
  try {
    const x = spawn("Xvfb", ["-displayfd", "3", "-screen", "0", "1280x800x24", "-nolisten", "tcp"], { stdio: ["ignore", "ignore", "ignore", "pipe"] });
    x.on("error", () => {});
    let n = "";
    x.stdio[3].on("data", (d) => { n += d; });
    await until(() => /\d+\n/.test(n) || x.exitCode !== null, 5000, "Xvfb");
    return /\d+\n/.test(n) ? { display: ":" + n.trim(), kill: () => x.kill() } : null;
  } catch (e) { return null; }
}
const xdisplay = await xvfb();

// a browser and its page, the page's console lines collected: navigate(url), evaluate(js)
async function browser(chrome, profile) {
  firefox = path.basename(chrome).startsWith("firefox");
  fs.mkdirSync(profile, { recursive: true });
  const args = firefox
    ? [...(xdisplay ? [] : ["--headless"]), "--no-remote", "--profile", profile, "--remote-debugging-port", "0", "about:blank"]
    : ["--no-sandbox", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"];
  // (never the desktop's own display)
  const env = { ...process.env };
  for (const k of ["DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "EGL_PLATFORM"]) delete env[k];
  if (xdisplay) { env.DISPLAY = xdisplay.display; env.GDK_BACKEND = "x11"; }
  const b = spawn(chrome, args, { stdio: ["ignore", "pipe", "pipe"], env });
  let err = "";
  b.stderr.on("data", (d) => { err += d; });
  b.stdout.on("data", (d) => { err += d; });
  const listening = firefox ? /WebDriver BiDi listening on (ws:\/\/\S+)/ : /DevTools listening on (ws:\/\/\S+)/;
  const wsUrl = await until(() => (err.match(listening) || [])[1], 20000, "the browser");
  const ws = new WebSocket(firefox ? wsUrl + "/session" : (await (await fetch(`http://127.0.0.1:${new URL(wsUrl).port}/json`)).json()).find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const lines = [], waits = {};
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && waits[msg.id]) waits[msg.id](msg.result);
    if (msg.method === "Runtime.consoleAPICalled") lines.push(msg.params.args.map((a) => a.value).join(" "));
    if (msg.method === "log.entryAdded" && msg.params.text != null) lines.push(msg.params.text);
  });
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  let navigate, evaluate;
  if (firefox) {
    await send("session.new", { capabilities: {} });
    await send("session.subscribe", { events: ["log.entryAdded"] });
    const context = (await send("browsingContext.getTree", {})).contexts[0].context;
    navigate = (url) => send("browsingContext.navigate", { context, url, wait: "none" });
    evaluate = (expression) => send("script.evaluate", { expression, target: { context }, awaitPromise: false });
  } else {
    await send("Runtime.enable");
    navigate = (url) => send("Page.navigate", { url });
    evaluate = (expression) => send("Runtime.evaluate", { expression });
  }
  return { lines, navigate, evaluate, close: () => { ws.close(); b.kill(); } };
}


const url = "file://" + path.resolve(page);
const A = await browser(browserA, dir + "/a");
const B = await browser(browserB, dir + "/b");
try {
  A.navigate(url + "?ROLE=invite");
  const code = await until(() => (A.lines.find((l) => l.startsWith("code:")) || "").slice(5), 20000, "A's code");
  B.navigate(url + "?ROLE=join&CODE=" + encodeURIComponent(code));
  const reply = await until(() => (B.lines.find((l) => l.startsWith("code:")) || "").slice(5), 20000, "B's reply");
  await sleep(Number(process.env.REPLY_DELAY || 0));
  A.evaluate(`history.replaceState(null, "", location.pathname + location.search + "&REPLY=" + encodeURIComponent(${JSON.stringify(reply)}))`);
  await until(() => A.lines.some((l) => l.startsWith("page got:pong")) && B.lines.some((l) => l.startsWith("page got:pong")), 30000, "ping and pong");
  console.log("ok   " + path.basename(browserA) + " invites, " + path.basename(browserB) + " joins");
} catch (e) {
  console.log("FAIL " + path.basename(browserA) + " -> " + path.basename(browserB) + ": " + e.message + "\n  A: " + A.lines.join(" | ").slice(0, 1500) + "\n  B: " + B.lines.join(" | ").slice(0, 1500));
} finally { A.close(); B.close(); if (xdisplay) xdisplay.kill(); }
process.exit(0);

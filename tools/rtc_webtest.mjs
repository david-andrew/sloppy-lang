// WebRTC between a web page (tests/net/invite_page.jo, built for the web) and a native program
// (tests/net/invite_peer.jo), each inviting in turn, the codes passed between them as players
// would; the page runs in a headless browser: Chromium, driven over its DevTools protocol, or
// Firefox (a path ending in "firefox"), over WebDriver BiDi.
// usage: node tools/rtc_webtest.mjs browser page.html native-program workdir
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const [chrome, page, native, dir] = process.argv.slice(2);
const firefox = path.basename(chrome).startsWith("firefox");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;

async function until(f, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const v = f();
    if (v) return v;
    await sleep(50);
  }
  throw new Error("timed out waiting for " + what);
}

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
const xdisplay = firefox ? await xvfb() : null;

// a browser and its page, the page's console lines collected: navigate(url), evaluate(js)
async function browser(profile) {
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

async function scenario(nativeInvites) {
  const work = path.join(dir, nativeInvites ? "a" : "b");
  fs.rmSync(work, { recursive: true, force: true });
  fs.mkdirSync(work, { recursive: true });
  const env = { ...process.env, DIR: work, ROLE: nativeInvites ? "invite" : "join" };
  const br = await browser(path.join(work, "profile"));
  let nat = null, natOut = "";
  const startNative = () => {
    nat = spawn(native, [], { env, stdio: ["ignore", "pipe", "pipe"] });
    nat.stdout.on("data", (d) => { natOut += d; });
    nat.stderr.on("data", (d) => { natOut += d; });
  };
  const url = "file://" + path.resolve(page);
  try {
    if (nativeInvites) {
      startNative();
      const code = await until(() => fs.existsSync(path.join(work, "code.txt")) && fs.readFileSync(path.join(work, "code.txt"), "utf8"), 15000, "the native code");
      br.navigate(`${url}?ROLE=join&CODE=${encodeURIComponent(code)}`);
      const reply = await until(() => (br.lines.find((l) => l.startsWith("code:")) || "").slice(5), 15000, "the page's reply");
      fs.writeFileSync(path.join(work, "reply.txt"), reply);
    } else {
      br.navigate(`${url}?ROLE=invite`);
      const code = await until(() => (br.lines.find((l) => l.startsWith("code:")) || "").slice(5), 15000, "the page's code");
      fs.writeFileSync(path.join(work, "code.txt"), code);
      startNative();
      const reply = await until(() => fs.existsSync(path.join(work, "reply.txt")) && fs.readFileSync(path.join(work, "reply.txt"), "utf8"), 15000, "the native reply");
      br.evaluate(`history.replaceState(null, "", location.pathname + location.search + "&REPLY=" + encodeURIComponent(${JSON.stringify(reply)}))`);
    }
    await until(() => br.lines.includes("page got:pong from native") && natOut.includes("native got:pong from the page"), 20000, "ping and pong both ways");
    console.log(`ok   WebRTC${firefox ? " (Firefox)" : ""}: ${nativeInvites ? "a native program invites, a web page joins" : "a web page invites, a native program joins"}`);
  } catch (e) {
    failed++;
    console.log(`FAIL WebRTC${firefox ? " in Firefox" : ""} (${nativeInvites ? "native invites" : "page invites"}): ${e.message}\n  page: ${br.lines.join(" | ")}\n  native: ${natOut.trim().replace(/\n/g, " | ")}`);
  } finally {
    br.close();
    if (nat) nat.kill();
  }
}

await scenario(true);
await scenario(false);
if (xdisplay) xdisplay.kill();
process.exit(failed ? 1 : 0);

// Rollback rejoining in web pages: two pages (tests/net/rejoin_page.jo, built for the web) play
// through a relay (tests/net/rejoin_relay.jo, native), straight to each other with WebRTC once they
// can; player 1's page is reloaded partway, and comes back into the game with the token it saved
// in the browser's storage. Both must then have the same game, straight to each other again.
// Chromium, driven over its DevTools protocol.
// usage: node tools/web_rejoin.mjs chromium page.html relay-program workdir
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const [chrome, page, relay, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function until(f, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const v = f();
    if (v) return v;
    await sleep(50);
  }
  throw new Error("timed out waiting for " + what);
}

// a browser and its page, the page's console lines collected: navigate(url)
async function browser(profile) {
  fs.mkdirSync(profile, { recursive: true });
  const env = { ...process.env };
  for (const k of ["DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "EGL_PLATFORM"]) delete env[k];
  const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"], { stdio: ["ignore", "pipe", "pipe"], env });
  let err = "";
  b.stderr.on("data", (d) => { err += d; });
  b.stdout.on("data", (d) => { err += d; });
  const wsUrl = await until(() => (err.match(/DevTools listening on (ws:\/\/\S+)/) || [])[1], 20000, "the browser");
  const target = (await (await fetch(`http://127.0.0.1:${new URL(wsUrl).port}/json`)).json()).find((t) => t.type === "page");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const lines = [], waits = {};
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && waits[msg.id]) waits[msg.id](msg.result);
    if (msg.method === "Runtime.consoleAPICalled") lines.push(msg.params.args.map((a) => a.value).join(" "));
  });
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  await send("Runtime.enable");
  return { lines, navigate: (url) => send("Page.navigate", { url }), close: () => { ws.close(); b.kill(); } };
}

fs.rmSync(dir, { recursive: true, force: true });
fs.mkdirSync(dir, { recursive: true });
const portFile = path.join(dir, "port");
const r = spawn(relay, [], { env: { ...process.env, NET_PORT: "0", NET_PORT_FILE: portFile }, stdio: ["ignore", "ignore", "ignore"] });
const pages = [];
let failed = 0;
try {
  const port = await until(() => fs.existsSync(portFile) && fs.readFileSync(portFile, "utf8"), 15000, "the relay's port");
  const url = (p) => `file://${path.resolve(page)}?NET_PORT=${port}&PLAYER=${p}&AT=900`;
  for (const p of [0, 1]) {
    pages.push(await browser(path.join(dir, `profile${p}`)));
    pages[p].navigate(url(p));
  }
  await until(() => pages[1].lines.includes("page 1: token saved") && pages[1].lines.includes("page 1: played 300"), 60000, "page 1 to play with its token saved");
  // (reloaded: the page starts again, its game and session gone, its saved token kept)
  const before = pages[1].lines.length;
  pages[1].navigate(url(1));
  await until(() => pages[1].lines.slice(before).includes("page 1: coming back"), 20000, "page 1 to start again");
  const hashes = await until(() => {
    const h = pages.map((b) => b.lines.find((l) => /^page \d: hash /.test(l)));
    return h.every((x) => x) && h;
  }, 90000, "both pages' games after it came back");
  const same = hashes[0].slice(7) === hashes[1].slice(7) && hashes[0].endsWith("desync -1, problem ''");
  if (same && pages[0].lines.includes("page 0: player 1 came back")) console.log("ok   netplay: a web page reloaded in a relay room comes back into the game (in Chromium)");
  else {
    failed++;
    console.log(`FAIL netplay: a web page reloaded in a relay room comes back: ${hashes.join(" / ")}`);
  }
} catch (e) {
  failed++;
  console.log(`FAIL netplay: a web page reloaded in a relay room comes back: ${e.message}\n  page 0: ${(pages[0] || { lines: [] }).lines.join(" | ")}\n  page 1: ${(pages[1] || { lines: [] }).lines.join(" | ")}`);
} finally {
  for (const b of pages) b.close();
  r.kill();
}
process.exit(failed ? 1 : 0);

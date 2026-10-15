// WebRTC between a web page (tests/net/invite_page.jo, built for the web) and a native program
// (tests/net/invite_peer.jo), each inviting in turn, the codes passed between them as players
// would; the page runs in headless Chromium, driven over its DevTools protocol.
// usage: node tools/rtc_webtest.mjs chrome page.html native-program workdir
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const [chrome, page, native, dir] = process.argv.slice(2);
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

// a browser and its page, the page's console lines collected
async function browser(profile) {
  const b = spawn(chrome, ["--no-sandbox", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
  let err = "";
  b.stderr.on("data", (d) => { err += d; });
  const wsUrl = await until(() => (err.match(/DevTools listening on (ws:\/\/\S+)/) || [])[1], 15000, "the browser");
  const port = new URL(wsUrl).port;
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const lines = [];
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (msg.method === "Runtime.consoleAPICalled") lines.push(msg.params.args.map((a) => a.value).join(" "));
  });
  const send = (method, params = {}) => ws.send(JSON.stringify({ id: ++id, method, params }));
  send("Runtime.enable");
  return { b, lines, send, close: () => { ws.close(); b.kill(); } };
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
      br.send("Page.navigate", { url: `${url}?ROLE=join&CODE=${encodeURIComponent(code)}` });
      const reply = await until(() => (br.lines.find((l) => l.startsWith("code:")) || "").slice(5), 15000, "the page's reply");
      fs.writeFileSync(path.join(work, "reply.txt"), reply);
    } else {
      br.send("Page.navigate", { url: `${url}?ROLE=invite` });
      const code = await until(() => (br.lines.find((l) => l.startsWith("code:")) || "").slice(5), 15000, "the page's code");
      fs.writeFileSync(path.join(work, "code.txt"), code);
      startNative();
      const reply = await until(() => fs.existsSync(path.join(work, "reply.txt")) && fs.readFileSync(path.join(work, "reply.txt"), "utf8"), 15000, "the native reply");
      br.send("Runtime.evaluate", { expression: `history.replaceState(null, "", location.pathname + location.search + "&REPLY=" + encodeURIComponent(${JSON.stringify(reply)}))` });
    }
    await until(() => br.lines.includes("page got:pong from native") && natOut.includes("native got:pong from the page"), 20000, "ping and pong both ways");
    console.log(`ok   WebRTC: ${nativeInvites ? "a native program invites, a web page joins" : "a web page invites, a native program joins"}`);
  } catch (e) {
    failed++;
    console.log(`FAIL WebRTC (${nativeInvites ? "native invites" : "page invites"}): ${e.message}\n  page: ${br.lines.join(" | ")}\n  native: ${natOut.trim().replace(/\n/g, " | ")}`);
  } finally {
    br.close();
    if (nat) nat.kill();
  }
}

await scenario(true);
await scenario(false);
process.exit(failed ? 1 : 0);

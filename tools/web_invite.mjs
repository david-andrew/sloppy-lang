// Two web pages (tests/web/invite_ui.jo) connected through lib/invite.jo's screens, clicked
// through as two players would: one chooses Invite a friend, its link (read from its clipboard)
// is opened in the other browser, which joins by itself; its reply code (from its clipboard) is
// pasted into the first page's box, and Connect. Both must connect and hear each other.
// usage: node tools/web_invite.mjs chrome page.html workdir
import { spawn } from "node:child_process";

const [chrome, page, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;

async function open(name) {
  const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${dir}/${name}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
  let err = "";
  b.stderr.on("data", (d) => { err += d; });
  const t0 = Date.now();
  while (!/DevTools listening on (ws:\S+)/.test(err)) { if (Date.now() - t0 > 15000) throw new Error("no browser"); await sleep(50); }
  const wsUrl = err.match(/DevTools listening on (ws:\S+)/)[1];
  // (the clipboard, to read what the page copied)
  const bws = new WebSocket(wsUrl);
  await new Promise((r) => bws.addEventListener("open", r));
  bws.send(JSON.stringify({ id: 1, method: "Browser.grantPermissions", params: { permissions: ["clipboardReadWrite", "clipboardSanitizedWrite"] } }));
  const t = (await (await fetch(`http://127.0.0.1:${new URL(wsUrl).port}/json`)).json()).find((x) => x.type === "page");
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const waits = {}, lines = [];
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && waits[msg.id]) waits[msg.id](msg.result || msg.error);
    if (msg.method === "Runtime.consoleAPICalled") lines.push(msg.params.args.map((a) => a.value).join(" "));
  });
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  const click = async (x, y) => {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    await sleep(200);
  };
  const clip = async () => (await send("Runtime.evaluate", { expression: "navigator.clipboard.readText()", awaitPromise: true, returnByValue: true })).result?.value || "";
  const paste = (text) => send("Runtime.evaluate", { expression: `(() => { const d = new DataTransfer(); d.setData("text/plain", ${JSON.stringify(text)}); document.activeElement.dispatchEvent(new ClipboardEvent("paste", { clipboardData: d, bubbles: true })); })()` });
  return { send, click, clip, paste, lines, close: () => { ws.close(); bws.close(); b.kill(); } };
}

const until = async (f, ms) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { const v = await f(); if (v) return v; await sleep(200); } return null; };
const A = await open("a"), B = await open("b");
try {
  await A.send("Page.navigate", { url: "file://" + page });
  await sleep(2000);
  await A.click(640, 323);                                       // Invite a friend
  const link = await until(async () => { const c = await A.clip(); return typeof c === "string" && c.includes("?invite=") && c; }, 15000);
  if (!link) throw new Error("no invite link was copied");
  await B.send("Page.navigate", { url: link });
  const reply = await until(async () => { const c = await B.clip(); return typeof c === "string" && c && !c.includes("?invite=") && c; }, 20000);
  if (!reply) throw new Error("the friend's page copied no reply code");
  await A.click(640, 462);                                       // the reply box
  await A.paste(reply);
  await sleep(200);
  await A.click(640, 527);                                       // Connect
  const ok = await until(() => A.lines.includes("got: hello from the friend") && B.lines.includes("got: hello from the inviter"), 20000);
  if (!ok || !A.lines.includes("connected: inviter true") || !B.lines.includes("connected: inviter false")) throw new Error(`not connected: inviter's page said ${JSON.stringify(A.lines)}, the friend's ${JSON.stringify(B.lines)}`);
  console.log("ok   two web pages through the invite screens (a link, a reply code, Connect)");
  // (on one machine the browsers connect straight to each other, and say so)
  const routed = await until(() => A.lines.includes("route: direct") && B.lines.includes("route: direct"), 10000);
  if (!routed) throw new Error(`net.route: the inviter's page said ${JSON.stringify(A.lines.filter((l) => l.startsWith("route")))}, the friend's ${JSON.stringify(B.lines.filter((l) => l.startsWith("route")))}`);
  console.log("ok   net.route says direct in both pages");
} catch (e) {
  failed++;
  console.log(`FAIL two web pages through the invite screens: ${e.message}`);
} finally {
  A.close(); B.close();
}
process.exit(failed ? 1 : 0);

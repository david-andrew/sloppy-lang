// Web pages (tests/web/invite_ui.jo) connected through a room of a matchmaking server
// (tools/rendezvous.jo, at ws://127.0.0.1:port), clicked through as players would: one page
// chooses Invite a friend and copies its room's link; after a reload the link must be the same;
// the other browser opens it and both connect. Then: the friend opening the link while the host's
// page is closed is told so, and joins once the host is back; the same program built for this
// computer joins a page's room by its code (ROOM=); and with the server out of reach, the page
// says so and Invite with a code instead still makes an invite. Then two pages choose Play with
// anybody: the first hosts a public room, the second is put in it; and a browser with WebRTC
// turned off (as Firefox's media.peerconnection.enabled = false: no RTCPeerConnection) says so.
// usage: node tools/web_room.mjs chrome page.html port native_build workdir
// (ROOM_PAGE_QUERY=SLOPPY_RTC_RELAY_ONLY=1: each page's address has it too; ROOM_STEPS=2: the
// first two steps only; ROOM_SERVER=wss://host: a server already running, as a deployed one)
import { spawn } from "node:child_process";

const [chrome, page, port, native, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const server = process.env.ROOM_SERVER || `ws://127.0.0.1:${port}`;
const extra = process.env.ROOM_PAGE_QUERY ? "&" + process.env.ROOM_PAGE_QUERY : "";
const steps = Number(process.env.ROOM_STEPS || 7);
let done = 0;
let failed = 0;

async function open(name) {
  const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${dir}/${name}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
  let err = "";
  b.stderr.on("data", (d) => { err += d; });
  const t0 = Date.now();
  while (!/DevTools listening on (ws:\S+)/.test(err)) { if (Date.now() - t0 > 15000) throw new Error("no browser"); await sleep(50); }
  const wsUrl = err.match(/DevTools listening on (ws:\S+)/)[1];
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
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  const click = async (x, y) => {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    await sleep(200);
  };
  const clip = async () => (await send("Runtime.evaluate", { expression: "navigator.clipboard.readText()", awaitPromise: true, returnByValue: true })).result?.value || "";
  const go = async (url) => { lines.length = 0; await send("Runtime.evaluate", { expression: "navigator.clipboard.writeText('')", awaitPromise: true }); await send("Page.navigate", { url }); await sleep(2000); };
  return { send, click, clip, go, lines, close: () => { ws.close(); bws.close(); b.kill(); } };
}

const until = async (f, ms) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { const v = await f(); if (v) return v; await sleep(200); } return null; };
const said = (p, text) => p.lines.some((l) => l.includes(text));
const step = async (name, f) => {
  if (done++ >= steps) return;
  try { await f(); console.log(`ok   web room: ${name}`); }
  catch (e) { failed++; console.log(`FAIL web room: ${name}: ${e.message}`); }
};
const A = await open("room_a"), B = await open("room_b");
const home = `file://${page}?server=${server}${extra}`;
// the host's page: Invite a friend, and its room's link
const host = async () => {
  await A.go(home);
  await A.click(640, 323);                                       // Invite a friend
  const link = await until(async () => { const c = await A.clip(); return c.includes("?room=") && c; }, 15000);
  if (!link) throw new Error(`no room link was copied: the page said ${JSON.stringify(A.lines)}`);
  return link;
};
let link = "";
try {
  await step("a page's room keeps its link after a reload", async () => {
    link = await host();
    const again = await host();
    if (again !== link) throw new Error(`${link} before, ${again} after`);
  });
  await step("a friend's page joins by the link", async () => {
    await B.go(link + extra);
    const ok = await until(() => said(A, "got: hello from the friend") && said(B, "got: hello from the inviter"), 20000);
    if (!ok || !said(A, "connected: inviter true") || !said(B, "connected: inviter false")) throw new Error(`not connected: the host's page said ${JSON.stringify(A.lines)}, the friend's ${JSON.stringify(B.lines)}`);
  });
  await step("the host's page closed: the friend is told, and joins once it is back", async () => {
    await A.go("about:blank");
    await B.go(link);
    if (!await until(() => said(B, "|wait host"), 10000)) throw new Error(`the friend's page said ${JSON.stringify(B.lines)}`);
    if (await host() !== link) throw new Error("another link");
    const ok = await until(() => said(A, "got: hello from the friend") && said(B, "got: hello from the inviter"), 20000);
    if (!ok) throw new Error(`not connected: the host's page said ${JSON.stringify(A.lines)}, the friend's ${JSON.stringify(B.lines)}`);
  });
  await step("a native program joins a page's room by its code", async () => {
    await B.go("about:blank");
    await host();
    const code = link.match(/room=(\w+)/)[1];
    const env = { ...process.env, SLOPPY_SOFTWARE: "1", SLOPPY_NO_AUDIO: "1", SLOPPY_FRAMES: "1800", SLOPPY_SERVER: server, ROOM: code, SLOPPY_SAVE_DIR: `${dir}/native` };
    delete env.DISPLAY; delete env.WAYLAND_DISPLAY;
    const n = spawn(native, [], { env, stdio: ["ignore", "pipe", "pipe"] });
    let out = "";
    n.stdout.on("data", (d) => { out += d; });
    n.stderr.on("data", (d) => { out += d; });
    const ok = await until(() => said(A, "got: hello from the friend") && out.includes("got: hello from the inviter"), 30000);
    n.kill();
    if (!ok) throw new Error(`not connected: the page said ${JSON.stringify(A.lines)}, the program ${JSON.stringify(out)}`);
  });
  await step("the server out of reach: said, and Invite with a code instead works", async () => {
    await A.go(`file://${page}?server=ws://127.0.0.1:${Number(port) + 1}`);
    await A.click(640, 323);
    if (!await until(() => said(A, "cannot be reached"), 15000)) throw new Error(`the page said ${JSON.stringify(A.lines)}`);
    await A.click(800, 502);                                     // Invite with a code instead
    const inv = await until(async () => { const c = await A.clip(); return c.includes("?invite=") && c; }, 15000);
    if (!inv) throw new Error("no invite link was copied");
  });
  await step("two pages play with anybody: the first hosts, the second is put in its room", async () => {
    await A.go(home);
    await A.click(640, 416);                                     // Play with anybody
    if (!await until(() => said(A, "hosts the public room true"), 15000)) throw new Error(`the first page said ${JSON.stringify(A.lines)}`);
    await B.go(home);
    await B.click(640, 416);
    const ok = await until(() => said(A, "got: hello from the friend") && said(B, "got: hello from the inviter"), 20000);
    if (!ok) throw new Error(`not connected: the first page said ${JSON.stringify(A.lines)}, the second ${JSON.stringify(B.lines)}`);
  });
  await step("a browser with WebRTC turned off says so", async () => {
    await B.go("about:blank");
    await A.send("Page.addScriptToEvaluateOnNewDocument", { source: "delete window.RTCPeerConnection; delete window.webkitRTCPeerConnection;" });
    await A.go(home);
    await A.click(640, 323);                                     // Invite a friend
    if (!await until(() => said(A, "the screen says: This browser has WebRTC turned off"), 10000)) throw new Error(`the page said ${JSON.stringify(A.lines)}`);
  });
} finally {
  A.close(); B.close();
}
process.exit(failed ? 1 : 0);

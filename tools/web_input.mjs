// A text field in a web page (tests/web/text_field.jo) typed in as on a phone, with touches and
// the phone keyboard's input, and as on a computer, with the mouse, keys and ctrl+V; the page
// runs in headless Chromium, driven over its DevTools protocol.
// usage: node tools/web_input.mjs chrome page.html workdir
import { spawn } from "node:child_process";

const [chrome, page, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;

async function session(touch, profile, run) {
  const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--window-size=800,600", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
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
  await send("Runtime.enable");
  if (touch) await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await send("Page.navigate", { url: "file://" + page });
  const t1 = Date.now();
  while (!lines.length && Date.now() - t1 < 15000) { await ev("0"); await sleep(100); if (await ev("!!document.getElementById('sloppy-canvas') && document.readyState === 'complete'")) break; }
  await sleep(1000);
  const value = () => (lines.filter((l) => l.startsWith("value:")).pop() || "value:").slice(6);
  const active = () => ev("document.activeElement ? document.activeElement.tagName : ''");
  const expect = (what, got, want) => {
    if (got === want) console.log(`ok   ${what}`);
    else { failed++; console.log(`FAIL ${what}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); }
  };
  try { await run({ send, ev, value, active, expect }); }
  finally { ws.close(); b.kill(); }
}

// (the page's 800x600 pixels are 1280x960 of the screen's units, 120 cut off above and below:
// the field, at 20..420 x 20..60, is at 12..262 x 87..113)
await session(true, dir + "/touch", async ({ send, ev, value, active, expect }) => {
  const tap = async (x, y) => {
    await send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
    await sleep(80);
    await send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await sleep(150);
  };
  await tap(100, 100);
  expect("a tapped text field brings up the phone's keyboard", await active(), "INPUT");
  await send("Input.insertText", { text: "hello" });
  await sleep(150);
  expect("typed on the phone's keyboard", value(), "hello");
  // (its backspace: the input loses a character, with no key event)
  await ev(`(() => { const k = document.activeElement; k.value = k.value.slice(0, -1); k.dispatchEvent(new InputEvent("input", { inputType: "deleteContentBackward" })); })()`);
  await sleep(150);
  expect("the phone keyboard's backspace", value(), "hell");
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "x", code: "KeyX", text: "x" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "x", code: "KeyX" });
  await sleep(150);
  expect("a key on a keyboard plugged into the phone", value(), "hellx");
  await ev(`navigator.clipboard.readText = async () => "PASTED\\nsecond line"`);
  await tap(248, 100);
  await sleep(150);
  expect("the Paste button (the clipboard's first line)", value(), "hellxPASTED");
  await tap(400, 400);
  expect("a tap elsewhere puts the keyboard away", await active(), "CANVAS");
  await send("Input.insertText", { text: "zz" });
  await sleep(150);
  expect("typing goes nowhere then", value(), "hellxPASTED");
});

await session(false, dir + "/mouse", async ({ send, ev, value, active, expect }) => {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 100, y: 100 });
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: 100, y: 100, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 100, y: 100, button: "left", clickCount: 1 });
  await sleep(150);
  expect("a clicked text field keeps the keyboard on the page", await active(), "CANVAS");
  for (const c of "abc") {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: c, code: "Key" + c.toUpperCase(), text: c });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: c, code: "Key" + c.toUpperCase() });
  }
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });
  await sleep(150);
  expect("typed on a computer's keyboard", value(), "ab");
  await ev(`(() => { const d = new DataTransfer(); d.setData("text/plain", "CLIP"); document.activeElement.dispatchEvent(new ClipboardEvent("paste", { clipboardData: d, bubbles: true })); })()`);
  await sleep(150);
  expect("ctrl+V", value(), "abCLIP");
});
process.exit(failed ? 1 : 0);

// A text field in a web page (tests/web/text_field.jo) typed in as on a phone, with touches and
// the phone keyboard's input, and as on a computer, with the mouse, keys and ctrl+V; a list of
// buttons tapped and dragged; a phone turned over and back. The page runs in headless Chromium,
// driven over its DevTools protocol.
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
  const said = (what) => lines.filter((l) => l.startsWith(what + ":")).map((l) => l.slice(what.length + 1));
  const active = () => ev("document.activeElement ? document.activeElement.tagName : ''");
  const expect = (what, got, want) => {
    if (got === want) console.log(`ok   ${what}`);
    else { failed++; console.log(`FAIL ${what}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); }
  };
  try { await run({ send, ev, value, said, active, expect }); }
  finally { ws.close(); b.kill(); }
}

// (the page's 800x600 pixels are 1280x960 of the screen's units, 120 cut off above and below:
// the field, at 20..420 x 20..60, is at 12..262 x 87..113)
await session(true, dir + "/touch", async ({ send, ev, value, said, active, expect }) => {
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
  // (the keyboard put away by the player, as by its own key: the field lets go, and a key typed
  // after goes nowhere)
  await tap(100, 100);
  await ev("document.activeElement.blur()");
  await sleep(150);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "q", code: "KeyQ", text: "q" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "q", code: "KeyQ" });
  await sleep(150);
  expect("the keyboard put away lets go of the field", value(), "hellxPASTED");
  // (the list: rows 50 units apart from y 200, 31.25 pixels from 200; a tap on a row presses it as
  // the finger lifts, a drag that starts on one scrolls the list instead)
  await tap(100, 214);
  expect("a tapped button is pressed", said("pressed").join(","), "0");
  const drag = async (x, y0, y1) => {
    await send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y: y0 }] });
    for (let i = 1; i <= 8; i++) { await sleep(20); await send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x, y: y0 + (y1 - y0) * i / 8 }] }); }
    await send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await sleep(600);
  };
  await drag(100, 276, 140);
  expect("a drag begun on a button presses nothing", said("pressed").join(","), "0");
  const off = Number(said("scrolled").pop() || 0);
  expect("a drag begun on a button scrolls the list", off >= 100, true);
  // (a phone turned sideways and back: the page is not left zoomed out)
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true });
  await sleep(300);
  await send("Emulation.setDeviceMetricsOverride", { width: 844, height: 390, deviceScaleFactor: 3, mobile: true, screenOrientation: { type: "landscapePrimary", angle: 90 } });
  await sleep(300);
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true, screenOrientation: { type: "portraitPrimary", angle: 0 } });
  await sleep(500);
  expect("a phone turned over and back is not zoomed out", await ev("[visualViewport.scale, document.getElementById('sloppy-canvas').clientWidth].join(' ')"), "1 390");
});

await session(false, dir + "/mouse", async ({ send, ev, value, active, expect }) => {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 100, y: 100 });
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: 100, y: 100, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 100, y: 100, button: "left", clickCount: 1 });
  await sleep(150);
  expect("a clicked text field keeps the keyboard on the page (its hidden textarea)", await active(), "TEXTAREA");
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
  // (the caret: home, then typing there; ctrl+A, then typing over it all)
  const key = async (k, code, vk, mods = 0, text = undefined) => {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: k, code, windowsVirtualKeyCode: vk, modifiers: mods, text });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: k, code, windowsVirtualKeyCode: vk, modifiers: mods });
  };
  await key("Home", "Home", 36);
  await sleep(100);
  await key("Z", "KeyZ", 90, 8, "Z");
  await sleep(150);
  expect("home, then typing at the caret", value(), "ZabCLIP");
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Control", code: "ControlLeft", windowsVirtualKeyCode: 17, modifiers: 2 });
  await key("a", "KeyA", 65, 2);
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Control", code: "ControlLeft", windowsVirtualKeyCode: 17 });
  await sleep(100);
  await key("q", "KeyQ", 81, 0, "q");
  await sleep(150);
  expect("ctrl+A, then typing over it", value(), "q");
});
process.exit(failed ? 1 : 0);

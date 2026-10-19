// A web page (tests/web/desktop.jo) used as on a computer: text typed through an input method
// (a composition) and from the emoji panel, files dropped on the canvas and chosen in the
// browser's file picker, the pointer's shape, and no frames while nothing happens
// (redraw_on_input). The page runs in headless Chromium, driven over its DevTools protocol.
// usage: node tools/web_desktop.mjs chrome page.html workdir
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const [chrome, page, dir] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;

const b = spawn(chrome, ["--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${dir}/desktop`, "--window-size=800,600", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
let err = "";
b.stderr.on("data", (d) => { err += d; });
const t0 = Date.now();
while (!/DevTools listening on (ws:\S+)/.test(err)) { if (Date.now() - t0 > 15000) throw new Error("no browser"); await sleep(50); }
const port = new URL(err.match(/DevTools listening on (ws:\S+)/)[1]).port;
const target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((x) => x.type === "page");
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const waits = {}, lines = [], choosers = [];
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waits[msg.id]) waits[msg.id](msg.result || msg.error);
  if (msg.method === "Runtime.consoleAPICalled") lines.push(msg.params.args.map((a) => a.value).join(" "));
  if (msg.method === "Page.fileChooserOpened") choosers.push(msg.params);
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result.value;
const said = (what) => lines.filter((l) => l.startsWith(what + ":")).map((l) => l.slice(what.length + 1));
const frames = () => said("frame").length;
const expect = (what, got, want) => {
  if (got === want) console.log(`ok   ${what}`);
  else { failed++; console.log(`FAIL ${what}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); }
};
try {
  await send("Runtime.enable");
  await send("Page.enable");
  await send("DOM.enable");
  await send("Page.setInterceptFileChooserDialog", { enabled: true });
  await send("Page.navigate", { url: "file://" + page });
  const t1 = Date.now();
  while (Date.now() - t1 < 15000) { await sleep(100); if (await ev("!!document.getElementById('sloppy-canvas') && document.readyState === 'complete'")) break; }
  await sleep(1000);

  // (nothing happening: no frames; the mouse moving: a few)
  const f0 = frames();
  await sleep(1000);
  expect("no frames while nothing happens", frames() - f0 <= 1, true);
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 600, y: 300 });
  await sleep(300);
  const f1 = frames();
  expect("the mouse moving draws frames", f1 - f0 >= 1, true);
  expect("the pointer's shape (a hand right of the middle)", await ev("document.getElementById('sloppy-canvas').style.cursor"), "pointer");
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 100, y: 300 });
  await sleep(300);
  expect("and the arrow left of it", await ev("document.getElementById('sloppy-canvas').style.cursor"), "");

  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: 100, y: 100, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 100, y: 100, button: "left", clickCount: 1 });
  await sleep(200);
  expect("a click puts the typing focus on the page's hidden textarea", await ev("document.activeElement.tagName"), "TEXTAREA");
  for (const c of "ab") {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: c, code: "Key" + c.toUpperCase(), text: c });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: c, code: "Key" + c.toUpperCase() });
  }
  await sleep(200);
  expect("keys typed arrive once each", said("typed").join(""), "ab");
  await send("Input.insertText", { text: "😀" });
  await sleep(200);
  expect("an emoji from the system's panel", said("typed").pop(), "😀");
  // (an input method: the composition shown as it is typed, then committed)
  await send("Input.imeSetComposition", { text: "にほん", selectionStart: 3, selectionEnd: 3 });
  await sleep(150);
  const during = said("typed").length;
  await send("Input.insertText", { text: "日本" });
  await sleep(200);
  expect("nothing arrives while it is composed", during, 3);
  expect("an input method's text, once committed", said("typed").slice(3).join(""), "日本");

  // files dropped on the canvas
  await ev(`(() => {
    const d = new DataTransfer();
    d.items.add(new File(["hello"], "dropped.txt"));
    d.items.add(new File(["ab"], "second.md"));
    document.getElementById("sloppy-canvas").dispatchEvent(new DragEvent("drop", { dataTransfer: d, bubbles: true, cancelable: true }));
  })()`);
  await sleep(400);
  expect("files dropped on the canvas, read into the page's files", said("dropped").join(","), "dropped.txt:5,second.md:2");

  // the file picker, opened by a key (o)
  writeFileSync(dir + "/chosen.txt", "chosen!");
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "o", code: "KeyO", text: "o" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "o", code: "KeyO" });
  await sleep(500);
  expect("a key opens the file picker", choosers.length, 1);
  if (choosers.length) {
    expect("for several files of the types asked for", choosers[0].mode, "selectMultiple");
    await send("DOM.setFileInputFiles", { files: [dir + "/chosen.txt"], backendNodeId: choosers[0].backendNodeId });
    await sleep(500);
    expect("the file chosen, read into the page's files", said("opened").join(" "), "chosen.txt:7");
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "o", code: "KeyO", text: "o" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "o", code: "KeyO" });
    await sleep(500);
    await ev(`document.querySelector("input[type=file]").dispatchEvent(new Event("cancel"))`);
    await sleep(300);
    expect("the picker cancelled: no files", said("opened").length === 2 && said("opened")[1] === "", true);
  }
  const f2 = frames();
  await sleep(1000);
  expect("no frames once it is all done", frames() - f2 <= 1, true);
} finally { ws.close(); b.kill(); }
process.exit(failed ? 1 : 0);

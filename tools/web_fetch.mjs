// Local HTTP server and headless Chromium/CDP, as in web_desktop.mjs. No desktop or audio.
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
const [chrome, dir] = process.argv.slice(2);
let pool = 0, peak = 0, retries = 0, aborted = 0;
const server = http.createServer((req, res) => {
  const path = new URL(req.url, "http://test").pathname;
  const reply = (status, body, extra = {}) => { res.writeHead(status, { "Content-Length": Buffer.byteLength(body), ...extra }); res.end(body); };
  if (path === "/fetch_tasks.html" || path === "/fetch_poll.html") return reply(200, fs.readFileSync(dir + path), { "Content-Type": "text/html" });
  if (path === "/hello") return reply(200, "hello", { "X-Reply": "yes" });
  if (path === "/binary") return reply(200, Buffer.from([0, 255, 1, 128]));
  if (path === "/redirect") return reply(302, "", { Location: "/hello" });
  if (path === "/echo") {
    let body = "";
    req.setEncoding("utf8"); req.on("data", (b) => body += b);
    req.on("end", () => reply(200, [req.method, req.headers["x-test"] || "", req.headers["content-type"], body].join("|")));
    return;
  }
  if (path === "/stream" || path === "/chunked") {
    res.writeHead(200, path === "/stream" ? { "Content-Length": 12 } : {});
    res.write("abc");
    const a = setTimeout(() => res.write("def"), 120);
    const b = setTimeout(() => res.end(path === "/stream" ? "ghijkl" : ""), 240);
    res.on("close", () => { clearTimeout(a); clearTimeout(b); });
    return;
  }
  if (path === "/hang_body") { res.writeHead(200, { "Content-Length": 100 }); res.write("a"); res.on("close", () => aborted++); return; }
  if (path === "/hang") { res.on("close", () => aborted++); return; }
  if (path.startsWith("/pool/")) {
    pool++; peak = Math.max(peak, pool);
    const timer = setTimeout(() => reply(200, path.slice(-1)), 150);
    res.on("close", () => { pool--; clearTimeout(timer); });
    return;
  }
  if (path === "/retry") return ++retries === 1 ? reply(503, "busy") : reply(200, "retried");
  if (path === "/allow_noheaders") { res.writeHead(200, { "Access-Control-Allow-Origin": "*" }); res.write("no headers"); res.end(); return; }
  if (path === "/allow") return reply(200, "cors", { "Access-Control-Allow-Origin": "*" });
  reply(404, "missing");
});
let port;
for (port = 9700; port < 9800; port++) {
  try { await new Promise((resolve, reject) => { server.once("error", reject); server.listen(port, "0.0.0.0", () => { server.removeListener("error", reject); resolve(); }); }); break; }
  catch (e) { if (e.code !== "EADDRINUSE") throw e; }
}
if (port === 9800) throw new Error("no free port in 9700-9799");
let b, ws;
try {
  b = spawn(chrome, ["--no-sandbox", "--mute-audio", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${dir}/browser`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"], env: { ...process.env, DISPLAY: "", WAYLAND_DISPLAY: "" } });
  const endpoint = await new Promise((resolve, reject) => {
    let err = "";
    const timer = setTimeout(() => reject(new Error("no Chromium DevTools endpoint: " + err)), 15000);
    b.on("error", reject);
    b.stderr.on("data", (d) => { err += d; const m = err.match(/DevTools listening on (ws:\S+)/); if (m) { clearTimeout(timer); resolve(m[1]); } });
  });
  const target = (await (await fetch(`http://127.0.0.1:${new URL(endpoint).port}/json`)).json()).find((t) => t.type === "page");
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve) => ws.addEventListener("open", resolve));
  let id = 0, passed, failed;
  const pending = new Map(), lines = [];
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id) { const p = pending.get(msg.id); pending.delete(msg.id); if (p) msg.error ? p.reject(new Error(JSON.stringify(msg.error))) : p.resolve(msg.result); }
    if (msg.method === "Runtime.consoleAPICalled") {
      const line = msg.params.args.map((a) => a.value || a.description || "").join(" ");
      lines.push(line);
      if (line.startsWith("PASS page")) passed?.(line);
      if (line.startsWith("panic:")) failed?.(new Error(line));
    }
    if (msg.method === "Runtime.exceptionThrown") failed?.(new Error(JSON.stringify(msg.params.exceptionDetails)));
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => { pending.set(++id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); });
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Page.addScriptToEvaluateOnNewDocument", { source: "window.beats=0; setInterval(()=>window.beats++,20); if(location.pathname.endsWith('/fetch_poll.html')) { WebAssembly.Suspending=undefined; WebAssembly.promising=undefined; }" });
  for (const page of ["fetch_tasks", "fetch_poll"]) {
    lines.length = 0;
    let timer;
    const result = new Promise((resolve, reject) => {
      passed = resolve; failed = reject;
      timer = setTimeout(() => reject(new Error(page + " timed out: " + lines.join(" | "))), 25000);
    });
    try {
      await send("Page.navigate", { url: `http://127.0.0.1:${port}/${page}.html?PORT=${port}` });
      console.log("ok   " + await result);
      const r = await send("Runtime.evaluate", { expression: "window.beats", returnByValue: true });
      if (r.result.value < 2) throw new Error("page event loop did not run");
    } finally { clearTimeout(timer); passed = failed = null; }
  }
  if (peak !== 2 || retries !== 2 || aborted < 2) throw new Error(`server observations: pool peak=${peak}, retries=${retries}, aborted=${aborted}`);
  console.log("ok   concurrent limit, retries, aborts, and responsive page event loop");
} catch (e) { console.error("FAIL browser fetch: " + e.stack); process.exitCode = 1; }
finally { ws?.close(); b?.kill(); server.closeAllConnections(); server.close(); }

// Checks that web pages decode base64 without building an intermediate array of characters
// (Uint8Array.from(atob(s), f) left ~490 MB of garbage for a 20 MB module, collected later in a
// ~55 ms pause during play). Run: node --expose-gc tools/webdecodecheck.mjs
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
let failed = 0;
const fail = (m) => { console.log("FAIL " + m); failed++; };

// 1. the pattern is gone from everything a page runs
const files = [...readdirSync(join(root, "lib/web")).map((f) => join("lib/web", f)),
  "tools/playground/host.js", "tools/playground/page.html"];
for (const f of files) {
  const lines = readFileSync(join(root, f), "utf8").split("\n");
  lines.forEach((l, i) => { if (/Uint8Array\.from\(\s*atob\(/.test(l) && !l.trim().startsWith("//")) fail(`${f}:${i + 1} decodes base64 through an intermediate array`); });
}

// 2. the runtime's decoder gives the same bytes, with or without Uint8Array.fromBase64
const src = readFileSync(join(root, "lib/web/runtime.js"), "utf8");
const m = src.match(/const sloppyFromBase64 = [\s\S]*?\n};\n/);
if (!m) fail("lib/web/runtime.js has no sloppyFromBase64");
else {
  const decode = new Function(m[0] + "return sloppyFromBase64;")();
  const saved = Uint8Array.fromBase64;
  for (const n of [0, 1, 2, 3, 255, 4096, 100003]) {
    const raw = new Uint8Array(n);
    for (let i = 0; i < n; i++) raw[i] = (i * 2654435761) >>> 24;
    const b64 = Buffer.from(raw).toString("base64");
    for (const native of [false, true]) {
      if (native && !saved) continue;
      Uint8Array.fromBase64 = native ? saved : undefined;
      const got = decode(b64);
      if (got.length !== n || got.some((v, i) => v !== raw[i])) fail(`decode of ${n} bytes (fromBase64 ${native ? "on" : "off"}) differs`);
    }
  }
  Uint8Array.fromBase64 = undefined;
  // 3. decoding 8 MB by the plain loop leaves little garbage (the old way left ~25x its size)
  if (globalThis.gc) {
    const n = 8_000_000, raw = new Uint8Array(n);
    for (let i = 0; i < n; i++) raw[i] = (i * 2654435761) >>> 24;
    const b64 = Buffer.from(raw).toString("base64");
    globalThis.gc();
    const before = process.memoryUsage().heapUsed;
    const bin = decode(b64);
    const left = (process.memoryUsage().heapUsed - before) / 1e6;
    if (bin.length !== n) fail("8 MB decode has the wrong length");
    if (left > 3 * n / 1e6) fail(`decoding 8 MB left ${left.toFixed(0)} MB on the heap`);
    else console.log(`ok   8 MB decode left ${left.toFixed(0)} MB on the heap`);
  }
  Uint8Array.fromBase64 = saved;
}
console.log(failed ? `${failed} failed` : "web base64 decoding: all checks passed");
process.exit(failed ? 1 : 0);

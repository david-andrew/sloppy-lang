// Run a Sloppy-generated .html (wasm target) under node: extracts the script and executes it.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error("no script found"); process.exit(1); }
// the module: base64 text in the page, or (built with --wasm-file) a file beside it
const w = html.match(/<script type="[^"]*" id="sloppy-wasm"(?: data-src="([^"?]*)[^"]*")?>([^<]*)<\/script>/);
if (!w) { console.error("no module found"); process.exit(1); }
const sloppyWasm = new Uint8Array(w[1] ? fs.readFileSync(require("path").join(require("path").dirname(process.argv[2]), decodeURIComponent(w[1]))) : Buffer.from(w[2], "base64"));
const vm = require("vm");
// (the program's files are the real ones; its arguments follow the page's name)
const path = require("path");
const sloppyArgs = [path.basename(process.argv[2]).replace(/\.html$/, "")].concat(process.argv.slice(3));
const ctx = { console, process, Buffer, TextDecoder, TextEncoder, WebAssembly, performance, Proxy, Error, Uint8Array, Object, WebSocket: globalThis.WebSocket, setTimeout, clearTimeout, queueMicrotask, sloppyFs: fs, sloppyArgs, sloppyWasm, crypto: globalThis.crypto,
              fetch: globalThis.fetch, AbortController, Headers, Request, Response, URL };
vm.createContext(ctx);
vm.runInContext(m[1], ctx);

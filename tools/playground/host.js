// The Sloppy compiler, compiled to WebAssembly, run on files kept in memory: the standard library
// (embedded in the page) and the program being edited. It runs in a worker (or, where a page
// cannot start one, on the page itself): each compile gets a fresh instance of the compiler.
//   compile(source, files) -> { ok, html, log, ms }   html: the program, a complete web page
//   (files: name -> Uint8Array, beside the program: a game's icon, its models)
"use strict";
const sloppyHost = (() => {
  let compiler = null;          // WebAssembly.Module
  let lib = null;               // path -> Uint8Array
  const enc = new TextEncoder(), dec = new TextDecoder();

  const fromB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  async function gunzip(bytes) {
    const ds = new DecompressionStream("gzip");
    const out = new Response(new Blob([bytes]).stream().pipeThrough(ds));
    return new Uint8Array(await out.arrayBuffer());
  }

  async function init(wasmGz, libGz) {
    compiler = await WebAssembly.compile(await gunzip(fromB64(wasmGz)));
    const files = JSON.parse(dec.decode(await gunzip(fromB64(libGz))));
    lib = {};
    for (const p of Object.keys(files)) lib[p] = fromB64(files[p]);
  }

  class Exit extends Error { constructor(code) { super("exit " + code); this.code = code; } }

  function compile(source, extra) {
    const t0 = performance.now();
    const files = Object.assign({}, lib);
    for (const n of Object.keys(extra || {})) files["/play/" + n] = extra[n];
    files["/play/main.jo"] = enc.encode(source);
    const args = ["/sloppy/bin/sloppy", "build", "/play/main.jo", "--target", "wasm", "-o", "/play/main"];
    const envVars = { SLOPPY_LIB: "/sloppy/lib" };
    let log = "";
    let mem = null;
    const u8 = () => new Uint8Array(mem.buffer);
    const str = (p, n) => dec.decode(u8().subarray(Number(p), Number(p) + Number(n)));
    function give(b, op, cap) {
      u8().set(b.subarray(0, Math.min(b.length, Number(cap))), Number(op));
      return BigInt(b.length);
    }
    function listDir(path) {
      const seen = new Set();
      for (const f of Object.keys(files)) if (f.startsWith(path + "/")) seen.add(f.slice(path.length + 1).split("/")[0]);
      return seen.size > 0 ? [...seen] : null;
    }
    const sockets = [];
    const env = {
      __wasm_write: (fd, p, n) => { log += str(p, n); },
      // WebSockets (lib/net.jo): poll gives -1 (nothing now), -2 (opened), -3 (closed), or a
      // message's length (written at out when it fits in cap)
      __wasm_ws_open: (p, n) => {
        try {
          const ws = new WebSocket(str(p, n));
          ws.binaryType = "arraybuffer";
          const s = { ws, q: [] };
          ws.onopen = () => s.q.push("open");
          ws.onmessage = (e) => s.q.push(typeof e.data === "string" ? new TextEncoder().encode(e.data) : new Uint8Array(e.data));
          ws.onclose = ws.onerror = () => s.q.push("close");
          sockets.push(s);
          return BigInt(sockets.length - 1);
        } catch (e) { return -1n; }
      },
      __wasm_ws_send: (id, p, n) => {
        const s = sockets[Number(id)];
        if (s && s.ws.readyState === 1) s.ws.send(u8().slice(Number(p), Number(p) + Number(n)));
      },
      __wasm_ws_poll: (id, op, cap) => {
        const s = sockets[Number(id)];
        if (!s || s.q.length === 0) return -1n;
        const x = s.q[0];
        if (x === "open") { s.q.shift(); return -2n; }
        if (x === "close") return -3n;
        if (x.length > Number(cap)) return BigInt(x.length);
        s.q.shift();
        u8().set(x, Number(op));
        return BigInt(x.length);
      },
      __wasm_ws_close: (id) => { const s = sockets[Number(id)]; if (s) s.ws.close(); },
      __wasm_exit: (code) => { throw new Exit(Number(code)); },
      __wasm_now: () => performance.now(),
      __wasm_grow: (n) => BigInt(mem.grow(Number(n))),
      __wasm_env: (np, nn, op, cap) => {
        const v = envVars[str(np, nn)];
        return v === undefined ? -1n : give(enc.encode(v), op, cap);
      },
      __wasm_read_file: (pp, pn, op, cap) => {
        const d = files[str(pp, pn)];
        return d === undefined ? -1n : give(d, op, cap);
      },
      __wasm_write_file: (pp, pn, dp, dn) => {
        files[str(pp, pn)] = u8().slice(Number(dp), Number(dp) + Number(dn));
        return 1n;
      },
      __wasm_list_dir: (pp, pn, op, cap) => {
        const names = listDir(str(pp, pn).replace(/\/+$/, ""));
        return names === null ? -1n : give(enc.encode(names.join("\n")), op, cap);
      },
      __wasm_args: (op, cap) => give(enc.encode(args.join("\0")), op, cap),
      // (the compiler reads no standard input here: it has ended)
      __wasm_read_stdin: (p, n) => -1n,
    };
    let ok = false;
    try {
      const inst = new WebAssembly.Instance(compiler, { env });
      mem = inst.exports.memory;
      inst.exports.__start();
      ok = true;
    } catch (e) {
      if (e instanceof Exit) ok = e.code === 0;
      else log += "internal compiler error: " + (e && e.message || e) + "\n";
    }
    const out = files["/play/main.html"];
    return { ok: ok && out !== undefined, html: out ? dec.decode(out) : "", log, ms: performance.now() - t0 };
  }

  return { init, compile };
})();

// (as a worker: messages {init: [wasm, lib]} and {source})
if (typeof window === "undefined" && typeof self !== "undefined") {
  self.onmessage = async (ev) => {
    const m = ev.data;
    try {
      if (m.init) {
        await sloppyHost.init(m.init[0], m.init[1]);
        self.postMessage({ ready: true });
      } else self.postMessage(Object.assign({ id: m.id }, sloppyHost.compile(m.source, m.files)));
    } catch (e) {
      self.postMessage({ id: m.id, ok: false, html: "", log: "playground error: " + (e && e.message || e) + "\n", ms: 0 });
    }
  };
}

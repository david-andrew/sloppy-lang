// start the program once all runtime modules are registered. Its module is in the page as base64
// text (a script element that is not run), or with `sloppy build --wasm-file` in a file beside
// the page, compiled while it downloads. Either is compiled off the main thread as the page loads,
// and nothing keeps the text or the bytes after: for a big game they are tens of megabytes.
if (typeof window === "undefined") { if (typeof sloppyWasm !== "undefined") sloppy.run(sloppyWasm); }   // (tools/runwasm.js)
else (() => {
  const el = document.getElementById("sloppy-wasm");
  if (!el) return;
  const fail = (e) => { const l = document.getElementById("log"); l.style.display = "block"; l.textContent += "error: " + sloppy.errorText(e) + "\n"; };
  window.addEventListener("error", (ev) => fail(ev.error || ev.message));
  const src = el.getAttribute("data-src");
  const code = src ? sloppyFetchModule(src) : sloppyCompileText(el);
  el.remove();
  code.catch(() => {});                                 // (reported once the page has loaded)
  window.addEventListener("load", () => { try { const r = sloppy.run(code); if (r && r.catch) r.catch(fail); } catch (e) { fail(e); } });
})();

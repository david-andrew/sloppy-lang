// start the program once all runtime modules are registered. Its module is in the page as base64
// text (a script element that is not run), or with `sloppy build --wasm-file` in a file beside
// the page, compiled while it downloads. Either is compiled off the main thread as the page loads,
// and nothing keeps the text or the bytes after: for a big game they are tens of megabytes.
if (typeof window === "undefined") { if (typeof sloppyWasm !== "undefined") sloppy.run(sloppyWasm); }   // (tools/runwasm.js)
else (() => {
  const el = document.getElementById("sloppy-wasm");
  if (!el) return;
  // (and a `sloppy:error` event on window, its detail the text: a page's own overlay may hide #log)
  const fail = (e) => {
    const text = sloppy.errorText(e), l = document.getElementById("log");
    if (l) { l.style.display = "block"; l.textContent += "error: " + text + "\n"; }
    window.dispatchEvent(new CustomEvent("sloppy:error", { detail: text }));
  };
  window.addEventListener("error", (ev) => fail(ev.error || ev.message));
  const src = el.getAttribute("data-src");
  const code = src ? sloppyFetchModule(src) : sloppyCompileText(el);
  el.remove();
  code.catch(() => {});                                 // (reported once the page has loaded)
  window.addEventListener("load", () => { try { const r = sloppy.run(code); if (r && r.catch) r.catch(fail); } catch (e) { fail(e); } });
})();

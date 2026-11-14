// start the program once all runtime modules are registered
if (typeof SLOPPY_WASM !== "undefined") {
  const bin = sloppyFromBase64(SLOPPY_WASM);
  SLOPPY_WASM = null;                                   // (the text is no longer needed: let it go)
  if (typeof window !== "undefined") {
    const fail = (e) => { const l = document.getElementById("log"); l.style.display = "block"; l.textContent += "error: " + sloppy.errorText(e) + "\n"; };
    window.addEventListener("error", (ev) => fail(ev.error || ev.message));
    window.addEventListener("load", () => { try { const r = sloppy.run(bin); if (r && r.catch) r.catch(fail); } catch (e) { fail(e); } });
  } else sloppy.run(bin);
}

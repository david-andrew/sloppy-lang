// WebGL2, canvas, input and frame loop for Sloppy programs running in the browser.
// the share of the canvas's pixels drawn (see start), and the canvas's fitting to the page again
sloppy.res = { scale: 1, fit: null };
sloppy.extra.push({
  imports(getMem, getExports) {
    // views of wasm memory, made again only when the memory grows (no garbage per GL call)
    let vbuf = null, vu8 = null, vf32 = null, vi32 = null;
    const views = () => { const b = getMem().buffer; if (b !== vbuf) { vbuf = b; vu8 = new Uint8Array(b); vf32 = new Float32Array(b); vi32 = new Int32Array(b); } };
    const u8 = () => { views(); return vu8; };
    const f32 = () => { views(); return vf32; };
    const i32 = () => { views(); return vi32; };
    // a view of wasm memory for pixel data of type ty, and p's offset in it
    const pix = (ty) => ty === 0x1406 ? f32() : ty === 0x1404 ? i32() : u8();
    const pixOff = (ty, p) => ty === 0x1406 || ty === 0x1404 ? Number(p) >> 2 : Number(p);
    const bytes = (p, n) => u8().subarray(Number(p), Number(p) + Number(n));
    const text = (p, n) => new TextDecoder().decode(bytes(p, n));
    let gl = null, canvas = null, lockWanted = false, safe = [0, 0, 0, 0], cursorName = "", cursorHidden = false;
    const objs = [null];            // integer handle -> WebGL object
    const add = (o) => { objs.push(o); return objs.length - 1; };
    const get = (h) => objs[h] || null;
    const locs = [null];
    const keymap = {};
    "abcdefghijklmnopqrstuvwxyz".split("").forEach((c, i) => keymap["Key" + c.toUpperCase()] = 1 + i);
    for (let i = 0; i < 10; i++) keymap["Digit" + i] = 27 + i;
    const named = ["Space", "Enter", "Escape", "Tab", "Backspace", "Delete", "Insert", "Home", "End", "PageUp", "PageDown",
      "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Shift", "Control", "Alt", "Meta"];
    named.forEach((n, i) => keymap[n] = 37 + i);
    keymap["ShiftLeft"] = keymap["ShiftRight"] = keymap["Shift"];
    keymap["ControlLeft"] = keymap["ControlRight"] = keymap["Control"];
    keymap["AltLeft"] = keymap["AltRight"] = keymap["Alt"];
    keymap["MetaLeft"] = keymap["MetaRight"] = keymap["Meta"];
    keymap["NumpadEnter"] = keymap["Enter"];
    for (let i = 1; i <= 12; i++) keymap["F" + i] = 55 + i;
    ["Minus", "Equal", "Comma", "Period", "Slash", "Semicolon", "Quote", "BracketLeft", "BracketRight", "Backslash", "Backquote"]
      .forEach((n, i) => keymap[n] = 68 + i);
    // (the number pad, with NumLock on or off: Key.kp0...)
    for (let i = 0; i < 10; i++) keymap["Numpad" + i] = 79 + i;
    ["NumpadDecimal", "NumpadAdd", "NumpadSubtract", "NumpadMultiply", "NumpadDivide"].forEach((n, i) => keymap[n] = 89 + i);
    // the clipboard: a page may read it only as it is pasted
    let clipText = "";
    // (what was pasted: the game hears it in its next frame; pasted into the phone keyboard's
    // input it goes there instead, not as typing)
    let pasted = () => {};
    if (typeof document !== "undefined") document.addEventListener("paste", (e) => {
      clipText = e.clipboardData ? e.clipboardData.getData("text") : "";
      if ((kb && e.target === kb) || (ime && e.target === ime)) e.preventDefault();
      pasted();
    });
    // a phone's keyboard: brought up by an input element that is not seen, while a text field
    // typed in with a finger has the focus (browsers show it only inside a touch: wanted at
    // another time, at the end of the next). What is typed goes to the game as characters and
    // backspaces; the input holds two characters that are not seen, so a backspace with nothing
    // typed still reaches it
    let kb = null, kbWanted = false, kbBase = "", kbBottom = 0;
    const KB_FILL = "\u200b\u200b";
    const kbNow = () => {
      if (!kb) return;
      if (kbWanted && document.activeElement !== kb) { kb.value = kbBase = KB_FILL; kb.focus({ preventScroll: true }); }
      else if (!kbWanted && document.activeElement === kb) { kb.blur(); if (canvas) canvas.focus(); }
    };
    // (the keyboard up over the field typed in: the canvas moved up just enough to show the
    // field above it, its size kept, so the game is not laid out again for a shorter screen)
    const kbPan = () => {
      if (!canvas) return;
      const vv = window.visualViewport;
      let y = 0;
      if (vv && kb && kbWanted && document.activeElement === kb && canvas.clientHeight > 0) {
        const bottom = kbBottom * canvas.clientHeight / canvas.height + 12, seen = vv.offsetTop + vv.height;
        if (bottom > seen) y = Math.min(bottom - seen, Math.max(canvas.clientHeight - seen, 0));
      }
      const t = y > 0 ? "translateY(" + (-Math.round(y)) + "px)" : "";
      if (canvas.style.transform !== t) canvas.style.transform = t;
    };
    // (the clipboard read, written again or shared, at the end of a touch, click or key: browsers
    // allow these only then)
    let pasteWanted = false, copyWanted = false, shareWanted = null;
    const pasteNow = () => {
      if (pasteWanted && navigator.clipboard && navigator.clipboard.readText)
        navigator.clipboard.readText().then((t) => { clipText = t; pasted(); }).catch(() => {});
      if (copyWanted && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(clipText).catch(() => {});
      if (shareWanted !== null && navigator.share) {
        const t = shareWanted.trim();
        // (a link alone goes as one, for the apps that take only links)
        navigator.share(/^https?:\/\/\S+$/.test(t) ? { url: t } : { text: t }).catch(() => {});
      }
      pasteWanted = copyWanted = false;
      shareWanted = null;
    };
    // typing on a computer: a textarea that is not seen has the focus (see canvas_open)
    let ime = null;
    // a user's files (lib/game/files.jo): dropped on the canvas, or chosen in the browser's file
    // picker, each read into the page's files (sloppy.files) under its name; then the program
    // hears of them ("drop", or "open ID", and the names, a line each)
    const fileEvents = [];
    const fileHeard = (what, names) => { fileEvents.push(what + "\n" + names.join("\n")); if (sloppy.wake) sloppy.wake(); };
    const takeFiles = async (list) => {
      const names = [];
      for (const f of list) { sloppy.files[f.name] = new Uint8Array(await f.arrayBuffer()); names.push(f.name); }
      return names;
    };
    // (the picker opens only inside a click, a key or the end of a touch: asked for at another
    // time, at the next one)
    let pickWanted = null;
    const pickNow = () => { const p = pickWanted; pickWanted = null; if (p) p(); };
    const enc = new TextEncoder();
    let fsWanted = false;
    const fsNow = () => {
      if (!fsWanted || !canvas || document.fullscreenElement) { fsWanted = false; return; }
      fsWanted = false;
      const r = canvas.requestFullscreen(); if (r) r.catch(() => {});
    };
    return {
      __web_set_title(tp, tn) { document.title = text(tp, tn); },
      // (browsers allow it only inside a click, key or the end of a touch: asked for at another
      // time, as by a game reading mouse_pressed while a finger is still down, it is made at the
      // next one)
      __web_fullscreen(on) {
        fsWanted = false;
        if (on) {
          if (!canvas || !canvas.requestFullscreen) return;
          if (navigator.userActivation && !navigator.userActivation.isActive) { fsWanted = true; return; }
          const r = canvas.requestFullscreen(); if (r) r.catch(() => { fsWanted = true; });
        }
        else if (document.fullscreenElement) { const r = document.exitFullscreen(); if (r) r.catch(() => {}); }
      },
      __web_can_fullscreen: () => (typeof document !== "undefined" && document.fullscreenEnabled && canvas && canvas.requestFullscreen) ? 1 : 0,
      __web_is_fullscreen: () => (typeof document !== "undefined" && document.fullscreenElement) ? 1 : 0,
      // (browsers grant the lock only during a click: wanted now, it is taken at the next one)
      __web_pointer_lock(on) {
        lockWanted = !!on;
        if (!canvas || !canvas.requestPointerLock) return 0;
        if (on) { try { const r = canvas.requestPointerLock(); if (r && r.catch) r.catch(() => {}); } catch (e) {} }
        else if (document.pointerLockElement === canvas) document.exitPointerLock();
        return 1;
      },
      __web_show_cursor(on) { cursorHidden = !on; if (canvas) canvas.style.cursor = on ? cursorName : "none"; },
      // (set_cursor's shapes, as Cursor numbers them: the browser's cursors)
      __web_set_cursor(k) {
        cursorName = ["", "text", "pointer", "crosshair", "move", "ew-resize", "ns-resize", "nwse-resize", "nesw-resize", "not-allowed", "wait"][k] || "";
        if (canvas && !cursorHidden) canvas.style.cursor = cursorName;
      },
      __web_pointer_locked: () => (typeof document !== "undefined" && canvas && document.pointerLockElement === canvas) ? 1 : 0,
      __web_clipboard_get(out, cap) {
        const b = enc.encode(clipText);
        u8().set(b.subarray(0, cap), Number(out));
        return b.length;
      },
      __web_keyboard(on, bottom) { kbWanted = !!on; kbBottom = bottom; if (!on) kbNow(); kbPan(); },
      // (read at the end of the touch or click that asked: Safari allows it only then)
      __web_paste() { pasteWanted = true; },
      __web_can_share: () => (typeof navigator !== "undefined" && navigator.share) ? 1 : 0,
      // (a finger is the main pointer: a phone or a tablet)
      __web_finger: () => (typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches) ? 1 : 0,
      __web_share(p, n) { shareWanted = text(p, n); },
      // the browser's file picker for open_file_dialog: accept is ".txt,.md" ("": any file); its
      // answer is the names of the files chosen, none when it is cancelled
      __web_file_open(id, ap, an, multiple) {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = text(ap, an);
        input.multiple = !!multiple;
        input.style.display = "none";
        document.body.appendChild(input);
        let done = false;
        const finish = (names) => { if (done) return; done = true; input.remove(); fileHeard("open " + id, names); };
        input.addEventListener("change", () => takeFiles(input.files).then(finish, () => finish([])));
        input.addEventListener("cancel", () => finish([]));
        const open = () => { try { input.click(); } catch (e) { finish([]); } };
        if (navigator.userActivation && !navigator.userActivation.isActive) pickWanted = open;
        else open();
      },
      __web_file_poll(out, cap) {
        if (!fileEvents.length) return -1;
        const b = enc.encode(fileEvents[0]);
        if (b.length <= cap) { u8().set(b, Number(out)); fileEvents.shift(); }
        return b.length;
      },
      // (where a text field typed in is, in the canvas's pixels: an input method shows what it
      // composes, and its choices, beside the textarea, moved there)
      __web_typing_at(y) {
        if (ime && canvas && canvas.height > 0) ime.style.top = Math.max(0, Math.round(y * canvas.clientHeight / canvas.height) - 20) + "px";
      },
      // (the page around the canvas, seen as a phone turns: the color the game clears the screen with)
      __web_page_color(r, g, b) {
        const c = (x) => Math.round(Math.min(Math.max(x, 0), 1) * 255);
        document.documentElement.style.background = document.body.style.background = "rgb(" + c(r) + "," + c(g) + "," + c(b) + ")";
      },
      // (refused, as phones' browsers do outside a touch: tried again at the end of the next one)
      __web_clipboard_set(p, n) {
        clipText = text(p, n);
        copyWanted = false;
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(clipText).catch(() => { copyWanted = true; });
      },
      __web_canvas_open(tp, tn, w, h) {
        document.title = text(tp, tn);
        canvas = document.getElementById("sloppy-canvas");
        // the canvas fills the page (the program sees the new size each frame, as when a window
        // is resized), drawn at the screen's pixel density up to about 2.6 million pixels. Its
        // size is the page's layout (CSS), never pixels the page might not have room for: a
        // phone turned over keeps the page unzoomed, and a phone's keyboard covers part of it
        // (kbPan) rather than shrinking it
        canvas.style.position = "fixed"; canvas.style.left = canvas.style.top = "0";
        canvas.style.width = canvas.style.height = "100%";
        // (the insets of a phone's notch, rounded corners and home bar, for safe_rect: CSS has them)
        const probe = document.createElement("div");
        probe.style.cssText = "position:fixed;left:0;top:0;width:0;height:0;visibility:hidden;pointer-events:none;" +
          "padding:env(safe-area-inset-top,0px) env(safe-area-inset-right,0px) env(safe-area-inset-bottom,0px) env(safe-area-inset-left,0px)";
        document.body.appendChild(probe);
        const fit = () => {
          const cw = Math.max(canvas.clientWidth, 1), ch = Math.max(canvas.clientHeight, 1);
          const top = Math.min(window.devicePixelRatio || 1, Math.sqrt(2.6e6 / Math.max(cw * ch, 1)));
          // (fewer while frames are missed: sloppy.res, in start; never below a pixel a CSS pixel)
          const d = Math.max(Math.min(top, 1), top * sloppy.res.scale);
          const w = Math.max(1, Math.round(cw * d)), h = Math.max(1, Math.round(ch * d));
          if (canvas.width !== w) canvas.width = w;
          if (canvas.height !== h) canvas.height = h;
          const cs = getComputedStyle(probe);
          safe = [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft].map((x) => Math.round(parseFloat(x) || 0));
          kbPan();
        };
        fit(); window.addEventListener("resize", fit);
        sloppy.res.fit = fit;
        // (the keyboard put away by the player, its input still focused: let go of it, so that the
        // next touch on the field brings it back, and the game's field lets go too)
        const vv = window.visualViewport;
        let kbTall = 0, kbShown = false;
        if (vv) {
          vv.addEventListener("resize", () => {
            fit();
            if (!kb || document.activeElement !== kb) return;
            if (vv.height < kbTall * 0.85) kbShown = true;
            else if (kbShown && vv.height > kbTall * 0.95) { kbShown = false; kb.blur(); canvas.focus(); }
          });
          vv.addEventListener("scroll", kbPan);
        }
        document.body.style.overflow = "hidden";
        document.getElementById("log").style.display = "none";
        gl = canvas.getContext("webgl2", { antialias: true, alpha: false, preserveDrawingBuffer: false });
        if (!gl) throw new Error("WebGL2 is not available in this browser");
        const ex = getExports();
        const key = (e, down) => {
          // (keys that compose text in an input method are its: the text arrives once composed)
          if (e.isComposing || e.keyCode === 229) return;
          const k = keymap[e.code] || keymap[e.key];
          // (ctrl+V/C/X stay with the browser, so pasting and copying work; a character typed into
          // the phone keyboard's input, or the computer's textarea, arrives as its text, a dead key
          // (´ then e) as the character it makes)
          const clip = (e.ctrlKey || e.metaKey) && (e.code === "KeyV" || e.code === "KeyC" || e.code === "KeyX");
          const toKb = ((kb && e.target === kb) || (ime && e.target === ime)) && ([...e.key].length === 1 || e.key === "Dead");
          if (k) { ex.__key(k, down ? (e.repeat ? 2 : 1) : 0); if (!clip && !toKb) e.preventDefault(); if (down) held.add(k); else held.delete(k); }
          if (down && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !toKb && ex.__char) ex.__char(e.key.charCodeAt(0));
        };
        pasted = () => { if (ex.__pasted) ex.__pasted(); if (sloppy.wake) sloppy.wake(); };
        kb = document.createElement("input");
        kb.type = "text";
        kb.setAttribute("autocomplete", "off"); kb.setAttribute("autocorrect", "off");
        kb.setAttribute("autocapitalize", "off"); kb.setAttribute("spellcheck", "false");
        kb.setAttribute("enterkeyhint", "done"); kb.setAttribute("aria-hidden", "true");
        // (16px: smaller, and iOS zooms the page to it)
        kb.style.cssText = "position:fixed;left:0;top:0;width:1px;height:1px;opacity:0;font-size:16px;border:0;padding:0;";
        document.body.appendChild(kb);
        const kbSync = () => {
          const v = kb.value;
          let i = 0;
          while (i < kbBase.length && i < v.length && kbBase[i] === v[i]) i++;
          for (let n = kbBase.length - i; n > 0; n--) { ex.__key(keymap["Backspace"], 1); ex.__key(keymap["Backspace"], 0); }
          for (const ch of v.slice(i)) if (ex.__char) ex.__char(ch.codePointAt(0));
          kb.value = kbBase = KB_FILL;
        };
        kb.addEventListener("input", (e) => { if (!e.isComposing) kbSync(); });
        kb.addEventListener("compositionend", kbSync);
        kb.addEventListener("focus", () => { kbTall = vv ? vv.height : 0; kbShown = false; });
        // (put away while the game still wanted it, by the keyboard's own key or the phone's back
        // button: the game's text field lets go of it)
        kb.addEventListener("blur", () => {
          if (kbWanted) { kbWanted = false; if (ex.__keyboard_closed) ex.__keyboard_closed(); }
          kbPan();
        });
        // (keys held when the page loses the focus, as by a click outside an itch.io frame: let
        // go, as the game will not hear them come up)
        const held = new Set();
        const release = () => { for (const k of held) ex.__key(k, 0); held.clear(); };
        window.addEventListener("keydown", (e) => key(e, true));
        window.addEventListener("keyup", (e) => { key(e, false); fsNow(); pasteNow(); pickNow(); });
        const focus = (on) => { if (ex.__focus) ex.__focus(on ? 1 : 0); };
        window.addEventListener("blur", () => { release(); focus(false); });
        window.addEventListener("focus", () => focus(true));
        // (the page closed or left: the game's quit())
        window.addEventListener("pagehide", () => { if (ex.__quit) ex.__quit(); });
        // (a hidden page gets no frames: its sound stops too, until it is shown again)
        document.addEventListener("visibilitychange", () => {
          if (document.hidden) { release(); focus(false); sloppy.pauseAudio && sloppy.pauseAudio(true); }
          else { focus(document.hasFocus()); sloppy.pauseAudio && sloppy.pauseAudio(false); }
        });
        // typing on a computer: a textarea that is not seen has the focus, not the canvas, so that
        // text not typed as one key reaches the program as typed text too: what an input method
        // composes (Japanese, Chinese, Korean), an emoji from the system's panel. Keys still arrive
        // as keys. (A phone's keyboard has its own input, kb: on a touch screen the canvas has the
        // focus.)
        ime = document.createElement("textarea");
        ime.setAttribute("autocomplete", "off"); ime.setAttribute("autocorrect", "off");
        ime.setAttribute("autocapitalize", "off"); ime.setAttribute("spellcheck", "false");
        ime.setAttribute("aria-hidden", "true");
        ime.style.cssText = "position:fixed;left:0;top:0;width:1px;height:1px;opacity:0;border:0;padding:0;resize:none;overflow:hidden;font-size:16px;";
        document.body.appendChild(ime);
        const imeTake = () => {
          const v = ime.value;
          ime.value = "";
          for (const ch of v) if (ch.codePointAt(0) >= 32 && ex.__char) ex.__char(ch.codePointAt(0));
          if (v && sloppy.wake) sloppy.wake();
        };
        ime.addEventListener("input", (e) => { if (!e.isComposing) imeTake(); });
        ime.addEventListener("compositionend", imeTake);
        const coarse = () => typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
        const typingFocus = () => { if (coarse()) canvas.focus(); else ime.focus({ preventScroll: true }); };
        // (a click on the canvas focuses it, after mousedown: the textarea takes the focus back)
        canvas.addEventListener("focus", () => { if (!coarse()) ime.focus({ preventScroll: true }); });
        const pos = (e) => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) * canvas.width / r.width, (e.clientY - r.top) * canvas.height / r.height]; };
        // files dropped on the canvas (dropped_files(): their names); the pointer follows the drag
        canvas.addEventListener("dragover", (e) => {
          e.preventDefault();
          if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
          const p = pos(e); ex.__mouse(0, p[0], p[1], 0);
        });
        canvas.addEventListener("drop", (e) => {
          e.preventDefault();
          const fs = e.dataTransfer ? e.dataTransfer.files : null;
          if (fs && fs.length) takeFiles(fs).then((names) => fileHeard("drop", names));
        });
        // (a file dropped beside the canvas is not opened by the browser in its place)
        window.addEventListener("dragover", (e) => e.preventDefault());
        window.addEventListener("drop", (e) => e.preventDefault());
        canvas.addEventListener("mousemove", (e) => {
          // locked: only how far it moved (in canvas pixels)
          if (document.pointerLockElement === canvas) { const r = canvas.getBoundingClientRect(); ex.__mouse(4, e.movementX * canvas.width / r.width, e.movementY * canvas.height / r.height, 0); return; }
          const p = pos(e); ex.__mouse(0, p[0], p[1], 0);
          if (ex.__touch) ex.__touch(-1, 3, 0, 0);
        });
        const btn = (b) => b === 0 ? 0 : b === 1 ? 1 : 2;
        // (a press let go on a button, a switch, a text field: the game's frame runs at once, inside
        // the touch's or click's end, where browsers allow what the tap does (the keyboard,
        // fullscreen, the clipboard, sharing), not at the next animation frame, after it)
        const tapFrame = () => { if (ex.__tap_pending && ex.__tap_pending() && sloppy.frameNow) sloppy.frameNow(); };
        canvas.addEventListener("mousedown", (e) => {
          typingFocus();
          if (lockWanted && document.pointerLockElement !== canvas && canvas.requestPointerLock) { try { const r = canvas.requestPointerLock(); if (r && r.catch) r.catch(() => {}); } catch (err) {} }
          const p = pos(e); if (document.pointerLockElement !== canvas) ex.__mouse(0, p[0], p[1], 0);
          ex.__mouse(1, 0, 0, btn(e.button)); sloppy.resumeAudio && sloppy.resumeAudio();
          if (ex.__touch) ex.__touch(-1, 3, 0, 0);
        });
        window.addEventListener("mouseup", (e) => { ex.__mouse(2, 0, 0, btn(e.button)); if (e.button === 0) tapFrame(); fsNow(); pasteNow(); pickNow(); });
        canvas.addEventListener("wheel", (e) => { ex.__mouse(3, 0, -Math.sign(e.deltaY), 0); e.preventDefault(); }, { passive: false });
        canvas.addEventListener("contextmenu", (e) => e.preventDefault());
        // touch: the first finger is the mouse with its left button held, pressed where it lands
        // and moved as it slides, so games that take the mouse work on phones (the page does
        // not scroll or zoom under it, and no mouse events are made up from the touches); every
        // finger is in touches()
        canvas.style.touchAction = "none";
        let finger = null;
        const touch = (e, kind) => {
          for (const t of e.changedTouches) {
            const p = pos(t);
            if (ex.__touch) ex.__touch(t.identifier, kind, p[0], p[1]);
            if (kind === 1 && finger === null) {
              finger = t.identifier;
              if (document.activeElement !== kb) canvas.focus();
              ex.__mouse(0, p[0], p[1], 0); ex.__mouse(1, 0, 0, 0);
            } else if (t.identifier === finger) {
              ex.__mouse(0, p[0], p[1], 0);
              if (kind === 2) { ex.__mouse(2, 0, 0, 0); finger = null; sloppy.resumeAudio && sloppy.resumeAudio(); }
            }
          }
          e.preventDefault();
        };
        canvas.addEventListener("touchstart", (e) => touch(e, 1), { passive: false });
        canvas.addEventListener("touchmove", (e) => touch(e, 0), { passive: false });
        canvas.addEventListener("touchend", (e) => { const was = finger; touch(e, 2); if (was !== null && finger === null) tapFrame(); fsNow(); kbNow(); pasteNow(); pickNow(); }, { passive: false });
        canvas.addEventListener("touchcancel", (e) => touch(e, 2), { passive: false });
        // (each key until the sound runs: Safari starts it only inside a key or click handler)
        window.addEventListener("keydown", () => sloppy.resumeAudio && sloppy.resumeAudio());
        typingFocus();
      },
      // GPU arrays: a WebGL 2 context on the page's canvas (the same one a window uses later);
      // 1 if it can render to float textures
      __web_gpu_init() {
        if (typeof document === "undefined") return 0;
        if (!gl) {
          canvas = document.getElementById("sloppy-canvas");
          gl = canvas && canvas.getContext("webgl2", { antialias: true, alpha: false, preserveDrawingBuffer: false });
        }
        return gl && gl.getExtension("EXT_color_buffer_float") ? 1 : 0;
      },
      // (the canvas's pixels, its size in CSS pixels, and the safe area's insets: top, right,
      // bottom, left)
      __web_canvas_size(out) {
        const a = new Int32Array(getMem().buffer, Number(out), 8);
        a[0] = canvas ? canvas.width : 0; a[1] = canvas ? canvas.height : 0;
        a[2] = canvas ? canvas.clientWidth : 0; a[3] = canvas ? canvas.clientHeight : 0;
        for (let i = 0; i < 4; i++) a[4 + i] = safe[i];
      },
      glClearColor: (r, g, b, a) => gl.clearColor(r, g, b, a),
      glClear: (m) => gl.clear(m),
      glViewport: (x, y, w, h) => gl.viewport(x, y, w, h),
      glScissor: (x, y, w, h) => gl.scissor(x, y, w, h),
      glEnable: (c) => gl.enable(c),
      glDisable: (c) => gl.disable(c),
      glBlendFunc: (s, d) => gl.blendFunc(s, d),
      glBlendFuncSeparate: (s, d, sa, da) => gl.blendFuncSeparate(s, d, sa, da),
      glDepthFunc: (f) => gl.depthFunc(f),
      glDepthMask: (f) => gl.depthMask(!!f),
      glCullFace: (m) => gl.cullFace(m),
      glFrontFace: (m) => gl.frontFace(m),
      glColorMask: (r, g, b, a) => gl.colorMask(!!r, !!g, !!b, !!a),
      glCreateBuffer: () => add(gl.createBuffer()),
      glDeleteBuffer: (b) => gl.deleteBuffer(get(b)),
      glBindBuffer: (t, b) => gl.bindBuffer(t, get(b)),
      glBufferData: (t, size, p, usage) => { if (Number(p) === 0) gl.bufferData(t, Number(size), usage); else gl.bufferData(t, u8(), usage, Number(p), Number(size)); },
      glBufferSubData: (t, off, size, p) => gl.bufferSubData(t, Number(off), u8(), Number(p), Number(size)),
      glCreateVertexArray: () => add(gl.createVertexArray()),
      glDeleteVertexArray: (v) => gl.deleteVertexArray(get(v)),
      glBindVertexArray: (v) => gl.bindVertexArray(get(v)),
      glEnableVertexAttribArray: (i) => gl.enableVertexAttribArray(i),
      glDisableVertexAttribArray: (i) => gl.disableVertexAttribArray(i),
      glVertexAttribPointer: (i, size, ty, norm, stride, off) => gl.vertexAttribPointer(i, size, ty, !!norm, stride, Number(off)),
      glVertexAttribDivisor: (i, d) => gl.vertexAttribDivisor(i, d),
      glDrawArrays: (m, f, c) => gl.drawArrays(m, f, c),
      glDrawElements: (m, c, t, off) => gl.drawElements(m, c, t, Number(off)),
      glDrawArraysInstanced: (m, f, c, n) => gl.drawArraysInstanced(m, f, c, n),
      glDrawElementsInstanced: (m, c, t, off, n) => gl.drawElementsInstanced(m, c, t, Number(off), n),
      glCreateProgramFrom(vp, vn, fp, fn) {
        const mk = (kind, src) => {
          const s = gl.createShader(kind);
          gl.shaderSource(s, src); gl.compileShader(s);
          if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error("shader error: " + gl.getShaderInfoLog(s) + "\n" + src);
          return s;
        };
        const p = gl.createProgram();
        gl.attachShader(p, mk(gl.VERTEX_SHADER, text(vp, vn)));
        gl.attachShader(p, mk(gl.FRAGMENT_SHADER, text(fp, fn)));
        gl.linkProgram(p);
        if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error("link error: " + gl.getProgramInfoLog(p));
        return add(p);
      },
      glUseProgram: (p) => gl.useProgram(get(p)),
      glDeleteProgram: (p) => gl.deleteProgram(get(p)),
      glGetUniformLocationStr(p, np, nn) {
        const l = gl.getUniformLocation(get(p), text(np, nn));
        if (!l) return -1;
        locs.push(l); return locs.length - 1;
      },
      glUniform1i: (l, v) => l >= 0 && gl.uniform1i(locs[l], v),
      glUniform1f: (l, v) => l >= 0 && gl.uniform1f(locs[l], v),
      glUniform2f: (l, x, y) => l >= 0 && gl.uniform2f(locs[l], x, y),
      glUniform3f: (l, x, y, z) => l >= 0 && gl.uniform3f(locs[l], x, y, z),
      glUniform4f: (l, x, y, z, w) => l >= 0 && gl.uniform4f(locs[l], x, y, z, w),
      glUniform4i: (l, x, y, z, w) => l >= 0 && gl.uniform4i(locs[l], x, y, z, w),
      glUniformMatrix4fv: (l, n, tr, p) => l >= 0 && gl.uniformMatrix4fv(locs[l], !!tr, f32(), Number(p) >> 2, 16 * n),
      glUniform4fv: (l, n, p) => l >= 0 && gl.uniform4fv(locs[l], f32(), Number(p) >> 2, 4 * n),
      glUniform1fv: (l, n, p) => l >= 0 && gl.uniform1fv(locs[l], f32(), Number(p) >> 2, n),
      glUniform2fv: (l, n, p) => l >= 0 && gl.uniform2fv(locs[l], f32(), Number(p) >> 2, 2 * n),
      glUniform3fv: (l, n, p) => l >= 0 && gl.uniform3fv(locs[l], f32(), Number(p) >> 2, 3 * n),
      glUniform1iv: (l, n, p) => l >= 0 && gl.uniform1iv(locs[l], i32(), Number(p) >> 2, n),
      glUniform2iv: (l, n, p) => l >= 0 && gl.uniform2iv(locs[l], i32(), Number(p) >> 2, 2 * n),
      glCreateTexture: () => add(gl.createTexture()),
      glDeleteTexture: (t) => gl.deleteTexture(get(t)),
      glBindTexture: (t, x) => gl.bindTexture(t, get(x)),
      glActiveTexture: (u) => gl.activeTexture(u),
      // (float data needs a Float32Array view)
      glTexImage2D: (t, lvl, internal, w, h, b, fmt, ty, p, size) => Number(p) === 0 ? gl.texImage2D(t, lvl, internal, w, h, b, fmt, ty, null)
        : gl.texImage2D(t, lvl, internal, w, h, b, fmt, ty, pix(ty), pixOff(ty, p)),
      glTexSubImage2D: (t, lvl, x, y, w, h, fmt, ty, p, size) => gl.texSubImage2D(t, lvl, x, y, w, h, fmt, ty, pix(ty), pixOff(ty, p)),
      glTexParameteri: (t, n, v) => gl.texParameteri(t, n, v),
      glGenerateMipmap: (t) => gl.generateMipmap(t),
      glPixelStorei: (n, v) => gl.pixelStorei(n, v),
      glCreateFramebuffer: () => add(gl.createFramebuffer()),
      glDeleteFramebuffer: (f) => gl.deleteFramebuffer(get(f)),
      glBindFramebuffer: (t, f) => gl.bindFramebuffer(t, get(f)),
      glFramebufferTexture2D: (t, a, tt, tex, lvl) => gl.framebufferTexture2D(t, a, tt, get(tex), lvl),
      glCreateRenderbuffer: () => add(gl.createRenderbuffer()),
      glDeleteRenderbuffer: (r) => gl.deleteRenderbuffer(get(r)),
      glBindRenderbuffer: (t, r) => gl.bindRenderbuffer(t, get(r)),
      glRenderbufferStorage: (t, f, w, h) => gl.renderbufferStorage(t, f, w, h),
      glFramebufferRenderbuffer: (t, a, rt, r) => gl.framebufferRenderbuffer(t, a, rt, get(r)),
      glCheckFramebufferStatus: (t) => gl.checkFramebufferStatus(t),
      glReadPixels: (x, y, w, h, fmt, ty, p, size) => gl.readPixels(x, y, w, h, fmt, ty, pix(ty), pixOff(ty, p)),
      glGetMaxTextureSize: () => gl ? gl.getParameter(gl.MAX_TEXTURE_SIZE) : 4096,
    };
  },
  start(ex) {
    // (no frames outside a browser: a program run by node)
    if (!ex.__frame || typeof requestAnimationFrame === "undefined") return;
    // (a page embedded without permission to read gamepads, as in a sandboxed frame, gets none)
    let padsAllowed = true;
    const getPads = () => {
      if (!padsAllowed || !navigator.getGamepads) return [];
      try { return navigator.getGamepads(); } catch (e) { padsAllowed = false; return []; }
    };
    const frame = (t) => {
      if (ex.__pad_begin && navigator.getGamepads) {
        // each gamepad as the browser numbers it (pads 0 to 7)
        const pads = getPads();
        ex.__pad_begin();
        for (let k = 0; k < 8; k++) {
          const g = pads[k];
          if (!g || !g.connected) { ex.__pad_present(k, 0, 0, 0); continue; }
          ex.__pad_present(k, 1, g.axes.length, g.buttons.length);
          for (let i = 0; i < 4 && i < g.axes.length; i++) ex.__pad_axis(k, i, g.axes[i]);
          const bv = (i) => g.buttons[i] ? g.buttons[i].value : 0;
          ex.__pad_axis(k, 4, bv(6)); ex.__pad_axis(k, 5, bv(7));
          // standard mapping -> a b x y lb rb back start home ls rs up down left right
          const order = [0, 1, 2, 3, 4, 5, 8, 9, 16, 10, 11, 12, 13, 14, 15];
          order.forEach((src, i) => ex.__pad_button(k, i, g.buttons[src] && g.buttons[src].pressed ? 1 : 0));
          for (let i = 0; i < 16 && i < g.axes.length; i++) ex.__pad_raw_axis(k, i, g.axes[i]);
          for (let i = 0; i < 32 && i < g.buttons.length; i++) ex.__pad_raw_button(k, i, g.buttons[i].pressed ? 1 : 0);
        }
      }
      const w0 = performance.now();
      const going = run(t);
      pace(t, performance.now() - w0);
      if (!going) return;
      // (redraw_on_input: no frames until input comes, or the time the program asked for; not
      // with tasks, whose frame may still be paused here)
      const wait = ex.__frame_wait && !tasked ? ex.__frame_wait() : -1;
      if (wait < 0) { requestAnimationFrame(frame); return; }
      asleep = true;
      if (wait < 1e8) nap = setTimeout(wake, wait);
    };
    let asleep = false, nap = null;
    const wake = () => {
      if (!asleep) return;
      asleep = false;
      if (nap !== null) clearTimeout(nap);
      nap = null;
      requestAnimationFrame(frame);
    };
    sloppy.wake = wake;
    for (const e of ["keydown", "keyup", "mousedown", "mouseup", "mousemove", "wheel", "touchstart", "touchmove", "touchend", "touchcancel",
                     "resize", "focus", "blur", "paste", "input", "compositionend", "drop", "pointerlockchange", "fullscreenchange"])
      window.addEventListener(e, wake, { capture: true, passive: true });
    document.addEventListener("visibilitychange", wake);
    if (window.visualViewport) window.visualViewport.addEventListener("resize", wake);
    // A phone that heats up slows its GPU, and frames are missed: each second in which more than
    // a quarter of them come late (half again the shortest gap between frames, the screen's
    // refresh, and fewer than 50 a second), and the program's own work is not what takes the
    // time, the canvas is drawn with fewer pixels; after 10 good seconds with more again (and if
    // that misses frames, again only after twice as long)
    const res = sloppy.res, steps = [1, 0.85, 0.72, 0.61, 0.52, 0.44];
    let last = 0, gaps = [], works = [], span = 0, period = 1e9, step = 0, good = 0, wait = 10, raisedAt = -1e9;
    const pace = (t, work) => {
      // (a gap over 250 ms: the page hidden, or the program waiting, not a frame missed)
      if (last) { const g = t - last; if (g < 250) { gaps.push(g); works.push(work); span += g; period = Math.max(Math.min(period, g), 4); } }
      last = t;
      if (span < 1000 || gaps.length < 20 || !res.fit) return;
      const late = gaps.filter((g) => g > Math.max(period * 1.5, 20)).length / gaps.length;
      const busy = works.slice().sort((a, b) => a - b)[works.length >> 1] > period * 0.7;
      gaps = []; works = []; span = 0;
      let to = step;
      if (late > 0.25 && !busy && step < steps.length - 1) {
        to = step + 1; good = 0;
        if (t - raisedAt < 3000) wait = Math.min(wait * 2, 120);
      }
      else if (late < 0.05 && step > 0 && ++good >= wait) { to = step - 1; good = 0; raisedAt = t; }
      else if (late >= 0.05) good = 0;
      if (to !== step) { step = to; res.scale = steps[step]; res.fit(); }
    };
    let stopped = false;
    const failed = (e0) => {
      const e = sloppy.overflowExit(e0);
      stopped = true;
      sloppy.tasks.dead = true;
      // (a panic: its message, written to the log, shown over the game instead of a frozen frame)
      const l = document.getElementById("log");
      const show = () => { Object.assign(l.style, { display: "block", position: "fixed", left: "0", top: "0", right: "0", margin: "0", padding: "12px", maxHeight: "60vh", background: "rgba(24, 0, 0, 0.88)", color: "#fcc", zIndex: "10" }); };
      if (e instanceof sloppy.Exit) { if (e.code !== 0) show(); return false; }
      show(); l.textContent += "error: " + sloppy.errorText(e) + "\n"; throw e;
    };
    // (a program with tasks: a frame runs where a task can pause it, and the next waits for it)
    const tasked = sloppy.tasks.on ? WebAssembly.promising(ex.__frame) : null;
    let busy = false;
    const run = (t) => {
      if (stopped || sloppy.tasks.dead) return false;
      if (tasked) {
        if (busy) return true;
        busy = true;
        tasked(t).then(() => { busy = false; }, (e) => { busy = false; try { failed(e); } catch (x) { console.error(x); } });
        return true;
      }
      try { ex.__frame(t); return true; } catch (e0) { return failed(e0); }
    };
    // (a frame now, between animation frames: a tap's, see tapFrame)
    sloppy.frameNow = () => { if (!stopped) run(performance.now()); };
    requestAnimationFrame(frame);
  },
});

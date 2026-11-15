// WebAudio output for the Sloppy mixer: audio is pulled from wasm a little ahead of time and played
// by an AudioWorklet (on the audio thread, so a busy page does not interrupt it), or where that
// is unavailable, by a buffer source node per chunk. A page that may share memory between threads
// (served cross-origin isolated) writes the samples into a ring both threads see: no message per
// chunk. Elsewhere (GitHub Pages cannot send the headers) each chunk is a message, and the worklet
// gives the buffers back four at a time once they have played, to be filled again: no garbage per
// chunk, and a quarter of the messages back.
sloppy.extra.push({
  imports(getMem, getExports) {
    let ctx = null, node = null, loading = false, rate = 48000;
    // (when the next chunk plays, in the context's seconds: in a typed array, as a fraction kept
    // in a closure's variable is an object made at each change)
    const at = new Float64Array(1);
    const worklet = `registerProcessor("sloppy-out", class extends AudioWorkletProcessor {
      constructor(o) {
        super(); this.q = []; this.at = 0;
        const s = o.processorOptions && o.processorOptions.ring;
        if (s) { this.ring = new Float32Array(s.samples); this.pos = new Int32Array(s.pos); this.mask = s.frames - 1; }
        this.port.onmessage = (e) => this.q.push(e.data);
      }
      process(_, outs) {
        const l = outs[0][0], r = outs[0][1] || outs[0][0];
        if (this.ring) {
          const ring = this.ring, m = this.mask, w = Atomics.load(this.pos, 0);
          let rd = this.pos[1];
          for (let i = 0; i < l.length; i++) {
            if (rd === w) { l[i] = r[i] = 0; continue; }
            const k = (rd & m) << 1;
            l[i] = ring[k]; r[i] = ring[k + 1];
            rd = (rd + 1) | 0;
          }
          Atomics.store(this.pos, 1, rd);
          return true;
        }
        for (let i = 0; i < l.length; i++) {
          const b = this.q[0];
          if (!b) { l[i] = r[i] = 0; continue; }
          l[i] = b[this.at]; r[i] = b[this.at + 1];
          this.at += 2;
          if (this.at >= b.length) { this.q.shift(); this.at = 0; }
        }
        return true;
      }
    });`;
    // (wasm memory as floats, made again only when the memory grows; chunks given back to fill)
    let fbuf = null, fview = null;
    let chunk = null;
    // (the ring: a power of two of frames, more than is ever queued ahead; frames written and
    // frames read so far, counted on, wrapping at 2^32)
    const RING = 16384;
    let ring = null, ringPos = null;
    function pump() {
      if (!ctx || ctx.state !== "running" || loading) return;
      const ex = getExports();
      const ahead = 0.09;
      const now = ctx.currentTime;
      if (at[0] < now) at[0] = now + 0.02;
      while (at[0] < now + ahead) {
        const n = 1024;
        if (ring && ((ringPos[0] - Atomics.load(ringPos, 1)) | 0) + n > RING) break;
        const o = ex.__audio_fill(n) >> 2;
        const mb = getMem().buffer;
        if (mb !== fbuf) { fbuf = mb; fview = new Float32Array(mb); }
        const f = fview;
        if (ring) {
          const w = ringPos[0], at = (w & (RING - 1)) << 1, first = Math.min(2 * n, 2 * RING - at);
          for (let i = 0; i < first; i++) ring[at + i] = f[o + i];
          for (let i = first; i < 2 * n; i++) ring[i - first] = f[o + i];
          Atomics.store(ringPos, 0, (w + n) | 0);
        } else if (node) {
          if (!chunk) chunk = new Float32Array(n * 2);
          const c = chunk;
          for (let i = 0; i < 2 * n; i++) c[i] = f[o + i];
          node.port.postMessage(c);
        } else {
          const buf = ctx.createBuffer(2, n, rate);
          const l = buf.getChannelData(0), r = buf.getChannelData(1);
          for (let i = 0; i < n; i++) { l[i] = f[o + 2 * i]; r[i] = f[o + 2 * i + 1]; }
          const src = ctx.createBufferSource();
          src.buffer = buf;
          src.connect(ctx.destination);
          src.start(at[0]);
        }
        at[0] += n / rate;
      }
    }
    let hidden = false;
    sloppy.resumeAudio = () => { if (ctx && !hidden && ctx.state !== "running") ctx.resume(); };
    // (the page hidden: the game gets no frames, so its sound stops; back as it is shown, if it
    // was running)
    let wasRunning = false;
    sloppy.pauseAudio = (on) => {
      hidden = on;
      if (!ctx) return;
      if (on) { wasRunning = ctx.state === "running"; if (wasRunning) ctx.suspend(); }
      else if (wasRunning) ctx.resume();
    };
    sloppy.pumpAudio = pump;
    // (how the sound goes out, for tools/webperfcheck.mjs: "ring", "messages", "nodes" or "")
    sloppy.audioPath = () => ring ? "ring" : node ? "messages" : ctx ? "nodes" : "";
    return {
      // (frames of sound given to the page and not heard yet: queued, and the output's latency
      // past the context; -1 while it is not playing. A whole number: no object made for it)
      __web_audio_held() {
        if (!ctx || ctx.state !== "running" || loading || at[0] <= 0) return -1;
        return Math.floor((Math.max(at[0] - ctx.currentTime, 0) + (ctx.outputLatency || ctx.baseLatency || 0)) * rate);
      },
      __web_audio_start(r) {
        rate = r;
        try { ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: r }); } catch (e) { ctx = null; }
        if (ctx && ctx.audioWorklet) {
          loading = true;
          // (a data: URL: pages opened from disk may not load blob: or file: modules)
          const url = "data:text/javascript;charset=utf-8," + encodeURIComponent(worklet);
          let shared = null;
          if (typeof SharedArrayBuffer === "function" && window.crossOriginIsolated) {
            try { shared = { samples: new SharedArrayBuffer(RING * 8), pos: new SharedArrayBuffer(8), frames: RING }; } catch (e) { shared = null; }
          }
          ctx.audioWorklet.addModule(url).then(() => {
            node = new AudioWorkletNode(ctx, "sloppy-out", { outputChannelCount: [2], processorOptions: shared ? { ring: shared } : {} });
            if (shared) { ring = new Float32Array(shared.samples); ringPos = new Int32Array(shared.pos); }
            node.connect(ctx.destination);
          }).catch(() => {}).finally(() => { loading = false; });
        }
        if (ctx) setInterval(pump, 20);       // (no audio here: nothing to feed)
      },
    };
  },
});

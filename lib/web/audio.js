// WebAudio output for the Sloppy mixer: audio is pulled from wasm a little ahead of time and played
// by an AudioWorklet (on the audio thread, so a busy page does not interrupt it), or where that
// is unavailable, by a buffer source node per chunk. The worklet gives each chunk's buffer back once
// it has played, and it is filled again: no garbage per chunk.
sloppy.extra.push({
  imports(getMem, getExports) {
    let ctx = null, node = null, loading = false, next = 0, rate = 48000;
    const worklet = `registerProcessor("sloppy-out", class extends AudioWorkletProcessor {
      constructor() { super(); this.q = []; this.at = 0; this.port.onmessage = (e) => this.q.push(e.data); }
      process(_, outs) {
        const l = outs[0][0], r = outs[0][1] || outs[0][0];
        for (let i = 0; i < l.length; i++) {
          const b = this.q[0];
          if (!b) { l[i] = r[i] = 0; continue; }
          l[i] = b[this.at]; r[i] = b[this.at + 1];
          this.at += 2;
          if (this.at >= b.length) { this.q.shift(); this.at = 0; this.port.postMessage(b, [b.buffer]); }
        }
        return true;
      }
    });`;
    // (wasm memory as floats, made again only when the memory grows; chunks given back to fill)
    let fbuf = null, fview = null;
    const spare = [];
    function pump() {
      if (!ctx || ctx.state !== "running" || loading) return;
      const ex = getExports();
      const ahead = 0.09;
      if (next < ctx.currentTime) next = ctx.currentTime + 0.02;
      while (next < ctx.currentTime + ahead) {
        const n = 1024;
        const o = Number(ex.__audio_fill(n)) >> 2;
        const mb = getMem().buffer;
        if (mb !== fbuf) { fbuf = mb; fview = new Float32Array(mb); }
        const f = fview;
        if (node) {
          const c = spare.length ? spare.pop() : new Float32Array(n * 2);
          for (let i = 0; i < 2 * n; i++) c[i] = f[o + i];
          node.port.postMessage(c, [c.buffer]);
        } else {
          const buf = ctx.createBuffer(2, n, rate);
          const l = buf.getChannelData(0), r = buf.getChannelData(1);
          for (let i = 0; i < n; i++) { l[i] = f[o + 2 * i]; r[i] = f[o + 2 * i + 1]; }
          const src = ctx.createBufferSource();
          src.buffer = buf;
          src.connect(ctx.destination);
          src.start(next);
        }
        next += n / rate;
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
    return {
      // (seconds of sound given to the page and not heard yet: queued, and the output's latency
      // past the context; -1 while it is not playing)
      __web_audio_held() {
        if (!ctx || ctx.state !== "running" || loading || next <= 0) return -1;
        return Math.max(next - ctx.currentTime, 0) + (ctx.outputLatency || ctx.baseLatency || 0);
      },
      __web_audio_start(r) {
        rate = r;
        try { ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: r }); } catch (e) { ctx = null; }
        if (ctx && ctx.audioWorklet) {
          loading = true;
          // (a data: URL: pages opened from disk may not load blob: or file: modules)
          const url = "data:text/javascript;charset=utf-8," + encodeURIComponent(worklet);
          ctx.audioWorklet.addModule(url).then(() => {
            node = new AudioWorkletNode(ctx, "sloppy-out", { outputChannelCount: [2] });
            node.port.onmessage = (e) => { if (spare.length < 16) spare.push(e.data); };
            node.connect(ctx.destination);
          }).catch(() => {}).finally(() => { loading = false; });
        }
        if (ctx) setInterval(pump, 20);       // (no audio here: nothing to feed)
      },
    };
  },
});

// Safari's engine (Playwright's WebKit), run by tools/webkitcheck.py in a container:
//   pages A B page.html     two invite pages (tests/net/invite_page.jo): A invites, B joins, the
//                           reply pasted into A REPLY_DELAY ms later, then ping and pong (A, B:
//                           webkit or chromium; Q: more of the page's query, a TURN relay)
//   native WHO page.html dir   a page and the native program (tests/net/invite_peer.jo, codes
//                           through files in dir); WHO invites: page or native
//   gallery dir             each .html in dir as an iPhone held sideways: errors, a screenshot
import { webkit, chromium, devices } from "playwright";
import fs from "node:fs";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(f, ms, what) { const t0 = Date.now(); while (Date.now() - t0 < ms) { const v = await f(); if (v) return v; await sleep(50); } throw new Error("timed out waiting for " + what); }
const launch = (kind) => kind === "webkit" ? webkit.launch() : chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
async function open(kind, opts = {}) {
  const b = await launch(kind);
  const ctx = await b.newContext(opts);
  const p = await ctx.newPage();
  const lines = [];
  p.on("console", (m) => lines.push(m.text()));
  p.on("pageerror", (e) => lines.push("pageerror: " + e.message));
  return { b, p, lines };
}
const q = process.env.Q ? "&" + process.env.Q : "";
const [mode, ...args] = process.argv.slice(2);
const code = (x) => (x.lines.find((l) => l.startsWith("code:")) || "").slice(5);
const paste = (x, r) => x.p.evaluate((r) => history.replaceState(null, "", location.pathname + location.search + "&REPLY=" + encodeURIComponent(r)), r);

if (mode === "pages") {
  const [ka, kb, page] = args;
  const A = await open(ka), B = await open(kb);
  try {
    await A.p.goto("file://" + page + "?ROLE=invite" + q);
    const c = await until(() => code(A), 20000, "A's code");
    await B.p.goto("file://" + page + "?ROLE=join&CODE=" + encodeURIComponent(c) + q);
    const r = await until(() => code(B), 20000, "B's reply");
    await sleep(Number(process.env.REPLY_DELAY || 0));
    await paste(A, r);
    await until(() => A.lines.some((l) => l.startsWith("page got:pong")) && B.lines.some((l) => l.startsWith("page got:pong")), 40000, "ping and pong");
    console.log(`ok   ${ka} invites, ${kb} joins`);
  } catch (e) {
    console.log(`FAIL ${ka} invites, ${kb} joins: ${e.message}\n  A: ${A.lines.join(" | ").slice(0, 1500)}\n  B: ${B.lines.join(" | ").slice(0, 1500)}`);
  } finally { await A.b.close(); await B.b.close(); }
} else if (mode === "native") {
  const [who, page, dir] = args;
  const rd = (f) => { try { return fs.readFileSync(dir + "/" + f, "utf8"); } catch (e) { return ""; } };
  const A = await open("webkit");
  try {
    if (who === "page") {
      await A.p.goto("file://" + page + "?ROLE=invite" + q);
      fs.writeFileSync(dir + "/code.txt", await until(() => code(A), 20000, "the page's code"));
      await paste(A, await until(() => rd("reply.txt"), 30000, "the native program's reply"));
    } else {
      const c = await until(() => rd("code.txt"), 30000, "the native program's code");
      await A.p.goto("file://" + page + "?ROLE=join&CODE=" + encodeURIComponent(c) + q);
      fs.writeFileSync(dir + "/reply.txt", await until(() => code(A), 20000, "the page's reply"));
    }
    await until(() => A.lines.some((l) => l.startsWith("page got:pong")), 40000, "pong");
    console.log(`ok   ${who === "page" ? "webkit invites, a native program joins" : "a native program invites, webkit joins"}`);
  } catch (e) {
    console.log(`FAIL webkit and a native program (${who} invites): ${e.message}\n  ${A.lines.join(" | ").slice(0, 1500)}`);
  } finally { await A.b.close(); }
} else if (mode === "gallery") {
  const [dir] = args;
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith(".html")).sort()) {
    const A = await open("webkit", { ...devices["iPhone 15 landscape"] });
    await A.p.goto("file://" + dir + "/" + f);
    await A.p.waitForTimeout(6000);
    await A.p.screenshot({ path: dir + "/" + f.replace(/\.html$/, ".png") });
    const bad = A.lines.filter((l) => /^pageerror|panic|error:/i.test(l));
    console.log(bad.length ? `FAIL ${f}: ${bad.join(" | ").slice(0, 600)}` : `ok   ${f} (as an iPhone)`);
    await A.b.close();
  }
}

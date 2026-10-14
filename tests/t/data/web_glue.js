// (tests/t/web_js.jo: what its extern does in a web page)
sloppy.env.js_double_len = (p, n, k) => BigInt((sloppy.text(p, n).length + Number(k)) * 2);

// Crawl every page of the Incheon preview: follow all same-origin links from the home page,
// recursively, and on each page record console/page errors, failed requests, HTTP >= 400,
// sideways overflow, broken images, and every internal link's status. Zero of each is the bar.
//   node crawl_incheon.mjs http://127.0.0.1:8801
import { createRequire } from "node:module";
const require = createRequire(new URL("../../../sounding/tools/package.json", import.meta.url));
const { chromium } = require("playwright");
const base = process.argv[2] || "http://127.0.0.1:8801";
const origin = new URL(base).origin;
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
const problems = [];
let cur = "";
page.on("pageerror", (e) => problems.push({ page: cur, kind: "pageerror", msg: e.message.slice(0, 160) }));
page.on("console", (m) => { if (m.type() === "error") problems.push({ page: cur, kind: "console", msg: m.text().slice(0, 160) }); });
page.on("requestfailed", (r) => { if (r.url().startsWith(origin)) problems.push({ page: cur, kind: "reqfail", msg: r.url().slice(0, 160) }); });
page.on("response", (r) => { if (r.status() >= 400 && r.url().startsWith(origin)) problems.push({ page: cur, kind: "http" + r.status(), msg: r.url().slice(0, 160) }); });

const seen = new Set();
const queue = [base + "/"];
const linkStatus = {};
let pages = 0;
while (queue.length) {
  const url = queue.shift();
  const key = url.split("#")[0];
  if (seen.has(key)) continue;
  seen.add(key);
  cur = key;
  const resp = await page.goto(key, { waitUntil: "networkidle", timeout: 60000 }).catch((e) => { problems.push({ page: key, kind: "goto", msg: e.message.slice(0, 120) }); return null; });
  if (!resp) continue;
  pages++;
  const info = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute("src")),
    links: [...document.querySelectorAll("a[href]")].map((a) => a.href),
    h1: (document.querySelector("h1") || {}).textContent?.trim().slice(0, 60),
    title: document.title,
  }));
  if (info.overflowX > 0) problems.push({ page: key, kind: "overflow", msg: String(info.overflowX) });
  for (const s of info.broken) problems.push({ page: key, kind: "brokenimg", msg: s });
  if (!info.title || info.title === "Vidimus · 비디무스" && !key.endsWith("/")) { /* preview has no titles plugin — not a fault */ }
  for (const href of info.links) {
    if (!href.startsWith(origin)) continue;
    const k = href.split("#")[0];
    if (!seen.has(k) && !queue.includes(k)) queue.push(k);
  }
}
// HEAD-check every internal link target once via fetch inside the page
const all = [...seen];
for (const u of all) {
  const st = await page.evaluate(async (x) => { try { const r = await fetch(x, { method: "GET" }); return r.status; } catch (e) { return "ERR"; } }, u);
  linkStatus[u] = st;
  if (st !== 200) problems.push({ page: "(link)", kind: "link" + st, msg: u });
}
await b.close();
console.log(JSON.stringify({ pages, urls: all.length, problems }, null, 1));

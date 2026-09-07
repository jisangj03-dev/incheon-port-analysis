// Print-media emulation for the Incheon layout: paper white, dark text, no bar/footer/toc/pager,
// reveal elements visible. Runs under both color schemes (dark is the case that used to fail).
//   node printcheck.mjs <url> <outprefix>
import { createRequire } from "node:module";
const require = createRequire(new URL("../../../sounding/tools/package.json", import.meta.url));
const { chromium } = require("playwright");
const [url, out] = process.argv.slice(2);
const b = await chromium.launch();
const res = {};
for (const scheme of ["light", "dark"]) {
  const p = await (await b.newContext({ viewport: { width: 816, height: 1056 }, colorScheme: scheme })).newPage();
  await p.goto(url, { waitUntil: "networkidle" });
  await p.emulateMedia({ media: "print" });
  await p.waitForTimeout(600);
  const info = await p.evaluate(() => {
    const cs = (el) => el && getComputedStyle(el);
    const vis = (sel) => { const el = document.querySelector(sel); return el ? cs(el).display !== "none" : null; };
    const hiddenRv = [...document.querySelectorAll(".rv")].filter((e) => +cs(e).opacity < 0.99).length;
    return {
      bodyBg: cs(document.body).backgroundColor,
      htmlBg: cs(document.documentElement).backgroundColor,
      h1: cs(document.querySelector("h1")).color,
      p: cs(document.querySelector(".doc p")).color,
      mast: vis(".mast"), foot: vis(".foot"), toc: vis(".toc"), pager: vis(".pager"),
      rv: document.querySelectorAll(".rv").length, hiddenRv,
      tableDisplay: document.querySelector(".doc table") ? cs(document.querySelector(".doc table")).display : null,
    };
  });
  await p.screenshot({ path: `${out}-${scheme}.png`, clip: { x: 0, y: 0, width: 816, height: 1056 } });
  res[scheme] = info;
  await p.context().close();
}
await b.close();
console.log(JSON.stringify(res, null, 1));

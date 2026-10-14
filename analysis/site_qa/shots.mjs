// Incheon preview capture: pages x schemes x viewports -> full-page PNG, plus console errors,
// sideways overflow, and every report-row link actually followed (landing H1 recorded).
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
const require = createRequire(new URL("../../../sounding/tools/package.json", import.meta.url));
const { chromium } = require("playwright");
const [base = "http://127.0.0.1:8801", out = "shots_incheon"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const PAGES = [
  ["home", "/"],
  ["r07", "/reports/report_07_공컨테이너_표본외검증.md"],
  ["r09", "/reports/report_09_공컨테이너_시계열연장.md"],
  ["r01", "/reports/report_01_공컨테이너_물동량.md"],
  ["about", "/about.html"],
  ["404", "/404.html"],
];
const VIEWS = [["desk", { width: 1280, height: 900 }, false], ["mob", { width: 390, height: 844 }, true]];
const report = {};
const browser = await chromium.launch();
for (const scheme of ["light", "dark"]) {
  for (const [vname, viewport, mobile] of VIEWS) {
    const ctx = await browser.newContext({ viewport, isMobile: mobile, hasTouch: mobile, deviceScaleFactor: 1, colorScheme: scheme });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text().slice(0, 160)); });
    page.on("requestfailed", (r) => errors.push("reqfail: " + r.url().slice(0, 160)));
    page.on("response", (r) => { if (r.status() >= 400) errors.push(`http ${r.status()}: ` + r.url().slice(0, 160)); });
    for (const [pname, path] of PAGES) {
      await page.goto(base + path, { waitUntil: "networkidle", timeout: 60000 });
      await page.addStyleTag({ content: "html{scroll-behavior:auto!important}" });
      // reveal: walk the page so every .rv has been observed, then return to top
      const H = await page.evaluate(() => document.documentElement.scrollHeight);
      for (let y = 0; y < H; y += 600) { await page.evaluate((yy) => window.scrollTo(0, yy), y); await page.waitForTimeout(60); }
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(900);
      const hidden = await page.evaluate(() => [...document.querySelectorAll(".rv")].filter((e) => !e.classList.contains("is-in")).length);
      const info = await page.evaluate(() => ({
        title: document.title,
        h1: (document.querySelector("h1") || {}).textContent?.trim().slice(0, 80),
        overflowX: document.documentElement.scrollWidth - window.innerWidth,
        height: document.documentElement.scrollHeight,
        brokenImgs: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute("src")),
        bodyClass: document.body.className,
        rv: document.querySelectorAll(".rv").length,
        mark: !!document.querySelector(".brand__mark"),
      }));
      info.rvHidden = hidden;
      await page.screenshot({ path: `${out}/${pname}-${scheme}-${vname}.png`, fullPage: true });
      report[`${pname}-${scheme}-${vname}`] = info;
    }
    // follow every report row link from home (desktop dark only, once)
    if (scheme === "dark" && vname === "desk") {
      await page.goto(base + "/", { waitUntil: "networkidle" });
      const hrefs = await page.$$eval('a[href*="reports/report_"]', (as) => as.map((a) => a.getAttribute("href")));
      const landings = [];
      for (const h of hrefs) {
        await page.goto(base + "/", { waitUntil: "networkidle" });
        const [resp] = await Promise.all([page.waitForNavigation({ waitUntil: "networkidle" }), page.click(`a[href="${h}"]`)]);
        landings.push({ href: h, status: resp?.status(), h1: await page.evaluate(() => document.querySelector("h1")?.textContent.trim().slice(0, 60)) });
      }
      report.landings = landings;
    }
    report[`errors-${scheme}-${vname}`] = errors;
    await ctx.close();
  }
}
await browser.close();
writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1));
console.log(JSON.stringify(report, null, 1));

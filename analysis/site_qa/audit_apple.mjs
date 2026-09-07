// Measure the same design dimensions on Apple pages and on ours, from computed styles.
//   node apple_audit.mjs
import { createRequire } from "node:module";
const require = createRequire(new URL("../../../sounding/tools/package.json", import.meta.url));
const { chromium } = require("playwright");

const TARGETS = [
  ["apple-kr-home", "https://www.apple.com/kr/", "nav#globalnav, .globalnav, header", "h2, h1"],
  ["apple-dev-docs", "https://developer.apple.com/documentation/swiftui", "nav, header", "h1"],
  ["sounding-live", "https://sounding.higgsfield.app/", ".sd-nav, header, nav", ".sd-h2, h1"],
  ["incheon-home", "http://127.0.0.1:8801/", ".mast", "h1"],
  ["incheon-r07", "http://127.0.0.1:8801/reports/report_07_%EA%B3%B5%EC%BB%A8%ED%85%8C%EC%9D%B4%EB%84%88_%ED%91%9C%EB%B3%B8%EC%99%B8%EA%B2%80%EC%A6%9D.md", ".mast", "h1"],
];

const b = await chromium.launch();
const out = {};
for (const [name, url, navSel, h1Sel] of TARGETS) {
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: "ko-KR", colorScheme: "light",
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36" });
  const p = await ctx.newPage();
  try {
    await p.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await p.waitForTimeout(2500);
    out[name] = await p.evaluate(([navSel, h1Sel]) => {
      const cs = (el) => el && getComputedStyle(el);
      const pick = (sel) => [...document.querySelectorAll(sel)].find((e) => e.getBoundingClientRect().height > 0 && e.getBoundingClientRect().width > 300);
      const nav = pick(navSel);
      const navCs = cs(nav);
      const navBg = nav ? (navCs.backdropFilter || navCs.webkitBackdropFilter) : null;
      // find the element that actually paints the bar (blur may be on a child/pseudo)
      let blur = navBg && navBg !== "none" ? navBg : null;
      if (nav && !blur) for (const c of nav.querySelectorAll("*")) { const f = cs(c).backdropFilter || cs(c).webkitBackdropFilter; if (f && f !== "none") { blur = f; break; } }
      const h1 = pick(h1Sel);
      const h1cs = cs(h1);
      const body = cs(document.body);
      const p = [...document.querySelectorAll("p")].find((e) => e.textContent.trim().length > 60 && e.getBoundingClientRect().width > 200);
      const pcs = cs(p);
      const main = [...document.querySelectorAll("main, article, .doc, .sd-section, section")].find((e) => e.getBoundingClientRect().width > 300);
      const btn = [...document.querySelectorAll("a, button")].find((e) => { const s = cs(e); return parseFloat(s.borderRadius) >= 12 && (s.backgroundColor !== "rgba(0, 0, 0, 0)" || s.borderWidth !== "0px") && e.getBoundingClientRect().height >= 32; });
      const fonts = new Set([...document.querySelectorAll("h1,h2,p,a,li,td")].slice(0, 200).map((e) => cs(e).fontFamily.split(",")[0].replace(/"/g, "").trim()));
      const links = [...document.querySelectorAll("a")].map((a) => cs(a).color);
      const accent = [...new Set(links)].filter((c) => { const m = c.match(/\d+/g); if (!m) return false; const [r, g, bb] = m.map(Number); return Math.max(r, g, bb) - Math.min(r, g, bb) > 40; });
      const trans = [...document.querySelectorAll("a, button, li, img")].slice(0, 300).filter((e) => cs(e).transitionDuration && cs(e).transitionDuration !== "0s").length;
      return {
        nav: nav ? { h: Math.round(nav.getBoundingClientRect().height), pos: navCs.position, blur, bg: navCs.backgroundColor, border: navCs.borderBottom } : null,
        h1: h1 ? { size: h1cs.fontSize, weight: h1cs.fontWeight, tracking: h1cs.letterSpacing, lh: h1cs.lineHeight, font: h1cs.fontFamily.split(",")[0], text: h1.textContent.trim().slice(0, 30) } : null,
        body: { size: body.fontSize, font: body.fontFamily.split(",")[0], bg: body.backgroundColor, color: body.color },
        para: p ? { size: pcs.fontSize, lh: pcs.lineHeight, colWidth: Math.round(p.getBoundingClientRect().width) } : null,
        mainWidth: main ? Math.round(main.getBoundingClientRect().width) : null,
        pill: btn ? { radius: cs(btn).borderRadius, h: Math.round(btn.getBoundingClientRect().height), text: btn.textContent.trim().slice(0, 20) } : null,
        fonts: [...fonts].slice(0, 5),
        accentColors: accent.slice(0, 4),
        transitionsOnElements: trans,
        darkMedia: !!([...document.styleSheets].some((s) => { try { return [...s.cssRules].some((r) => r.media && /prefers-color-scheme/.test(r.media.mediaText)); } catch (e) { return false; } })),
        reducedMotion: !!([...document.styleSheets].some((s) => { try { return [...s.cssRules].some((r) => r.media && /prefers-reduced-motion/.test(r.media.mediaText)); } catch (e) { return false; } })),
      };
    }, [navSel, h1Sel]);
  } catch (e) {
    out[name] = { error: e.message.slice(0, 120) };
  }
  await ctx.close();
}
await b.close();
console.log(JSON.stringify(out, null, 1));

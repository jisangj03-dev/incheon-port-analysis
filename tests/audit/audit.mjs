// 공개판 전수조사(2026-10-21 선장님 지시 「모든 지면·링크·숫자·동작·네 폭·느린 회선과 접근성」) — 로컬 빌드(astro/dist)만 연다 · 외부 요청 0.
//   node tests/audit/audit.mjs <출력 폴더>        (서버가 없으면 tests/serve.mjs 를 띄운다)
// 지면 = sitemap + 내린 주소(넘김 지면) + 404. 폭 넷 = 390 · 768 · 1280 · 1920.
// 지면 × 폭: 응답 · 화면 오류 · 외부 요청(Cloudflare 비컨 예외) · 가로 넘침 · 화면 밖으로 나간 요소 · axe(WCAG 2.2 A·AA)
// 지면 한 번: 링크(내부 주소 응답 · #앵커 대상) · 느린 회선(느린 4G · CPU 4배 / 느린 3G) 첫 제목·답 보이는 시각 · JS 꺼도 제목·답 · 키보드 초점 표시
import { chromium } from "@playwright/test";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const OUT = process.argv[2] || "audit-out";
mkdirSync(OUT, { recursive: true });
const PORT = Number(process.env.AUDIT_PORT || 4173), ORIGIN = `http://127.0.0.1:${PORT}`, BASE = "/incheon-port-analysis";
const AXE = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf-8");
const ALLOWED = new Set(["static.cloudflareinsights.com", "cloudflareinsights.com"]);
const WIDTHS = [[390, 844], [768, 1024], [1280, 720], [1920, 1080]];

const sitemap = readFileSync("astro/dist/sitemap.xml", "utf-8");
const PAGES = [...sitemap.matchAll(/<loc>https:\/\/jisangj03-dev\.github\.io([^<]+)<\/loc>/g)].map((m) => decodeURI(m[1]));
const live = JSON.parse(readFileSync("tools-build/live-check.json", "utf-8"));
const REDIRECTS = live.pages.filter((p) => p.endsWith(".html") || p.endsWith("/")).map((p) => BASE + p).filter((p) => !PAGES.includes(p) && !p.endsWith("no-such-page.html"));

async function up() { try { return (await fetch(`${ORIGIN}${BASE}/`)).status === 200; } catch { return false; } }
let srv = null;
if (!(await up())) {
  srv = spawn("node", ["tests/serve.mjs", String(PORT), "astro/dist"], { stdio: "ignore" });
  for (let i = 0; i < 50 && !(await up()); i++) await new Promise((r) => setTimeout(r, 200));
}

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const rows = [], pageRows = [], linkProblems = [];

async function guard(page) {
  const ext = [], errors = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { const h = new URL(r.request().url()).hostname; if (!ALLOWED.has(h)) ext.push(r.request().url()); return r.abort(); });
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error" && !/cloudflareinsights|net::ERR_FAILED/.test(m.text())) errors.push(m.text().slice(0, 200)); });
  page.on("response", (r) => { if (r.status() >= 400 && r.url().startsWith(ORIGIN) && !r.url().endsWith("favicon.ico")) errors.push(`${r.status()} ${r.url().replace(ORIGIN, "")}`); });
  return { ext, errors };
}

// ── 지면 × 폭 ──
for (const p of PAGES) {
  for (const [w, h] of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500 });
    const page = await ctx.newPage();
    const g = await guard(page);
    const res = await page.goto(ORIGIN + p, { waitUntil: "load" });
    await page.waitForTimeout(1200);
    const lay = await page.evaluate(() => {
      const vw = document.documentElement.clientWidth;
      const sw = document.scrollingElement.scrollWidth;
      const off = [];
      for (const el of document.querySelectorAll("body *")) {
        const cs = getComputedStyle(el);
        if (cs.visibility === "hidden" || cs.display === "none" || cs.position === "fixed") continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        // 가로 스크롤 상자 안의 것은 뺀다(표·코드는 상자 안에서 밀린다)
        let a = el.parentElement, inScroll = false;
        while (a && a !== document.body) { const o = getComputedStyle(a).overflowX; if (o === "auto" || o === "scroll" || o === "hidden" || o === "clip") { inScroll = true; break; } a = a.parentElement; }
        if (!inScroll && r.right > vw + 1 && el.children.length === 0 && (el.textContent || "").trim()) off.push(`${el.tagName.toLowerCase()}.${[...el.classList].join(".")} 「${el.textContent.trim().slice(0, 24)}」 ${Math.round(r.right - vw)}px`);
      }
      return { vw, sw, off: off.slice(0, 5) };
    });
    let axe = null;
    if (w === 390 || w === 1280) {
      await page.addScriptTag({ content: AXE });
      axe = await page.evaluate(async () => {
        const r = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] }, resultTypes: ["violations"] });
        return r.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, help: v.help, where: v.nodes.slice(0, 3).map((n) => n.target.join(" ")) }));
      });
    }
    rows.push({ p, w, status: res.status(), errors: [...new Set(g.errors)], ext: g.ext, overflow: lay.sw - lay.vw, off: lay.off, axe });
    await ctx.close();
  }
}

// ── 지면 한 번 — 링크 · 느린 회선 · JS 끔 · 키보드 ──
const linkCache = new Map();
async function status(u) {
  if (!linkCache.has(u)) linkCache.set(u, await fetch(u, { redirect: "manual" }).then((r) => r.status, () => 0));
  return linkCache.get(u);
}
const SLOW = { "느린 4G": { latency: 150, down: 1.6e6 / 8, up: 750e3 / 8, cpu: 4 }, "느린 3G": { latency: 400, down: 400e3 / 8, up: 400e3 / 8, cpu: 4 } };

for (const p of [...PAGES, ...REDIRECTS]) {
  const rec = { p, redirect: REDIRECTS.includes(p) };
  // 링크
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await ctx.newPage(); await guard(page);
    const res = await page.goto(ORIGIN + p, { waitUntil: "load" });
    rec.status = res.status();
    if (rec.redirect) {
      // 0초 넘김이라 도착 뒤에는 원 지면의 meta 가 없다 — HTML 을 따로 받아 읽는다
      const html = await fetch(ORIGIN + p).then((r) => r.text());
      rec.refresh = (html.match(/<meta[^>]+http-equiv=["']?refresh["']?[^>]*content=["']([^"']+)/i) || [])[1] || "";
      await page.waitForTimeout(2500);
      rec.landed = new URL(page.url()).pathname;
    }
    const links = await page.evaluate(() => [...document.querySelectorAll("a[href]")].filter((a) => a.dataset.c !== "mail").map((a) => ({ href: a.getAttribute("href"), abs: a.href, text: (a.textContent || a.getAttribute("aria-label") || "").trim().slice(0, 30) })));
    const ids = new Set(await page.evaluate(() => [...document.querySelectorAll("[id]")].map((e) => e.id)));
    // 메일 단추(data-c="mail")는 주소를 숨겨 두고 누를 때 스크립트가 mailto 로 연다 — 링크 검사 대신 눌러서 본다
    rec.mail = await page.evaluate(() => [...document.querySelectorAll('a[data-c="mail"]')].length);
    if (rec.mail) {
      const got = await page.evaluate(() => new Promise((res) => {
        const a = document.querySelector('a[data-c="mail"]');
        const orig = window.open; let seen = "";
        window.addEventListener("beforeunload", () => {}, { once: true });
        a.addEventListener("click", () => setTimeout(() => res(a.getAttribute("href") || seen), 50), { once: true });
        a.click();
      }));
      rec.mailHref = /^mailto:[^@\s]+@[^@\s]+\.[a-z]{2,}/i.test(got) ? "mailto 정상" : (String(got).startsWith("mailto:") ? "**mailto 꼴 이상**" : `**${String(got).slice(0, 12)}**`);
    }
    rec.links = links.length; rec.external = [];
    for (const l of links) {
      if (/^(mailto|tel|javascript):/.test(l.href)) continue;
      const u = new URL(l.abs);
      if (u.origin !== ORIGIN) { rec.external.push(u.href); continue; }
      const path = u.pathname;
      if (u.hash && (path === new URL(page.url()).pathname) && !ids.has(decodeURIComponent(u.hash.slice(1)))) linkProblems.push({ from: p, href: l.href, text: l.text, why: "앵커 대상 없음" });
      const s = await status(ORIGIN + path);
      if (s !== 200) linkProblems.push({ from: p, href: l.href, text: l.text, why: `응답 ${s}` });
    }
    rec.external = [...new Set(rec.external)];
    await ctx.close();
  }
  if (rec.redirect) { pageRows.push(rec); continue; }
  // 느린 회선 — 첫 제목(h1)과 첫 문단이 보이기까지 · 받은 바이트
  rec.slow = {};
  for (const [name, c] of Object.entries(SLOW)) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const page = await ctx.newPage(); await guard(page);
    const cdp = await ctx.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: c.latency, downloadThroughput: c.down, uploadThroughput: c.up });
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: c.cpu });
    let bytes = 0; cdp.on("Network.loadingFinished", (e) => { bytes += e.encodedDataLength; });
    const t0 = Date.now();
    await page.goto(ORIGIN + p, { waitUntil: "commit", timeout: 120_000 });
    let h1 = null;
    try { await page.locator("h1").first().waitFor({ state: "visible", timeout: 60_000 }); h1 = Date.now() - t0; } catch {}
    await page.waitForLoadState("load", { timeout: 120_000 }).catch(() => {});
    const load = Date.now() - t0;
    const lcp = await page.evaluate(() => new Promise((r) => { let v = 0; new PerformanceObserver((l) => { for (const e of l.getEntries()) v = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); setTimeout(() => r(Math.round(v)), 300); }));
    await page.waitForTimeout(3000);
    rec.slow[name] = { h1, load, lcp, kb: Math.round(bytes / 1024) };
    await ctx.close();
  }
  // JS 끔 — 제목과 첫 답이 HTML 에 있나
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, javaScriptEnabled: false });
    const page = await ctx.newPage(); await guard(page);
    await page.goto(ORIGIN + p, { waitUntil: "load" });
    rec.nojs = await page.evaluate(() => ({ h1: (document.querySelector("h1")?.textContent || "").trim().slice(0, 40), text: document.body.innerText.length }));
    await ctx.close();
  }
  // 키보드 — 앞 20칸 Tab: 초점이 보이나(외곽선 또는 그림자) · 건너뛰기 링크
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await ctx.newPage(); await guard(page);
    await page.goto(ORIGIN + p, { waitUntil: "load" });
    const seen = [];
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press("Tab");
      const f = await page.evaluate(() => {
        const e = document.activeElement; if (!e || e === document.body) return null;
        const cs = getComputedStyle(e);
        const vis = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== "none";
        const r = e.getBoundingClientRect();
        return { tag: e.tagName.toLowerCase(), text: (e.textContent || e.getAttribute("aria-label") || "").trim().slice(0, 20), vis, onscreen: r.bottom > 0 && r.top < innerHeight + 2000 && r.width > 0 };
      });
      if (f) seen.push(f);
    }
    rec.kbd = { stops: seen.length, invisible: seen.filter((f) => !f.vis).map((f) => `${f.tag}「${f.text}」`), skip: seen[0]?.text || "" };
    await ctx.close();
  }
  pageRows.push(rec);
  console.log("지면", p, JSON.stringify(rec.slow));
}

await browser.close();
if (srv) srv.kill();

// ── 결과 ──
writeFileSync(`${OUT}/audit.json`, JSON.stringify({ made: new Date().toISOString(), widths: WIDTHS, rows, pageRows, linkProblems }, null, 1));
const L = [];
L.push(`# 전수조사 기계 판정 — ${new Date().toISOString().slice(0, 16)}Z`, "", `지면 ${PAGES.length} · 넘김 주소 ${REDIRECTS.length} · 폭 ${WIDTHS.map((w) => w[0]).join("·")}`, "");
L.push("## 지면 × 폭", "", "| 지면 | 폭 | 응답 | 화면 오류 | 외부 요청 | 가로 넘침 px | 화면 밖 글 | axe 위반 |", "|---|---|---|---|---|---|---|---|");
for (const r of rows) L.push(`| ${r.p.replace(BASE, "") || "/"} | ${r.w} | ${r.status} | ${r.errors.length ? r.errors.join("<br>") : 0} | ${r.ext.length} | ${Math.max(0, r.overflow)} | ${r.off.length ? r.off.join("<br>") : 0} | ${r.axe == null ? "—" : r.axe.length ? r.axe.map((v) => `${v.id}(${v.impact}·${v.n}) ${v.where.join(", ")}`).join("<br>") : 0} |`);
L.push("", "## 지면 한 번", "", "| 지면 | 링크 | 메일 단추 | 바깥 링크 | 느린 4G 제목/LCP/완료 ms · KB | 느린 3G 제목/LCP/완료 ms · KB | JS 끔 제목 | 키보드 초점 안 보임 |", "|---|---|---|---|---|---|---|---|");
for (const r of pageRows.filter((x) => !x.redirect)) {
  const s = (k) => r.slow[k] ? `${r.slow[k].h1 ?? "안 보임"}/${r.slow[k].lcp}/${r.slow[k].load} · ${r.slow[k].kb}` : "—";
  L.push(`| ${r.p.replace(BASE, "") || "/"} | ${r.links} | ${r.mail ? `${r.mail} · ${r.mailHref}` : 0} | ${r.external.length} | ${s("느린 4G")} | ${s("느린 3G")} | ${r.nojs.h1 || "**없음**"} | ${r.kbd.invisible.length ? r.kbd.invisible.join(", ") : 0}/${r.kbd.stops} |`);
}
L.push("", "## 넘김 주소(내린 지면)", "", "| 주소 | 응답 | meta refresh | 도착 |", "|---|---|---|---|");
for (const r of pageRows.filter((x) => x.redirect)) L.push(`| ${r.p.replace(BASE, "")} | ${r.status} | ${r.refresh || "**없음**"} | ${r.landed?.replace(BASE, "")} |`);
L.push("", "## 링크 문제", "", linkProblems.length ? linkProblems.map((x) => `- ${x.from.replace(BASE, "")} → \`${x.href}\` 「${x.text}」 — ${x.why}`).join("\n") : "0");
L.push("", "## 바깥 링크(요청하지 않음 · 목록만)", "", [...new Set(pageRows.flatMap((r) => r.external))].sort().map((u) => `- ${u}`).join("\n") || "0");
writeFileSync(`${OUT}/audit.md`, L.join("\n") + "\n");
console.log(`끝 — ${OUT}/audit.md · 링크 문제 ${linkProblems.length}`);

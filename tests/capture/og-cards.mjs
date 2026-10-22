// 보고서 공유 카드(B6) — 빌드된 og/<id>.html 을 1200×630 으로 찍어 og/<id>.jpg 로 바꾸고 틀 HTML 은 지운다.
//   node tests/capture/og-cards.mjs [dist 폴더]     기본 astro/dist · 시험 서버(tests/serve.mjs)를 스스로 띄웠다 내린다
// 빌드 직후 · 배포 전에 돈다(pages.yml · sounding-qa.yml). 하나라도 못 찍으면 종료 1 — 깨진 카드를 배포하지 않는다.
import { chromium } from "@playwright/test";
import { readdirSync, unlinkSync, existsSync, statSync, readFileSync, writeFileSync, mkdirSync, copyFileSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";

const dist = process.argv[2] || "astro/dist";
const port = 4179;
const base = `http://127.0.0.1:${port}`;
const srv = spawn(process.execPath, ["tests/serve.mjs", String(port), dist], { stdio: "ignore" });
for (let i = 0; i < 50; i++) { try { if ((await fetch(`${base}/incheon-port-analysis/`)).ok) break; } catch {} await new Promise((r) => setTimeout(r, 100)); }
const dir = join(dist, "og");
if (!existsSync(dir)) { console.error("og/ 가 없다 — 빌드부터"); process.exit(1); }
const pages = readdirSync(dir).filter((f) => f.endsWith(".html") && f !== "tool.html"); // tool.html = 도구 카드 틀(아래 따로)
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
let bad = 0;
for (const f of pages) {
  const id = f.replace(/\.html$/, "");
  try {
    await page.goto(`${base}/incheon-port-analysis/og/${encodeURIComponent(id)}.html`, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForSelector("[data-og-ready]");
    await page.screenshot({ path: join(dir, `${id}.jpg`), type: "jpeg", quality: 86, clip: { x: 0, y: 0, width: 1200, height: 630 } });
    unlinkSync(join(dir, f));
    console.log(`카드 ${id}.jpg ${statSync(join(dir, `${id}.jpg`)).size}B`);
  } catch (e) { bad++; console.error(`못 찍었다 ${id}: ${String(e).split("\n")[0]}`); }
}
// 도구 카드(B6) · 도구 퍼가기(B7) — 전권 위임 ④. 도구 지면을 **스크립트 없이**(서버가 그린 첫 상태) 열어 질문·큰 숫자·3초 답·기준일·출처·CSV 를
// 읽고, 그 값으로 카드 틀을 채워 찍고, 같은 값으로 퍼가기 지면을 쓴다. 카드·퍼가기·지면이 한 순간 한 출처에서 나온다(숫자를 따로 만들지 않는다).
const SITE = "https://jisangj03-dev.github.io/incheon-port-analysis";
const TOOLS = (JSON.parse(readFileSync("data/rooms.json", "utf-8")).rooms.find((r) => r.id === "tools")?.items || []).filter((t) => /^\/tools\/.+\.html$/.test(t.href));
const cards = {};
let tbad = 0;
if (existsSync(join(dir, "tool.html")) && TOOLS.length) {
  const ctx = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1440, height: 900 } });
  const rd = await ctx.newPage();
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  mkdirSync(join(dist, "embed"), { recursive: true });
  for (const t of TOOLS) {
    try {
      await rd.goto(`${base}/incheon-port-analysis${t.href}`, { waitUntil: "load" });
      const v = await rd.evaluate(() => {
        const T = (s) => (document.querySelector(s)?.textContent || "").replace(/\s+/g, " ").trim(), n = document.querySelector("[data-og-num]");
        return { q: T(".tool__q"), lead: T(".tool__lead"), who: T(".tool__head .s-cap").replace(/ · [^·]*기준$/, ""), asof: T(".tool__asof"),
          num: (n?.textContent || "").replace(/\s+/g, "").trim(), unit: n?.getAttribute("data-og-num") || "", source: T(".tool__foot .s-trust").replace(/ · CSV$/, ""), // 끝의 CSV 링크 글자는 아래 퍼가기 지면이 따로 단다(「CSV · CSV」 겹침 · 3차 사실 대조)
          csv: document.querySelector(".tool__foot a[download]")?.getAttribute("href") || "" };
      });
      if (!v.q || !v.num) throw new Error(`질문 또는 큰 숫자를 못 읽었다(${t.href})`);
      await page.goto(`${base}/incheon-port-analysis/og/tool.html`, { waitUntil: "load" });
      await page.evaluate((v) => { const $ = (id) => document.getElementById(id); $("og-eb").textContent = v.who || "도구"; $("og-q").textContent = v.q; $("og-num").textContent = v.num; $("og-unit").textContent = v.unit; $("og-lead").textContent = v.lead; $("og-asof").textContent = v.asof; }, v);
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: join(dir, `tool-${t.id}.jpg`), type: "jpeg", quality: 86, clip: { x: 0, y: 0, width: 1200, height: 630 } });
      cards[t.id] = { href: t.href, q: v.q, num: v.num, unit: v.unit, asof: v.asof };
      // 퍼가기 지면 — 남의 지면 안에서 도니 분석·글꼴·스크립트 0(외부 요청 0) · noindex · 카드 그림과 출처·CSV·원 도구 링크
      writeFileSync(join(dist, "embed", `tool-${t.id}.html`), `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>${esc(t.title)} · 측심 도구</title><link rel="canonical" href="${SITE}${t.href}">
<style>body{margin:0;padding:10px;background:#f5f2eb;color:#191714;font:15px/1.5 system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;word-break:keep-all}
img{display:block;width:100%;height:auto;aspect-ratio:1200/630;border:1px solid #d9d3c7}p{margin:8px 0 0}small{color:#5b554c}a{color:#191714}</style></head>
<body><main data-embed-tool="${esc(t.id)}"><a href="${SITE}${t.href}" target="_blank" rel="noopener"><img src="../og/tool-${esc(t.id)}.jpg" alt="${esc(v.q)} — ${esc(v.num)}${esc(v.unit ? " " + v.unit : "")} · ${esc(v.lead)}" width="1200" height="630"></a>
<p><a href="${SITE}${t.href}" target="_blank" rel="noopener"><b>${esc(v.q)}</b></a></p>
<p><small>${esc(v.asof)}${v.asof ? " · " : ""}${esc(v.source)}${v.csv ? ` · <a href="https://jisangj03-dev.github.io${esc(v.csv)}" download>CSV</a>` : ""} · 측심 도구(공공 1차 데이터)</small></p></main></body></html>
`);
      console.log(`도구 카드 tool-${t.id}.jpg ${v.num}${v.unit ? " " + v.unit : ""}`);
    } catch (e) { tbad++; console.error(`도구 카드 못 찍었다 ${t.id}: ${String(e).split("\n")[0]}`); }
  }
  await ctx.close();
  writeFileSync(join(dir, "cards.json"), JSON.stringify({ _설명: "도구 카드에 찍힌 값(카드를 찍는 순간 도구 지면에서 읽음) — 시험이 지면과 대조한다", cards }, null, 1));
  unlinkSync(join(dir, "tool.html"));
}
// 홈 「실제 도구 화면」 띠(2026-10-22 · data/home_showcase.json) — 실제 도구 지면의 주 그림(sel)을 찍는다(지어낸 목업 0 · iframe 0).
// 넓은 화면용(640 폭 · 2배 · 2:1)과 좁은 화면용(520 폭 · 2배 · 2:1 — 390 폭에선 차트·트리맵이 세로로 길어 한 조각만 들어왔다) 두 장 — 홈 띠 칸(16:9 · 넓은 화면 약 580px · 좁은 화면 약 360px)에 거의 제 크기로 들어가
// 지면 이름표가 읽힌다(24차 화면 판정: 1200 폭에서 찍어 줄였더니 이름표가 8px). 그림 = 주 그림 상자 너비 × 16:9(상자가 더 길면 위에서부터).
// 배포 때마다 다시 찍으므로 그림 = 그 배포의 실제 지면이다. 못 찍으면 홈은 그림 없이 글(도구 이름·한 줄)만 보인다 — 실패로 센다.
const SHOW = existsSync("data/home_showcase.json") ? JSON.parse(readFileSync("data/home_showcase.json", "utf-8")).shots : [];
if (SHOW.length) {
  mkdirSync(join(dist, "assets", "toolshots"), { recursive: true });
  for (const [suf, ratio, opt] of [["", 1 / 2, { viewport: { width: 640, height: 900 }, deviceScaleFactor: 2 }], ["-m", 1 / 2, { viewport: { width: 520, height: 900 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }]]) {
    const sctx = await browser.newContext(opt);
    const sp = await sctx.newPage();
    for (const t of SHOW) {
      const name = `${t.id}${suf}.jpg`, out = join(dist, "assets", "toolshots", name);
      try {
        await sp.goto(`${base}/incheon-port-analysis${t.href}`, { waitUntil: "load" });
        await sp.evaluate(() => document.fonts.ready);
        await sp.waitForTimeout(3500); // 첫 장면이 그려지고 움직임이 한 번 돌 시간
        const el = t.sel ? sp.locator(t.sel).first() : null;
        if (el && (await el.count())) {
          await el.evaluate((e) => e.scrollIntoView({ block: "center" })); await sp.waitForTimeout(800);
          const bb = await el.boundingBox(), w = Math.floor(bb.width), h = Math.round(w * ratio);
          const y = bb.height >= h ? bb.y : bb.y - (h - bb.height) / 2; // 위에 맞춘다(트리맵 가장 큰 칸 이름 · 지도 위쪽 이름표가 잘렸다)
          // 그림 가장자리에 반쯤 걸린 글자(지도 이름표 등)는 숨긴다 — 잘린 이름표가 읽히지 않는 조각으로 남았다(24차 화면 판정 경미 1). 다른 것은 손대지 않는다
          // 주 그림이 16:9 보다 납작해 위아래로 넓혀 찍을 때 들어오는 지면 글(「아래 막대를 움직여 보세요」 등 — 정지 그림에선 뜻이 없다)도 숨긴다
          await sp.evaluate(([y0, y1, x0, x1, sel]) => {
            const main = document.querySelector(sel);
            for (const e of document.querySelectorAll("body *")) {
              const own = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
              if (!own) continue;
              const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
              if (r.bottom <= y0 || r.top >= y1 || r.right <= x0 || r.left >= x1) continue;
              const cut = (r.top < y0 && r.bottom > y0) || (r.top < y1 && r.bottom > y1) || (r.left < x0 && r.right > x0) || (r.left < x1 && r.right > x1);
              if (cut || (main && !main.contains(e))) e.style.visibility = "hidden";
            }
          }, [Math.max(0, y), Math.max(0, y) + h, bb.x, bb.x + w, t.sel]);
          await sp.screenshot({ path: out, type: "jpeg", quality: 72, clip: { x: Math.floor(bb.x), y: Math.max(0, Math.round(y)), width: w, height: h } }); // 주 그림(지도 · 트리맵 · 차트) · 16:9
        }
        else {
          const top = await sp.evaluate(() => Math.ceil(document.querySelector("header.s-mast")?.getBoundingClientRect().bottom || 0));
          const vp = opt.viewport;
          await sp.screenshot({ path: out, type: "jpeg", quality: 74, clip: { x: 0, y: top, width: vp.width, height: Math.min(750, vp.height - top) } });
        }
        console.log(`도구 화면 toolshots/${name} ${statSync(out).size}B`);
      } catch (e) { bad++; console.error(`도구 화면 못 찍었다 ${name}: ${String(e).split("\n")[0]}`); }
    }
    await sctx.close();
  }
}
// 홈 카드 = 지면 기본 카드(Base.astro ogImage 기본값 /og/home.jpg) · 옛 주소 /assets/og.jpg 를 미리 긁어 간 곳도 새 그림을 받게 덮어쓴다(2026-10-20)
if (existsSync(join(dir, "home.jpg"))) { mkdirSync(join(dist, "assets"), { recursive: true }); copyFileSync(join(dir, "home.jpg"), join(dist, "assets", "og.jpg")); console.log("assets/og.jpg ← og/home.jpg"); }
else { bad++; console.error("홈 카드 og/home.jpg 가 없다 — assets/og.jpg 를 못 바꿨다"); }
bad += tbad;
await browser.close();
srv.kill();
console.log(`공유 카드 ${pages.length + TOOLS.length - bad}/${pages.length + TOOLS.length}`);
process.exit(bad ? 1 : 0);

// 품질 채점용 스크린샷(docs/품질기준.md §2·§5) — 지면마다 네 폭 첫 화면 + 1520·390 전체 쪽 + 동작 줄이기 프레임 차이.
//   node tests/capture/quality-shots.mjs <출력 폴더> [지면 …]     지면을 안 주면 사이트맵 + 도구 목록 전부
//   빌드(astro/dist)를 시험 서버로 띄워 찍는다. 화면 판정 서브에이전트는 이 폴더의 그림과 기준 표만 받는다.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";

const out = process.argv[2] || "quality-shots";
const port = 4195, base = `http://127.0.0.1:${port}/incheon-port-analysis`;
mkdirSync(out, { recursive: true });
const srv = spawn(process.execPath, ["tests/serve.mjs", String(port), "astro/dist"], { stdio: "ignore" });
for (let i = 0; i < 50; i++) { try { if ((await fetch(`${base}/`)).ok) break; } catch {} await new Promise((r) => setTimeout(r, 100)); }

const sm = existsSync("astro/dist/sitemap.xml") ? [...readFileSync("astro/dist/sitemap.xml", "utf-8").matchAll(/<loc>https:\/\/[^<]*?\/incheon-port-analysis([^<]*)<\/loc>/g)].map((m) => decodeURI(m[1])) : [];
const tools = (JSON.parse(readFileSync("data/rooms.json", "utf-8")).rooms.find((r) => r.id === "tools")?.items || []).map((t) => t.href);
const pages = process.argv.length > 3 ? process.argv.slice(3) : [...new Set([...sm, "/tools/", ...tools])];
const slug = (p) => p.replace(/^\/|\.html$/g, "").replace(/\/$/, "").replace(/\//g, "_") || "home";

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
const WIDTHS = [[1280, 720], [1520, 730], [1920, 1080], [390, 844]];
const rows = [];
const open = async (ctx, p) => { const pg = await ctx.newPage(); await pg.goto(encodeURI(base + p), { waitUntil: "load", timeout: 45000 }); await pg.waitForTimeout(2500); return pg; };

for (const [w, h] of WIDTHS) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500, deviceScaleFactor: 1 });
  for (const p of pages) {
    const s = slug(p);
    try {
      const pg = await open(ctx, p);
      await pg.screenshot({ path: `${out}/${s}--${w}x${h}.png` });
      const r = await pg.evaluate(() => ({ over: document.documentElement.scrollWidth - document.documentElement.clientWidth, H: document.documentElement.scrollHeight }));
      if (w === 1520 || w === 390) await pg.screenshot({ path: `${out}/${s}--${w}-full.png`, fullPage: true });
      rows.push({ p, w, h, ...r });
      await pg.close();
    } catch (e) { rows.push({ p, w, h, err: String(e).split("\n")[0].slice(0, 100) }); }
  }
  await ctx.close();
}
// 동작 줄이기 — 2초 간격 두 장이 다르면 움직인다(정지 지면은 같다 · 판정은 사람/에이전트가 지면 성격과 같이 본다)
const rm = await browser.newContext({ viewport: { width: 1520, height: 730 }, reducedMotion: "reduce" });
const motion = {};
for (const p of pages) {
  try {
    const pg = await open(rm, p);
    const a = await pg.screenshot(); await pg.waitForTimeout(2000); const b = await pg.screenshot();
    motion[p] = Buffer.compare(a, b) !== 0;
    await pg.close();
  } catch (e) { motion[p] = `오류 ${String(e).slice(0, 60)}`; }
}
await rm.close();
await browser.close();
srv.kill();
writeFileSync(`${out}/shots.json`, JSON.stringify({ made: new Date().toISOString(), widths: WIDTHS, pages: pages.map((p) => ({ p, slug: slug(p), reducedMotionMoves: motion[p] })), rows }, null, 1));
console.log(`지면 ${pages.length} · 그림 ${rows.filter((r) => !r.err).length * 1}+ · 오류 ${rows.filter((r) => r.err).length}`);

// 도구 시연 영상 녹화(⑤ · 선커밋 ⑤-상세) — 빌드된 사이트의 도구 지면을 조작하며 Playwright 로 녹화한다.
// 편마다 세로(9:16)·정사각(1:1) 두 판 · 조작한 시각(ms)을 표지로 남긴다 → video/public/rec/<편>-<판>.mp4 · .json
// [2026-10-15 실측] Playwright recordVideo·CDP 화면 중계는 헤드리스에서 기기 배율(DPR)을 무시해 432px 로 찍힌다 → 고해상도 스크린샷을
// 쉬지 않고 찍어(초당 12~16장) 찍은 시각대로 ffmpeg 로 엮는다(30fps 로 채움). 조작은 실제 시각으로 돈다.
// Remotion(video/)이 이 녹화와 표지로 자막을 맞춘다. 외부 요청은 막는다(비콘 포함 — 영상에 필요 없다).
//   node tests/capture/record-reels.mjs [dist]      시험 서버를 스스로 띄웠다 내린다
import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync, rmSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { spawn } from "node:child_process";

const dist = process.argv[2] || "astro/dist";
const port = 4181, base = `http://127.0.0.1:${port}/incheon-port-analysis`;
const OUT = "video/public/rec";
const srv = spawn(process.execPath, ["tests/serve.mjs", String(port), dist], { stdio: "ignore" });
for (let i = 0; i < 50; i++) { try { if ((await fetch(`${base}/`)).ok) break; } catch {} await new Promise((r) => setTimeout(r, 100)); }

const FORMATS = { portrait: { viewport: { width: 432, height: 768 }, scale: 2.5, size: { width: 1080, height: 1920 } }, square: { viewport: { width: 720, height: 720 }, scale: 1.5, size: { width: 1080, height: 1080 } } };
const FFMPEG = process.env.FFMPEG || "ffmpeg";
const CARDS = JSON.parse(readFileSync(join(dist, "og/cards.json"), "utf-8")).cards; // 카드를 찍을 때 지면에서 읽은 값(자막과 같은 출처)
const wait = (p, ms) => p.waitForTimeout(ms);
const glide = (p, sel) => p.evaluate((s) => { const el = document.querySelector(s); if (el) window.scrollTo({ top: el.getBoundingClientRect().top + scrollY - 80, behavior: "smooth" }); }, sel);
const top = (p) => p.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));

// 편 셋 — 표지 이름은 video/src 의 자막 표가 쓴다(이름이 같아야 자막이 붙는다)
const REELS = {
  chokepoint: { href: "/tools/chokepoint.html", run: async (p, mark) => {
    await glide(p, ".ck__big"); await wait(p, 3200); mark("hormuz");
    for (const id of ["redsea", "malacca", "taiwan"]) { await glide(p, ".ck__ctl"); await wait(p, 700); await p.locator(`.seg button[data-id=${id}]`).click(); await glide(p, ".ck__big"); mark(id); await wait(p, 2600); }
    await glide(p, ".ck__ctl"); await wait(p, 600); await p.locator(".seg button[data-id=hormuz]").click(); mark("hormuz2"); await wait(p, 2400);
  } },
  "import-cost": { href: "/tools/import-cost.html", run: async (p, mark) => {
    // 3초 답이 주를 넘겨 보다 이번 주로 돌아온 뒤에 표지를 찍는다(자막 숫자 = 화면 숫자 · 2026-10-15 검수: 4초에는 아직 2025-02 주였다)
    await glide(p, ".cost__big"); await p.waitForFunction(() => !!window.__cost); await wait(p, 150); await p.waitForFunction((n) => (document.getElementById("cs-diff")?.textContent || "").replace(/\s+/g, "") === n, CARDS["import-cost"].num, { timeout: 20000 }); mark("now"); await wait(p, 2600);
    await glide(p, "#wave"); await wait(p, 1500); mark("wave");
    const r = p.locator("#wave-r"); const n = await r.locator("option").count();
    if (n > 1) { await r.selectOption({ index: 1 }); mark("route"); await wait(p, 2400); }
    await p.locator("#wave-apply").click(); mark("apply"); await wait(p, 1200);
    await glide(p, ".cost__big"); await wait(p, 2600); mark("end");
  } },
  "bid-radar": { href: "/tools/bid-radar.html", run: async (p, mark) => {
    await glide(p, ".br__big"); await wait(p, 2800); mark("all");
    for (const g of ["보관·창고", "항만·해운·항공"]) { await glide(p, ".br__ctl"); await wait(p, 600); await p.locator(`.br__ctl .seg button[data-g="${g}"]`).click(); mark(g); await wait(p, 900); await glide(p, "#br-items"); await wait(p, 2200); }
    await glide(p, ".br__ctl"); await wait(p, 500); await p.locator('.br__ctl .seg button[data-g=""]').click(); await p.selectOption("#br-sort", "price"); mark("price"); await wait(p, 700); await glide(p, "#br-items"); await wait(p, 2600);
  } },
};

const only = process.env.REELS_ONLY ? process.env.REELS_ONLY.split(",") : null;
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
let bad = 0;
for (const [id, R] of Object.entries(REELS)) {
  if (only && !only.includes(id)) continue;
  for (const [fmt, F] of Object.entries(FORMATS)) {
    const tmp = join(OUT, `_tmp-${id}-${fmt}`); rmSync(tmp, { recursive: true, force: true }); mkdirSync(tmp, { recursive: true });
    const ctx = await browser.newContext({ viewport: F.viewport, deviceScaleFactor: F.scale, reducedMotion: "no-preference" });
    await ctx.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
    const p = await ctx.newPage(); const marks = {}; let t0 = Date.now();
    const mark = (k) => { marks[k] = Date.now() - t0; };
    try {
      await p.goto(`${base}${R.href}`, { waitUntil: "load" }); await p.evaluate(() => document.fonts.ready);
      const shots = []; let stop = false; t0 = Date.now(); mark("loaded");
      const grab = (async () => { while (!stop) { const at = Date.now() - t0; const buf = await p.screenshot({ type: "jpeg", quality: 88 }); shots.push([at, buf]); } })();
      await R.run(p, mark); mark("done"); stop = true; await grab;
      // 찍은 시각대로 이어 붙인다(concat 목록의 duration = 다음 장까지의 간격)
      const lines = [];
      shots.forEach(([at, buf], i) => { const f = `f${String(i).padStart(5, "0")}.jpg`; writeFileSync(join(tmp, f), buf); const nx = i + 1 < shots.length ? shots[i + 1][0] : marks.done; lines.push(`file '${f}'`, `duration ${Math.max(0.001, (nx - at) / 1000).toFixed(3)}`); });
      lines.push(`file 'f${String(shots.length - 1).padStart(5, "0")}.jpg'`);
      writeFileSync(join(tmp, "list.txt"), lines.join("\n") + "\n");
      const r = spawnSync(FFMPEG, ["-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", join(tmp, "list.txt"), "-vf", `scale=${F.size.width}:${F.size.height}:flags=lanczos,fps=30`, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", join(OUT, `${id}-${fmt}.mp4`)], { stdio: "inherit" });
      if (r.status !== 0) throw new Error(`ffmpeg ${r.status}`);
      writeFileSync(join(OUT, `${id}-${fmt}.json`), JSON.stringify({ id, fmt, size: F.size, fps_captured: +(shots.length / (marks.done / 1000)).toFixed(1), marks }, null, 1));
      console.log(`녹화 ${id}-${fmt} ${(marks.done / 1000).toFixed(1)}초 · ${shots.length}장(${(shots.length / (marks.done / 1000)).toFixed(1)}/초)`, Object.keys(marks).join(" "));
      await ctx.close();
    } catch (e) { bad++; console.error(`녹화 실패 ${id}-${fmt}: ${String(e).split("\n")[0]}`); await ctx.close().catch(() => {}); }
    rmSync(tmp, { recursive: true, force: true });
  }
}
await browser.close(); srv.kill();
process.exit(bad ? 1 : 0);

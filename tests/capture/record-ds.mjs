// 시안 조작 녹화 — 선장님이 폰에서도 판정하게(2026-10-14). 우리 면만(기준 사이트 없음) · 390 세로 · 1440 가로 · 면마다 15초 안팎 mp4 + 첫 화면 PNG.
// Playwright 녹화(webm) → ffmpeg 로 H.264 mp4(폰 재생 · faststart). 외부 요청은 막는다(지면이 외부 요청 0 인지도 같이 본다).
//   node tests/capture/record-ds.mjs [--base http://127.0.0.1:4173/incheon-port-analysis] [--out lab-out/ours]
import { chromium } from "@playwright/test";
import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const base = arg("base", "http://127.0.0.1:4173/incheon-port-analysis"), out = arg("out", "lab-out/ours");
mkdirSync(out, { recursive: true });
const tmp = join(out, "_webm"); mkdirSync(tmp, { recursive: true });

const wait = (p, ms) => p.waitForTimeout(ms);
// 천천히 내린다 — 사람이 스크롤하듯(스크롤로 그려지는 주홍 선이 보이게)
async function glide(p, to, ms) {
  const from = await p.evaluate(() => scrollY), steps = Math.max(1, Math.round(ms / 50));
  for (let i = 1; i <= steps; i++) { await p.evaluate((y) => scrollTo(0, y), from + ((to - from) * i) / steps); await wait(p, 50); }
}
async function sweep(p, sel, values, each) { for (const v of values) { await p.locator(sel).fill(String(v)); await p.locator(sel).dispatchEvent("input"); await wait(p, each); } }

const FACES = {
  // 홈: 첫 화면 → 스크롤로 주홍 선이 그려짐 → 숫자 장면에서 달 막대
  home: { path: "/lab/ds/index.html", run: async (p) => {
    await wait(p, 1500);
    const H = await p.evaluate(() => document.querySelector(".hero").offsetHeight - innerHeight);
    await glide(p, H, 6000);
    await glide(p, H + (await p.evaluate(() => innerHeight)) * 0.9, 1500);
    const max = Number(await p.locator("#now-m").getAttribute("max"));
    await sweep(p, "#now-m", Array.from({ length: 14 }, (_, i) => Math.round(max - (i * max) / 13)), 250);
    await wait(p, 800);
  } },
  // 맥주 게임: 막대를 움직이면 그림·숫자가 같이(34% → 0 → 100% → 34%)
  beer: { path: "/lab/ds/beer.html", run: async (p) => {
    await p.waitForSelector("#wave[data-ready]"); await wait(p, 1500);
    const seq = [0.34, 0.25, 0.15, 0.05, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 0.8, 0.6, 0.45, 0.34];
    await sweep(p, "#beta", seq, 520);
    await wait(p, 1500);
  } },
  // 지도: 그대로 두면 달이 흐르고 점이 숨 쉰다 → 달 막대로 앞뒤
  map: { path: "/lab/ds/map.html", run: async (p) => {
    await p.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 });
    const top = await p.evaluate(() => document.getElementById("ds-map").getBoundingClientRect().top + scrollY - 80);
    await glide(p, top, 1200);
    await wait(p, 9000);
    const max = Number(await p.locator("#ds-m").getAttribute("max"));
    await sweep(p, "#ds-m", [max, Math.round(max * 0.75), Math.round(max * 0.5), Math.round(max * 0.25), 0, max], 500);
    await wait(p, 600);
  } },
  // 노트: 단계·날짜 → 막대 차트 → 자라려면 → 이어지는 노트
  note: { path: "/lab/ds/note.html", run: async (p) => {
    await wait(p, 1800);
    const H = await p.evaluate(() => document.documentElement.scrollHeight - innerHeight);
    await glide(p, H, 10000);
    await wait(p, 1500);
    await glide(p, 0, 1500);
  } },
};
const VIEWS = [{ name: "390", w: 390, h: 844, mobile: true }, { name: "1440", w: 1440, h: 900, mobile: false }];

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const report = [];
for (const [face, F] of Object.entries(FACES)) for (const V of VIEWS) {
  const dir = join(tmp, `${face}-${V.name}`); rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({ viewport: { width: V.w, height: V.h }, isMobile: V.mobile, hasTouch: V.mobile, deviceScaleFactor: 1, recordVideo: { dir, size: { width: V.w, height: V.h } } });
  const page = await ctx.newPage();
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { ext.push(r.request().url()); return r.abort(); });
  const t0 = Date.now();
  let err = null;
  try {
    await page.goto(base + F.path, { waitUntil: "networkidle", timeout: 45_000 });
    await page.screenshot({ path: join(out, `${face}-${V.name}-first.png`) });
    await F.run(page);
  } catch (e) { err = String(e).split("\n")[0]; }
  await ctx.close();
  const webm = readdirSync(dir).find((f) => f.endsWith(".webm"));
  const mp4 = join(out, `${face}-${V.name}.mp4`);
  if (webm) {
    // 폰 재생용 — H.264 · yuv420p · 앞머리에 색인(faststart) · 짝수 크기
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", join(dir, webm), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", mp4]);
  }
  report.push({ face, view: V.name, seconds: Math.round((Date.now() - t0) / 1000), mp4: webm ? mp4 : null, external: ext.length, err });
  console.log(`${face} ${V.name} · ${Math.round((Date.now() - t0) / 1000)}초 · ${webm ? mp4 : "녹화 없음"} · 외부 요청 ${ext.length}${err ? ` · 오류 ${err}` : ""}`);
}
await browser.close();
rmSync(tmp, { recursive: true, force: true });
writeFileSync(join(out, "report.json"), JSON.stringify(report, null, 1));
if (report.some((r) => r.err || !r.mp4)) process.exit(1);

// 개편 전·후 캡처 — 같은 네 화면 × 같은 두 크기(데스크톱 1440 · iPhone 13). 판정 기준 문서가 요구한 짝이다.
//
//   node tests/capture/capture.mjs docs/개편전_20261010            # 공개 주소(라이브)를 찍는다
//   CAPTURE_BASE=http://127.0.0.1:4173 node tests/capture/capture.mjs /tmp/x   # 로컬 빌드로 시험
//
// 공개 주소는 이 컨테이너(클라우드 세션)의 네트워크 정책이 막는다 — 그래서 GitHub Actions 에서 돈다.
// 전체 화면(fullPage) · CSS 화소 배율(scale:"css") — 모바일 3배 화소로 찍으면 높이가 브라우저 한도를 넘는다.
// 스크롤해야 나타나는 블록(리빌)이 있다 — 첫 판은 그 자리가 빈 채로 찍혔다. 그래서 끝까지 한 화면씩
// 내려가 리빌을 다 깨운 뒤 맨 위로 돌아와 찍는다. 움직임 줄이기(reducedMotion)도 같이 켠다.
import { chromium, devices } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

const out = process.argv[2];
if (!out) { console.error("출력 폴더를 준다"); process.exit(2); }
mkdirSync(out, { recursive: true });

const base = process.env.CAPTURE_BASE;   // 있으면 GitHub Pages 세 화면을 그 주소로 바꾼다(시험용)
const PAGES_ROOT = base ? `${base}/incheon-port-analysis` : "https://jisangj03-dev.github.io/incheon-port-analysis";
const SCREENS = [
  ["home", `${PAGES_ROOT}/`],
  ["calculator", `${PAGES_ROOT}/tools/logistics-cost.html`],
  ["warehouse-map", `${PAGES_ROOT}/tools/warehouse-map.html`],
  ["higgsfield", base ? null : "https://sounding.higgsfield.app/"],
];
const SIZES = [
  ["desktop-1440", { viewport: { width: 1440, height: 900 } }],
  ["iphone-13", { ...devices["iPhone 13"] }],
];

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
const log = [];
let bad = 0;
for (const [sname, opts] of SIZES) {
  const { defaultBrowserType, ...ctxOpts } = opts;
  const ctx = await browser.newContext({ ...ctxOpts, reducedMotion: "reduce" });
  for (const [name, url] of SCREENS) {
    if (!url) continue;
    const page = await ctx.newPage();
    const file = `${out}/${name}_${sname}.png`;
    try {
      const res = await page.goto(url, { waitUntil: "networkidle", timeout: 60_000 });
      await page.evaluate(() => document.fonts && document.fonts.ready);
      await page.evaluate(async () => {
        const step = Math.max(200, Math.floor(window.innerHeight * 0.8));
        for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 120));
        }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(800);
      const h = await page.evaluate(() => document.documentElement.scrollHeight);
      await page.screenshot({ path: file, fullPage: true, scale: "css" });
      log.push(`| ${name} | ${sname} | ${res ? res.status() : "?"} | ${h} | ${url} |`);
    } catch (e) {
      log.push(`| ${name} | ${sname} | 실패 | | ${url} — ${String(e).split("\n")[0]} |`);
      bad++;
    }
    await page.close();
  }
  await ctx.close();
}
await browser.close();
const md = [
  `# 캡처 기록 — ${new Date().toISOString()}`,
  "",
  "전체 화면 · CSS 화소 배율 · 데스크톱 1440×900 / iPhone 13(390×844, 모바일 UA)을 크로미움으로.",
  "",
  "| 화면 | 크기 | HTTP | 문서 높이(px) | 주소 |",
  "|---|---|---|---|---|",
  ...log,
  "",
].join("\n");
writeFileSync(`${out}/캡처기록.md`, md);
console.log(md);
process.exit(bad ? 1 : 0);

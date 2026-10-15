// 도구 시연형 릴스 재료 — 계산기를 실제로 쓰는 화면을 녹화한다(크레딧 0 · 무료 연산: Actions 에서 돈다).
//   node tests/capture/record-calc.mjs <기준주소> <출력 webm>
// 9:16 화면(540×960 · 녹화 크기 = 화면 크기 — 크면 왼쪽 위 구석에만 찍힌다 · Remotion 이 키운다). 입력은 「가상 예시 넣기」(가상값 · 실제 업체 견적 아님).
import { chromium, devices } from "@playwright/test";
import { mkdirSync, renameSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";

const base = (process.argv[2] || "http://127.0.0.1:4173").replace(/\/$/, "");
const out = process.argv[3] || "remotion/public/reel-01-calc.webm";
const tmp = join(dirname(out), "_rec");
mkdirSync(tmp, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
const ctx = await browser.newContext({ ...devices["iPhone 13"], viewport: { width: 540, height: 960 }, deviceScaleFactor: 1, recordVideo: { dir: tmp, size: { width: 540, height: 960 } }, reducedMotion: "no-preference" });
const page = await ctx.newPage();
await page.route(/cloudflareinsights/, (r) => r.abort());
await page.goto(`${base}/incheon-port-analysis/tools/logistics-cost.html`, { waitUntil: "load" });
await page.waitForTimeout(1200);
await page.click("#sample");
await page.waitForTimeout(1500);
// 결과 카드로 천천히 내려간다 — 모름 경고가 화면에 오게
const y = await page.locator("#res-1").evaluate((el) => el.getBoundingClientRect().top + scrollY - 140);
for (let k = 1; k <= 30; k++) { await page.evaluate((t) => scrollTo(0, t), (y * k) / 30); await page.waitForTimeout(40); }
await page.waitForTimeout(3500);
const y2 = await page.locator("#be-text").evaluate((el) => el.getBoundingClientRect().top + scrollY - 200);
for (let k = 1; k <= 25; k++) { await page.evaluate(([a, b, kk]) => scrollTo(0, a + ((b - a) * kk) / 25), [y, y2, k]); await page.waitForTimeout(40); }
await page.waitForTimeout(4000);
await ctx.close();
await browser.close();
const f = readdirSync(tmp).find((n) => n.endsWith(".webm"));
renameSync(join(tmp, f), out);
console.log(`녹화: ${out}`);

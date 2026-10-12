// 보고서 공유 카드(B6) — 빌드된 og/<id>.html 을 1200×630 으로 찍어 og/<id>.jpg 로 바꾸고 틀 HTML 은 지운다.
//   node tests/capture/og-cards.mjs [dist 폴더]     기본 astro/dist · 시험 서버(tests/serve.mjs)를 스스로 띄웠다 내린다
// 빌드 직후 · 배포 전에 돈다(pages.yml · sounding-qa.yml). 하나라도 못 찍으면 종료 1 — 깨진 카드를 배포하지 않는다.
import { chromium } from "@playwright/test";
import { readdirSync, unlinkSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";

const dist = process.argv[2] || "astro/dist";
const port = 4179;
const base = `http://127.0.0.1:${port}`;
const srv = spawn(process.execPath, ["tests/serve.mjs", String(port), dist], { stdio: "ignore" });
for (let i = 0; i < 50; i++) { try { if ((await fetch(`${base}/incheon-port-analysis/`)).ok) break; } catch {} await new Promise((r) => setTimeout(r, 100)); }
const dir = join(dist, "og");
if (!existsSync(dir)) { console.error("og/ 가 없다 — 빌드부터"); process.exit(1); }
const pages = readdirSync(dir).filter((f) => f.endsWith(".html"));
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
await browser.close();
srv.kill();
console.log(`공유 카드 ${pages.length - bad}/${pages.length}`);
process.exit(bad ? 1 : 0);

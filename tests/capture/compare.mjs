// 화면 비교 — 우리 화면과 기준 화면을 같은 폭으로 찍어 한 장에 나란히 놓는다(디자인 도구 판정 v3 · 2026-10-14).
// 기존 Playwright 만 쓴다. 봇 탐지 우회 없음 — 기본 UA·기본 설정 그대로, 막히면 막힌 대로 적는다.
// 기준 사이트 화면은 저장소에 커밋하지 않는다(남의 이미지 복제 금지) — Actions 산출물(짧은 보관)로만 남긴다.
//   node tests/capture/compare.mjs --ours <주소> --ref <주소> [--widths 1440,390] [--out lab-out/compare] [--name 이름]
import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const ours = arg("ours"), ref = arg("ref"), out = arg("out", "lab-out/compare"), name = arg("name", "compare");
const widths = arg("widths", "1440,390").split(",").map(Number);
if (!ours || !ref) { console.error("--ours 와 --ref 가 필요하다"); process.exit(2); }
mkdirSync(out, { recursive: true });

// 이 세션은 /opt/pw-browsers 의 크로미움(PW_CHROMIUM_PATH) · Actions 는 기본 설치본
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
const report = [];
for (const w of widths) {
  const h = w >= 1000 ? 900 : 844;
  const shots = [];
  for (const [label, url] of [["우리", ours], ["기준", ref]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    let status = null, err = null;
    try {
      const res = await page.goto(url, { waitUntil: "networkidle", timeout: 45_000 });
      status = res ? res.status() : null;
      await page.waitForTimeout(800);
    } catch (e) { err = String(e).split("\n")[0]; }
    const buf = await page.screenshot({ fullPage: false }).catch(() => null);
    shots.push({ label, url, status, err, b64: buf ? buf.toString("base64") : null });
    await ctx.close();
  }
  // 한 장으로 — 두 장을 같은 폭으로 나란히(왼쪽 우리 · 오른쪽 기준)
  const page = await browser.newPage({ viewport: { width: w * 2 + 24, height: h + 40 } });
  await page.setContent(`<body style="margin:0;background:#222;color:#eee;font:13px system-ui;display:flex;gap:24px">${shots
    .map((s) => `<figure style="margin:0;width:${w}px"><figcaption style="height:40px;line-height:40px;padding:0 8px">${s.label} · ${w}px · ${s.status ?? s.err ?? "?"}</figcaption>${s.b64 ? `<img src="data:image/png;base64,${s.b64}" style="display:block;width:${w}px">` : "<p>찍지 못함</p>"}</figure>`)
    .join("")}</body>`);
  const file = join(out, `${name}-${w}.png`);
  await page.screenshot({ path: file, fullPage: true });
  await page.close();
  report.push({ width: w, file, shots: shots.map(({ b64, ...r }) => r) });
}
await browser.close();
writeFileSync(join(out, `${name}.json`), JSON.stringify(report, null, 1));
console.log(report.map((r) => `${r.width}px → ${r.file} · ${r.shots.map((s) => `${s.label} ${s.status ?? s.err}`).join(" / ")}`).join("\n"));

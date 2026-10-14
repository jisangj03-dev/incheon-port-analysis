// 화면 비교 — 우리 화면과 기준 화면을 같은 폭으로 찍어 한 장에 나란히 놓는다(디자인 도구 판정 v3 · 2026-10-14).
// 기존 Playwright 만 쓴다. 봇 탐지 우회 없음 — 기본 UA·기본 설정 그대로, 막히면 막힌 대로 적는다.
// 기준 사이트 화면은 저장소에 커밋하지 않는다(남의 이미지 복제 금지) — Actions 산출물(짧은 보관)로만 남긴다.
//   node tests/capture/compare.mjs --ours <주소> --ref <주소> [--widths 1440,390] [--out lab-out/compare] [--name 이름] [--full]
//   --full 이면 첫 화면 한 장에 더해 전체 페이지 한 장(<이름>-<폭>-full.png)도 만든다.
import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const ours = arg("ours"), ref = arg("ref"), out = arg("out", "lab-out/compare"), name = arg("name", "compare");
const widths = arg("widths", "1440,390").split(",").map(Number);
const full = process.argv.includes("--full");
const FULL_MAX = 9000; // 아주 긴 기준 페이지는 위에서 이만큼까지만(합성 이미지가 브라우저 한계를 넘지 않게)
if (!ours || !ref) { console.error("--ours 와 --ref 가 필요하다"); process.exit(2); }
mkdirSync(out, { recursive: true });

// 이 세션은 /opt/pw-browsers 의 크로미움(PW_CHROMIUM_PATH) · Actions 는 기본 설치본
// WebGL 은 소프트웨어(SwiftShader)로 — GPU 없는 Actions 머리없는 크로미움은 이 인자 없이 WebGL 을 못 만들어 지도가 빈 면이 된다(playwright.config 와 같은 인자)
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
// 한 장으로 — 두 장을 같은 폭으로 나란히(왼쪽 우리 · 오른쪽 기준)
async function compose(w, shots, file) {
  const h = Math.max(...shots.map((s) => s.h || 0), 200);
  const page = await browser.newPage({ viewport: { width: w * 2 + 24, height: h + 40 } });
  await page.setContent(`<body style="margin:0;background:#222;color:#eee;font:13px system-ui;display:flex;gap:24px;align-items:flex-start">${shots
    .map((s) => `<figure style="margin:0;width:${w}px"><figcaption style="height:40px;line-height:40px;padding:0 8px">${s.label} · ${w}px · ${s.status ?? s.err ?? "?"}${s.cut ? ` · 위 ${FULL_MAX}px 까지` : ""}</figcaption>${s.b64 ? `<img src="data:image/png;base64,${s.b64}" style="display:block;width:${w}px">` : "<p>찍지 못함</p>"}</figure>`)
    .join("")}</body>`);
  // 큰 data: 이미지가 다 풀리기 전에 찍으면 「Unable to capture screenshot」이 난다(2026-10-14 run 38514859590) — 풀림을 기다리고 한 번 더 찍는다
  await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0), null, { timeout: 30_000 });
  await page.screenshot({ path: file, fullPage: true }).catch(() => page.waitForTimeout(1000).then(() => page.screenshot({ path: file, fullPage: true })));
  await page.close();
}

const report = [];
for (const w of widths) {
  const h = w >= 1000 ? 900 : 844;
  const shots = [], fulls = [];
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
    shots.push({ label, url, status, err, h, b64: buf ? buf.toString("base64") : null });
    if (full && !err) {
      // fullPage 옵션은 찍는 순간에만 창을 늘려 WebGL 지도가 빈 면으로 찍힌다(2026-10-14 로컬 실측).
      // 그래서 창을 문서 높이로 먼저 늘리고, 다시 그려질 시간을 준 뒤 보이는 만큼을 찍는다.
      // 창 높이에 따라 자라는 칸(지도 = 100svh 기준)이 있어 한 번 늘린 뒤 다시 재고, 더 길어졌으면 한 번 더 늘린다
      const measure = () => page.evaluate(() => Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0)).catch(() => h);
      let docH = await measure(), fh = h;
      for (let k = 0; k < 3; k++) {
        const want = Math.min(Math.max(docH, h), FULL_MAX);
        if (want === fh && k) break;
        fh = want;
        await page.setViewportSize({ width: w, height: fh });
        await page.waitForTimeout(2000);
        docH = await measure();
      }
      const fb = await page.screenshot({ fullPage: false }).catch(() => null);
      fulls.push({ label, url, status, err, h: fh, cut: docH > FULL_MAX, b64: fb ? fb.toString("base64") : null });
    }
    await ctx.close();
  }
  const file = join(out, `${name}-${w}.png`);
  await compose(w, shots, file);
  const row = { width: w, file, shots: shots.map(({ b64, ...r }) => r) };
  if (full && fulls.length) {
    row.full = join(out, `${name}-${w}-full.png`);
    await compose(w, fulls, row.full);
    row.fullShots = fulls.map(({ b64, ...r }) => r);
  }
  report.push(row);
}
await browser.close();
writeFileSync(join(out, `${name}.json`), JSON.stringify(report, null, 1));
console.log(report.map((r) => `${r.width}px → ${r.file}${r.full ? ` + ${r.full}` : ""} · ${r.shots.map((s) => `${s.label} ${s.status ?? s.err}`).join(" / ")}`).join("\n"));

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
    .map((s) => `<figure style="margin:0;width:${w}px"><figcaption style="height:40px;line-height:40px;padding:0 8px">${s.label} · ${w}px · ${s.status ?? s.err ?? "?"}${s.cut ? ` · 위 ${FULL_MAX}px 까지` : ""}</figcaption>${
      s.parts ? `<div style="width:${w}px;height:${s.h}px;overflow:hidden">${s.parts.map((p) => `<div style="overflow:hidden;width:${w}px"><img src="data:image/png;base64,${p.b64}" style="display:block;width:${w}px;margin-top:${p.skip ? -p.skip : 0}px"></div>`).join("")}</div>`
      : s.b64 ? `<img src="data:image/png;base64,${s.b64}" style="display:block;width:${w}px">` : "<p>찍지 못함</p>"}</figure>`)
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
      // 전체 페이지 = 한 화면씩 내려가며 찍어 세로로 잇는다(창 크기를 바꾸지 않는다).
      //  · fullPage 옵션은 찍는 순간만 창을 늘려 WebGL 지도가 빈 면으로 찍혔다(2026-10-14 로컬 실측)
      //  · 창을 문서 높이로 늘리면 vh 로 정한 장면(스크롤 홈 190vh)이 같이 늘어 끝없이 길어진다
      //  · 스크롤로 움직이는 장면(주홍 선)은 내려가는 동안의 상태가 그대로 찍힌다
      const docH = Math.min(await page.evaluate(() => document.documentElement.scrollHeight).catch(() => h), FULL_MAX);
      const parts = [];
      for (let y = 0; y < docH; y += h) {
        await page.evaluate((yy) => scrollTo(0, yy), y);
        await page.waitForTimeout(500);
        const at = await page.evaluate(() => scrollY);
        const fb = await page.screenshot({ fullPage: false }).catch(() => null);
        if (fb) parts.push({ b64: fb.toString("base64"), skip: y - at }); // 끝 화면은 덜 내려가므로 겹친 만큼 잘라 낸다
        if (at < y) break;
      }
      const real = await page.evaluate(() => document.documentElement.scrollHeight).catch(() => docH);
      fulls.push({ label, url, status, err, h: Math.min(real, FULL_MAX), cut: real > FULL_MAX, parts });
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

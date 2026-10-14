// 디자인 시스템 「해도」 시안 3면(lab/ds/) — 숫자 = 데이터 파일(정체성 §2-1) · 외부 요청 0 · 360px 넘침 0 · 만든 사람 노트(지도·시뮬레이션).
// 공개 배포물에는 없다(SOUNDING_LAB=1 빌드에만).
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync, existsSync, mkdirSync } from "node:fs";
import { check } from "../tools-build/check-data-numbers.mjs";
const B = "/incheon-port-analysis/lab/ds";
// 노트 목록은 보고서 제목을 그대로 가져온다 — 보고서 원문도 원천이다
const DATA = ["analysis/terminal_monthly_long.csv", "data/derived/places.json", "data/sim/beer-game.json", "data/rooms.json", ...readdirSync("reports").filter((f) => f.endsWith(".md")).map((f) => `reports/${f}`)].map((f) => readFileSync(f, "utf-8"));

for (const f of ["index", "beer", "map", "note"]) {
  test(`§2-1 ${f}: 지면 숫자는 데이터 파일에만 있다`, () => {
    const r = check(readFileSync(`astro/dist/lab/ds/${f}.html`, "utf-8"), DATA);
    expect(r.bad).toEqual([]);
  });
  test(`화면 ${f}: 외부 요청 0 · 360px 넘침 0 · 오류 0`, async ({ page }, info) => {
    const ext = [], errors = [];
    await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { ext.push(r.request().url()); return r.abort(); });
    page.on("pageerror", (e) => errors.push(String(e)));
    if (info.project.name === "iphone-13") await page.setViewportSize({ width: 360, height: 720 });
    await page.goto(`${B}/${f}.html`, { waitUntil: "networkidle" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
    if (f === "beer" || f === "map") for (const k of ["why", "how", "limits"]) await expect(page.locator(`[data-note="${k}"]`)).not.toBeEmpty();
    expect(ext).toEqual([]);
    expect(errors).toEqual([]);
  });
}

// 지도 면이 실제로 그려졌는지 — 화면을 찍어 픽셀로 판정한다(2026-10-14 · Actions 에서 지도 칸이 통째로 빈 면이었는데 위 시험은 모두 통과했다).
// 타일이 있으면(CI 는 반드시) 바다·땅 두 면과 점(먹 · 주홍)이 다 보여야 한다. 타일이 없는 로컬은 점만 본다.
test("지도 면: 바탕·점이 실제로 그려졌다(픽셀 판정)", async ({ page }, info) => {
  const tiles = existsSync("astro/dist/tiles/incheon.pmtiles");
  if (process.env.CI) expect(tiles, "CI 에는 지도 타일이 있어야 한다 — 없으면 바탕을 증명할 수 없다").toBe(true);
  await page.goto(`${B}/map.html`, { waitUntil: "networkidle" });
  await page.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 });
  const st = await page.evaluate(() => window.__dsmap);
  expect(st.errors).toEqual([]);
  expect(await page.locator(".ds-label").count()).toBe(st.places);
  if (tiles) expect(st.base, "타일이 있는데 바탕 원천을 못 읽었다").toBe(true);
  mkdirSync("lab-out", { recursive: true });
  const shot = await page.locator("#ds-map").screenshot({ path: `lab-out/ds-map-${info.project.name}.png` });
  // 픽셀 세기는 브라우저 캔버스로(저장소에 PNG 해석 의존성을 늘리지 않는다)
  const n = await page.evaluate(async (b64) => {
    const img = new Image(); img.src = `data:image/png;base64,${b64}`; await img.decode();
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
    const g = c.getContext("2d"); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data;
    // 해도 팔레트 — 종이(땅) · 물 · 주홍(85% 위 종이) · 먹(85% 위 종이)
    const P = { paper: [245, 242, 235], water: [227, 222, 210], signal: [189, 82, 61], ink: [58, 56, 52] };
    const k = Object.fromEntries(Object.keys(P).map((x) => [x, 0]));
    for (let i = 0; i < d.length; i += 4) for (const [x, [r, gg, bb]] of Object.entries(P)) {
      if (Math.abs(d[i] - r) + Math.abs(d[i + 1] - gg) + Math.abs(d[i + 2] - bb) <= 24) { k[x]++; break; }
    }
    return { total: d.length / 4, ...k };
  }, shot.toString("base64"));
  info.annotations.push({ type: "map-pixels", description: JSON.stringify(n) });
  expect(n.signal, "주홍 점(가장 큰 문)이 안 보인다").toBeGreaterThan(300);
  expect(n.ink, "먹 점이 안 보인다").toBeGreaterThan(300);
  if (tiles) {
    expect(n.water / n.total, "바다 면이 안 그려졌다").toBeGreaterThan(0.05);
    expect(n.paper / n.total, "땅 면이 안 그려졌다").toBeGreaterThan(0.05);
  }
});

// 맥주 게임 첫 장면 — 누르기 전부터 그림이 있고, 막대를 움직이면 그림과 큰 숫자가 같이 바뀐다(ncase 원리). 개발 용어는 지면에 없다.
test("맥주 게임: 첫 화면에 그림 · 막대를 움직이면 그림이 바뀐다 · 개발 용어 0", async ({ page }) => {
  await page.goto(`${B}/beer.html`, { waitUntil: "networkidle" });
  await page.waitForSelector("#wave[data-ready]");
  const vh = page.viewportSize().height;
  // 큰 숫자까지는 키 800 이상 화면에서만 요구한다(iPhone 13 기기 묘사 390×664 에선 그림·막대까지가 첫 화면)
  for (const sel of vh >= 800 ? ["#wave svg", "#beta", "#amp"] : ["#wave svg", "#beta"]) {
    const b = await page.locator(sel).boundingBox();
    expect(b && b.y + b.height, `${sel} 가 첫 화면 안에 있어야 한다`).toBeLessThanOrEqual(vh);
  }
  expect(await page.locator("#wave polyline").count()).toBe(5);
  const before = { pts: await page.locator("#wave polyline").last().getAttribute("points"), amp: await page.locator("#amp").innerText() };
  await page.locator("#beta").fill("1");
  await expect(page.locator("#amp")).not.toHaveText(before.amp);
  expect(await page.locator("#wave polyline").last().getAttribute("points")).not.toBe(before.pts);
  const text = await page.locator("main, body").first().innerText();
  for (const w of ["씨앗", "증폭비", "seed", "β", "alpha", "beta"]) expect(text, `개발 용어 「${w}」`).not.toContain(w);
});

// 차트 신뢰(OWID 원리) — 차트가 있는 지면마다 갱신일·출처·CSV 꼬리가 있고, CSV 는 실제로 내려온다
test("차트마다 갱신일·출처·CSV 꼬리 · CSV 200", async ({ page, request }) => {
  for (const f of ["index", "beer", "map", "note"]) {
    await page.goto(`${B}/${f}.html`, { waitUntil: "networkidle" });
    const t = page.locator(".s-trust");
    expect(await t.count(), `${f} 신뢰 꼬리`).toBeGreaterThan(0);
    await expect(t.first().locator("[data-updated]")).toHaveCount(1);
    const href = await t.first().locator("a[download]").getAttribute("href");
    expect(href, `${f} CSV 고리`).toBeTruthy();
    if (href !== "#") { const r = await request.get(href); expect(r.status(), `${f} CSV`).toBe(200); expect(await r.text()).toContain("# 측심"); }
  }
});

// 홈 — 스크롤을 따라 주홍 선이 그려지고, 달 막대를 옮기면 큰 숫자가 바뀐다 · 방·노트는 콘텐츠 목록에서 자동
test("홈: 스크롤 선 · 달 막대 · 콘텐츠 목록 자동 배치", async ({ page }) => {
  await page.goto(`${B}/index.html`, { waitUntil: "networkidle" });
  const off = () => page.evaluate(() => parseFloat(getComputedStyle(document.getElementById("route")).strokeDashoffset));
  const a = await off();
  await page.evaluate(() => { const h = document.querySelector(".hero"); scrollTo(0, h.offsetHeight - innerHeight); });
  // 등심선이 많아 스크롤 처리가 늦을 수 있다 — 정해진 시간 대신 조건이 설 때까지 기다린다
  await expect.poll(off, { message: "끝까지 내리면 선이 다 그려진다", timeout: 10_000 }).toBeLessThan(a);
  const v = await page.locator("#now-v").innerText();
  await page.locator("#now-m").fill("0");
  await expect(page.locator("#now-v")).not.toHaveText(v);
  const rooms = JSON.parse(readFileSync("data/rooms.json", "utf-8"));
  await expect(page.locator(".s-index > li")).toHaveCount(rooms.rooms.length);
  expect(await page.locator(".s-notes li").count()).toBeGreaterThan(0);
  expect(await page.locator(".s-notes li[data-stage]").first().getAttribute("data-stage")).toMatch(/^(초안|갱신 중|정본)$/);
});

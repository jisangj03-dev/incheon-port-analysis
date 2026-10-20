// [2026-10-15 공개 전 개편 P0] 홈·지도 지면은 들어오자마자 클릭 없이 움직인다 · 만지면 멈췄다가 6초 뒤 다시 · 동작 줄이기만 예외.
// 판정 기준 = docs/측심_공개전개편_판정기준_선커밋_20261015.md P0.
// CI(소프트웨어 렌더)에서 지도 루프가 주 스레드를 오래 잡으므로 「그림이 바뀌었나」 대신 상태(돌고 있나 · 단계·달이 바뀌나)를 본다.
import { test, expect } from "@playwright/test";
import { labelHits } from "./label-hits.mjs";

const B = "/incheon-port-analysis";
test.setTimeout(120_000);

test("홈: 손대지 않아도 지도가 받아져 돌고(수도권 첫 화면) · 끌면 멈췄다가 6초 뒤 다시 · 멈춤 단추는 그대로", async ({ page }) => {
  await page.goto(`${B}/`, { waitUntil: "load" });
  // 아무 입력 없이 — 좁은 화면 포함
  await page.waitForSelector("#live-stage[data-ready='1']", { timeout: 30_000 });
  const st = () => page.evaluate(() => ({ run: window.__fm.running, tour: window.__fm.touring, zoom: window.__fm.cam.zoom }));
  await expect.poll(async () => (await st()).run, { timeout: 10_000, message: "손대지 않았는데 지도가 안 돈다" }).toBe(true);
  const s0 = await st();
  expect(s0.tour, "둘러보기가 켜져 있지 않다").toBe(true);
  expect(s0.zoom, "첫 화면이 수도권(가까이)이 아니다").toBeGreaterThan(7);
  // 끌기 — 카메라가 멈춘다
  await page.locator("#fm").scrollIntoViewIfNeeded(); // 좁은 화면은 지도가 글 아래에 있다 — 화면 밖 좌표엔 손이 안 닿는다
  const box = await page.locator("#fm").boundingBox();
  const cx = box.x + box.width * 0.7, cy = box.y + box.height * 0.6;
  const n0 = await page.evaluate(() => window.__fmStops || 0);
  await page.mouse.move(cx, cy); await page.mouse.down(); await page.mouse.move(cx + 60, cy, { steps: 4 }); await page.mouse.up();
  // 끌면 멈춘다 — CI 부하로 끌기 자체가 6초를 넘기면 이미 다시 돌고 있을 수 있어 「멈춘 기록」으로 본다
  expect(await page.evaluate(() => window.__fmStops || 0), "끌었는데 둘러보기가 안 멈췄다").toBeGreaterThan(n0);
  // 6초 뒤 다시
  const ms = await page.evaluate(() => window.__fmResumeMs);
  expect(ms).toBe(6000);
  await expect.poll(async () => (await st()).tour, { timeout: 25_000, intervals: [1000], message: "6초 뒤 다시 돌지 않는다(CI 는 타이머가 밀려 25초까지 본다 · QA 225)" }).toBe(true);
  // 「둘러보기 멈춤」 — 누르면 다시 누를 때까지 그대로
  await page.locator("#fm-tour").click();
  expect((await st()).tour).toBe(false);
  await expect(page.locator("#fm-tour")).toHaveAttribute("aria-pressed", "false");
  await page.waitForTimeout(7000);
  expect((await st()).tour, "멈춤 단추로 멈췄는데 저절로 다시 돈다").toBe(false);
  // 두 번째 누름 — CI(소프트웨어 렌더)에서 「stable」(연속 두 프레임 같은 자리) 대기가 120초를 넘겼다(QA 304 · 두 번 · 로컬 3/3 통과).
  // 첫 누름이 실제 클릭 가능성을 이미 쟀으니 여기는 상태 전환만 본다 — 단추 자리를 몇 번 재어 흔들림이 있으면 기록에 남긴다.
  const at = [];
  for (let i = 0; i < 4; i++) { const b = await page.locator("#fm-tour").boundingBox(); at.push(b && `${Math.round(b.x)},${Math.round(b.y)},${Math.round(b.width)}`); await page.waitForTimeout(150); }
  if (new Set(at).size > 1) test.info().annotations.push({ type: "단추 흔들림", description: at.join(" | ") });
  await page.locator("#fm-tour").click({ force: true });
  expect((await st()).tour).toBe(true);
});

test("홈: 동작 줄이기면 돌지 않는다", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(`${B}/`, { waitUntil: "load" });
  await page.waitForSelector("#live-stage[data-ready='1']", { timeout: 30_000 });
  const st = await page.evaluate(() => ({ run: window.__fm.running, tour: window.__fm.touring }));
  expect(st).toEqual({ run: false, tour: false });
  await expect(page.locator("#fm-tour")).toHaveAttribute("aria-pressed", "false");
});

test("공급망 따라가기: 맨 위에서 손대지 않으면 단계가 스스로 넘어간다 · 내리면 스크롤이 카메라", async ({ page }) => {
  await page.goto(`${B}/map/follow.html`, { waitUntil: "load" });
  await page.waitForSelector("#trip-stage[data-ready='1']", { timeout: 30_000 });
  const seen = new Set();
  await expect.poll(async () => { seen.add(await page.getAttribute(".story", "data-step")); return seen.size; },
    { timeout: 30_000, intervals: [500], message: "손대지 않았는데 단계가 안 넘어간다" }).toBeGreaterThan(1);
  await expect(page.locator("#trip-stage")).toHaveAttribute("data-auto", "1");
  // 내리면 자동 미리보기가 멈추고 스크롤 자리 단계가 된다
  await page.evaluate(() => { const el = document.querySelector('[data-s="customs"]'); scrollTo(0, el.getBoundingClientRect().top + scrollY - innerHeight * 0.3); });
  await expect.poll(async () => { await page.evaluate(() => window.__followPick?.()); return page.getAttribute(".story", "data-step"); }, { timeout: 15_000 }).toBe("customs");
  // 내린 자리에서는 자동 미리보기가 꺼져 있다(6초 뒤 다시 켜져도 맨 위가 아니면 돌지 않는다)
  await expect(page.locator("#trip-stage")).toHaveAttribute("data-auto", "0");
  await page.waitForTimeout(7000); await page.evaluate(() => window.__followPick?.());
  expect(await page.getAttribute(".story", "data-step")).toBe("customs");
});

test("선박 리플레이: 클릭 없이 달이 흐른다 · 동작 줄이기면 그대로", async ({ page, browser }) => {
  await page.goto(`${B}/map/vessels.html`, { waitUntil: "load" });
  const m0 = await page.getAttribute("#vr-chart", "data-month");
  await expect.poll(() => page.getAttribute("#vr-chart", "data-month"), { timeout: 10_000, message: "손대지 않았는데 달이 안 바뀐다" }).not.toBe(m0);
  const ctx = await browser.newContext({ reducedMotion: "reduce" });
  const p2 = await ctx.newPage();
  await p2.goto(`${B}/map/vessels.html`, { waitUntil: "load" });
  await p2.waitForTimeout(2500);
  expect(await p2.evaluate(() => window.__vrPlay.on)).toBe(false);
  await ctx.close();
});

// [2026-10-15 P0 · 단추 다섯] 지도 단추(아시아·수도권·인천·멈춤·관문 숫자)가 숫자판·범례와 겹치지 않는다 — 좁은 화면에서 두 줄로 넘쳐 범례를 덮었다
for (const w of [0, 320]) test(`홈: 지도 단추가 숫자판·범례와 겹치지 않는다${w ? ` · ${w}px` : ""}`, async ({ page }, info) => {
  if (w && info.project.name !== "iphone-13") return;
  if (w) await page.setViewportSize({ width: w, height: 640 });
  await page.goto(`${B}/`, { waitUntil: "load" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), "가로 넘침").toBeLessThanOrEqual(0);
  const r = await page.evaluate(() => {
    const box = (e) => e.getBoundingClientRect();
    const btns = [...document.querySelectorAll(".live__ctl .s-btn")].map(box), hud = [...document.querySelectorAll(".live__hud > p")].map(box);
    const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
    const right = document.querySelector(".live__stage").getBoundingClientRect().right;
    return { rows: new Set(btns.map((b) => Math.round(b.top))).size, tall: btns.filter((b) => b.height > 52).length, out: btns.filter((b) => b.right > right + 1).length, overlaps: btns.flatMap((b, i) => hud.filter((h) => hit(b, h)).map(() => i)) };
  });
  expect(r.overlaps, "단추가 숫자판·범례를 덮는다").toEqual([]);
  expect(r.rows, "단추가 두 줄로 넘친다").toBe(1);
  expect(r.tall, "단추 글자가 두 줄로 꺾인다").toBe(0);
  expect(r.out, "단추가 화면 밖으로 나간다").toBe(0);
});

// [2026-10-20 #67 ③] 검수 크기 1568×709 · 움직이는 지도에서도 이름표 × 글·단추 겹침 0 — 움직이는 지도 시험은 이 파일에 모아 한 작업자에서 차례로(동시에 돌면 CI 에서 지도 둘이 CPU 를 나눠 120초를 넘겼다 · QA 288)
test("히어로 — 1568×709 움직이는 지도에서도 이름표 × 글·단추 겹침 0", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "크기를 시험 안에서 바꾼다 — 한 번이면 된다");
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1568, height: 709 });
  await page.goto(`${B}/`, { waitUntil: "load" });
  const bad = [];
  for (let k = 0; k < 6; k++) { await page.waitForTimeout(1500); for (const h of await labelHits(page)) bad.push(h); }
  expect([...new Set(bad)], [...new Set(bad)].join("\n")).toEqual([]);
});

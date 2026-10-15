// [2026-10-15 공개 전 개편 P0] 홈·지도 지면은 들어오자마자 클릭 없이 움직인다 · 만지면 멈췄다가 6초 뒤 다시 · 동작 줄이기만 예외.
// 판정 기준 = docs/측심_공개전개편_판정기준_선커밋_20261015.md P0.
// CI(소프트웨어 렌더)에서 지도 루프가 주 스레드를 오래 잡으므로 「그림이 바뀌었나」 대신 상태(돌고 있나 · 단계·달이 바뀌나)를 본다.
import { test, expect } from "@playwright/test";

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
  await page.mouse.move(cx, cy); await page.mouse.down(); await page.mouse.move(cx + 60, cy, { steps: 4 }); await page.mouse.up();
  expect((await st()).tour, "끌었는데 둘러보기가 안 멈췄다").toBe(false);
  // 6초 뒤 다시
  const ms = await page.evaluate(() => window.__fmResumeMs);
  expect(ms).toBe(6000);
  await expect.poll(async () => (await st()).tour, { timeout: 12_000, intervals: [1000], message: "6초 뒤 다시 돌지 않는다" }).toBe(true);
  // 「둘러보기 멈춤」 — 누르면 다시 누를 때까지 그대로
  await page.locator("#fm-tour").click();
  expect((await st()).tour).toBe(false);
  await expect(page.locator("#fm-tour")).toHaveAttribute("aria-pressed", "false");
  await page.waitForTimeout(7000);
  expect((await st()).tour, "멈춤 단추로 멈췄는데 저절로 다시 돈다").toBe(false);
  await page.locator("#fm-tour").click();
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

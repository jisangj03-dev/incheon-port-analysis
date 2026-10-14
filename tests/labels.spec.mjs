// 라벨 겹침 0(2026-10-14 채팅 검수 ① — 지도 390 첫 화면에서 인천공항·남항·국제여객부두 이름표가 겹쳐 안 읽혔다).
// 모든 공개 면 × 두 폭(desktop-1440 · iphone-13=390) · 지도는 정지 그림과 움직이는 지도 둘 다 · 따라가기는 단계마다 · 선박·맥주 게임은 달·막대를 끝까지 옮긴 상태까지.
// 판정 = 보이는 라벨끼리 경계 상자 교차 0(tests/lib/label-overlap.mjs) · 그림 속 글자 명암비 4.5:1(채팅 검수 ② · tests/lib/contrast.mjs).
import { test, expect } from "@playwright/test";
import { overlaps } from "./lib/label-overlap.mjs";
import { lowContrast } from "./lib/contrast.mjs";
const B = "/incheon-port-analysis";
const PAGES = ["/", "/map.html", "/map/follow.html", "/map/vessels.html", "/sim/", "/sim/beer-game.html", "/sim/forecast.html", "/notes.html", "/notes/port-yoy.html", "/notes/ai-ops.html", "/about.html", "/tools/warehouse-map.html"];
const check = async (page, where) => { const r = await overlaps(page); expect(r.out, `${where} 라벨 겹침(보이는 라벨 ${r.n}개)`).toEqual([]); return r.n; };

for (const p of PAGES) test(`라벨 겹침 0 — ${p}`, async ({ page }) => {
  await page.goto(`${B}${p}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await check(page, p);
  expect(await lowContrast(page), `${p} 그림 속 글자 명암비`).toEqual([]);
});

test("라벨 겹침 0 — 움직이는 지도(달 처음·끝)", async ({ page }) => {
  await page.goto(`${B}/map.html`, { waitUntil: "networkidle" });
  await page.mouse.move(20, 20);
  await page.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 });
  await page.click("#ds-play"); // 자동 재생을 멈춘다
  for (const v of ["0", await page.locator("#ds-m").getAttribute("max")]) {
    await page.locator("#ds-m").fill(v);
    await page.waitForTimeout(300);
    expect(await check(page, `지도 달 ${v}`), "지도 이름표가 있어야 한다").toBeGreaterThan(4);
    expect(await lowContrast(page), `지도 달 ${v} 명암비`).toEqual([]);
  }
});

test("라벨 겹침 0 — 공급망 따라가기 단계마다", async ({ page }) => {
  await page.goto(`${B}/map/follow.html`, { waitUntil: "networkidle" });
  for (const id of await page.locator(".st[data-s]").evaluateAll((a) => a.map((x) => x.getAttribute("data-s")))) {
    await page.evaluate((id) => { const el = document.querySelector(`[data-s="${id}"]`); scrollTo(0, el.getBoundingClientRect().top + scrollY - innerHeight * 0.3); }, id);
    await expect.poll(() => page.getAttribute(".story", "data-step"), { timeout: 5_000 }).toBe(id);
    // 꼬리표는 0.5초에 걸쳐 나타나고 사라진다(장면마다 위치를 다시 잡는다) — CI 는 장면 간격이 2초를 넘는 때가 있어(QA 122) 전환이 끝나기를 최대 15초 기다린다. 끝난 뒤에도 겹치면 실패
    await expect.poll(async () => (await overlaps(page)).out, { timeout: 15_000, message: `따라가기 ${id} 라벨 겹침` }).toEqual([]);
  }
});

test("라벨 겹침 0 — 선박 리플레이 달 처음·끝 · 맥주 게임 막대 양 끝", async ({ page }) => {
  await page.goto(`${B}/map/vessels.html`, { waitUntil: "networkidle" });
  for (const v of ["0", await page.locator("#vr-m").getAttribute("max")]) { await page.locator("#vr-m").fill(v); await page.waitForTimeout(200); await check(page, `선박 ${v}`); }
  await page.goto(`${B}/sim/beer-game.html`, { waitUntil: "networkidle" });
  await page.waitForSelector("#wave[data-ready]");
  for (const v of ["0", "0.5", "1"]) { await page.locator("#beta").fill(v); await page.waitForTimeout(200); await check(page, `맥주 게임 ${v}`); expect(await lowContrast(page), `맥주 게임 ${v} 명암비`).toEqual([]); }
});

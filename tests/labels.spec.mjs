// 라벨 겹침 0(2026-10-14 채팅 검수 ① — 지도 390 첫 화면에서 인천공항·남항·국제여객부두 이름표가 겹쳐 안 읽혔다).
// 모든 공개 면 × 두 폭(desktop-1440 · iphone-13=390) · 지도는 정지 그림과 움직이는 지도 둘 다 · 따라가기는 단계마다 · 선박·맥주 게임은 달·막대를 끝까지 옮긴 상태까지.
// 판정 = 보이는 라벨끼리 경계 상자 교차 0(tests/lib/label-overlap.mjs) · 그림 속 글자 명암비 4.5:1(채팅 검수 ② · tests/lib/contrast.mjs).
import { test, expect } from "@playwright/test";
import { overlaps } from "./lib/label-overlap.mjs";
import { lowContrast } from "./lib/contrast.mjs";
const B = "/incheon-port-analysis";
const PAGES = ["/", "/tools/", "/map/vessels.html", "/sim/beer-game.html", "/sim/forecast.html", "/notes.html", "/notes/port-yoy.html", "/about.html"];
const check = async (page, where) => { const r = await overlaps(page); expect(r.out, `${where} 라벨 겹침(보이는 라벨 ${r.n}개)`).toEqual([]); return r.n; };

for (const p of PAGES) test(`라벨 겹침 0 — ${p}`, async ({ page }) => {
  await page.goto(`${B}${p}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await check(page, p);
  expect(await lowContrast(page), `${p} 그림 속 글자 명암비`).toEqual([]);
});

test("라벨 겹침 0 — 선박 리플레이 달 처음·끝 · 맥주 게임 막대 양 끝", async ({ page }) => {
  await page.goto(`${B}/map/vessels.html`, { waitUntil: "networkidle" });
  for (const v of ["0", await page.locator("#vr-m").getAttribute("max")]) { await page.locator("#vr-m").fill(v); await page.waitForTimeout(200); await check(page, `선박 ${v}`); }
  await page.goto(`${B}/sim/beer-game.html`, { waitUntil: "networkidle" });
  await page.waitForSelector("#wave[data-ready]");
  for (const v of ["0", "0.5", "1"]) { await page.locator("#beta").fill(v); await page.waitForTimeout(200); await check(page, `맥주 게임 ${v}`); expect(await lowContrast(page), `맥주 게임 ${v} 명암비`).toEqual([]); }
});

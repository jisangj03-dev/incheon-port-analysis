// 자동 갱신 신선도(2026-10-21 선장님 질문 「사이트 숫자는 매번 최신이어야 하지 않나?」) — data/derived/freshness.json(tools-build/refresh.py 가 쓴다).
//  ① 지면 기준기가 원천이 낸 마지막 기준기보다 뒤처지면 빨강(원천이 냈는데 지면이 안 바뀌었다).
//  ② 마지막 확인이 없거나 오래면 빨강(갱신 사슬이 멈췄다 — 「지난 숫자가 새것처럼」의 다른 얼굴).
//  ③ 신선도를 다는 지면은 출처 줄에 「원천 확인 · 다음 공표 예정」이 실제로 보인다.
// 빨강이면 refresh 워크플로가 main 에 쓰지 않고 배포하지 않는다 — 이슈가 열린다.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const BASE = "/incheon-port-analysis";
const F = JSON.parse(readFileSync("data/derived/freshness.json", "utf-8"));
const MAX_AGE = 10; // 일 — refresh 는 매일 돌고, 확인일만 바뀐 날은 7일에 한 번 커밋한다
const today = new Date().toISOString().slice(0, 10);
const days = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);

test.describe("신선도 — 원천 대비", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "desktop-1440", "데이터 판정은 한 번만"));
  for (const [id, r] of Object.entries(F.sources)) {
    test(`${id} — 지면 ${r.ours} ≥ 원천 ${r.source_latest}`, () => {
      expect(r.ours, "지면 기준기").toBeTruthy();
      expect(r.source_latest, "원천 마지막 기준기(확인한 적 없음)").toBeTruthy();
      expect(String(r.ours) >= String(r.source_latest), `${r.label}: 원천은 ${r.source_latest} 까지 냈는데 지면은 ${r.ours}`).toBe(true);
    });
    test(`${id} — 마지막 확인 ${MAX_AGE}일 이내`, () => {
      expect(r.checked, `${r.label}: 원천에 닿은 적이 없다${r.last_error ? ` — ${r.last_error}` : ""}`).toBeTruthy();
      expect(days(r.checked, today), `${r.label}: 마지막 확인 ${r.checked}${r.last_error ? ` — 마지막 오류 ${r.last_error}` : ""}`).toBeLessThanOrEqual(MAX_AGE);
      expect(r.next_expected, "다음 공표 예정").toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
  }
});

const PAGES = ["/", "/tools/chokepoint.html", "/tools/import-cost.html", "/tools/trade-race.html", "/notes/port-yoy.html", "/sim/forecast.html", "/map/vessels.html"];
test.describe("신선도 — 지면 출처 줄", () => {
  for (const p of PAGES) {
    test(p, async ({ page }) => {
      await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
      await page.goto(BASE + p, { waitUntil: "domcontentloaded" });
      const t = (await page.locator("[data-fresh]").allTextContents()).join(" | ");
      expect(t, "출처 줄의 신선도 토막").toContain("다음 공표 예정");
      expect(t, "원천 확인").toMatch(/원천 확인 \d{4}-\d{2}-\d{2}/);
    });
  }
});

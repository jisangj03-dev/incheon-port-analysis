// 자동 갱신 신선도(2026-10-21 선장님 질문 「사이트 숫자는 매번 최신이어야 하지 않나?」) — data/derived/freshness.json(tools-build/refresh.py 가 쓴다).
//  ① 지면 기준기가 원천이 낸 마지막 기준기보다 뒤처지면 빨강(원천이 냈는데 지면이 안 바뀌었다).
//  ② 마지막 확인이 없거나 오래면 빨강(갱신 사슬이 멈췄다 — 「지난 숫자가 새것처럼」의 다른 얼굴).
//  ③ 신선도를 다는 지면은 출처 줄에 「원천 확인 · 다음 공표 예정」이 실제로 보인다.
// 빨강이면 refresh 워크플로가 main 에 쓰지 않고 배포하지 않는다 — 이슈가 열린다.
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const BASE = "/incheon-port-analysis";
const F = JSON.parse(readFileSync("data/derived/freshness.json", "utf-8"));
const MAX_AGE = 10; // 일 — refresh 는 매일 돌고, 확인일만 바뀐 날은 7일에 한 번 커밋한다
const today = new Date().toISOString().slice(0, 10);

// [2026-10-22 갱신 무인화 ④ · docs/측심_갱신무인화_판정기준_선커밋_20261022.md] 원천 하나가 끊기거나 뒤처져도 **배포는 막지 않는다**(다른 원천 갱신은 나간다).
//   대신 그 원천을 쓰는 지면마다 「갱신 지연」이 보여야 한다 — 지난 숫자를 새것처럼 내보내지 않는 것이 이 시험의 일이다. 사람 손은 refresh 가 이슈(자동경보)로 올린다.
const days = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);
const shouldDelay = (r) => !!(r.behind || ["auth", "format"].includes(r.fail_kind) || (r.fail_kind && r.fail_since && days(r.fail_since, F.made) + 1 >= 2) || !r.checked || days(r.checked, F.made) > (r.max_age ?? MAX_AGE));
const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : [p]; });
const built = () => walk("astro/dist").filter((f) => f.endsWith(".html") && !/\/(docs|analysis|_a)\//.test(f)).map((f) => [f, readFileSync(f, "utf-8")]);

test.describe("신선도 — 원천 대비 · 갱신 지연 표시", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "desktop-1440", "데이터 판정은 한 번만"));
  for (const [id, r] of Object.entries(F.sources)) {
    test(`${id} — 지연 판정이 규칙과 같다 · 지연이 아니면 지면 ≥ 원천 · 확인 ${r.max_age ?? MAX_AGE}일 이내`, () => {
      expect(!!r.delayed, `${r.label}: 지연 판정(${r.delay_reason})이 규칙과 다르다`).toBe(shouldDelay(r));
      if (!r.delayed) {
        expect(String(r.ours) >= String(r.source_latest), `${r.label}: 원천은 ${r.source_latest} 까지 냈는데 지면은 ${r.ours}`).toBe(true);
        expect(days(r.checked, today), `${r.label}: 마지막 확인 ${r.checked}`).toBeLessThanOrEqual((r.max_age ?? MAX_AGE) + 1);
      }
      expect(r.next_expected, "다음 공표 예정").toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
  }
  test("원천마다 그것을 쓰는 지면이 있다(지연을 걸 자리) · 지연 원천을 쓰는 지면은 「갱신 지연」이 보이고, 아니면 없다", () => {
    const pages = built();
    const ids = (h) => [...h.matchAll(/data-fresh-ids="([^"]*)"/g)].flatMap((m) => m[1].split(",")).filter(Boolean);
    const wired = new Set(pages.flatMap(([, h]) => ids(h)));
    expect(Object.keys(F.sources).filter((k) => !wired.has(k)), "지연을 걸 지면이 없는 원천").toEqual([]);
    const late = new Set(Object.entries(F.sources).filter(([, r]) => r.delayed).map(([k]) => k));
    const wrong = pages.filter(([, h]) => ids(h).some((k) => late.has(k)) !== /data-delay/.test(h)).map(([f]) => f);
    expect(wrong, "갱신 지연 표시가 원천 상태와 다르다").toEqual([]);
  });
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

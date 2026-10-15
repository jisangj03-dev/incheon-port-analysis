// 지면 눈 검사(2026-10-14 채팅 검수) — 출고 검사의 「차트 주 계열 가시」 · 잘린 글자 0 · 상자 없음.
// 모든 공개 면 × 두 폭(desktop-1440 · iphone-13). 주 계열이 있는 차트 지면은 1440 첫 화면 안에 주 계열이 들어와야 한다.
import { test, expect } from "@playwright/test";
import { mainSeries, clipped, boxes } from "./lib/chart-checks.mjs";
const B = "/incheon-port-analysis";
import { readdirSync } from "node:fs";
// 공개 면 전부 + 노트가 링크하는 보고서 전 편. 옛 도구 둘(계산기·창고 배치도 — 메뉴에서 뺐다)은 입력 칸·지도 칸이 곧 생김새라 상자 검사에서 뺀다.
const REPORTS = readdirSync("astro/dist/reports").filter((f) => f.endsWith(".html") && f !== "index.html").map((f) => `/reports/${f}`);
const PAGES = ["/", "/map.html", "/map/follow.html", "/map/vessels.html", "/sim/", "/sim/beer-game.html", "/sim/forecast.html", "/notes.html", "/notes/port-yoy.html", "/notes/ai-ops.html", "/about.html", "/data.html", ...REPORTS];
// 주 계열 차트(주인공 = 주홍) — 지면 · 기다릴 것
const MAIN = { "/map/vessels.html": "#vr-chart svg", "/sim/forecast.html": "#fc-chart[data-ready] svg", "/sim/beer-game.html": "#wave[data-ready] svg" };

for (const p of PAGES) test(`눈 검사 — ${p}`, async ({ page }, info) => {
  await page.goto(encodeURI(`${B}${p}`), { waitUntil: "networkidle" });
  if (MAIN[p]) await page.waitForSelector(MAIN[p]);
  await page.waitForTimeout(300);
  expect(await clipped(page), `${p} 잘린 글자`).toEqual([]);
  expect(await boxes(page), `${p} 상자(테두리 + 바탕)`).toEqual([]);
  if (MAIN[p]) {
    const m = await mainSeries(page);
    expect(m.length, `${p} 주 계열([data-main])`).toBeGreaterThan(0);
    for (const s of m) {
      expect(s.signal, `${p} ${s.name} 주홍(신호색) — 지금 ${s.stroke}`).toBe(true);
      expect(s.w + s.h, `${p} ${s.name} 크기`).toBeGreaterThan(20);
      expect(s.inside, `${p} ${s.name} 그림 칸 안`).toBe(true);
      expect(s.front, `${p} ${s.name} 맨 앞(다른 선보다 뒤에 그림)`).toBe(true);
      expect(s.opacity, `${p} ${s.name} 불투명`).toBeGreaterThan(0.5);
      if (info.project.name === "desktop-1440") expect(s.top, `${p} ${s.name} 1440 첫 화면 안`).toBeLessThan(page.viewportSize().height);
    }
  }
});

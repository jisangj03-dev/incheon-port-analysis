// Chart.js 4.5.1 · Observable Plot 0.6.17 — Astro(Vite)가 저장소 안 번들로 묶은 것이 실제로 그려지는가.
// CDN 이 아니라는 증거 = 지면이 localhost 밖으로 요청을 하나도 안 낸다.
import { test, expect } from "@playwright/test";

test("두 차트가 그려지고 외부 요청 0", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  const external = [];
  const errors = [];
  page.on("request", (r) => {
    const h = new URL(r.url()).hostname;
    if (h !== "localhost" && h !== "127.0.0.1") external.push(r.url());
  });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto("http://127.0.0.1:4174/");
  await page.waitForFunction(() => window.__charts);
  const c = await page.evaluate(() => window.__charts);
  expect(errors).toEqual([]);
  expect(c.chartjs).toBe(3);                 // 막대 셋(지금 방식·견적 A·견적 B)
  expect(c.plotRects).toBeGreaterThanOrEqual(3);
  // 캔버스에 실제로 칠해졌는가 — 투명이 아닌 화소가 있다
  const painted = await page.evaluate(() => {
    const cv = document.getElementById("cj");
    const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height).data;
    let n = 0;
    for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++;
    return n;
  });
  expect(painted).toBeGreaterThan(100);
  expect(external, "외부 요청 0").toEqual([]);
});

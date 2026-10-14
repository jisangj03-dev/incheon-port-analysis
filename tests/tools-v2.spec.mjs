// 판정 v2 도구 실행 증명 — lab/tools-v2.html(SOUNDING_LAB=1 빌드에만 있다)이 외부 요청 없이 다 도는가.
import { test, expect } from "@playwright/test";
import { existsSync } from "node:fs";

test("maplibre·pmtiles·basemaps·deck.gl·three·gsap·lenis·Plot·d3 — 외부 요청 0", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  test.skip(!existsSync("astro/dist/lab/tools-v2.html"), "SOUNDING_LAB=1 빌드가 아니다");
  const external = [], errors = [];
  // 개편 기준 17의 예외(Cloudflare 분석 둘)는 세지 않고 끊는다. 그 밖은 하나라도 있으면 실패.
  const ALLOWED = new Set(["static.cloudflareinsights.com", "cloudflareinsights.com"]);
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => {
    if (!ALLOWED.has(new URL(r.request().url()).hostname)) external.push(r.request().url());
    return r.abort();
  });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto("/incheon-port-analysis/lab/tools-v2.html");
  await page.waitForFunction(() => (window).__proof && (window).__proof.deck === "rendered", null, { timeout: 45_000 });
  const p = await page.evaluate(() => (window).__proof);
  console.log("증명:", JSON.stringify(p));
  expect(p.maplibre).toBe("6.11.2");
  expect(String(p.workerUrl)).toContain("/incheon-port-analysis/vendor/maplibre/maplibre-gl-worker.mjs");
  expect(p.three).toBe("186");
  expect(p.plotRects).toBe(3);
  expect(p.d3).toBe(6);
  expect(p.basemapLayers).toBeGreaterThan(20);
  expect(p.gsap && p.lenis).toBe(true);
  expect(errors).toEqual([]);
  expect(external, "외부 요청 0").toEqual([]);
});

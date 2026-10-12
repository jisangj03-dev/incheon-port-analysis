// 3D 지도(기준 20) — 정지 그림이 먼저 · 누르면 maplibre+deck.gl 이 같은 주소 파일로 뜬다 · 외부 요청 0 · 시간축이 돈다.
import { test, expect } from "@playwright/test";

test("정지 그림 → 3D · 외부 요청 0 · 시간축", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  const ext = [], errors = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => { if (!/cloudflareinsights\.com$/.test(new URL(r.request().url()).hostname)) ext.push(r.request().url()); return r.abort(); });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto("/incheon-port-analysis/map.html");
  await expect(page.locator(".mp__still")).toBeVisible();
  await page.click("#open3d");
  await page.waitForFunction(() => window.__map3d, null, { timeout: 45_000 });
  await expect(page.locator(".mp__still")).toBeHidden();
  await expect(page.locator("#map canvas").first()).toBeVisible();
  const before = await page.locator("#month-out").innerText();
  await page.locator("#month").fill("0");
  await expect(page.locator("#month-out")).not.toHaveText(before);
  await expect(page.locator(".mp__stage [data-updated]")).toHaveCount(1);
  await expect(page.locator("#attrib")).toContainText("OpenStreetMap");
  // A-6: 자리표 출처가 화면에 — OSM 으로 바꾼 곳과 개략으로 남은 곳을 갈라 적는다
  await expect(page.locator(".mp__note")).toContainText("OpenStreetMap 시설 면의 중심점");
  await expect(page.locator(".mp__note")).toContainText("남항은 개략 위치");
  expect(errors).toEqual([]);
  expect(ext).toEqual([]);
});

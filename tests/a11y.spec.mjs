// 접근성(2026-10-21 전수조사) — 전 지면에 axe-core(WCAG 2.0·2.1 A/AA · 2.2 AA)를 돌려 심각·치명 위반 0.
// 전수조사 기계 판정(tests/audit/audit.mjs)이 처음 잡은 것: 로고 링크 이름이 보이는 글자를 안 담음(전 지면) · 트리맵 칸 글자 대비 4.45 · 버튼을 품은 role=img.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const AXE = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf-8");
const sitemap = readFileSync("astro/dist/sitemap.xml", "utf-8");
const PAGES = [...sitemap.matchAll(/<loc>https:\/\/jisangj03-dev\.github\.io([^<]+)<\/loc>/g)].map((m) => decodeURI(m[1]));

for (const p of PAGES) {
  test(`axe 심각·치명 0 — ${p}`, async ({ page }) => {
    await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
    await page.goto(p, { waitUntil: "load" });
    await page.waitForTimeout(800);
    await page.addScriptTag({ content: AXE });
    const v = await page.evaluate(async () => (await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] }, resultTypes: ["violations"] }))
      .violations.filter((x) => x.impact === "serious" || x.impact === "critical").map((x) => `${x.id}(${x.impact}) ${x.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(", ")}`));
    expect(v, v.join("\n")).toEqual([]);
  });
}

// 레이더 「마감 지남」 — 스냅샷보다 늦은 날에만 생기는 상태라 그날의 날짜에 기대지 않고 시계를 60일 뒤로 돌려 늘 본다(사고 141)
test("axe 심각·치명 0 — 레이더 마감 지남 상태(시계 +60일)", async ({ page }) => {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.clock.install({ time: Date.now() + 60 * 864e5 });
  await page.goto("/incheon-port-analysis/tools/radar.html", { waitUntil: "load" });
  expect(await page.locator("#rd-s > li.gone, #rd-r > li.gone").count(), "마감 지남 공고가 그려졌다").toBeGreaterThan(0);
  await page.addScriptTag({ content: AXE });
  const v = await page.evaluate(async () => (await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] }, resultTypes: ["violations"] }))
    .violations.filter((x) => x.impact === "serious" || x.impact === "critical").map((x) => `${x.id}(${x.impact}) ${x.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(", ")}`));
  expect(v, v.join("\n")).toEqual([]);
});

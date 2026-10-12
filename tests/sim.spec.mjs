// 몬테카를로(2단계 시뮬레이션 1) — 흔들기 폭 0 이면 계산기와 같은 답 · 같은 씨앗이면 같은 결과 · 외부 요청 0.
import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
const req = createRequire(import.meta.url);

test("node: 폭 0 = 계산기 답(4,044/2,805/2,960) · 같은 씨앗 = 같은 결과", () => {
  const C = req("../assets/js/cost-check.js"), S = req("../assets/js/cost-sim.js");
  const s = C.SAMPLE;
  const st = { ship: s.ship, ret: s.ret, blocks: s.blocks.map((b) => b.map((r) => [r[0], r[1] === null ? "" : String(r[1]), r[2] === null ? "" : String(r[2])])) };
  const z = S.simulate(C, st, { runs: 50, volSwing: 0, unknownMax: [0, 0, 0] });
  expect(z.map((x) => Math.round(x.p50))).toEqual([4044, 2805, 2960]);
  const a = S.simulate(C, st, { runs: 2000, volSwing: 0.2, seed: 7 }), b = S.simulate(C, st, { runs: 2000, volSwing: 0.2, seed: 7 });
  expect(a.map((x) => x.pBest)).toEqual(b.map((x) => x.pBest));
  expect(a.reduce((t, x) => t + (x.pBest || 0), 0)).toBeCloseTo(1, 6);
});

test("화면: 계산기 주소(?s=)를 받아 돌리고 분포를 그린다 · 외부 요청 0", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => { if (!/cloudflareinsights\.com$/.test(new URL(r.request().url()).hostname)) ext.push(r.request().url()); return r.abort(); });
  await page.goto("/incheon-port-analysis/tools/logistics-cost.html");
  await page.click("#sample");
  await page.waitForFunction(() => location.search.includes("s="));
  const s = new URL(page.url()).searchParams.get("s");
  await page.goto(`/incheon-port-analysis/tools/simulate.html?s=${s}`);
  await page.waitForFunction(() => window.__sim);
  const sim = await page.evaluate(() => window.__sim);
  expect(sim.length).toBe(3);
  await expect(page.locator("#src-note")).toContainText("계산기에서 넣은 값");
  await expect(page.locator("#hist svg").first()).toBeVisible({ timeout: 10_000 });
  expect(ext).toEqual([]);
});

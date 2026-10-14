// 디자인 시스템 「해도」 시안 3면(lab/ds/) — 숫자 = 데이터 파일(정체성 §2-1) · 외부 요청 0 · 360px 넘침 0 · 만든 사람 노트(지도·시뮬레이션).
// 공개 배포물에는 없다(SOUNDING_LAB=1 빌드에만).
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync } from "node:fs";
import { check } from "../tools-build/check-data-numbers.mjs";
const B = "/incheon-port-analysis/lab/ds";
// 노트 목록은 보고서 제목을 그대로 가져온다 — 보고서 원문도 원천이다
const DATA = ["analysis/terminal_monthly_long.csv", "data/derived/places.json", "data/sim/beer-game.json", ...readdirSync("reports").filter((f) => f.endsWith(".md")).map((f) => `reports/${f}`)].map((f) => readFileSync(f, "utf-8"));

for (const f of ["index", "beer", "map"]) {
  test(`§2-1 ${f}: 지면 숫자는 데이터 파일에만 있다`, () => {
    const r = check(readFileSync(`astro/dist/lab/ds/${f}.html`, "utf-8"), DATA);
    expect(r.bad).toEqual([]);
  });
  test(`화면 ${f}: 외부 요청 0 · 360px 넘침 0 · 오류 0`, async ({ page }, info) => {
    const ext = [], errors = [];
    await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { ext.push(r.request().url()); return r.abort(); });
    page.on("pageerror", (e) => errors.push(String(e)));
    if (info.project.name === "iphone-13") await page.setViewportSize({ width: 360, height: 720 });
    await page.goto(`${B}/${f}.html`, { waitUntil: "networkidle" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
    if (f !== "index") for (const k of ["why", "how", "limits"]) await expect(page.locator(`[data-note="${k}"]`)).not.toBeEmpty();
    expect(ext).toEqual([]);
    expect(errors).toEqual([]);
  });
}

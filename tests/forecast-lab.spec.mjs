// 수요예측 실험실(정체성 전환 §3-4) — 화면 수치 = 데이터 파일(§2-1) · 채점 = analysis/forecast_teu.py 와 같은 값 · 노트 3줄 · AI 표기 · 360px · 외부 요청 0.
// 지면은 lab/(SOUNDING_LAB=1 빌드에만) — 공개 배포물에는 없다.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { check } from "../tools-build/check-data-numbers.mjs";
const PAGE = "/incheon-port-analysis/lab/forecast.html";
const py = () => JSON.parse(execFileSync("python3", ["analysis/forecast_teu.py", "--json"], { encoding: "utf-8" }));

test("§2-1: 지면 숫자는 원장·대상 계열·실험실 글·채점 결과에만 있다", () => {
  const files = ["data/forecast/incheon_container_teu.csv", "analysis/terminal_monthly_long.csv", "data/forecast/lab.json"].map((f) => readFileSync(f, "utf-8"));
  const r = check(readFileSync("astro/dist/lab/forecast.html", "utf-8"), [...files, JSON.stringify(py())]);
  expect(r.checked).toBeGreaterThan(10);
  expect(r.bad).toEqual([]);
});

test("화면: 원장 행 · 채점이 파이썬과 같다 · 노트 3줄 · 360px · 외부 요청 0", async ({ page }, info) => {
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { if (!/cloudflareinsights\.com$/.test(new URL(r.request().url()).hostname)) ext.push(r.request().url()); return r.abort(); });
  if (info.project.name === "iphone-13") await page.setViewportSize({ width: 360, height: 720 });
  await page.goto(PAGE);
  const ledgerRows = readFileSync("data/forecast/incheon_container_teu.csv", "utf-8").trim().split(/\r?\n/).length - 1;
  await expect(page.locator("#h-ledger + .tbl tbody tr")).toHaveCount(ledgerRows / 2); // B·M1 이 한 줄
  const s = py();
  if (s.matured === 0) await expect(page.locator("[data-score=none]")).toBeVisible();
  else for (const [m, d] of Object.entries(s.models)) await expect(page.locator(`[data-model=${m}] [data-mape]`)).toHaveText(d.mape_pct);
  for (const k of ["why", "how", "limits"]) await expect(page.locator(`[data-note="${k}"]`)).not.toBeEmpty();
  await expect(page.locator("[data-ai-mark]")).toContainText("AI 정리");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  expect(ext).toEqual([]);
});

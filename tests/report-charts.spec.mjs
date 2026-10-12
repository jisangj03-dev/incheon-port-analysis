// 보고서 ② 층 위젯 — 위젯이 쓰는 계열(= 내려받는 CSV)이 발행본의 결론 수치를 그대로 재현하는가, 그리고 화면이 도는가.
// 위젯은 새 결론을 만들지 않는다 — 같은 정의의 값을 범위·보기만 바꿔 보인다. 그러니 발행 수치가 안 나오면 위젯이 틀린 것이다.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const read = (n) => {
  const [, ...lines] = readFileSync(`astro/dist/data/${n}.csv`, "utf-8").replace(/^﻿/, "").split("\n").filter(Boolean);
  // 품목 이름에 쉼표가 있다(따옴표로 싼 칸) — 쉼표로만 자르면 칸이 밀린다.
  const split = (l) => l.match(/("([^"]|"")*"|[^,]*)(,|$)/g).slice(0, -1).map((c) => c.replace(/,$/, "").replace(/^"|"$/g, "").replace(/""/g, '"'));
  const head = split(lines[0]);
  return lines.slice(1).map((l) => Object.fromEntries(split(l).map((c, i) => [head[i], c])));
};
const sum = (rows, k) => rows.reduce((a, r) => a + Number(r[k] || 0), 0);

test("CSV = 발행 수치(#03 · #04 · #06 · #13 · #12)", () => {
  const d = read("empty-direction");
  const y = (yy) => d.filter((r) => r["연월"].startsWith(yy));
  expect(Math.round(sum(y("2025"), "수출방향_TEU"))).toBe(843838);            // #03
  expect(Math.round(sum(y("2025"), "수입방향_TEU"))).toBe(139418);            // #03
  expect(Math.round((sum(y("2022"), "수출방향_TEU") / sum(y("2022"), "수입방향_TEU")) * 100) / 100).toBe(27.32); // #04 연간 최대
  const s = read("size-direction").filter((r) => r["연월"] >= "2022-01" && r["연월"] <= "2025-12");
  expect(s.length).toBe(48);
  expect(s.filter((r) => Number(r["격차_pp"]) > 0).length).toBe(42);         // #06 「48개월 중 42개월」
  const it = read("items");
  const ex = {};
  for (const r of it) ex[r["HS류"]] = (ex[r["HS류"]] || 0) + Number(r["수출_천달러"]);
  const tot = Object.values(ex).reduce((a, b) => a + b, 0);
  const top3 = Object.entries(ex).sort((a, b) => b[1] - a[1]).slice(0, 3);
  expect(top3.map((t) => t[0]).sort()).toEqual(["30", "85", "87"]);          // #13 85·87·30류
  expect(Math.round((top3.reduce((a, t) => a + t[1], 0) / tot) * 1000) / 10).toBe(63.6); // #13 63.6%
  const t = read("terminals").filter((r) => r["연월"] === "2026-07");
  expect(t.find((r) => r["터미널"] === "HJIT")["당월_천TEU"]).toBe("107");
});

test("화면: 범위·보기를 바꾸면 문장과 차트가 바뀐다 · 외부 요청 0", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => { if (!/cloudflareinsights\.com$/.test(new URL(r.request().url()).hostname)) ext.push(r.request().url()); return r.abort(); });
  await page.goto("/incheon-port-analysis/reports/report_03_공컨테이너_수출입방향.html");
  const w = page.locator(".rc[data-kind=direction]");
  await w.scrollIntoViewIfNeeded();
  await expect(w.locator(".rc__say")).toContainText("843,838 TEU");
  await expect(w.locator(".rc__plot svg").first()).toBeVisible();
  await w.locator("button[data-view=ratio]").click();
  await expect(w.locator(".rc__say")).toContainText("6.05배");
  await w.locator("select[data-k=from]").selectOption("2022");
  await expect(w.locator(".rc__say")).toContainText("2022~2025");

  await page.goto("/incheon-port-analysis/reports/report_13_인천_품목별_수출입.html");
  const it = page.locator(".rc[data-kind=item]");
  await it.scrollIntoViewIfNeeded();
  await expect(it.locator(".rc__say")).toContainText("상위 10개 류");
  await it.locator("button[data-view=imp]").click();
  await expect(it.locator(".rc__say")).toContainText("수입");

  await page.goto("/incheon-port-analysis/reports/report_12_터미널별_장기창.html");
  const tw = page.locator(".rc[data-kind=terminal]");
  await tw.scrollIntoViewIfNeeded();
  await expect(tw.locator(".rc__say")).toContainText("마지막 달 2026-07");
  await tw.locator("button[data-view=yoy]").click();
  await expect(tw.locator(".rc__say")).toContainText("%");
  await expect(tw.locator("[data-updated]")).toHaveCount(1);
  expect(ext).toEqual([]);
});

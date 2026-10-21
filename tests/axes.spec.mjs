// 홈 세 축(2026-10-21 선장님 과제 1) — 첫 화면 축 줄의 숫자가 데이터 파일과 같고, 줄을 누르면 그 축의 질문 묶음으로 간다.
// 숫자는 전부 refresh 가 다시 받는 파일에서(docs/숫자전수_20261021.md ① 칸): home_axes.json · terminal long · vessel_replay · home_flows.
import { test, expect } from "@playwright/test";
import { readFileSync, existsSync } from "node:fs";

const B = "/incheon-port-analysis";
const J = (f) => JSON.parse(readFileSync(f, "utf-8"));
const fmt = (v) => v.toLocaleString("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

test("세 축 — 축 줄 숫자 = 데이터 파일 · 줄 → 그 축 질문 묶음", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "데이터 판정은 한 번만");
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.goto(`${B}/`, { waitUntil: "domcontentloaded" });
  const rows = page.locator(".ax__row a");
  const AX = existsSync("data/derived/home_axes.json") ? J("data/derived/home_axes.json") : null;
  await expect(rows).toHaveCount(AX ? 3 : 1);
  // 물류 — 인천항 컨테이너 마지막 달(공표 long) · 외항선 마지막 달
  const long = readFileSync("analysis/terminal_monthly_long.csv", "utf-8").trim().split("\n").map((l) => l.split(","));
  const h = long[0], tot = long.filter((r) => r[h.indexOf("계층")] === "합계" && r[h.indexOf("당월_천TEU")]);
  const last = tot[tot.length - 1];
  const logi = await page.locator('.ax__row a[href="#ax-logi"]').innerText();
  expect(logi).toContain(fmt(Number(last[h.indexOf("당월_천TEU")])));
  expect(logi).toContain(last[h.indexOf("기준연월")]);
  const V = J("data/derived/vessel_replay.json").latest;
  expect(logi).toContain(`외항선 ${V.incheon.toLocaleString("ko-KR")}척(${V.ym})`);
  if (AX) {
    const t = await page.locator('.ax__row a[href="#ax-trade"]').innerText();
    expect(t).toContain(fmt(AX.trade.sudo_imp));
    expect(t).toContain(`전국의 ${AX.trade.exp_pct}%`);
    await expect(page.locator("#live-h")).toContainText(`${AX.trade.imp_pct}%`);
    const r = await page.locator('.ax__row a[href="#ax-retail"]').innerText();
    expect(r).toContain(fmt(AX.retail.cons_imp));
  }
  // 줄마다 대상 묶음이 있고, 묶음마다 질문이 하나 이상
  for (const href of await rows.evaluateAll((a) => a.map((x) => x.getAttribute("href")))) {
    const sec = page.locator(href);
    await expect(sec, href).toHaveCount(1);
    expect(await sec.locator(".qs > li").count(), `${href} 질문 수`).toBeGreaterThan(0);
  }
  // 질문마다 축이 있다(축 없는 질문은 홈에서 빠진다)
  const Q = J("data/questions.json"), ids = new Set(Q.axes.map((a) => a.id));
  for (const q of Q.questions) expect(ids.has(q.axis), `${q.id} 축 ${q.axis}`).toBe(true);
});

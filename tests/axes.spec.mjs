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
  expect(logi).toContain(Number(last[h.indexOf("당월_천TEU")]).toLocaleString("ko-KR")); // 원천 정밀도 그대로(20차 사실 대조 — 281.0 은 없는 정밀도)
  expect(logi).toContain(last[h.indexOf("기준연월")]);
  const V = J("data/derived/vessel_replay.json").latest;
  expect(logi).toContain(`외항선 ${V.incheon.toLocaleString("ko-KR")}척(${V.ym})`);
  if (AX) {
    const t = await page.locator('.ax__row a[href="#ax-trade"]').innerText();
    expect(t).toContain(fmt(AX.trade.sudo_imp));
    expect(await page.locator('.ax__row a[href="#ax-trade"]').textContent()).toContain(`같은 달 수출 ${fmt(AX.trade.sudo_exp)}억`); // 낮은 창에서는 감춘다 — 글은 늘 있다
    await expect(page.locator("#axes-h")).toContainText(`${AX.trade.imp_pct}%`); // 2026-10-22 첫 화면 아래 절로 내림
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

// [2026-10-22 선장님 방향 전환 · 품질기준 Q9] 첫 화면 = 정체성·대상 — 두 폭 첫 화면에 「무엇」(제목) · 대상 둘(실무자 · 채용 담당자) · 연락 단추가 접힘선 위 ·
// 통계 숫자(%·억 달러·TEU)는 첫 화면 글에 없다(아래 #now-axes 절로). 사람 판정(Q9)의 필요조건만 기계로 본다.
for (const [w, h] of [[1520, 730], [390, 844]]) {
  test(`Q9 첫 화면 정체성·대상 — ${w}×${h}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop-1440", "크기를 시험 안에서 바꾼다 — 한 번이면 된다");
    await page.setViewportSize({ width: w, height: h });
    await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
    await page.goto(`${B}/`, { waitUntil: "domcontentloaded" });
    const above = async (sel) => { const b = await page.locator(sel).first().boundingBox(); return !!b && b.y + b.height <= h; };
    expect(await above("#live-h"), "제목").toBe(true);
    const who = await page.locator(".aud__who").allInnerTexts();
    expect(who.join(" "), "대상 둘").toMatch(/실무자[\s\S]*채용 담당자/);
    for (const i of [0, 1]) { const b = await page.locator(".aud__who").nth(i).boundingBox(); expect(b && b.y + b.height <= h, `대상 ${i + 1} 접힘선 위`).toBe(true); }
    expect(await above('.live__cta [data-c="mail"]'), "문의 단추").toBe(true);
    const txt = await page.locator(".live__text").innerText();
    expect(txt, "첫 화면 글에 통계 숫자").not.toMatch(/\d+(\.\d+)?\s*%|억 달러|TEU/);
    await expect(page.locator("#now-axes #axes-h"), "숫자 절은 아래에 있다").toHaveCount(1);
  });
}

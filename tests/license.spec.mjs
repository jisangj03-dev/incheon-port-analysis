// 이용허락 — 상업 재사용에 허락이 필요한 원천(data/sources.json 의 commercial 「허락 필요」)을 쓰는 지면에는 사업 문의 꼬리([data-ask])와 바닥글 「문의를 받습니다」를 달지 않는다(Base biz=false).
// 2026-10-21 결정(채팅 · 선장님 위임): IMF PortWatch 를 쓰는 초크포인트 지면에서 「이 분석을 우리 회사 숫자로」를 뗐다. 허락을 받으면 이 표와 대장을 같이 고친다.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const S = JSON.parse(readFileSync("data/sources.json", "utf-8")).sources;
const NEEDS = S.filter((s) => /허락 필요/.test(s.commercial || "") && !s.retired).map((s) => s.id);
// 원천 id → 화면에서 그 원천을 알아보는 말(사업 문의 문장이 붙은 지면에 이 말이 있으면 빨강)
const MARK = { "imf-portwatch": /PortWatch|통항/ };
// 원천 id → 그 원천을 쓰는 공개 지면(대장 used_by 는 이름이라 경로를 여기 둔다)
const PAGES = { "imf-portwatch": ["/tools/chokepoint.html"] };

test("상업 허락이 필요한 원천을 쓰는 지면 — 사업 문의 꼬리 0", async ({ page }) => {
  expect(NEEDS, "대장에서 「허락 필요」 원천을 못 찾았다 — 대장이 바뀌었으면 이 시험도 고친다").toContain("imf-portwatch");
  for (const id of NEEDS) {
    expect(PAGES[id], `${id}: 이 원천을 쓰는 지면 경로를 PAGES 에 적어라`).toBeTruthy();
    for (const p of PAGES[id]) {
      await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
      await page.goto(`/incheon-port-analysis${p}`, { waitUntil: "domcontentloaded" });
      await expect(page.locator("[data-ask]"), `${p} 에 사업 문의 꼬리`).toHaveCount(0);
      await expect(page.locator("footer.foot"), `${p} 바닥글에 사업 문의 문장`).not.toContainText("문의를 받습니다");
    }
  }
});

test("사업 문의가 붙은 지면(홈 「같이 푸는 질문」 · 도구 목록)에 허락이 필요한 원천의 숫자·제안 0", async ({ page }) => {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.goto("/incheon-port-analysis/", { waitUntil: "domcontentloaded" });
  await expect(page.locator('[data-q="choke"]'), "홈 「귀사 숫자로」 질문 목록에 초크포인트").toHaveCount(0);
  // [2026-10-22 24차 사실 대조 중대 1] 첫 화면 「이런 분께」 표·도구 화면 띠도 사업 문의(연락 줄) 바로 위 — 허락이 필요한 원천의 지면을 걸지 않는다
  for (const id of NEEDS) for (const p of PAGES[id] || []) await expect(page.locator(`.idv a[href$="${p}"]`), `홈 첫 화면에 ${p}`).toHaveCount(0);
  await page.goto("/incheon-port-analysis/tools/", { waitUntil: "domcontentloaded" });
  const row = await page.locator('main .tl a[href$="/tools/chokepoint.html"]').first().innerText();
  for (const id of NEEDS) expect(row, `도구 목록 초크포인트 줄에 ${id} 숫자`).not.toMatch(MARK[id]);
});

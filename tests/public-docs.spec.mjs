// 운영 문서는 공개 지면이 아니다(2026-10-12 · 허용 목록 = astro/src/lib/public-docs.mjs).
// 빌드가 이미 막지만(astro.config.mjs checkDist), 시험은 산출물을 서버로 띄워 실제 응답으로 한 번 더 본다.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const BASE = "/incheon-port-analysis";
const HIDDEN = ["STATUS", "작업기록", "위임문_다음세션_20261012", "사고기록", "측심_전면개편_판정기준_선커밋_20261010",
  "측심_디자인브리프_20261012", "도구도입_판정_20261010", "채널대기열", "실물점검"];
const SHOWN = ["FACTS", "07_판정결과", "인천물류지수_방법론_선커밋_20261012", "검수기록"];

test("운영 문서 지면은 404 · 독자용 방법 문서는 200 · sitemap 에 운영 문서 0", async ({ request }) => {
  for (const id of HIDDEN) expect((await request.get(`${BASE}/docs/${encodeURIComponent(id)}.html`)).status(), id).toBe(404);
  for (const id of SHOWN) expect((await request.get(`${BASE}/docs/${encodeURIComponent(id)}.html`)).status(), id).toBe(200);
  const sm = readFileSync("astro/dist/sitemap.xml", "utf-8");
  for (const id of HIDDEN) expect(decodeURI(sm)).not.toContain(`/docs/${id}`);
});

test("발행본이 가리키던 운영 문서 링크는 저장소 원문으로 간다(깨진 링크 0)", async ({ page }) => {
  await page.goto(`${BASE}/reports/report_09_공컨테이너_시계열연장.html`);
  const hrefs = await page.locator("a[href*='사고기록'], a[href*='%EC%82%AC%EA%B3%A0%EA%B8%B0%EB%A1%9D']").evaluateAll((as) => as.map((a) => a.getAttribute("href")));
  for (const h of hrefs) expect(h).toMatch(/^https:\/\/github\.com\/jisangj03-dev\/incheon-port-analysis\/blob\/main\/docs\//);
});

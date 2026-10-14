// 계산 정확도 회귀 — 성공 기준 6. 엑셀 가상 샘플을 화면에 **손으로 입력하듯** 넣고 같은 답이 나오는지 본다.
// 어댑터 기본값 = v2(2026-10-12 Astro 이전 · v1 화면은 새 빌드에 없다). 기대값 파일은 그대로다.
// 「가상 예시 넣기」 단추는 쓰지 않는다 — 단추가 넣는 값과 계산이 같이 틀리면 같이 맞아 보인다.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(readFileSync(new URL("./fixtures/cost-sample.json", import.meta.url), "utf-8"));
const adapter = await import(`./adapters/cost-${process.env.COST_ADAPTER || "v2"}.mjs`);

test("엑셀 가상 샘플 → 건당 4,044 / 2,805 / 2,960원", async ({ page }) => {
  // 외부 요청 0 — 단 개편 기준 17이 선커밋한 예외 하나(Cloudflare 분석 둘)는 세지 않고, 시험에서는 끊는다.
  const ALLOWED = new Set(["static.cloudflareinsights.com", "cloudflareinsights.com"]);
  const external = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (route) => {
    const h = new URL(route.request().url()).hostname;
    if (!ALLOWED.has(h)) external.push(route.request().url());
    return route.abort();
  });
  await page.goto(adapter.path);
  await adapter.fill(page, fixture.input);
  const got = await adapter.read(page);
  expect(got.perUnit).toEqual(fixture.expect.perUnit);
  expect(got.monthly).toEqual(fixture.expect.monthly);
  expect(got.unknown).toEqual(fixture.expect.unknown);
  expect(external, "공개 화면 외부 요청 0").toEqual([]);
});

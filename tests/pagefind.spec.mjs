// Pagefind — 빌드 때 만든 색인이 사이트 안에서 검색되는가('공컨' 1건 이상). 외부 요청 없이 같은 주소에서 받는다.
import { test, expect } from "@playwright/test";

test("'공컨' 검색 결과 1건 이상", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  await page.goto("/incheon-port-analysis/");
  const r = await page.evaluate(async () => {
    const pf = await import("/incheon-port-analysis/pagefind/pagefind.js");
    await pf.init();
    const res = await pf.search("공컨");
    const first = res.results.length ? await res.results[0].data() : null;
    return { n: res.results.length, first: first && first.url };
  });
  console.log(`pagefind '공컨': ${r.n}건 · 첫 결과 ${r.first}`);
  expect(r.n).toBeGreaterThanOrEqual(1);
});

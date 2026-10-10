// 계산 정확도 회귀 — 성공 기준 6. 엑셀 가상 샘플을 화면에 **손으로 입력하듯** 넣고 같은 답이 나오는지 본다.
// 「가상 예시 넣기」 단추는 쓰지 않는다 — 단추가 넣는 값과 계산이 같이 틀리면 같이 맞아 보인다.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(readFileSync(new URL("./fixtures/cost-sample.json", import.meta.url), "utf-8"));
const adapter = await import(`./adapters/cost-${process.env.COST_ADAPTER || "v1"}.mjs`);

test("엑셀 가상 샘플 → 건당 4,044 / 2,805 / 2,960원", async ({ page }) => {
  const external = [];
  page.on("request", (r) => {
    const h = new URL(r.url()).hostname;
    if (h !== "localhost" && h !== "127.0.0.1") external.push(r.url());
  });
  await page.goto(adapter.path);
  await adapter.fill(page, fixture.input);
  const got = await adapter.read(page);
  expect(got.perUnit).toEqual(fixture.expect.perUnit);
  expect(got.monthly).toEqual(fixture.expect.monthly);
  expect(got.unknown).toEqual(fixture.expect.unknown);
  expect(external, "공개 화면 외부 요청 0").toEqual([]);
});

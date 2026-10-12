// 계산기 v2 사용성 — 개편 기준 3·4·5·7·8. 계산 정확도(기준 6)는 tests/cost.spec.mjs(COST_ADAPTER=v2)가 따로 본다.
import { test, expect } from "@playwright/test";
const PATH = "/incheon-port-analysis/tools/logistics-cost.html";
const won = (s) => Number(String(s).replace(/[^0-9]/g, ""));

test("기준 3·4 — 5칸으로 첫 답, 입력하는 동안 결과가 화면 안", async ({ page }, info) => {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(PATH);
  const typed = ["#ship", "#q-0-0", "#q-0-2", "#q-0-3", "#q-0-6"];
  await page.fill("#ship", "1000");
  await page.fill("#q-0-0", "2800");
  await page.fill("#q-0-2", "120000");
  await page.fill("#q-0-3", "300");
  await page.locator("#q-0-6").fill("100000");
  expect(typed.length).toBeLessThanOrEqual(5);
  // (2800+300)×1000 + 120000 + 100000 = 3,320,000 → 건당 3,320
  await expect(page.locator("#res-0 [data-per]")).toHaveText("3,320원");
  // 입력 칸에 초점이 있는 채로 건당 값이 화면 안에 보이는가
  const vh = page.viewportSize().height;
  const target = info.project.name === "iphone-13" ? page.locator('[data-dock="0"]') : page.locator("#res-0 [data-per]");
  const box = await target.boundingBox();
  expect(box && box.y >= 0 && box.y + box.height <= vh, "결과가 화면 안").toBe(true);
  await expect(target).toHaveText("3,320원");
});

test("기준 5·7·8 — 세 견적 동시·손익분기 그래프·모름 경고·주소로 공유", async ({ page }) => {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(PATH);
  await page.click("#sample");
  for (let b = 0; b < 3; b++) await expect(page.locator(`#res-${b} [data-per]`)).not.toHaveText("—");
  await expect(page.locator("#res-1 [data-unknown]")).toBeVisible();
  await expect(page.locator("#res-1 [data-unknown]")).toContainText("모름 칸 3개");
  await expect(page.locator("#be-text")).toContainText("가장 쌉니다");
  await expect(page.locator(`#be-chart g[aria-label="line"] path`)).toHaveCount(3, { timeout: 10_000 });  // 견적 셋의 선이 그려졌다
  await page.waitForFunction(() => location.search.includes("s="));
  const url = page.url();
  const per = await page.locator("#res-2 [data-per]").innerText();
  const p2 = await page.context().newPage();
  await p2.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await p2.goto(url);
  await expect(p2.locator("#res-2 [data-per]")).toHaveText(per);
  expect(won(per)).toBe(2960);
});

// 계산기 화면 어댑터 — 개편 전(2026-10-10) tools/logistics-cost.html 용.
// 입력·기대값(tests/fixtures/cost-sample.json)은 화면을 모른다. 화면을 바꾸면 이 파일 대신
// cost-v2.mjs 같은 새 어댑터를 쓰고 COST_ADAPTER=v2 로 고른다 — 같은 기대값을 통과해야 한다.
export const path = "/incheon-port-analysis/tools/logistics-cost.html";

export async function fill(page, input) {
  await page.fill("#cc-ship", String(input.ship));
  await page.fill("#cc-ret", String(input.ret));
  for (let b = 0; b < input.blocks.length; b++) {
    await page.click(`#cc-tab-${b}`);          // 탭을 바꾸면 칸이 다시 그려진다
    const rows = input.blocks[b].rows;
    for (let i = 0; i < rows.length; i++) {
      const [mode, price, qty] = rows[i];
      await page.selectOption(`#cc-${i}-m`, mode);
      if (price !== null) await page.fill(`#cc-${i}-p`, String(price));
      if (qty !== null) await page.fill(`#cc-${i}-q`, String(qty));
    }
  }
}

const digits = (s) => Number(String(s).replace(/[^0-9]/g, ""));

export async function read(page) {
  const cards = page.locator("#cc-cards .cc-card");
  const n = await cards.count();
  const out = { perUnit: [], monthly: [], unknown: [] };
  for (let k = 0; k < n; k++) {
    const c = cards.nth(k);
    out.perUnit.push(digits(await c.locator(".cc-big").innerText()));
    const subs = await c.locator(".cc-sub").allInnerTexts();
    const m = subs.find((t) => t.includes("건당 합계"));
    out.monthly.push(digits(m.split("월")[1]));
    const u = subs.find((t) => t.startsWith("모름 칸"));
    out.unknown.push(digits(u));
  }
  return out;
}

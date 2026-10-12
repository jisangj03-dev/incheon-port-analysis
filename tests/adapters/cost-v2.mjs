// 계산기 화면 어댑터 — 개편 후(2026-10-12) astro/src/pages/tools/logistics-cost.astro 용.
// 기대값(tests/fixtures/cost-sample.json)은 손대지 않는다 — v1 과 같은 입력·같은 답을 이 화면으로 통과해야 한다(기준 6).
// 「가상 예시 넣기」 단추는 쓰지 않는다 — 정밀 10항목을 손으로 입력하듯 칸마다 채운다.
export const path = "/incheon-port-analysis/tools/logistics-cost.html";

export async function fill(page, input) {
  await page.fill("#ship", String(input.ship));
  await page.fill("#ret", String(input.ret));
  await page.click("#precise > summary");
  for (let b = 0; b < input.blocks.length; b++) {
    await page.click(`#pt-${b}`);
    const rows = input.blocks[b].rows;
    for (let i = 0; i < rows.length; i++) {
      const [mode, price, qty] = rows[i];
      await page.selectOption(`#p-${b}-${i}-m`, mode);
      if (price !== null) await page.fill(`#p-${b}-${i}-p`, String(price));
      if (qty !== null) await page.fill(`#p-${b}-${i}-q`, String(qty));
    }
  }
}

const digits = (s) => Number(String(s).replace(/[^0-9]/g, ""));

export async function read(page) {
  const out = { perUnit: [], monthly: [], unknown: [] };
  for (let b = 0; b < 3; b++) {
    const card = page.locator(`#res-${b}`);
    out.perUnit.push(digits(await card.locator("[data-per]").innerText()));
    out.monthly.push(digits((await card.locator("[data-monthly-line]").innerText()).split("월")[1]));
    const u = card.locator("[data-unknown]");
    out.unknown.push((await u.isHidden()) ? 0 : digits((await u.innerText()).match(/모름 칸 (\d+)개/)[1]));
  }
  return out;
}

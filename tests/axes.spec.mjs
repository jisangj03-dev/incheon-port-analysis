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
    // [2026-10-22] KOSIS 가 있고 출처 대장 줄이 있으면 유통 줄 = 수도권 대형소매점 + 전국 온라인쇼핑, 아니면 종전(생활소비재 수입)
    const SRC = J("data/sources.json").sources, KO = AX.retail.kosis?.large && AX.retail.kosis?.online && SRC.some((s) => s.id === "kostat-kosis") ? AX.retail.kosis : null;
    if (KO) {
      expect(r).toContain(`${fmt(KO.large.sudo_jo)}`);
      expect(r).toContain(KO.large.ym);
      expect(await page.locator('.ax__row a[href="#ax-retail"]').textContent()).toContain(`전국 온라인쇼핑 ${fmt(KO.online.jo)}조 원`);
      expect(r).not.toContain(fmt(AX.retail.cons_imp)); // 교체 — 두 숫자를 한 줄에 섞지 않는다
    } else expect(r).toContain(fmt(AX.retail.cons_imp));
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

// [2026-10-22 선장님 최종 결정 · 품질기준 Q9·Q11] 첫 화면 = 측심이 무엇·누구를 위해·얻는 것·왜 연락 — 두 폭 첫 화면에 제목(무엇) · 측심 한 문장 ·
// 도구 화면 띠 · 독자 세 줄(물류·무역·유통) · 연락 문장 · 문의 단추가 접힘선 위 · 통계 숫자(%·억 달러·TEU)는 첫 화면 글에 없다(아래 #now-axes 절로) ·
// 첫 화면 글 양 ≤ 직전 공개판(1520×730 463자 · 390×844 349자 · 2026-10-22 실측) · 사람 정보(실명·학교·자격·채용)는 홈에 0. 사람 판정(Q9·Q11)의 필요조건만 기계로 본다.
const P = J("data/profile.json"), SHOW = J("data/home_showcase.json").shots;
const CHARS = { 1520: 463, 390: 349 };
for (const [w, h] of [[1520, 730], [390, 844]]) {
  test(`Q9 첫 화면 무엇·누구·얻는 것·왜 연락 — ${w}×${h}`, async ({ page }, info) => {
    test.skip(info.project.name !== "desktop-1440", "크기를 시험 안에서 바꾼다 — 한 번이면 된다");
    await page.setViewportSize({ width: w, height: h });
    await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
    await page.goto(`${B}/`, { waitUntil: "domcontentloaded" });
    const above = async (sel) => { const b = await page.locator(sel).first().boundingBox(); return !!b && b.y + b.height <= h; };
    await expect(page.locator("#live-h"), "무엇").toContainText("물류·무역·유통");
    await expect(page.locator(".idv__one"), "측심").toContainText("측심");
    for (const [sel, nm] of [["#live-h", "제목"], [".idv__one", "한 문장"], [".shots__stage", "도구 화면"], [".who3", "독자 세 줄"], [".idv__ask", "연락 이유"], ['.live__cta [data-c="mail"]', "문의 단추"]])
      expect(await above(sel), `${nm} 접힘선 위`).toBe(true);
    await expect(page.locator(".who3__row"), "물류·무역·유통").toHaveCount(3);
    const txt = await page.locator(".idv").innerText();
    expect(txt, "첫 화면 글에 통계 숫자").not.toMatch(/\d+(\.\d+)?\s*%|억 달러|TEU/);
    for (const x of [P.name, ...P.credentials, "채용"]) expect(txt, `첫 화면에 「${x}」`).not.toContain(x);
    // 글 양 — 접힘선 위에 보이는 글자(공백 빼고 · 머리 메뉴·숨긴 글 제외)
    const n = await page.evaluate(() => { const vh = innerHeight; let n = 0; const tw = document.createTreeWalker(document.querySelector("main") || document.body, NodeFilter.SHOW_TEXT);
      for (let t = tw.nextNode(); t; t = tw.nextNode()) { const s = t.textContent.replace(/\s+/g, ""); if (!s) continue; const el = t.parentElement; if (el.closest("header.s-mast,[aria-hidden=true]")) continue;
        const rg = document.createRange(); rg.selectNodeContents(t); const r = rg.getBoundingClientRect(); if (r.width && r.top < vh && r.bottom > 0 && getComputedStyle(el).visibility !== "hidden") n += s.length; } return n; });
    expect(n, "첫 화면 글 양 ≤ 직전 공개판").toBeLessThanOrEqual(CHARS[w]);
    await expect(page.locator("#now-axes #axes-h"), "숫자 절은 아래에 있다").toHaveCount(1);
  });
}

// [품질기준 Q10] 정적이지 않은가 — 첫 화면에 실제 도구 화면(배포 때 그 지면을 찍은 그림 · iframe 0) · 7초마다 돌고 맞는 독자 줄이 켜진다 ·
// 지금 것 표시(마디)와 멈춤 단추 · 줄·그림에 올리면 그 자리에서 멈춘다 · 동작 줄이기면 돌지 않는다. 그림이 배포물에 실제로 있는지도 본다(og-cards.mjs 가 찍는다).
test("Q10 실제 도구 화면 띠 — 그림 실재 · 회전 · 마디 · 줄 연동 · 멈춤", async ({ page, request }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  test.setTimeout(60_000);
  await page.setViewportSize({ width: 1520, height: 730 });
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.clock.install();
  await page.goto(`${B}/`, { waitUntil: "load" });
  await page.clock.pauseAt((await page.evaluate(() => Date.now())) + 1000); // 가짜 시계도 그냥 두면 실제 시간대로 흐른다 — 멈춰 두고 넘긴 만큼만 간다
  await expect(page.locator("#shots iframe"), "iframe 0").toHaveCount(0);
  await expect(page.locator("#shots .shot")).toHaveCount(SHOW.length);
  await expect(page.locator("#shots .seg")).toHaveCount(SHOW.length);
  for (const t of SHOW) {
    await expect(page.locator(`#shots .shot[href$="${t.href}"]`), `${t.id} 실제 지면으로 간다`).toHaveCount(1);
    await expect(page.locator(`.who3__row[data-axis="${t.axis}"] a[href$="${t.href}"]`), `${t.id} 그 독자 줄에 같은 도구`).toHaveCount(1);
    if (existsSync(`astro/dist/assets/toolshots/${t.id}.jpg`)) expect((await request.get(`${B}/assets/toolshots/${t.id}.jpg`)).status(), `${t.id} 그림`).toBe(200);
  }
  const on = () => page.evaluate(() => window.__shots.cur);
  const lit = () => page.locator(".who3__row.is-on").getAttribute("data-axis");
  const seg = () => page.locator("#shots .seg.is-on").getAttribute("data-i");
  expect(await on()).toBe(0);
  expect(await lit()).toBe(SHOW[0].axis);
  await page.mouse.move(5, 5);
  await page.clock.fastForward(7100); // 지도 프레임을 다 돌리지 않고 시계만 넘긴다(runFor 는 rAF 를 프레임마다 돌려 60초를 넘겼다)
  expect(await on(), "7초 뒤 다음 도구").toBe(1);
  expect(await lit(), "맞는 독자 줄").toBe(SHOW[1].axis);
  expect(await seg(), "마디도 따라간다").toBe("1");
  const rb = await page.locator(`.who3__row[data-axis="${SHOW[2].axis}"]`).boundingBox();
  await page.mouse.move(rb.x + 20, rb.y + rb.height / 2); // hover() 는 가짜 시계에서 안정 대기가 끝나지 않는다
  expect(await on(), "줄에 올리면 그 도구").toBe(2);
  await page.clock.fastForward(7100); await page.clock.fastForward(7100);
  expect(await on(), "올려 둔 동안 멈춤").toBe(2);
  await page.mouse.move(5, 5);
  await page.locator("#shots-pause").dispatchEvent("click");
  await expect(page.locator("#shots-pause")).toHaveAttribute("aria-pressed", "true");
  await page.clock.fastForward(7100); await page.clock.fastForward(7100);
  expect(await on(), "멈춤 단추").toBe(2);
  await page.locator('#shots .seg[data-i="0"]').dispatchEvent("click");
  expect(await on(), "마디를 누르면 그 도구").toBe(0);
});

test("Q10 동작 줄이기 — 띠가 돌지 않는다 · 마디로 고른다", async ({ browser }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  const ctx = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 1520, height: 730 } });
  const page = await ctx.newPage();
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.clock.install();
  await page.goto(`${B}/`, { waitUntil: "load" });
  await page.clock.pauseAt((await page.evaluate(() => Date.now())) + 1000); // 가짜 시계도 그냥 두면 실제 시간대로 흐른다 — 멈춰 두고 넘긴 만큼만 간다
  await page.mouse.move(5, 5);
  for (let k = 0; k < 3; k++) await page.clock.fastForward(7100);
  expect(await page.evaluate(() => window.__shots.cur)).toBe(0);
  expect(await page.locator("#shots .seg.is-on i").evaluate((e) => getComputedStyle(e, "::after").animationName)).toBe("none");
  await page.locator('#shots .seg[data-i="1"]').dispatchEvent("click");
  expect(await page.evaluate(() => window.__shots.cur)).toBe(1);
  await ctx.close();
});

// 실무 도구(2026-10-14 선장님 최종 위임 · 판정 기준 선커밋 §2) — 도구마다 완료 기준을 그대로 시험한다:
// ① 실무 질문이 첫 화면 맨 위 ② 3초 답(움직이는 그림 + 숫자)이 1440·390 첫 화면 안 ③ 조작하면 답이 바뀐다 ④ 원문·CSV·갱신일
// ⑥ 계산 도구는 지면 안에 「참고용 · 자문 아님」 ⑦ 「○일 기준」 ⑨ 외부 요청 0(CF 비콘 예외) · 지면 숫자 = 데이터 파일 · 오류 0 · 가로 넘침 0.
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { check } from "../tools-build/check-data-numbers.mjs";
const B = "/incheon-port-analysis";
const J = (f) => readFileSync(f, "utf-8");
const COMMON = ["data/rooms.json", "data/sources.json", "data/profile.json", "data/questions.json"];
const TOOLS = {
  "port-pulse": { data: ["data/derived/port_pulse.json"], answer: "#pl-fig", num: "#pl-pct", asof: true,
    act: async (p) => { const a = await p.locator("#pl-word").innerText(); await p.locator(".pulse__cmp button[data-port=Busan]").click(); await expect(p.locator("#pl-word")).not.toHaveText(a); } },
  "delivery-reach": { data: ["data/derived/isochrones.json"], answer: ".reach__map", num: "#reach-min",
    act: async (p) => { await p.waitForSelector(".reach__map[data-ready='1']"); const a = await p.locator("#reach-list li b").first().innerText(); await p.locator(".seg button[data-k='2']").click(); await expect(p.locator("#reach-list li b").first()).not.toHaveText(a); } },
  "trade-race": { data: ["data/derived/trade_race.json", "data/hs2_short.json"], answer: "#race-box", num: "#race-total",
    act: async (p) => { await p.waitForSelector("#race-box[data-ready='1']"); await p.evaluate(() => window.__race.stop()); const a = await p.locator("#race-total").innerText(); await p.locator(".seg button[data-k=imp]").click(); await expect(p.locator("#race-k")).toHaveText("수입"); await expect(p.locator("#race-total")).not.toHaveText(a); } },
  "import-cost": { data: ["data/derived/import_cost.json"], answer: "#cs-fig", num: "#cs-diff", asof: true, advice: true,
    act: async (p) => { await p.waitForTimeout(3500); const a = await p.locator("#cs-body tr.sum td").last().innerText(); await p.fill("input[name=duty_pct]", "0"); await expect(p.locator("#cs-body tr.sum td").last()).not.toHaveText(a); } },
  anchorage: { data: ["data/derived/s2_anchorage.json"], answer: "#anc-fig", num: "#anc-n", asof: true,
    act: async (p) => { await p.locator("#anc-play").click(); await p.locator(".anc__bars button").first().click(); await expect(p.locator("#anc-date")).toHaveText(JSON.parse(J("data/derived/s2_anchorage.json")).frames[0].date); } },
};

for (const [id, T] of Object.entries(TOOLS)) {
  test(`§2-1 ${id}: 지면 숫자는 데이터 파일에만 있다`, () => {
    const r = check(J(`astro/dist/tools/${id}.html`), [...T.data, ...COMMON].map(J));
    expect(r.bad).toEqual([]);
  });
  test(`도구 ${id}: 질문·3초 답 첫 화면 · 조작 · 신뢰 꼬리 · 외부 요청 0`, async ({ page }) => {
    const ext = [], errors = [];
    await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { if (!/cloudflareinsights\.com$/.test(new URL(r.request().url()).hostname)) ext.push(r.request().url()); return r.abort(); });
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto(`${B}/tools/${id}.html`, { waitUntil: "networkidle" });
    const vh = page.viewportSize().height;
    // ① 질문 = h1 · 첫 화면 맨 위
    const h1 = await page.locator(".tool__q").boundingBox();
    expect(h1.y).toBeLessThan(vh * 0.35);
    // ② 3초 답 — 숫자와 그림이 첫 화면 안에서 시작한다
    const num = await page.locator(T.num).boundingBox(), ans = await page.locator(T.answer).boundingBox();
    expect(num.y + num.height, "숫자가 첫 화면 밖").toBeLessThan(vh);
    expect(ans.y, "그림이 첫 화면 밖에서 시작").toBeLessThan(vh * 0.85);
    // ⑦ 기준일
    if (T.asof) await expect(page.locator(".tool__asof")).toContainText("기준");
    // ③ 조작
    await T.act(page);
    // ④ 원문·CSV·갱신일 · 만든 사람 노트 · AI 표기
    await expect(page.locator(".tool__foot a[download]")).toHaveCount(1);
    for (const k of ["how", "limits"]) await expect(page.locator(`[data-note="${k}"]`)).not.toBeEmpty();
    // ⑥ 계산 도구 = 지면 안 자문 아님
    if (T.advice) await expect(page.locator(".tool__advice")).toContainText("자문이 아닙니다");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
    expect(ext).toEqual([]);
    expect(errors).toEqual([]);
  });
}

test("CSV = 지면 데이터(맥박·등시선·트리맵·환율·묘박지) · 머리줄 · 행 수", async ({ request }) => {
  const P = JSON.parse(J("data/derived/port_pulse.json")), C = JSON.parse(J("data/derived/import_cost.json"));
  const rows = async (n) => (await (await request.get(`${B}/data/${n}.csv`)).text()).trim().split(/\r?\n/);
  expect((await rows("port-pulse")).length - 1).toBeGreaterThanOrEqual(Object.values(P.ports).reduce((s, p) => s + p.days.length, 0));
  expect((await rows("import-cost")).length - 1).toBeGreaterThanOrEqual(C.weeks.length);
  for (const n of ["delivery-reach", "trade-race", "anchorage"]) expect((await rows(n)).length).toBeGreaterThan(5);
});

test("도구 목록 · 홈 질문 · 관문 판이 같은 도구 목록(rooms.json)에서 나온다", async ({ page }) => {
  const R = JSON.parse(J("data/rooms.json")).rooms.find((r) => r.id === "tools").items;
  await page.goto(`${B}/tools/`, { waitUntil: "domcontentloaded" });
  for (const t of R) await expect(page.locator(`a[href$="${t.href}"]`).first()).toBeVisible();
  await page.goto(`${B}/`, { waitUntil: "domcontentloaded" });
  expect(await page.locator("#fm-panel .live__tools a").count()).toBe(R.filter((t) => t.gate).length);
});

test("계산식 = 파생 스크립트(fx_derive.py 예시 숫자를 브라우저 계산이 그대로 낸다)", async ({ page }) => {
  const E = JSON.parse(J("data/derived/import_cost.json")).example;
  await page.goto(`${B}/tools/import-cost.html`, { waitUntil: "networkidle" });
  await page.waitForTimeout(3500);
  const sum = (await page.locator("#cs-body tr.sum td").last().innerText()).replace(/,/g, "");
  expect(Number(sum)).toBe(E.now.landed);
});

// 실무 도구(2026-10-14 선장님 최종 위임 · 판정 기준 선커밋 §2) — 도구마다 완료 기준을 그대로 시험한다:
// ① 실무 질문이 첫 화면 맨 위 ② 3초 답(움직이는 그림 + 숫자)이 1440·390 첫 화면 안 ③ 조작하면 답이 바뀐다 ④ 원문·CSV·갱신일
// ⑥ 계산 도구는 지면 안에 「참고용 · 자문 아님」 ⑦ 「○일 기준」 ⑨ 외부 요청 0(CF 비콘 예외) · 지면 숫자 = 데이터 파일 · 오류 0 · 가로 넘침 0.
import { test, expect } from "@playwright/test";
import { readFileSync, existsSync } from "node:fs";
import { check } from "../tools-build/check-data-numbers.mjs";
const B = "/incheon-port-analysis";
const J = (f) => readFileSync(f, "utf-8");
const COMMON = ["data/rooms.json", "data/sources.json", "data/profile.json", "data/questions.json"];
const TOOLS = {
  "port-pulse": { data: ["data/derived/port_pulse.json"], answer: "#pl-fig", num: "#pl-pct", asof: true,
    act: async (p) => { const a = await p.locator("#pl-word").innerText(); await p.locator(".pulse__cmp button[data-port=Busan]").click(); await expect(p.locator("#pl-word")).not.toHaveText(a); } },
  "delivery-reach": { data: ["data/derived/isochrones.json", ...["data/derived/navi_check.json", "data/derived/reach_slots.json"].filter((f) => existsSync(f))], answer: ".reach__map", num: "#reach-min",
    act: async (p) => { await p.waitForSelector(".reach__map[data-ready='1']"); const a = await p.locator("#reach-list li b").first().innerText(); await p.locator(".seg:not(#reach-veh) button").last().click(); await expect(p.locator("#reach-list li b").first()).not.toHaveText(a); } },
  "trade-race": { data: ["data/derived/trade_race.json", "data/hs2_short.json"], answer: "#race-box", num: "#race-total",
    act: async (p) => { await p.waitForSelector("#race-box[data-ready='1']"); await p.evaluate(() => window.__race.stop()); const a = await p.locator("#race-total").innerText(); await p.locator(".seg button[data-k=imp]").click(); await expect(p.locator("#race-k")).toHaveText("수입"); await expect(p.locator("#race-total")).not.toHaveText(a); } },
  "import-cost": { data: ["data/derived/import_cost.json"], answer: "#cs-fig", num: "#cs-diff", asof: true, advice: true,
    act: async (p) => { await p.waitForTimeout(3500); const a = await p.locator("#cs-body tr.sum td").last().innerText(); await p.fill("input[name=duty_pct]", "0"); await expect(p.locator("#cs-body tr.sum td").last()).not.toHaveText(a); } },
  chokepoint: { data: ["data/derived/chokepoints.json", "data/derived/choke_detour.json"], answer: "#ck-fig", num: "#ck-pct", asof: true,
    act: async (p) => { const a = await p.locator("#ck-imp").innerText(); await p.locator(".seg button[data-id=taiwan]").click(); await expect(p.locator("#ck-name")).toHaveText(/대만/); await expect(p.locator("#ck-imp")).not.toHaveText(a); const h = await p.locator("#ck-hit").innerText(); await p.locator("#ck-x").fill("10"); await expect(p.locator("#ck-hit")).not.toHaveText(h); } },
  anchorage: { data: ["data/derived/s2_anchorage.json"], answer: "#anc-fig", num: "#anc-n", asof: true,
    act: async (p) => { await p.locator("#anc-play").click(); await p.locator(".anc__bars button").first().click(); await expect(p.locator("#anc-date")).toHaveText(JSON.parse(J("data/derived/s2_anchorage.json")).frames[0].date); } },
  "bid-radar": { data: ["data/derived/bid_radar.json"], answer: "#br-fig", num: "#br-n", asof: true,
    act: async (p) => { const R = JSON.parse(J("data/derived/bid_radar.json")), g = R.groups.find((x) => R.group_counts[x] !== R.n); await p.locator(`.br__ctl .seg button[data-g="${g}"]`).click(); await expect(p.locator("#br-shown")).toHaveText(String(R.group_counts[g])); await expect(p.locator("#br-items li:visible")).toHaveCount(R.group_counts[g]); } },
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
  for (const n of ["delivery-reach", "trade-race", "anchorage", "chokepoint"]) expect((await rows(n)).length).toBeGreaterThan(5);
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
  expect(Number(sum)).toBe(E.now.cost); // 원가 = 부가세 제외(채팅 최종 검수 10/15)
  const paid = (await page.locator("#cs-body tr.paid td").last().innerText()).replace(/,/g, "");
  expect(Number(paid)).toBe(E.now.landed); // 납부 합계 = 관세·부가세 포함
  expect(E.now.landed - E.now.cost).toBe(E.now.vat);
});

test("묘박지: 큰 숫자는 최신의 맑은 날 — 넘겨 보기·구름 많은 날을 눌러도 바뀌지 않는다(채팅 검수 10/14)", async ({ page }) => {
  const F = JSON.parse(J("data/derived/s2_anchorage.json")).frames, clear = [...F].reverse().find((f) => !f.low_confidence);
  await page.goto(`${B}/tools/anchorage.html`, { waitUntil: "networkidle" });
  await expect(page.locator("#anc-n")).toHaveText(String(clear.ships_seen));
  await page.waitForTimeout(F.length * 600 + 1500); // 3초 답 넘겨 보기가 끝날 때까지
  await expect(page.locator("#anc-n")).toHaveText(String(clear.ships_seen));
  await expect(page.locator("#anc-date")).toHaveText(clear.date); // 넘겨 보기가 끝나면 그 날로 돌아온다
  const cloudy = F.findIndex((f) => f.low_confidence);
  if (cloudy >= 0) { await page.locator(`.anc__bars button[data-i="${cloudy}"]`).click(); await expect(page.locator("#anc-low")).toContainText("구름"); await expect(page.locator("#anc-n")).toHaveText(String(clear.ships_seen)); }
});

test("트리맵: 재생이 끝나면 최신 온전한 해에 멈춘다(채팅 검수 10/14)", async ({ page }) => {
  const D = JSON.parse(J("data/derived/trade_race.json")), full = D.years.filter((y) => !y.partial), L = full[full.length - 1];
  expect(J("astro/dist/tools/trade-race.html")).toMatch(new RegExp(`<b id="race-y"[^>]*>${L.y}</b>`)); // 첫 화면 정지 상태(서버 그림)
  await page.goto(`${B}/tools/trade-race.html`, { waitUntil: "networkidle" });
  await expect(page.locator("#race-play")).toHaveAttribute("aria-pressed", "true", { timeout: 10_000 }); // 3초 답 재생 시작
  await expect(page.locator("#race-play")).toHaveAttribute("aria-pressed", "false", { timeout: 25_000 }); // 끝
  await expect(page.locator("#race-y")).toHaveText(L.y);
});

test("운임 파도(KCCI): 마지막 반영 주 = 원천 마지막 주 · 「달러 운임 아님」 · 제안 = 지수 변동률만", async ({ page }) => {
  const K = JSON.parse(J("data/derived/import_cost.json")).kcci;
  test.skip(!K, "KCCI 자료 없음 — 칸을 그리지 않는다");
  await page.goto(`${B}/tools/import-cost.html`, { waitUntil: "networkidle" });
  await expect(page.locator(".wave__asof")).toHaveText(K.last_week);
  await expect(page.locator("#wave-note")).toContainText("달러 운임이 아닙니다");
  await page.waitForTimeout(3500);
  await page.fill("input[name=freight]", "1000");
  const wk = await page.locator("input[name=wk]").inputValue();
  const C = JSON.parse(J("data/derived/import_cost.json")), d = String(C.weeks[Number(wk)][0]), day = `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
  let i0 = 0; K.weeks.forEach((w, i) => { if (w[0] <= day) i0 = i; });
  const want = Math.round(1000 * (K.weeks[K.weeks.length - 1][1] / K.weeks[i0][1]));
  await page.click("#wave-apply");
  await expect(page.locator("input[name=freight]")).toHaveValue(String(want));
});

test("입찰 레이더: 담당자 개인정보 0 · 스냅샷 시각 · 「검수 안 함」 · 키 0 · CSV = 목록(선커밋 ③-가)", async ({ page, request }) => {
  const raw = J("data/derived/bid_radar.json"), R = JSON.parse(raw);
  expect(raw).not.toMatch(/Ofcl|TelNo|Email|serviceKey/);
  expect(R.n).toBeGreaterThanOrEqual(5);
  for (const x of R.items) expect(x.bidClseDt.slice(0, 16) > R.snapshot, `${x.bidNtceNo} 스냅샷 때 이미 마감`).toBe(true);
  const csv = await (await request.get(`${B}/data/bid-radar.csv`)).text();
  expect(csv).not.toMatch(/Ofcl|TelNo|Email|serviceKey/);
  expect(csv.trim().split(/\r?\n/).length - 2).toBe(R.n);
  await page.goto(`${B}/tools/bid-radar.html`, { waitUntil: "networkidle" });
  await expect(page.locator(".tool__asof")).toContainText(`${R.snapshot} 스냅샷`);
  await expect(page.locator(".br__auto")).toHaveText("자동 수집 · 고르는 규칙 그대로 · 검수 안 함");
  await expect(page.locator("#br-items li")).toHaveCount(R.n);
});

test("도구 제목 — 가운뎃점(·)이 줄머리에 오지 않는다(360·390·768·1280·1440 · 채팅 최종 검수 10/15)", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "폭을 시험 안에서 바꾼다");
  const R = JSON.parse(J("data/rooms.json")).rooms.find((r) => r.id === "tools").items.filter((t) => !t.needs && /^\/tools\/.+\.html$/.test(t.href));
  const bad = [];
  for (const w of [360, 390, 768, 1280, 1440]) {
    await page.setViewportSize({ width: w, height: 700 });
    for (const t of R) {
      await page.goto(`${B}${t.href}`, { waitUntil: "domcontentloaded" });
      const n = await page.evaluate(() => { const h = document.querySelector(".tool__q"), r = document.createRange(); let prev = null, out = 0;
        for (const tn of [...h.childNodes].filter((x) => x.nodeType === 3)) for (let i = 0; i < tn.length; i++) { r.setStart(tn, i); r.setEnd(tn, i + 1); const c = r.getClientRects()[0]; if (!c) continue; if (prev !== null && c.top > prev + 5 && tn.data[i] === "·") out++; prev = c.top; }
        return out; });
      if (n) bad.push(`${w} ${t.href}`);
    }
  }
  expect(bad).toEqual([]);
});

// [2026-10-15 선커밋 ① 내비 대조] 등시선 「한계」 칸 — 대조가 ok 면 시간대마다 중앙값·범위, 아니면 「내비 대조 미실시」 · 쌍별 시간·경로는 파일에 없다(약관)
test("등시선: 내비 대조 표기 = navi_check.json · 쌍별 값 저장 0", async ({ page }) => {
  await page.goto(`${B}/tools/delivery-reach.html`);
  const NV = existsSync("data/derived/navi_check.json") ? JSON.parse(J("data/derived/navi_check.json")) : null;
  const body = page.locator("main");
  if (NV?.status === "ok") {
    for (const [k, v] of Object.entries(NV.slots)) await expect(body).toContainText(`${k} 중앙값 ${v.median_pct > 0 ? "+" : ""}${v.median_pct}%`);
    for (const pr of NV.pairs) expect(Object.keys(pr).sort(), "쌍에는 이름만 — 시간·거리·경로 없음").toEqual(["from", "to"]);
    expect(JSON.stringify(NV)).not.toMatch(/"(duration|distance|sections|roads|vertexes)"/);
  } else await expect(body).toContainText("내비 대조 미실시");
});

// [2026-10-15 P1 ②] 수입원가 — 표 숫자가 열 머리와 같은 가운데(차 ≤ 2px) · 내국세(개소세 대상)를 넣으면 개별소비세·교육세 줄이 생기고 식대로다
test("수입원가: 표 가운데 정렬 · 내국세 줄 · 세액 10원 미만 버림", async ({ page }) => {
  await page.goto(`${B}/tools/import-cost.html`);
  await page.waitForFunction(() => !!window.__cost); await page.waitForTimeout(3000);
  const off = await page.evaluate(() => {
    const cx = (e) => { const r = e.getBoundingClientRect(); return r.left + r.width / 2; };
    const th = [...document.querySelectorAll(".cost__tbl thead th")].slice(1), out = [];
    for (const tr of document.querySelectorAll("#cs-body tr")) [...tr.querySelectorAll("td")].forEach((td, i) => {
      const r = document.createRange(); r.selectNodeContents(td); const b = r.getBoundingClientRect(); out.push(Math.abs(b.left + b.width / 2 - cx(th[i])));
    });
    return Math.max(...out);
  });
  expect(off, "숫자 가운데와 열 머리 가운데 차(px)").toBeLessThanOrEqual(2);
  await page.locator(".cost__more summary").click();
  await page.fill("input[name=goods]", "1000"); await page.fill("input[name=duty_pct]", "8"); await page.fill("input[name=excise_pct]", "20");
  const row = (k) => page.locator("#cs-body tr", { has: page.locator(`th:text-is("${k}")`) }).locator("td").last();
  await expect(row("개별소비세")).toBeVisible();
  const n = async (k) => Number((await row(k).innerText()).replace(/,/g, ""));
  const cv = await n("과세가격"), duty = await n("관세"), ex = await n("개별소비세"), edu = await n("교육세"), vat = await n("부가가치세");
  const t10 = (v) => Math.floor(v / 10 + 1e-9) * 10;
  expect(duty).toBe(t10(cv * 0.08)); expect(ex).toBe(t10((cv + duty) * 0.2)); expect(edu).toBe(t10(ex * 0.3)); expect(vat).toBe(t10((cv + duty + ex + edu) * 0.1));
  for (const v of [duty, ex, edu, vat]) expect(v % 10, "세액 10원 미만 버림").toBe(0);
});

// [2026-10-15 P1 ①] 등시선 — 시간대 배율(내비 대조 보정) 단추 · 상하차·준비 분을 넣으면 표의 도착 분이 그만큼 늘어난다
test("등시선: 시간대 배율 = reach_slots.json · 상하차 분 더하기", async ({ page }) => {
  await page.goto(`${B}/tools/delivery-reach.html`);
  await page.waitForSelector(".reach__map[data-ready='1']");
  const SL = JSON.parse(J("data/derived/reach_slots.json")).slots;
  await expect(page.locator(".seg:not(#reach-veh) button")).toHaveCount(SL.length);
  const first = async () => Number(await page.locator("#reach-list li b").first().innerText());
  const a = await first();
  await page.fill("#reach-prep", "30");
  await expect.poll(first).toBe(a + 30);
});

// [2026-10-15 P1 ③] 초크포인트 — 우회 거리·일수 · 운임 충격(실측) · 품목 · 경유 규칙이 길목마다 바뀐다 · 항공 포함 표기
test("초크포인트: 우회·운임 충격·품목·경유 규칙 · 항공 포함 표기", async ({ page }) => {
  await page.goto(`${B}/tools/chokepoint.html`);
  const D = JSON.parse(J("data/derived/chokepoints.json"));
  await expect(page.locator("main")).toContainText("항공·해상을 가르지 않는다");
  for (const p of D.points) {
    await page.locator(`.seg button[data-id=${p.id}]`).click();
    const m = page.locator("#ck-more");
    if (p.detour?.extra_nm != null) await expect(m).toContainText(`+${p.detour.extra_days}일`);
    if (p.shock) await expect(m).toContainText(`+${p.shock.routes[0].pct}%`);
    await expect(m.locator("summary")).toContainText(`${p.rule.countries.length}곳`);
  }
});

// [2026-10-15 P1 ①] 등시선 화물차 판 — 단추를 누르면 표가 화물차 도착 분(cities_truck)으로 바뀐다
test("등시선: 화물차 판 = cities_truck", async ({ page }) => {
  const I = JSON.parse(J("data/derived/isochrones.json"));
  test.skip(!I.origins[0].b64_truck, "화물차 판 데이터 없음");
  await page.goto(`${B}/tools/delivery-reach.html`);
  await page.waitForSelector(".reach__map[data-ready='1']");
  await page.locator("#reach-veh button[data-truck='1']").click();
  const sel = Number(await page.locator("#reach-o").inputValue()), O = I.origins[sel];
  await expect(page.locator('#reach-list li[data-city="서울시청"] b')).toHaveText(String(O.cities_truck["서울시청"]));
});

// [2026-10-15 P1 ②] HS 코드 → 관세율표 — 기본·WTO 중 낮은 쪽이 관세율 칸에 · FTA 는 원산지증명이 있을 때만 고를 수 있다
test("수입원가: HS 코드 → 관세율표 자동 채움 · 원산지증명", async ({ page }) => {
  const T = JSON.parse(J("data/derived/tariff/84.json"))["8471300000"];
  test.skip(!T, "관세율표 스냅샷 없음");
  await page.goto(`${B}/tools/import-cost.html`);
  await page.waitForFunction(() => !!window.__cost); await page.waitForTimeout(3000);
  await page.fill("input[name=hs]", "8471300000");
  const lowAC = Math.min(...["A", "C"].filter((k) => typeof T[k] === "number").map((k) => T[k]));
  await expect(page.locator("input[name=duty_pct]")).toHaveValue(String(lowAC));
  await expect(page.locator("select[name=rate_pick] option:disabled").first()).toContainText("원산지증명 필요");
  await page.locator("input[name=co]").check();
  await expect(page.locator("select[name=rate_pick] option:disabled")).toHaveCount(0);
  await page.fill("input[name=hs]", "0000000000");
  await expect(page.locator("#cs-hs-note")).toContainText("찾지 못했습니다");
});

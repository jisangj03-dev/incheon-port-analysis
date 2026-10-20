// 디자인 시스템 「해도」 공개 지면(2026-10-14 공개 전환 · 종전 lab/ds/ 시안) — 숫자 = 데이터 파일(정체성 §2-1) · 외부 요청 0 · 360px 넘침 0 · 만든 사람 노트.
// 지면 이름 → 공개 주소. 시험 이름은 시안 때 이름을 그대로 둔다(이력 대조).
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync, existsSync, mkdirSync } from "node:fs";
import { check } from "../tools-build/check-data-numbers.mjs";
const B = "/incheon-port-analysis";
const PATH = { index: "/index.html", about: "/about.html", beer: "/sim/beer-game.html", map: "/map.html", note: "/notes/port-yoy.html", follow: "/map/follow.html", "ai-ops": "/notes/ai-ops.html", vessels: "/map/vessels.html" };
const at = (f) => `${B}${PATH[f]}`;
// 노트 목록은 보고서 제목을 그대로 가져온다 — 보고서 원문도 원천이다
const DATA = ["analysis/terminal_monthly_long.csv", "data/derived/places.json", "data/derived/home_flows.json", "data/questions.json", "data/sim/beer-game.json", "data/rooms.json", "tools-build/pmtiles.json", "data/sources.json", "data/derived/supply_hs85.json", "data/derived/ops_stats.json", "data/derived/vessel_replay.json", "data/profile.json", ...readdirSync("reports").filter((f) => f.endsWith(".md")).map((f) => `reports/${f}`)].map((f) => readFileSync(f, "utf-8"));

for (const f of ["index", "beer", "map", "note", "ai-ops", "vessels"]) {
  test(`§2-1 ${f}: 지면 숫자는 데이터 파일에만 있다`, () => {
    const r = check(readFileSync(`astro/dist${PATH[f]}`, "utf-8"), DATA);
    expect(r.bad).toEqual([]);
  });
  test(`화면 ${f}: 외부 요청 0 · 360px 넘침 0 · 오류 0`, async ({ page }, info) => {
    const ext = [], errors = [];
    await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { if (!/cloudflareinsights\.com$/.test(new URL(r.request().url()).hostname)) ext.push(r.request().url()); return r.abort(); });
    page.on("pageerror", (e) => errors.push(String(e)));
    if (info.project.name === "iphone-13") await page.setViewportSize({ width: 360, height: 720 });
    await page.goto(at(f), { waitUntil: "networkidle" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
    if (["beer", "map", "ai-ops", "vessels"].includes(f)) for (const k of ["why", "how", "limits"]) await expect(page.locator(`[data-note="${k}"]`)).not.toBeEmpty();
    expect(ext).toEqual([]);
    expect(errors).toEqual([]);
  });
}

// 지도 면이 실제로 그려졌는지 — 화면을 찍어 픽셀로 판정한다(2026-10-14 · Actions 에서 지도 칸이 통째로 빈 면이었는데 위 시험은 모두 통과했다).
// 타일이 있으면(CI 는 반드시) 바다·땅 두 면과 점(먹 · 주홍)이 다 보여야 한다. 타일이 없는 로컬은 점만 본다.
test("지도 면: 바탕·점이 실제로 그려졌다(픽셀 판정)", async ({ page }, info) => {
  const tiles = existsSync("astro/dist/tiles/incheon.pmtiles");
  if (process.env.CI) expect(tiles, "CI 에는 지도 타일이 있어야 한다 — 없으면 바탕을 증명할 수 없다").toBe(true);
  await page.goto(at("map"), { waitUntil: "networkidle" });
  await page.mouse.move(20, 20); // 움직이는 지도는 사람이 움직이면 뜬다
  await page.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 });
  const st = await page.evaluate(() => window.__dsmap);
  expect(st.errors).toEqual([]);
  expect(await page.locator(".ds-label").count(), "장소 넷 + 흐름선 끝(서울)").toBeGreaterThanOrEqual(st.places);
  if (tiles) expect(st.base, "타일이 있는데 바탕 원천을 못 읽었다").toBe(true);
  mkdirSync("lab-out", { recursive: true });
  const shot = await page.locator("#ds-map").screenshot({ path: `lab-out/ds-map-${info.project.name}.png` });
  // 픽셀 세기는 브라우저 캔버스로(저장소에 PNG 해석 의존성을 늘리지 않는다)
  const n = await page.evaluate(async (b64) => {
    const img = new Image(); img.src = `data:image/png;base64,${b64}`; await img.decode();
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
    const g = c.getContext("2d"); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data;
    // 해도 팔레트 — 종이(땅) · 물 · 주홍(85% 위 종이) · 먹(85% 위 종이)
    const P = { paper: [245, 242, 235], water: [227, 222, 210], signal: [189, 82, 61], ink: [58, 56, 52] };
    const k = Object.fromEntries(Object.keys(P).map((x) => [x, 0]));
    for (let i = 0; i < d.length; i += 4) for (const [x, [r, gg, bb]] of Object.entries(P)) {
      if (Math.abs(d[i] - r) + Math.abs(d[i + 1] - gg) + Math.abs(d[i + 2] - bb) <= 24) { k[x]++; break; }
    }
    return { total: d.length / 4, ...k };
  }, shot.toString("base64"));
  info.annotations.push({ type: "map-pixels", description: JSON.stringify(n) });
  expect(n.signal, "주홍 점(가장 큰 문)이 안 보인다").toBeGreaterThan(300);
  expect(n.ink, "먹 점이 안 보인다").toBeGreaterThan(300);
  if (tiles) {
    expect(n.water / n.total, "바다 면이 안 그려졌다").toBeGreaterThan(0.05);
    expect(n.paper / n.total, "땅 면이 안 그려졌다").toBeGreaterThan(0.05);
  }
});

// 맥주 게임 첫 장면 — 누르기 전부터 그림이 있고, 막대를 움직이면 그림과 큰 숫자가 같이 바뀐다(ncase 원리). 개발 용어는 지면에 없다.
test("맥주 게임: 첫 화면에 그림 · 막대를 움직이면 그림이 바뀐다 · 개발 용어 0", async ({ page }) => {
  await page.goto(at("beer"), { waitUntil: "networkidle" });
  await page.waitForSelector("#wave[data-ready]");
  const vh = page.viewportSize().height;
  // 큰 숫자까지는 키 800 이상 화면에서만 요구한다(iPhone 13 기기 묘사 390×664 에선 그림·막대까지가 첫 화면)
  for (const sel of vh >= 800 ? ["#wave svg", "#beta", "#amp"] : ["#wave svg", "#beta"]) {
    const b = await page.locator(sel).boundingBox();
    expect(b && b.y + b.height, `${sel} 가 첫 화면 안에 있어야 한다`).toBeLessThanOrEqual(vh);
  }
  expect(await page.locator("#wave polyline").count()).toBe(5);
  const before = { pts: await page.locator("#wave polyline").last().getAttribute("points"), amp: await page.locator("#amp").innerText() };
  await page.locator("#beta").fill("1");
  await expect(page.locator("#amp")).not.toHaveText(before.amp);
  expect(await page.locator("#wave polyline").last().getAttribute("points")).not.toBe(before.pts);
  const text = await page.locator("main, body").first().innerText();
  for (const w of ["씨앗", "증폭비", "seed", "β", "alpha", "beta"]) expect(text, `개발 용어 「${w}」`).not.toContain(w);
});

// 차트 신뢰(OWID 원리) — 차트가 있는 지면마다 갱신일·출처·CSV 꼬리가 있고, CSV 는 실제로 내려온다
test("차트마다 갱신일·출처·CSV 꼬리 · CSV 200", async ({ page, request }) => {
  for (const f of ["index", "beer", "map", "note", "ai-ops", "vessels"]) {
    await page.goto(at(f), { waitUntil: "networkidle" });
    const t = page.locator(".s-trust");
    expect(await t.count(), `${f} 신뢰 꼬리`).toBeGreaterThan(0);
    await expect(t.first().locator("[data-updated]")).toHaveCount(1);
    const href = await t.first().locator("a[download]").getAttribute("href");
    expect(href, `${f} CSV 고리`).toBeTruthy();
    if (href !== "#") { const r = await request.get(href); expect(r.status(), `${f} CSV`).toBe(200); expect(await r.text()).toContain("# 측심"); }
  }
});

// 홈 — 살아 있는 지도(2026-10-14 선장님 판정 뒤): 정지 해도 → 캔버스가 받아 움직인다 · 달이 흐르면 숫자가 돈다 · 보기 단추·관문 숫자 판
// · 달 막대를 옮기면 큰 숫자가 바뀐다 · 방·노트는 콘텐츠 목록에서 자동
test("홈: 살아 있는 지도 · 달 막대 · 콘텐츠 목록 자동 배치", async ({ page }) => {
  await page.goto(at("index"), { waitUntil: "networkidle" });
  await expect(page.locator(".live__poster")).toBeVisible(); // 정지 그림이 먼저
  await page.mouse.wheel(0, 1); await page.mouse.wheel(0, -1); // 좁은 화면은 만지면 움직인다
  await page.waitForSelector("#live-stage[data-ready='1']", { timeout: 20_000 });
  const st = () => page.evaluate(() => ({ N: window.__fm.N, t: window.__fm.t, zoom: window.__fm.cam.zoom }));
  await expect.poll(async () => (await st()).N, { timeout: 25_000, message: "흐르는 점이 있다(CI 소프트웨어 렌더에서 점이 늦게 찬다 — 기본 5초를 25초로 · QA 290)" }).toBeGreaterThan(50);
  // 그림이 실제로 바뀐다(두 장면의 픽셀이 다르다) — CI(소프트웨어 렌더 · 병렬)에서는 화면 합성기가 수십 초 장면을 못 내 캡처가 시간 초과했다(QA 115·118).
  // 그래서 화면 캡처 대신 캔버스 픽셀을 직접 읽고, 지도 시계를 손으로 한 걸음 민다(그리기 함수는 실제 것 그대로).
  const px = () => page.evaluate(() => document.getElementById("fm").toDataURL());
  const tick = (sec) => page.evaluate((s) => { const f = window.__fm; f.step(s); f.o.camStep ? f.o.camStep(f, s) : f.camStep(s); f.draw(); }, sec);
  const s1 = await px(); await tick(0.4); const s2 = await px();
  expect(s1 === s2, "캔버스가 움직이지 않는다").toBe(false);
  // 달이 흐르면 머리 숫자가 바뀐다(한 달 = 7초 — 시계를 한 달 앞으로 민다)
  const ym = await page.locator("#fm-ym").innerText();
  await page.evaluate(() => { window.__fm.t += 7; }); await tick(0.05);
  await expect(page.locator("#fm-ym")).not.toHaveText(ym, { timeout: 10_000 });
  // [2026-10-15 P0] 첫 화면 = 수도권(가까이) · 「아시아」 → 멀리 · 「인천 관문」 → 더 가까이(비행 3.2초를 지도 시계로 넘긴다) · 관문 숫자 판이 열린다
  expect((await st()).zoom, "첫 화면이 수도권이 아니다").toBeGreaterThan(7);
  await page.locator("[data-view=asia]").click();
  await page.evaluate(() => { window.__fm.t += 4; }); await tick(0.05);
  await expect.poll(async () => (await st()).zoom, { timeout: 10_000 }).toBeLessThan(4);
  await page.locator("[data-view=incheon]").click();
  await page.evaluate(() => { window.__fm.t += 4; }); await tick(0.05);
  await expect.poll(async () => (await st()).zoom, { timeout: 10_000 }).toBeGreaterThan(8.3);
  await page.locator("#fm-gates").click();
  await expect(page.locator("#fm-panel")).toBeVisible();
  await expect(page.locator("#fm-p-dl")).toContainText("인천공항");
  await page.locator("#fm-x").click();
  await expect(page.locator("#fm-panel")).toBeHidden();
  // 흐름은 월 통계를 그린 것 — 실시간이 아니라고 화면에 적었다
  await expect(page.locator(".live__legend")).toContainText("실시간 위치가 아닙니다");
  // 같이 푸는 질문 — 질문마다 지면 하나
  const Q = JSON.parse(readFileSync("data/questions.json", "utf-8")).questions;
  await expect(page.locator(".qs > li")).toHaveCount(Q.length);
  const v = await page.locator("#now-v").innerText();
  await page.locator("#now-m").fill("0");
  await expect(page.locator("#now-v")).not.toHaveText(v);
  const rooms = JSON.parse(readFileSync("data/rooms.json", "utf-8"));
  await expect(page.locator(".s-index > li")).toHaveCount(rooms.rooms.length);
  expect(await page.locator(".s-notes li").count()).toBeGreaterThan(0);
  expect(await page.locator(".s-notes li[data-stage]").first().getAttribute("data-stage")).toMatch(/^(초안|갱신 중|정본)$/);
});

// 지도 움직임 — 달 막대를 옮기면 달·점 숫자가 바뀌고, 그대로 두면 달이 흐른다(움직임 줄이기 설정이 아닐 때)
test("지도: 달 막대 · 자동으로 흐르는 달 · 개념선 0(2026-10-20 품질기준 Q3)", async ({ page }) => {
  await page.goto(at("map"), { waitUntil: "networkidle" });
  await page.mouse.move(20, 20); // 움직이는 지도는 사람이 움직이면 뜬다
  await page.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 });
  await page.locator("#ds-m").fill("0");
  const ym0 = await page.locator("#ds-ym").innerText();
  const v0 = await page.locator('[data-v="신항"]').innerText();
  await page.locator("#ds-m").fill(String(await page.locator("#ds-m").getAttribute("max")));
  await expect(page.locator("#ds-ym")).not.toHaveText(ym0);
  await expect(page.locator('[data-v="신항"]')).not.toHaveText(v0);
  await page.click("#ds-play");
  const a = await page.getAttribute("#ds-map", "data-month");
  await expect.poll(() => page.getAttribute("#ds-map", "data-month"), { timeout: 5_000 }).not.toBe(a);
  await expect(page.locator("[data-content='ds-map-foot']")).not.toContainText("개념선");
});

// [2026-10-20 내림 · docs/품질기준.md Q2·Q3] 공급망 따라가기 — 주소는 살아 있고 지도 지면으로 넘긴다 · 메뉴·홈·소개·사이트맵에서 빠졌다
test("공급망 따라가기: 내림 — 지도로 넘김 · 색인 제외 · 메뉴·사이트맵·소개 링크 0", async ({ page, request }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  const html = await (await request.get(at("follow"))).text();
  expect(html).toMatch(/http-equiv="refresh" content="0;url=\/incheon-port-analysis\/map\.html"/);
  expect(html).toContain('name="robots" content="noindex');
  expect(readFileSync("astro/dist/sitemap.xml", "utf-8")).not.toContain("follow");
  for (const f of ["index", "about", "map"]) expect(readFileSync(`astro/dist${PATH[f]}`, "utf-8"), `${f} 에 따라가기 링크`).not.toContain("map/follow.html");
  for (const f of ["data/rooms.json", "data/questions.json"]) expect(readFileSync(f, "utf-8"), f).not.toContain("/map/follow.html");
});

// 선박 리플레이(§3-3) — 월 집계라고 적었다 · 원천 행 수·기간이 수집 CSV 와 맞다(V1) · 막대·재생으로 달이 바뀐다 · 반대 지표
test("선박 리플레이: 월 집계 표기 · 원천 대조 · 달 막대 · 재생 · 반대 지표", async ({ page, request }) => {
  await page.goto(at("vessels"), { waitUntil: "networkidle" });
  // [2026-10-15 P0] 들어오자마자 돈다 — 손대지 않았는데 달이 바뀐다
  await expect.poll(() => page.evaluate(() => window.__vrPlay?.on), { timeout: 5_000 }).toBe(true);
  const csv = readFileSync("data/collected/vessel-monthly.csv", "utf-8").trim().split("\n").slice(1);
  const yms = csv.map((l) => l.split(",")[0]);
  const V = JSON.parse(readFileSync("data/derived/vessel_replay.json", "utf-8"));
  expect(V.source_rows).toBe(csv.length);
  expect(V.source_months[0]).toBe(yms.reduce((a, b) => (a < b ? a : b)));
  await expect(page.locator("[data-v1]")).toContainText(`원천 ${V.source_rows}행`);
  await expect(page.locator("main, body").first()).toContainText("개별 선박 아님");
  await expect(page.locator(".counter")).toContainText("반대 지표");
  // 처음 그려지는 달(서버가 낸 HTML) = 마지막 달 — 자동 재생이 곧 바꾸므로 HTML 원문으로 본다
  const html = await (await request.get(page.url())).text();
  const ym = (html.match(/id="vr-ym"[^>]*>([^<]+)</) || [])[1];
  await page.locator("#vr-m").fill("0");
  // 만지면 멈춘다(6초 뒤 다시)
  expect(await page.evaluate(() => window.__vrPlay.on), "달 막대를 만졌는데 멈추지 않았다").toBe(false);
  await expect(page.locator("#vr-ym")).toHaveText(V.months[0]);
  await expect(page.locator("#vr-inc")).toHaveText(String(V.ocean_arrivals["인천"][0]));
  await page.click("#vr-play");
  await expect.poll(() => page.getAttribute("#vr-chart", "data-month"), { timeout: 5_000 }).not.toBe(V.months[0]);
  expect(ym).toBe(V.latest.ym);
});

// 지도 첫 화면(2026-10-14 출고 검사 · 모바일 성능 · 10-15 P0 자동 재생) — 좁은 화면은 maplibre 를 받지 않고 해도 그림 위에서 달이 스스로 흐른다(가벼운 첫 장면).
// 넓은 화면은 한가할 때 maplibre 를 받아 이어 돈다. 둘 다 클릭 없이.
test("지도: 클릭 없이 달이 흐른다 · 좁은 화면은 maplibre 0 · 움직이면 뜬다", async ({ page }) => {
  const got = [];
  page.on("request", (r) => got.push(r.url()));
  await page.goto(at("map"), { waitUntil: "networkidle" });
  const narrow = (page.viewportSize()?.width || 1440) <= 720;
  if (narrow) expect(got.filter((u) => /maplibre|pmtiles/.test(u)), "좁은 화면 손대기 전 지도 엔진 요청").toEqual([]);
  await expect(page.locator("#map-poster .h-pt")).toHaveCount(JSON.parse(readFileSync("data/derived/places.json", "utf-8")).places.length + 1);
  // 좁은 화면은 첫 장면(해도 그림)이 지도 칸을 채운다 · 넓은 화면은 maplibre 가 곧 받아 그림이 물러난다 — 지도 칸 자체를 잰다
  const box = await page.locator(narrow ? "#map-poster" : ".ds-map-box").boundingBox();
  expect(box && box.height, "지도 칸이 채워져 있다").toBeGreaterThan(300);
  // 클릭 없이 달이 바뀐다(첫 장면이든 maplibre 든)
  const f0 = await page.evaluate(() => window.__mapPlay.frames);
  await expect.poll(() => page.evaluate(() => window.__mapPlay.frames), { timeout: 15_000, message: "손대지 않았는데 달이 안 흐른다" }).toBeGreaterThan(f0 + 1);
  await page.mouse.move(30, 30);
  await page.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 });
});

// [2026-10-15 P2 「사업」] 홈·소개 — 「문의 틀로 메일」 = mailto(제목·적을 칸 미리 채움) · 원문 HTML 에 주소 0 · 외부 요청 0(양식 서버 없음)
test("문의 틀로 메일 — 제목·적을 칸 · 원문에 주소 없음", async ({ page, request }) => {
  for (const p of ["index", "about"]) {
    const html = await (await request.get(at(p === "about" ? "about" : "index"))).text();
    expect(html, `${p} 원문에 메일 주소`).not.toMatch(/[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}/);
  }
  await page.goto(at("index"));
  const a = page.locator('[data-c=mail][data-ask="1"]').first();
  await expect(a).toBeVisible();
  await a.dispatchEvent("pointerdown");
  const href = await a.getAttribute("href");
  expect(href).toMatch(/^mailto:[^?]+@[^?]+\?subject=/);
  expect(decodeURIComponent(href.split("subject=")[1])).toContain("[측심 문의]");
});

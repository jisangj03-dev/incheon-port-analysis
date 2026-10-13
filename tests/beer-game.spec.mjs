// 맥주 게임(정체성 전환 정본 §3-1) — G1 규칙 파일 · G2 재현 · G3 증폭비·비용 고정 · G4 서버·쿠키·외부 요청 0 · G5 360px · G6 만든 사람 노트·AI 표기
// · §2-1 화면 수치 = 데이터 파일. 지면은 lab/(SOUNDING_LAB=1 빌드에만) — 공개 배포물에는 없다.
import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { check } from "../tools-build/check-data-numbers.mjs";
const req = createRequire(import.meta.url);
const B = req("../assets/js/beer-game.js"), R = req("../data/sim/beer-game.json");
const PAGE = "/incheon-port-analysis/lab/beer-game.html";

test("G1: 규칙 상수는 data/ 파일 하나 · 출처(Sterman 1989, Management Science 35(3))", () => {
  expect(R.stages.map((s) => s.id)).toEqual(["retailer", "wholesaler", "distributor", "factory"]);
  expect(R.source.cite).toContain("Sterman");
  expect(R.source.cite).toContain("35(3)");
  for (const k of ["weeks", "initial", "delays", "cost", "demand", "autoPolicy"]) expect(R[k]).toBeTruthy();
  // 엔진 본문에 규칙 숫자를 박지 않았다 — 규칙 상수 이름은 전부 rules.* 로만 읽는다
  const src = readFileSync("assets/js/beer-game.js", "utf-8");
  for (const v of [R.autoPolicy.alpha, R.autoPolicy.beta, R.autoPolicy.theta, R.autoPolicy.targetStock, R.cost.holding]) expect(src).not.toContain(String(v));
});

test("G2·G3: 같은 씨앗·같은 주문 = 같은 결과 · 증폭비와 비용 고정값", () => {
  // 네 단계 모두 자동, 계단 수요 — 고정 결과(규칙 파일이 바뀌면 이 값도 같이 바뀐다)
  const s = B.summary(B.replay(R, { role: -1 }));
  expect(s.stages.map((x) => Math.round(x.amplification * 100) / 100)).toEqual([5.51, 25.79, 55.91, 82.56]);
  expect(s.stages.map((x) => x.cost)).toEqual([299, 695, 962.5, 741.5]);
  expect(s.totalCost).toBe(2698);
  // 위로 갈수록 출렁임이 커진다(채찍효과)
  for (let i = 1; i < 4; i++) expect(s.stages[i].amplification).toBeGreaterThan(s.stages[i - 1].amplification);
  const opt = { role: 2, demand: "random", seed: 7, orders: Array.from({ length: R.weeks }, (_, i) => (i * 5) % 11) };
  expect(JSON.stringify(B.summary(B.replay(R, opt)))).toBe(JSON.stringify(B.summary(B.replay(R, opt))));
  expect(B.summary(B.replay(R, { ...opt, seed: 8 })).totalCost).not.toBe(B.summary(B.replay(R, opt)).totalCost);
  // 증폭비 = 주문 분산 ÷ 수요 분산 — 손 계산과 같다
  expect(B.variance([4, 8])).toBe(4);
  const g = B.replay(R, { role: -1 }), dv = B.variance(g.demand);
  expect(B.summary(g).stages[0].amplification).toBeCloseTo(B.variance(g.stages[0].hist.order) / dv, 12);
});

test("G4: 주소 값 ↔ 판 설정(서버 0) · 이상한 값은 잘라 낸다", () => {
  const o = { role: 1, demand: "random", seed: 3, orders: [4, 5, 6] };
  expect(B.decode("?" + B.encode(o), R)).toEqual(o);
  expect(B.decode("?r=9&d=x&s=-2&o=-1.a.3", R)).toEqual({ role: 3, demand: "step", seed: 1, orders: [0, 0, 3] });
});

test("§2-1: 지면에 보이는 숫자는 전부 규칙 파일에 있다", () => {
  const r = check(readFileSync("astro/dist/lab/beer-game.html", "utf-8"), [readFileSync("data/sim/beer-game.json", "utf-8")]);
  expect(r.checked).toBeGreaterThan(5);
  expect(r.bad).toEqual([]);
});

test("화면: 한 판 끝까지 · 결과 주소로 되살림 · 360px 넘침 0 · 외부 요청·쿠키 0 · 노트 3줄", async ({ page, context }, info) => {
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { const h = new URL(r.request().url()).hostname; if (!/cloudflareinsights\.com$/.test(h)) ext.push(r.request().url()); return r.abort(); });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  if (info.project.name === "iphone-13") await page.setViewportSize({ width: 360, height: 720 });
  await page.goto(PAGE);
  for (const k of ["why", "how", "limits"]) await expect(page.locator(`[data-note="${k}"]`)).not.toBeEmpty();
  await expect(page.locator("[data-ai-mark]")).toContainText("AI 정리");
  await page.selectOption("#role", "1");
  await page.click("#start");
  for (let w = 0; w < R.weeks; w++) {
    await page.fill("#order", String(w < 4 ? 4 : 8));
    await page.press("#order", "Enter");
  }
  await expect(page.locator("#result")).toBeVisible();
  await expect(page.locator("#rows tr")).toHaveCount(R.stages.length);
  const verdict = await page.locator("#verdict").textContent();
  expect(page.url()).toContain("o=");
  const sw = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(sw).toBeLessThanOrEqual(0);
  // 주소만으로 같은 판
  await page.goto(page.url());
  await expect(page.locator("#verdict")).toHaveText(verdict);
  expect((await context.cookies()).length).toBe(0);
  expect(ext).toEqual([]);
  expect(errors).toEqual([]);
});

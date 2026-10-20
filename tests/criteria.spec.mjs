// 개편 기준 자동 판정(2026-10-12) — docs/측심_전면개편_판정기준_선커밋_20261010.md 의 번호를 시험 이름에 단다.
// 외부 요청: Cloudflare 분석 둘만 허용(기준 17)하고, 시험에서는 그 둘도 끊는다(밖으로 나가지 않는다).
import { test, expect } from "@playwright/test";
import { readFileSync, existsSync } from "node:fs";

const BASE = "/incheon-port-analysis";
const ALLOWED = new Set(["static.cloudflareinsights.com", "cloudflareinsights.com"]);
const sitemap = readFileSync("astro/dist/sitemap.xml", "utf-8");
const PAGES = [...sitemap.matchAll(/<loc>https:\/\/jisangj03-dev\.github\.io([^<]+)<\/loc>/g)].map((m) => decodeURI(m[1]))
  .concat([`${BASE}/docs/FACTS.html`, `${BASE}/docs/10_판정결과.html`, `${BASE}/404.html`, `${BASE}/go/sheet.html`]);

async function watch(page) {
  const ext = [], disallowed = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (route) => {
    const h = new URL(route.request().url()).hostname;
    ext.push(h);
    if (!ALLOWED.has(h)) disallowed.push(route.request().url());
    return route.abort();
  });
  return { ext, disallowed };
}

test.describe("기준 9·10·14·15·16·17·19·24 — 전 지면", () => {
  for (const p of PAGES) {
    test(`${p}`, async ({ page }, info) => {
      const w = await watch(page);
      const errors = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      if (info.project.name === "iphone-13") await page.setViewportSize({ width: 320, height: 640 });
      const res = await page.goto(p, { waitUntil: "load" });
      expect(res.status(), "지면 응답").toBe(p.endsWith("404.html") ? 200 : 200);
      // 10 레이아웃 없는 지면 0
      await expect(page.locator("header.s-mast"), "상단 바").toHaveCount(1);
      await expect(page.locator("footer.foot"), "바닥글").toHaveCount(1);
      // 9 description·OG 누락 0
      const meta = await page.evaluate(() => ({
        d: document.querySelector('meta[name="description"]')?.content || "",
        t: document.querySelector('meta[property="og:title"]')?.content || "",
        i: document.querySelector('meta[property="og:image"]')?.content || "",
        c: document.querySelector('link[rel="canonical"]')?.href || "",
      }));
      expect(meta.d.length, "description").toBeGreaterThan(20);
      expect(meta.t && meta.i && meta.c, "OG·canonical").toBeTruthy();
      // 15 신뢰 지면 링크 · 24 새 글 받아보기 링크 — 바닥글에 하나씩
      await expect(page.locator("footer [data-trust]")).toHaveCount(1);
      await expect(page.locator("footer [data-newsletter]")).toHaveCount(1);
      await expect(page.locator("footer [data-newsletter]")).toHaveAttribute("href", "/incheon-port-analysis/go/newsletter.html");
      // 14 차트·지도 위젯마다 갱신일
      const charts = await page.locator("[data-chart]").count();
      const chartsWithDate = await page.locator("[data-chart]:has([data-updated])").count();
      expect(chartsWithDate, "갱신일 없는 차트").toBe(charts);
      // 19 AI 장면 표기 — 포스터·영상이 있으면 표기가 있어야 한다
      if (await page.locator(".hero__poster, .hero__video").count()) await expect(page.locator(".ai-mark")).toHaveCount(1);
      // 10 가로 넘침 0(모바일 프로젝트는 320px 로 잰다)
      const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(over, "가로 넘침(px)").toBeLessThanOrEqual(0);
      // 17 외부 요청 = Cloudflare 분석 둘뿐
      expect(w.disallowed, "허용 밖 외부 요청").toEqual([]);
      expect(errors, "스크립트 오류").toEqual([]);
    });
  }
});

// 정체성 전환(2026-10-14 · docs/측심_정체성전환_판정기준_선커밋_20261014.md §2·§5-4) — 종전 기준 2·12(도구 링크·사람별 입구 넷)를 대신한다.
test("정체성 §2 — 상단 메뉴 = 구조 넷 · 첫 화면에 실명 · 크몽·셀러 입구 0", async ({ page }) => {
  await watch(page);
  await page.goto(`${BASE}/`);
  await expect(page.locator("header.s-mast nav a")).toHaveText(["도구", "노트", "소개"]); // 2026-10-20 지도 지면을 내렸다 — 첫 화면이 지도
  const P = JSON.parse(readFileSync("data/profile.json", "utf-8"));
  const vh = page.viewportSize().height;
  const lead = page.locator(".live__who");
  await expect(lead).toContainText(P.name);
  const b = await lead.boundingBox();
  expect(b && b.y + b.height <= vh, "실명 한 줄이 첫 화면 안").toBe(true);
  const html = await page.content();
  for (const w of ["kmong", "크몽", "data-persona", "/for/"]) expect(html, w).not.toContain(w);
  // 메뉴마다 한 번 눌러 200
  for (const href of await page.locator("header.s-mast nav a").evaluateAll((a) => a.map((x) => x.getAttribute("href")))) {
    expect((await page.request.get(href)).status(), href).toBe(200);
  }
});

test("기존 주소 유지 — 옛 목록·입구·크몽 주소는 살아 있고 새 자리로 넘긴다", async ({ page }) => {
  const MOVED = { "/reports/": "/notes.html", "/for/pro.html": "/", "/for/press.html": "/", "/for/student.html": "/", "/go/kmong-829076.html": "/", "/go/kmong-824011.html": "/" };
  for (const [from, to] of Object.entries(MOVED)) {
    const html = await (await page.request.get(`${BASE}${from}`)).text();
    expect(html, from).toContain(`url=${BASE}${to}"`);
    expect(html, `${from} 색인 제외`).toContain('name="robots" content="noindex');
  }
  // [2026-10-20 품질 재정비 · docs/품질기준.md §3] 내린 지면 — 주소는 살아 있고 상위 지면으로 넘긴다 · 색인 제외 · 사이트맵에 없다
  const DOWN = {"/tools/bid-radar.html": "/tools/", "/map.html": "/", "/map/follow.html": "/", "/tools/anchorage.html": "/tools/", "/notes/ai-ops.html": "/about.html", "/tools/logistics-cost.html": "/tools/", "/tools/simulate.html": "/tools/", "/tools/warehouse-map.html": "/tools/", "/sim/": "/tools/", "/reports/report_03_공컨테이너_수출입방향.html": "/notes.html"};
  for (const [from, to] of Object.entries(DOWN)) {
    const html = await (await page.request.get(`${BASE}${encodeURI(from)}`)).text();
    expect(html, from).toContain(`url=${BASE}${to}"`);
    expect(html, `${from} 색인 제외`).toContain('name="robots" content="noindex');
    expect(sitemap, `${from} 사이트맵`).not.toContain(`incheon-port-analysis${encodeURI(from)}<`);
  }
});

test("기준 9 — sitemap.xml · robots.txt 200 · 옛 블로그 이동 주소 /go/sheet · 뉴스레터", async ({ page }) => {
  expect((await page.request.get(`${BASE}/sitemap.xml`)).status()).toBe(200);
  expect((await page.request.get(`${BASE}/robots.txt`)).status()).toBe(200);
  const go = await (await page.request.get(`${BASE}/go/sheet.html`)).text();
  expect(go).toContain("logisticsforeveryone.tistory.com/79");
  // 기준 24 — 뉴스레터(물류로그 beehiiv · 2026-10-12 선장님 지정)
  const nl = await (await page.request.get(`${BASE}/go/newsletter.html`)).text();
  expect(nl).toContain("logisticslog.beehiiv.com/subscribe");
  // [2026-10-15 P1 ⑤] 「차단됨」 — 구독 링크는 새 창(틀 안에서 beehiiv 로 넘어가지 않게) · 이동 지면 손 링크는 최상위 창 · 이동 지면 200
  expect(nl).toMatch(/href="https:\/\/logisticslog\.beehiiv\.com\/subscribe[^"]*"[^>]*target="_top"/);
  expect((await page.request.get(`${BASE}/go/newsletter.html`)).status()).toBe(200);
  await page.goto(`${BASE}/`);
  const a = page.locator("footer a[data-newsletter]");
  await expect(a).toHaveAttribute("target", "_blank");
  await expect(a).toHaveAttribute("rel", /noopener/);
});

test("출처 대장 — 행마다 이용 조건 칸이 다 차 있다(기준 16 · 보고서는 2026-10-20 내림)", async () => {
  const reg = JSON.parse(readFileSync("data/sources.json", "utf-8"));
  for (const s of reg.sources) for (const k of ["license", "kogl", "commercial", "modify", "checked"]) expect(s[k], `${s.id}.${k}`).toBeTruthy();
});

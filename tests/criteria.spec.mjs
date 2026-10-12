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
      await expect(page.locator("header.mast"), "상단 바").toHaveCount(1);
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

test("기준 2·12 — 첫 화면(스크롤 0)에 도구 링크·사람별 입구 넷·상단 메뉴 「도구」", async ({ page }) => {
  await watch(page);
  await page.goto(`${BASE}/`);
  const vh = page.viewportSize().height;
  const inView = async (loc) => { const b = await loc.boundingBox(); return !!b && b.y >= 0 && b.y + b.height <= vh; };
  expect(await inView(page.locator("[data-tool-link]")), "도구 링크가 첫 화면 안").toBe(true);
  const who = page.locator("[data-persona]");
  await expect(who).toHaveCount(4);
  for (let i = 0; i < 4; i++) expect(await inView(who.nth(i)), `입구 ${i + 1} 첫 화면 안`).toBe(true);
  await expect(page.locator("header.mast nav a", { hasText: "도구" })).toHaveCount(1);
  // 입구마다 한 번 눌러 200
  for (let i = 0; i < 4; i++) {
    const href = await who.nth(i).getAttribute("href");
    const r = await page.request.get(href);
    expect(r.status(), href).toBe(200);
  }
});

test("기준 9 — sitemap.xml · robots.txt 200, 블로그 /79 링크(계산기 → 블로그)", async ({ page }) => {
  expect((await page.request.get(`${BASE}/sitemap.xml`)).status()).toBe(200);
  expect((await page.request.get(`${BASE}/robots.txt`)).status()).toBe(200);
  const html = await (await page.request.get(`${BASE}/tools/logistics-cost.html`)).text();
  expect(html).toContain(`${BASE}/go/sheet.html`);
  const go = await (await page.request.get(`${BASE}/go/sheet.html`)).text();
  expect(go).toContain("logisticsforeveryone.tistory.com/79");
});

test("기준 16 — 보고서마다 출처 대장에 행이 있다", async () => {
  const reg = JSON.parse(readFileSync("data/sources.json", "utf-8"));
  const used = new Set(reg.sources.flatMap((s) => s.used_by));
  const reports = [...sitemap.matchAll(/\/reports\/([^<]+)\.html/g)].map((m) => decodeURI(m[1]));
  const missing = reports.filter((r) => !used.has(r));
  expect(missing, "대장에 없는 보고서").toEqual([]);
  for (const s of reg.sources) for (const k of ["license", "kogl", "commercial", "modify", "checked"]) expect(s[k], `${s.id}.${k}`).toBeTruthy();
});

test("기준 18 — 보고서 3층(① 결론 ② 만지기/준비 중 ③ 원문 접힘)", async ({ page }) => {
  await watch(page);
  const reports = [...sitemap.matchAll(/(\/incheon-port-analysis\/reports\/[^<]+\.html)/g)].map((m) => decodeURI(m[1]));
  for (const r of reports) {
    await page.goto(r);
    await expect(page.locator("#l1"), r).toHaveCount(1);
    await expect(page.locator("#l2"), r).toHaveCount(1);
    await expect(page.locator("details#original"), r).toHaveCount(1);
  }
});

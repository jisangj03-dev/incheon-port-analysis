// B6 공유 카드 · B7 퍼가기 — 보고서마다 1200×630 카드가 있고 og:image 가 그것을 가리키는가 · 퍼가기 지면이 밖으로 요청을 안 내는가.
// 카드는 빌드 뒤 `npm run site:og` 가 만든다(CI 는 시험 전에 돈다). 로컬에서 안 돌렸으면 건너뛴다.
import { test, expect } from "@playwright/test";
import { readFileSync, existsSync, readdirSync } from "node:fs";

const reports = [...readFileSync("astro/dist/sitemap.xml", "utf-8").matchAll(/\/reports\/([^<]+)\.html/g)].map((m) => decodeURI(m[1]));
const jpegSize = (buf) => { // SOF0/SOF2 표지에서 높이·너비
  for (let i = 2; i < buf.length; ) {
    if (buf[i] !== 0xff) return null;
    const m = buf[i + 1], len = buf.readUInt16BE(i + 2);
    if (m === 0xc0 || m === 0xc2) return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) };
    i += 2 + len;
  }
  return null;
};

test("B6 — 보고서마다 1200×630 카드 · og:image 가 그 카드 · 틀 HTML 은 배포물에 없다", async ({ request }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  test.skip(!existsSync("astro/dist/og") || readdirSync("astro/dist/og").some((f) => f.endsWith(".html")), "npm run site:og 를 안 돌렸다");
  expect(reports.length).toBeGreaterThan(10);
  for (const id of reports) {
    const buf = readFileSync(`astro/dist/og/${id}.jpg`);
    expect(jpegSize(buf), id).toEqual({ w: 1200, h: 630 });
    const html = await (await request.get(`/incheon-port-analysis/reports/${id}.html`)).text();
    const m = html.match(/<meta property="og:image" content="([^"]+)"/);
    expect(decodeURI(m[1]), id).toBe(`https://jisangj03-dev.github.io/incheon-port-analysis/og/${id}.jpg`);
  }
});

test("B7 — 퍼가기 지면: 위젯이 돌고 외부 요청 0(분석도 없다) · 출처 링크 · 보고서 지면에 퍼가기 코드", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => { ext.push(r.request().url()); return r.abort(); });
  await page.goto("/incheon-port-analysis/embed/report_04_공컨테이너_연도별추세.html");
  await expect(page.locator(".rc .rc__say")).toContainText("배");
  await expect(page.locator(".em-src a")).toHaveAttribute("href", /reports\/report_04/);
  expect(await page.locator('meta[name="robots"][content="noindex"]').count()).toBe(1);
  expect(ext, "퍼가기 지면은 분석 비컨도 안 싣는다").toEqual([]);
  await page.goto("/incheon-port-analysis/reports/report_04_공컨테이너_연도별추세.html");
  await page.locator(".rc__embed").click();
  await expect(page.locator(".rc__code textarea")).toHaveValue(/<iframe src="https:\/\/jisangj03-dev\.github\.io\/incheon-port-analysis\/embed\/report_04/);
});
